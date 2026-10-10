"""Generates explicit, reviewable Python transformation adapters from approved mapping plans."""

import re
from recon.adapters.models import GeneratedAdapter
from recon.contracts.models import ContractType, TargetContract
from recon.exceptions import AdapterError
from recon.logging import log_safe_event
from recon.mapping.models import ApprovedMappingPlan, MappingStatus


def generate_adapter(
    approved_plan: ApprovedMappingPlan,
    contract: TargetContract,
    invalid_record_policy: str = "quarantine",
) -> GeneratedAdapter:
    """Generates standalone, reviewable Python adapter code from an ApprovedMappingPlan.

    Raises:
        AdapterError: If the plan is incomplete or missing approved mappings for required target fields.
    """
    missing_req = [
        f.name for f in contract.fields.values()
        if f.required and (
            f.name not in approved_plan.approved_mappings
            or approved_plan.approved_mappings[f.name].status != MappingStatus.APPROVED
            or not approved_plan.approved_mappings[f.name].source_field
        )
    ]
    if missing_req:
        raise AdapterError(
            f"Cannot generate adapter: approved mapping plan is incomplete. Missing required fields: {missing_req}",
            actionable_suggestion="Approve all required target field mappings before generating an adapter.",
            context={"missing_required_fields": missing_req},
        )

    # Build field transformation logic
    field_code_blocks: list[str] = []

    for target_name, target_field in contract.fields.items():
        mapping = approved_plan.approved_mappings.get(target_name)
        if not mapping or not mapping.source_field:
            if not target_field.required:
                # Optional unmapped field defaults to None
                field_code_blocks.append(f"    # {target_name}: unmapped optional field\n    output['{target_name}'] = None")
            continue

        src_field = mapping.source_field
        tgt_type = target_field.target_type
        req = target_field.required
        nullable = target_field.nullable
        allowed_vals = target_field.allowed_values
        pattern = target_field.pattern
        trans_rule = mapping.transformation_rule or ""

        block = [f"    # Target: {target_name} <- Source: '{src_field}'"]
        block.append(f"    raw_val_{target_name} = record.get('{src_field}')")
        block.append(f"    val_{target_name} = str(raw_val_{target_name}).strip() if raw_val_{target_name} is not None else ''")
        block.append(f"    if raw_val_{target_name} is None or val_{target_name}.lower() in ('', 'null', 'none', 'nan', 'n/a'):")
        if req and not nullable:
            block.append(f"        errors.append(\"Required non-nullable field '{target_name}' is missing or null (source '{src_field}')\")")
            block.append(f"        output['{target_name}'] = None")
        elif not req and not nullable:
            block.append(f"        errors.append(\"Non-nullable field '{target_name}' cannot be null (source '{src_field}')\")")
            block.append(f"        output['{target_name}'] = None")
        else:
            block.append(f"        output['{target_name}'] = None")
        block.append("    else:")

        # Parse / Transform non-null value
        if tgt_type == ContractType.STRING:
            if "uppercase" in trans_rule or (allowed_vals and any(v.isupper() for v in allowed_vals)):
                block.append(f"        parsed_{target_name} = val_{target_name}.upper()")
            else:
                block.append(f"        parsed_{target_name} = val_{target_name}")

            # Enum validation
            if allowed_vals:
                allowed_repr = repr(allowed_vals)
                block.append(f"        if parsed_{target_name} not in {allowed_repr}:")
                block.append(f"            errors.append(f\"Value '{{parsed_{target_name}}}' for '{target_name}' not in allowed values {allowed_repr}\")")

            # Regex pattern validation
            if pattern:
                pattern_repr = repr(pattern)
                block.append(f"        if not re.match({pattern_repr}, parsed_{target_name}):")
                block.append(f"            errors.append(f\"Value '{{parsed_{target_name}}}' for '{target_name}' does not match pattern \" + {pattern_repr})")

            block.append(f"        output['{target_name}'] = parsed_{target_name}")

        elif tgt_type == ContractType.INTEGER:
            block.append("        try:")
            block.append(f"            output['{target_name}'] = int(raw_val_{target_name}) if isinstance(raw_val_{target_name}, (int, float)) else int(val_{target_name})")
            block.append("        except ValueError:")
            block.append(f"            errors.append(f\"Cannot parse integer for '{target_name}' from '{{raw_val_{target_name}}}'\")")
            block.append(f"            output['{target_name}'] = None")

        elif tgt_type == ContractType.FLOAT:
            block.append("        try:")
            block.append(f"            output['{target_name}'] = float(raw_val_{target_name})")
            block.append("        except ValueError:")
            block.append(f"            errors.append(f\"Cannot parse float for '{target_name}' from '{{raw_val_{target_name}}}'\")")
            block.append(f"            output['{target_name}'] = None")

        elif tgt_type == ContractType.DATETIME:
            # Datetime parsing
            # Default to standard ISO-8601 unless non-standard format is captured in transformation rule
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            if "parse_datetime('" in trans_rule:
                match = re.search(r"parse_datetime\('([^']+)'\)", trans_rule)
                if match:
                    fmt = match.group(1)

            block.append("        try:")
            block.append(f"            dt = datetime.strptime(val_{target_name}, '{fmt}')")
            block.append(f"            output['{target_name}'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')")
            block.append("        except ValueError:")
            block.append(f"            errors.append(f\"Cannot parse datetime for '{target_name}' using format '{fmt}' from '{{val_{target_name}}}'\")")
            block.append(f"            output['{target_name}'] = None")

        elif tgt_type == ContractType.BOOLEAN:
            block.append(f"        if isinstance(raw_val_{target_name}, bool):")
            block.append(f"            output['{target_name}'] = raw_val_{target_name}")
            block.append(f"        elif val_{target_name}.lower() in ('true', 'yes', '1', 't'):")
            block.append(f"            output['{target_name}'] = True")
            block.append(f"        elif val_{target_name}.lower() in ('false', 'no', '0', 'f'):")
            block.append(f"            output['{target_name}'] = False")
            block.append("        else:")
            block.append(f"            errors.append(f\"Cannot parse boolean for '{target_name}' from '{{raw_val_{target_name}}}'\")")
            block.append(f"            output['{target_name}'] = None")

        field_code_blocks.append("\n".join(block))

    body = "\n\n".join(field_code_blocks)

    adapter_code = f'''"""Generated Integration Adapter for {contract.contract_name}.
Auto-generated by Recon — The Integration Readiness Engine.
Contract Version: {contract.version}
Invalid Record Policy: {invalid_record_policy}
"""

import re
from datetime import datetime
from typing import Any, Tuple, List, Dict, Optional


def transform_record(record: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Transforms a single raw source record into the target contract format.

    Returns:
        (transformed_payload, validation_errors)
        If validation_errors is non-empty, transformed_payload is None.
    """
    errors: List[str] = []
    output: Dict[str, Any] = {{}}

{body}

    if errors:
        return None, errors
    return output, []


def transform_dataset(records: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Transforms a collection of raw source records according to the contract.

    Never silently drops records.
    Returns:
        (valid_records, quarantined_records)
    """
    valid: List[Dict[str, Any]] = []
    quarantined: List[Dict[str, Any]] = []

    for idx, rec in enumerate(records, start=1):
        transformed, errors = transform_record(rec)
        if errors:
            quarantined.append({{
                "record_index": idx,
                "raw_record": rec,
                "errors": errors,
            }})
        else:
            valid.append(transformed)

    return valid, quarantined
'''

    adapter = GeneratedAdapter(
        adapter_name=f"{contract.contract_name}_adapter",
        source_fingerprint=approved_plan.source_fingerprint,
        contract_name=contract.contract_name,
        contract_version=contract.version,
        python_code=adapter_code,
        invalid_record_policy=invalid_record_policy,
    )

    log_safe_event(
        "ADAPTER_GENERATED",
        contract=contract.contract_name,
        adapter=adapter.adapter_name,
        policy=invalid_record_policy,
    )

    return adapter
