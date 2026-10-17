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


def test_quarantine_records_contain_structured_metadata(fixtures_dir: Path):
    """Verifies that quarantined records include row index, raw payload, violated field, failure reason, and error codes."""
    from recon.adapters.generator import generate_adapter
    from recon.contracts.loader import load_target_contract
    from recon.ingestion.csv_loader import load_csv
    from recon.mapping.approval import approve_mapping_plan
    from recon.mapping.proposer import propose_mappings
    from recon.profiling.profiler import profile_dataset
    from recon.validation.executor import compile_adapter_sandbox

    csv_path = fixtures_dir / "corrupted_nyc_311.csv"
    contract_path = fixtures_dir / "target_contract_service_request.json"

    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)
    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)

    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid, quarantined = sandbox["transform_dataset"](dataset.rows)

    assert len(quarantined) > 0
    for q in quarantined:
        assert "record_index" in q
        assert isinstance(q["record_index"], int)
        assert "raw_record" in q
        assert isinstance(q["raw_record"], dict)
        assert "errors" in q
        assert isinstance(q["errors"], list)
        assert "violated_fields" in q
        assert isinstance(q["violated_fields"], list)
        assert "failure_reason" in q
        assert isinstance(q["failure_reason"], str)
        assert "error_codes" in q
        assert isinstance(q["error_codes"], list)


def test_sandbox_security_blocks_dangerous_operations():
    """Verifies that the adapter sandbox execution namespace strictly prevents filesystem and unauthorized module imports."""
    from recon.validation.executor import compile_adapter_sandbox

    # Test 1: Filesystem access via open() is blocked
    code_with_open = """
def transform_record(record):
    open('malicious.txt', 'w').write('hacked')
    return {}, []

def transform_dataset(records):
    return [transform_record(r) for r in records], []
"""
    sandbox = compile_adapter_sandbox(code_with_open)
    with pytest.raises(NameError) as exc_info:
        sandbox["transform_record"]({})
    assert "name 'open' is not defined" in str(exc_info.value)

    # Test 2: Unauthorized module import (e.g. os, sys, subprocess) is blocked
    code_with_os = """
import os
def transform_record(record):
    return {}, []
"""
    with pytest.raises(ImportError) as exc_info:
        compile_adapter_sandbox(code_with_os)
    assert "disallowed in adapter sandbox" in str(exc_info.value)

    # Test 3: Subprocess import is blocked
    code_with_subproc = """
import subprocess
"""
    with pytest.raises(ImportError) as exc_info:
        compile_adapter_sandbox(code_with_subproc)
    assert "disallowed in adapter sandbox" in str(exc_info.value)


def test_adapter_edge_cases_unicode_mixed_nulls_and_extra_fields():
    """Verifies adapter handles unicode, various null token representations, and ignores extra source columns."""
    from recon.adapters.generator import generate_adapter
    from recon.contracts.loader import load_target_contract
    from recon.mapping.models import ApprovedMappingPlan, FieldMappingProposal, MappingStatus, MappingType
    from recon.validation.executor import compile_adapter_sandbox

    contract = load_target_contract({
        "contract_name": "edge_case_contract",
        "fields": {
            "name": {"name": "name", "target_type": "string", "required": True},
            "notes": {"name": "notes", "target_type": "string", "required": False, "nullable": True},
            "count": {"name": "count", "target_type": "integer", "required": True},
        },
    })

    plan = ApprovedMappingPlan(
        contract_name="edge_case_contract",
        source_name="edge_test.csv",
        source_fingerprint="fp123",
        approved_by="tester",
        approved_mappings={
            "name": FieldMappingProposal(
                target_field="name",
                target_type="string",
                target_required=True,
                target_nullable=False,
                source_field="raw_name",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
            "notes": FieldMappingProposal(
                target_field="notes",
                target_type="string",
                target_required=False,
                target_nullable=True,
                source_field="raw_notes",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
            "count": FieldMappingProposal(
                target_field="count",
                target_type="integer",
                target_required=True,
                target_nullable=False,
                source_field="raw_count",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
        },
    )

    adapter = generate_adapter(plan, contract)
    sandbox = compile_adapter_sandbox(adapter.python_code)
    transform_dataset = sandbox["transform_dataset"]

    records = [
        # Unicode record with non-ASCII characters & extra unmapped field
        {"raw_name": "Café München 北京 🚀", "raw_notes": "São Paulo", "raw_count": "100", "extra_field": "IGNORED"},
        # Mixed null representations in optional nullable field
        {"raw_name": "Alice", "raw_notes": "NULL", "raw_count": "200"},
        {"raw_name": "Bob", "raw_notes": "n/a", "raw_count": "300"},
        {"raw_name": "Charlie", "raw_notes": "none", "raw_count": "400"},
        # Valid null in nullable field
        {"raw_name": "Dave", "raw_notes": "", "raw_count": "500"},
    ]

    valid, quarantined = transform_dataset(records)
    assert len(quarantined) == 0, f"Expected 0 quarantined, got {quarantined}"
    assert len(valid) == 5

    # Check unicode preserved
    assert valid[0]["name"] == "Café München 北京 🚀"
    assert "extra_field" not in valid[0]

    # Check null tokens correctly normalized to None in nullable field
    assert valid[1]["notes"] is None
    assert valid[2]["notes"] is None
    assert valid[3]["notes"] is None
    assert valid[4]["notes"] is None

