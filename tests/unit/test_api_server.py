"""Unit tests for Recon FastAPI server and developer web endpoints."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from recon.server.app import app


@pytest.fixture
def client() -> TestClient:
    """Provides FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def fixtures_dir() -> Path:
    """Returns path to test fixtures."""
    return Path(__file__).resolve().parents[1] / "fixtures"


def test_health_check(client: TestClient) -> None:
    """Verifies API health endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "Recon" in data["engine"]


def test_sample_catalogs(client: TestClient) -> None:
    """Verifies sample contracts and datasets enumeration endpoints."""
    res_c = client.get("/api/sample-contracts")
    assert res_c.status_code == 200
    contracts = res_c.json()
    assert len(contracts) >= 3
    contract_ids = [c["id"] for c in contracts]
    assert any("service_request" in cid for cid in contract_ids)
    assert any("ecommerce_order" in cid for cid in contract_ids)

    res_d = client.get("/api/sample-datasets")
    assert res_d.status_code == 200
    datasets = res_d.json()
    assert len(datasets) >= 3
    dataset_ids = [d["id"] for d in datasets]
    assert any("nyc_311" in did for did in dataset_ids)


def test_assess_with_preloaded_samples(client: TestClient) -> None:
    """Verifies assess endpoint using preloaded sample IDs."""
    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["source"]["total_rows"] == 10
    assert data["source"]["total_columns"] == 15
    assert data["contract"]["contract_name"] == "service_request_target_contract"

    # Evidence fidelity check: proposals must have genuine string evidence, no fake percentages
    assert len(data["proposals"]) > 0
    for p in data["proposals"]:
        assert isinstance(p["evidence"], list)
        assert len(p["evidence"]) > 0
        assert "confidence_score" not in p  # Engine does not invent fake confidence scores


def test_assess_file_upload(client: TestClient, fixtures_dir: Path) -> None:
    """Verifies assess endpoint with multipart CSV and JSON file uploads."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_path = fixtures_dir / "target_contract_service_request.json"

    with open(csv_path, "rb") as f_csv, open(contract_path, "rb") as f_cont:
        res = client.post(
            "/api/assess",
            files={
                "source_file": ("my_data.csv", f_csv, "text/csv"),
                "contract_file": ("contract.json", f_cont, "application/json"),
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["source"]["file_name"] == "my_data.csv"
    assert data["source"]["total_rows"] == 10
    assert data["has_unresolved_required"] is False


def test_unfamiliar_schema_returns_unresolved_required_fields(
    client: TestClient, fixtures_dir: Path
) -> None:
    """Verifies that unfamiliar logistics schema is not falsely claimed as understood.

    Directly reflects the 0/8 unfamiliar benchmark reality from Gate 03.
    """
    csv_path = fixtures_dir / "warehouse_manifest_unfamiliar.csv"
    contract_path = fixtures_dir / "target_contract_dispatch_manifest.json"

    with open(csv_path, "rb") as f_csv, open(contract_path, "rb") as f_cont:
        res = client.post(
            "/api/assess",
            files={
                "source_file": ("unfamiliar.csv", f_csv, "text/csv"),
                "contract_file": ("contract.json", f_cont, "application/json"),
            },
        )

    assert res.status_code == 200
    data = res.json()

    # Engine must honestly report unresolved fields
    assert data["has_unresolved_required"] is True
    assert len(data["unresolved_required_fields"]) > 0
    assert "consignment_id" in data["unresolved_required_fields"]
    assert "recipient_code" in data["unresolved_required_fields"]
    assert "destination_city" in data["unresolved_required_fields"]
    assert data["is_blocked"] is True


def test_approval_rejects_when_required_fields_unresolved(
    client: TestClient, fixtures_dir: Path
) -> None:
    """Verifies that approve endpoint rejects adapter generation if required fields are missing."""
    csv_path = fixtures_dir / "warehouse_manifest_unfamiliar.csv"
    contract_path = fixtures_dir / "target_contract_dispatch_manifest.json"

    with open(csv_path, "rb") as f_csv, open(contract_path, "rb") as f_cont:
        res_assess = client.post(
            "/api/assess",
            files={
                "source_file": ("unfamiliar.csv", f_csv, "text/csv"),
                "contract_file": ("contract.json", f_cont, "application/json"),
            },
        )
    session_id = res_assess.json()["session_id"]

    # Attempt approval without manual overrides for unfamiliar required fields
    res_approve = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "qa_engineer", "overrides": {}},
    )
    # Must fail closed with 400
    assert res_approve.status_code == 400
    assert "required" in res_approve.json()["detail"].lower()


def test_approval_succeeds_with_human_overrides(
    client: TestClient, fixtures_dir: Path
) -> None:
    """Verifies that human developer mapping overrides enable adapter generation and validation."""
    csv_path = fixtures_dir / "warehouse_manifest_unfamiliar.csv"
    contract_path = fixtures_dir / "target_contract_dispatch_manifest.json"

    with open(csv_path, "rb") as f_csv, open(contract_path, "rb") as f_cont:
        res_assess = client.post(
            "/api/assess",
            files={
                "source_file": ("unfamiliar.csv", f_csv, "text/csv"),
                "contract_file": ("contract.json", f_cont, "application/json"),
            },
        )
    session_id = res_assess.json()["session_id"]

    # Provide explicit human overrides
    overrides = {
        "consignment_id": "manifest_no",
        "recipient_code": "party_id",
        "dispatch_status": "workflow_stage",
        "departure_time": "departed_at",
        "gross_weight_kg": "weight_metric",
        "declared_value": "valuation",
        "destination_city": "dropoff_locality",
        "destination_state": "dropoff_province",
    }

    res_approve = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "lead_architect", "overrides": overrides},
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert "adapter" in data
    assert "def transform_record(" in data["adapter"]["python_code"]
    assert "def transform_dataset(" in data["adapter"]["python_code"]
    assert data["validation"]["all_tests_passed"] is True
    assert data["validation"]["total_input_records"] == 5
    assert data["validation"]["valid_records_count"] == 5
    assert data["validation"]["quarantined_records_count"] == 0


def test_quarantine_accounting_on_corrupted_dataset(
    client: TestClient, fixtures_dir: Path
) -> None:
    """Verifies zero-loss accounting and quarantine reporting on corrupted dataset."""
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "corrupted_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    assert res_assess.status_code == 200
    session_id = res_assess.json()["session_id"]

    res_approve = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "qa_tester", "overrides": {}},
    )
    assert res_approve.status_code == 200
    data = res_approve.json()

    total = data["validation"]["total_input_records"]
    valid = data["validation"]["valid_records_count"]
    quarantined = data["validation"]["quarantined_records_count"]

    # Zero-loss invariant
    assert total == valid + quarantined
    assert quarantined == 5
    assert valid == 5
    assert len(data["validation"]["sample_quarantined_records"]) <= 5
    assert len(data["validation"]["sample_quarantined_records"]) > 0
    for qr in data["validation"]["sample_quarantined_records"]:
        assert len(qr["failure_reasons"]) > 0


def test_download_endpoints(client: TestClient) -> None:
    """Verifies download endpoints for reports (.md, .json) and adapter (.py)."""
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    session_id = res_assess.json()["session_id"]
    client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "tester", "overrides": {}},
    )

    # 1. Download Markdown Report
    res_md = client.get(f"/api/download/report/{session_id}?format=md")
    assert res_md.status_code == 200
    assert "Recon Integration Readiness Report" in res_md.text
    assert res_md.headers["content-type"].startswith("text/markdown")

    # 2. Download JSON Report
    res_json = client.get(f"/api/download/report/{session_id}?format=json")
    assert res_json.status_code == 200
    report_data = json.loads(res_json.text)
    assert "readiness_state" in report_data

    # 3. Download Adapter Python code
    res_py = client.get(f"/api/download/adapter/{session_id}")
    assert res_py.status_code == 200
    assert "def transform_record(" in res_py.text
    assert "def transform_dataset(" in res_py.text
    assert "attachment; filename=" in res_py.headers["content-disposition"]


def test_invalid_requests(client: TestClient) -> None:
    """Verifies error handling on bad requests."""
    # Missing source and contract
    res_missing = client.post("/api/assess", data={})
    assert res_missing.status_code == 400

    # Malformed contract JSON text
    res_bad_json = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "contract_text": "{invalid_json: true",
        },
    )
    assert res_bad_json.status_code == 400

    # Nonexistent session
    res_bad_session = client.post(
        "/api/approve-and-generate",
        json={"session_id": "non-existent-uuid", "reviewer": "tester"},
    )
    assert res_bad_session.status_code == 404

    # Nonexistent source column in overrides
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    session_id = res_assess.json()["session_id"]
    res_bad_override = client.post(
        "/api/approve-and-generate",
        json={
            "session_id": session_id,
            "reviewer": "tester",
            "overrides": {"unique_key": "non_existent_column_123"},
        },
    )
    assert res_bad_override.status_code == 400
