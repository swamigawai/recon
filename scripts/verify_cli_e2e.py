import json
import subprocess
import sys

def run(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def main():
    print("=== 1. CLI VERSION ===")
    code, out, err = run("python -m recon.cli --version")
    print(f"Code: {code}, Output: {out}")
    assert code == 0
    assert "recon" in out.lower()

    print("\n=== 2. CLI PROFILE ===")
    code, out, err = run("python -m recon.cli profile tests/fixtures/synthetic_nyc_311.csv")
    print(f"Code: {code}, Output Snippet:\n{out[:260]}...")
    assert code == 0
    assert "RECON PROFILING REPORT" in out

    print("\n=== 3. CLI ASSESS ===")
    code, out, err = run("python -m recon.cli assess tests/fixtures/synthetic_nyc_311.csv tests/fixtures/target_contract_service_request.json")
    print(f"Code: {code}, Output Snippet:\n{out[:260]}...")
    assert code == 0
    assert "RECON RISK ASSESSMENT" in out

    print("\n=== 4. CLI GATE (PASS - EXIT 0) ===")
    code, out, err = run("python -m recon.cli gate --source tests/fixtures/synthetic_nyc_311.csv --contract tests/fixtures/target_contract_service_request.json --json")
    print(f"Code: {code}")
    data = json.loads(out)
    print(f"Status: {data.get('status')}, Exit Code: {data.get('exit_code')}")
    assert code == 0
    assert data["status"] == "PASS"
    assert data["exit_code"] == 0

    print("\n=== 5. CLI GATE (BLOCK - EXIT 1) ===")
    code, out, err = run("python -m recon.cli gate --source tests/fixtures/warehouse_manifest_unfamiliar.csv --contract tests/fixtures/target_contract_service_request.json --json")
    print(f"Code: {code}")
    data = json.loads(out)
    print(f"Status: {data.get('status')}, Exit Code: {data.get('exit_code')}, Reason: {data.get('exit_reason')[:80]}...")
    assert code == 1
    assert data["status"] == "FAIL"
    assert data["exit_code"] == 1

    print("\n=== 6. CLI GATE (INVALID INPUT - EXIT 2) ===")
    code, out, err = run("python -m recon.cli gate --source non_existent.csv --contract tests/fixtures/target_contract_service_request.json --json")
    print(f"Code: {code}")
    data = json.loads(out)
    print(f"Status: {data.get('status')}, Exit Code: {data.get('exit_code')}, Reason: {data.get('exit_reason')}")
    assert code == 2
    assert data["status"] == "ERROR"
    assert data["exit_code"] == 2

    print("\n=== 7. CLI RUN (END-TO-END WORKFLOW) ===")
    code, out, err = run("python -m recon.cli run tests/fixtures/synthetic_nyc_311.csv tests/fixtures/target_contract_service_request.json --output-dir recon_output")
    print(f"Code: {code}")
    assert code == 0
    assert "RECON INTEGRATION READINESS ENGINE — RUN COMPLETE" in out

    print("\nALL CLI TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    main()
