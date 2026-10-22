"""Mapping proposal and approval engine for Recon."""

from recon.mapping.models import (
    ApprovedMappingPlan,
    FieldMappingProposal,
    MappingPlan,
    MappingStatus,
    MappingType,
)
from recon.mapping.proposer import propose_mappings, find_matching_source_columns, normalize_name
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.specification import (
    MappingDecision,
    MappingSpecification,
    SpecificationValidationResult,
    export_mapping_spec,
    load_mapping_spec,
    validate_and_apply_mapping_spec,
)

__all__ = [
    "ApprovedMappingPlan",
    "FieldMappingProposal",
    "MappingPlan",
    "MappingStatus",
    "MappingType",
    "propose_mappings",
    "find_matching_source_columns",
    "normalize_name",
    "approve_mapping_plan",
    "MappingDecision",
    "MappingSpecification",
    "SpecificationValidationResult",
    "export_mapping_spec",
    "load_mapping_spec",
    "validate_and_apply_mapping_spec",
]
