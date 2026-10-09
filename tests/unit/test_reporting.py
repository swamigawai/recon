"""Unit tests for human-readable and machine-readable readiness reports."""

import json
from pathlib import Path
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.ingestion.csv_loader import load_csv
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import (
    build_readiness_report,
    export_reports,
    render_markdown_report,
)
from recon.reporting.models import ReadinessReport, ReadinessState
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


def test_end_to_end_readiness_report(fixtures_dir: Path, tmp_path: Path):
    """Verifies complete end-to-end report generation, formatting, and file export."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_path = fixtures_dir / "target_contract_service_request.json"

    # Full pipeline execution
    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)
    plan = propose_mappings(profile, contract)
    risks = evaluate_risks(profile, contract, plan)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
        approved_plan=approved_plan,
        validation_result=validation,
    )

    assert isinstance(report, ReadinessReport)
    assert report.contract_name == "service_request_target_contract"
    assert report.verified_facts["total_source_rows"] == 10
    assert report.verified_facts["total_source_columns"] == 15
    assert report.adapter_validation is not None
    assert report.adapter_validation.is_ready is True

    # Render Markdown
    md_content = render_markdown_report(report)
    assert "# Recon Integration Readiness Report" in md_content
    assert "Risk Assessment Summary" in md_content
    assert "Verified Profiling Facts" in md_content
    assert "Adapter Validation & Test Outcomes" in md_content

    # Export reports
    json_path, md_path = export_reports(report, tmp_path)
    assert json_path.exists()
    assert md_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        reloaded = json.load(f)
    assert reloaded["source_file"] == "synthetic_nyc_311.csv"
    assert reloaded["readiness_state"] in ("READY", "NEEDS_REVIEW", "BLOCKED")


def test_blocked_state_on_unmapped_required_field(fixtures_dir: Path):
    """Verifies that an unmapped required target field results in BLOCKED state."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_dict = {
        "contract_name": "missing_required_contract",
        "fields": {
            "unmapped_id": {"name": "unmapped_id", "target_type": "string", "required": True},
        },
    }
    contract = load_target_contract(contract_dict)
    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    risks = evaluate_risks(profile, contract, plan)

    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
    )

    assert report.readiness_state == ReadinessState.BLOCKED
    assert len(report.blocking_reasons) > 0
    assert any("unmapped_id" in b for b in report.blocking_reasons)
