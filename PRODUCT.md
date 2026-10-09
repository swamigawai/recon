# PRODUCT.md — Recon: The Integration Readiness Engine

## 1. Product Overview

- **Product Name:** Recon (The Integration Readiness Engine)
- **Product Promise:** **"Know what will break before you build the integration."**
- **First User:** A software or data engineer tasked with integrating an unfamiliar source dataset into a target system with an explicit contract.
- **Core Hypothesis:** Discovering data incompatibilities, ambiguous semantics, and contract mismatches *before* writing integration code dramatically reduces integration cycle time, defects, and post-deployment pipeline failures.

---

## 2. Supported First Path (The Vertical Slice)

The MVP strictly focuses on one end-to-end, deterministic vertical slice:
```
Source CSV Dataset (e.g., NYC 311 Service Requests)
   │
   ▼
[Deterministic Profiler] ──▶ Verified Profile (Counts, Types, Nulls, Ranges)
   │
   ▼
[Target Contract] ─────────▶ Explicit Target Schema (Types, Nullability, Enums, Required)
   │
   ▼
[Mapping Engine] ──────────▶ Evidence-Backed Proposals (Direct, Transform, Ambiguous, Missing)
   │
   ▼
[Risk Engine] ─────────────▶ Actionable Risk Findings (Critical, High, Medium, Low)
   │
   ▼
[Human Review Boundary] ───▶ Approved Mapping Plan (Explicit Human Decisions)
   │
   ▼
[Adapter Generator] ───────▶ Reviewable Python Adapter Code + Test Suite
   │
   ▼
[Validation Engine] ───────▶ Contract Validation & Isolated Test Execution
   │
   ▼
[Readiness Engine] ────────▶ Human-Readable & Machine-Readable Readiness Report
```

---

## 3. Epistemological Framework: What Recon Knows

To prevent hallucination, false confidence, and opaque scores, Recon rigorously partitions every output into four categories:

1. **Verified Fact:** An empirical observation computed by deterministic code (e.g., exactly 5,000 rows ingested, 14 null values in column `incident_zip`, observed format `YYYY-MM-DD`).
2. **Inference:** A heuristic or statistical deduction that may be mistaken (e.g., column `created_date` inferred as timestamp based on 100% regex match; column `borough` matches target field `location_borough` with 0.88 semantic similarity).
3. **Warning / Risk:** An evidence-backed threat that an integration requirement will fail or corrupt data (e.g., target field `complaint_type` is required and non-nullable, but source column contains 2.1% nulls).
4. **Unknown:** A question or ambiguity where evidence is insufficient for Recon to decide safely (e.g., does source status code `0` mean "Open" or "Resolved"?). Recon flags unknowns and requires human resolution.
5. **Not Checked / Skipped:** Explicitly recorded checks that were not evaluated due to missing dependencies, unsupported types, or skipped configurations.

---

## 4. Severity Rules

| Severity | Definition | Examples | Readiness Impact |
| :--- | :--- | :--- | :--- |
| **Critical** | Guaranteed integration failure or contract violation. | Required target field has no mapping; required target field is non-nullable but source has nulls; source/target types fundamentally incompatible without conversion. | **Blocks Readiness** |
| **High** | High probability of runtime error, data loss, or semantic corruption. | Ambiguous date formatting (e.g., `MM/DD/YYYY` vs `DD/MM/YYYY`); unmapped source values violating target enum/category constraints; lossy type conversions. | **Blocks Readiness unless explicitly waived** |
| **Medium** | Degradation of data quality, partial loss of precision, or potential performance penalty. | Truncation of string lengths; float-to-integer rounding; unexpected leading/trailing whitespace; unmapped non-critical source columns. | **Warning (Requires review)** |
| **Low** | Informational observation or non-standard formatting. | Minor casing differences; harmless extra padding; unreferenced optional target fields. | **Informational** |

---

## 5. Human Approval Boundary & What Recon Must NEVER Do

Recon operates under strict safety and agency constraints:

### When Human Approval is Mandatory
- Approving any candidate mapping marked as `ambiguous` or `transformation_required`.
- Specifying default/fallback values for missing required target fields.
- Waiving any `High` severity risk finding.
- Selecting record quarantine, drop, or fail-fast policies for invalid records.
- Approving generated adapter code before execution.

### What Recon Must NEVER Do Automatically
- **Never execute generated adapter code silently** without explicit user invocation.
- **Never fabricate or synthesize values** to force contract validation to pass.
- **Never overwrite raw source data**.
- **Never silently drop or discard invalid rows** without logging or quarantining.
- **Never rely on an LLM to calculate facts** (row counts, null percentages, distinct counts, schema validation).
- **Never send raw dataset values to remote APIs** without explicit user opt-in and consent.

---

## 6. Definition of "Ready"

An integration is declared **READY** if and only if:
1. Every required field in the target contract has an approved, valid mapping.
2. Zero unresolved `Critical` severity risks exist.
3. All `High` severity risks have either been resolved by transformation or explicitly accepted by a human reviewer.
4. An adapter has been generated from the approved mapping plan.
5. The generated adapter passes 100% of its generated test suite and produces output that strictly conforms to the target contract.

If any of these conditions are unmet, readiness is declared **NOT READY** or **BLOCKED**, with explicit citations of blocking causes.

---

## 7. Scope Boundaries & 12-Day MVP Boundary

### MVP Scope (Days 1–12)
- Single-table CSV ingestion.
- Explicit JSON target schema contracts.
- Deterministic profiling (counts, nulls, distincts, types, ranges, whitespace).
- Deterministic heuristic mapping proposals with evidence citations.
- Explainable risk rules with stable rule IDs.
- Deterministic adapter generation in readable Python.
- Adapter validation and isolated test execution.
- Human-readable Markdown and machine-readable JSON readiness reports.
- Comprehensive benchmark against NYC 311 ground-truth answer key and fault ledger.

### Non-Goals (Explicitly Deferred)
- Relational joins across multiple tables (deferred until NYC 311 slice is proven).
- Database connectors (Postgres, Snowflake, BigQuery) or live API pollers.
- Multi-agent autonomous debate or web scraping.
- Visual web UI or cloud dashboard (CLI first).
- Arbitrary streaming or real-time pipelines.

---

## 8. Success Metrics

1. **Mapping Precision:** $\frac{\text{Correct accepted proposals}}{\text{All accepted proposals}} \ge 90\%$ on benchmark.
2. **Mapping Recall:** $\frac{\text{Correct mappings found}}{\text{All labeled ground-truth mappings}} \ge 90\%$ on benchmark.
3. **Risk Recall:** $\frac{\text{Known injected risks detected}}{\text{All known injected risks in fault ledger}} = 100\%$.
4. **False Positive Rate:** Documented and minimized; every flag traces to verifiable evidence.
5. **Contract Pass Rate:** 100% of valid test rows produced by the approved adapter pass target contract validation.
6. **Time to Reviewed Readiness:** Total human time measured against a documented manual baseline.
