"""Unit tests for the Recon CSV ingestion module."""

import hashlib
from pathlib import Path

import pytest

from recon.exceptions import IngestionError
from recon.ingestion.csv_loader import calculate_file_hash, detect_file_encoding, load_csv
from recon.ingestion.models import IngestionConfig, RawDataset


@pytest.fixture
def synthetic_csv_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "synthetic_nyc_311.csv"


def test_load_valid_csv(synthetic_csv_path: Path):
    """Verifies that a valid CSV loads correctly with exact headers and rows."""
    dataset = load_csv(synthetic_csv_path)

    assert isinstance(dataset, RawDataset)
    assert dataset.file_name == "synthetic_nyc_311.csv"
    assert dataset.row_count == 10
    assert len(dataset.headers) == 15
    assert "Unique Key" in dataset.headers
    assert "Created Date" in dataset.headers
    assert "Borough" in dataset.headers

    # Check immutability & exact string preservation
    assert dataset.rows[0]["Unique Key"] == "10000001"
    assert dataset.rows[0]["Status"] == "Closed"
    assert dataset.rows[1]["Status"] == "Open"
    assert dataset.rows[1]["Closed Date"] == ""  # Empty string preserved, not fabricated

    # Verify SHA-256 fingerprint matches independent calculation
    with open(synthetic_csv_path, "rb") as f:
        expected_hash = hashlib.sha256(f.read()).hexdigest()
    assert dataset.fingerprint == expected_hash

    # Test preview method
    preview = dataset.preview(3)
    assert len(preview) == 3


def test_load_nonexistent_file(tmp_path: Path):
    """Verifies that non-existent file raises IngestionError with actionable guidance."""
    missing = tmp_path / "does_not_exist.csv"
    with pytest.raises(IngestionError) as exc_info:
        load_csv(missing)

    assert "Source file not found" in str(exc_info.value)
    assert exc_info.value.actionable_suggestion is not None
    assert "does_not_exist.csv" in exc_info.value.context["file_path"]


def test_load_directory_as_file(tmp_path: Path):
    """Verifies that attempting to load a directory raises IngestionError."""
    with pytest.raises(IngestionError) as exc_info:
        load_csv(tmp_path)
    assert "Path is not a regular file" in str(exc_info.value)


def test_load_empty_file(tmp_path: Path):
    """Verifies that a 0-byte file raises IngestionError."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_csv(empty_file)
    assert "completely empty (0 bytes)" in str(exc_info.value)


def test_load_file_with_blank_header(tmp_path: Path):
    """Verifies that an empty header name in the header row raises IngestionError."""
    csv_file = tmp_path / "blank_header.csv"
    csv_file.write_text("id,,status\n1,foo,bar\n", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_csv(csv_file)
    assert "Empty or blank column header found at column 2" in str(exc_info.value)
    assert exc_info.value.context["column_index"] == 2


def test_load_file_with_duplicate_headers(tmp_path: Path):
    """Verifies that duplicate headers raise IngestionError."""
    csv_file = tmp_path / "duplicate_headers.csv"
    csv_file.write_text("id,status,id\n1,open,2\n", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_csv(csv_file)
    assert "Duplicate column headers detected" in str(exc_info.value)
    assert "id" in exc_info.value.context["duplicate_headers"]


def test_load_file_with_malformed_ragged_row(tmp_path: Path):
    """Verifies that rows with unexpected column counts raise IngestionError with line number."""
    csv_file = tmp_path / "ragged.csv"
    # Row 2 has 3 cols, Row 3 has 2 cols (malformed)
    csv_file.write_text("col_a,col_b,col_c\n1,2,3\n4,5\n", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_csv(csv_file)
    assert "Malformed row at line 3" in str(exc_info.value)
    assert exc_info.value.context["line_number"] == 3
    assert exc_info.value.context["expected_columns"] == 3
    assert exc_info.value.context["found_columns"] == 2


def test_load_file_with_malformed_row_non_strict(tmp_path: Path):
    """Verifies that non-strict mode skips ragged rows and records warnings."""
    csv_file = tmp_path / "ragged_non_strict.csv"
    csv_file.write_text("col_a,col_b,col_c\n1,2,3\n4,5\n7,8,9\n", encoding="utf-8")

    cfg = IngestionConfig(strict_row_counts=False)
    dataset = load_csv(csv_file, config=cfg)

    assert dataset.row_count == 2
    assert any("Row at line 3 has 2 columns" in w for w in dataset.warnings)


def test_file_size_limit_exceeded(tmp_path: Path):
    """Verifies that files exceeding configured max size raise IngestionError."""
    big_file = tmp_path / "big.csv"
    big_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    cfg = IngestionConfig(max_file_size_bytes=5)  # 5 bytes threshold
    with pytest.raises(IngestionError) as exc_info:
        load_csv(big_file, config=cfg)
    assert "exceeds maximum configured limit" in str(exc_info.value)


def test_latin1_encoding_detection(tmp_path: Path):
    """Verifies that Latin-1 encoded files with accented characters are safely loaded."""
    latin1_file = tmp_path / "latin1.csv"
    # Latin-1 byte representation of 'café'
    content = "id,name\n1,café\n".encode("latin-1")
    latin1_file.write_bytes(content)

    dataset = load_csv(latin1_file)
    assert dataset.row_count == 1
    assert dataset.rows[0]["name"] == "café"


def test_max_rows_truncation(tmp_path: Path):
    """Verifies that max_rows truncates reading and adds a warning."""
    csv_file = tmp_path / "many_rows.csv"
    lines = ["id,val"] + [f"{i},{i*10}" for i in range(1, 20)]
    csv_file.write_text("\n".join(lines), encoding="utf-8")

    cfg = IngestionConfig(max_rows=5)
    dataset = load_csv(csv_file, config=cfg)

    assert dataset.row_count == 5
    assert any("truncated at 5 rows" in w for w in dataset.warnings)
