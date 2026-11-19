"""Execution engine for applying remediation rules, recompiling adapters, and verifying yield gain."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from recon.adapters.generator import generate_adapter
from recon.contracts.models import TargetContract
from recon.ingestion.models import RawDataset
from recon.logging import log_safe_event
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import ApprovedMappingPlan, MappingPlan, MappingStatus, MappingType
from recon.profiling.models import SourceProfile
from recon.remediation.detector import detect_remediations
from recon.remediation.models import RemediationCandidate, RemediationReceipt
from recon.reporting.generator import build_readiness_report, render_markdown_report
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter
from recon.validation.models import ValidationResult


def apply_remediations(
    session: dict[str, Any],
    selected_candidate_ids: List[str],
    reviewer: str = "web_user",
    store: Any = None,
) -> dict[str, Any]:
    """Applies selected remediation transformations, re-synthesizes the AST adapter, re-validates data, and commits audit trail."""
    
    dataset: RawDataset = session["dataset"]
    profile: SourceProfile = session["profile"]
    contract: TargetContract = session["contract"]
    plan: MappingPlan = session["plan"]
    prior_validation: Optional[ValidationResult] = session.get("validation")
    session_id: str = session.get("session_id", "default_session")

    # Detect all available remediation candidates
    detection_plan = detect_remediations(
        contract=contract,
        mapping_plan=plan,
        profile=profile,
        validation_result=prior_validation,
        session_id=session_id,
    )

    # Filter candidates to selected IDs, or default to all recommended candidates if none selected
    selected_set = set(selected_candidate_ids)
    applied_candidates: List[RemediationCandidate] = [
        c for c in detection_plan.candidates
        if not selected_set or c.candidate_id in selected_set
    ]

    applied_rule_titles: List[str] = []

    # Apply remediation mutations onto mapping proposals
    for cand in applied_candidates:
        prop = plan.get_proposal(cand.field_name)
        if not prop:
            continue

        # If candidate maps an unmapped field
        if cand.source_field and not prop.source_field:
            prop.source_field = cand.source_field
            prop.mapping_type = MappingType.DIRECT
            prop.status = MappingStatus.APPROVED

        # If candidate applies a transformation rule
        if cand.proposed_transformation_rule:
            prop.transformation_rule = cand.proposed_transformation_rule
            prop.mapping_type = MappingType.TRANSFORMATION_REQUIRED
            prop.evidence.append(
                f"Remediated via '{cand.title}' ({cand.proposed_transformation_rule}) by {reviewer}."
            )

        applied_rule_titles.append(cand.title)

    # 1. Approve mapping plan
    approved_plan: ApprovedMappingPlan = approve_mapping_plan(
        plan=plan,
        reviewer=reviewer,
        overrides={},
    )

    # 2. Re-synthesize adapter code
    adapter = generate_adapter(approved_plan, contract)

    # 3. Re-execute sandbox validation
    new_validation: ValidationResult = validate_adapter(adapter, contract, dataset.rows)

    # 4. Re-evaluate risks and build readiness report
    active_plan = MappingPlan(
        contract_name=approved_plan.contract_name,
        source_name=approved_plan.source_name,
        source_fingerprint=approved_plan.source_fingerprint,
        proposals=dict(approved_plan.approved_mappings),
    )
    active_risks = evaluate_risks(profile, contract, active_plan)

    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=active_plan,
        risk_assessment=active_risks,
        approved_plan=approved_plan,
        validation_result=new_validation,
    )
    report_md = render_markdown_report(report)
    report_json = report.model_dump(mode="json")

    # Calculate audit deltas
    prior_pass_rate = prior_validation.contract_pass_rate if prior_validation else 0.0
    prior_valid_cnt = prior_validation.valid_records_count if prior_validation else 0
    new_pass_rate = new_validation.contract_pass_rate
    new_valid_cnt = new_validation.valid_records_count
    rescued_count = max(0, new_valid_cnt - prior_valid_cnt)

    now_iso = datetime.now(timezone.utc).isoformat()
    receipt = RemediationReceipt(
        session_id=session_id,
        applied_at=now_iso,
        applied_by=reviewer,
        rules_applied=applied_rule_titles,
        prior_pass_rate=prior_pass_rate,
        new_pass_rate=new_pass_rate,
        rescued_records_count=rescued_count,
        new_readiness_state=report.readiness_state.value,
    )

    # Update in-memory session
    session["approved_plan"] = approved_plan
    session["adapter"] = adapter
    session["validation"] = new_validation
    session["report"] = report
    session["report_md"] = report_md
    session["report_json"] = report_json

    # Build standardized results response
    results_response = {
        "session_id": session_id,
        "readiness_state": report.readiness_state.value,
        "readiness_rationale": report.readiness_rationale,
        "blocking_reasons": report.blocking_reasons,
        "review_reasons": report.review_reasons,
        "adapter": {
            "adapter_name": adapter.adapter_name,
            "contract_name": adapter.contract_name,
            "contract_version": adapter.contract_version,
            "python_code": adapter.python_code,
        },
        "validation": {
            "total_input_records": new_validation.total_input_records,
            "valid_records_count": new_validation.valid_records_count,
            "quarantined_records_count": new_validation.quarantined_records_count,
            "contract_pass_rate": new_validation.contract_pass_rate,
            "is_contract_valid": new_validation.is_contract_valid,
            "all_tests_passed": new_validation.all_tests_passed,
            "test_case_results": [
                {
                    "test_name": tc.test_name,
                    "passed": tc.passed,
                    "expected_behavior": tc.expected_behavior,
                    "actual_behavior": tc.actual_behavior,
                    "error_message": tc.error_message,
                }
                for tc in new_validation.test_case_results
            ],
            "sample_valid_output": new_validation.sample_valid_output[:5],
            "sample_quarantined_records": [
                {
                    "row_index": qr.get("record_index", 0),
                    "record_index": qr.get("record_index", 0),
                    "failure_reasons": qr.get("errors", []),
                    "errors": qr.get("errors", []),
                    "raw_record": qr.get("raw_record", {}),
                }
                for qr in (new_validation.all_quarantined_records[:100] if getattr(new_validation, "all_quarantined_records", None) else new_validation.sample_quarantined_records)
            ],
            "quarantine_error_groups": [],
        },
        "report_markdown": report_md,
        "remediation_receipt": receipt.model_dump(mode="json"),
    }

    # Persist into SQLite WAL store if configured
    if store is not None:
        try:
            quar_recs = new_validation.all_quarantined_records if getattr(new_validation, "all_quarantined_records", None) else new_validation.sample_quarantined_records
            store.save_results(
                session_id=session_id,
                results_data=results_response,
                adapter_code=adapter.python_code,
                report_md=report_md,
                report_json=report_json,
                mapping_spec_json=session.get("mapping_spec_json", ""),
                quarantine_records=quar_recs,
            )
        except Exception as exc:
            log_safe_event("remediation_store_warning", {"error": str(exc), "session_id": session_id})

    session["results_response"] = results_response

    log_safe_event(
        "REMEDIATION_APPLIED",
        session_id=session_id,
        rules_applied=len(applied_rule_titles),
        prior_pass_rate=prior_pass_rate,
        new_pass_rate=new_pass_rate,
        rescued_records=rescued_count,
    )

    return {
        "results": results_response,
        "receipt": receipt.model_dump(mode="json"),
    }
