"""Benchmark integration test evaluating Recon on real-world B2B vendor invoicing and logistics workflows."""

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
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
def b2b_fixtures(fixtures_dir: Path):
    contract_path = fixtures_dir / "target_contract_b2b_vendor_invoice.json"
    csv_path = fixtures_dir / "b2b_vendor_invoices_raw.csv"
    expected_path = fixtures_dir / "b2b_vendor_invoices_expected_output.json"

    contract = load_target_contract(contract_path)
    dataset = load_dataset(csv_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    return contract, dataset, expected


def test_b2b_mapping_guardrails_and_blocking(b2b_fixtures):
    """Verifies that unfamiliar business fields are not hallucinated and strictly block adapter generation."""
    contract, dataset, _ = b2b_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # 1. Total fields in target contract: 11
    assert len(plan.proposals) == 11

    # 2. Unfamiliar source columns must be UNRESOLVED (Zero Hallucination)
    unresolved_required = ["invoice_number", "vendor_gstin", "buyer_pan", "destination_pincode"]
    for field_name in unresolved_required:
        prop = plan.proposals[field_name]
        assert prop.source_field is None
        assert prop.status == MappingStatus.UNRESOLVED
        assert prop.mapping_type == MappingType.MISSING_SOURCE

    # 3. Risk Engine must flag integration as BLOCKED
    risks = evaluate_risks(profile, contract, plan)
    assert risks.is_blocked is True
    missing_rules = [f for f in risks.critical_findings if f.rule_id == "R001_MISSING_REQUIRED_FIELD"]
    assert len(missing_rules) == 4


def test_b2b_exact_transformation_and_zero_loss_quarantine(b2b_fixtures):
    """Verifies 100% transformation match and 100% fault recall on real-world Indian business data errors."""
    contract, dataset, expected_data = b2b_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # Human reviewer provides overrides for the 4 unfamiliar business terms
    overrides = {
        "invoice_number": {"source_field": "bill_no", "status": MappingStatus.APPROVED},
        "vendor_gstin": {"source_field": "supplier_gst", "status": MappingStatus.APPROVED},
        "buyer_pan": {"source_field": "client_pan_id", "status": MappingStatus.APPROVED},
        "destination_pincode": {"source_field": "delivery_pincode", "status": MappingStatus.APPROVED},
    }
    approved_plan = approve_mapping_plan(plan, reviewer="finance_operations_manager", overrides=overrides)
    assert approved_plan.is_complete is True

    # Generate adapter and validate
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 1. Zero Data Loss Invariant
    assert validation.total_input_records == 10
    assert validation.valid_records_count == 4
    assert validation.quarantined_records_count == 6
    assert validation.valid_records_count + validation.quarantined_records_count == 10

    # 2. Exact Value-by-Value Match on Conforming Records
    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid_records, quarantined_records = sandbox["transform_dataset"](dataset.rows)

    expected_valid = expected_data["valid_records"]
    assert len(valid_records) == len(expected_valid)

    for i in range(len(valid_records)):
        actual = valid_records[i]
        expected = expected_valid[i]
        assert actual == expected, f"Record {i+1} mismatch:\nActual:   {actual}\nExpected: {expected}"

    # Verify subtle human text preserved and extraneous column excluded
    assert valid_records[3]["vendor_notes"] == "None of the items were returned during inspection"
    for rec in valid_records:
        assert "truck_vehicle_number" not in rec

    # 3. 100% Recall on Injected Business Faults
    expected_faults = expected_data["quarantined_fault_ledger"]
    assert len(quarantined_records) == len(expected_faults)

    for actual_q, exp_f in zip(quarantined_records, expected_faults):
        assert actual_q["record_index"] == exp_f["record_index"]
        assert exp_f["error_code"] in actual_q["error_codes"]
        assert any(exp_f["expected_error_substring"] in err for err in actual_q["errors"])


def test_b2b_api_workflow_end_to_end(fixtures_dir: Path):
    """Verifies that a user can execute the entire B2B vendor invoicing workflow via the REST API."""
    client = TestClient(app)

    csv_path = fixtures_dir / "b2b_vendor_invoices_raw.csv"
    contract_path = fixtures_dir / "target_contract_b2b_vendor_invoice.json"

    with open(csv_path, "rb") as f_src, open(contract_path, "rb") as f_tgt:
        response = client.post(
            "/api/assess",
            files={
                "source_file": ("b2b_vendor_invoices_raw.csv", f_src, "text/csv"),
                "contract_file": ("target_contract_b2b_vendor_invoice.json", f_tgt, "application/json"),
            },
        )
    assert response.status_code == 200
    assess_data = response.json()
    session_id = assess_data["session_id"]
    assert assess_data["is_blocked"] is True
    assert set(assess_data["unresolved_required_fields"]) == {
        "invoice_number",
        "vendor_gstin",
        "buyer_pan",
        "destination_pincode",
    }

    # Submit approval with human overrides
    approval_resp = client.post(
        "/api/approve-and-generate",
        json={
            "session_id": session_id,
            "reviewer": "finance_lead",
            "overrides": {
                "invoice_number": "bill_no",
                "vendor_gstin": "supplier_gst",
                "buyer_pan": "client_pan_id",
                "destination_pincode": "delivery_pincode",
            },
        },
    )
    assert approval_resp.status_code == 200
    approval_data = approval_resp.json()
    assert approval_data["validation"]["total_input_records"] == 10
    assert approval_data["validation"]["valid_records_count"] == 4
    assert approval_data["validation"]["quarantined_records_count"] == 6

    # Verify report download reflects resolved status
    report_resp = client.get(f"/api/download/report/{session_id}?format=json")
    assert report_resp.status_code == 200
    report_json = report_resp.json()
    assert report_json["contract_name"] == "target_contract_b2b_vendor_invoice"
    assert report_json["readiness_state"] in (ReadinessState.BLOCKED.value, "READY")
