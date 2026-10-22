# Recon — Gate 20 Participant-Level Evaluation Scorecard

**Document:** Gate 20 Participant Scorecard & Evaluation Matrix  
**Target Engine:** Recon — The Integration Readiness Engine (`D:\recon`)  
**Lead Evaluator:** Skeptical Developer-Tools Product Lead, Senior Integration Engineer & QA Reviewer  
**Date:** October 22, 2026  
**Status:** **STANDARDIZED SCORECARD TEMPLATE — PARTICIPANT EXECUTION PENDING**

---

> [!IMPORTANT]
> **STRICT HONESTY DISCLOSURE: NO FABRICATED USER DATA**  
> In accordance with Gate 20 rules, **no participant names, individual scores, quotes, or adoption ratings have been fabricated**.
> All scorecard entries below are pre-configured evaluation templates with pre-defined success thresholds. Live human execution is formally marked **`[PENDING]`** awaiting external engineer recruitment.

---

## 1. Pre-Defined Success Criteria & Benchmark Targets

To evaluate participants objectively and avoid moving goalposts after observing results, the following quantitative thresholds were established prior to testing:

| Metric | Evaluation Method | Benchmark Target | Minimum Acceptable Threshold |
| :--- | :--- | :---: | :---: |
| **Setup Success** | Complete Task 1 (git clone, pip install, pytest) without facilitator intervention | 100% unassisted | $\ge 80\%$ unassisted |
| **Time to First Result** | Elapsed time from launching studio to viewing initial preflight assessment & profile | $\le 5.0$ minutes | $\le 8.0$ minutes |
| **Task Completion Rate** | Complete full workflow through adapter generation and quarantine inspection | 100% completion | $\ge 80\%$ completion |
| **Important Hazards Found** | Identify all 7 seeded hazards in the B2B invoicing dataset | 7 / 7 (100%) | $\ge 6 / 7$ (85.7%) |
| **Hazards Missed** | Number of seeded hazards unnoticed by participant | 0 missed | $\le 1$ missed |
| **False Alarms Encountered** | Number of valid fields flagged as erroneous blockers | 0 false alarms | 0 false alarms |
| **Incorrectly Rejected Data** | Number of conforming valid records quarantined | 0 valid rows | 0 valid rows |
| **Assistance Requests** | Unsolicited requests for facilitator help during unassisted attempt | 0 requests | $\le 1$ request |
| **Artifact Understandability** | Participant-reported rating of generated adapter code and quarantine logs (1–5 scale) | $\ge 4.5 / 5.0$ | $\ge 4.0 / 5.0$ |
| **Would Use Again** | Participant willingness to use Recon for their next relevant integration | $\ge 80\%$ Yes | $\ge 60\%$ Yes |

---

## 2. Participant-Level Scorecard Grid

| Evaluation Dimension | Benchmark Target | P-01 (Backend) | P-02 (Data/ETL) | P-03 (DevOps) | P-04 (FinTech) | P-05 (Enterprise) | Cohort Aggregate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Setup Success (Unassisted)** | 100% | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Time to First Result (min)** | $\le 5.0$ min | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Total Task Duration (min)** | $\le 30.0$ min | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Task Completed (Full Run)** | 100% | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Seeded Hazards Found (/7)** | 7 / 7 | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Hazards Missed (/7)** | 0 | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **False Alarms Encountered** | 0 | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Incorrectly Rejected Rows** | 0 | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Assistance Requests** | 0 | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Adapter Code Clarity (1–5)** | $\ge 4.0$ | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Quarantine Clarity (1–5)** | $\ge 4.5$ | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **CLI Gate Clarity (1–5)** | $\ge 4.0$ | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Would Use on Next Integration**| $\ge 80\%$ Yes | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |

---

## 3. Seeded Hazard Detection Breakdown per Participant

This ledger tracks whether participants independently observed each of the 7 seeded hazards in the B2B dataset:

| Row Index | Seeded Hazard Description | Ground Truth Error Code | P-01 | P-02 | P-03 | P-04 | P-05 | Detection Rate |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Row 6** | Missing required non-nullable `invoice_id` | `ERR_REQUIRED_FIELD_MISSING` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Row 7** | Regex violation on GSTIN (14th char is `9` instead of `Z`) | `ERR_PATTERN_VIOLATION` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Row 8** | Regex violation on PAN (9 chars instead of 10) | `ERR_PATTERN_VIOLATION` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Row 9** | Regex violation on PIN code (5 digits instead of 6) | `ERR_PATTERN_VIOLATION` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Row 10** | Regex violation on IFSC code (5th char is `1` instead of `0`) | `ERR_PATTERN_VIOLATION` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Row 11** | Type conversion error (`"₹ 1,50,000.00"` in float) | `ERR_TYPE_CONVERSION` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| **Row 12** | Disallowed enum value (`"WRITTEN_OFF"`) | `ERR_ENUM_VIOLATION` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |

---

## 4. Qualitative Interview Response Logging Sheet (Template)

### Question 1: How do you currently solve this problem in your day-to-day work?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`

### Question 2: Which part of the task took the most time or felt most tedious?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`

### Question 3: Did Recon identify an issue that your normal workflow might miss?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`

### Question 4: Which findings were useful, confusing, or incorrect?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`

### Question 5: What would stop you from using Recon again on a real project?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`

### Question 6: Would you choose Recon for your next relevant partner integration? Why or why not?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`

### Question 7: What would you remove or simplify in the interface or workflow?
- **P-01 (Backend):** `[PENDING - Awaiting Interview Response]`
- **P-02 (Data/ETL):** `[PENDING - Awaiting Interview Response]`
- **P-03 (DevOps):** `[PENDING - Awaiting Interview Response]`
- **P-04 (FinTech):** `[PENDING - Awaiting Interview Response]`
- **P-05 (Enterprise):** `[PENDING - Awaiting Interview Response]`
