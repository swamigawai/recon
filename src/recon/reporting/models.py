"""Data models for comprehensive integration readiness reporting."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from recon.risks.models import RiskFinding
from recon.validation.models import ValidationResult


class ReadinessState(str, Enum):
    """Categorical readiness status for downstream integration deployment."""
    READY = "READY"                    # All required fields approved, no blockers, tests pass
    NEEDS_REVIEW = "NEEDS_REVIEW"      # Ambiguities, unwaived high risks, or pending decisions
    BLOCKED = "BLOCKED"                # Critical contract violation, missing required fields, test failure


class ReadinessReport(BaseModel):
    """Complete, reproducible integration readiness report."""
    recon_version: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    source_file: str
    source_fingerprint: str
    contract_name: str
    contract_version: str
    readiness_state: ReadinessState
    readiness_rationale: str
    blocking_reasons: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    verified_facts: dict[str, Any] = Field(default_factory=dict)
    inferred_types: dict[str, str] = Field(default_factory=dict)
    mapping_summary: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, int] = Field(default_factory=dict)
    risk_findings: list[RiskFinding] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    adapter_validation: ValidationResult | None = None
    checks_run: list[str] = Field(default_factory=list)
    checks_skipped: list[str] = Field(default_factory=list)
