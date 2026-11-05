"""Deterministic Excel (.xlsx / .xlsm) dataset loader with sheet inspection, type normalization, and fingerprinting."""

from collections import Counter
import datetime
from pathlib import Path
from typing import Any
import zipfile

try:
    import openpyxl
    from openpyxl.utils.exceptions import InvalidFileException
except ImportError:
    openpyxl = None
    InvalidFileException = Exception

from recon.exceptions import IngestionError
from recon.ingestion.csv_loader import calculate_file_hash
from recon.ingestion.models import IngestionConfig, RawDataset
from recon.logging import log_safe_event


def _normalize_cell_value(val: Any) -> Any:
    """Normalizes an Excel cell value into clean, deterministic types for profiling & mapping."""
    if val is None:
        return ""
    if isinstance(val, datetime.datetime):
        if val.time() == datetime.time(0, 0, 0):
            return val.strftime("%Y-%m-%d")
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, datetime.date):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, datetime.time):
        return val.strftime("%H:%M:%S")
    if isinstance(val, float):
        if val.is_integer() and abs(val) < 1e15:
            return int(val)
        return val
    if isinstance(val, str):
        return val.strip()
    return val


def load_excel(file_path: str | Path, config: IngestionConfig | None = None) -> RawDataset:
    """Loads and validates an Excel (.xlsx / .xlsm) workbook into an immutable RawDataset model.

    Performs:
    1. Path validation & existence checks.
    2. File size ceiling checks.
    3. Empty file detection.
    4. Deterministic SHA-256 fingerprinting.
    5. Sheet selection (primary/active sheet with multi-sheet warning).
    6. Header integrity (no missing, blank, or duplicate headers; trims trailing blank columns).
    7. Row width consistency.
    8. Cell value normalization (dates to ISO, integer floats, whitespace trimming).

    Raises:
        IngestionError: If the file is missing, empty, malformed, or exceeds size limits.
    """
    if openpyxl is None:
        raise IngestionError(
            "Excel file ingestion requires the 'openpyxl' package.",
            actionable_suggestion="Install openpyxl via 'pip install openpyxl' or ensure dev dependencies are installed.",
            context={"file_path": str(file_path)},
        )

    cfg = config or IngestionConfig()
    path = Path(file_path).resolve()

    if not path.exists():
        raise IngestionError(
            f"Source Excel file not found: {path}",
            actionable_suggestion="Verify the source file path and ensure the file exists.",
            context={"file_path": str(path)},
        )

    if not path.is_file():
        raise IngestionError(
            f"Path is not a regular file: {path}",
            actionable_suggestion="Provide a path pointing directly to an Excel (.xlsx) file.",
            context={"file_path": str(path)},
        )

    file_size = path.stat().st_size
    if file_size == 0:
        raise IngestionError(
            f"Source Excel file is completely empty (0 bytes): {path.name}",
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

    # 2. Open workbook with openpyxl
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except zipfile.BadZipFile as exc:
        raise IngestionError(
            f"Corrupted or invalid Excel file: {path.name} (failed ZIP archive verification)",
            actionable_suggestion="Ensure the file is a valid, uncorrupted Excel (.xlsx) document.",
            context={"file_path": str(path), "error": str(exc)},
        ) from exc
    except InvalidFileException as exc:
        raise IngestionError(
            f"Invalid Excel file format for {path.name}: {exc}",
            actionable_suggestion="Ensure the file is a modern .xlsx or .xlsm workbook. Legacy .xls binary files must be converted.",
            context={"file_path": str(path), "error": str(exc)},
        ) from exc
    except Exception as exc:
        raise IngestionError(
            f"Failed to load Excel workbook {path.name}: {exc}",
            actionable_suggestion="Check file permissions and verify the workbook is not encrypted with a password.",
            context={"file_path": str(path), "error": str(exc)},
        ) from exc

    warnings: list[str] = []

    try:
        sheet_names = wb.sheetnames
        if not sheet_names:
            raise IngestionError(
                f"Excel workbook contains zero sheets: {path.name}",
                actionable_suggestion="Ensure the workbook contains at least one worksheet with data.",
                context={"file_path": str(path)},
            )

        active_sheet = wb.active or wb[sheet_names[0]]
        if len(sheet_names) > 1:
            warnings.append(
                f"Multiple sheets detected in {path.name} ({len(sheet_names)} total: {sheet_names}). "
                f"Ingested active sheet '{active_sheet.title}'."
            )

        # 3. Read rows from worksheet
        raw_rows_iter = active_sheet.iter_rows(values_only=True)

        raw_headers = None
        for r in raw_rows_iter:
            # Skip completely blank leading rows
            if r is not None and any(c is not None and str(c).strip() != "" for c in r):
                raw_headers = list(r)
                break

        if raw_headers is None:
            raise IngestionError(
                f"Excel worksheet contains no data rows or headers: {path.name}",
                actionable_suggestion="Check that the Excel worksheet contains a valid header row.",
                context={"file_path": str(path), "sheet_name": active_sheet.title},
            )

        # Trim trailing None/empty column headers
        while raw_headers and (raw_headers[-1] is None or str(raw_headers[-1]).strip() == ""):
            raw_headers.pop()

        if not raw_headers:
            raise IngestionError(
                f"Excel header row is empty in {path.name}",
                actionable_suggestion="Provide an Excel file with non-empty column names in the first data row.",
                context={"file_path": str(path), "sheet_name": active_sheet.title},
            )

        headers: list[str] = []
        for idx, h in enumerate(raw_headers, start=1):
            if h is None or not str(h).strip():
                raise IngestionError(
                    f"Empty or blank column header found at column {idx} in {path.name}",
                    actionable_suggestion="Ensure all columns in the header row have meaningful, non-empty names.",
                    context={"column_index": idx, "file_path": str(path), "sheet_name": active_sheet.title},
                )
            headers.append(str(h).strip())

        # Check for duplicate headers
        header_counts = Counter(headers)
        duplicates = [name for name, count in header_counts.items() if count > 1]
        if duplicates:
            raise IngestionError(
                f"Duplicate column headers detected in {path.name}: {duplicates}",
                actionable_suggestion="Rename duplicate columns in the source spreadsheet so every header is unique.",
                context={"duplicate_headers": duplicates, "file_path": str(path), "sheet_name": active_sheet.title},
            )

        expected_cols = len(headers)
        rows: list[dict[str, Any]] = []
        line_num = 1

        for raw_row in raw_rows_iter:
            line_num += 1
            if raw_row is None:
                continue

            # Convert row tuple to list
            row_vals = list(raw_row)

            # Check if row is completely empty
            if all(v is None or str(v).strip() == "" for v in row_vals):
                continue

            # Handle column width mismatch
            if len(row_vals) < expected_cols:
                row_vals.extend([""] * (expected_cols - len(row_vals)))
            elif len(row_vals) > expected_cols:
                extra = row_vals[expected_cols:]
                if any(v is not None and str(v).strip() != "" for v in extra):
                    if cfg.strict_row_counts:
                        raise IngestionError(
                            f"Malformed row at line {line_num} in {path.name}: expected {expected_cols} columns, found {len(row_vals)}",
                            actionable_suggestion="Check the spreadsheet for extra cells beyond the declared headers.",
                            context={
                                "line_number": line_num,
                                "expected_columns": expected_cols,
                                "found_columns": len(row_vals),
                                "file_path": str(path),
                            },
                        )
                    else:
                        warnings.append(
                            f"Row at line {line_num} has {len(row_vals)} columns (expected {expected_cols})"
                        )
                row_vals = row_vals[:expected_cols]

            normalized_vals = [_normalize_cell_value(v) for v in row_vals]
            rows.append(dict(zip(headers, normalized_vals)))

            if cfg.max_rows and len(rows) >= cfg.max_rows:
                warnings.append(f"Ingestion truncated at {cfg.max_rows} rows limit")
                break

    finally:
        wb.close()

    dataset = RawDataset(
        file_path=str(path),
        file_name=path.name,
        fingerprint=fingerprint,
        file_size_bytes=file_size,
        encoding="binary/xlsx",
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
        format="xlsx",
    )

    return dataset
