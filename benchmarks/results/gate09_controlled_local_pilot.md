# Recon Gate 09 — Controlled Local Pilot & Real-World Validation Report

**Product:** Recon — The Integration Readiness Engine  
**Product Promise:** *“Know what will break before you build the integration.”*  
**Date:** October 18, 2026  
**Evaluation Scope:** Complete regression suite, local startup and environment verification, primary B2B pilot scenario with independent ground truth, duplicate record preservation, API/web workflow lifecycle, reliability checks, and security boundaries.  
**Baseline Tests:** 98 passed  
**Final Tests:** **101 passed, 0 failed, 0 skipped in 8.83s**  
**Readiness Status:** **READY FOR CONTROLLED LOCAL PILOT**  
*(Note: Independent developer usability remains unverified / NOT TESTED).*

---

## 1. Executive Summary

Recon Gate 09 prepared the engine for real-world pilot deployment by establishing a copyable, verified local startup procedure, testing an end-to-end B2B vendor invoicing pilot dataset against pre-declared independent ground truth, and proving the zero-data-loss invariant across edge cases including duplicate records, error-like text, and leading zeros.

### Key Gate 09 Findings:
1. **Regression Stability:** All 98 baseline tests reproduced cleanly. With 3 new Gate 09 pilot integration tests, the regression suite now stands at **101 passing tests** (100% pass rate in 8.83s).
2. **Deterministic Pilot Execution:** Across the 12-row pilot dataset, Recon automatically proposed 7 exact/normalized fields, refused to guess on 4 unfamiliar/ambiguous fields, and strictly blocked adapter generation until human overrides were approved.
3. **Zero Data Loss Invariant ($\Delta = 0$):**
   $$\text{Total Input (12)} = \text{Valid Transformed (5)} + \text{Quarantined (7)}$$
   - All 5 valid records matched pre-declared outputs value-by-value.
   - Exact duplicate records were both preserved without silent dropping.
   - Legitimate text resembling an error string (`"ERROR: Client reported damaged outer box..."`) was correctly accepted without false quarantine.
   - All 7 injected faults were quarantined with 100% recall.
4. **Environment Packaging Defect Corrected:** Identified that `fastapi` and `uvicorn` were missing from `pyproject.toml` dependencies, which would have prevented clean installation on fresh machines. Added `fastapi>=0.100.0` and `uvicorn>=0.20.0` to `dependencies`.
5. **Usability Status:** Formally marked as **NOT TESTED** because no second independent human developer was available during this evaluation.

---

## 2. Repository Branch, Commit, and Working-Tree Status

- **Git Branch:** `main`
- **Baseline Commit:** `df8daae` (`feat(benchmark): add real-world B2B vendor invoicing and logistics validation suite`)
- **Working Tree Preservation:** All pre-existing Gate 08 files, benchmarks, and fixtures were preserved. No resets, cleanups, or destructive operations were performed. No git commits or pushes were executed.
- **Untracked Artifacts in Tree:**
  - `benchmarks/results/gate08_full_system_validation.md`
  - `benchmarks/results/gate09_ground_truth_specification.md`
  - `benchmarks/results/gate09_controlled_local_pilot.md`
  - `tests/benchmark/test_gate08_pilot_scenarios.py`
  - `tests/benchmark/test_gate09_controlled_local_pilot.py`
  - Fixtures for Gate 08 & Gate 09 pilot scenarios.

---

## 3. Baseline and Final Test Results

- **Baseline Test Execution:**
  - Command: `python -m pytest D:/recon/tests -v`
  - Result: **98 passed in 9.47s** (0 failed, 0 skipped, 0 errors).
- **Final Test Execution:**
  - Command: `python -m pytest D:/recon/tests -v`
  - Result: **101 passed in 8.83s** (0 failed, 0 skipped, 0 errors).
  - Net Change: +3 automated tests (`test_gate09_pilot_mapping_evidence_and_blocking`, `test_gate09_pilot_transformation_and_zero_loss_accounting`, `test_gate09_pilot_api_workflow_and_session_lifecycle`).

---

## 4. Local Setup and Startup Procedure

Recon runs locally on Windows without cloud services or external API dependencies.

### 4.1 Prerequisites
- Python 3.11+ (verified on Python 3.11.9)
- Git

### 4.2 Installation (Windows PowerShell / CMD)
```powershell
# 1. Clone repository
git clone https://github.com/swamigawai/recon.git
cd recon

# 2. Create and activate virtual environment (recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install Recon in editable mode with development dependencies
python -m pip install -e ".[dev]"
```

### 4.3 Starting the Web Interface
```powershell
# Launch via CLI shortcut:
recon web

# Or launch directly via Python module:
python -m recon.cli web --host 127.0.0.1 --port 8000
```
- **Local URL:** `http://127.0.0.1:8000`
- **Application Startup Output:**
  ```text
  Starting Recon Web Interface at http://127.0.0.1:8000
  INFO: Started server process [PID]
  INFO: Waiting for application startup.
  INFO: Application startup complete.
  INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
  ```

### 4.4 Graceful Shutdown
- Press `CTRL + C` in the running terminal.
- Uvicorn signals shutdown and gracefully closes the event loop.

---

## 5. Pilot Dataset and Target Contract Description

The primary pilot scenario models an enterprise B2B vendor onboarding workflow:

- **Target Contract:** `tests/fixtures/target_contract_gate09_pilot_b2b.json` (11 fields)
  - `invoice_id` (String regex: `^[A-Z0-9\-\/]{3,20}$`, required, non-nullable)
  - `supplier_gstin` (String regex: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`, required, non-nullable)
  - `buyer_pan` (String regex: `^[A-Z]{5}[0-9]{4}[A-Z]{1}$`, required, non-nullable)
  - `billing_date` (ISO-8601 Datetime, required, non-nullable)
  - `net_amount` (Float decimal, required, non-nullable)
  - `tax_amount` (Float decimal, optional, nullable)
  - `hsn_sac_code` (String regex: `^[0-9]{4,8}$`, required, non-nullable)
  - `destination_pin` (String regex: `^[1-9][0-9]{5}$`, required, non-nullable)
  - `bank_ifsc` (String regex: `^[A-Z]{4}0[A-Z0-9]{6}$`, required, non-nullable)
  - `invoice_status` (Enum: `["PENDING", "SETTLED", "DISPUTED", "VOID"]`, required, non-nullable)
  - `dispatch_notes` (String free-text, optional, nullable)

- **Source Dataset:** `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv` (12 rows, 14 columns)
  - Unfamiliar column names: `doc_number`, `gst_reg_no`, `entity_pan`, `postal_code_primary`.
  - Ambiguous / competing column: `postal_code_secondary`.
  - Extraneous columns to omit: `driver_phone_number`, `warehouse_dock_no`.

---

## 6. Independent Ground-Truth Methodology

Independent ground truth was prepared and documented in `benchmarks/results/gate09_ground_truth_specification.md` and `tests/fixtures/gate09_pilot_expected_output.json` **before** executing tests:
- Field-level mapping expectations were declared independently.
- Expected transformed payloads for all valid records were calculated manually.
- Injected faults and their exact error codes were pre-declared.
- Expected results were never derived from adapter output.

---

## 7. Mapping Correctness Results

| Target Contract Field | Source Column in Pilot File | Proposal Status | Proposer Evidence | Human Decision |
| :--- | :--- | :---: | :--- | :--- |
| `invoice_id` | `doc_number` | **UNRESOLVED** | No lexical match; zero guessing | Approved override: `doc_number` |
| `supplier_gstin` | `gst_reg_no` | **UNRESOLVED** | No lexical match; zero guessing | Approved override: `gst_reg_no` |
| `buyer_pan` | `entity_pan` | **UNRESOLVED** | No lexical match; zero guessing | Approved override: `entity_pan` |
| `billing_date` | `billing_date` | **PROPOSED** | Exact name match | Direct approval |
| `net_amount` | `net_amount` | **PROPOSED** | Exact name match | Direct approval |
| `tax_amount` | `tax_amount` | **PROPOSED** | Exact name match | Direct approval |
| `hsn_sac_code` | `hsn_sac_code` | **PROPOSED** | Exact name match | Direct approval |
| `destination_pin` | `postal_code_primary` | **UNRESOLVED** | Ambiguous candidate with `postal_code_secondary` | Approved override: `postal_code_primary` |
| `bank_ifsc` | `bank_ifsc` | **PROPOSED** | Exact name match | Direct approval |
| `invoice_status` | `invoice_status` | **PROPOSED** | Exact match with `uppercase_strip` | Direct approval |
| `dispatch_notes` | `dispatch_notes` | **PROPOSED** | Exact name match | Direct approval |

- **Mapping Proposals:** 7 Proposed, 4 Unresolved.
- **False Matches:** **0 / 11 (0.0%)**.
- **Blocker Status:** Integration flagged as `BLOCKED` with 4 critical `R001` findings. Automated adapter generation was strictly refused until overrides were submitted.

---

## 8. Transformation Correctness Results

- **Total Valid Transformed Records:** 5
- **Field-Level Match:** 55 / 55 fields matched independently pre-declared values (**100.0%**).
- **Record-Level Match:** 5 / 5 records matched entirely (**100.0%**).
- **Key Edge Cases Verified:**
  1. *Duplicate Records:* Row 1 and Row 2 are identical valid records. Both were preserved in the output without deduplication.
  2. *Error-Like Text:* Row 3 contained `dispatch_notes="ERROR: Client reported damaged outer box..."`. It was correctly processed and transformed as valid without triggering false quarantine.
  3. *Leading Zeros:* `invoice_id="INV-00042"` retained leading zeros as a string.
  4. *Case Normalization:* Row 4 `invoice_status="pending"` normalized to `"PENDING"`.
  5. *Null Preservation:* Row 5 `dispatch_notes="None of the items were returned during inspection"` was preserved intact as a string, while literal `"NULL"` in Row 4 became `None`.
  6. *Column Pruning:* `driver_phone_number`, `warehouse_dock_no`, and `postal_code_secondary` were omitted from output.

---

## 9. Quarantine and Record-Accounting Results

### 9.1 Zero Data Loss Invariant
$$\text{Total Input (12)} = \text{Valid Transformed (5)} + \text{Quarantined Records (7)}$$
$$\Delta = 0 \text{ (Zero Records Dropped)}$$

### 9.2 Injected Fault Accounting
| Row Index | Source Payload Key | Injected Condition | Result | Diagnostic Code |
| :-: | :--- | :--- | :---: | :--- |
| **Row 6** | `doc_number=""` | Missing mandatory invoice ID | **QUARANTINED** | `ERR_REQUIRED_FIELD_MISSING` |
| **Row 7** | `gst_reg_no="27AAPFU0939F199"` | GSTIN 14th char is 9, not Z | **QUARANTINED** | `ERR_PATTERN_VIOLATION` |
| **Row 8** | `entity_pan="AAPF0939F"` | 9-character malformed PAN | **QUARANTINED** | `ERR_PATTERN_VIOLATION` |
| **Row 9** | `postal_code_primary="40001"` | 5-digit PIN code | **QUARANTINED** | `ERR_PATTERN_VIOLATION` |
| **Row 10** | `bank_ifsc="SBIN1001234"` | IFSC 5th char is 1, not 0 | **QUARANTINED** | `ERR_PATTERN_VIOLATION` |
| **Row 11** | `net_amount="₹ 1,50,000.00"` | Currency string in float | **QUARANTINED** | `ERR_TYPE_CONVERSION` |
| **Row 12** | `invoice_status="WRITTEN_OFF"` | Illegal enum category | **QUARANTINED** | `ERR_ENUM_VIOLATION` |

- **Fault Recall:** 7 / 7 (**100.0%**).
- **False Quarantines:** 0 / 5 (**0.0%**).

---

## 10. API and Web Workflow Results

The full application workflow was validated via Starlette `TestClient` in `test_gate09_pilot_api_workflow_and_session_lifecycle`:
1. **Upload & Assess (`POST /api/assess`):** Uploaded source CSV and target JSON contract; returned session ID and `is_blocked = True`.
2. **Rejection Safeguard (`POST /api/approve-and-generate`):** Empty approval request without overrides returned HTTP 400 Bad Request.
3. **Approval (`POST /api/approve-and-generate`):** Submitting overrides returned HTTP 200 with generated adapter and validation metrics (5 valid, 7 quarantined).
4. **Downloads:**
   - JSON report (`GET /api/download/report/{id}?format=json`) returned HTTP 200.
   - Markdown report (`GET /api/download/report/{id}?format=md`) returned HTTP 200.
   - Adapter code (`GET /api/download/adapter/{id}`) returned HTTP 200 with self-contained Python code.
5. **Session Deletion (`DELETE /api/session/{id}`):** Returned HTTP 200 with `status="cleaned"`. Subsequent download requests returned HTTP 404.

---

## 11. Developer Usability Results

**Status: NOT TESTED.**

In accordance with Phase F instructions:
- Because no independent human developer was available during this session, this phase is explicitly recorded as **NOT TESTED**.
- No synthetic walkthrough was substituted for an actual human usability test.
- Independent developer usability remains unverified.

---

## 12. Reliability and Security Findings

1. **In-Process Python Execution Sandbox:**
   - Compiled adapters run with `SAFE_BUILTINS` and restricted `_sandbox_import`.
   - Dangerous builtins (`open`, `eval`, `exec`) and unauthorized modules (`os`, `sys`, `subprocess`) are blocked.
   - *Security Boundary:* Effective defense-in-depth for local developer use; **not** an OS-level sandbox (Docker/container). Untrusted public execution is forbidden.
2. **Upload Enforcement:**
   - Source files strictly capped at 100 MB (`MAX_SOURCE_SIZE_BYTES`).
   - Contracts capped at 5 MB (`MAX_CONTRACT_SIZE_BYTES`).
   - Extensions restricted to `.csv`, `.tsv`, `.txt`, `.json`, `.jsonl`.
   - Path traversal in sample IDs (`../`) is blocked by regex `^[A-Za-z0-9_-]+$`.
3. **Session Volatility:**
   - Sessions are stored in an in-memory dictionary (`SESSIONS`).
   - A server restart resets active sessions.

---

## 13. Defects Fixed and Regression Tests Added

1. **Missing Packaging Dependencies in `pyproject.toml`:**
   - *Problem:* `fastapi` and `uvicorn` were imported by `recon.server` and `recon.cli web`, but were omitted from `pyproject.toml` `dependencies`.
   - *Fix:* Added `"fastapi>=0.100.0"` and `"uvicorn>=0.20.0"` to `project.dependencies` in `pyproject.toml`.
   - *Verification:* Verified via `python -m pip install -e ".[dev]"` compatibility and `python -m recon.cli web --help`.

---

## 14. Known Limitations and Unsupported Capabilities

1. **In-Memory Sessions:** Server restart resets session state.
2. **In-Process Sandbox:** No containerized isolation; not safe for multi-tenant public hosting.
3. **No Cross-Row Semantic Deduplication:** Identical records are both processed and output; deduplication must happen outside Recon.
4. **Strict Datetime & Currency Non-Coercion:** Recon quarantines non-ISO datetimes and currency strings rather than guessing formats.
5. **Unverified Independent Usability:** Usability by a non-coached external developer has not yet been observed.

---

## 15. Evidence and Reproduction Steps

To reproduce all findings from a fresh terminal:
```powershell
cd D:\recon
python -m pytest tests/benchmark/test_gate09_controlled_local_pilot.py -v
python -m pytest tests -v
```

---

## 16. Recommended Next Action

The core engine, API, and packaging are verified and ready for a **Controlled Local Pilot**. 
The immediate next action is to **conduct an uncoached, observed session with an actual internal developer or data engineer using the provided local startup procedure and pilot dataset**, recording points of confusion in the UI or report.

---

## 17. Final Readiness Decision

### **DECISION: READY FOR CONTROLLED LOCAL PILOT**

- **Criteria Met:** Application runs locally without external dependencies; 101/101 automated tests pass; zero data loss is mathematically enforced; packaging dependencies are fixed; known boundaries are documented.
- **Qualification:** Independent developer usability has not yet been tested and remains unverified. Public production deployment is out of scope.
