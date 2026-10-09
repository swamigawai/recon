"""Unit tests for adapter generation, isolated execution, and contract validation."""

from pathlib import Path
import pytest

from recon.adapters.generator import generate_adapter
from recon.adapters.models import GeneratedAdapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import AdapterError
from recon.ingestion.csv_loader import load_csv
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingPlan
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.validation.executor import validate_adapter, validate_contract_payload
from recon.validation.models import ValidationResult


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def setup_nyc_311(fixtures_dir: Path):
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_path = fixtures_dir / "target_contract_service_request.json"

    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)
    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)

    return dataset, contract, approved_plan


def test_generate_adapter_success(setup_nyc_311):
    """Verifies that an approved mapping plan generates clean, reviewable Python adapter code."""
    dataset, contract, approved_plan = setup_nyc_311

    adapter = generate_adapter(approved_plan, contract)
    assert isinstance(adapter, GeneratedAdapter)
    assert adapter.contract_name == "service_request_target_contract"
    assert "def transform_record(record:" in adapter.python_code
    assert "def transform_dataset(records:" in adapter.python_code
    assert "ticket_id" in adapter.python_code
    assert "datetime.strptime" in adapter.python_code


def test_generate_adapter_incomplete_plan_fails(setup_nyc_311):
    """Verifies that attempting to generate an adapter from an incomplete plan raises AdapterError."""
    dataset, contract, approved_plan = setup_nyc_311

    # Remove an approved required mapping
    del approved_plan.approved_mappings["ticket_id"]

    with pytest.raises(AdapterError) as exc_info:
        generate_adapter(approved_plan, contract)
    assert "Cannot generate adapter: approved mapping plan is incomplete" in str(exc_info.value)
    assert "ticket_id" in exc_info.value.context["missing_required_fields"]


def test_adapter_validation_end_to_end(setup_nyc_311):
    """Verifies that the generated adapter executes in sandbox and passes contract validation."""
    dataset, contract, approved_plan = setup_nyc_311

    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    assert isinstance(validation, ValidationResult)
    assert validation.is_contract_valid is True
    assert validation.all_tests_passed is True
    assert validation.total_input_records == 10
    # Every row is accounted for (never dropped silently)
    assert validation.valid_records_count + validation.quarantined_records_count == 10

    # Synthetic test cases executed
    test_names = [tc.test_name for tc in validation.test_case_results]
    assert "test_valid_record_transformation" in test_names
    assert "test_missing_required_field_quarantine" in test_names
    assert "test_malformed_date_quarantine" in test_names


def test_validate_contract_payload_direct():
    """Verifies contract validator catches type, enum, and pattern violations."""
    contract_dict = {
        "contract_name": "strict_test",
        "fields": {
            "zip": {"name": "zip", "target_type": "string", "pattern": r"^\d{5}$"},
            "borough": {
                "name": "borough",
                "target_type": "string",
                "allowed_values": ["MANHATTAN", "BROOKLYN"],
            },
        },
    }
    contract = load_target_contract(contract_dict)

    # Valid payload
    assert len(validate_contract_payload({"zip": "10001", "borough": "MANHATTAN"}, contract)) == 0

    # Pattern violation
    errs = validate_contract_payload({"zip": "123", "borough": "MANHATTAN"}, contract)
    assert any("does not match pattern" in e for e in errs)

    # Enum violation
    errs = validate_contract_payload({"zip": "10001", "borough": "QUEENS"}, contract)
    assert any("not in allowed values" in e for e in errs)
