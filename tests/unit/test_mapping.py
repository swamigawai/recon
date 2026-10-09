"""Unit tests for evidence-backed mapping proposals and approval plans."""

from pathlib import Path
import pytest

from recon.contracts.loader import load_target_contract
from recon.exceptions import MappingError
from recon.ingestion.csv_loader import load_csv
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import (
    ApprovedMappingPlan,
    FieldMappingProposal,
    MappingPlan,
    MappingStatus,
    MappingType,
)
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mapping_plan(fixtures_dir: Path) -> MappingPlan:
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_path = fixtures_dir / "target_contract_service_request.json"

    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)

    return propose_mappings(profile, contract)


def test_proposals_nyc_311_ground_truth(mapping_plan: MappingPlan):
    """Verifies that all 11 target fields receive evidence-backed proposals matching ground truth."""
    proposals = mapping_plan.proposals
    assert len(proposals) == 11

    # 1. ticket_id <- Unique Key (int to string transformation)
    p_ticket = proposals["ticket_id"]
    assert p_ticket.source_field == "Unique Key"
    assert p_ticket.mapping_type == MappingType.TRANSFORMATION_REQUIRED
    assert p_ticket.transformation_rule == "to_string"
    assert any("requires cast to target type 'string'" in e for e in p_ticket.evidence)

    # 2. created_at <- Created Date (datetime format conversion)
    p_created = proposals["created_at"]
    assert p_created.source_field == "Created Date"
    assert p_created.mapping_type == MappingType.TRANSFORMATION_REQUIRED
    assert "parse_datetime" in (p_created.transformation_rule or "")
    assert any("requires parsing to target ISO-8601" in e for e in p_created.evidence)

    # 3. agency_code <- Agency (abbreviation with alternatives)
    p_agency = proposals["agency_code"]
    assert p_agency.source_field == "Agency"
    assert "Agency Name" in p_agency.alternative_candidates

    # 4. category <- Complaint Type
    p_cat = proposals["category"]
    assert p_cat.source_field == "Complaint Type"

    # 5. description <- Descriptor
    p_desc = proposals["description"]
    assert p_desc.source_field == "Descriptor"

    # 6. status <- Status (casing normalization for enum)
    p_status = proposals["status"]
    assert p_status.source_field == "Status"
    assert p_status.mapping_type == MappingType.TRANSFORMATION_REQUIRED
    assert p_status.transformation_rule == "uppercase_strip"

    # 7. latitude & longitude (direct float mapping)
    p_lat = proposals["latitude"]
    assert p_lat.source_field == "Latitude"
    assert p_lat.mapping_type == MappingType.DIRECT

    p_lon = proposals["longitude"]
    assert p_lon.source_field == "Longitude"
    assert p_lon.mapping_type == MappingType.DIRECT


def test_missing_source_field_marked_unresolved(fixtures_dir: Path):
    """Verifies that unmapped target fields are flagged as MISSING_SOURCE and UNRESOLVED."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_dict = {
        "contract_name": "contract_with_extra_field",
        "fields": {
            "ticket_id": {"name": "ticket_id", "target_type": "string", "required": True},
            "unheard_of_target_field": {
                "name": "unheard_of_target_field",
                "target_type": "string",
                "required": True,
            },
        },
    }
    contract = load_target_contract(contract_dict)
    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)

    plan = propose_mappings(profile, contract)
    p_missing = plan.proposals["unheard_of_target_field"]

    assert p_missing.mapping_type == MappingType.MISSING_SOURCE
    assert p_missing.status == MappingStatus.UNRESOLVED
    assert p_missing.source_field is None
    assert any("No candidate column found" in e for e in p_missing.evidence)
    assert len(plan.unresolved_proposals()) == 1


def test_approve_mapping_plan_success(mapping_plan: MappingPlan):
    """Verifies human approval turns proposed plan into an ApprovedMappingPlan."""
    approved_plan = approve_mapping_plan(mapping_plan, reviewer="test_reviewer")

    assert isinstance(approved_plan, ApprovedMappingPlan)
    assert approved_plan.approved_by == "test_reviewer"
    assert approved_plan.is_complete is True

    # Check that required fields are marked APPROVED
    assert approved_plan.approved_mappings["ticket_id"].status == MappingStatus.APPROVED


def test_approve_plan_rejects_missing_required_field():
    """Verifies that an unmapped required field cannot be approved without a mapping."""
    fake_plan = MappingPlan(
        contract_name="test_contract",
        source_name="test.csv",
        source_fingerprint="abc",
        proposals={
            "required_field": FieldMappingProposal(
                target_field="required_field",
                target_type="string",  # type: ignore
                target_required=True,
                target_nullable=False,
                source_field=None,
                mapping_type=MappingType.MISSING_SOURCE,
                status=MappingStatus.UNRESOLVED,
            )
        },
    )

    # Attempting to override to APPROVED without providing source_field must fail
    with pytest.raises(MappingError) as exc_info:
        approve_mapping_plan(
            fake_plan,
            overrides={"required_field": {"status": MappingStatus.APPROVED, "source_field": None}},
        )
    assert "Cannot approve required target field" in str(exc_info.value)
