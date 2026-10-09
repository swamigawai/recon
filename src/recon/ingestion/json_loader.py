"""Deterministic JSON dataset loader with flattening, envelope extraction, and structural validation."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from recon.exceptions import IngestionError
from recon.ingestion.csv_loader import calculate_file_hash, detect_file_encoding
from recon.ingestion.models import IngestionConfig, RawDataset
from recon.logging import log_safe_event

COMMON_ENVELOPE_KEYS = ("data", "items", "results", "records", "rows")


def flatten_json_record(
    data: dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> dict[str, Any]:
    """Recursively flattens nested dictionary keys using dot notation (e.g. address.city)."""
    items: list[tuple[str, Any]] = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
        if isinstance(v, dict):
            items.extend(flatten_json_record(v, parent_key=new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def extract_records_from_json(payload: Any, file_name: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Extracts a flat list of record dictionaries and warnings from arbitrary JSON payloads."""
    warnings: list[str] = []

    if isinstance(payload, list):
        if not payload:
            raise IngestionError(
                f"JSON array contains zero records in {file_name}",
                actionable_suggestion="Ensure the JSON file contains at least one object record.",
                context={"file_name": file_name},
            )
        # Verify elements are objects
        if not all(isinstance(elem, dict) for elem in payload):
            raise IngestionError(
                f"JSON array elements must be objects in {file_name}",
                actionable_suggestion="Ensure the JSON array contains structured dictionary records, not scalar primitives.",
                context={"file_name": file_name},
            )
        raw_records = payload

    elif isinstance(payload, dict):
        # Check for enveloped list
        enveloped_list = None
        for key in COMMON_ENVELOPE_KEYS:
            if key in payload and isinstance(payload[key], list) and payload[key]:
                if all(isinstance(item, dict) for item in payload[key]):
                    enveloped_list = payload[key]
                    warnings.append(f"Extracted {len(enveloped_list)} records from envelope key '{key}'")
                    break

        if enveloped_list is not None:
            raw_records = enveloped_list
        else:
            # Single object document -> 1 row dataset
            raw_records = [payload]
            warnings.append("Ingested single JSON object document as a 1-record dataset")

    else:
        raise IngestionError(
            f"Unsupported JSON root shape in {file_name}: expected array of objects or object, got {type(payload).__name__}",
            actionable_suggestion="Format the JSON source as an array of object records or an enveloped object.",
            context={"root_type": type(payload).__name__, "file_name": file_name},
        )

    # Flatten nested structures
    flattened_records = [flatten_json_record(rec) for rec in raw_records]
    return flattened_records, warnings


def load_json(file_path: str | Path, config: IngestionConfig | None = None) -> RawDataset:
    """Loads and validates a JSON file into an immutable RawDataset model.

    Features:
    1. Safe path resolution and size checking.
    2. Deterministic streaming SHA-256 fingerprinting.
    3. Detailed JSON syntax error diagnostics.
    4. Envelope unwrapping (`data`, `items`, `results`).
    5. Automatic dot-notation flattening of nested structures (`address.city`).
    6. Union header discovery across heterogeneous objects.
    """
    cfg = config or IngestionConfig()
    path = Path(file_path).resolve()

    if not path.exists():
        raise IngestionError(
            f"Source file not found: {path}",
            actionable_suggestion="Verify the source file path and ensure the file exists.",
            context={"file_path": str(path)},
        )

    if not path.is_file():
        raise IngestionError(
            f"Path is not a regular file: {path}",
            actionable_suggestion="Provide a path pointing directly to a JSON file.",
            context={"file_path": str(path)},
        )

    file_size = path.stat().st_size
    if file_size == 0:
        raise IngestionError(
            f"Source JSON file is completely empty (0 bytes): {path.name}",
            actionable_suggestion="Ensure the file was not created as an empty placeholder.",
            context={"file_path": str(path), "size_bytes": 0},
        )

    if file_size > cfg.max_file_size_bytes:
        raise IngestionError(
            f"File size ({file_size} bytes) exceeds maximum configured limit of {cfg.max_file_size_bytes} bytes",
            actionable_suggestion="Increase IngestionConfig.max_file_size_bytes or sample the dataset.",
            context={"file_size": file_size, "limit": cfg.max_file_size_bytes},
        )

    fingerprint = calculate_file_hash(path)
    encoding = cfg.encoding or detect_file_encoding(path)

    try:
        with open(path, "r", encoding=encoding) as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise IngestionError(
            f"Malformed JSON in {path.name}: {exc.msg} (line {exc.lineno}, col {exc.colno})",
            actionable_suggestion="Check JSON syntax, trailing commas, or unescaped characters in the source file.",
            context={
                "file_path": str(path),
                "line_number": exc.lineno,
                "column_number": exc.colno,
                "error": exc.msg,
            },
        ) from exc

    records, warnings = extract_records_from_json(payload, path.name)

    if cfg.max_rows and len(records) > cfg.max_rows:
        records = records[: cfg.max_rows]
        warnings.append(f"Ingestion truncated at {cfg.max_rows} rows limit")

    # Discover union of all headers across records, preserving first observed order
    ordered_headers: list[str] = []
    seen_headers: set[str] = set()

    for rec in records:
        for key in rec.keys():
            if key not in seen_headers:
                seen_headers.add(key)
                ordered_headers.append(key)

    # Validate header presence
    if not ordered_headers or all(not h.strip() for h in ordered_headers):
        raise IngestionError(
            f"No valid attributes found across JSON records in {path.name}",
            actionable_suggestion="Ensure JSON objects contain at least one non-empty attribute key.",
            context={"file_path": str(path)},
        )

    # Check for empty header keys
    for idx, h in enumerate(ordered_headers, start=1):
        if not h.strip():
            raise IngestionError(
                f"Empty or blank attribute key found at index {idx} in {path.name}",
                actionable_suggestion="Rename empty JSON keys to meaningful non-empty names.",
                context={"column_index": idx, "file_path": str(path)},
            )

    # Check for duplicate headers
    header_counts = Counter(ordered_headers)
    duplicates = [name for name, count in header_counts.items() if count > 1]
    if duplicates:
        raise IngestionError(
            f"Duplicate attribute keys detected in {path.name}: {duplicates}",
            actionable_suggestion="Ensure attribute keys are unique across the schema.",
            context={"duplicate_headers": duplicates, "file_path": str(path)},
        )

    dataset = RawDataset(
        file_path=str(path),
        file_name=path.name,
        fingerprint=fingerprint,
        file_size_bytes=file_size,
        encoding=encoding,
        headers=ordered_headers,
        row_count=len(records),
        rows=records,
        warnings=warnings,
    )

    log_safe_event(
        "DATASET_INGESTED",
        file_name=path.name,
        format="json",
        rows=len(records),
        columns=len(ordered_headers),
        fingerprint_prefix=fingerprint[:12],
    )

    return dataset
