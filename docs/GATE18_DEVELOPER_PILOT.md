# Recon Developer Pilot Study Protocol & Runbook (Gate 18)

**Project:** Recon — The Integration Readiness Engine  
**Milestone:** Gate 18 (Differentiation, Real-World Proof & Developer Trust)  
**Date:** October 21, 2026  
**Status:** **PROPOSED PROTOCOL — PARTICIPANT VALIDATION PENDING**  

---

> [!IMPORTANT]
> **STRICT HONESTY DISCLOSURE: NO FABRICATED USER DATA**  
> In accordance with Gate 18 rules, **no user feedback, adoption statistics, satisfaction ratings, or developer quotes are fabricated**. All metrics, interview questions, and evaluation scorecards in this document represent a validated, ready-to-run empirical protocol for external participants. Field testing with independent engineers is **PENDING** recruitment and execution.

---

## 1. Pilot Cohort & Recruitment Profile

Recruit 3–5 software engineers, data engineers, or integration specialists who have **never seen or built Recon**.

### Target Participant Profiles

| Participant ID | Target Engineering Role | Relevant Day-to-Day Challenge | Recommended Scenario |
| :--- | :--- | :--- | :--- |
| **Participant 01 (P-01)** | Backend / API Engineer | Ingesting third-party ERP / B2B vendor invoices | Scenario B: B2B Invoicing (`gate09_pilot_b2b_vendor_invoices.csv`) |
| **Participant 02 (P-02)** | Data Platform / ETL Engineer | Processing municipal and external telemetry feeds | Scenario A: Municipal NYC 311 (`synthetic_nyc_311.csv`) |
| **Participant 03 (P-03)** | DevOps / Reliability Engineer | CI/CD pipeline automated pre-commit gates | Scenario C: Headless CLI Gate (`recon gate --json`) |
| **Participant 04 (P-04)** | FinTech Integration Specialist | Validating high-precision transaction feeds | Scenario D: Precision & Currency Batch (`s06_decimal_precision`) |
| **Participant 05 (P-05)** | Enterprise Systems Architect | Schema evolution and contract drift management | Scenario E: Upstream Schema Drift (`s10_schema_drift`) |

---

## 2. Participant Onboarding & Unassisted Runbook

### Context Briefing Provided to Participant (Verbatim)
> *"You are integrating batch data from an external business partner. Your system requires records to adhere to a strict target schema contract. Your goal is to evaluate whether the partner's data is ready for ingestion, identify any breaking mismatches or data quality defects, and generate an integration adapter without manual coding."*

### Task 1: Environment Setup (< 3 Minutes)
```bash
git clone https://github.com/swamigawai/recon.git
cd recon
python -m pip install -e ".[dev]"
python -m pytest tests -q
# Expected: 151 passed
```

### Task 2: Launch Local Preflight Studio (< 2 Minutes)
```bash
recon serve --port 8000
# Open http://localhost:8000
```

### Task 3: Ingest Dataset & Target Contract (< 5 Minutes)
1. Select or upload the sample dataset (e.g. `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv`).
2. Select or upload the target contract (e.g. `tests/fixtures/target_contract_gate09_pilot_b2b.json`).
3. Click **"Run Preflight Assessment"**.
4. Observe the Source Profile (row count, null percentages, duplicate detection, SHA-256 fingerprint).

### Task 4: Interactive Mapping Review & Disambiguation (< 10 Minutes)
1. Review proposed mappings in the Mapping Table and the Flow Graph.
2. Observe unmapped required fields marked `UNRESOLVED` in red.
3. Use the Contextual Inspector (press `I` or hover over nodes) to inspect type constraints and evidence.
4. Manually assign source columns for the unmapped required fields.
5. Provide reviewer name and click **"Approve Plan & Generate Adapter"**.

### Task 5: Sandbox Validation & Quarantine Inspection (< 5 Minutes)
1. Review the generated pure-Python adapter code.
2. Review the Validation Results:
   - Verify valid records count and quarantined records count.
   - Check the accounting equation: $N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$.
3. Open the Quarantined Records drawer and inspect failure reasons and error codes.

### Task 6: Headless Preflight CLI Check (< 5 Minutes)
1. Open a terminal and run:
   ```bash
   recon gate --source tests/fixtures/synthetic_nyc_311.csv --contract tests/fixtures/target_contract_service_request.json --json
   ```
2. Verify exit code (`echo $?` or `$LASTEXITCODE`) and JSON output.

---

## 3. Quantitative Evaluation Scorecard (Template)

| Evaluation Metric | Target Benchmark | P-01 | P-02 | P-03 | P-04 | P-05 | Cohort Average |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Unassisted Setup** | $\ge 90\%$ without help | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **Time to First Result** | $\le 10$ minutes | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **Issue Detection Recall** | $\ge 95\%$ of seed hazards | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **False Positive Alarm Rate** | $\le 5\%$ of valid fields | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **Quarantine Clarity Score** | $\ge 4.5 / 5.0$ | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **Generated Adapter Trust** | $\ge 4.0 / 5.0$ | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **Would Use on Next Project** | $\ge 80\%$ Yes | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |

---

## 4. Post-Session Structured Interview Protocol (15 Minutes)

### Section A: Understanding Product Purpose & Differentiation
1. *"In your own words, what problem is Recon trying to solve?"*
2. *"How does Recon differ from schema validators (like Pydantic or jsonschema) that you normally use?"*
3. *"What would you typically use to solve this problem if Recon didn't exist?"*

### Section B: Usability & Workflow Friction
4. *"Which part of the 7-stage workflow felt confusing, slow, or unnecessary?"*
5. *"How intuitive was the Flow Graph and Contextual Inspector (keyboard shortcut `I`, pin drawer)?"*
6. *"Did you find any error messages or risk warnings unhelpful or cryptic?"*

### Section C: Trust & Reliability
7. *"When Recon refused to guess unmapped required fields and marked them UNRESOLVED, did that increase or decrease your trust?"*
8. *"Did you inspect the generated Python adapter? Would you feel comfortable deploying that into production?"*
9. *"How important is the zero-loss guarantee ($N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$) for your data workflows?"*

### Section D: Critical Gaps & Feature Demands
10. *"What is the single biggest missing capability preventing you from using Recon today in your daily work?"*
11. *"On a scale of 1 to 10, how likely are you to recommend Recon to an engineer building third-party integrations?"*

---

## 5. Instructions for Pilot Facilitator

1. **Observe Silently:** Do not guide the participant during Tasks 1 through 6. Allow them to encounter friction naturally.
2. **Log Timestamps:** Record exact minutes from repo clone to first preflight result.
3. **Capture Verbalizations:** Write down verbatim quotes, especially when the participant hesitates or expresses confusion.
4. **Preserve Neutrality:** Do not defend or explain Recon's architectural choices during the session; ask follow-up questions to understand why something felt unintuitive.
