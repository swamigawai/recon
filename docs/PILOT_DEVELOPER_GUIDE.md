# Recon Developer Pilot Guide (v1.0)
**The Integration Readiness Engine**
> *"Know what will break before you build the integration."*

---

## 1. Pilot Testing Status

> [!IMPORTANT]
> **PILOT TESTING STATUS: NOT TESTED — HUMAN VALIDATION REQUIRED**  
> While the engine logic, test suites (151 passing tests), CI preflight gate, and REST API have been validated deterministically, actual end-user human testing with independent external engineers has **not yet been conducted**. This guide is prepared specifically to onboard human pilot participants.

---

## 2. Pilot Objectives

This controlled local pilot evaluates whether an independent software engineer can:
1. Ingest an unfamiliar third-party dataset and a target schema contract.
2. Review automated data profiling and understand column types and data anomalies.
3. Review evidence-backed source-to-target mapping proposals without AI hallucination.
4. Supply explicit human approvals and overrides for ambiguous or unmapped required fields.
5. Generate and inspect reviewable Python adapter code.
6. Validate data transformations in an isolated sandbox with zero data loss ($N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$).
7. Download full valid outputs, quarantine diagnostics, versioned mapping specifications, and readiness reports.
8. Run headless preflight gate checks (`recon gate`) in local terminal or CI/CD pipelines.

---

## 3. Quick Start (< 2 Minutes)

### Prerequisites
- Python 3.11+ installed
- Git

### 1. Installation
Clone the repository and install Recon in editable mode:
```bash
git clone <repo-url> recon
cd recon
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2. Verify Installation
Run the automated test suite:
```bash
python -m pytest tests -q
# Expected: 151 passed in ~25-30 seconds
```

### 3. Launch Local Developer Web Studio
Start the local server:
```bash
recon web --port 8000
# or: recon serve --port 8000
```
Open your browser to: **[http://localhost:8000](http://localhost:8000)** (or `http://127.0.0.1:8000`)

---

## 4. Guided Pilot Scenarios

Recon includes 3 pre-packaged domain fixtures for pilot testing:

| Scenario | Domain | Source Dataset | Target Contract | Primary Test Objective |
| :--- | :--- | :--- | :--- | :--- |
| **A** | **Municipal Services** | `tests/fixtures/synthetic_nyc_311.csv` | `tests/fixtures/target_contract_service_request.json` | High auto-match rate, clean direct transformations, exit code 0. |
| **B** | **B2B Vendor Invoicing** | `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv` | `tests/fixtures/target_contract_gate09_pilot_b2b.json` | Unfamiliar headers requiring human overrides, duplicate rows, zero-loss quarantine. |
| **C** | **Dispatch & Freight** | `tests/fixtures/freight_manifest_raw.csv` | `tests/fixtures/target_contract_freight_manifest.json` | Type casts (floats, timestamps), enum validation, isolated adapter review. |

---

## 5. Walkthrough: Scenario B (Unfamiliar Schema & Quarantine)

### Step 1: Ingestion & Profiling (Screens 01 & 02)
1. In the Web UI, select **"gate09_pilot_b2b_vendor_invoices.csv"** under Sample Source Dataset (or upload the file).
2. Select **"target_contract_gate09_pilot_b2b.json"** under Sample Target Contract.
3. Click **"Run Preflight Assessment"**.
4. **Observe:** Recon profiles all 14 columns, identifies 1 duplicate row, calculates null percentages, and computes a SHA-256 fingerprint.

### Step 2: Mapping Review Studio & Flow Graph (Screen 03)
1. Inspect the mapping table and the interactive **Flow Graph** canvas.
   - The Flow Graph visualizes connections between Source columns (left) and Target contract fields (right) via live SVG connectors.
   - Dual-mode editing: Reassigning a source column in either the dropdown table or the Flow Graph immediately synchronizes both views.
2. Notice that unfamiliar required target fields (`invoice_id`, `supplier_gstin`, `buyer_pan`, `destination_pin`) are marked **UNRESOLVED** in red.
3. **Recon does NOT guess.** It leaves unfamiliar fields unresolved rather than fabricating mappings.
4. **Contextual Inspector:**
   - Hover over any field node or table row to reveal the Inspector drawer, which displays field specifications, data types, regex patterns, nullability constraints, and the exact evidence breakdown.
   - Click to **Pin** the inspector in place; press `I` to toggle it or `Esc` to close.
5. Select the appropriate source fields using the dropdown selectors or Flow Graph nodes:
   - `invoice_id` ➔ map to `doc_number`
   - `supplier_gstin` ➔ map to `gst_reg_no`
   - `buyer_pan` ➔ map to `entity_pan`
   - `destination_pin` ➔ map to `postal_code_primary`
6. Enter your reviewer name (e.g. `pilot_engineer`) and click **"Approve Plan & Generate Adapter"**.

### Step 3: Risk Assessment & Blocker Audit (Screen 04)
1. Review identified risks. High-severity risks (e.g. date format parsing, type conversions) are highlighted with actionable suggestions.
2. Verify that all critical blockers are resolved once required fields are mapped.

### Step 4: Adapter Inspection & Sandbox Validation (Screens 05 & 06)
1. Inspect the generated Python adapter code. It is deterministic, pure Python with no AI dependencies.
2. Review the Validation Results:
   - **Total Input Records:** 12
   - **Valid Output Records:** 5
   - **Quarantined Records:** 7
   - **Accounting Equation:** $12 = 5 + 7$ (Balanced, Zero Data Loss)
3. Check the quarantined records drawer. Notice that each quarantine record provides specific, human-readable diagnostics (e.g. invalid GSTIN pattern, invalid PIN length, illegal enum value `WRITTEN_OFF`).

### Step 5: Export Artifacts (Screen 07)
Download each artifact from Screen 07:
- **Adapter Code:** `.py` file
- **Valid Transformed Records:** `.jsonl` file (all 5 valid records)
- **Quarantined Records:** `.jsonl` file with failure diagnostics (all 7 records)
- **Readiness Report:** Markdown or JSON format
- **Reusable Mapping Spec:** `recon_mapping_spec.json` (versioned specification)

---

## 6. Headless CI/CD Preflight Gate

To run Recon in your CI pipeline or pre-commit hook:

### 1. Test Gate Passing (Exit Code 0)
```bash
recon gate \
  --source tests/fixtures/synthetic_nyc_311.csv \
  --contract tests/fixtures/target_contract_service_request.json \
  --json
```

### 2. Test Gate Blocking (Exit Code 1)
```bash
recon gate \
  --source tests/fixtures/warehouse_manifest_unfamiliar.csv \
  --contract tests/fixtures/target_contract_service_request.json \
  --json
```

### 3. Run Preflight Gate Demonstration Script
```bash
python scripts/ci_preflight_demo.py
```

---

## 7. Pilot Feedback Questionnaire

Please complete this evaluation after running the scenarios:

1. **Setup & Time-to-First-Assessment:**
   - Did installation and first assessment complete within 2 minutes?
   - Any dependency or environment friction?
2. **Schema & Profiling Clarity:**
   - Did the source profile clearly communicate data types, nulls, and duplicate rows?
3. **Zero-Hallucination Mapping Guardrails:**
   - Did the engine correctly leave ambiguous fields unresolved rather than guessing?
   - How intuitive was the human override dropdown workflow?
4. **Risk Assessment Explanations:**
   - Were risk finding codes (e.g. `R001`, `R004`) clear and actionable?
5. **Adapter Quality & Trust:**
   - Is the generated Python adapter code readable, reviewable, and production-deployable?
   - Would you feel confident checking this adapter into source control?
6. **Zero Data Loss Invariant:**
   - Was the quarantine accounting ($N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$) transparent and trustworthy?
7. **Mapping Specification Portability:**
   - Did exporting and re-importing `recon_mapping_spec.json` save time across repeated runs?
8. **Universal Contracts Ingestion:**
   - Did you test your own OpenAPI or JSON Schema files? Did they parse cleanly?
9. **Headless CI/CD Gate:**
   - Are exit codes (0, 1, 2) and `--json` stdout output well-suited for your CI/CD pipelines?
10. **Overall Rating & Recommendation:**
    - On a scale of 1-10, how likely are you to recommend Recon for enterprise preflight integration audits?

---

## 8. Troubleshooting & FAQ

- **Port 8000 already in use:** Run `recon serve --port 8080`.
- **Custom contract fails to load:** Ensure the JSON file is valid JSON and has either a Recon native format, JSON Schema (`$schema`), or OpenAPI (`openapi: 3.x`).
- **Where are outputs stored during web sessions?** Web sessions store temporary working files in isolated temporary directories that are cleaned up upon session termination.

---

## 9. Security Boundary & Operational Scope

> [!WARNING]
> **IN-PROCESS RESTRICTION ONLY — NOT AN OS-LEVEL SANDBOX**
>
> 1. **Execution Model:** Recon validates generated Python adapters via in-process AST restricted compilation (`compile_adapter_sandbox`). This blocks dangerous builtins (`__import__`, `open`, `eval`, `exec`, `os`, `sys`, `subprocess`).
> 2. **Boundary Limitation:** This is an in-process language restriction, **NOT** an OS-level sandbox. It does not provide Linux kernel cgroup, seccomp, or container-level isolation.
> 3. **Controlled Local Pilot Only:** Recon is strictly intended for **controlled local developer evaluation** and managed internal engineering pilots. Do not host Recon as a public multi-tenant service or execute untrusted third-party code without external VM or container isolation.
> 4. **Network & File Boundaries:** Remote `$ref` resolution in schemas is disabled by default to prevent SSRF. Ingested files are strictly processed from local file paths or web upload streams within size limits.
