"""End-to-end integration tests proving JSON input generalization across the complete Recon pipeline."""

from pathlib import Path
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report
from recon.reporting.models import ReadinessState
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


def test_json_pipeline_clean_users_end_to_end(fixtures_dir: Path):
    """Proves the entire Recon pipeline on a clean nested JSON dataset."""
    json_path = fixtures_dir / "jsonplaceholder_users.json"
    contract_path = fixtures_dir / "target_contract_user_profile.json"

    # 1. Ingestion
    dataset = load_dataset(json_path)
    assert dataset.row_count == 5

    # 2. Profiling
    profile = profile_dataset(dataset)
    assert profile.total_rows == 5
    assert "address.city" in profile.columns
    assert "company.name" in profile.columns

    # 3. Target Contract & Mapping
    contract = load_target_contract(contract_path)
    assert len(contract.fields) == 7

    plan = propose_mappings(profile, contract)
    # Check that flattened keys correctly map to target fields
    assert plan.proposals["user_id"].source_field == "id"
    assert plan.proposals["full_name"].source_field == "name"
    assert plan.proposals["email"].source_field == "email"
    assert plan.proposals["city"].source_field == "address.city"
    assert plan.proposals["postal_code"].source_field == "address.zipcode"
    assert plan.proposals["company_name"].source_field == "company.name"
    assert plan.proposals["website"].source_field == "website"

    # 4. Risks & Approval
    risks = evaluate_risks(profile, contract, plan)
    approved_plan = approve_mapping_plan(plan)

    # 5. Adapter Generation & Validation
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    assert validation.is_contract_valid is True
    assert validation.all_tests_passed is True
    assert validation.valid_records_count == 5
    assert validation.quarantined_records_count == 0
    assert validation.contract_pass_rate == 100.0

    # 6. Readiness Report
    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
        approved_plan=approved_plan,
        validation_result=validation,
    )
    assert report.readiness_state == ReadinessState.READY


def test_json_pipeline_corrupted_users_quarantine(fixtures_dir: Path):
    """Proves that corrupted JSON records (missing keys, bad regex, nulls) are safely quarantined."""
    json_path = fixtures_dir / "corrupted_users.json"
    contract_path = fixtures_dir / "target_contract_user_profile.json"

    dataset = load_dataset(json_path)
    contract = load_target_contract(contract_path)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    risks = evaluate_risks(profile, contract, plan)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    assert validation.total_input_records == 4
    # Record 1 (Alice) is valid
    assert validation.valid_records_count == 1
    # Record 2 (missing name), Record 3 (bad email regex), Record 4 (null city) quarantined
    assert validation.quarantined_records_count == 3
    # Absolute integrity: 1 valid + 3 quarantined == 4 total
    assert validation.valid_records_count + validation.quarantined_records_count == 4

    # Report state must reflect warnings/review
    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
        approved_plan=approved_plan,
        validation_result=validation,
    )
    assert report.readiness_state in (ReadinessState.NEEDS_REVIEW, ReadinessState.BLOCKED)
