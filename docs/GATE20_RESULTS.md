# Recon — Gate 20 Developer Pilot Results & Evidence Analysis

**Document:** Gate 20 Developer Pilot Results & Analysis  
**Target Engine:** Recon — The Integration Readiness Engine (`D:\recon`)  
**Lead Evaluator:** Skeptical Developer-Tools Product Lead, Senior Integration Engineer & QA Reviewer  
**Date:** October 22, 2026  
**Status:** **TECHNICAL OUTCOMES VERIFIED — HUMAN FIELD TRIALS PENDING**

---

> [!IMPORTANT]
> **STRICT HONESTY DISCLOSURE: SEPARATION OF REPRODUCED EVIDENCE AND PENDING HUMAN TRIALS**  
> In accordance with Gate 20 rules, **no human participant quotes, satisfaction ratings, or adoption numbers have been fabricated**.
> To prevent conflating automated engine capabilities with actual human developer behavior, this document explicitly separates:
> 1. **Observed Task Outcomes:** Deterministically verified in the live code checkout.
> 2. **Participant Opinions:** Formally labeled **`[PENDING]`** awaiting external recruitment.
> 3. **Researcher Interpretation:** Usability and friction analysis conducted by the research team.
> 4. **Unresolved Questions:** Critical adoption and trust hypotheses to be settled during live trials.

---

## 1. Executive Summary & Verification Baseline

| Verification Dimension | Current Evaluated Status | Evidence Reference |
| :--- | :---: | :--- |
| **Automated Test Suite** | **152 Passed in 37.34s** (0 failures, 0 warnings) | [`tests/`](file:///D:/recon/tests) |
| **Hardened Synthetic Benchmark** | **16/16 Scenarios Passed** (100% Recall, 100% Precision) | [`benchmarks/gate19/`](file:///D:/recon/benchmarks/gate19/) |
| **Deep Value Content Preservation** | **12/12 Executed Scenarios Passed** (100% Value Equality) | [`docs/GATE19_BENCHMARK_RESULTS.md`](file:///D:/recon/docs/GATE19_BENCHMARK_RESULTS.md) |
| **Pilot Standardized Task & Fixtures** | **Verified & Reproducible** (`gate09_pilot_b2b`) | [`tests/fixtures/`](file:///D:/recon/tests/fixtures) |
| **External Human Participant Trials** | **`[PENDING]` Awaiting External Cohort Execution** | [`docs/GATE20_PARTICIPANT_SCORECARD.md`](file:///D:/recon/docs/GATE20_PARTICIPANT_SCORECARD.md) |

---

## 2. Separation of the Four Evidence Dimensions

### Dimension A: Observed Task Outcomes (Engine & Studio Verification) `[VERIFIED]`

When an engineer executes the standardized pilot workflow (`tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv` against `tests/fixtures/target_contract_gate09_pilot_b2b.json`), the observed, reproducible system behavior is:

1. **Ingestion & Profiling:**  
   - Source dataset loaded: 12 rows, 14 columns.
   - Profiling correctly identifies 1 duplicate row (Row 0 and Row 1 are identical).
   - Computes deterministic SHA-256 fingerprint of the source dataset.
2. **Preflight Mapping Proposals & Guardrails:**  
   - Target schema requires 11 fields.
   - Recon auto-maps 7 fields where column names match (`billing_date`, `net_amount`, `tax_amount`, `hsn_sac_code`, `bank_ifsc`, `invoice_status`, `dispatch_notes`).
   - Recon leaves 4 required fields as `UNRESOLVED` (`invoice_id`, `supplier_gstin`, `buyer_pan`, `destination_pin`).
   - **Zero Hallucination Guardrail:** Recon strictly halts adapter generation with `MappingError: approved mapping plan is incomplete. Missing required fields: ['invoice_id', 'supplier_gstin', 'buyer_pan', 'destination_pin']`.
3. **Interactive Human Disambiguation:**  
   - Developer assigns `doc_number` $\to$ `invoice_id`.
   - Developer assigns `gst_reg_no` $\to$ `supplier_gstin`.
   - Developer assigns `entity_pan` $\to$ `buyer_pan`.
   - Developer resolves ambiguous candidate columns for `destination_pin`, choosing `postal_code_primary` over `postal_code_secondary`.
4. **Adapter Synthesis & Execution:**  
   - Synthesizes pure-Python AST adapter with sanitized local variables and case normalization.
   - Executes transformation in an in-process restricted sandbox.
5. **Sandbox Validation & Quarantine Proof:**  
   - Valid records produced: **5 records** (includes identical duplicate row preservation and lowercase `"pending"` normalized to `"PENDING"`).
   - Quarantined records produced: **7 records** (each mapped to exact error codes: `ERR_REQUIRED_FIELD_MISSING`, `ERR_PATTERN_VIOLATION`, `ERR_TYPE_CONVERSION`, `ERR_ENUM_VIOLATION`).
   - Zero data loss invariant confirmed: $N_{\text{total}} \equiv N_{\text{valid}} + N_{\text{quarantine}} = 5 + 7 = 12$.
6. **Headless CLI Gate:**  
   - `recon gate --source ... --contract ... --json` returns non-zero exit code due to critical quarantine findings, emitting structured preflight JSON.

---

### Dimension B: Participant Opinions & Feedback `[PENDING]`

Because independent external software engineers have not yet sat for live unassisted testing sessions, participant opinions cannot be claimed as empirical fact:
- **Participant Setup Experience:** `[PENDING]`
- **Comprehension of Contextual Inspector & Flow Graph:** `[PENDING]`
- **Trust in Synthesized Python Adapter Code:** `[PENDING]`
- **Willingness to Adopt in Production:** `[PENDING]`

> *Note:* Any previous claims of "developer satisfaction" in earlier gate documents reflected internal author self-testing or synthetic benchmarks, not independent external developers.

---

### Dimension C: Researcher Usability Walkthrough & Observed Friction `[VERIFIED]`

During internal dry-runs of the unassisted pilot protocol, the research team identified three concrete friction points that could impede an external developer:

1. **CLI Command Consistency:**  
   - *Observation:* The documentation intermittently refers to `recon serve --port 8000` and `recon web --port 8000`. While both commands work via Click aliases, inconsistent naming in user-facing guides creates hesitation during Task 2.
2. **Contextual Inspector Discovery for Mouse-First Developers:**  
   - *Observation:* The Inspector drawer displays crucial evidence (sample values, type requirements, alternative candidate columns). It can be opened via the keyboard shortcut `I` or by hovering over nodes. However, developers working exclusively with mouse clicks can miss the `I` shortcut if the visual drawer toggle is subtle.
3. **Explaining Ambiguity in Mapping:**  
   - *Observation:* When multiple source columns match a target field (e.g. `postal_code_primary` vs `postal_code_secondary`), Recon marks the field `UNRESOLVED` to prevent guessing. While this is mathematically safe, a developer without prior training might wonder why an obvious match wasn't selected automatically unless an explanatory tooltip clarifies: *"Multiple candidate columns detected — manual selection required."*

---

### Dimension D: Unresolved Adoption Questions `[UNRESOLVED]`

These critical product questions can only be answered once external human participants complete the pilot:

1. **Table vs Flow Graph Preference:**  
   Do backend engineers prefer reviewing mappings in a dense tabular grid, or does the SVG Flow Graph provide meaningful disambiguation value?
2. **Adapter Code Trust:**  
   Will developers feel comfortable using an auto-generated Python adapter in their production pipelines, or will they treat Recon purely as an advisory diagnostic tool and write their own transformation code?
3. **CLI Gate vs Web Studio Adoption:**  
   Will developers adopt Recon as an interactive preflight studio during partner onboarding, or will they primarily embed `recon gate` in CI/CD pipelines as a pre-commit check?
4. **Friction Threshold vs Ad-Hoc Scripts:**  
   Is the setup time of Recon low enough that developers will reach for it instead of writing a quick 20-line throwaway Python script?

---

## 3. Comparative Workflow Analysis

| Dimension | Typical Ad-Hoc Script (Pandas / DictReader) | Schema Validator (Pydantic / jsonschema) | Recon Integration Readiness Engine |
| :--- | :--- | :--- | :--- |
| **Mapping Timing** | Manual hardcoded dictionary lookup | None (Requires prior mapping) | Automated proposal with evidence & human approval |
| **Ambiguity Detection** | Arbitrary choice (silently picks one column) | None (Fails on missing field) | Flags candidate alternatives; halts on ambiguity |
| **Data Loss Behavior** | Drops bad rows silently or crashes on error | Rejects entire payload or bad rows | Zero-loss quarantine accounting ($N_{\text{total}} = N_{\text{val}} + N_{\text{quar}}$) |
| **Execution Safety** | Arbitrary unchecked script execution | In-process schema validation | In-process AST sandbox with dangerous builtins stripped |
| **Auditing & Traceability** | Unstructured terminal printouts | Validation error exception tree | Versioned mapping spec, readiness state, quarantine JSON |

---

## 4. Evaluation Summary & Readiness for External Cohort

The technical foundation, benchmark ground truth, and unassisted protocol are fully validated and reproducible. The next critical milestone requires recruiting 3–5 external developers to execute the standardized protocol and record real-world developer sentiment.
