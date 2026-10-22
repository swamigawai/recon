"""Reusable, versioned mapping specifications for Recon."""

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any
from pydantic import BaseModel, Field

from recon.contracts.models import ContractType, TargetContract
from recon.exceptions import MappingError
from recon.mapping.models import (
    ApprovedMappingPlan,
    FieldMappingProposal,
    MappingPlan,
    MappingStatus,
    MappingType,
)
from recon.profiling.models import InferredType, SourceProfile

SPEC_SCHEMA_VERSION = "1.0"
ENGINE_VERSION = "0.1.0"


class MappingDecision(BaseModel):
    """An individual mapping decision serialized within a versioned specification."""
    target_field: str
    source_field: str | None = None
    mapping_type: MappingType = MappingType.DIRECT
    transformation_rule: str | None = None
    target_required: bool = False
    approved: bool = False
    approver: str | None = None
    approved_at: datetime | None = None
    notes: str | None = None


class MappingSpecification(BaseModel):
    """Versioned, reusable mapping specification (recon_mapping_spec.json)."""
    schema_version: str = SPEC_SCHEMA_VERSION
    engine_version: str = ENGINE_VERSION
    created_at: datetime = Field(default_factory=datetime.utcnow)
    contract_name: str
    contract_version: str = "1.0.0"
    contract_fingerprint: str
    source_fingerprint: str
    source_columns: dict[str, str] = Field(default_factory=dict)
    mappings: list[MappingDecision] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        """Serializes specification to a formatted JSON string."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "MappingSpecification":
        """Deserializes specification from a JSON string."""
        return cls.model_validate_json(json_str)

    def save_to_file(self, path: Path | str) -> None:
        """Saves specification to a JSON file."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(self.to_json(), encoding="utf-8")


class SpecificationValidationResult(BaseModel):
    """Diagnostic outcome of validating and applying a MappingSpecification."""
    is_valid: bool
    schema_version: str
    contract_match: bool
    source_match: bool
    reused_count: int
    unresolved_count: int
    conflicts: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


def export_mapping_spec(
    contract: TargetContract,
    profile: SourceProfile,
    plan: MappingPlan | ApprovedMappingPlan,
    reviewer: str | None = None,
) -> MappingSpecification:
    """Exports a versioned MappingSpecification from the current mapping state.

    Only substantiable mapping and provenance information is recorded.
    """
    is_approved_plan = isinstance(plan, ApprovedMappingPlan)
    decisions: list[MappingDecision] = []

    mappings_dict = (
        plan.approved_mappings if is_approved_plan else plan.proposals
    )

    for target_name, prop in mappings_dict.items():
        decisions.append(
            MappingDecision(
                target_field=target_name,
                source_field=prop.source_field,
                mapping_type=prop.mapping_type,
                transformation_rule=prop.transformation_rule,
                target_required=prop.target_required,
                approved=is_approved_plan or (prop.status == MappingStatus.APPROVED),
                approver=plan.approved_by if is_approved_plan else reviewer,
                approved_at=plan.approved_at if is_approved_plan else None,
                notes=prop.human_notes,
            )
        )

    # Sort decisions deterministically by target_field name
    decisions.sort(key=lambda d: d.target_field)

    source_cols = {
        col.name: col.inferred_type.value for col in profile.columns.values()
    }

    return MappingSpecification(
        schema_version=SPEC_SCHEMA_VERSION,
        engine_version=ENGINE_VERSION,
        contract_name=contract.contract_name,
        contract_version=contract.version,
        contract_fingerprint=contract.fingerprint,
        source_fingerprint=profile.fingerprint,
        source_columns=source_cols,
        mappings=decisions,
    )


def load_mapping_spec(
    source: Path | str | dict[str, Any],
) -> MappingSpecification:
    """Parses and validates the raw structure of a mapping specification file or dictionary.

    Raises:
        MappingError: If JSON syntax is invalid, schema_version is unsupported,
                      or duplicate conflicting target mappings exist.
    """
    if isinstance(source, (str, Path)):
        path_str = str(source)
        if path_str.startswith("{"):
            try:
                data = json.loads(path_str)
            except json.JSONDecodeError as err:
                raise MappingError(
                    f"Invalid JSON in mapping specification: {err}",
                    actionable_suggestion="Check the mapping specification file for JSON syntax errors.",
                    context={"line": err.lineno, "col": err.colno},
                ) from err
        else:
            p = Path(source)
            if not p.is_file():
                raise MappingError(
                    f"Mapping specification file not found: {source}",
                    actionable_suggestion="Provide a valid file path to an existing recon_mapping_spec.json.",
                    context={"path": str(p)},
                )
            try:
                content = p.read_text(encoding="utf-8")
                data = json.loads(content)
            except json.JSONDecodeError as err:
                raise MappingError(
                    f"Invalid JSON in mapping specification file '{source}': {err}",
                    actionable_suggestion="Check file for syntax errors or corrupted content.",
                    context={"file": str(p), "line": err.lineno},
                ) from err
    elif isinstance(source, dict):
        data = source
    else:
        raise MappingError(
            f"Unsupported mapping specification input type: {type(source).__name__}",
            actionable_suggestion="Provide a file path, JSON string, or dictionary.",
        )

    if not isinstance(data, dict):
        raise MappingError(
            "Mapping specification root must be a JSON object.",
            actionable_suggestion="Ensure the mapping spec contains a JSON object '{...}'.",
        )

    # 1. Version check
    schema_ver = str(data.get("schema_version", ""))
    if schema_ver != SPEC_SCHEMA_VERSION:
        raise MappingError(
            f"Unsupported mapping specification schema version '{schema_ver}'. Supported version: '{SPEC_SCHEMA_VERSION}'.",
            actionable_suggestion=f"Upgrade specification to schema_version '{SPEC_SCHEMA_VERSION}'.",
            context={"found_version": schema_ver, "supported_version": SPEC_SCHEMA_VERSION},
        )

    # 2. Check duplicate / conflicting target mappings
    raw_mappings = data.get("mappings", [])
    if isinstance(raw_mappings, list):
        seen_targets: set[str] = set()
        for idx, item in enumerate(raw_mappings):
            if isinstance(item, dict) and "target_field" in item:
                tgt = item["target_field"]
                if tgt in seen_targets:
                    raise MappingError(
                        f"Duplicate / conflicting mapping decision for target field '{tgt}' at index {idx}.",
                        actionable_suggestion="Ensure each target field appears at most once in the specification.",
                        context={"target_field": tgt, "index": idx},
                    )
                seen_targets.add(tgt)

    try:
        spec = MappingSpecification.model_validate(data)
    except Exception as err:
        raise MappingError(
            f"Mapping specification validation failed: {err}",
            actionable_suggestion="Verify specification conforms to the Recon mapping specification schema.",
        ) from err

    return spec


def validate_and_apply_mapping_spec(
    spec: MappingSpecification,
    contract: TargetContract,
    profile: SourceProfile,
    base_plan: MappingPlan,
) -> tuple[MappingPlan, SpecificationValidationResult]:
    """Validates imported mapping decisions against current contract and source profile.

    Strict Import Rules:
    1. Schema version must match '1.0'.
    2. Target field must exist in the active contract.
    3. Source field must exist in the source profile.
    4. Fingerprints are compared for strict provenance checking.
    5. Required fields MUST NEVER be automatically marked approved solely from imported JSON.
       Human approval remains mandatory!
    6. Returns updated MappingPlan with reused decisions and detailed diagnostics.
    """
    conflicts: list[str] = []
    mismatches: list[str] = []
    warnings: list[str] = []
    diagnostics: list[dict[str, Any]] = []

    contract_match = (spec.contract_fingerprint == contract.fingerprint)
    if not contract_match:
        mismatches.append(
            f"Contract fingerprint mismatch: spec '{spec.contract_fingerprint[:8]}...' != active '{contract.fingerprint[:8]}...'. Target contract has changed."
        )

    source_match = (spec.source_fingerprint == profile.fingerprint)
    if not source_match:
        warnings.append(
            f"Source schema fingerprint mismatch: spec '{spec.source_fingerprint[:8]}...' != active '{profile.fingerprint[:8]}...'. Source batch or columns differ."
        )

    source_col_map = profile.columns
    reused_count = 0
    unresolved_count = 0

    # Build indexed map of spec decisions
    spec_decisions = {d.target_field: d for d in spec.mappings}

    updated_proposals: dict[str, FieldMappingProposal] = {}

    for target_name, target_field in contract.fields.items():
        base_proposal = base_plan.get_proposal(target_name)
        decision = spec_decisions.get(target_name)

        if decision is None:
            # Not in spec; keep base proposal
            if base_proposal:
                updated_proposals[target_name] = base_proposal
                if base_proposal.status == MappingStatus.UNRESOLVED or base_proposal.mapping_type in (
                    MappingType.AMBIGUOUS,
                    MappingType.MISSING_SOURCE,
                    MappingType.UNSUPPORTED,
                ):
                    unresolved_count += 1
            continue

        # Target field is in spec: validate applicability
        src_field_name = decision.source_field

        if not src_field_name:
            # Explicit unmapped decision in spec
            updated_proposals[target_name] = FieldMappingProposal(
                target_field=target_name,
                target_type=target_field.target_type,
                target_required=target_field.required,
                target_nullable=target_field.nullable,
                source_field=None,
                source_inferred_type=None,
                mapping_type=MappingType.MISSING_SOURCE,
                status=MappingStatus.UNRESOLVED if target_field.required else MappingStatus.PROPOSED,
                transformation_rule=None,
                evidence=["Specification explicitly unmapped this field."],
                human_notes=decision.notes,
            )
            if target_field.required:
                unresolved_count += 1
                conflicts.append(f"Required target field '{target_name}' is explicitly unmapped in specification.")
            continue

        # Check if source field exists in current source profile
        if src_field_name not in source_col_map:
            mismatches.append(
                f"Source column '{src_field_name}' specified for '{target_name}' not found in current source profile."
            )
            diagnostics.append({
                "target_field": target_name,
                "specified_source": src_field_name,
                "reason": "SOURCE_COLUMN_MISSING",
            })
            # Mark as missing source / unresolved
            updated_proposals[target_name] = FieldMappingProposal(
                target_field=target_name,
                target_type=target_field.target_type,
                target_required=target_field.required,
                target_nullable=target_field.nullable,
                source_field=None,
                source_inferred_type=None,
                mapping_type=MappingType.MISSING_SOURCE,
                status=MappingStatus.UNRESOLVED,
                transformation_rule=None,
                evidence=[
                    f"Specification mapped '{target_name}' to '{src_field_name}', but column '{src_field_name}' does not exist in the current source dataset."
                ],
                human_notes=decision.notes,
            )
            unresolved_count += 1
            continue

        src_col = source_col_map[src_field_name]

        # Check transformation rule validity
        trans_rule = decision.transformation_rule
        if trans_rule:
            # Disallow arbitrary executable code patterns
            if any(forbidden in trans_rule for forbidden in ("import", "exec", "eval", "__", "open", "os.")):
                conflicts.append(
                    f"Unsafe or forbidden transformation rule in specification for '{target_name}': '{trans_rule}'."
                )
                unresolved_count += 1
                updated_proposals[target_name] = FieldMappingProposal(
                    target_field=target_name,
                    target_type=target_field.target_type,
                    target_required=target_field.required,
                    target_nullable=target_field.nullable,
                    source_field=src_field_name,
                    source_inferred_type=src_col.inferred_type,
                    mapping_type=MappingType.UNSUPPORTED,
                    status=MappingStatus.UNRESOLVED,
                    transformation_rule=None,
                    evidence=[f"Rejected unsafe transformation rule: '{trans_rule}'."],
                    human_notes=decision.notes,
                )
                continue

        # Decision is compatible and accepted to pre-fill proposal!
        # CRITICAL: Client-supplied approval status is NEVER automatically accepted for required fields!
        # Status is PROPOSED so human approval remains strictly enforced.
        reused_count += 1
        evidence_list = [
            f"Reused from mapping specification (spec v{spec.schema_version}, created {spec.created_at.strftime('%Y-%m-%d')}).",
            f"Source column '{src_field_name}' matched (type: {src_col.inferred_type.value}).",
        ]
        if decision.approver:
            evidence_list.append(f"Previously reviewed by: {decision.approver}.")

        updated_proposals[target_name] = FieldMappingProposal(
            target_field=target_name,
            target_type=target_field.target_type,
            target_required=target_field.required,
            target_nullable=target_field.nullable,
            source_field=src_field_name,
            source_inferred_type=src_col.inferred_type,
            mapping_type=decision.mapping_type,
            status=MappingStatus.PROPOSED,  # Human approval remains mandatory!
            transformation_rule=trans_rule,
            evidence=evidence_list,
            alternative_candidates=base_proposal.alternative_candidates if base_proposal else [],
            human_notes=decision.notes,
        )

    # Check for orphaned mappings in spec that do not exist in the active contract
    for spec_target in spec_decisions:
        if spec_target not in contract.fields:
            warnings.append(
                f"Specification contains mapping for target field '{spec_target}', but '{spec_target}' does not exist in active contract '{contract.contract_name}'."
            )

    updated_plan = MappingPlan(
        contract_name=contract.contract_name,
        source_name=profile.source_name,
        source_fingerprint=profile.fingerprint,
        proposals=updated_proposals,
    )

    validation_result = SpecificationValidationResult(
        is_valid=(len(conflicts) == 0),
        schema_version=spec.schema_version,
        contract_match=contract_match,
        source_match=source_match,
        reused_count=reused_count,
        unresolved_count=unresolved_count,
        conflicts=conflicts,
        mismatches=mismatches,
        warnings=warnings,
        diagnostics=diagnostics,
    )

    return updated_plan, validation_result
