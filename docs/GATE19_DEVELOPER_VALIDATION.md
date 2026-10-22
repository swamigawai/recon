# Recon — Gate 19 Developer Pilot Protocol & Human Validation Framework

**Document:** Gate 19 Developer Validation Protocol  
**Target Engine:** Recon — The Integration Readiness Engine (`D:\recon`)  
**Lead Reviewer:** Skeptical Principal Engineer, QA Lead & Independent Benchmark Reviewer  
**Date:** October 22, 2026  
**Status:** **READY-TO-RUN PILOT PROTOCOL — HUMAN PARTICIPATION PENDING**

---

> [!IMPORTANT]
> **STRICT HONESTY DISCLOSURE: NO FABRICATED USER DATA**  
> In accordance with Gate 19 requirements, **no human participant results, quotes, satisfaction ratings, or adoption numbers have been fabricated**. 
> All sections below provide an independently verifiable, standardized, reproducible pilot protocol ready for external developer execution. The empirical field trials are formally labeled as **`[PENDING]`** awaiting external engineer recruitment.

---

## 1. Pilot Purpose & Objectives

The purpose of this human developer validation is to determine whether external engineers—working without assistance, training, or prior exposure to Recon—can successfully use Recon as a preflight readiness engine to:

1. **Setup and run Recon** locally in under 5 minutes without environment blockers.
2. **Identify critical integration hazards** (missing required fields, ambiguous source columns, type incompatibilities) in third-party batches before writing ingestion code.
3. **Disambiguate mapping conflicts** using evidence provided in the Studio interface (Flow Graph, Table, and Contextual Inspector).
4. **Approve a mapping plan and inspect the generated adapter** to verify that valid data is preserved and non-conforming data is quarantined with complete traceability.
5. **Evaluate developer trust**: Establish whether developers would adopt Recon over their traditional workflow (custom Python scripts, manual Pydantic models, or trial-and-error database ingestion).

---

## 2. Participant Cohort Specification

Recruit **3 to 5 independent software engineers** matching the following profile criteria:
- Experience writing or maintaining data ingestion pipelines, ETL jobs, or API integrations.
- Zero prior involvement in the Recon codebase, specification, or previous gate audits.
- Diverse background across backend services, data engineering, and DevOps.

| Participant ID | Target Background | Typical Ingestion Workflow | Assigned Pilot Scenario | Evaluation Status |
| :---: | :--- | :--- | :--- | :---: |
| **P-01** | Senior Backend Engineer | Fast-moving API integration; writes ad-hoc Pydantic models | B2B Vendor Invoicing (Heterogeneous headers, ambiguous columns) | `[PENDING]` |
| **P-02** | Data / Analytics Engineer | Builds Airflow / dbt pipelines from third-party CSV/JSON dumps | Municipal Telemetry (High row volume, dirty nulls, string floats) | `[PENDING]` |
| **P-03** | DevOps / Platform Engineer | Maintains CI/CD ingestion gates and validation pre-commit hooks | Headless CLI Gate (`recon gate --json` automated pipeline) | `[PENDING]` |
| **P-04** | FinTech Integration Engineer | Ingests financial partner transaction records | Financial Ledger (Leading zeroes, high-precision floats, strict enums) | `[PENDING]` |
| **P-05** | Enterprise Solutions Architect | Manages external vendor data exchange & contract governance | Upstream Contract Drift (Schema evolution, new mandatory fields) | `[PENDING]` |

---

## 3. Standardized Participant Runbook (Unassisted)

### Facilitator Rules of Engagement
- **Strictly No Coaching on First Attempt:** The observer must not offer hints, explain UI elements, or suggest mapping choices during the participant's first pass.
- **Intervention Protocol:** The observer may only intervene if the participant is blocked by an operating-system or Python environment crash for $> 5$ minutes. Any such intervention must be recorded as an assisted failure on Task 1.
- **Observation Logging:** Facilitator records timestamps, screen actions, hesitation points, error messages encountered, and verbatim questions asked by the participant.

---

### Step-by-Step Instructions Given to Participant

#### Context Briefing
> *"You are integrating third-party data from an external business partner. Your backend system expects records to strictly conform to a target contract schema. Your task is to use Recon to determine whether the partner's batch is ready for ingestion, identify what will break, resolve any ambiguities, and generate an adapter to process the data safely."*

#### Task 1: Environment Setup (< 3 Minutes)
```bash
git clone https://github.com/swamigawai/recon.git
cd recon
python -m pip install -e ".[dev]"
python -m pytest tests -q
# Target baseline: 152 passed in ~35s
```

#### Task 2: Launch Local Preflight Studio (< 2 Minutes)
```bash
recon serve --port 8000
# Open browser at http://localhost:8000
```

#### Task 3: Ingest Dataset & Target Contract (< 5 Minutes)
1. Select the sample dataset: `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv`.
2. Select the target contract: `tests/fixtures/target_contract_gate09_pilot_b2b.json`.
3. Click **"Run Preflight Assessment"**.
4. Observe the Source Profile (record counts, column types, null percentages, duplicate detection, SHA-256 fingerprint).

#### Task 4: Mapping Review & Disambiguation (< 10 Minutes)
1. Inspect the proposed mappings in the Mapping Table and the Flow Graph.
2. Identify target fields marked `UNRESOLVED` (e.g. required fields with ambiguous or missing source columns).
3. Use the Contextual Inspector (press `I` or hover over nodes/rows) to examine type constraints, transformation rules, and evidence.
4. Disambiguate and assign appropriate source columns.
5. Provide a reviewer identity and click **"Approve Plan & Generate Adapter"**.

#### Task 5: Adapter Execution & Quarantine Inspection (< 5 Minutes)
1. Review the synthesized pure-Python adapter code.
2. Inspect the Validation Results:
   - Valid records count vs Quarantined records count.
   - Verify the invariant: $\text{Total Input} = \text{Valid} + \text{Quarantined}$.
3. Open the Quarantined Records drawer and inspect failure reasons and error codes.
4. Verify whether any valid records were improperly rejected.

#### Task 6: Headless Preflight CLI Check (< 3 Minutes)
1. In a terminal, run:
   ```bash
   recon gate --source tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv --contract tests/fixtures/target_contract_gate09_pilot_b2b.json --json
   ```
2. Verify the exit code and inspect the machine-readable JSON preflight report.

---

## 4. Quantitative Evaluation Scorecard Template

| Evaluation Dimension | Benchmark Target | P-01 | P-02 | P-03 | P-04 | P-05 | Cohort Aggregate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Unassisted Setup Success** | 100% without intervention | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Time to First Useful Result** | $\le 8.0$ minutes | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Hazard Identification Recall** | 100% of seed hazards | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **False Alarm Encounters** | 0 valid fields blocked | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Adapter Code Comprehension** | $\ge 4.0 / 5.0$ rating | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Quarantine Reason Clarity** | $\ge 4.5 / 5.0$ rating | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Confidence in Data Preservation** | $\ge 4.5 / 5.0$ rating | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Willingness to Use in Production** | $\ge 80\%$ positive | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |

---

## 5. Post-Session Structured Interview Protocol (15 Minutes)

### Section A: Differentiation & Workflow Comparison
1. *"How does using Recon compare to how you currently validate and ingest third-party data?"*
2. *"What does Recon catch that your usual approach (e.g. Pandas script, Pydantic model, or raw SQL) would have missed?"*
3. *"Did the tool present any false alarms that caused you unnecessary work?"*

### Section B: Usability & Trust
4. *"When the tool generated the Python adapter code, did you trust it to run against production data? Why or why not?"*
5. *"Was the separation between Valid Output and Quarantined Records clear? Did you understand why quarantined records failed?"*
6. *"How intuitive was the Contextual Inspector and the Flow Graph for resolving ambiguous mappings?"*

### Section C: Future Adoption & Gaps
7. *"Under what circumstances would you choose to use Recon on your current projects?"*
8. *"What is the single biggest missing feature or rough edge that would prevent you from using Recon today?"*
9. *"Would you prefer to run Recon as a local developer CLI/UI or as part of a CI/CD automated pipeline?"*

---

## 6. Participant Privacy & Ethical Data Handling

- **Confidentiality:** All participant feedback, company affiliations, and proprietary workflows will remain anonymized using participant identifiers (`P-01` through `P-05`).
- **Data Protection:** No proprietary customer data or production credentials will be uploaded. All testing will run strictly on synthetic open datasets on the developer's local machine.
- **Reporting:** Only aggregated metrics and anonymized, verbatim quotes will be included in subsequent release gate documentation.
