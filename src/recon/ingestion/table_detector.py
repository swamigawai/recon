"""Smart table detector for visual reports, dashboards, and offset spreadsheets.

Detects when a spreadsheet or CSV contains top-level visual reporting, question banners,
or pivot summaries before the actual continuous data table begins, and locates the
primary tabular data sheet in multi-sheet workbooks.
"""

from collections import Counter
import re
from typing import Any, List, Optional, Tuple


def _is_probable_header_row(row_cells: List[str]) -> bool:
    """Returns True if a candidate list of cells has strong characteristics of a table header."""
    if not row_cells or len(row_cells) < 2:
        return False

    # No blanks allowed in header row
    if any(not c for c in row_cells):
        return False

    # No duplicates allowed (case-insensitive check for cleanliness)
    lower_cells = [c.lower() for c in row_cells]
    if len(set(lower_cells)) != len(lower_cells):
        return False

    # Header cells shouldn't be full question sentences or question identifiers
    if any(c.endswith("?") or (c.startswith("Q") and any(sep in c[:5] for sep in [")", ":", ".", " "])) for c in row_cells):
        return False

    # Header cells shouldn't start with summary / aggregate markers
    first_cell_lower = lower_cells[0]
    if any(first_cell_lower.startswith(k) for k in ["total", "grand total", "average", "avg ", "summary", "notes:"]):
        return False

    # Data rows usually contain numbers, IDs, prices, booleans, or dates.
    # If more than 40% of the cells parse strictly as pure numbers, it's likely a data row, not a header.
    num_like = 0
    for c in row_cells:
        cleaned = c.replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            float(cleaned)
            num_like += 1
        except ValueError:
            pass

    if num_like > len(row_cells) * 0.4:
        return False

    return True


def detect_tabular_header_offset(
    rows_sample: List[List[Any]],
    max_scan_rows: int = 150,
    min_data_rows: int = 2,
) -> Optional[Tuple[int, List[str]]]:
    """Scans leading rows to detect if a valid tabular table begins at a non-zero offset.
    
    Used when a spreadsheet or CSV contains top-level visual reporting, question banners,
    charts, or pivot summaries before the actual continuous data table begins.
    
    Returns (header_row_index, clean_headers) if a deeper valid table is found, else None.
    """
    if not rows_sample or len(rows_sample) <= 1:
        return None

    scan_limit = min(len(rows_sample), max_scan_rows)
    best_candidate: Optional[Tuple[int, List[str], int]] = None

    for idx in range(1, scan_limit):
        raw_row = rows_sample[idx]
        if not raw_row:
            continue

        trimmed = [str(c).strip() if c is not None else "" for c in raw_row]
        while trimmed and not trimmed[-1]:
            trimmed.pop()

        if not _is_probable_header_row(trimmed):
            continue

        # Verify that subsequent rows look like genuine data rows for this table
        subsequent = rows_sample[idx + 1 : idx + 1 + 25]
        if len(subsequent) < min_data_rows:
            continue

        valid_subsequent = 0
        expected_cols = len(trimmed)

        for nxt in subsequent:
            if not nxt:
                continue
            nxt_trimmed = [str(c).strip() if c is not None else "" for c in nxt]
            while nxt_trimmed and not nxt_trimmed[-1]:
                nxt_trimmed.pop()
            # If the row has at least 50% of expected columns with data
            if len(nxt_trimmed) >= max(2, int(expected_cols * 0.5)):
                valid_subsequent += 1

        if valid_subsequent >= min_data_rows:
            # Score candidate higher for more columns and more data rows
            score = (expected_cols * 10) + (valid_subsequent * 5)
            if best_candidate is None or score > best_candidate[2]:
                best_candidate = (idx, trimmed, score)

    if best_candidate:
        return best_candidate[0], best_candidate[1]
    return None


def is_report_footer_row(row_vals: List[Any], expected_col_count: int) -> bool:
    """Detects trailing notes, summary text, or post-table narrative commentary.
    
    Example: 'Average purchases of Males', 'The clothing category stays on the top'
    """
    if not row_vals:
        return False

    non_empty = [v for v in row_vals if v is not None and str(v).strip() != ""]
    if len(non_empty) <= 3 and expected_col_count >= 5:
        first_str = str(non_empty[0]).strip().lower()
        footer_keywords = [
            "average", "avg ", "total", "grand total", "customers with",
            "conclusion", "difference between", "notes:", "purchases of",
            "accessories purchased", "payment methods used", "category stays"
        ]
        if any(kw in first_str for kw in footer_keywords):
            return True
        if len(first_str) > 35 and " " in first_str:
            return True
    return False


def evaluate_sheet_tabular_structure(
    sheet_title: str,
    sample_rows: List[List[Any]],
    is_active: bool = False,
    max_scan_rows: int = 100,
) -> Optional[dict]:
    """Evaluates whether a worksheet contains a valid tabular dataset and returns metadata."""
    if not sample_rows:
        return None

    # Check for leading non-empty row (standard table starting at row 0 or near top)
    first_row_idx = None
    first_row = None
    for idx, r in enumerate(sample_rows[:20]):
        if any(c is not None and str(c).strip() for c in r):
            first_row_idx = idx
            first_row = [str(c).strip() if c is not None else "" for c in r]
            while first_row and not first_row[-1]:
                first_row.pop()
            break

    name_lower = sheet_title.lower()
    name_score = 0
    if any(k in name_lower for k in ["data", "raw", "table", "records", "transactions", "orders", "sales"]):
        name_score += 150
    if any(k in name_lower for k in ["pivot", "chart", "dashboard", "analysis", "summary", "rough", "cover"]):
        name_score -= 150

    if is_active:
        name_score += 20  # slight tie-breaker preference for active sheet

    # Case 1: First row is already a valid header
    if first_row and _is_probable_header_row(first_row):
        data_rows = 0
        for nxt in sample_rows[first_row_idx + 1:]:
            if any(c is not None and str(c).strip() for c in nxt):
                data_rows += 1
        score = (len(first_row) * 15) + (data_rows * 5) + name_score
        return {
            "offset": first_row_idx,
            "headers": first_row,
            "score": score,
            "data_rows": data_rows,
            "is_offset": first_row_idx > 0,
        }

    # Case 2: Check if table starts at a non-zero offset down in the sheet
    offset_result = detect_tabular_header_offset(sample_rows, max_scan_rows=max_scan_rows)
    if offset_result:
        offset, headers = offset_result
        data_rows = 0
        for nxt in sample_rows[offset + 1:]:
            if any(c is not None and str(c).strip() for c in nxt):
                data_rows += 1
        score = (len(headers) * 15) + (data_rows * 5) + name_score
        return {
            "offset": offset,
            "headers": headers,
            "score": score,
            "data_rows": data_rows,
            "is_offset": True,
        }

    return None
