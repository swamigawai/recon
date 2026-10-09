"""Consistent error types and actionable failure messages for Recon."""

from typing import Any


class ReconError(Exception):
    """Base exception for all Recon errors with actionable guidance."""

    def __init__(
        self,
        message: str,
        *,
        actionable_suggestion: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.actionable_suggestion = actionable_suggestion
        self.context = context or {}

    def __str__(self) -> str:
        lines = [self.message]
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            lines.append(f"  Context: {ctx_str}")
        if self.actionable_suggestion:
            lines.append(f"  Action: {self.actionable_suggestion}")
        return "\n".join(lines)


class IngestionError(ReconError):
    """Raised when source dataset cannot be safely loaded or validated."""


class ProfilingError(ReconError):
    """Raised when deterministic profiling encounters an unrecoverable issue."""


class ContractError(ReconError):
    """Raised when target schema contract is invalid, malformed, or missing required attributes."""


class MappingError(ReconError):
    """Raised when mapping rules or human approval plans are inconsistent or invalid."""


class RiskAssessmentError(ReconError):
    """Raised when risk rule execution encounters an internal error."""


class AdapterError(ReconError):
    """Raised when adapter code generation fails."""


class ValidationError(ReconError):
    """Raised when target contract validation or test execution fails."""
