"""Loader and validator for target contracts."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from recon.contracts.models import TargetContract
from recon.exceptions import ContractError


def load_target_contract(contract_path_or_dict: str | Path | dict[str, Any]) -> TargetContract:
    """Loads and validates a target contract from a JSON file path or dictionary.

    Raises:
        ContractError: If the file is missing, invalid JSON, or fails schema validation.
    """
    if isinstance(contract_path_or_dict, dict):
        raw_data = contract_path_or_dict
        source_label = "<dictionary>"
    else:
        path = Path(contract_path_or_dict)
        source_label = str(path)
        if not path.exists():
            raise ContractError(
                f"Target contract file not found: {path}",
                actionable_suggestion="Verify the target contract file path and ensure it exists.",
                context={"file_path": str(path)},
            )
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ContractError(
                f"Malformed JSON in contract file: {exc.msg} (line {exc.lineno}, col {exc.colno})",
                actionable_suggestion="Check JSON syntax, trailing commas, or unescaped characters in the contract file.",
                context={"file_path": str(path), "line": exc.lineno, "column": exc.colno},
            ) from exc

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
