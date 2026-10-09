"""Unit tests for deterministic integration risk rules."""

from pathlib import Path
import pytest

from recon.contracts.loader import load_target_contract
from recon.ingestion.csv_loader import load_csv
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.risks.evaluator import evaluate_risks
from recon.risks.models import Severity


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


def test_risks_on_synthetic_nyc_311(fixtures_dir: Path):
    """Verifies expected risk findings on the synthetic NYC 311 dataset."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_path = fixtures_dir / "target_contract_service_request.json"

    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)
    plan = propose_mappings(profile, contract)

    assessment = evaluate_risks(profile, contract, plan)

    # In synthetic fixture, all required fields are mapped, so no R001
    r001_findings = [f for f in assessment.findings if f.rule_id == "R001_MISSING_REQUIRED_FIELD"]
    assert len(r001_findings) == 0

    # Date parsing risk R004 should be detected for created_at
    r004_findings = [f for f in assessment.findings if f.rule_id == "R004_DATE_PARSING_RISK"]
    assert any("created_at" in f.affected_fields for f in r004_findings)

    # Checks run accounting
    assert "R001_MISSING_REQUIRED_FIELD" in assessment.checks_run
    assert "R003_NULLABILITY_CONFLICT" in assessment.checks_run


def test_rule_r001_missing_required_field(fixtures_dir: Path):
    """Verifies R001 triggers CRITICAL severity when required target field is unmapped."""
    csv_path = fixtures_dir / "synthetic_nyc_311.csv"
    contract_dict = {
        "contract_name": "test_missing_required",
        "fields": {
            "critical_id": {"name": "critical_id", "target_type": "string", "required": True},
        },
    }
    contract = load_target_contract(contract_dict)
    dataset = load_csv(csv_path)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    assessment = evaluate_risks(profile, contract, plan)

    assert assessment.is_blocked is True
    assert len(assessment.critical_findings) == 1
    f = assessment.critical_findings[0]
    assert f.rule_id == "R001_MISSING_REQUIRED_FIELD"
    assert f.severity == Severity.CRITICAL
    assert "critical_id" in f.affected_fields


def test_rule_r002_incompatible_types(tmp_path: Path):
    """Verifies R002 triggers CRITICAL severity when source string cannot map to target integer."""
    csv_file = tmp_path / "incompatible.csv"
    csv_file.write_text("code\nabc\ndef\n", encoding="utf-8")

    contract_dict = {
        "contract_name": "test_incompatible",
        "fields": {
            "code": {"name": "code", "target_type": "integer", "required": True},
        },
    }
    contract = load_target_contract(contract_dict)
    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    assessment = evaluate_risks(profile, contract, plan)

    r002 = [f for f in assessment.findings if f.rule_id == "R002_INCOMPATIBLE_TYPES"]
    assert len(r002) == 1
    assert r002[0].severity == Severity.CRITICAL


def test_rule_r003_nullability_conflict(tmp_path: Path):
    """Verifies R003 flags nulls present in non-nullable target fields."""
    csv_file = tmp_path / "has_nulls.csv"
    csv_file.write_text('name\nalice\n""\nbob\n', encoding="utf-8")

    contract_dict = {
        "contract_name": "test_nullability",
        "fields": {
            "name": {"name": "name", "target_type": "string", "required": True, "nullable": False},
        },
    }
    contract = load_target_contract(contract_dict)
    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    assessment = evaluate_risks(profile, contract, plan)

    r003 = [f for f in assessment.findings if f.rule_id == "R003_NULLABILITY_CONFLICT"]
    assert len(r003) == 1
    assert r003[0].severity == Severity.CRITICAL
    assert "name" in r003[0].affected_fields
    assert "1 nulls" in r003[0].evidence


def test_rule_r005_enum_violation(tmp_path: Path):
    """Verifies R005 triggers HIGH severity when source values violate target allowed_values."""
    csv_file = tmp_path / "enum_data.csv"
    csv_file.write_text("status\nOPEN\nUNKNOWN_STATUS\n", encoding="utf-8")

    contract_dict = {
        "contract_name": "test_enums",
        "fields": {
            "status": {
                "name": "status",
                "target_type": "string",
                "required": True,
                "allowed_values": ["OPEN", "CLOSED"],
            },
        },
    }
    contract = load_target_contract(contract_dict)
    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    assessment = evaluate_risks(profile, contract, plan)

    r005 = [f for f in assessment.findings if f.rule_id == "R005_ENUM_VIOLATION"]
    assert len(r005) == 1
    assert r005[0].severity == Severity.HIGH
    assert "UNKNOWN_STATUS" in r005[0].evidence
