"""Recon 1-Click Smart Remediation Engine.

Transforms integration data blockers (dirty currencies, non-standard dates, enum casing, whitespace)
into verified, certified pass yield with AST code generation and deterministic mathematical proof.
"""

from recon.remediation.applier import apply_remediations
from recon.remediation.detector import detect_remediations
from recon.remediation.models import (
    ApplyRemediationRequest,
    RemediationCandidate,
    RemediationCategory,
    RemediationPlan,
    RemediationReceipt,
    ValueDiff,
)

__all__ = [
    "ApplyRemediationRequest",
    "RemediationCandidate",
    "RemediationCategory",
    "RemediationPlan",
    "RemediationReceipt",
    "ValueDiff",
    "apply_remediations",
    "detect_remediations",
]
