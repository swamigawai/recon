"""Deterministic risk evaluation engine executing explicit integration risk rules."""

from recon.contracts.models import ContractType, TargetContract
from recon.logging import log_safe_event
from recon.mapping.models import MappingPlan, MappingType
from recon.profiling.models import InferredType, SourceProfile
from recon.risks.models import RiskAssessment, RiskFinding, RiskStatus, Severity


def evaluate_risks(
    profile: SourceProfile,
    contract: TargetContract,
    mapping_plan: MappingPlan,
) -> RiskAssessment:
    """Evaluates deterministic risk rules across the source profile, contract, and mapping plan.

    Rules evaluated:
    - R001: Missing required target fields.
    - R002: Incompatible data types between source and target.
    - R003: Nullability conflicts (nulls in non-nullable target fields).
    - R004: Date/timestamp parsing and formatting risks.
    - R005: Target enum / allowed value domain violations.
    - R006: Whitespace inconsistencies.
    - R007: Constant source columns.
    """
    findings: list[RiskFinding] = []
    checks_run = [
        "R001_MISSING_REQUIRED_FIELD",
        "R002_INCOMPATIBLE_TYPES",
        "R003_NULLABILITY_CONFLICT",
        "R004_DATE_PARSING_RISK",
        "R005_ENUM_VIOLATION",
        "R006_WHITESPACE_INCONSISTENCY",
        "R007_CONSTANT_SOURCE_COLUMN",
    ]
    checks_skipped: list[str] = []

    for target_name, target_field in contract.fields.items():
        proposal = mapping_plan.get_proposal(target_name)

        # -------------------------------------------------------------
        # Rule R001: Missing Required Field
        # -------------------------------------------------------------
        if not proposal or not proposal.source_field:
            if target_field.required:
                findings.append(
                    RiskFinding(
                        rule_id="R001_MISSING_REQUIRED_FIELD",
                        rule_name="Missing Required Target Field",
                        severity=Severity.CRITICAL,
                        status=RiskStatus.CONFIRMED,
                        affected_fields=[target_name],
                        evidence=f"Target field '{target_name}' is declared required=True, but no source column is mapped.",
                        explanation=f"Downstream systems expecting '{target_name}' will reject payloads or fail validation.",
                        suggested_action=f"Map a valid source column to '{target_name}' or specify a default fallback transformation.",
                    )
                )
            continue

        src_col = profile.get_column(proposal.source_field)
        if not src_col:
            continue

        # -------------------------------------------------------------
        # Rule R002: Incompatible Types
        # -------------------------------------------------------------
        # Example: Target expects integer or float, but source is string and cannot be parsed
        if target_field.target_type in (ContractType.INTEGER, ContractType.FLOAT):
            if src_col.inferred_type == InferredType.STRING:
                findings.append(
                    RiskFinding(
                        rule_id="R002_INCOMPATIBLE_TYPES",
                        rule_name="Incompatible Source and Target Types",
                        severity=Severity.CRITICAL,
                        status=RiskStatus.CONFIRMED,
                        affected_fields=[target_name, src_col.name],
                        evidence=f"Target field '{target_name}' expects {target_field.target_type.value}, but source column '{src_col.name}' is non-numeric string.",
                        explanation="Casting non-numeric strings to numeric types will raise runtime conversion exceptions.",
                        suggested_action="Provide a parsing/cleaning regex transformation or verify field mapping.",
                    )
                )

        # -------------------------------------------------------------
        # Rule R003: Nullability Conflict
        # -------------------------------------------------------------
        if not target_field.nullable and src_col.null_count > 0:
            severity = Severity.CRITICAL if target_field.required else Severity.HIGH
            findings.append(
                RiskFinding(
                    rule_id="R003_NULLABILITY_CONFLICT",
                    rule_name="Nullability Constraint Violation",
                    severity=severity,
                    status=RiskStatus.CONFIRMED,
                    affected_fields=[target_name, src_col.name],
                    evidence=f"Target field '{target_name}' is non-nullable (nullable=False), but source column '{src_col.name}' has {src_col.null_count} nulls ({src_col.null_percentage}%).",
                    explanation=f"Passing nulls into a non-nullable target field violates contract integrity.",
                    suggested_action="Define a default value, drop/quarantine rows with nulls, or mark target field as nullable in contract.",
                )
            )

        # -------------------------------------------------------------
        # Rule R004: Date Parsing Risk
        # -------------------------------------------------------------
        if target_field.target_type == ContractType.DATETIME:
            if src_col.format_patterns:
                primary_fmt = src_col.format_patterns[0]
                if primary_fmt != "%Y-%m-%dT%H:%M:%SZ":
                    findings.append(
                        RiskFinding(
                            rule_id="R004_DATE_PARSING_RISK",
                            rule_name="Non-Standard Datetime Format",
                            severity=Severity.HIGH,
                            status=RiskStatus.POTENTIAL,
                            affected_fields=[target_name, src_col.name],
                            evidence=f"Source timestamp '{src_col.name}' uses format '{primary_fmt}', while target requires ISO-8601.",
                            explanation="Date parsing must account for regional format semantics (e.g., US month-first vs ISO year-first).",
                            suggested_action=f"Generate explicit datetime transformation parsing '{primary_fmt}' to ISO-8601.",
                        )
                    )

        # -------------------------------------------------------------
        # Rule R005: Enum / Category Violations
        # -------------------------------------------------------------
        if target_field.allowed_values:
            allowed_upper = {val.upper() for val in target_field.allowed_values}
            # Check source sample values
            unrecognized_samples = [
                s for s in src_col.sample_values
                if s.strip().upper() not in allowed_upper
            ]
            if unrecognized_samples:
                findings.append(
                    RiskFinding(
                        rule_id="R005_ENUM_VIOLATION",
                        rule_name="Allowed Value Domain Violation",
                        severity=Severity.HIGH,
                        status=RiskStatus.CONFIRMED,
                        affected_fields=[target_name, src_col.name],
                        evidence=f"Source column '{src_col.name}' contains values {unrecognized_samples} outside target allowed domain {target_field.allowed_values}.",
                        explanation="Records with unexpected categorical values will fail target schema validation.",
                        suggested_action="Add category mapping dictionary or quarantine records with unmapped domain values.",
                    )
                )

        # -------------------------------------------------------------
        # Rule R006: Whitespace Inconsistency
        # -------------------------------------------------------------
        if src_col.has_whitespace_anomalies:
            findings.append(
                RiskFinding(
                    rule_id="R006_WHITESPACE_INCONSISTENCY",
                    rule_name="Leading or Trailing Whitespace Detected",
                    severity=Severity.MEDIUM,
                    status=RiskStatus.POTENTIAL,
                    affected_fields=[target_name, src_col.name],
                    evidence=f"Source column '{src_col.name}' contains values with leading or trailing whitespace.",
                    explanation="Unstripped whitespace can cause failed string equality checks and broken downstream lookups.",
                    suggested_action="Ensure adapter transformation applies strip() on all string values.",
                )
            )

        # -------------------------------------------------------------
        # Rule R007: Constant Column Warning
        # -------------------------------------------------------------
        if src_col.is_constant:
            findings.append(
                RiskFinding(
                    rule_id="R007_CONSTANT_SOURCE_COLUMN",
                    rule_name="Constant Source Column",
                    severity=Severity.LOW,
                    status=RiskStatus.POTENTIAL,
                    affected_fields=[target_name, src_col.name],
                    evidence=f"Source column '{src_col.name}' has constant value '{src_col.sample_values[0]}' across all {src_col.total_count} rows.",
                    explanation="Constant source columns may indicate dummy test data, mock inputs, or degenerate columns.",
                    suggested_action="Verify with data owners whether this column represents genuine production variation.",
                )
            )

    assessment = RiskAssessment(
        contract_name=contract.contract_name,
        source_name=profile.source_name,
        source_fingerprint=profile.fingerprint,
        findings=findings,
        checks_run=checks_run,
        checks_skipped=checks_skipped,
    )

    log_safe_event(
        "RISKS_EVALUATED",
        source=profile.source_name,
        contract=contract.contract_name,
        total_findings=len(findings),
        critical=len(assessment.critical_findings),
        high=len(assessment.high_findings),
        blocked=assessment.is_blocked,
    )

    return assessment
