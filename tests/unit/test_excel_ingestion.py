"""Unit tests for Excel (.xlsx) ingestion and end-to-end integration assessment."""

import datetime
from pathlib import Path
import pytest
from starlette.testclient import TestClient

import openpyxl

from recon.contracts.loader import load_target_contract
from recon.exceptions import IngestionError
from recon.ingestion.excel_loader import load_excel
from recon.ingestion.loader import load_dataset
from recon.ingestion.models import IngestionConfig, RawDataset
from recon.profiling.profiler import profile_dataset
from recon.server.app import app


@pytest.fixture
def sample_xlsx_path(tmp_path: Path) -> Path:
    """Creates a sample valid Excel file for testing."""
    file_path = tmp_path / "enterprise_vendor_orders.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"

    # Header row
    ws.append(["order_id", "vendor_name", "order_date", "total_amount", "is_urgent", "notes"])

    # Data rows
    ws.append([10001, "Acme Logistics", datetime.date(2026, 4, 1), 4500.50, True, "Deliver to dock 3"])
    ws.append([10002, "Beta Supplies", datetime.datetime(2026, 4, 2, 9, 30), 1200.00, False, None])
    ws.append([10003, "Gamma Tech", "2026-04-03", 8900.25, True, "Priority handling"])

    wb.save(file_path)
    return file_path


def test_load_valid_xlsx(sample_xlsx_path: Path):
    """Verifies that load_dataset and load_excel correctly ingest an .xlsx workbook."""
    dataset = load_dataset(sample_xlsx_path)

    assert isinstance(dataset, RawDataset)
    assert dataset.file_name == "enterprise_vendor_orders.xlsx"
    assert dataset.row_count == 3
    assert dataset.headers == ["order_id", "vendor_name", "order_date", "total_amount", "is_urgent", "notes"]
    assert dataset.encoding == "binary/xlsx"

    # Verify rows & data type conversions
    row0 = dataset.rows[0]
    assert row0["order_id"] == 10001
    assert row0["vendor_name"] == "Acme Logistics"
    assert row0["order_date"] == "2026-04-01"
    assert row0["total_amount"] == 4500.50
    assert row0["is_urgent"] is True
    assert row0["notes"] == "Deliver to dock 3"

    row1 = dataset.rows[1]
    assert row1["order_id"] == 10002
    assert row1["notes"] == ""  # None normalized to empty string

    # Deterministic fingerprint verified
    assert len(dataset.fingerprint) == 64


def test_xlsx_profiling_compatibility(sample_xlsx_path: Path):
    """Verifies that an ingested Excel dataset profiles cleanly without exceptions."""
    dataset = load_dataset(sample_xlsx_path)
    profile = profile_dataset(dataset)

    assert profile.total_rows == 3
    assert profile.total_columns == 6
    assert "order_id" in profile.columns
    assert "total_amount" in profile.columns
    assert profile.columns["order_id"].inferred_type.value in ("integer", "number")


def test_xlsx_empty_file(tmp_path: Path):
    """Verifies that a 0-byte file raises IngestionError."""
    empty_file = tmp_path / "empty.xlsx"
    empty_file.touch()

    with pytest.raises(IngestionError) as exc_info:
        load_dataset(empty_file)
    assert "completely empty" in str(exc_info.value)


def test_xlsx_missing_file(tmp_path: Path):
    """Verifies that a non-existent file raises IngestionError."""
    missing = tmp_path / "missing_file.xlsx"
    with pytest.raises(IngestionError) as exc_info:
        load_dataset(missing)
    assert "not found" in str(exc_info.value)


def test_xlsx_corrupt_file(tmp_path: Path):
    """Verifies that a corrupt binary file raises IngestionError."""
    corrupt = tmp_path / "corrupted.xlsx"
    corrupt.write_bytes(b"NOT_A_VALID_ZIP_EXCEL_STREAM")

    with pytest.raises(IngestionError) as exc_info:
        load_dataset(corrupt)
    assert "failed ZIP archive verification" in str(exc_info.value) or "Corrupted" in str(exc_info.value)


def test_xlsx_duplicate_headers(tmp_path: Path):
    """Verifies that duplicate column headers in an Excel file raise IngestionError."""
    dup_file = tmp_path / "dup.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["id", "name", "id"])
    ws.append([1, "Alice", 2])
    wb.save(dup_file)

    with pytest.raises(IngestionError) as exc_info:
        load_dataset(dup_file)
    assert "Duplicate column headers detected" in str(exc_info.value)


def test_xlsx_blank_intermediate_header(tmp_path: Path):
    """Verifies that empty column headers in between columns raise IngestionError."""
    blank_file = tmp_path / "blank_header.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["id", "", "amount"])
    ws.append([1, "x", 100])
    wb.save(blank_file)

    with pytest.raises(IngestionError) as exc_info:
        load_dataset(blank_file)
    assert "Empty or blank column header" in str(exc_info.value)


def test_xlsx_multi_sheet_warning(tmp_path: Path):
    """Verifies that workbooks with multiple sheets produce informative warnings."""
    multi_file = tmp_path / "multi_sheet.xlsx"
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "PrimaryData"
    ws1.append(["col1", "col2"])
    ws1.append(["a", "b"])

    ws2 = wb.create_sheet(title="LookupTable")
    ws2.append(["ref_id", "val"])
    ws2.append([1, 10])

    wb.save(multi_file)

    dataset = load_dataset(multi_file)
    assert dataset.row_count == 1
    assert any("Multiple sheets detected" in w for w in dataset.warnings)


def test_xlsx_as_target_contract(sample_xlsx_path: Path):
    """Verifies that an .xlsx file can also serve as a target contract schema/template."""
    contract = load_target_contract(sample_xlsx_path)

    assert contract.contract_name == "enterprise_vendor_orders"
    assert "order_id" in contract.fields
    assert "vendor_name" in contract.fields
    assert "total_amount" in contract.fields


def test_api_assess_endpoint_with_xlsx(sample_xlsx_path: Path):
    """End-to-end integration test: Verifies POST /api/assess succeeds with an uploaded .xlsx source file."""
    client = TestClient(app)

    with open(sample_xlsx_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/api/assess",
        data={"sample_contract_id": "target_contract_service_request"},
        files={"source_file": ("enterprise_vendor_orders.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data and len(data["session_id"]) > 0
    assert data["source"]["total_rows"] == 3
    assert data["source"]["total_columns"] == 6
    assert data["source"]["file_name"] == "enterprise_vendor_orders.xlsx"
