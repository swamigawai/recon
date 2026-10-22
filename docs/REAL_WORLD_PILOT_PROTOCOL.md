# Real-World Developer Pilot Protocol (Gate 17)
**Recon — The Integration Readiness Engine**
> *"Know what will break before you build the integration."*

---

> [!IMPORTANT]
> **PROPOSED PILOT SPECIFICATION — NO UNCONFIRMED CLAIMS**
> This protocol specifies an empirical evaluation with external engineers. In accordance with Gate 17 requirements, **all metrics, scores, and participant feedback outlined below are proposed evaluation protocols and templates until actual participants complete their sessions.** No market validation or completed user trials are claimed prior to human execution.

---

## 1. Pilot Purpose & Hypothesis

### Primary Objective
Evaluate whether engineers unfamiliar with Recon can independently assess third-party data integration readiness, catch real-world schema and data quality defects before building adapters, and prevent integration downtime without human handholding.

### Core Hypotheses to Test
1. **Time-to-Readiness:** An external developer can install Recon and arrive at a definitive Go/No-Go readiness verdict in under 10 minutes.
2. **Defect Catch Rate:** Recon catches at least 90% of subtle data mismatches (regex patterns, enum violations, type conversions, missing required fields) that typical ad-hoc ETL scripts overlook.
3. **Zero Hallucination:** Recon will never automatically fabricate mappings for ambiguous or unfamiliar field names, requiring explicit human approval.
4. **Zero Data Loss:** $100\%$ of input records are deterministically accounted for in valid outputs or quarantine logs ($N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$).

---

## 2. Participant Profile & Cohort Selection

Recruit 2–3 software, data, or integration engineers matching these profiles:

| Participant ID | Target Profile | Recommended Pilot Dataset |
| :--- | :--- | :--- |
| **Participant A (P-01)** | Backend / API Engineer | Invoicing / Financial Data (`target_contract_gate09_pilot_b2b.json` or custom REST OpenAPI spec) |
| **Participant B (P-02)** | Data / ETL Engineer | Logistics / Municipal Feed (`target_contract_service_request.json` or Freight Manifest) |
| **Participant C (P-03)** | DevOps / CI Engineer | Headless CI Preflight Gate (`recon gate` with exit code verification in GitHub Actions / local script) |

---

## 3. Session Protocol & Step-by-Step Task Script

### Logistics
- **Duration:** 45 minutes total (30 min hands-on task + 15 min debrief).
- **Environment:** Clean local machine or VM (Python 3.11+, pip, Git).
- **Observer Role:** Silent observation. The facilitator does not intervene unless there is an environment blocker.

### Scenario Runbook for Participant

```markdown
### Task 1: Environment Setup (< 5 minutes)
1. Clone the repository: `git clone <repo-url> recon && cd recon`
2. Install in editable mode: `python -m pip install -e ".[dev]"`
3. Verify test baseline: `python -m pytest tests -q` (151 tests expected)
4. Start Web Studio: `recon serve --port 8000` and navigate to http://localhost:8000

### Task 2: First Assessment & Ingestion (< 5 minutes)
1. Select or upload the B2B Invoicing dataset: `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv`
2. Select or upload the Target Contract: `tests/fixtures/target_contract_gate09_pilot_b2b.json`
3. Click "Run Preflight Assessment"
4. Observe the Source Profile: check column counts, duplicate detection, and SHA-256 fingerprinting.

### Task 3: Interactive Mapping Review (< 10 minutes)
1. Review the proposed mappings in the Mapping Table and the Flow Graph canvas.
2. Observe which fields are auto-mapped and which are marked UNRESOLVED in red.
3. Hover over fields to inspect type constraints and evidence in the Contextual Inspector (toggle with 'I').
4. Reassign sources for unmapped required fields (`invoice_id`, `supplier_gstin`, `buyer_pan`, `destination_pin`).
5. Enter your reviewer name and approve the plan.

### Task 4: Risk Review & Adapter Generation (< 5 minutes)
1. Review risk findings (Critical blockers vs Warnings).
2. Generate the Python adapter and inspect the synthesized code in Screen 05.
3. Review sandbox validation results in Screen 06:
   - Check valid count, quarantined count, and the zero-loss equation.
   - Inspect quarantined records to evaluate diagnostic clarity.

### Task 5: Headless CLI Preflight Check (< 5 minutes)
1. Open a terminal and run:
   `recon gate --source tests/fixtures/synthetic_nyc_311.csv --contract tests/fixtures/target_contract_service_request.json --json`
2. Verify exit code (`echo $?` or `$LASTEXITCODE`) and JSON output.
```

---

## 4. Quantitative Metrics Recording Sheet

| Metric Category | Target Benchmark | Participant A (P-01) | Participant B (P-02) | Participant C (P-03) |
| :--- | :--- | :--- | :--- | :--- |
| **Unassisted Setup** | Yes (0 facilitator hints) | [Pending Execution] | [Pending Execution] | [Pending Execution] |
| **Time to First Result** | $\le 10$ minutes | [Pending Execution] | [Pending Execution] | [Pending Execution] |
| **Defects Detected** | Enum, Regex, Missing Fields | [Pending Execution] | [Pending Execution] | [Pending Execution] |
| **False Positives** | 0 misleading auto-approvals | [Pending Execution] | [Pending Execution] | [Pending Execution] |
| **Zero-Loss Accounting** | $N_{in} = N_{val} + N_{quar}$ verified | [Pending Execution] | [Pending Execution] | [Pending Execution] |
| **CLI Exit Code Accuracy** | Exit 0 on pass, 1 on block | [Pending Execution] | [Pending Execution] | [Pending Execution] |
| **Overall Net Promoter** | $\ge 8 / 10$ | [Pending Execution] | [Pending Execution] | [Pending Execution] |

---

## 5. Post-Session Interview Script (15 Minutes)

1. **First Impressions & Friction:**
   - *"Did anything during installation or server launch surprise or confuse you?"*
   - *"Were the 7 workflow stages logical, or did you ever wonder what to do next?"*
2. **Confidence & Trust:**
   - *"When Recon left unfamiliar required fields unresolved rather than guessing, how did that affect your trust in the tool?"*
   - *"Did you read the generated Python adapter? Would you feel comfortable deploying that into your existing ETL or API service?"*
3. **Comparison with Existing Workflow:**
   - *"In your day-to-day work, how do you currently detect schema incompatibilities and data defects before writing code?"*
   - *"Did Recon surface issues that your current tools or intuition would have missed?"*
4. **Usability of Flow Graph & Inspector:**
   - *"Did the Flow Graph connectors help you understand relationships between source and target?"*
   - *"How was the Contextual Inspector drawer (hover vs pin vs 'I' shortcut)?"*
5. **Critical Gaps:**
   - *"What was the most frustrating part of the experience?"*
   - *"What is the single most important capability Recon lacks for you to use it on your actual production integrations?"*
