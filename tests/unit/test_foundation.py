"""Foundation tests verifying project setup, contracts, fixtures, and errors."""

import csv
import io
import logging
from pathlib import Path

import pytest

import recon
from recon.contracts.loader import load_target_contract
from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.exceptions import ContractError, ReconError
from recon.logging import configure_logging, log_safe_event


def test_package_version():
    """Verifies that recon package exposes a valid version."""
    assert recon.__version__ == "0.1.0"


def test_actionable_exception_formatting():
    """Verifies that ReconError formats message, context, and actionable guidance."""
    err = ReconError(
        "Source file not accessible",
        actionable_suggestion="Check read permissions on the file.",
        context={"path": "/tmp/test.csv"},
    )
    rendered = str(err)
    assert "Source file not accessible" in rendered
    assert "Action: Check read permissions on the file." in rendered
    assert "path='/tmp/test.csv'" in rendered


def test_load_target_contract_from_fixture():
    """Verifies that the target contract fixture parses and validates correctly."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "target_contract_service_request.json"
    assert fixture_path.exists(), f"Missing fixture at {fixture_path}"

    contract = load_target_contract(fixture_path)
    assert isinstance(contract, TargetContract)
    assert contract.contract_name == "service_request_target_contract"
    assert contract.version == "1.0.0"

    # Check key fields
    assert "ticket_id" in contract.fields
    assert contract.fields["ticket_id"].target_type == ContractType.STRING
    assert contract.fields["ticket_id"].required is True
    assert contract.fields["ticket_id"].nullable is False

    assert "created_at" in contract.fields
    assert contract.fields["created_at"].target_type == ContractType.DATETIME

    assert "borough" in contract.fields
    assert contract.fields["borough"].allowed_values == [
        "MANHATTAN",
        "BROOKLYN",
        "QUEENS",
        "BRONX",
        "STATEN ISLAND",
    ]

    # Required fields helper
    req_fields = contract.required_field_names()
    assert "ticket_id" in req_fields
    assert "created_at" in req_fields
    assert "closed_at" not in req_fields


def test_load_target_contract_invalid_schema():
    """Verifies that malformed or incomplete contracts raise ContractError with actionable advice."""
    invalid_dict = {
        "contract_name": "broken_contract",
        "fields": {
            "bad_field": {
                "name": "bad_field",
                "target_type": "unsupported_type",  # invalid type
            }
        },
    }
    with pytest.raises(ContractError) as exc_info:
        load_target_contract(invalid_dict)
    assert "Invalid target contract schema" in str(exc_info.value)
    assert exc_info.value.actionable_suggestion is not None


def test_synthetic_csv_fixture_integrity():
    """Verifies that the synthetic NYC 311 CSV fixture exists and has expected rows and columns."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "synthetic_nyc_311.csv"
    assert fixture_path.exists()

    with open(fixture_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    assert len(rows) == 10
    assert "Unique Key" in headers
    assert "Created Date" in headers
    assert "Complaint Type" in headers
    assert "Borough" in headers
    assert "Status" in headers

    # Verify first row data
    assert rows[0]["Unique Key"] == "10000001"
    assert rows[0]["Borough"] == "MANHATTAN"
    assert rows[0]["Status"] == "Closed"


def test_safe_logging_does_not_leak_raw_rows():
    """Verifies that structured logging excludes raw row payloads from outputs."""
    log_stream = io.StringIO()
    test_logger = configure_logging(level=logging.INFO, stream=log_stream)

    log_safe_event("FILE_LOADED", filename="test.csv", rows_count=10, raw_row={"secret": "123"})
    output = log_stream.getvalue()

    assert "FILE_LOADED" in output
    assert "filename=test.csv" in output
    assert "rows_count=10" in output
    assert "secret" not in output
