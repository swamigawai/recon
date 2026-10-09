"""Unit tests for JSON dataset ingestion, flattening, envelope unwrapping, and error handling."""

import json
from pathlib import Path
import pytest

from recon.exceptions import IngestionError
from recon.ingestion.json_loader import extract_records_from_json, flatten_json_record, load_json
from recon.ingestion.loader import load_dataset
from recon.ingestion.models import IngestionConfig, RawDataset


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


def test_load_valid_json_array(fixtures_dir: Path):
    """Verifies that an array of JSON objects loads correctly with nested dot-notation flattening."""
    json_path = fixtures_dir / "jsonplaceholder_users.json"
    dataset = load_json(json_path)

    assert isinstance(dataset, RawDataset)
    assert dataset.row_count == 5
    assert dataset.file_name == "jsonplaceholder_users.json"

    # Flattened keys verified
    assert "address.city" in dataset.headers
    assert "company.name" in dataset.headers
    assert "address.geo.lat" in dataset.headers

    # Row 1 values
    row0 = dataset.rows[0]
    assert row0["id"] == 1
    assert row0["name"] == "Leanne Graham"
    assert row0["address.city"] == "Gwenborough"
    assert row0["company.name"] == "Romaguera-Crona"


def test_flatten_json_record_nested():
    """Verifies recursive flattening of deeply nested dictionary keys."""
    nested = {
        "user": {
            "profile": {
                "first_name": "Ada",
                "last_name": "Lovelace",
            },
            "role": "admin",
        },
        "active": True,
    }
    flattened = flatten_json_record(nested)

    assert flattened == {
        "user.profile.first_name": "Ada",
        "user.profile.last_name": "Lovelace",
        "user.role": "admin",
        "active": True,
    }


def test_load_enveloped_json(tmp_path: Path):
    """Verifies extraction of records from common envelope keys like 'data' or 'items'."""
    enveloped = {
        "status": "success",
        "page": 1,
        "data": [
            {"id": 101, "event": "click"},
            {"id": 102, "event": "hover"},
        ],
    }
    json_file = tmp_path / "enveloped.json"
    json_file.write_text(json.dumps(enveloped), encoding="utf-8")

    dataset = load_json(json_file)
    assert dataset.row_count == 2
    assert "id" in dataset.headers
    assert "event" in dataset.headers
    assert any("envelope key 'data'" in w for w in dataset.warnings)


def test_load_single_object_document(tmp_path: Path):
    """Verifies that a single JSON object document is ingested as a 1-row dataset."""
    doc = {"transaction_id": "TX999", "amount": 150.75, "currency": "USD"}
    json_file = tmp_path / "single_doc.json"
    json_file.write_text(json.dumps(doc), encoding="utf-8")

    dataset = load_json(json_file)
    assert dataset.row_count == 1
    assert dataset.rows[0]["transaction_id"] == "TX999"
    assert any("single JSON object document" in w for w in dataset.warnings)


def test_load_malformed_json_syntax(tmp_path: Path):
    """Verifies that JSON syntax errors raise IngestionError with line/col diagnostics."""
    json_file = tmp_path / "syntax_error.json"
    json_file.write_text('[{"id": 1,}]', encoding="utf-8")  # Trailing comma error

    with pytest.raises(IngestionError) as exc_info:
        load_json(json_file)
    assert "Malformed JSON" in str(exc_info.value)
    assert "line_number" in exc_info.value.context
    assert exc_info.value.actionable_suggestion is not None


def test_load_empty_json_file(tmp_path: Path):
    """Verifies that an empty 0-byte JSON file raises IngestionError."""
    json_file = tmp_path / "empty.json"
    json_file.write_text("", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_json(json_file)
    assert "completely empty (0 bytes)" in str(exc_info.value)


def test_load_empty_json_array(tmp_path: Path):
    """Verifies that a JSON file containing an empty array [] raises IngestionError."""
    json_file = tmp_path / "empty_array.json"
    json_file.write_text("[]", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_json(json_file)
    assert "contains zero records" in str(exc_info.value)


def test_load_array_of_primitives_rejected(tmp_path: Path):
    """Verifies that an array of primitive values ([1, 2, 3]) is rejected."""
    json_file = tmp_path / "primitives.json"
    json_file.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_json(json_file)
    assert "must be objects" in str(exc_info.value)


def test_heterogeneous_json_records(tmp_path: Path):
    """Verifies that heterogeneous JSON records merge their union of attributes cleanly."""
    hetero = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "email": "bob@example.com"},  # missing name
        {"id": 3, "name": "Charlie", "phone": "123"},
    ]
    json_file = tmp_path / "hetero.json"
    json_file.write_text(json.dumps(hetero), encoding="utf-8")

    dataset = load_json(json_file)
    assert dataset.row_count == 3
    assert set(dataset.headers) == {"id", "name", "email", "phone"}
    assert dataset.rows[1].get("name") is None  # Missing key preserved as None


def test_unified_loader_routes_formats(fixtures_dir: Path):
    """Verifies that load_dataset transparently routes CSV and JSON files correctly."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    json_path = fixtures_dir / "jsonplaceholder_users.json"

    ds_csv = load_dataset(csv_path)
    assert ds_csv.row_count == 10
    assert "Unique Key" in ds_csv.headers

    ds_json = load_dataset(json_path)
    assert ds_json.row_count == 5
    assert "address.city" in ds_json.headers
