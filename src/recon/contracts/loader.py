"""Loader and validator for target contracts supporting Native, JSON Schema, and OpenAPI 3.x."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from recon.contracts.models import TargetContract
from recon.contracts.universal import (
    ContractFormat,
    detect_contract_format,
    parse_json_schema,
    parse_openapi_contract,
)
from recon.exceptions import ContractError


def load_target_contract(
    contract_path_or_dict: str | Path | dict[str, Any],
    schema_name: str | None = None,
) -> TargetContract:
    """Loads, validates, and normalizes a target contract from Native Recon, JSON Schema, or OpenAPI formats.

    Args:
        contract_path_or_dict: JSON file path or in-memory dictionary.
        schema_name: Optional explicit schema model name when loading multi-schema OpenAPI documents.

    Returns:
        TargetContract: Normalized internal target contract.

    Raises:
        ContractError: If the file is missing, invalid JSON, or fails schema validation.
    """
    if isinstance(contract_path_or_dict, dict):
        raw_data = contract_path_or_dict
        source_label = "<dictionary>"
        contract_stem = "contract"
    else:
        path = Path(contract_path_or_dict)
        source_label = str(path)
        contract_stem = path.stem
        if not path.exists():
            raise ContractError(
                f"Target contract file not found: {path}",
                actionable_suggestion="Verify the target contract file path and ensure it exists.",
                context={"file_path": str(path)},
            )
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ContractError(
                f"Malformed JSON in contract file: {exc.msg} (line {exc.lineno}, col {exc.colno})",
                actionable_suggestion="Check JSON syntax, trailing commas, or unescaped characters in the contract file.",
                context={"file_path": str(path), "line": exc.lineno, "column": exc.colno},
            ) from exc

    # Deterministically detect contract format
    fmt, _ = detect_contract_format(raw_data)

    if fmt == ContractFormat.NATIVE:
        try:
            return TargetContract.model_validate(raw_data)
        except PydanticValidationError as exc:
            errors = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()]
            err_msg = "; ".join(errors)
            raise ContractError(
                f"Invalid target contract schema in {source_label}: {err_msg}",
                actionable_suggestion="Update the contract JSON to match the required TargetContract specification.",
                context={"source": source_label, "validation_errors": errors},
            ) from exc

    elif fmt in (ContractFormat.JSON_SCHEMA_DRAFT_07, ContractFormat.JSON_SCHEMA_2020_12):
        return parse_json_schema(
            raw_data,
            contract_name=raw_data.get("title") or contract_stem,
        )

    elif fmt == ContractFormat.OPENAPI_3:
        return parse_openapi_contract(
            raw_data,
            schema_name=schema_name,
        )

    raise ContractError(
        f"Unsupported contract format: {fmt}",
        actionable_suggestion="Provide a Native Recon contract, JSON Schema, or OpenAPI 3.x document.",
    )
