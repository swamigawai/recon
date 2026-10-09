"""Deterministic dataset profiler computing exact statistics, type inference, and anomalies."""

from datetime import datetime
from typing import Any

from recon.ingestion.models import RawDataset
from recon.logging import log_safe_event
from recon.profiling.models import ColumnProfile, SourceProfile
from recon.profiling.type_inference import infer_column_type

DEFAULT_NULL_TOKENS = {"", "null", "none", "nan", "n/a", "undefined"}


def is_null_value(val: Any, null_tokens: set[str]) -> bool:
    """Checks whether a value represents a null/missing value."""
    if val is None:
        return True
    if isinstance(val, (int, float, bool)):
        return False
    return str(val).strip().lower() in null_tokens


def profile_dataset(
    dataset: RawDataset,
    null_tokens: set[str] | None = None,
) -> SourceProfile:
    """Computes deterministic profile statistics from an ingested RawDataset.

    Calculates:
    - Row and column counts.
    - Exact duplicate row counts.
    - Null counts and percentages per column.
    - Distinct non-null value counts.
    - Inferred candidate data types with format patterns.
    - Value ranges (min / max).
    - Constant column detection.
    - Whitespace anomalies.
    - Safe sample values.
    """
    active_null_tokens = {t.lower() for t in (null_tokens or DEFAULT_NULL_TOKENS)}
    total_rows = dataset.row_count
    total_cols = len(dataset.headers)

    # 1. Detect exact duplicate rows
    row_tuples = [
        tuple(str(row.get(h, "")) if row.get(h) is not None else "" for h in dataset.headers)
        for row in dataset.rows
    ]
    unique_rows_count = len(set(row_tuples))
    duplicate_rows_count = total_rows - unique_rows_count

    columns: dict[str, ColumnProfile] = {}
    warnings: list[str] = list(dataset.warnings)

    # 2. Profile each column
    for col in dataset.headers:
        raw_values = [row.get(col) for row in dataset.rows]

        null_count = sum(1 for v in raw_values if is_null_value(v, active_null_tokens))
        null_pct = round((null_count / total_rows) * 100.0, 2) if total_rows > 0 else 0.0

        non_null_values = [v for v in raw_values if not is_null_value(v, active_null_tokens)]
        distinct_vals = set(non_null_values)
        distinct_count = len(distinct_vals)

        has_whitespace = any(isinstance(v, str) and v != v.strip() for v in raw_values if v is not None)

        # Detect constant columns
        is_constant = distinct_count == 1 and null_count == 0
        if is_constant:
            warnings.append(f"Column '{col}' is constant across all {total_rows} rows.")

        # Safe sample values: first 5 sorted unique non-null values
        sample_values = [str(x) for x in sorted(list(distinct_vals), key=lambda x: str(x))[:5]]

        # Type inference & range evaluation
        inferred_type, type_dist, formats, min_val, max_val = infer_column_type(non_null_values)

        columns[col] = ColumnProfile(
            name=col,
            inferred_type=inferred_type,
            total_count=total_rows,
            null_count=null_count,
            null_percentage=null_pct,
            distinct_count=distinct_count,
            min_value=min_val,
            max_value=max_val,
            sample_values=sample_values,
            is_constant=is_constant,
            has_whitespace_anomalies=has_whitespace,
            format_patterns=formats,
            type_distribution=type_dist,
        )

    profile = SourceProfile(
        source_name=dataset.file_name,
        fingerprint=dataset.fingerprint,
        total_rows=total_rows,
        total_columns=total_cols,
        duplicate_rows_count=duplicate_rows_count,
        columns=columns,
        profiling_timestamp=datetime.utcnow(),
        warnings=warnings,
    )

    log_safe_event(
        "DATASET_PROFILED",
        source=dataset.file_name,
        rows=total_rows,
        columns=total_cols,
        duplicates=duplicate_rows_count,
    )

    return profile
