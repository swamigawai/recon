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


def test_static_frontend_assets_served(client: TestClient) -> None:
    """Verifies static frontend shell and assets are served by FastAPI."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "RECON // 01" in res_root.text
    assert "Contextual Inspector" in res_root.text

    res_css = client.get("/style.css")
    assert res_css.status_code == 200
    assert "--recon-bg-root" in res_css.text

    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "initShell" in res_js.text


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

    # 4. Download Valid Records (.jsonl)
    res_valid = client.get(f"/api/download/valid-records/{session_id}")
    assert res_valid.status_code == 200
    assert res_valid.headers["content-type"].startswith("application/x-jsonlines")
    valid_lines = [line for line in res_valid.text.strip().split("\n") if line.strip()]
    assert len(valid_lines) == 10  # all 10 valid records exported, not truncated to 3 sample records

    # 5. Download Quarantine Records (.jsonl)
    res_quarantine = client.get(f"/api/download/quarantine-records/{session_id}")
    assert res_quarantine.status_code == 200
    assert res_quarantine.headers["content-type"].startswith("application/x-jsonlines")


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


def test_unsupported_file_extension_rejected(client: TestClient) -> None:
    """Verifies that uploading an unsupported executable or script is rejected."""
    import io
    exe_content = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    res = client.post(
        "/api/assess",
        files={"source_file": ("malicious.exe", exe_content, "application/octet-stream")},
        data={"sample_contract_id": "target_contract_service_request"},
    )
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]


def test_empty_or_dot_filename_rejected(client: TestClient) -> None:
    """Verifies that dangerous or empty filenames (e.g. '.') are rejected gracefully with 400."""
    import io
    csv_bytes = io.BytesIO(b"id,name\n1,alice\n")
    res = client.post(
        "/api/assess",
        files={"source_file": (".", csv_bytes, "text/csv")},
        data={"sample_contract_id": "target_contract_service_request"},
    )
    assert res.status_code == 400
    assert "Invalid source file name" in res.json()["detail"]


def test_path_traversal_in_sample_ids_rejected(client: TestClient) -> None:
    """Verifies that path traversal in sample dataset or contract IDs is blocked."""
    res_d = client.post(
        "/api/assess",
        data={"sample_dataset_id": "../../src/recon/cli", "sample_contract_id": "target_contract_service_request"},
    )
    assert res_d.status_code == 400
    assert "Invalid sample_dataset_id format" in res_d.json()["detail"]

    res_c = client.post(
        "/api/assess",
        data={"sample_dataset_id": "synthetic_nyc_311", "sample_contract_id": "../../src/recon/cli"},
    )
    assert res_c.status_code == 400
    assert "Invalid sample_contract_id format" in res_c.json()["detail"]


def test_non_json_contract_file_rejected(client: TestClient) -> None:
    """Verifies that non-JSON contract files are rejected."""
    import io
    txt_content = io.BytesIO(b"contract schema in text")
    res = client.post(
        "/api/assess",
        data={"sample_dataset_id": "synthetic_nyc_311"},
        files={"contract_file": ("contract.txt", txt_content, "text/plain")},
    )
    assert res.status_code == 400
    assert "Target contract file must be a .json file" in res.json()["detail"]


def test_download_before_approval_rejected(client: TestClient) -> None:
    """Verifies that requesting downloads before adapter generation returns 404."""
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    sid = res_assess.json()["session_id"]
    res_md = client.get(f"/api/download/report/{sid}?format=md")
    assert res_md.status_code == 404
    assert "Run approval and validation first" in res_md.json()["detail"]

    res_py = client.get(f"/api/download/adapter/{sid}")
    assert res_py.status_code == 404
    assert "Adapter code not generated yet" in res_py.json()["detail"]


def test_json_workflow_end_to_end(client: TestClient) -> None:
    """Verifies complete JSON dataset workflow through API."""
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "jsonplaceholder_users",
            "sample_contract_id": "target_contract_user_profile",
        },
    )
    assert res_assess.status_code == 200
    data = res_assess.json()
    assert data["source"]["format"] == "json"
    assert data["source"]["total_rows"] == 5
    assert data["has_unresolved_required"] is False
    sid = data["session_id"]

    res_approve = client.post(
        "/api/approve-and-generate",
        json={"session_id": sid, "reviewer": "api_user", "overrides": {}},
    )
    assert res_approve.status_code == 200
    data_app = res_approve.json()
    assert data_app["validation"]["total_input_records"] == 5
    assert data_app["validation"]["valid_records_count"] == 5
    assert data_app["validation"]["quarantined_records_count"] == 0
    assert data_app["validation"]["all_tests_passed"] is True


def test_session_lifecycle_and_deletion(client: TestClient) -> None:
    """Verifies explicit session termination and artifact cleanup."""
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    sid = res_assess.json()["session_id"]

    # Delete session
    res_del = client.delete(f"/api/session/{sid}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "cleaned"

    # Subsequent access fails with 404
    res_retry = client.get(f"/api/download/report/{sid}?format=md")
    assert res_retry.status_code == 404


def test_mapping_spec_download_and_upload(client: TestClient) -> None:
    """Verifies exporting and re-uploading mapping specifications via API."""
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    assert res_assess.status_code == 200
    sid = res_assess.json()["session_id"]

    # 1. Download mapping spec
    res_dl = client.get(f"/api/download/mapping-spec/{sid}")
    assert res_dl.status_code == 200
    spec_data = res_dl.json()
    assert spec_data["schema_version"] == "1.0"
    assert spec_data["contract_name"] == "service_request_target_contract"
    assert len(spec_data["mappings"]) > 0

    # 2. Upload spec back to active session
    res_up = client.post(
        "/api/upload-mapping-spec",
        data={"session_id": sid, "spec_json": json.dumps(spec_data)},
    )
    assert res_up.status_code == 200
    up_data = res_up.json()
    assert up_data["validation_result"]["is_valid"] is True
    assert up_data["validation_result"]["reused_count"] > 0
    assert up_data["validation_result"]["contract_match"] is True

    # Check human approval requirement: required fields must NOT be silently auto-approved!
    ticket_prop = next(p for p in up_data["proposals_summary"] if p["target_field"] == "ticket_id")
    assert ticket_prop["status"] == "proposed"


def test_standard_contract_ingestion_api(client: TestClient) -> None:
    """Verifies that JSON Schema and OpenAPI contracts can be uploaded directly via /api/assess."""
    json_schema_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "UniversalCustomer",
        "type": "object",
        "required": ["customer_id", "email"],
        "properties": {
            "customer_id": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer"},
        },
    }

    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "contract_text": json.dumps(json_schema_contract),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["contract"]["contract_name"] == "UniversalCustomer"
    assert "customer_id" in [p["target_field"] for p in data["proposals"]]


def test_interactive_mapping_scenario_1_straightforward_1to1(client: TestClient) -> None:
    """Verifies scenario 1: Straightforward 1-to-1 mapping assignment."""
    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    assert res.status_code == 200
    sid = res.json()["session_id"]

    # Reassign ticket_id explicitly to Unique Key
    res_approve = client.post(
        "/api/approve-and-generate",
        json={
            "session_id": sid,
            "reviewer": "qa_verifier",
            "overrides": {"ticket_id": "Unique Key"},
        },
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert data["validation"]["all_tests_passed"] is True
    assert "ticket_id" in data["adapter"]["python_code"]
    assert "Unique Key" in data["adapter"]["python_code"]


def test_interactive_mapping_scenario_2_transformation_required(client: TestClient) -> None:
    """Verifies scenario 2: Mapping requiring a transformation (e.g. date parsing or cast)."""
    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    assert res.status_code == 200
    sid = res.json()["session_id"]

    # created_at requires datetime transformation
    res_approve = client.post(
        "/api/approve-and-generate",
        json={
            "session_id": sid,
            "reviewer": "qa_verifier",
            "overrides": {"created_at": "Created Date"},
        },
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert "created_at" in data["adapter"]["python_code"]


def test_interactive_mapping_scenario_3_ambiguous_source_selection(client: TestClient) -> None:
    """Verifies scenario 3: Ambiguous source selection resolved by explicit human choice."""
    contract = {
        "contract_name": "ambiguity_contract",
        "version": "1.0.0",
        "fields": {
            "incident_code": {
                "name": "incident_code",
                "target_type": "string",
                "required": True,
                "description": "Unique incident identifier",
            },
        },
    }
    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "contract_text": json.dumps(contract),
        },
    )
    assert res.status_code == 200
    sid = res.json()["session_id"]

    # In absence of exact match, user manually disambiguates and assigns 'Complaint Type'
    res_approve = client.post(
        "/api/approve-and-generate",
        json={
            "session_id": sid,
            "reviewer": "qa_verifier",
            "overrides": {"incident_code": "Complaint Type"},
        },
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert data["validation"]["all_tests_passed"] is True
    assert "Complaint Type" in data["adapter"]["python_code"]


def test_interactive_mapping_scenario_4_missing_required_blocks_approval(client: TestClient) -> None:
    """Verifies scenario 4: Required target field with no valid source blocks approval."""
    contract = {
        "contract_name": "strict_required_contract",
        "version": "1.0.0",
        "fields": {
            "mandatory_unmapped_token": {
                "name": "mandatory_unmapped_token",
                "target_type": "string",
                "required": True,
                "description": "Field that does not exist in source data",
            },
        },
    }
    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "contract_text": json.dumps(contract),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_unresolved_required"] is True
    sid = data["session_id"]

    # Attempting to approve without mapping the required field must fail with 400
    res_approve = client.post(
        "/api/approve-and-generate",
        json={"session_id": sid, "reviewer": "qa_verifier", "overrides": {}},
    )
    assert res_approve.status_code == 400
    err = res_approve.json()
    assert "Cannot approve required target field" in err["detail"] or "required" in err["detail"].lower()


def test_interactive_mapping_scenario_5_duplicate_source_assignment(client: TestClient) -> None:
    """Verifies scenario 5: Conflicting or duplicate source assignment to multiple target fields."""
    contract = {
        "contract_name": "duplicate_source_contract",
        "version": "1.0.0",
        "fields": {
            "ticket_primary": {
                "name": "ticket_primary",
                "target_type": "string",
                "required": True,
                "description": "First target field",
            },
            "ticket_secondary": {
                "name": "ticket_secondary",
                "target_type": "string",
                "required": True,
                "description": "Second target field reusing same source",
            },
        },
    }
    res = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "contract_text": json.dumps(contract),
        },
    )
    assert res.status_code == 200
    sid = res.json()["session_id"]

    # Reassign BOTH target fields to the identical source column 'Unique Key'
    res_approve = client.post(
        "/api/approve-and-generate",
        json={
            "session_id": sid,
            "reviewer": "qa_verifier",
            "overrides": {
                "ticket_primary": "Unique Key",
                "ticket_secondary": "Unique Key",
            },
        },
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert data["validation"]["all_tests_passed"] is True
    code = data["adapter"]["python_code"]
    assert "ticket_primary" in code
    assert "ticket_secondary" in code
    assert code.count("Unique Key") >= 2


def test_inspector_and_flow_static_assets_verified(client: TestClient) -> None:
    """Verifies the new Inspector and Flow Graph static assets and elements."""
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "inspector-edge-tab" in res_html.text
    assert "flow-meter-evidence" in res_html.text
    assert "flow-meter-panel" in res_html.text

    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "evaluateMappingEvidence" in res_js.text
    assert "getDuplicateSourceAssignments" in res_js.text
    assert "handleMappingChange" in res_js.text


def test_command_palette_static_assets_verified(client: TestClient) -> None:
    """Verifies the Apple-grade Command Palette (⌘K / Ctrl+K) elements and handlers."""
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "modal-command-palette" in res_html.text
    assert "btn-command-palette" in res_html.text
    assert "palette-search-input" in res_html.text

    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "initCommandPalette" in res_js.text
    assert "openCommandPalette" in res_js.text
    assert "renderPaletteResults" in res_js.text

    res_css = client.get("/style.css")
    assert res_css.status_code == 200
    assert "recon-palette-backdrop" in res_css.text
    assert "recon-palette-container" in res_css.text


def test_living_flow_and_dynamic_island_static_assets_verified(client: TestClient) -> None:
    """Verifies Living Data Flow Canvas (particles, conduit bubble) and Dynamic Island."""
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "recon-dynamic-island" in res_html.text
    assert "island-pill-trigger" in res_html.text
    assert "island-expanded-tray" in res_html.text
    assert "island-primary-action" in res_html.text
    assert "flow-svg-canvas" in res_html.text
    assert "flow-chips-layer" in res_html.text

    res_css = client.get("/style.css")
    assert res_css.status_code == 200
    assert "flow-packet-particle" in res_css.text
    assert "flow-conduit-bubble" in res_css.text
    assert "recon-dynamic-island" in res_css.text
    assert "island-pill" in res_css.text
    assert "island-expanded-tray" in res_css.text

    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "flow-packet-particle" in res_js.text
    assert "animateMotion" in res_js.text
    assert "flow-conduit-bubble" in res_js.text
    assert "initDynamicIsland" in res_js.text
    assert "updateDynamicIsland" in res_js.text
    assert "executeDynamicIslandAction" in res_js.text


def test_morphing_diff_and_gutter_minimap_static_assets_verified(client: TestClient) -> None:
    """Verifies Before-After Morphing Diff Inspector and Xcode-Style Gutter Minimap."""
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "morphing-diff-view" in res_html.text
    assert "diff-scrub-input" in res_html.text
    assert "morph-wipe-card" in res_html.text
    assert "flow-minimap-gutter" in res_html.text
    assert "minimap-track" in res_html.text

    res_css = client.get("/style.css")
    assert res_css.status_code == 200
    assert "morph-diff-container" in res_css.text
    assert "morph-scrub-slider" in res_css.text
    assert "morph-wipe-card" in res_css.text
    assert "morph-sample-card" in res_css.text
    assert "flow-minimap-gutter" in res_css.text
    assert "minimap-marker" in res_css.text

    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "computeTransformedValue" in res_js.text
    assert "renderMinimapGutter" in res_js.text
    assert "queueFlowReset" in res_js.text
    assert "morph-wipe-target" in res_js.text
    assert "minimap-track" in res_js.text



