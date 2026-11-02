"""Unit tests for Recon installation resilience, self-healing launchers, and the doctor diagnostic engine."""

import json
from pathlib import Path
import subprocess
import sys
import pytest

from scripts.fde_launcher import check_python_version, resolve_available_port


def test_recon_doctor_cli_human_output() -> None:
    """Verifies that `recon doctor` runs all checks and outputs a clean report with exit code 0."""
    res = subprocess.run(
        [sys.executable, "-m", "recon.cli", "doctor"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "RECON ENVIRONMENT DIAGNOSTIC REPORT" in res.stdout
    assert "[PASS]   Python Runtime" in res.stdout
    assert "[PASS]   Core Dependencies" in res.stdout
    assert "[PASS]   File System I/O" in res.stdout
    assert "[PASS]   UTF-8 & BOM Engine" in res.stdout
    assert "[PASS]   Pipeline Invariants" in res.stdout
    assert "Environment is 100% HEALTHY" in res.stdout


def test_recon_doctor_cli_json_mode() -> None:
    """Verifies that `recon doctor --json` outputs parseable JSON with HEALTHY status."""
    res = subprocess.run(
        [sys.executable, "-m", "recon.cli", "doctor", "--json"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    # Isolate JSON payload
    json_start = res.stdout.find("{")
    assert json_start != -1
    data = json.loads(res.stdout[json_start:])
    assert data["status"] == "HEALTHY"
    check_names = [c["check"] for c in data["checks"]]
    assert "Python Runtime" in check_names
    assert "Core Dependencies" in check_names
    assert "File System I/O" in check_names
    assert "UTF-8 & BOM Engine" in check_names
    assert "Pipeline Invariants" in check_names
    assert all(c["passed"] for c in data["checks"])


def test_fde_launcher_helpers() -> None:
    """Verifies the core helper functions of fde_launcher.py."""
    assert check_python_version() is True
    # Test port resolver
    port, is_recon = resolve_available_port(8000)
    assert isinstance(port, int)
    assert port >= 8000


def test_packaging_artifacts_presence() -> None:
    """Verifies that universal install artifacts exist for cross-platform zero-friction installation."""
    root = Path(__file__).resolve().parents[2]
    assert (root / "requirements.txt").is_file()
    assert (root / "requirements-dev.txt").is_file()
    assert (root / "setup.py").is_file()
    assert (root / "pyproject.toml").is_file()
    assert (root / "start.bat").is_file()
    assert (root / "start.sh").is_file()

    # Ensure requirements.txt lists all mandatory core libraries
    req_text = (root / "requirements.txt").read_text(encoding="utf-8")
    assert "fastapi" in req_text
    assert "uvicorn" in req_text
    assert "pydantic" in req_text
    assert "python-multipart" in req_text
