"""Runnable demonstration script showing Recon as a CI/CD preflight gate.

Simulates how a CI runner (e.g. GitHub Actions, GitLab CI, Jenkins) invokes
`recon gate` to block or allow deployment before adapter code reaches production.
"""

import json
from pathlib import Path
import subprocess
import sys


def run_gate(description: str, *args: str) -> int:
    print("\n" + "=" * 70)
    print(f"RUNNING SCENARIO: {description}")
    print("=" * 70)
    cmd = [sys.executable, "-m", "recon.cli", "gate", *args]
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Exit Code: {result.returncode}")

    if "--json" in args:
        try:
            parsed = json.loads(result.stdout)
            print("Parsed JSON Output:")
            print(json.dumps(parsed, indent=2))
        except Exception as exc:
            print(f"Failed to parse JSON: {exc}")
            print(f"Raw stdout: {result.stdout}")
    else:
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

    return result.returncode


def main() -> None:
    fixtures = Path("tests/fixtures")
    contract = fixtures / "target_contract_service_request.json"
    clean_csv = fixtures / "synthetic_nyc_311.csv"
    corrupted_csv = fixtures / "corrupted_nyc_311.csv"
    unfamiliar_csv = fixtures / "warehouse_manifest_unfamiliar.csv"

    print("====================================================================")
    print(" RECON CI/CD PREFLIGHT GATE DEMONSTRATION")
    print(" 'Know what will break before you build the integration.'")
    print("====================================================================")

    # Scenario 1: Clean data with automatic mapping (JSON output)
    code1 = run_gate(
        "1. Clean Dataset Preflight Check (PASS -> Exit Code 0)",
        "--source", str(clean_csv),
        "--contract", str(contract),
        "--json",
    )
    assert code1 == 0, f"Expected 0, got {code1}"

    # Scenario 2: Unfamiliar schema with missing required fields (BLOCKED)
    code2 = run_gate(
        "2. Unfamiliar Schema Missing Required Fields (BLOCKED -> Exit Code 1)",
        "--source", str(unfamiliar_csv),
        "--contract", str(contract),
        "--json",
    )
    assert code2 == 1, f"Expected 1, got {code2}"

    # Scenario 3: Corrupted dataset exceeding 0% quarantine tolerance
    code3 = run_gate(
        "3. Corrupted Dataset Exceeding Quarantine Threshold (FAIL -> Exit Code 1)",
        "--source", str(corrupted_csv),
        "--contract", str(contract),
        "--max-quarantine-pct", "0.0",
        "--json",
    )
    assert code3 == 1, f"Expected 1, got {code3}"

    # Scenario 4: Bad CLI argument (syntax/input error)
    code4 = run_gate(
        "4. Nonexistent Source Data File (ERROR -> Exit Code 2)",
        "--source", "nonexistent_source.csv",
        "--contract", str(contract),
    )
    assert code4 == 2, f"Expected 2, got {code4}"

    print("\n" + "=" * 70)
    print("ALL CI PREFLIGHT GATE SCENARIOS DEMONSTRATED SUCCESSFULLY!")
    print("Exit code semantics:")
    print("  0 = Integration Ready (Deploy adapter)")
    print("  1 = Integration Blocked (Halt deployment; notify engineer)")
    print("  2 = Invalid Configuration / File Error (Fix pipeline inputs)")
    print("  3 = Internal Engine Error (Bug in pipeline runner)")
    print("====================================================================")


if __name__ == "__main__":
    main()
