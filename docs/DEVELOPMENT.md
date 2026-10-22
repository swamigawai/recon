# Recon — Developer & Contributor Guide

**Product:** Recon — The Integration Readiness Engine  
**Status:** `[VERIFIED CONTRIBUTOR SPECIFICATION]`

---

## 1. Prerequisites & Environment Setup

### Required Tooling
- **Python:** 3.11 or higher (Python 3.11.9+ recommended)
- **Git**
- **Virtual Environment Tool:** `venv` (recommended) or `uv`

### Clean Clone Setup

```bash
# 1. Clone repository
git clone https://github.com/swamigawai/recon.git
cd recon

# 2. Create and activate virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Install Recon in editable mode with development dependencies
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

---

## 2. Running Automated Tests

Recon uses `pytest` for all unit, integration, and benchmark tests.

```bash
# Run the complete test suite (152 tests)
pytest

# Run with concise output
pytest -q

# Run specific test suites
pytest tests/unit/ -v                      # Unit tests
pytest tests/benchmark/ -v                 # Real-world benchmark suites
pytest tests/integration/ -v               # End-to-end integration tests
```

### Test Suite Structure

```text
tests/
├── benchmark/                             # Real-world domain benchmarks
│   ├── test_b2b_vendor_invoicing_benchmark.py
│   ├── test_ecommerce_gate03_benchmark.py
│   ├── test_gate06_real_world_edge_cases.py
│   ├── test_gate07_output_correctness.py
│   ├── test_gate08_pilot_scenarios.py
│   ├── test_gate09_controlled_local_pilot.py
│   ├── test_gate12_pilot_validation.py
│   ├── test_mapping_generalization.py
│   ├── test_nyc311_benchmark.py
│   └── test_nyc311_real_5k.py
├── fixtures/                              # Domain datasets and contracts
├── integration/                           # Pipeline end-to-end tests
└── unit/                                  # Component unit tests
    ├── test_adapters_and_validation.py
    ├── test_api_server.py
    ├── test_cli_gate.py
    ├── test_foundation.py
    ├── test_ingestion.py
    ├── test_json_ingestion.py
    ├── test_mapping.py
    ├── test_mapping_spec.py
    ├── test_profiling.py
    ├── test_reporting.py
    ├── test_risks.py
    └── test_universal_contracts.py
```

---

## 3. Running Synthetic Benchmarks

The Gate 19 16-scenario hardened benchmark can be reproduced deterministically:

```bash
# Generate fixtures and independent ground truth
python benchmarks/gate19/scenarios.py

# Execute the benchmark against Baselines A & B
python benchmarks/gate19/runner.py
```

Results are saved to: `benchmarks/gate19/gate19_benchmark_results.json`

---

## 4. Launching the Developer Studio Locally

Start the local preflight web interface:

```bash
# Canonical command:
recon serve --port 8000

# Compatible alias:
recon web --port 8000

# Specify custom host or port:
recon serve --host 127.0.0.1 --port 8080
```

Open your browser to: `http://127.0.0.1:8000`

---

## 5. Testing the Headless Preflight CLI Gate

Run an automated preflight check from your terminal:

```bash
# Pass scenario:
recon gate \
  --source tests/fixtures/synthetic_nyc_311.csv \
  --contract tests/fixtures/target_contract_service_request.json

# Machine-readable JSON output:
recon gate \
  --source tests/fixtures/synthetic_nyc_311.csv \
  --contract tests/fixtures/target_contract_service_request.json \
  --json

# Strict mode with quarantine threshold:
recon gate \
  --source tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv \
  --contract tests/fixtures/target_contract_gate09_pilot_b2b.json \
  --strict \
  --max-quarantine-pct 0.0
```

---

## 6. Code Formatting & Linting

Recon uses `ruff` for linting and style enforcement. Configuration is in `pyproject.toml`.

```bash
# Run linter
ruff check src tests

# Format code
ruff format src tests
```

### Style Guidelines
- **Python:** 3.11+ type annotations on all public functions.
- **Error Handling:** Use explicit, actionable exceptions inheriting from `recon.exceptions.ReconError`.
- **Zero Hallucination:** Heuristics must never silently invent mappings for ambiguous columns.
- **Privacy:** Never print raw data records or PII to console or log output.
