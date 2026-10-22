"""Unit tests for reusable, versioned mapping specifications (Feature A)."""

import json
from pathlib import Path
import pytest

from recon.contracts.loader import load_target_contract
from recon.exceptions import MappingError
from recon.ingestion import load_csv
from recon.mapping import (
    MappingDecision,
    MappingPlan,
    MappingSpecification,
    MappingStatus,
    MappingType,
    approve_mapping_plan,
    export_mapping_spec,
    load_mapping_spec,
    propose_mappings,
    validate_and_apply_mapping_spec,
)
from recon.profiling import profile_dataset


@pytest.fixture
def sample_nyc311_context() -> tuple:
    """Fixture providing contract, profile, and base proposal plan for NYC 311 data."""
    contract_path = Path("tests/fixtures/target_contract_service_request.json")
    data_path = Path("tests/fixtures/synthetic_nyc_311.csv")

    contract = load_target_contract(contract_path)
    dataset = load_csv(data_path)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    return contract, profile, plan


def test_export_mapping_spec(sample_nyc311_context: tuple) -> None:
    """Verifies exporting mapping specification produces a valid v1.0 spec."""
    contract, profile, plan = sample_nyc311_context
    spec = export_mapping_spec(contract, profile, plan, reviewer="test_engineer")

    assert spec.schema_version == "1.0"
    assert spec.engine_version == "0.1.0"
    assert spec.contract_name == contract.contract_name
    assert spec.contract_fingerprint == contract.fingerprint
    assert spec.source_fingerprint == profile.fingerprint
    assert len(spec.mappings) == len(contract.fields)

    # Check serialization to valid JSON
    json_str = spec.to_json()
    parsed = json.loads(json_str)
    assert parsed["schema_version"] == "1.0"
    assert parsed["contract_name"] == "service_request_target_contract"
    assert "ticket_id" in [m["target_field"] for m in parsed["mappings"]]


def test_export_approved_mapping_spec(sample_nyc311_context: tuple) -> None:
    """Verifies exporting an ApprovedMappingPlan records honest approval provenance."""
    contract, profile, plan = sample_nyc311_context
    approved_plan = approve_mapping_plan(plan, reviewer="principal_lead")

    spec = export_mapping_spec(contract, profile, approved_plan)
    assert spec.mappings[0].approved is True
    assert spec.mappings[0].approver == "principal_lead"
    assert spec.mappings[0].approved_at is not None


def test_load_mapping_spec_roundtrip(sample_nyc311_context: tuple, tmp_path: Path) -> None:
    """Verifies round-trip saving and loading from file."""
    contract, profile, plan = sample_nyc311_context
    spec = export_mapping_spec(contract, profile, plan)

    out_file = tmp_path / "recon_mapping_spec.json"
    spec.save_to_file(out_file)

    loaded_spec = load_mapping_spec(out_file)
    assert loaded_spec.schema_version == spec.schema_version
    assert loaded_spec.contract_fingerprint == spec.contract_fingerprint
    assert len(loaded_spec.mappings) == len(spec.mappings)


def test_load_mapping_spec_unsupported_version() -> None:
    """Verifies that an unsupported schema version is rejected with a clear diagnostic."""
    bad_data = {
        "schema_version": "99.0",
        "contract_name": "test",
        "contract_fingerprint": "abc",
        "source_fingerprint": "def",
        "mappings": [],
    }
    with pytest.raises(MappingError) as exc_info:
        load_mapping_spec(bad_data)
    assert "Unsupported mapping specification schema version '99.0'" in str(exc_info.value)


def test_load_mapping_spec_duplicate_target_conflict() -> None:
    """Verifies that conflicting mappings for the same target field are rejected."""
    bad_data = {
        "schema_version": "1.0",
        "contract_name": "test",
        "contract_fingerprint": "abc",
        "source_fingerprint": "def",
        "mappings": [
            {"target_field": "order_id", "source_field": "col_a"},
            {"target_field": "order_id", "source_field": "col_b"},
        ],
    }
    with pytest.raises(MappingError) as exc_info:
        load_mapping_spec(bad_data)
    assert "Duplicate / conflicting mapping decision" in str(exc_info.value)


def test_validate_and_apply_spec_compatible(sample_nyc311_context: tuple) -> None:
    """Verifies compatible mapping reuse pre-fills decisions without bypassing human approval."""
    contract, profile, plan = sample_nyc311_context
    spec = export_mapping_spec(contract, profile, plan)

    updated_plan, result = validate_and_apply_mapping_spec(spec, contract, profile, plan)

    assert result.is_valid is True
    assert result.contract_match is True
    assert result.source_match is True
    assert result.reused_count > 0

    # CRITICAL CHECK: Mappings are PROPOSED, not pre-approved, protecting human approval boundary
    ticket_prop = updated_plan.get_proposal("ticket_id")
    assert ticket_prop is not None
    assert ticket_prop.status == MappingStatus.PROPOSED
    assert "Reused from mapping specification" in ticket_prop.evidence[0]


def test_validate_and_apply_spec_missing_source_column(sample_nyc311_context: tuple) -> None:
    """Verifies that if a source column from spec does not exist in new source, it is marked unresolved."""
    contract, profile, plan = sample_nyc311_context
    spec = export_mapping_spec(contract, profile, plan)

    # Corrupt a mapping decision to point to a nonexistent column
    for m in spec.mappings:
        if m.target_field == "ticket_id":
            m.source_field = "nonexistent_column_xyz"

    updated_plan, result = validate_and_apply_mapping_spec(spec, contract, profile, plan)

    ticket_prop = updated_plan.get_proposal("ticket_id")
    assert ticket_prop is not None
    assert ticket_prop.mapping_type == MappingType.MISSING_SOURCE
    assert ticket_prop.status == MappingStatus.UNRESOLVED
    assert any("does not exist in the current source dataset" in ev for ev in ticket_prop.evidence)
    assert any("nonexistent_column_xyz" in m for m in result.mismatches)


def test_validate_and_apply_spec_contract_fingerprint_mismatch(sample_nyc311_context: tuple) -> None:
    """Verifies contract fingerprint mismatch triggers revalidation requirement."""
    contract, profile, plan = sample_nyc311_context
    spec = export_mapping_spec(contract, profile, plan)

    # Change fingerprint in spec to simulate changed contract
    spec.contract_fingerprint = "0000000000000000000000000000000000000000000000000000000000000000"

    updated_plan, result = validate_and_apply_mapping_spec(spec, contract, profile, plan)

    assert result.contract_match is False
    assert any("Contract fingerprint mismatch" in m for m in result.mismatches)


def test_validate_and_apply_spec_rejects_unsafe_code(sample_nyc311_context: tuple) -> None:
    """Verifies arbitrary execution code in transformation rule is rejected."""
    contract, profile, plan = sample_nyc311_context
    spec = export_mapping_spec(contract, profile, plan)

    for m in spec.mappings:
        if m.target_field == "ticket_id":
            m.transformation_rule = "__import__('os').system('echo hacked')"

    updated_plan, result = validate_and_apply_mapping_spec(spec, contract, profile, plan)

    ticket_prop = updated_plan.get_proposal("ticket_id")
    assert ticket_prop is not None
    assert ticket_prop.mapping_type == MappingType.UNSUPPORTED
    assert ticket_prop.status == MappingStatus.UNRESOLVED
    assert any("Unsafe or forbidden transformation rule" in c for c in result.conflicts)
