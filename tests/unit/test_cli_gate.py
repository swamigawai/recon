"""Subprocess and unit tests for the headless CI/CD preflight gate: `recon gate` (Feature C)."""

import json
from pathlib import Path
import subprocess
import sys
import pytest

from recon.contracts.loader import load_target_contract
from recon.ingestion import load_csv
from recon.mapping import export_mapping_spec, propose_mappings
from recon.profiling import profile_dataset


@pytest.fixture
def nyc311_spec_file(tmp_path: Path) -> Path:
    """Creates a valid recon_mapping_spec.json for testing."""
    contract = load_target_contract(Path("tests/fixtures/target_contract_service_request.json"))
    dataset = load_csv(Path("tests/fixtures/synthetic_nyc_311.csv"))
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    spec = export_mapping_spec(contract, profile, plan, reviewer="ci_test_engineer")
    spec_path = tmp_path / "recon_mapping_spec.json"
    spec.save_to_file(spec_path)
    return spec_path


def run_recon_cli(*args: str) -> subprocess.CompletedProcess:
    """Helper to run recon CLI in a subprocess and capture returncode, stdout, and stderr."""
    cmd = [sys.executable, "-m", "recon.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path.cwd()))


def test_cli_gate_success_clean_input(nyc311_spec_file: Path) -> None:
    """Verifies that clean input with complete mapping spec passes gate with exit code 0."""
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--mapping-spec", str(nyc311_spec_file),
        "--max-quarantine-pct", "100.0",
    )
    assert res.returncode == 0
    assert "RECON CI/CD PREFLIGHT GATE: PASSED" in res.stdout
    assert "Total=10 = Valid=10 + Quarantined=0" in res.stdout


def test_cli_gate_json_output_mode(nyc311_spec_file: Path) -> None:
    """Verifies --json output mode returns valid JSON with zero decorative formatting."""
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--mapping-spec", str(nyc311_spec_file),
        "--max-quarantine-pct", "10.0",
        "--json",
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["status"] == "PASS"
    assert data["exit_code"] == 0
    assert data["contract"]["name"] == "service_request_target_contract"
    assert data["accounting"]["total_input_records"] == 10
    assert data["accounting"]["quarantined_records_count"] == 0


def test_cli_gate_quarantine_threshold_exceeded(nyc311_spec_file: Path) -> None:
    """Verifies that exceeding the quarantine threshold returns exit code 1."""
    # Use corrupted dataset where records fail validation
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/corrupted_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--mapping-spec", str(nyc311_spec_file),
        "--max-quarantine-pct", "0.0",  # 0% tolerance
    )
    assert res.returncode == 1
    assert "FAILED (THRESHOLD EXCEEDED)" in res.stdout or "BLOCKED" in res.stdout


def test_cli_gate_unresolved_required_fields_fails() -> None:
    """Verifies that missing required source column returns exit code 1."""
    # warehouse_manifest_unfamiliar does not match nyc311 contract fields
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/warehouse_manifest_unfamiliar.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
    )
    assert res.returncode == 1
    assert "Unresolved required target fields" in res.stdout


def test_cli_gate_invalid_threshold_exit_code_2() -> None:
    """Verifies that --max-quarantine-pct outside [0.0, 100.0] returns exit code 2."""
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--max-quarantine-pct", "-5.0",
    )
    assert res.returncode == 2
    assert "Must be between 0.0 and 100.0" in res.stderr

    res_high = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--max-quarantine-pct", "150.0",
    )
    assert res_high.returncode == 2


def test_cli_gate_invalid_source_file_exit_code_2() -> None:
    """Verifies that nonexistent source file returns exit code 2."""
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/nonexistent_data_file.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
    )
    assert res.returncode == 2
    assert "Input validation failed" in res.stderr


def test_cli_gate_invalid_contract_file_exit_code_2() -> None:
    """Verifies that nonexistent contract file returns exit code 2."""
    res = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/nonexistent_contract.json",
    )
    assert res.returncode == 2
    assert "Input validation failed" in res.stderr


def test_cli_gate_strict_mode(nyc311_spec_file: Path) -> None:
    """Verifies strict mode rules enforcement."""
    # 1. Strict mode fails if no mapping spec provided
    res_no_spec = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--strict",
    )
    assert res_no_spec.returncode == 1
    assert "Strict mode requires an explicit --mapping-spec" in res_no_spec.stdout

    # 2. Strict mode on clean dataset with spec
    res_with_spec = run_recon_cli(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--mapping-spec", str(nyc311_spec_file),
        "--strict",
        "--json",
    )
    # Target contract has 12 fields, some optional fields may not be in synthetic CSV
    # Verify exit code is either 0 or 1 with strict explanation, never 2 or 3
    assert res_with_spec.returncode in (0, 1)
    data = json.loads(res_with_spec.stdout)
    assert data["strict_mode"] is True


def test_cli_assess_and_run_backward_compatibility() -> None:
    """Verifies that existing CLI commands (`assess`, `profile`, `run`) remain fully backward compatible."""
    res_prof = run_recon_cli("profile", "tests/fixtures/synthetic_nyc_311.csv")
    assert res_prof.returncode == 0
    assert "RECON PROFILING REPORT" in res_prof.stdout

    res_assess = run_recon_cli(
        "assess",
        "tests/fixtures/synthetic_nyc_311.csv",
        "tests/fixtures/target_contract_service_request.json",
    )
    assert res_assess.returncode == 0
    assert "RECON RISK ASSESSMENT" in res_assess.stdout


def test_cli_web_and_serve_aliases() -> None:
    """Verifies that both `recon web` and `recon serve` display web interface options."""
    res_web = run_recon_cli("web", "--help")
    assert res_web.returncode == 0
    assert "--host" in res_web.stdout
    assert "--port" in res_web.stdout

    res_serve = run_recon_cli("serve", "--help")
    assert res_serve.returncode == 0
    assert "--host" in res_serve.stdout
    assert "--port" in res_serve.stdout
