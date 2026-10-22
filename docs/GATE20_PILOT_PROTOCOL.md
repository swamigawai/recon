# Recon — Gate 20 External Developer Pilot Protocol

**Document:** Gate 20 External Developer Pilot Protocol  
**Target Engine:** Recon — The Integration Readiness Engine (`D:\recon`)  
**Lead Reviewer:** Skeptical Developer-Tools Product Lead, Senior Integration Engineer & QA Reviewer  
**Date:** October 22, 2026  
**Status:** **STANDARDIZED PROTOCOL — HUMAN EXECUTION PENDING**

---

> [!IMPORTANT]
> **STRICT HONESTY DISCLOSURE: NO FABRICATED USER DATA**  
> In accordance with Gate 20 requirements, **no human participant results, quotes, satisfaction ratings, or adoption numbers have been fabricated**. 
> All sections below provide an independently verifiable, standardized, reproducible pilot protocol ready for external developer execution. The empirical field trials are formally labeled as **`[PENDING]`** awaiting external engineer recruitment.

---

## 1. Pilot Mandate, Objective & Target User Segment

### Core Mandate
Determine whether independent developers—who have never built or used Recon—can successfully complete a real-world third-party data integration preflight assessment, discover subtle data hazards, and find meaningful value in Recon compared to their existing workflows.

### Target User Segment (Narrowest Compelling Cohort)
- **Role:** Backend, Integration, and Data Platform Engineers.
- **Workflow:** Ingesting external, third-party partner data batches (e.g. vendor invoice dumps, municipal feeds, or customer exports) into an internal system with strict schema constraints.
- **Pain Point:** Partner data arrives with misaligned column headers, formatting errors, pattern violations, and unannounced schema drift. Writing custom scripts or running schema validators after the fact leads to silent data corruption, runtime crashes, or hours of manual debugging.

---

## 2. Standardized Benchmark Task & Ground Truth Specification

### The Realistic Integration Task: B2B Enterprise Vendor Invoicing
Participants are given an unfamiliar third-party vendor invoice batch (`gate09_pilot_b2b_vendor_invoices.csv`) and an internal enterprise target schema contract (`target_contract_gate09_pilot_b2b.json`).

The task requires the participant to:
1. Ingest the dataset and schema contract.
2. Review automated data profiling (identifying row counts, null rates, and duplicate rows).
3. Review mapping proposals and resolve ambiguous or unmapped required fields without guesswork.
4. Approve the mapping plan and generate a pure-Python adapter.
5. Validate the transformation in the local sandbox and inspect quarantined records.
6. Run the headless preflight CLI gate (`recon gate`).

### Independent Ground Truth Specification (Defined Independently of Recon)

| Metric / Dimension | Independent Ground Truth Expectation |
| :--- | :--- |
| **Total Input Records** | 12 records |
| **Expected Valid Output Records** | 5 records (Records 0, 1, 2, 3, 4) |
| **Expected Quarantined Records** | 7 records (Records 5, 6, 7, 8, 9, 10, 11) |
| **Zero-Loss Accounting Invariant** | $N_{\text{total}} \equiv N_{\text{valid}} + N_{\text{quarantine}} = 5 + 7 = 12$ |
| **Duplicate Preservation** | Records 0 and 1 are identical valid rows; both must appear in valid output |
| **Enum Case Normalization** | Record 3 has status `"pending"`; normalized to valid enum `"PENDING"` |
| **Nullable Null Preservation** | Record 3 has empty `tax_amount`; preserved as `null` / `None` without failure |

### Seeded Hazards in Third-Party Dataset

| Record Index | Target Field Affected | Seeded Data Hazard | Expected Quarantine Error Code |
| :---: | :--- | :--- | :--- |
| **Row 6** | `invoice_id` | Missing required non-nullable value (empty string) | `ERR_REQUIRED_FIELD_MISSING` |
| **Row 7** | `supplier_gstin` | Regex pattern mismatch (14th char is `9` instead of `Z`) | `ERR_PATTERN_VIOLATION` |
| **Row 8** | `buyer_pan` | Regex pattern mismatch (9 chars instead of 10) | `ERR_PATTERN_VIOLATION` |
| **Row 9** | `destination_pin` | Regex pattern mismatch (5-digit PIN instead of 6 digits) | `ERR_PATTERN_VIOLATION` |
| **Row 10** | `bank_ifsc` | Regex pattern mismatch (5th char is `1` instead of `0`) | `ERR_PATTERN_VIOLATION` |
| **Row 11** | `net_amount` | Type conversion error (Currency string `"₹ 1,50,000.00"`) | `ERR_TYPE_CONVERSION` |
| **Row 12** | `invoice_status` | Disallowed enum value (`"WRITTEN_OFF"`) | `ERR_ENUM_VIOLATION` |

### Required Semantic Disambiguation (Mapping)

The source dataset uses heterogeneous column names that do not match the target contract:
- `doc_number` $\to$ `invoice_id` (Unmapped required; requires human assignment)
- `gst_reg_no` $\to$ `supplier_gstin` (Unmapped required; requires human assignment)
- `entity_pan` $\to$ `buyer_pan` (Unmapped required; requires human assignment)
- `postal_code_primary` vs `postal_code_secondary` $\to$ `destination_pin` (Ambiguous candidate columns; requires human selection of primary)

---

## 3. Participant Cohort Specification

Recruit **3 to 5 external software engineers** who have never seen or built Recon:

| Participant ID | Target Profile | Relevant Experience | Assigned Scenario |
| :---: | :--- | :--- | :---: |
| **P-01** | Senior Backend Engineer | Fast-moving API integrations; writes Pydantic / Marshmallow schemas | B2B Vendor Invoicing |
| **P-02** | Data / Analytics Engineer | Airflow / dbt pipelines from third-party vendor CSV dumps | B2B Vendor Invoicing |
| **P-03** | DevOps / Platform Engineer | CI/CD pipelines, automated testing, quality gates | B2B Vendor Invoicing |
| **P-04** | FinTech Integration Specialist | Financial data exchange, regulatory reporting, ledger ingestion | B2B Vendor Invoicing |
| **P-05** | Enterprise Solutions Architect | Legacy ERP migrations, partner data onboarding governance | B2B Vendor Invoicing |

---

## 4. Facilitator Rules of Engagement

1. **Standardized Time Limit:**  
   - Maximum duration: **45 minutes** (30 minutes hands-on unassisted task + 15 minutes structured interview).
   - Time limit is communicated in advance.
2. **Strictly No Coaching on Initial Attempt:**  
   - The facilitator must not suggest mapping choices, explain UI controls, or guide the participant.
   - If the participant asks: *"What does UNRESOLVED mean?"* or *"Which postal code should I pick?"*, the facilitator responds: *"Please explore the interface and use your best judgment as you would in your normal day-to-day work."*
3. **Intervention Protocol:**  
   - The facilitator may only intervene if an unrecoverable environment blocker (e.g. OS Python library failure) halts progress for $> 5$ minutes. Any intervention is logged as an assisted setup failure.
4. **Observer Metric Tracking:**  
   - Observer records exact timestamps, user hesitation points, friction areas, verbatim questions, and error outputs.

---

## 5. Step-by-Step Task Script (Unassisted Participant Runbook)

### Introductory Briefing Provided to Participant (Verbatim)
> *"You are integrating batch data from an external business partner. Your system requires records to strictly adhere to a target contract schema. Your goal is to evaluate whether the partner's data is ready for ingestion, identify any breaking mismatches or data quality defects, resolve any mapping ambiguities, and generate an integration adapter without manual coding. Please work independently as you would on a normal production task."*

---

### Task 1: Environment Setup (< 5 Minutes)
```bash
git clone https://github.com/swamigawai/recon.git
cd recon
python -m pip install -e ".[dev]"
python -m pytest tests -q
# Target baseline: 152 passed
```

### Task 2: Launch Local Preflight Studio (< 3 Minutes)
```bash
recon serve --port 8000
# Open browser at http://localhost:8000
```

### Task 3: Ingest Dataset & Target Contract (< 5 Minutes)
1. Select or upload the sample dataset: `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv`.
2. Select or upload the target contract: `tests/fixtures/target_contract_gate09_pilot_b2b.json`.
3. Click **"Run Preflight Assessment"**.
4. Review the Source Profile: check row counts, null percentages, duplicate rows, and fingerprint.

### Task 4: Interactive Mapping Review & Disambiguation (< 10 Minutes)
1. Review the proposed mappings in the Mapping Table and the Flow Graph canvas.
2. Identify fields marked `UNRESOLVED` in red (required fields missing source columns).
3. Use the Contextual Inspector (press `I` or hover over nodes) to inspect type constraints and evidence.
4. Manually assign source columns:
   - Assign `doc_number` to `invoice_id`.
   - Assign `gst_reg_no` to `supplier_gstin`.
   - Assign `entity_pan` to `buyer_pan`.
   - Disambiguate `destination_pin` by selecting `postal_code_primary`.
5. Enter your name as reviewer and click **"Approve Plan & Generate Adapter"**.

### Task 5: Adapter Execution & Quarantine Inspection (< 5 Minutes)
1. Review the synthesized pure-Python adapter code in Screen 05.
2. Review the sandbox validation results:
   - Check valid count vs quarantined count.
   - Verify the accounting equation: $N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$.
3. Open the Quarantined Records drawer and inspect failure reasons and error codes.
4. Verify whether any valid records were improperly rejected.

### Task 6: Headless Preflight CLI Check (< 2 Minutes)
1. In a terminal, run:
   ```bash
   recon gate --source tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv --contract tests/fixtures/target_contract_gate09_pilot_b2b.json --json
   ```
2. Verify exit code and JSON preflight output.

---

## 6. Post-Session Structured Interview Protocol (15 Minutes)

The facilitator conducts a 1-on-1 debrief asking these exact 7 questions:

1. **Normal Workflow Comparison:**  
   *"How do you currently solve this problem in your day-to-day work?"*
2. **Time Consumption:**  
   *"Which part of the task took the most time or felt most tedious?"*
3. **Hazard Detection:**  
   *"Did Recon identify an issue that your normal workflow or custom scripts might miss?"*
4. **Finding Clarity:**  
   *"Which findings or error messages were useful, confusing, or incorrect?"*
5. **Adoption Blockers:**  
   *"What would stop you from using Recon again on a real project?"*
6. **Future Adoption:**  
   *"Would you choose Recon for your next relevant partner data integration? Why or why not?"*
7. **Simplification:**  
   *"What would you remove or simplify in the interface or workflow?"*

---

## 7. Security & Release Boundaries

- **Local Execution Only:** Recon executes generated adapters in an in-process restricted AST sandbox on the local machine. It does **not** provide an OS-level sandbox (no cgroups, seccomp, or Docker isolation).
- **Public Hosting Prohibited:** Recon is strictly intended for local developer preflight use; it must not be hosted as a public multi-tenant SaaS service.
- **Network Isolation:** Remote contract `$ref` dereferencing is disabled to prevent SSRF and network leakage.
