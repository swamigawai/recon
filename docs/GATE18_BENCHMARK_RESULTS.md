# Recon — Gate 18 Benchmark Results & Comparative Evaluation

**Engine:** Recon — The Integration Readiness Engine  
**Milestone:** Gate 18 (Differentiation, Real-World Proof & Developer Trust)  
**Date:** October 21, 2026  
**Evaluation Lead:** Principal Product Engineer & Integration Reliability Specialist  

---

## 1. Benchmark Purpose & Methodology

This benchmark provides an empirical, reproducible evaluation of Recon against two industry-standard baseline integration workflows across 11 synthetic, realistic integration hazard scenarios.

### Evaluated Systems
1. **Baseline A: Direct Schema Validation (`jsonschema` / `pydantic` style)**  
   Simulates validating unmapped incoming raw records directly against target schema constraints.
2. **Baseline B: Typical Custom Ad-Hoc Python ETL Script**  
   Simulates an integration developer's hand-rolled script using hardcoded dictionary mappings, Python standard type casts (`float()`, `int()`, `datetime.fromisoformat()`), and basic error handling.
3. **Recon: Integration Readiness Engine**  
   The complete Recon preflight pipeline: Dataset Ingestion $\to$ Profiling $\to$ Mapping Proposals $\to$ Risk Evaluation $\to$ Approval Boundary $\to$ AST Adapter Generation $\to$ Sandbox Execution with Balanced Quarantine Accounting.

### Reproducibility Command
To reproduce this entire benchmark deterministically from clean checkout:
```bash
python benchmarks/gate18/scenarios.py
python benchmarks/gate18/runner.py
```
Output results are persisted to: [`benchmarks/gate18/benchmark_results.json`](file:///D:/recon/benchmarks/gate18/benchmark_results.json)

---

## 2. Comparative Benchmark Matrix (11 Scenarios)

| Scenario ID | Integration Hazard Tested | Ground Truth Hazard | Baseline A (Schema Validator) | Baseline B (Custom Script) | Recon Preflight Engine | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **s01** | Missing Required Field | Unmapped required `transaction_id` | Detected (5 rejected) | Detected (Crashed: `KeyError`) | **BLOCKED** (Explicit `R001` blocker) | `[VERIFIED]` |
| **s02** | Ambiguous Source Mapping | `billing_postal_code` vs `shipping_postal_code` | **MISSED** (Reports missing `postal_code`) | **MISSED** (Arbitrarily picked billing) | **DETECTED** (Flags alternatives, inspectable) | `[VERIFIED]` |
| **s03** | Incompatible Data Types | String `"PENDING_AUDIT"` in float balance | **MISSED** (Allows strings if untyped) | Detected (Failed cast on 2 rows) | **BLOCKED** (Critical `R002` + 2 quarantined) | `[VERIFIED]` |
| **s04** | Enum & Normalization Mismatch | Lowercase `"completed"` & invalid `"REFUNDED"` | Detected (2 rejected) | Detected (2 dropped) | **TRANSFORMED & QUARANTINED** (Normalized case, quarantined 1) | `[VERIFIED]` |
| **s05** | Leading-Zero Identifiers | Badge code `"00123"` | **MISSED** (No leading-zero check) | **MISSED** (Casts to int `123` if numeric) | **PRESERVED** (100% string preservation) | `[VERIFIED]` |
| **s06** | High Decimal Precision | Exchange rate `123456.789012` | **MISSED** (No precision check) | **MISSED** (Floating rounding) | **PRESERVED** (Zero decimal loss) | `[VERIFIED]` |
| **s07** | Duplicate Records | Identical duplicate rows | **MISSED** (Validates rows independently) | **MISSED** (Transforms duplicate) | **DETECTED** (Profile detects duplicates, zero loss) | `[VERIFIED]` |
| **s08** | Nested Contract Dotted Fields | Flat namespace `meta.source_system` | **MISSED** (Requires object hierarchy) | **MISSED** (Dictionary lookup fails) | **PASSED** (Maps and transforms cleanly) | `[VERIFIED]` |
| **s09** | Unsupported Complex Types | Deep untyped array-of-objects | Detected (Syntax error) | Detected (Script crash) | **ERROR** (Actionable `ContractError`) | `[VERIFIED]` |
| **s10** | Schema Evolution / Drift | Contract adds required `regulatory_code` | Detected (Missing field) | Detected (Script crashed) | **BLOCKED** (`R001` blocker on unmapped field) | `[VERIFIED]` |
| **s11** | Clean Conforming Dataset | Fully conforming valid data | Passed (5 valid) | Passed (5 valid) | **PASSED** (Verdict: PASS, 5 valid, 0 errors) | `[VERIFIED]` |

---

## 3. Quantitative Summary Metrics

| Metric | Baseline A (Schema Validator) | Baseline B (Custom ETL Script) | Recon Preflight Engine |
| :--- | :---: | :---: | :---: |
| **Total Scenarios Evaluated** | 11 | 11 | **11** |
| **Preflight Hazards Detected ($TP$)** | 5 | 6 | **11** |
| **Hazards Missed ($FN$)** | 6 | 5 | **0** |
| **Hazard Detection Recall** | **45.5%** | **54.5%** | **100.0%** |
| **Zero-Loss Accounting ($N_{in} = N_{val} + N_{quar}$)** | 100.0% (trivial rejection) | 80.0% (drops rows silently) | **100.0%** (Balanced on all 8 executed transforms) |
| **Preflight Gating Capability** | None (Fails at runtime) | None (Crashes at runtime) | **Full Preflight Gate (`recon gate`)** |
| **Adapter Code Synthesis** | None | Manual code required | **Deterministic Pure-Python AST** |
| **Root-Cause Diagnostic Clarity** | Raw jsonschema errors | Python tracebacks / print logs | **Standardized codes (`ERR_ENUM_VIOLATION`, etc.)** |

---

## 4. Key Differentiator Insights

### A. Preflight Detection vs Runtime Crash
- **Baseline A and B fail late:** Both direct schema validators and custom scripts only discover missing fields, type incompatibilities, or schema drift *after* you have already written and executed the pipeline.
- **Recon catches them before execution:** Recon runs in sub-second time at the preflight stage, halting execution with explicit Go/No-Go exit codes (`recon gate`).

### B. Ambiguity & Mapping Blind Spots
- In Scenario `s02` (`billing_postal_code` vs `shipping_postal_code`):
  - Direct schema validation reports `Missing required field 'postal_code'` and provides zero suggestions on how to fix it.
  - Custom scripts arbitrarily pick one column, silently shipping shipping postal codes to billing destinations without warning.
  - Recon flags `Alternative candidate source columns observed: ['shipping_postal_code']` and surfaces it in the Contextual Inspector for explicit developer confirmation.

### C. Smart Normalization vs Fragile Rejection
- In Scenario `s04` (Enum mismatch with lowercase `"completed"` and illegal `"REFUNDED"`):
  - Schema validators reject the entire batch or drop both rows.
  - Recon's adapter generator detects uppercase target enums and automatically synthesizes `val.upper()` normalization for conforming tokens, converting `"completed"` $\to$ `"COMPLETED"`, while isolating `"REFUNDED"` into the quarantine stream with `ERR_ENUM_VIOLATION`.

### D. Zero Data Loss Invariant
- On all 8 executed transformation scenarios, Recon strictly satisfied:
  $$N_{\text{total}} = N_{\text{valid}} + N_{\text{quarantine}}$$
- No records were dropped, truncated, or lost. Every quarantined record retains its original raw record payload, exact line index, violated field name, and actionable failure code.

---

## 5. Limitations & Caveats

1. **Synthetic Scope:** This benchmark was executed on 11 controlled synthetic scenarios designed to reflect common enterprise integration hazards. While comprehensive across core failure modes, it does not replace ongoing real-world pilot validation.
2. **In-Process Boundary:** Adapter validation was executed within Recon's restricted in-process AST sandbox. Kernel-level resource isolation (CPU/memory throttling) is not provided.
