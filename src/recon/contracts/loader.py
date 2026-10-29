"""Loader and validator for target contracts supporting Native Recon, JSON Schema, OpenAPI 3.x, and CSV/TSV Schema/Data."""

import io
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.contracts.universal import (
    ContractFormat,
    detect_contract_format,
    parse_json_schema,
    parse_openapi_contract,
)
from recon.exceptions import ContractError
from recon.ingestion.loader import load_dataset
from recon.profiling.models import InferredType
from recon.profiling.profiler import profile_dataset


def load_csv_contract(path: Path) -> TargetContract:
    """Loads and derives a TargetContract from a CSV/TSV data dictionary or sample dataset file.

    Supports:
      1. Schema Data Dictionaries: CSV with columns like (name/field, type, required, description)
      2. Target Sample Datasets: Any CSV file representing the target format, with profiling
      3. Header-only Templates: CSV with zero rows, inferring fields from header tokens
    """
    try:
        dataset = load_dataset(path)
    except Exception as exc:
        raise ContractError(
            f"Failed to ingest target contract CSV '{path.name}': {exc}",
            actionable_suggestion="Verify the CSV file formatting, encoding, and permissions.",
            context={"file_path": str(path)},
        ) from exc

    if not dataset.headers:
        raise ContractError(
            f"Target contract CSV '{path.name}' contains no header columns.",
            actionable_suggestion="Ensure the CSV file contains a valid header row.",
            context={"file_path": str(path)},
        )

    # Check for Schema / Data Dictionary CSV format
    header_lower_map = {h.strip().lower(): h for h in dataset.headers}
    name_col = None
    for cand in ("name", "field", "field_name", "column", "column_name", "target_field", "attribute", "property"):
        if cand in header_lower_map:
            name_col = header_lower_map[cand]
            break

    type_col = None
    for cand in ("type", "target_type", "data_type", "datatype", "dtype", "col_type"):
        if cand in header_lower_map:
            type_col = header_lower_map[cand]
            break

    # If both name and type column exist and we have rows, treat as a Data Dictionary CSV
    if name_col and type_col and dataset.rows:
        req_col = None
        for cand in ("required", "mandatory", "is_required", "nullable"):
            if cand in header_lower_map:
                req_col = header_lower_map[cand]
                break

        enum_col = None
        for cand in ("allowed_values", "enum", "values", "choices", "enums"):
            if cand in header_lower_map:
                enum_col = header_lower_map[cand]
                break

        desc_col = None
        for cand in ("description", "desc", "comment", "notes", "definition"):
            if cand in header_lower_map:
                desc_col = header_lower_map[cand]
                break

        pattern_col = None
        for cand in ("pattern", "regex", "format"):
            if cand in header_lower_map:
                pattern_col = header_lower_map[cand]
                break

        min_col = None
        for cand in ("min", "min_value", "minimum"):
            if cand in header_lower_map:
                min_col = header_lower_map[cand]
                break

        max_col = None
        for cand in ("max", "max_value", "maximum"):
            if cand in header_lower_map:
                max_col = header_lower_map[cand]
                break

        fields: dict[str, TargetField] = {}
        for row in dataset.rows:
            f_name = str(row.get(name_col, "")).strip()
            if not f_name:
                continue

            raw_t = str(row.get(type_col, "")).strip().lower()
            if any(k in raw_t for k in ("int", "integer", "bigint", "smallint")):
                target_type = ContractType.INTEGER
            elif any(k in raw_t for k in ("float", "double", "decimal", "numeric", "real", "number")):
                target_type = ContractType.FLOAT
            elif "bool" in raw_t:
                target_type = ContractType.BOOLEAN
            elif any(k in raw_t for k in ("datetime", "timestamp")):
                target_type = ContractType.DATETIME
            elif "date" in raw_t:
                target_type = ContractType.DATE
            else:
                target_type = ContractType.STRING

            if req_col:
                val = str(row.get(req_col, "")).strip().lower()
                if req_col.lower() == "nullable":
                    required = not (val in ("true", "1", "yes", "t"))
                    nullable = val in ("true", "1", "yes", "t")
                else:
                    required = val in ("true", "1", "yes", "t", "required")
                    nullable = not required
            else:
                required = True
                nullable = False

            allowed_values = None
            if enum_col:
                raw_enum = str(row.get(enum_col, "")).strip()
                if raw_enum.startswith("[") and raw_enum.endswith("]"):
                    try:
                        allowed_values = json.loads(raw_enum)
                    except Exception:
                        allowed_values = [v.strip().strip("'\"") for v in raw_enum.strip("[]").split(",") if v.strip()]
                elif raw_enum:
                    allowed_values = [v.strip().strip("'\"") for v in re.split(r"[,;|]", raw_enum) if v.strip()]

            desc = str(row.get(desc_col, "")).strip() if desc_col and row.get(desc_col) else None
            pattern = str(row.get(pattern_col, "")).strip() if pattern_col and row.get(pattern_col) else None

            min_val = None
            if min_col and row.get(min_col) is not None:
                try:
                    min_val = float(str(row.get(min_col)).strip())
                except (ValueError, TypeError):
                    pass

            max_val = None
            if max_col and row.get(max_col) is not None:
                try:
                    max_val = float(str(row.get(max_col)).strip())
                except (ValueError, TypeError):
                    pass

            fields[f_name] = TargetField(
                name=f_name,
                target_type=target_type,
                required=required,
                nullable=nullable,
                allowed_values=allowed_values,
                pattern=pattern,
                min_value=min_val,
                max_value=max_val,
                description=desc or f"Target field '{f_name}' from data dictionary CSV.",
            )

        if not fields:
            raise ContractError(
                f"Data dictionary CSV '{path.name}' declared no valid field rows.",
                actionable_suggestion="Check that rows have non-empty field names.",
                context={"file_path": str(path)},
            )

        return TargetContract(
            contract_name=path.stem,
            version="1.0.0",
            description=f"Target contract derived from data dictionary CSV: {path.name}",
            fields=fields,
        )

    # Otherwise, treat as Target Dataset / Sample CSV (profile rows or infer from headers)
    if dataset.rows:
        profile = profile_dataset(dataset)
        fields = {}
        for col_name in dataset.headers:
            col_prof = profile.columns.get(col_name)
            if col_prof:
                target_type = ContractType(col_prof.inferred_type.value)
                required = (col_prof.null_count == 0)
                nullable = (col_prof.null_count > 0)
                allowed = None
                if 0 < col_prof.distinct_count <= 8 and profile.total_rows >= 10:
                    allowed = sorted([str(s) for s in col_prof.sample_values if s])

                min_val = None
                max_val = None
                if col_prof.inferred_type in (InferredType.INTEGER, InferredType.FLOAT):
                    if col_prof.min_value is not None:
                        try:
                            min_val = float(col_prof.min_value)
                        except (ValueError, TypeError):
                            pass
                    if col_prof.max_value is not None:
                        try:
                            max_val = float(col_prof.max_value)
                        except (ValueError, TypeError):
                            pass

                fields[col_name] = TargetField(
                    name=col_name,
                    target_type=target_type,
                    required=required,
                    nullable=nullable,
                    allowed_values=allowed,
                    min_value=min_val,
                    max_value=max_val,
                    description=f"Target field '{col_name}' inferred from target dataset ({col_prof.inferred_type.value}).",
                )
            else:
                fields[col_name] = TargetField(
                    name=col_name,
                    target_type=ContractType.STRING,
                    required=True,
                    nullable=False,
                    description=f"Target field '{col_name}' from target CSV template.",
                )
    else:
        # Header template with zero rows
        fields = {}
        for col_name in dataset.headers:
            clean_name = col_name.strip()
            if not clean_name:
                continue
            lower = clean_name.lower()
            if lower.endswith(("_at", "_date", "date", "timestamp", "time")) or lower in ("date", "datetime", "timestamp"):
                t = ContractType.DATETIME if ("time" in lower or "_at" in lower) else ContractType.DATE
            elif lower in ("amount", "price", "fee", "cost", "total", "rate", "pct", "percent") or lower.endswith(("_amount", "_price", "_fee", "_cost", "_total", "_rate", "_pct", "_percent", "price", "fee", "cost", "total")):
                t = ContractType.FLOAT
            elif lower in ("qty", "quantity", "count", "number") or lower.endswith(("_count", "_num", "_qty", "quantity", "number")):
                t = ContractType.INTEGER
            elif lower.startswith("is_") or lower.startswith("has_"):
                t = ContractType.BOOLEAN
            else:
                t = ContractType.STRING

            fields[clean_name] = TargetField(
                name=clean_name,
                target_type=t,
                required=True,
                nullable=False,
                description=f"Target field '{clean_name}' declared in target CSV template.",
            )

    return TargetContract(
        contract_name=path.stem,
        version="1.0.0",
        description=f"Target contract dynamically generated from CSV: {path.name}",
        fields=fields,
    )


def load_target_contract(
    contract_path_or_dict: str | Path | dict[str, Any],
    schema_name: str | None = None,
) -> TargetContract:
    """Loads, validates, and normalizes a target contract from Native Recon, JSON Schema, OpenAPI, or CSV formats.

    Args:
        contract_path_or_dict: File path (.json, .csv, .tsv), raw JSON/CSV string, or in-memory dictionary.
        schema_name: Optional explicit schema model name when loading multi-schema OpenAPI documents.

    Returns:
        TargetContract: Normalized internal target contract.

    Raises:
        ContractError: If the file is missing, invalid JSON/CSV, or fails schema validation.
    """
    if isinstance(contract_path_or_dict, dict):
        raw_data = contract_path_or_dict
        source_label = "<dictionary>"
        contract_stem = "contract"
    elif isinstance(contract_path_or_dict, str) and contract_path_or_dict.strip().lstrip("\ufeff").startswith("{"):
        source_label = "<json_string>"
        contract_stem = "contract"
        clean_json_str = contract_path_or_dict.strip().lstrip("\ufeff")
        try:
            raw_data = json.loads(clean_json_str)
        except json.JSONDecodeError as exc:
            raise ContractError(
                f"Malformed JSON in contract string: {exc.msg} (line {exc.lineno}, col {exc.colno})",
                actionable_suggestion="Check JSON syntax, trailing commas, or unescaped characters.",
                context={"line": exc.lineno, "column": exc.colno},
            ) from exc
    else:
        path = Path(contract_path_or_dict)
        if not path.exists():
            # If string contains newlines or commas, treat as raw CSV text
            if isinstance(contract_path_or_dict, str) and ("," in contract_path_or_dict or "\n" in contract_path_or_dict):
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".csv", delete=False) as tf:
                    tf.write(contract_path_or_dict.strip().lstrip("\ufeff"))
                    temp_csv_path = Path(tf.name)
                try:
                    return load_csv_contract(temp_csv_path)
                finally:
                    try:
                        temp_csv_path.unlink()
                    except Exception:
                        pass

            raise ContractError(
                f"Target contract file not found: {path}",
                actionable_suggestion="Verify the target contract file path and ensure it exists.",
                context={"file_path": str(path)},
            )

        source_label = str(path)
        contract_stem = path.stem
        suffix = path.suffix.lower()

        # Handle CSV / TSV / tabular target contracts
        if suffix in (".csv", ".tsv"):
            return load_csv_contract(path)

        # Handle JSON / OpenAPI contracts (with rigorous BOM stripping)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read().lstrip("\ufeff")
                raw_data = json.loads(content)
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
        actionable_suggestion="Provide a Native Recon contract, JSON Schema, OpenAPI 3.x, or CSV file.",
    )
