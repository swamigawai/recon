"""Data models for source-to-target mapping proposals and approval plans."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from recon.contracts.models import ContractType
from recon.profiling.models import InferredType


class MappingType(str, Enum):
    """Categorization of proposed field mapping."""
    DIRECT = "direct"
    TRANSFORMATION_REQUIRED = "transformation_required"
    AMBIGUOUS = "ambiguous"
    MISSING_SOURCE = "missing_source"
    UNSUPPORTED = "unsupported"


class MappingStatus(str, Enum):
    """Lifecycle status of a mapping proposal."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class FieldMappingProposal(BaseModel):
    """Evidence-backed mapping proposal for an individual target field."""
    target_field: str
    target_type: ContractType
    target_required: bool
    target_nullable: bool
    source_field: str | None = None
    source_inferred_type: InferredType | None = None
    mapping_type: MappingType
    status: MappingStatus = MappingStatus.PROPOSED
    transformation_rule: str | None = None
    evidence: list[str] = Field(default_factory=list)
    alternative_candidates: list[str] = Field(default_factory=list)
    human_notes: str | None = None


class MappingPlan(BaseModel):
    """Complete collection of mapping proposals comparing SourceProfile to TargetContract."""
    contract_name: str
    source_name: str
    source_fingerprint: str
    proposals: dict[str, FieldMappingProposal]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_proposal(self, target_field: str) -> FieldMappingProposal | None:
        """Retrieves proposal for a target field."""
        return self.proposals.get(target_field)

    def unresolved_proposals(self) -> list[FieldMappingProposal]:
        """Returns all proposals requiring human attention."""
        return [
            p for p in self.proposals.values()
            if p.mapping_type in (MappingType.AMBIGUOUS, MappingType.MISSING_SOURCE, MappingType.UNSUPPORTED)
            or p.status == MappingStatus.UNRESOLVED
        ]


class ApprovedMappingPlan(BaseModel):
    """An immutable, human-reviewed and approved mapping plan ready for adapter generation."""
    contract_name: str
    source_name: str
    source_fingerprint: str
    approved_mappings: dict[str, FieldMappingProposal]
    approved_by: str
    approved_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_complete(self) -> bool:
        """Returns True if every required target field has an approved source mapping."""
        return all(
            p.status == MappingStatus.APPROVED and p.source_field is not None
            for p in self.approved_mappings.values()
            if p.target_required
        )
