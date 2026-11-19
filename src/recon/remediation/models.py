"""Data models for Recon's 1-Click Smart Remediation Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class RemediationCategory(str, Enum):
    """Categorization of detected data dirtyness / contract blockers."""
    CURRENCY_CLEANING = "currency_cleaning"
    PERCENTAGE_CONVERSION = "percentage_conversion"
    DATETIME_FORMATTING = "datetime_formatting"
    ENUM_NORMALIZATION = "enum_normalization"
    WHITESPACE_TRIM = "whitespace_trim"
    NUMERIC_CLEANING = "numeric_cleaning"
    UNMAPPED_FIELD = "unmapped_field"
    BOOLEAN_NORMALIZATION = "boolean_normalization"


class ValueDiff(BaseModel):
    """Concrete before/after evidence showing raw value transformed to cleaned value."""
    raw_sample: str
    remediated_sample: Any
    row_index: Optional[int] = None


class RemediationCandidate(BaseModel):
    """An explicit, reviewable remediation proposal targeting a specific blocker."""
    candidate_id: str
    field_name: str
    source_field: Optional[str] = None
    category: RemediationCategory
    title: str
    diagnosis: str
    suggested_action: str
    proposed_transformation_rule: str
    proposed_ast_code: str
    sample_diffs: List[ValueDiff] = Field(default_factory=list)
    affected_records_count: int = 0
    projected_yield_gain_percent: float = 0.0
    confidence_score: float = 1.0
    is_recommended: bool = True


class RemediationPlan(BaseModel):
    """Aggregated remediation forecast for an integration run."""
    session_id: str
    current_readiness_state: str
    current_pass_rate: float
    projected_pass_rate: float
    total_quarantined_records: int
    projected_rescued_records: int
    candidates: List[RemediationCandidate] = Field(default_factory=list)


class ApplyRemediationRequest(BaseModel):
    """Request payload to apply selected remediation rules and recompile."""
    session_id: str
    selected_candidate_ids: List[str] = Field(default_factory=list)
    reviewer: str = "web_user"


class RemediationReceipt(BaseModel):
    """Audit receipt confirming the applied rules and resulting yield leap."""
    session_id: str
    applied_at: str
    applied_by: str
    rules_applied: List[str]
    prior_pass_rate: float
    new_pass_rate: float
    rescued_records_count: int
    new_readiness_state: str
