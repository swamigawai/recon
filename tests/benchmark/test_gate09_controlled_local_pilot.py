"""Gate 09 Controlled Local Pilot & Real-World Validation Benchmark Suite.

Covers:
1. Mapping evidence, zero-guessing guardrails, and blocker enforcement.
2. Full transformation output verification, duplicate row preservation, and zero data loss accounting.
3. Complete FastAPI REST API workflow, session lifecycle, and report downloads.
"""

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import AdapterError
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingStatus, MappingType
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.models import ReadinessState
from recon.risks.evaluator import evaluate_risks
from recon.server.app import app
from recon.validation.executor import compile_adapter_sandbox, validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def pilot_fixtures(fixtures_dir: Path):
    contract_path = fixtures_dir / "target_contract_gate09_pilot_b2b.json"
    csv_path = fixtures_dir / "gate09_pilot_b2b_vendor_invoices.csv"
    expected_path = fixtures_dir / "gate09_pilot_expected_output.json"

    contract = load_target_contract(contract_path)
    dataset = load_dataset(csv_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    return contract, dataset, expected


def test_gate09_pilot_mapping_evidence_and_blocking(pilot_fixtures):
    """Verifies that unfamiliar and ambiguous fields are marked UNRESOLVED with zero guessing and block progression."""
    contract, dataset, _ = pilot_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # 1. Total fields in target contract: 11
    assert len(plan.proposals) == 11

    # 2. Unfamiliar required fields must be UNRESOLVED (Zero Hallucination)
    unresolved_required = ["invoice_id", "supplier_gstin", "buyer_pan", "destination_pin"]
    for field_name in unresolved_required:
        prop = plan.proposals[field_name]
        assert prop.status == MappingStatus.UNRESOLVED

    # 3. Risk Engine must report blocked status
    risks = evaluate_risks(profile, contract, plan)
    assert risks.is_blocked is True
    missing_rules = [f for f in risks.critical_findings if f.rule_id == "R001_MISSING_REQUIRED_FIELD"]
    assert len(missing_rules) == 4

    # 4. Refuse adapter generation without overrides
    with pytest.raises(AdapterError):
        generate_adapter(approve_mapping_plan(plan), contract)


def test_gate09_pilot_transformation_and_zero_loss_accounting(pilot_fixtures):
    """Verifies exact output matching, duplicate record preservation, and 100% quarantine recall."""
    contract, dataset, expected_data = pilot_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # Human reviewer overrides for unfamiliar/ambiguous fields
    overrides = {
        "invoice_id": {"source_field": "doc_number", "status": MappingStatus.APPROVED},
        "supplier_gstin": {"source_field": "gst_reg_no", "status": MappingStatus.APPROVED},
        "buyer_pan": {"source_field": "entity_pan", "status": MappingStatus.APPROVED},
        "destination_pin": {"source_field": "postal_code_primary", "status": MappingStatus.APPROVED},
    }
    approved_plan = approve_mapping_plan(plan, reviewer="pilot_lead", overrides=overrides)
    assert approved_plan.is_complete is True

    # Generate adapter and validate
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 1. Zero Data Loss Invariant: 12 Input = 5 Valid + 7 Quarantined
    assert validation.total_input_records == 12
    assert validation.valid_records_count == 5
    assert validation.quarantined_records_count == 7
    assert validation.valid_records_count + validation.quarantined_records_count == 12

    # 2. Exact Value-by-Value Match on Conforming Records
    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid_records, quarantined_records = sandbox["transform_dataset"](dataset.rows)

    expected_valid = expected_data["valid_records"]
    assert len(valid_records) == len(expected_valid)

    for i in range(len(valid_records)):
        actual = valid_records[i]
        expected = expected_valid[i]
        assert actual == expected, f"Record {i+1} mismatch:\nActual:   {actual}\nExpected: {expected}"

    # Specific Verification 1: Duplicate preservation (Row 1 and Row 2 are both preserved)
    assert valid_records[0] == valid_records[1]
    assert valid_records[0]["invoice_id"] == "INV-00042"

    # Specific Verification 2: Record resembling an error is NOT quarantined
    assert valid_records[2]["dispatch_notes"] == "ERROR: Client reported damaged outer box but contents verified intact and accepted"

    # Specific Verification 3: Null-like human text preserved
    assert valid_records[4]["dispatch_notes"] == "None of the items were returned during inspection"

    # Specific Verification 4: Extraneous source columns pruned
    for rec in valid_records:
        assert "driver_phone_number" not in rec
        assert "warehouse_dock_no" not in rec
        assert "postal_code_secondary" not in rec

    # 3. 100% Fault Recall on Injected Faults
    expected_faults = expected_data["quarantined_fault_ledger"]
    assert len(quarantined_records) == len(expected_faults)

    for actual_q, exp_f in zip(quarantined_records, expected_faults):
        assert actual_q["record_index"] == exp_f["record_index"]
        assert exp_f["error_code"] in actual_q["error_codes"]
        assert any(exp_f["expected_error_substring"] in err for err in actual_q["errors"])


def test_gate09_pilot_api_workflow_and_session_lifecycle(fixtures_dir: Path):
    """Verifies end-to-end API execution, file upload, overrides, report download, and session cleanup."""
    client = TestClient(app)

    csv_path = fixtures_dir / "gate09_pilot_b2b_vendor_invoices.csv"
    contract_path = fixtures_dir / "target_contract_gate09_pilot_b2b.json"

    # 1. Assess Upload
    with open(csv_path, "rb") as f_src, open(contract_path, "rb") as f_tgt:
        response = client.post(
            "/api/assess",
            files={
                "source_file": ("gate09_pilot_b2b_vendor_invoices.csv", f_src, "text/csv"),
                "contract_file": ("target_contract_gate09_pilot_b2b.json", f_tgt, "application/json"),
            },
        )
    assert response.status_code == 200
    assess_data = response.json()
    session_id = assess_data["session_id"]
    assert assess_data["is_blocked"] is True
    assert len(assess_data["unresolved_required_fields"]) == 4

    # 2. Reject Approval Without Overrides
    empty_appr = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "pilot_user", "overrides": {}},
    )
    assert empty_appr.status_code == 400

    # 3. Approve With Overrides
    overrides = {
        "invoice_id": "doc_number",
        "supplier_gstin": "gst_reg_no",
        "buyer_pan": "entity_pan",
        "destination_pin": "postal_code_primary",
    }
    appr_resp = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "pilot_user", "overrides": overrides},
    )
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["validation"]["total_input_records"] == 12
    assert appr_data["validation"]["valid_records_count"] == 5
    assert appr_data["validation"]["quarantined_records_count"] == 7

    # 4. Download Reports
    rep_json = client.get(f"/api/download/report/{session_id}?format=json")
    assert rep_json.status_code == 200
    assert rep_json.json()["contract_name"] == "target_contract_gate09_pilot_b2b"

    rep_md = client.get(f"/api/download/report/{session_id}?format=md")
    assert rep_md.status_code == 200
    assert "Recon Integration Readiness Report" in rep_md.text

    # 5. Download Adapter Code
    adapter_resp = client.get(f"/api/download/adapter/{session_id}")
    assert adapter_resp.status_code == 200
    assert "def transform_record" in adapter_resp.text

    # 6. Session Deletion
    del_resp = client.delete(f"/api/session/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "cleaned"

    # 7. Post-Deletion Verification
    retry_download = client.get(f"/api/download/report/{session_id}?format=json")
    assert retry_download.status_code == 404
