"""Data models for risk assessment findings and evaluation rules."""

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity classification determining integration readiness impact."""
    CRITICAL = "critical"  # Blocks readiness completely
    HIGH = "high"          # Likely runtime failure or data corruption; blocks readiness unless waived
    MEDIUM = "medium"      # Data quality degradation or precision loss
    LOW = "low"            # Informational / minor styling inconsistency


class RiskStatus(str, Enum):
    """Distinction between confirmed incompatibilities and potential risks."""
    CONFIRMED = "confirmed"
    POTENTIAL = "potential"


class RiskFinding(BaseModel):
    """An individual, explainable risk finding citing concrete evidence and remediation."""
    rule_id: str
    rule_name: str
    severity: Severity
    status: RiskStatus
    affected_fields: list[str]
    evidence: str
    explanation: str
    suggested_action: str


class RiskAssessment(BaseModel):
    """Collection of evaluated risk findings for a source dataset and target contract."""
    contract_name: str
    source_name: str
    source_fingerprint: str
    findings: list[RiskFinding] = Field(default_factory=list)
    checks_run: list[str] = Field(default_factory=list)
    checks_skipped: list[str] = Field(default_factory=list)

    @property
    def critical_findings(self) -> list[RiskFinding]:
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    @property
    def high_findings(self) -> list[RiskFinding]:
        return [f for f in self.findings if f.severity == Severity.HIGH]

    @property
    def medium_findings(self) -> list[RiskFinding]:
        return [f for f in self.findings if f.severity == Severity.MEDIUM]

    @property
    def low_findings(self) -> list[RiskFinding]:
        return [f for f in self.findings if f.severity == Severity.LOW]

    @property
    def is_blocked(self) -> bool:
        """Readiness is blocked if any CRITICAL risk finding exists."""
        return len(self.critical_findings) > 0
