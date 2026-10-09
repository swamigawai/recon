"""Readiness report generation and formatting engine producing JSON and Markdown reports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import recon
from recon.contracts.models import TargetContract
from recon.logging import log_safe_event
from recon.mapping.models import ApprovedMappingPlan, MappingPlan, MappingStatus, MappingType
from recon.profiling.models import SourceProfile
from recon.reporting.models import ReadinessReport, ReadinessState
from recon.risks.models import RiskAssessment
from recon.validation.models import ValidationResult


def build_readiness_report(
    profile: SourceProfile,
    contract: TargetContract,
    mapping_plan: MappingPlan,
    risk_assessment: RiskAssessment,
    approved_plan: ApprovedMappingPlan | None = None,
    validation_result: ValidationResult | None = None,
) -> ReadinessReport:
    """Builds a complete, reproducible integration readiness report."""
    blocking_reasons: list[str] = []
    review_reasons: list[str] = []
    unresolved_questions: list[str] = []

    # 1. Evaluate Critical Risk Blockers
    for crit in risk_assessment.critical_findings:
        blocking_reasons.append(f"[{crit.rule_id}] {crit.rule_name} on {crit.affected_fields}: {crit.evidence}")

    # 2. Evaluate Unresolved Mappings
    unresolved_props = mapping_plan.unresolved_proposals()
    for p in unresolved_props:
        msg = f"Target field '{p.target_field}' has status '{p.mapping_type.value}'"
        if p.target_required:
            blocking_reasons.append(f"Missing required target mapping: {msg}")
        else:
            review_reasons.append(f"Unresolved optional target mapping: {msg}")
        unresolved_questions.append(
            f"How should '{p.target_field}' ({'required' if p.target_required else 'optional'}) be populated from source?"
        )

    # 3. Evaluate High Severity Risks
    for high in risk_assessment.high_findings:
        review_reasons.append(f"[{high.rule_id}] {high.rule_name} on {high.affected_fields}: {high.evidence}")
        unresolved_questions.append(
            f"Review risk on {high.affected_fields}: {high.suggested_action}"
        )

    # 4. Evaluate Adapter Validation (if generated and tested)
    if validation_result:
        if not validation_result.is_ready:
            blocking_reasons.append(
                f"Adapter validation failed: contract valid={validation_result.is_contract_valid}, tests passed={validation_result.all_tests_passed}"
            )
    elif approved_plan and approved_plan.is_complete:
        review_reasons.append("Adapter has not yet been generated and validated against test fixtures.")

    # 5. Determine Overall State
    if blocking_reasons:
        state = ReadinessState.BLOCKED
        rationale = f"Integration is BLOCKED by {len(blocking_reasons)} critical issue(s)."
    elif review_reasons:
        state = ReadinessState.NEEDS_REVIEW
        rationale = f"Integration requires human review for {len(review_reasons)} warning(s) or ambiguous decision(s)."
    else:
        state = ReadinessState.READY
        rationale = "Integration is READY: all required fields approved, no blockers, and tests pass."

    # Verified Facts Summary
    verified_facts = {
        "total_source_rows": profile.total_rows,
        "total_source_columns": profile.total_columns,
        "duplicate_source_rows": profile.duplicate_rows_count,
        "columns_summary": {
            col_name: {
                "inferred_type": col.inferred_type.value,
                "null_count": col.null_count,
                "null_percentage": col.null_percentage,
                "distinct_count": col.distinct_count,
                "is_constant": col.is_constant,
                "has_whitespace": col.has_whitespace_anomalies,
            }
            for col_name, col in profile.columns.items()
        },
    }

    inferred_types = {k: v.inferred_type.value for k, v in profile.columns.items()}

    mapping_summary = {
        "total_target_fields": len(contract.fields),
        "total_proposals": len(mapping_plan.proposals),
        "approved_mappings_count": len(approved_plan.approved_mappings) if approved_plan else 0,
        "unresolved_count": len(unresolved_props),
    }

    risk_summary = {
        "critical": len(risk_assessment.critical_findings),
        "high": len(risk_assessment.high_findings),
        "medium": len(risk_assessment.medium_findings),
        "low": len(risk_assessment.low_findings),
    }

    report = ReadinessReport(
        recon_version=recon.__version__,
        generated_at=datetime.utcnow(),
        source_file=profile.source_name,
        source_fingerprint=profile.fingerprint,
        contract_name=contract.contract_name,
        contract_version=contract.version,
        readiness_state=state,
        readiness_rationale=rationale,
        blocking_reasons=blocking_reasons,
        review_reasons=review_reasons,
        verified_facts=verified_facts,
        inferred_types=inferred_types,
        mapping_summary=mapping_summary,
        risk_summary=risk_summary,
        risk_findings=risk_assessment.findings,
        unresolved_questions=unresolved_questions,
        adapter_validation=validation_result,
        checks_run=risk_assessment.checks_run,
        checks_skipped=risk_assessment.checks_skipped,
    )

    log_safe_event(
        "REPORT_GENERATED",
        source=profile.source_name,
        contract=contract.contract_name,
        state=state.value,
        blockers=len(blocking_reasons),
    )

    return report


def render_markdown_report(report: ReadinessReport) -> str:
    """Renders the ReadinessReport into a clean, human-readable GitHub Flavored Markdown document."""
    state_badge = {
        ReadinessState.READY: "READY",
        ReadinessState.NEEDS_REVIEW: "NEEDS HUMAN REVIEW",
        ReadinessState.BLOCKED: "BLOCKED",
    }.get(report.readiness_state, report.readiness_state.value)

    lines = [
        f"# Recon Integration Readiness Report",
        f"",
        f"**Source Dataset:** `{report.source_file}`  ",
        f"**Target Contract:** `{report.contract_name}` (v{report.contract_version})  ",
        f"**Fingerprint:** `{report.source_fingerprint[:16]}...`  ",
        f"**Recon Engine Version:** `v{report.recon_version}`  ",
        f"**Generated:** `{report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
        f"",
        f"## Readiness Status: **{state_badge}**",
        f"",
        f"> {report.readiness_rationale}",
        f"",
    ]

    # Blocking Reasons
    if report.blocking_reasons:
        lines.append("### Critical Blocking Issues")
        for b in report.blocking_reasons:
            lines.append(f"- **[BLOCKER]** {b}")
        lines.append("")

    # Review Reasons
    if report.review_reasons:
        lines.append("### Warnings & Review Items")
        for r in report.review_reasons:
            lines.append(f"- **[REVIEW]** {r}")
        lines.append("")

    # Risk Summary Table
    lines.extend([
        "## Risk Assessment Summary",
        "",
        "| Severity | Findings Count | Impact |",
        "| :--- | :---: | :--- |",
        f"| **Critical** | {report.risk_summary.get('critical', 0)} | Blocks deployment |",
        f"| **High** | {report.risk_summary.get('high', 0)} | Probable runtime error / data loss |",
        f"| **Medium** | {report.risk_summary.get('medium', 0)} | Data quality degradation / format variance |",
        f"| **Low** | {report.risk_summary.get('low', 0)} | Informational observation |",
        "",
    ])

    # Detailed Risk Findings
    if report.risk_findings:
        lines.append("### Detailed Risk Findings")
        for f in report.risk_findings:
            lines.extend([
                f"- **`{f.rule_id}`** ({f.severity.upper()}): {f.rule_name}",
                f"  - **Affected Fields:** {', '.join(f.affected_fields)}",
                f"  - **Evidence:** {f.evidence}",
                f"  - **Action:** {f.suggested_action}",
            ])
        lines.append("")

    # Verified Facts Table
    lines.extend([
        "## Verified Profiling Facts",
        "",
        f"- **Total Rows:** {report.verified_facts.get('total_source_rows', 0):,}",
        f"- **Total Columns:** {report.verified_facts.get('total_source_columns', 0)}",
        f"- **Duplicate Rows:** {report.verified_facts.get('duplicate_source_rows', 0)}",
        "",
        "| Column Name | Inferred Type | Null Count | Null % | Distinct Count | Anomalies |",
        "| :--- | :--- | :---: | :---: | :---: | :--- |",
    ])

    cols_summary = report.verified_facts.get("columns_summary", {})
    for col_name, stats in cols_summary.items():
        anomalies = []
        if stats.get("is_constant"):
            anomalies.append("Constant")
        if stats.get("has_whitespace"):
            anomalies.append("Whitespace")
        anom_str = ", ".join(anomalies) if anomalies else "None"

        lines.append(
            f"| `{col_name}` | `{stats.get('inferred_type')}` | {stats.get('null_count')} | {stats.get('null_percentage')}% | {stats.get('distinct_count')} | {anom_str} |"
        )
    lines.append("")

    # Adapter Validation Results
    if report.adapter_validation:
        v = report.adapter_validation
        lines.extend([
            "## Adapter Validation & Test Outcomes",
            "",
            f"- **Adapter:** `{v.adapter_name}`",
            f"- **Input Records Tested:** {v.total_input_records}",
            f"- **Valid Outputs:** {v.valid_records_count}",
            f"- **Quarantined Records:** {v.quarantined_records_count}",
            f"- **Contract Pass Rate:** `{v.contract_pass_rate}%`",
            f"- **Target Contract Valid:** `{'PASS' if v.is_contract_valid else 'FAIL'}`",
            f"- **Synthetic Fault Tests:** `{'ALL PASSED' if v.all_tests_passed else 'FAIL'}`",
            "",
            "### Synthetic Test Suite Details",
            "",
            "| Test Case | Status | Expected Behavior | Actual Behavior |",
            "| :--- | :---: | :--- | :--- |",
        ])
        for tc in v.test_case_results:
            status_icon = "PASS" if tc.passed else "FAIL"
            lines.append(f"| `{tc.test_name}` | **{status_icon}** | {tc.expected_behavior} | {tc.actual_behavior} |")
        lines.append("")

    # Unresolved Questions
    if report.unresolved_questions:
        lines.append("## Decisions Required from Human Reviewer")
        for q in report.unresolved_questions:
            lines.append(f"- [ ] {q}")
        lines.append("")

    return "\n".join(lines)


def export_reports(report: ReadinessReport, output_dir: Path | str) -> tuple[Path, Path]:
    """Exports both machine-readable JSON and human-readable Markdown reports."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_path = out_path / "readiness_report.json"
    md_path = out_path / "readiness_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown_report(report))

    return json_path, md_path
