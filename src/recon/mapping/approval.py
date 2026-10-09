"""Human approval boundary for mapping proposals."""

from datetime import datetime
from typing import Any

from recon.exceptions import MappingError
from recon.mapping.models import ApprovedMappingPlan, FieldMappingProposal, MappingPlan, MappingStatus, MappingType


def approve_mapping_plan(
    plan: MappingPlan,
    reviewer: str = "human_engineer",
    overrides: dict[str, dict[str, Any]] | None = None,
) -> ApprovedMappingPlan:
    """Transitions a proposed MappingPlan into an immutable ApprovedMappingPlan.

    Applies explicit human decisions, overrides, and verifies readiness constraints.

    Raises:
        MappingError: If a required target field is approved without a source mapping or fallback.
    """
    applied_overrides = overrides or {}
    approved_mappings: dict[str, FieldMappingProposal] = {}

    for target_name, proposal in plan.proposals.items():
        # Copy proposal
        prop_data = proposal.model_dump()

        if target_name in applied_overrides:
            override_data = applied_overrides[target_name]
            prop_data.update(override_data)
            prop_data["human_notes"] = f"Approved with overrides by {reviewer}"
            prop_data["status"] = MappingStatus.APPROVED
        else:
            # If mapping is direct or transformation required with known rule, default approve
            if proposal.mapping_type in (MappingType.DIRECT, MappingType.TRANSFORMATION_REQUIRED):
                prop_data["status"] = MappingStatus.APPROVED
            else:
                # Ambiguous or missing source fields cannot be silently auto-approved
                prop_data["status"] = MappingStatus.UNRESOLVED

        approved_prop = FieldMappingProposal.model_validate(prop_data)

        # Safety Check: Required target field cannot be marked APPROVED without a source field
        if approved_prop.target_required and approved_prop.status == MappingStatus.APPROVED:
            if not approved_prop.source_field:
                raise MappingError(
                    f"Cannot approve required target field '{target_name}' without a source column mapping.",
                    actionable_suggestion=f"Provide a source_field mapping or default fallback for '{target_name}'.",
                    context={"target_field": target_name},
                )

        approved_mappings[target_name] = approved_prop

    return ApprovedMappingPlan(
        contract_name=plan.contract_name,
        source_name=plan.source_name,
        source_fingerprint=plan.source_fingerprint,
        approved_mappings=approved_mappings,
        approved_by=reviewer,
        approved_at=datetime.utcnow(),
    )
