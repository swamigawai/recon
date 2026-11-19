"""Deterministic root-cause detector for Recon's 1-Click Smart Remediation Engine."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, List, Optional, Set, Tuple

from recon.contracts.models import ContractType, TargetContract
from recon.mapping.models import MappingPlan, MappingType
from recon.profiling.models import SourceProfile
from recon.remediation.models import (
    RemediationCandidate,
    RemediationCategory,
    RemediationPlan,
    ValueDiff,
)
from recon.validation.models import ValidationResult


COMMON_DATE_FORMATS = [
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%b %d, %Y",
    "%d-%b-%Y",
]


def _try_parse_datetime(raw: str) -> Optional[Tuple[str, str]]:
    """Attempts parsing raw datetime string against common enterprise formats.
    
    Returns (detected_format, iso8601_output) or None.
    """
    clean = raw.strip()
    for fmt in COMMON_DATE_FORMATS:
        try:
            dt = datetime.strptime(clean, fmt)
            return fmt, dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            continue
    return None


def detect_remediations(
    contract: TargetContract,
    mapping_plan: MappingPlan,
    profile: Optional[SourceProfile] = None,
    validation_result: Optional[ValidationResult] = None,
    session_id: str = "default_session",
) -> RemediationPlan:
    """Analyzes validation failures and mapping gaps to formulate concrete, reviewable remediation candidates."""
    
    candidates: List[RemediationCandidate] = []
    
    # 1. Post-Validation Quarantine Analysis (The most common blocker source)
    quarantined: List[dict[str, Any]] = []
    total_input = 0
    valid_count = 0
    current_pass_rate = 100.0
    current_state = "READY"
    
    if validation_result:
        quarantined = (
            getattr(validation_result, "all_quarantined_records", None)
            or validation_result.sample_quarantined_records
            or []
        )
        total_input = validation_result.total_input_records
        valid_count = validation_result.valid_records_count
        current_pass_rate = validation_result.contract_pass_rate
        current_state = "PASS" if validation_result.is_contract_valid else "BLOCKED"

    # Map target field to source field from proposals
    target_to_source: dict[str, str] = {}
    for tgt, prop in mapping_plan.proposals.items():
        if prop.source_field:
            target_to_source[tgt] = prop.source_field

    # Track which row indices are affected by each candidate
    candidate_affected_rows: dict[str, Set[int]] = {}
    # Track which errors each row had
    row_error_signatures: dict[int, Set[str]] = {}

    # Inspect quarantined records
    for rec in quarantined:
        row_idx = rec.get("record_index") or rec.get("row_index", 0)
        errors = rec.get("errors") or rec.get("failure_reasons") or []
        raw_rec = rec.get("raw_record") or {}

        if row_idx not in row_error_signatures:
            row_error_signatures[row_idx] = set()

        for err in errors:
            err_lower = err.lower()
            row_error_signatures[row_idx].add(err)

            # Detect field name from error message
            target_field: Optional[str] = None
            match = re.search(r"for '([^']+)'|field '([^']+)'|'([^']+)' is missing|'([^']+)' does not match", err, re.IGNORECASE)
            if match:
                for g in match.groups():
                    if g:
                        target_field = g
                        break
            if not target_field:
                m2 = re.search(r"'([^']+)'", err)
                if m2:
                    target_field = m2.group(1)

            if not target_field or target_field not in contract.fields:
                continue

            field_def = contract.fields[target_field]
            src_col = target_to_source.get(target_field)
            raw_val = str(raw_rec.get(src_col, "")).strip() if src_col else ""

            # Check 1: Currency / Comma / Percentage in Float or Integer
            if field_def.target_type in (ContractType.FLOAT, ContractType.INTEGER) and (
                "cannot parse float" in err_lower or "cannot parse integer" in err_lower
            ):
                cand_id = f"rem_{target_field}_currency"
                if any(sym in raw_val for sym in ("$", "€", "£", "¥", ",")):
                    if cand_id not in candidate_affected_rows:
                        candidate_affected_rows[cand_id] = set()
                        clean_example = re.sub(r"[\$,€£¥\s]", "", raw_val).replace(",", "")
                        diff_val: Any = float(clean_example) if field_def.target_type == ContractType.FLOAT else int(float(clean_example))
                        
                        code_snippet = (
                            f"# Remediation: Strip currency & thousands separators\n"
                            f"clean_val = re.sub(r'[\\$,€£¥\\s]', '', val_{target_field}).replace(',', '')\n"
                            f"output['{target_field}'] = {field_def.target_type.value}(clean_val)"
                        )
                        candidates.append(
                            RemediationCandidate(
                                candidate_id=cand_id,
                                field_name=target_field,
                                source_field=src_col,
                                category=RemediationCategory.CURRENCY_CLEANING,
                                title=f"Strip Currency Symbols & Thousands Separators for '{target_field}'",
                                diagnosis=f"Field '{target_field}' contains raw currency symbols or thousands commas preventing {field_def.target_type.value} casting.",
                                suggested_action="Apply deterministic regex filter to strip currency glyphs ($ € £ ¥) and thousand commas before parsing.",
                                proposed_transformation_rule="clean_currency",
                                proposed_ast_code=code_snippet,
                                sample_diffs=[
                                    ValueDiff(
                                        raw_sample=raw_val,
                                        remediated_sample=diff_val,
                                        row_index=row_idx,
                                    )
                                ],
                                confidence_score=0.99,
                                is_recommended=True,
                            )
                        )
                    candidate_affected_rows[cand_id].add(row_idx)

                elif "%" in raw_val:
                    pct_cand_id = f"rem_{target_field}_percentage"
                    if pct_cand_id not in candidate_affected_rows:
                        candidate_affected_rows[pct_cand_id] = set()
                        clean_pct = float(raw_val.replace("%", "").strip())
                        code_snippet = (
                            f"# Remediation: Strip percentage glyph\n"
                            f"clean_val = val_{target_field}.replace('%', '').strip()\n"
                            f"output['{target_field}'] = float(clean_val)"
                        )
                        candidates.append(
                            RemediationCandidate(
                                candidate_id=pct_cand_id,
                                field_name=target_field,
                                source_field=src_col,
                                category=RemediationCategory.PERCENTAGE_CONVERSION,
                                title=f"Parse Percentage Values for '{target_field}'",
                                diagnosis=f"Field '{target_field}' contains percentage notation ('%') causing type conversion errors.",
                                suggested_action="Remove trailing '%' sign and convert to standard numeric float.",
                                proposed_transformation_rule="clean_percentage",
                                proposed_ast_code=code_snippet,
                                sample_diffs=[
                                    ValueDiff(
                                        raw_sample=raw_val,
                                        remediated_sample=clean_pct,
                                        row_index=row_idx,
                                    )
                                ],
                                confidence_score=0.99,
                                is_recommended=True,
                            )
                        )
                    candidate_affected_rows[pct_cand_id].add(row_idx)

            # Check 2: Non-Standard Datetime / Date Formats
            elif field_def.target_type in (ContractType.DATETIME, ContractType.DATE) and (
                "cannot parse datetime" in err_lower or "cannot parse date" in err_lower
            ):
                cand_id = f"rem_{target_field}_datetime"
                dt_result = _try_parse_datetime(raw_val)
                if dt_result:
                    detected_fmt, iso_sample = dt_result
                    if cand_id not in candidate_affected_rows:
                        candidate_affected_rows[cand_id] = set()
                        code_snippet = (
                            f"# Remediation: Parse enterprise date format '{detected_fmt}'\n"
                            f"dt = datetime.strptime(val_{target_field}, '{detected_fmt}')\n"
                            f"output['{target_field}'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')"
                        )
                        candidates.append(
                            RemediationCandidate(
                                candidate_id=cand_id,
                                field_name=target_field,
                                source_field=src_col,
                                category=RemediationCategory.DATETIME_FORMATTING,
                                title=f"Parse Timestamp Format for '{target_field}'",
                                diagnosis=f"Field '{target_field}' uses timestamp format '{detected_fmt}' instead of ISO-8601.",
                                suggested_action=f"Configure datetime parser with format '{detected_fmt}' and output normalized ISO-8601.",
                                proposed_transformation_rule=f"parse_datetime('{detected_fmt}')->iso8601",
                                proposed_ast_code=code_snippet,
                                sample_diffs=[
                                    ValueDiff(
                                        raw_sample=raw_val,
                                        remediated_sample=iso_sample,
                                        row_index=row_idx,
                                    )
                                ],
                                confidence_score=0.98,
                                is_recommended=True,
                            )
                        )
                    candidate_affected_rows[cand_id].add(row_idx)

            # Check 3: Enum Casing & Whitespace Normalization
            elif field_def.allowed_values and (
                "not in allowed values" in err_lower or "enum" in err_lower
            ):
                cand_id = f"rem_{target_field}_enum"
                raw_norm = raw_val.strip().lower()
                allowed_match = next((v for v in field_def.allowed_values if v.strip().lower() == raw_norm), None)
                if allowed_match:
                    if cand_id not in candidate_affected_rows:
                        candidate_affected_rows[cand_id] = set()
                        code_snippet = (
                            f"# Remediation: Case-insensitive enum alignment\n"
                            f"enum_map = {{v.lower().strip(): v for v in {repr(field_def.allowed_values)}}}\n"
                            f"output['{target_field}'] = enum_map.get(val_{target_field}.lower().strip(), val_{target_field}.strip())"
                        )
                        candidates.append(
                            RemediationCandidate(
                                candidate_id=cand_id,
                                field_name=target_field,
                                source_field=src_col,
                                category=RemediationCategory.ENUM_NORMALIZATION,
                                title=f"Case-Insensitive Enum Alignment for '{target_field}'",
                                diagnosis=f"Field '{target_field}' values match allowed categories but differ in casing or padding (e.g. '{raw_val}' vs '{allowed_match}').",
                                suggested_action="Normalize values case-insensitively to exact contract enum allowed values.",
                                proposed_transformation_rule="case_insensitive_enum",
                                proposed_ast_code=code_snippet,
                                sample_diffs=[
                                    ValueDiff(
                                        raw_sample=raw_val,
                                        remediated_sample=allowed_match,
                                        row_index=row_idx,
                                    )
                                ],
                                confidence_score=0.99,
                                is_recommended=True,
                            )
                        )
                    candidate_affected_rows[cand_id].add(row_idx)

    # 2. Check for Unmapped Required Fields (Pre-approval or Validation Block)
    for tgt_name, tgt_field in contract.fields.items():
        if tgt_field.required:
            prop = mapping_plan.get_proposal(tgt_name)
            if not prop or not prop.source_field or prop.mapping_type == MappingType.MISSING_SOURCE:
                # Find candidate from profile columns if available
                suggested_col: Optional[str] = None
                if profile:
                    norm_tgt = tgt_name.lower().replace("_", "")
                    for col in profile.columns.keys():
                        norm_col = col.lower().replace("_", "")
                        if norm_col == norm_tgt or norm_tgt in norm_col or norm_col in norm_tgt:
                            suggested_col = col
                            break
                
                if suggested_col:
                    cand_id = f"rem_{tgt_name}_unmapped"
                    code_snippet = (
                        f"# Remediation: Map required field '{tgt_name}' to candidate column '{suggested_col}'\n"
                        f"output['{tgt_name}'] = record.get('{suggested_col}')"
                    )
                    candidates.append(
                        RemediationCandidate(
                            candidate_id=cand_id,
                            field_name=tgt_name,
                            source_field=suggested_col,
                            category=RemediationCategory.UNMAPPED_FIELD,
                            title=f"Auto-Map Required Field '{tgt_name}' ➔ '{suggested_col}'",
                            diagnosis=f"Required contract field '{tgt_name}' is currently unmapped, blocking adapter generation.",
                            suggested_action=f"Map target field '{tgt_name}' to candidate source column '{suggested_col}'.",
                            proposed_transformation_rule="direct_map",
                            proposed_ast_code=code_snippet,
                            sample_diffs=[
                                ValueDiff(
                                    raw_sample=f"<unmapped: {suggested_col}>",
                                    remediated_sample=f"output['{tgt_name}']",
                                )
                            ],
                            confidence_score=0.90,
                            is_recommended=True,
                        )
                    )

    # 3. Deterministic Yield Gain Calculation
    # Determine which quarantined rows are 100% rescued if all candidates are applied
    rescued_row_indices: Set[int] = set()
    all_candidate_affected = set().union(*candidate_affected_rows.values()) if candidate_affected_rows else set()

    for r_idx, errors in row_error_signatures.items():
        # Check if every error in this row is addressed by at least one candidate
        addressed = True
        for err in errors:
            err_lower = err.lower()
            # Does this error correspond to a candidate?
            err_handled = False
            for cand in candidates:
                if cand.field_name.lower() in err_lower or f"'{cand.field_name.lower()}'" in err_lower:
                    err_handled = True
                    break
            if not err_handled:
                addressed = False
                break
        if addressed:
            rescued_row_indices.add(r_idx)

    # Update candidate affected counts & yield impact
    for cand in candidates:
        affected = candidate_affected_rows.get(cand.candidate_id, set())
        cand.affected_records_count = len(affected)
        if total_input > 0:
            cand.projected_yield_gain_percent = round((len(affected) / total_input) * 100.0, 2)

    projected_rescued = len(rescued_row_indices)
    projected_pass_rate = (
        round(((valid_count + projected_rescued) / total_input) * 100.0, 2)
        if total_input > 0
        else 100.0
    )

    return RemediationPlan(
        session_id=session_id,
        current_readiness_state=current_state,
        current_pass_rate=current_pass_rate,
        projected_pass_rate=projected_pass_rate,
        total_quarantined_records=len(quarantined),
        projected_rescued_records=projected_rescued,
        candidates=candidates,
    )
