"""Deterministic candidate type inference for raw string columns."""

from datetime import datetime
from typing import Any

from recon.profiling.models import InferredType

# Explicit, ordered list of candidate datetime formats to test
CANDIDATE_DATETIME_FORMATS = [
    # US Formats (including NYC 311 format)
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
    # ISO-8601 & Standard Formats
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]

BOOLEAN_TOKENS = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
    "t": True,
    "f": False,
}


def try_parse_int(val: str) -> int | None:
    """Attempts to parse string as integer."""
    clean = val.strip()
    if not clean or not (clean[0].isdigit() or clean[0] in ("+", "-")):
        return None
    try:
        # Check without floating point representation
        if "." in clean:
            return None
        return int(clean)
    except ValueError:
        return None


def try_parse_float(val: str) -> float | None:
    """Attempts to parse string as float."""
    clean = val.strip()
    if not clean or not (clean[0].isdigit() or clean[0] in ("+", "-")):
        return None
    try:
        f = float(clean)
        # Avoid treating integers as floats unless decimal/scientific notation is present
        if "." in clean or "e" in clean.lower():
            return f
        return None
    except ValueError:
        return None


def try_parse_bool(val: str) -> bool | None:
    """Attempts to parse string as boolean."""
    clean = val.strip().lower()
    return BOOLEAN_TOKENS.get(clean)


def try_parse_datetime(val: str) -> tuple[datetime | None, str | None, bool]:
    """Attempts to parse string as datetime or date.

    Returns:
        (parsed_datetime, matched_format_string, is_date_only)
    """
    clean = val.strip()
    # Fast guard: datetime representations require at least 8 chars and delimiters
    if len(clean) < 8 or ("/" not in clean and "-" not in clean):
        return None, None, False
    for fmt in CANDIDATE_DATETIME_FORMATS:
        try:
            dt = datetime.strptime(clean, fmt)
            is_date_only = fmt in ("%m/%d/%Y", "%Y-%m-%d")
            return dt, fmt, is_date_only
        except ValueError:
            continue
    return None, None, False


def infer_column_type(
    non_null_values: list[str],
) -> tuple[InferredType, dict[str, int], list[str], Any | None, Any | None]:
    """Deterministically infers column type, format patterns, and min/max ranges.

    Returns:
        (inferred_type, type_distribution, format_patterns, min_val, max_val)
    """
    if not non_null_values:
        return InferredType.STRING, {}, [], None, None

    total = len(non_null_values)
    int_count = 0
    float_count = 0
    bool_count = 0
    dt_count = 0
    date_only_count = 0

    matched_dt_formats: set[str] = set()

    for val in non_null_values:
        # Test bool
        if try_parse_bool(val) is not None:
            bool_count += 1

        # Test int
        if try_parse_int(val) is not None:
            int_count += 1
        # Test float
        elif try_parse_float(val) is not None:
            float_count += 1

        # Test datetime
        dt, fmt, is_date = try_parse_datetime(val)
        if dt is not None and fmt is not None:
            dt_count += 1
            if is_date:
                date_only_count += 1
            matched_dt_formats.add(fmt)

    distribution = {
        "integer": int_count,
        "float": float_count,
        "boolean": bool_count,
        "datetime": dt_count,
        "string": total,
    }

    format_patterns = sorted(list(matched_dt_formats))

    # Decision tree: 100% threshold for primitive types
    if int_count == total:
        parsed_ints = [int(v.strip()) for v in non_null_values]
        return InferredType.INTEGER, distribution, [], min(parsed_ints), max(parsed_ints)

    if (int_count + float_count) == total and (float_count > 0 or int_count > 0):
        parsed_floats = [float(v.strip()) for v in non_null_values]
        return InferredType.FLOAT, distribution, [], min(parsed_floats), max(parsed_floats)

    if dt_count == total:
        # Differentiate date vs datetime
        target_type = InferredType.DATE if date_only_count == total else InferredType.DATETIME
        primary_fmt = format_patterns[0] if format_patterns else "%Y-%m-%d"
        parsed_dts = [datetime.strptime(v.strip(), primary_fmt) for v in non_null_values]
        min_dt = min(parsed_dts).isoformat()
        max_dt = max(parsed_dts).isoformat()
        return target_type, distribution, format_patterns, min_dt, max_dt

    if bool_count == total:
        return InferredType.BOOLEAN, distribution, [], False, True

    # Default fallback: STRING
    # String min/max by alphabetical order
    stripped = [v.strip() for v in non_null_values if v.strip()]
    min_str = min(stripped) if stripped else None
    max_str = max(stripped) if stripped else None

    return InferredType.STRING, distribution, format_patterns, min_str, max_str
