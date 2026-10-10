# Gate 03: Second-Domain Evaluation & Generalization Review

**Engine:** Recon — The Integration Readiness Engine  
**Gate:** Gate 03 (Second-Domain Evaluation & Generalization Review)  
**Execution Date:** 2026-10-10  
**Test Suite Status:** **PASSED (55/55 tests passing in 5.59s)**

---

## 1. Executive Summary
Gate 03 subjected Recon to two distinct evaluations:
1. **Commercial E-Commerce Order Validation (Olist):** Validating complex types (floats, timestamps, enums, regex patterns) and proving the **Zero Data Loss Law** against a pre-declared 6-fault ledger.
2. **Fair Generalization & Mapping Quality Benchmark (Unfamiliar Schema):** Stress-testing the automated mapping engine on an unfamiliar logistics manifest (`manifest_no`, `party_id`, `workflow_stage`, etc.) without pre-seeded synonyms to measure true zero-tuning mapping capability.

---

## 2. Contract Validation Results (Olist Clean Dataset)

Evaluated against `target_contract_ecommerce_order.json` (9 fields: order ID, customer ID, order status enum, purchase timestamp, delivery timestamp, payment float, freight float, city, 2-letter state regex):

| Metric | Target Specification | Empirical Result | Status |
| :--- | :--- | :--- | :--- |
| **Total Ingested Records** | 10 | 10 | **PASS** |
| **Valid Output Records** | 10 | 10 | **PASS** |
| **Quarantined Records** | 0 | 0 | **PASS** |
| **Contract Pass Rate** | 100.0% | 100.0% | **PASS** |
| **Synthetic Edge Tests** | All edge tests pass | 4/4 synthetic sandbox tests passed | **PASS** |
| **Readiness Status** | `READY` | `READY` (0 blocking reasons) | **PASS** |

---

## 3. Fault Detection & Quarantine Results (Pre-Declared Fault Ledger)

Evaluated against `olist_orders_corrupted.csv` containing 4 clean baseline records and 6 injected integration failure cases:

| Fault ID | Hazard Description | Injected Input | Expected Action | Actual System Response | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F01** | Missing Mandatory ID | `order_id = ""` | Quarantine | `Required non-nullable field 'order_id' is missing or null` | **CAUGHT (100%)** |
| **F02** | Illegal Status Enum | `order_status = "RETURNED_TO_SENDER"` | Quarantine | `Value 'RETURNED_TO_SENDER' for 'order_status' not in allowed values` | **CAUGHT (100%)** |
| **F03** | Currency Formatting Symbol | `payment_value = "$129.90"` | Quarantine | `Cannot parse float for 'payment_value' from '$129.90'` | **CAUGHT (100%)** |
| **F04** | Non-Standard Datetime | `order_purchase_timestamp = "09/25/2024 02:30:00 PM"` | Quarantine | `Cannot parse datetime for 'order_purchase_timestamp' using format '%Y-%m-%dT%H:%M:%SZ'` | **CAUGHT (100%)** |
| **F05** | Null in Non-Nullable Field | `payment_value = ""` | Quarantine | `Required non-nullable field 'payment_value' is missing or null` | **CAUGHT (100%)** |
| **F06** | Regex Pattern Mismatch | `customer_state = "CALIFORNIA"` | Quarantine | `Value 'CALIFORNIA' for 'customer_state' does not match pattern ^[A-Z]{2}$` | **CAUGHT (100%)** |

### The "No Data Loss" Proof
$$\text{Total Records} = \text{Valid Records} + \text{Quarantined Records} \implies 10 = 4 + 6$$
- Clean rows passed: **4 (100% contract compliance)**
- Corrupted rows quarantined: **6 (100% pre-declared fault recall)**
- Silently dropped rows: **0 (Zero)**

---

## 4. Mapping & Generalization Quality Results

To test generalization fairly, we evaluated mapping quality across two distinct scenarios:

### Scenario A: Identical / Synonym-Seeded Schema (Olist E-Commerce)
- **Target Fields:** 9
- **Source Columns:** 9 exact or synonym-seeded matches (`order_id`, `payment_value`, etc.)
- **Proposed Mappings:** 9 / 9
- **Mapping Precision:** 100.0% (9/9)
- **Mapping Recall:** 100.0% (9/9)
- *Assessment:* High precision, but reliant on exact naming or pre-declared synonym tables.

### Scenario B: Fair Unfamiliar Schema (Logistics Dispatch Manifest)
Evaluated against `warehouse_manifest_unfamiliar.csv` with a pre-declared Ground-Truth Answer Key:
- `consignment_id` $\to$ `manifest_no`
- `recipient_code` $\to$ `party_id`
- `dispatch_status` $\to$ `workflow_stage`
- `departure_time` $\to$ `departed_at`
- `gross_weight_kg` $\to$ `weight_metric`
- `declared_value` $\to$ `valuation`
- `destination_city` $\to$ `dropoff_locality`
- `destination_state` $\to$ `dropoff_province`

**Empirical Mapping Scores (Zero-Tuning Baseline):**
- **Total Target Fields:** 8
- **Correct Mappings:** 0
- **Incorrect / False Mappings:** **0 (Zero False Matches)**
- **Unresolved Mappings:** **8 (100%)**
- **Mapping Precision:** N/A (0 false positives)
- **Mapping Recall:** **0.0%**

### Safety & Fail-Safe Verification
While syntactic heuristic recall was 0% on unfamiliar vocabulary, the engine's **fail-safe safety boundary operated perfectly**:
1. **Zero Hallucination:** The engine did not fabricate false pairings.
2. **Refused Blind Code Generation:** `generate_adapter()` threw `AdapterError` refusing to compile code with unresolved required fields.
3. **Fail-Closed Readiness:** The readiness report correctly transitioned to `ReadinessState.BLOCKED` with 14 explicit blocking explanations, forcing human review before downstream execution.

---

## 5. Architectural Defect Fixes Delivered in Gate 03
1. **Datetime Candidate Frequency Ordering ([`type_inference.py`](file:///D:/recon/src/recon/profiling/type_inference.py)):** Fixed alphabetical sorting bug where a single rogue American timestamp (`%m/...`) overrode 90% dominant ISO timestamps (`%Y-...`). Patterns are now ordered by frequency of occurrence descending.
2. **Standard Default Datetime Format ([`generator.py`](file:///D:/recon/src/recon/adapters/generator.py)):** Replaced NYC 311 hardcoded fallback format (`%m/%d/%Y %I:%M:%S %p`) with standard ISO-8601 (`%Y-%m-%dT%H:%M:%SZ`).
3. **Regex Quantifier Bracket Isolation ([`generator.py`](file:///D:/recon/src/recon/adapters/generator.py)):** Prevented regular expression repetition quantifier braces `{n,m}` inside generated Python strings from being evaluated as f-string expressions.
4. **Benchmark Portability ([`test_ecommerce_gate03_benchmark.py`](file:///D:/recon/tests/benchmark/test_ecommerce_gate03_benchmark.py)):** Replaced hardcoded `D:/recon` output directory with repository-relative `benchmarks_dir` fixture.

---

## 6. Known Limitations
1. **Syntactic Vocabulary Boundary:** The deterministic proposer relies on exact matching and `SYNONYMS` dictionaries. Without semantic embeddings or LLM-assisted matching, completely unfamiliar column names will always require human-in-the-loop review.
2. **Single-Table Streaming:** Recon currently evaluates single tabular or flattened JSON streams. Multi-table relational joins (e.g., joining an orders table to an order items table) must be denormalized prior to ingestion.
3. **Interactive Human Approval:** Currently, human approval is executed programmatically via `approve_mapping_plan(overrides=...)`. A web UI or CLI prompt is required for non-technical users to provide mapping overrides.

---

## 7. Recommendation for Gate 04 (Website Readiness)
**Status: READY FOR MINIMAL WEBSITE / API INTERFACE.**

The engine's core promise is:
> *"Know what will break before you build the integration."*

The fair generalization evaluation proves that Recon's safety mechanisms work as advertised:
- On familiar schemas, it automates mapping, profiling, risk detection, and adapter generation end-to-end.
- On unfamiliar schemas, it **safely blocks execution**, generates zero hallucinations, and produces an auditable readiness report showing exactly what a human must resolve.
- On corrupted data, it achieves **100% fault detection** with **zero data loss**.

With 55 / 55 tests passing across 3 domains and 2 data formats, the underlying engine is stable and safe to wrap with a minimal FastAPI backend and frontend UI.
