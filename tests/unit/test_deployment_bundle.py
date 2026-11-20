"""Unit tests for the Enterprise Deployability Pack and CI/CD bundle generator."""

import io
import json
import zipfile
import pytest
from fastapi.testclient import TestClient

from recon.deploy.bundle import (
    create_deployment_bundle_zip,
    generate_bundle_readme,
    generate_dockerfile,
    generate_github_workflow,
)
from recon.server.app import create_app


def test_dockerfile_generation():
    """Verifies that generated Dockerfile follows enterprise container security best practices."""
    dockerfile = generate_dockerfile(adapter_name="ecommerce_adapter", python_version="3.11-slim")
    
    assert "FROM python:3.11-slim" in dockerfile
    assert "useradd -u 10001 -g recon" in dockerfile
    assert "USER recon:recon" in dockerfile
    assert 'ENTRYPOINT ["python", "adapter.py"]' in dockerfile
    assert "RECON_AIRGAP=1" in dockerfile


def test_github_workflow_generation():
    """Verifies that generated GitHub Actions pipeline enforces strict zero-loss gating."""
    workflow = generate_github_workflow(contract_name="ecommerce_order", quarantine_threshold=0.02)
    
    assert "name: Recon Data Conformance Gate" in workflow
    assert "actions/checkout@v4" in workflow
    assert "actions/setup-python@v5" in workflow
    assert "python -m recon.cli gate" in workflow
    assert "--quarantine-threshold 0.02" in workflow


def test_create_deployment_bundle_zip():
    """Verifies that in-memory deployment pack ZIP contains all 7 production deliverables."""
    adapter_py = "def transform_record(r): return r, []"
    contract_dict = {"contract_name": "billing", "version": "1.0.0", "fields": {}}
    spec_dict = {"spec_version": "1.0.0", "mappings": []}
    report_md = "# Readiness Report\nStatus: PASS"

    zip_bytes = create_deployment_bundle_zip(
        session_id="test_sess_123",
        adapter_code=adapter_py,
        contract_json=contract_dict,
        mapping_spec_json=spec_dict,
        report_md=report_md,
        contract_name="billing",
        version="1.0.0",
        pass_rate=100.0,
        total_records=5000,
    )

    assert len(zip_bytes) > 0
    buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buffer, "r") as zf:
        namelist = zf.namelist()
        expected_files = [
            "adapter.py",
            "target_contract.json",
            "recon_mapping_spec.json",
            "readiness_report.md",
            "Dockerfile",
            ".github/workflows/recon-gate.yml",
            "README.md",
        ]
        for ef in expected_files:
            assert ef in namelist, f"Missing {ef} in bundle"
            content = zf.read(ef).decode("utf-8")
            assert len(content.strip()) > 0, f"Empty content in {ef}"

        # Verify target_contract.json is valid JSON
        contract_content = json.loads(zf.read("target_contract.json").decode("utf-8"))
        assert contract_content["contract_name"] == "billing"

        # Verify README contains pass rate
        readme_content = zf.read("README.md").decode("utf-8")
        assert "100.0%" in readme_content


def test_api_deployment_bundle_and_preview_endpoints():
    """Tests /api/download/deployment-bundle, /api/deployment/dockerfile, and /api/deployment/github-workflow."""
    app = create_app()
    client = TestClient(app)

    # 1. Run assessment
    res_assess = client.post(
        "/api/assess",
        data={
            "sample_dataset_id": "synthetic_nyc_311",
            "sample_contract_id": "target_contract_service_request",
        },
    )
    assert res_assess.status_code == 200
    session_id = res_assess.json()["session_id"]

    # 2. Approve and generate adapter
    res_approve = client.post(
        "/api/approve-and-generate",
        json={"session_id": session_id, "reviewer": "test_engineer", "overrides": {}},
    )
    assert res_approve.status_code == 200

    # 3. Download ZIP bundle
    res_bundle = client.get(f"/api/download/deployment-bundle/{session_id}")
    assert res_bundle.status_code == 200
    assert res_bundle.headers["content-type"] == "application/zip"
    assert "attachment; filename=\"recon_deployment_bundle_" in res_bundle.headers["content-disposition"]

    # Verify zip content
    with zipfile.ZipFile(io.BytesIO(res_bundle.content), "r") as zf:
        namelist = zf.namelist()
        assert "adapter.py" in namelist
        assert "Dockerfile" in namelist
        assert ".github/workflows/recon-gate.yml" in namelist
        assert "README.md" in namelist

    # 4. Preview Dockerfile
    res_docker = client.get(f"/api/deployment/dockerfile/{session_id}")
    assert res_docker.status_code == 200
    assert "FROM python:" in res_docker.text
    assert "USER recon:recon" in res_docker.text

    # 5. Preview GitHub Workflow
    res_wf = client.get(f"/api/deployment/github-workflow/{session_id}")
    assert res_wf.status_code == 200
    assert "name: Recon Data Conformance Gate" in res_wf.text
    assert "python -m recon.cli gate" in res_wf.text

    # 6. Resilient preview on arbitrary/unapproved or non-cached session ID
    res_docker_fallback = client.get("/api/deployment/dockerfile/unknown_session_id")
    assert res_docker_fallback.status_code == 200
    assert "FROM python:" in res_docker_fallback.text

    res_wf_fallback = client.get("/api/deployment/github-workflow/unknown_session_id")
    assert res_wf_fallback.status_code == 200
    assert "name: Recon Data Conformance Gate" in res_wf_fallback.text


def test_deployment_bundle_frontend_assets_present():
    """Asserts that all HTML, CSS, and JS components for Enterprise Deploy Pack and code preview modal exist."""
    app = create_app()
    client = TestClient(app)

    # index.html
    res_html = client.get("/")
    assert res_html.status_code == 200
    html = res_html.text
    assert "deploy-pack-hero" in html
    assert "modal-code-preview" in html
    assert "art-dl-bundle" in html
    assert "btn-preview-dockerfile" in html
    assert "btn-preview-workflow" in html
    assert "btn-copy-code-preview" in html

    # style.css
    res_css = client.get("/style.css")
    assert res_css.status_code == 200
    css = res_css.text
    assert ".deploy-pack-hero" in css
    assert ".bundle-file-pill" in css

    # app.js
    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    js = res_js.text
    assert "getAuthHeaders" in js
    assert "ReconStateMachine" in js
    assert "showDockerfilePreview" in js
    assert "showWorkflowPreview" in js
    assert "openCodePreviewModal" in js
    assert "initCodePreviewModal" in js
    assert "download-deploy-bundle" in js

