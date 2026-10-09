"""Deterministic mapping proposal engine generating evidence-backed field alignments."""

import re
from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.logging import log_safe_event
from recon.mapping.models import FieldMappingProposal, MappingPlan, MappingStatus, MappingType
from recon.profiling.models import ColumnProfile, InferredType, SourceProfile

SYNONYMS: dict[str, list[str]] = {
    "ticket_id": ["unique key", "ticket id", "ticket", "id", "incident id", "key"],
    "created_at": ["created date", "created at", "creation date", "opened date", "open date"],
    "closed_at": ["closed date", "closed at", "resolution date", "completion date"],
    "agency_code": ["agency", "agency code", "agency id", "dept code", "dept"],
    "category": ["complaint type", "category", "issue type", "problem type", "type"],
    "description": ["descriptor", "description", "details", "narrative", "comments"],
    "borough": ["borough", "district", "county"],
    "status": ["status", "state", "current status"],
    "postal_code": ["incident zip", "postal code", "zip code", "zip", "postcode"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
}


def normalize_name(name: str) -> str:
    """Normalizes field name by lower-casing and stripping non-alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_matching_source_columns(
    target_name: str,
    available_columns: list[str],
) -> tuple[str | None, list[str]]:
    """Identifies primary candidate source column and alternative candidates using deterministic heuristics."""
    norm_target = normalize_name(target_name)
    synonym_candidates = SYNONYMS.get(target_name, [target_name])
    norm_synonyms = [normalize_name(s) for s in synonym_candidates]

    exact_matches: list[str] = []
    synonym_matches: list[str] = []

    for col in available_columns:
        norm_col = normalize_name(col)
        if norm_col == norm_target:
            exact_matches.append(col)
        elif norm_col in norm_synonyms or any(norm_s in norm_col for norm_s in norm_synonyms):
            synonym_matches.append(col)

    if exact_matches:
        primary = exact_matches[0]
        alternatives = exact_matches[1:] + synonym_matches
        return primary, alternatives

    if synonym_matches:
        # Prioritize exact synonym phrase over substring
        primary = synonym_matches[0]
        alternatives = synonym_matches[1:]
        return primary, alternatives

    return None, []


def propose_mappings(
    profile: SourceProfile,
    contract: TargetContract,
) -> MappingPlan:
    """Generates evidence-backed mapping proposals by comparing SourceProfile to TargetContract."""
    available_source_cols = list(profile.columns.keys())
    proposals: dict[str, FieldMappingProposal] = {}

    for target_name, target_field in contract.fields.items():
        primary_col, alternatives = find_matching_source_columns(
            target_name,
            available_source_cols,
        )

        if not primary_col:
            # Missing source column
            proposals[target_name] = FieldMappingProposal(
                target_field=target_name,
                target_type=target_field.target_type,
                target_required=target_field.required,
                target_nullable=target_field.nullable,
                source_field=None,
                source_inferred_type=None,
                mapping_type=MappingType.MISSING_SOURCE,
                status=MappingStatus.UNRESOLVED,
                evidence=[
                    f"No candidate column found among source headers: {available_source_cols}."
                ],
            )
            continue

        src_col_profile: ColumnProfile = profile.columns[primary_col]
        evidence: list[str] = []
        mapping_type = MappingType.DIRECT
        transformation_rule: str | None = None

        # Evidence: Name alignment
        evidence.append(
            f"Field name '{src_col_profile.name}' matched target '{target_name}' via heuristic/synonym rule."
        )

        # Evidence & Transformation: Type alignment
        src_type = src_col_profile.inferred_type
        tgt_type = target_field.target_type

        # 1. Target STRING from Source INTEGER or FLOAT
        if tgt_type == ContractType.STRING and src_type in (InferredType.INTEGER, InferredType.FLOAT):
            mapping_type = MappingType.TRANSFORMATION_REQUIRED
            transformation_rule = "to_string"
            evidence.append(
                f"Source column type '{src_type.value}' requires cast to target type 'string'."
            )

        # 2. Target DATETIME from Source DATETIME
        elif tgt_type == ContractType.DATETIME:
            if src_type in (InferredType.DATETIME, InferredType.DATE):
                fmt = src_col_profile.format_patterns[0] if src_col_profile.format_patterns else "unknown"
                if fmt != "%Y-%m-%dT%H:%M:%SZ":
                    mapping_type = MappingType.TRANSFORMATION_REQUIRED
                    transformation_rule = f"parse_datetime('{fmt}')->iso8601"
                    evidence.append(
                        f"Source format '{fmt}' requires parsing to target ISO-8601 timestamp."
                    )
                else:
                    evidence.append("Source timestamp is already in standard ISO-8601 format.")
            else:
                mapping_type = MappingType.TRANSFORMATION_REQUIRED
                transformation_rule = "parse_datetime->iso8601"
                evidence.append(
                    f"Source type '{src_type.value}' is not declared datetime; parsing required."
                )

        # 3. Target STRING with Allowed Values (Enum/Categories)
        elif tgt_type == ContractType.STRING and target_field.allowed_values:
            # Check if casing conversion is needed
            allowed_set = set(target_field.allowed_values)
            sample_vals = src_col_profile.sample_values
            needs_uppercase = any(
                s.upper() in allowed_set and s not in allowed_set for s in sample_vals
            )
            if needs_uppercase:
                mapping_type = MappingType.TRANSFORMATION_REQUIRED
                transformation_rule = "uppercase_strip"
                evidence.append(
                    f"Target enum requires uppercase values {target_field.allowed_values}; source contains mixed-case samples {sample_vals}."
                )
            else:
                evidence.append(
                    f"Source samples {sample_vals} match allowed target categories."
                )

        # 4. Check for leading/trailing whitespace
        if src_col_profile.has_whitespace_anomalies:
            if mapping_type == MappingType.DIRECT:
                mapping_type = MappingType.TRANSFORMATION_REQUIRED
                transformation_rule = "strip"
            evidence.append(
                f"Source column '{src_col_profile.name}' exhibits whitespace anomalies; strip required."
            )

        # 5. Nullability constraint evidence
        if not target_field.nullable and src_col_profile.null_count > 0:
            evidence.append(
                f"POTENTIAL CONFLICT: Target field is non-nullable, but source column contains {src_col_profile.null_percentage}% null values ({src_col_profile.null_count}/{src_col_profile.total_count})."
            )

        # 6. Ambiguity check: if multiple strong alternatives exist
        if alternatives:
            evidence.append(f"Alternative candidate source columns observed: {alternatives}.")

        proposals[target_name] = FieldMappingProposal(
            target_field=target_name,
            target_type=target_field.target_type,
            target_required=target_field.required,
            target_nullable=target_field.nullable,
            source_field=src_col_profile.name,
            source_inferred_type=src_type,
            mapping_type=mapping_type,
            status=MappingStatus.PROPOSED,
            transformation_rule=transformation_rule,
            evidence=evidence,
            alternative_candidates=alternatives,
        )

    plan = MappingPlan(
        contract_name=contract.contract_name,
        source_name=profile.source_name,
        source_fingerprint=profile.fingerprint,
        proposals=proposals,
    )

    log_safe_event(
        "MAPPINGS_PROPOSED",
        contract=contract.contract_name,
        source=profile.source_name,
        total_fields=len(proposals),
        unresolved=len(plan.unresolved_proposals()),
    )

    return plan
