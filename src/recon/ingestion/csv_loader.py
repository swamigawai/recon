"""Deterministic CSV loader with encoding detection, structural validation, and fingerprinting."""

import csv
import hashlib
from collections import Counter
from pathlib import Path

from recon.exceptions import IngestionError
from recon.ingestion.models import IngestionConfig, RawDataset
from recon.logging import log_safe_event


def calculate_file_hash(path: Path) -> str:
    """Computes SHA-256 hexadecimal digest of a file in 64KB streaming chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def detect_file_encoding(path: Path, candidate_encodings: list[str] | None = None) -> str:
    """Detects encoding by testing candidate encodings against raw bytes."""
    candidates = candidate_encodings or ["utf-8", "utf-8-sig", "latin1", "cp1252"]
    for enc in candidates:
        try:
            with open(path, "r", encoding=enc) as f:
                # Read first 128KB to verify decodability
                f.read(131072)
            return enc
        except UnicodeDecodeError:
            continue
    raise IngestionError(
        f"Unable to decode file with tested encodings: {candidates}",
        actionable_suggestion="Specify an explicit encoding in IngestionConfig or convert file to UTF-8.",
        context={"tested_encodings": candidates, "file_path": str(path)},
    )


def load_csv(file_path: str | Path, config: IngestionConfig | None = None) -> RawDataset:
    """Loads and validates a CSV file into an immutable RawDataset model.

    Performs:
    1. Path validation & existence checks.
    2. File size ceiling checks.
    3. Empty file detection.
    4. Deterministic SHA-256 fingerprinting.
    5. Encoding validation.
    6. Header integrity (no missing, blank, or duplicate headers).
    7. Row width consistency (detects malformed/ragged rows).

    Raises:
        IngestionError: If the file is missing, empty, malformed, or exceeds size limits.
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
            actionable_suggestion="Provide a path pointing directly to a CSV file.",
            context={"file_path": str(path)},
        )

    file_size = path.stat().st_size
    if file_size == 0:
        raise IngestionError(
            f"Source CSV file is completely empty (0 bytes): {path.name}",
            actionable_suggestion="Ensure the file was not truncated or created as an empty placeholder.",
            context={"file_path": str(path), "size_bytes": 0},
        )

    if file_size > cfg.max_file_size_bytes:
        raise IngestionError(
            f"File size ({file_size} bytes) exceeds maximum configured limit of {cfg.max_file_size_bytes} bytes",
            actionable_suggestion="Increase IngestionConfig.max_file_size_bytes or sample the dataset.",
            context={"file_size": file_size, "limit": cfg.max_file_size_bytes},
        )

    # 1. Compute deterministic SHA-256 fingerprint
    fingerprint = calculate_file_hash(path)

    # 2. Resolve encoding
    encoding = cfg.encoding or detect_file_encoding(path)

    # 3. Read and validate structure
    warnings: list[str] = []
    rows: list[dict[str, str]] = []
    headers: list[str] = []

    try:
        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.reader(f)

            try:
                raw_headers = next(reader)
            except StopIteration:
                raise IngestionError(
                    f"File contains no data rows or headers: {path.name}",
                    actionable_suggestion="Check that the CSV file contains a valid header row.",
                    context={"file_path": str(path)},
                )

            # Validate header presence and whitespace
            if not raw_headers or all(not h.strip() for h in raw_headers):
                raise IngestionError(
                    f"CSV header row is empty in {path.name}",
                    actionable_suggestion="Provide a CSV with non-empty column names in row 1.",
                    context={"file_path": str(path)},
                )

            # Check for empty header fields
            for idx, h in enumerate(raw_headers, start=1):
                if not h.strip():
                    raise IngestionError(
                        f"Empty or blank column header found at column {idx} in {path.name}",
                        actionable_suggestion="Ensure all columns in the header row have meaningful, non-empty names.",
                        context={"column_index": idx, "file_path": str(path)},
                    )

            # Check for duplicate headers
            header_counts = Counter(raw_headers)
            duplicates = [name for name, count in header_counts.items() if count > 1]
            if duplicates:
                raise IngestionError(
                    f"Duplicate column headers detected in {path.name}: {duplicates}",
                    actionable_suggestion="Rename duplicate columns in the source file so every header is unique.",
                    context={"duplicate_headers": duplicates, "file_path": str(path)},
                )

            # Check for whitespace in headers (record as warning)
            whitespace_headers = [h for h in raw_headers if h != h.strip()]
            if whitespace_headers:
                warnings.append(
                    f"Headers with leading/trailing whitespace detected: {whitespace_headers}"
                )

            headers = raw_headers
            expected_col_count = len(headers)

            # Read rows and check row width consistency
            line_num = 1
            for row in reader:
                line_num += 1
                if not row:
                    # Skip completely empty lines
                    continue

                if len(row) != expected_col_count:
                    if cfg.strict_row_counts:
                        raise IngestionError(
                            f"Malformed row at line {line_num} in {path.name}: expected {expected_col_count} columns, found {len(row)}",
                            actionable_suggestion="Inspect line in source file for unescaped quotes or delimiter mismatches.",
                            context={
                                "line_number": line_num,
                                "expected_columns": expected_col_count,
                                "found_columns": len(row),
                                "file_path": str(path),
                            },
                        )
                    else:
                        warnings.append(
                            f"Row at line {line_num} has {len(row)} columns (expected {expected_col_count})"
                        )
                        continue

                rows.append(dict(zip(headers, row)))

                if cfg.max_rows and len(rows) >= cfg.max_rows:
                    warnings.append(f"Ingestion truncated at {cfg.max_rows} rows limit")
                    break

    except UnicodeDecodeError as exc:
        raise IngestionError(
            f"Encoding error while reading {path.name} with encoding {encoding}: {exc.reason}",
            actionable_suggestion="Ensure the source file encoding matches the configured encoding.",
            context={"file_path": str(path), "encoding": encoding, "error": str(exc)},
        ) from exc
    except csv.Error as exc:
        raise IngestionError(
            f"CSV parsing error in {path.name}: {exc}",
            actionable_suggestion="Verify CSV quoting, delimiter consistency, and escaping.",
            context={"file_path": str(path), "error": str(exc)},
        ) from exc

    dataset = RawDataset(
        file_path=str(path),
        file_name=path.name,
        fingerprint=fingerprint,
        file_size_bytes=file_size,
        encoding=encoding,
        headers=headers,
        row_count=len(rows),
        rows=rows,
        warnings=warnings,
    )

    log_safe_event(
        "DATASET_INGESTED",
        file_name=path.name,
        rows=len(rows),
        columns=len(headers),
        fingerprint_prefix=fingerprint[:12],
    )

    return dataset
