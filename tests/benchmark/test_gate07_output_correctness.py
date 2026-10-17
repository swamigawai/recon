"""Gate 07 Independent Output Correctness & Real-World Validation Benchmark.

Validates:
1. Phase Three: Mapping correctness on unfamiliar schema without synonym cheating.
2. Phase Four: Exact value-by-value transformation output vs independent expected output.
3. Phase Five: 100% pre-declared fault ledger quarantine recall and zero data loss accounting.
4. Phase Six: Adapter repeatability, deterministic code, and security boundary verification.
5. Phase Seven: End-to-end API workflow consistency and report downloads.
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
from recon.reporting.generator import build_readiness_report, render_markdown_report
from recon.reporting.models import ReadinessState
from recon.risks.evaluator import evaluate_risks
from recon.server.app import create_app
from recon.validation.executor import validate_adapter, compile_adapter_sandbox


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def healthcare_fixtures(fixtures_dir: Path):
    contract_path = fixtures_dir / "target_contract_healthcare_encounter.json"
    csv_path = fixtures_dir / "healthcare_encounters_raw.csv"
    expected_path = fixtures_dir / "healthcare_encounters_expected_output.json"

    contract = load_target_contract(contract_path)
    dataset = load_dataset(csv_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    return contract, dataset, expected


def test_phase3_mapping_correctness_and_blockers(healthcare_fixtures):
    """Verifies that unfamiliar required fields remain unresolved, block adapter generation, and require human approval."""
    contract, dataset, _ = healthcare_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # 1. Total fields in target contract: 11
    assert len(plan.proposals) == 11

    # 2. Verify Exact Matches (7 fields)
    assert plan.proposals["encounter_date"].source_field == "encounter_date"
    assert plan.proposals["department"].source_field == "department"
    assert plan.proposals["department"].transformation_rule == "uppercase_strip"
    assert plan.proposals["clinician_notes"].source_field == "clinician_notes"
    assert plan.proposals["copay_amount"].source_field == "copay_amount"
    assert plan.proposals["billing_code"].source_field == "billing_code"
    assert plan.proposals["emergency_flag"].source_field == "emergency_flag"
    assert plan.proposals["insurance_provider"].source_field == "insurance_provider"

    # 3. Verify Ambiguous Match with Alternative Candidates (1 field)
    facility_prop = plan.proposals["facility_code"]
    assert facility_prop.source_field == "facility_code_primary"
    assert "facility_code_billing" in facility_prop.alternative_candidates

    # 4. Verify Unfamiliar Fields remain UNRESOLVED (3 fields: all required)
    unresolved_fields = plan.unresolved_proposals()
    unresolved_names = {p.target_field for p in unresolved_fields}
    assert unresolved_names == {"encounter_id", "patient_id", "visit_duration_minutes"}

    for name in unresolved_names:
        prop = plan.proposals[name]
        assert prop.source_field is None
        assert prop.status == MappingStatus.UNRESOLVED
        assert prop.mapping_type == MappingType.MISSING_SOURCE

    # 5. Risk Assessment: Critical Blocker
    risks = evaluate_risks(profile, contract, plan)
    assert risks.is_blocked is True
    critical_rules = [f.rule_id for f in risks.critical_findings]
    assert critical_rules.count("R001_MISSING_REQUIRED_FIELD") == 3

    # 6. Adapter generation MUST FAIL when required fields are unresolved
    with pytest.raises(AdapterError) as exc_info:
        # Wrap in mock approved plan without required mappings
        fake_approved = approve_mapping_plan(plan, overrides={
            # Only approve one, leave encounter_id and patient_id missing
            "encounter_date": {"source_field": "encounter_date", "status": MappingStatus.APPROVED}
        })
        generate_adapter(fake_approved, contract)
    assert "Cannot generate adapter: approved mapping plan is incomplete" in str(exc_info.value)


def test_phase4_and_5_exact_transformation_output_and_quarantine_accounting(healthcare_fixtures):
    """Verifies value-by-value transformation match against independent ground truth and 100% quarantine recall."""
    contract, dataset, expected_data = healthcare_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # Human reviewer provides overrides for unfamiliar required fields
    overrides = {
        "encounter_id": {"source_field": "visit_ref", "status": MappingStatus.APPROVED},
        "patient_id": {"source_field": "subject_id", "status": MappingStatus.APPROVED},
        "visit_duration_minutes": {"source_field": "duration_min", "status": MappingStatus.APPROVED},
    }
    approved_plan = approve_mapping_plan(plan, reviewer="clinical_reviewer", overrides=overrides)
    assert approved_plan.is_complete is True

    # Generate adapter and validate
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 1. Zero Data Loss Accounting
    assert validation.total_input_records == 10
    assert validation.valid_records_count == 4
    assert validation.quarantined_records_count == 6
    assert validation.valid_records_count + validation.quarantined_records_count == 10

    # 2. Exact Value-by-Value Output Match
    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid_records, quarantined_records = sandbox["transform_dataset"](dataset.rows)

    expected_valid = expected_data["valid_records"]
    assert len(valid_records) == len(expected_valid)

    for i in range(len(valid_records)):
        actual = valid_records[i]
        expected = expected_valid[i]
        assert actual == expected, f"Record {i+1} mismatch:\nActual:   {actual}\nExpected: {expected}"

    # Specific Verification 1: Legitimate text resembling null is PRESERVED
    assert valid_records[1]["clinician_notes"] == "None of the above symptoms reported; patient clear."
    assert valid_records[3]["clinician_notes"] == "N/A - see chart notes from EMT"
    assert valid_records[3]["insurance_provider"] == "Not Applicable Inc."

    # Specific Verification 2: Null tokens in nullable fields become None
    assert valid_records[2]["clinician_notes"] is None
    assert valid_records[2]["copay_amount"] is None

    # Specific Verification 3: Extra columns excluded
    for rec in valid_records:
        assert "room_number" not in rec
        assert "facility_code_billing" not in rec

    # 3. Fault Ledger & Quarantine Recall Verification
    expected_faults = expected_data["quarantined_fault_ledger"]
    assert len(quarantined_records) == len(expected_faults)

    for actual_q, exp_f in zip(quarantined_records, expected_faults):
        assert actual_q["record_index"] == exp_f["record_index"]
        assert exp_f["error_code"] in actual_q["error_codes"]
        assert any(exp_f["expected_error_substring"] in err for err in actual_q["errors"])


def test_phase6_adapter_repeatability_and_cleanliness(healthcare_fixtures):
    """Verifies that generated adapter code is fully deterministic and contains no unauthorized operations."""
    contract, dataset, _ = healthcare_fixtures

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    overrides = {
        "encounter_id": {"source_field": "visit_ref", "status": MappingStatus.APPROVED},
        "patient_id": {"source_field": "subject_id", "status": MappingStatus.APPROVED},
        "visit_duration_minutes": {"source_field": "duration_min", "status": MappingStatus.APPROVED},
    }
    approved_plan = approve_mapping_plan(plan, reviewer="tester", overrides=overrides)

    adapter_1 = generate_adapter(approved_plan, contract)
    adapter_2 = generate_adapter(approved_plan, contract)

    # 1. Deterministic code generation
    assert adapter_1.python_code == adapter_2.python_code

    # 2. Cleanliness checks
    code = adapter_1.python_code
    assert "import os" not in code
    assert "import sys" not in code
    assert "import subprocess" not in code
    assert "open(" not in code
    assert "eval(" not in code
    assert "exec(" not in code


def test_phase7_api_workflow_end_to_end(fixtures_dir: Path):
    """Verifies the complete REST API workflow from upload through approval, adapter generation, and download."""
    app = create_app()
    client = TestClient(app)

    csv_file = fixtures_dir / "healthcare_encounters_raw.csv"
    contract_file = fixtures_dir / "target_contract_healthcare_encounter.json"

    # 1. Assess endpoint via file upload
    with open(csv_file, "rb") as f_src, open(contract_file, "rb") as f_ctr:
        response = client.post(
            "/api/assess",
            files={
                "source_file": ("healthcare_encounters_raw.csv", f_src, "text/csv"),
                "contract_file": ("target_contract_healthcare_encounter.json", f_ctr, "application/json"),
            },
        )
    assert response.status_code == 200
    assess_data = response.json()
    session_id = assess_data["session_id"]
    assert assess_data["is_blocked"] is True
    assert set(assess_data["unresolved_required_fields"]) == {"encounter_id", "patient_id", "visit_duration_minutes"}

    # 2. Approve with overrides
    overrides = {
        "encounter_id": "visit_ref",
        "patient_id": "subject_id",
        "visit_duration_minutes": "duration_min",
    }
    appr_resp = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "qa_engineer", "overrides": overrides},
    )
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["readiness_state"] == ReadinessState.BLOCKED.value
    assert len(appr_data["blocking_reasons"]) > 0
    assert appr_data["validation"]["total_input_records"] == 10
    assert appr_data["validation"]["valid_records_count"] == 4
    assert appr_data["validation"]["quarantined_records_count"] == 6

    # 3. Download Markdown Report
    rep_md_resp = client.get(f"/api/download/report/{session_id}?format=md")
    assert rep_md_resp.status_code == 200
    assert "Recon Integration Readiness Report" in rep_md_resp.text
    assert "target_contract_healthcare_encounter" in rep_md_resp.text

    # 4. Download JSON Report
    rep_json_resp = client.get(f"/api/download/report/{session_id}?format=json")
    assert rep_json_resp.status_code == 200
    rep_json = rep_json_resp.json()
    assert rep_json["contract_name"] == "target_contract_healthcare_encounter"
    assert rep_json["readiness_state"] == "BLOCKED"

    # 5. Download Adapter Code
    adp_resp = client.get(f"/api/download/adapter/{session_id}")
    assert adp_resp.status_code == 200
    assert "def transform_record" in adp_resp.text

    # 6. Session cleanup
    del_resp = client.delete(f"/api/session/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "cleaned"
