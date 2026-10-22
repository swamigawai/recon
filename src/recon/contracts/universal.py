"""Universal target contract ingestion engine supporting JSON Schema and OpenAPI 3.x."""

from enum import Enum
import re
from typing import Any

from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.exceptions import ContractError


class ContractFormat(str, Enum):
    """Supported target contract formats."""
    NATIVE = "native"
    JSON_SCHEMA_DRAFT_07 = "json_schema_draft_07"
    JSON_SCHEMA_2020_12 = "json_schema_2020_12"
    OPENAPI_3 = "openapi_3"
    UNKNOWN = "unknown"


def detect_contract_format(data: dict[str, Any]) -> tuple[ContractFormat, str]:
    """Deterministically identifies the schema format of a parsed JSON dictionary.

    Returns:
        tuple[ContractFormat, str]: The detected format enum and a human-readable description.
    """
    if not isinstance(data, dict):
        raise ContractError(
            "Contract root must be a JSON object (dictionary).",
            actionable_suggestion="Ensure the contract file root is an object '{...}', not a list or scalar.",
        )

    # 1. Native Recon Contract
    if "contract_name" in data and "fields" in data and isinstance(data["fields"], dict):
        return ContractFormat.NATIVE, "Native Recon Target Contract"

    # 2. OpenAPI 3.x
    if "openapi" in data:
        openapi_ver = str(data["openapi"]).strip()
        if openapi_ver.startswith("3."):
            return ContractFormat.OPENAPI_3, f"OpenAPI {openapi_ver}"
        raise ContractError(
            f"Unsupported OpenAPI version '{openapi_ver}'. Only OpenAPI 3.x is supported.",
            actionable_suggestion="Upgrade OpenAPI document to 3.0.x or 3.1.x, or convert to JSON Schema.",
        )

    # 3. JSON Schema
    schema_uri = str(data.get("$schema", "")).lower()
    if "draft-07" in schema_uri:
        return ContractFormat.JSON_SCHEMA_DRAFT_07, "JSON Schema Draft-07"
    if "2020-12" in schema_uri:
        return ContractFormat.JSON_SCHEMA_2020_12, "JSON Schema 2020-12"

    # Infer JSON Schema if standard properties/type are present
    if "properties" in data and isinstance(data["properties"], dict):
        return ContractFormat.JSON_SCHEMA_DRAFT_07, "JSON Schema (properties-inferred)"
    if data.get("type") == "object":
        return ContractFormat.JSON_SCHEMA_DRAFT_07, "JSON Schema (object-inferred)"

    raise ContractError(
        "Unrecognized contract schema format. Expected Native Recon contract, JSON Schema (Draft-07/2020-12), or OpenAPI 3.x.",
        actionable_suggestion="Ensure the file has either a native 'contract_name' with 'fields', a JSON Schema '$schema'/'properties', or an OpenAPI 'openapi: 3.x' specification.",
    )


def resolve_local_ref(
    ref_str: str,
    root_doc: dict[str, Any],
    visited: set[str] | None = None,
) -> dict[str, Any]:
    """Resolves local #/components/schemas/... references safely with cycle detection.

    Raises:
        ContractError: If reference is remote, malformed, circular, or cannot be resolved.
    """
    if visited is None:
        visited = set()

    clean_ref = ref_str.strip()
    if clean_ref.startswith("http://") or clean_ref.startswith("https://") or "://" in clean_ref:
        raise ContractError(
            f"Remote $ref references are forbidden for security reasons: {clean_ref}",
            actionable_suggestion="Incorporate external schemas locally into the contract file.",
            context={"ref": clean_ref},
        )

    if not clean_ref.startswith("#/"):
        raise ContractError(
            f"Only document-relative references (#/...) are supported: {clean_ref}",
            actionable_suggestion="Use local pointers such as '#/components/schemas/ModelName'.",
            context={"ref": clean_ref},
        )

    if clean_ref in visited:
        raise ContractError(
            f"Circular $ref reference detected at '{clean_ref}'.",
            actionable_suggestion="Eliminate circular definitions or flatten referenced schemas.",
            context={"circular_ref": clean_ref, "cycle_path": list(visited)},
        )

    visited.add(clean_ref)

    # Traverse JSON pointer
    tokens = clean_ref[2:].split("/")
    current: Any = root_doc
    for token in tokens:
        # Unescape RFC 6901 tokens (~1 -> /, ~0 -> ~)
        unescaped = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or unescaped not in current:
            raise ContractError(
                f"Failed to resolve local reference '{clean_ref}': token '{unescaped}' not found.",
                actionable_suggestion="Verify the pointer path matches the document structure.",
                context={"ref": clean_ref, "missing_token": unescaped},
            )
        current = current[unescaped]

    if not isinstance(current, dict):
        raise ContractError(
            f"Reference '{clean_ref}' did not resolve to a JSON object.",
            actionable_suggestion="Ensure referenced target is a schema object definition.",
            context={"ref": clean_ref},
        )

    # If the target is itself a reference, follow it
    if "$ref" in current:
        return resolve_local_ref(current["$ref"], root_doc, visited)

    return current


def parse_json_schema(
    schema_dict: dict[str, Any],
    contract_name: str = "json_schema_contract",
    version: str = "1.0.0",
    description: str | None = None,
    root_doc: dict[str, Any] | None = None,
) -> TargetContract:
    """Normalizes a JSON Schema (Draft-07 or 2020-12) into a TargetContract."""
    root = root_doc or schema_dict
    raw_props = schema_dict.get("properties")

    if not isinstance(raw_props, dict) or not raw_props:
        raise ContractError(
            f"JSON Schema for '{contract_name}' declares no properties.",
            actionable_suggestion="Declare a 'properties' object with at least one field definition.",
            context={"contract_name": contract_name},
        )

    required_set = set(schema_dict.get("required", []))
    parsed_fields: dict[str, TargetField] = {}

    for prop_name, prop_val in raw_props.items():
        if not isinstance(prop_val, dict):
            raise ContractError(
                f"Property definition for '{prop_name}' must be a JSON object.",
                actionable_suggestion="Check schema syntax for this property.",
                context={"property": prop_name},
            )

        # Resolve local reference if present
        resolved_prop = prop_val
        if "$ref" in prop_val:
            resolved_prop = resolve_local_ref(prop_val["$ref"], root)

        is_required = prop_name in required_set
        is_nullable = False

        raw_type = resolved_prop.get("type")
        target_type: ContractType | None = None

        # Handle type unions e.g. ["string", "null"] in 2020-12 / Draft-07
        if isinstance(raw_type, list):
            types_list = [str(t).lower() for t in raw_type]
            if "null" in types_list:
                is_nullable = True
                types_list = [t for t in types_list if t != "null"]
            if len(types_list) == 1:
                raw_type = types_list[0]
            elif len(types_list) == 0:
                raw_type = "string"
            else:
                raise ContractError(
                    f"Unsupported multi-type union {raw_type} on field '{prop_name}'.",
                    actionable_suggestion="Recon requires a single scalar target type per contract field.",
                    context={"property": prop_name, "types": raw_type},
                )
        elif isinstance(raw_type, str):
            raw_type = raw_type.lower()
        else:
            # Type might be implied by enum or format
            if "enum" in resolved_prop:
                raw_type = "string"
            else:
                raw_type = "string"

        # Check explicit nullable keyword (OpenAPI 3.0 / draft-07 extension)
        if resolved_prop.get("nullable") is True:
            is_nullable = True

        format_val = str(resolved_prop.get("format", "")).lower()

        if raw_type == "string":
            if format_val in ("date-time", "datetime"):
                target_type = ContractType.DATETIME
            elif format_val == "date":
                target_type = ContractType.DATE
            else:
                target_type = ContractType.STRING
        elif raw_type == "integer":
            target_type = ContractType.INTEGER
        elif raw_type in ("number", "float"):
            target_type = ContractType.FLOAT
        elif raw_type == "boolean":
            target_type = ContractType.BOOLEAN
        elif raw_type in ("array", "object"):
            raise ContractError(
                f"Complex nested type '{raw_type}' on field '{prop_name}' is not supported as a target field type.",
                actionable_suggestion="Flatten nested schemas or model target fields using scalar types: string, integer, float, boolean, datetime, date.",
                context={"property": prop_name, "type": raw_type},
            )
        else:
            raise ContractError(
                f"Unsupported schema type '{raw_type}' on field '{prop_name}'.",
                actionable_suggestion="Use supported scalar types: string, integer, float, boolean, datetime, date.",
                context={"property": prop_name, "type": raw_type},
            )

        # Allowed values (enums)
        allowed_values: list[str] | None = None
        if "enum" in resolved_prop and isinstance(resolved_prop["enum"], list):
            allowed_values = [str(v) for v in resolved_prop["enum"]]

        pattern = resolved_prop.get("pattern")
        if pattern is not None:
            pattern = str(pattern)

        min_val = resolved_prop.get("minimum")
        if min_val is not None:
            try:
                min_val = float(min_val)
            except (ValueError, TypeError):
                min_val = None

        max_val = resolved_prop.get("maximum")
        if max_val is not None:
            try:
                max_val = float(max_val)
            except (ValueError, TypeError):
                max_val = None

        prop_desc = resolved_prop.get("description")

        parsed_fields[prop_name] = TargetField(
            name=prop_name,
            target_type=target_type,
            required=is_required,
            nullable=is_nullable,
            allowed_values=allowed_values,
            pattern=pattern,
            min_value=min_val,
            max_value=max_val,
            description=prop_desc,
        )

    title = schema_dict.get("title") or contract_name
    desc = schema_dict.get("description") or description

    return TargetContract(
        contract_name=title,
        version=version,
        description=desc,
        fields=parsed_fields,
    )


def parse_openapi_contract(
    openapi_doc: dict[str, Any],
    schema_name: str | None = None,
) -> TargetContract:
    """Extracts and normalizes a target schema model from an OpenAPI 3.x document.

    If multiple models exist in components.schemas, schema_name must be explicitly specified.
    """
    schemas = openapi_doc.get("components", {}).get("schemas", {})
    if not isinstance(schemas, dict) or not schemas:
        raise ContractError(
            "No schema definitions found in OpenAPI document under 'components.schemas'.",
            actionable_suggestion="Declare at least one model schema under 'components.schemas'.",
            context={"openapi_version": openapi_doc.get("openapi")},
        )

    available_names = sorted(schemas.keys())

    if schema_name is not None and schema_name.strip():
        chosen_name = schema_name.strip()
        if chosen_name not in schemas:
            raise ContractError(
                f"Requested schema model '{chosen_name}' not found in OpenAPI components.schemas.",
                actionable_suggestion=f"Choose one of the available schemas: {', '.join(available_names)}",
                context={"requested_schema": chosen_name, "available_schemas": available_names},
            )
    else:
        # If single schema exists, auto-select
        if len(available_names) == 1:
            chosen_name = available_names[0]
        else:
            raise ContractError(
                f"Multiple schemas found in OpenAPI document: {', '.join(available_names)}. Explicit schema selection is required.",
                actionable_suggestion=f"Specify schema_name as one of: {', '.join(available_names)}",
                context={"available_schemas": available_names},
            )

    selected_schema = schemas[chosen_name]
    if not isinstance(selected_schema, dict):
        raise ContractError(
            f"Schema '{chosen_name}' in components.schemas is not an object.",
            actionable_suggestion="Ensure the schema declaration is a valid object.",
            context={"schema_name": chosen_name},
        )

    info = openapi_doc.get("info", {})
    doc_version = str(info.get("version", "1.0.0"))

    return parse_json_schema(
        schema_dict=selected_schema,
        contract_name=chosen_name,
        version=doc_version,
        description=selected_schema.get("description") or info.get("description"),
        root_doc=openapi_doc,
    )
