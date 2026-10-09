# Recon Limitations & Known Boundary Conditions

## 1. Current Architectural Boundaries (MVP Vertical Slice)

In accordance with product principles, Recon prioritizes a verified, deterministic vertical slice over speculative generalizations. The current boundaries are:

1. **Single-Table Ingestion:**
   - Recon currently ingests single-table CSV sources. Multi-table relational joins, foreign key graph traversal, and database link exploration are intentionally deferred to future milestones.
2. **Tabular CSV Focus:**
   - Ingestion natively processes delimited text files (CSV, TSV). Unstructured documents, nested Avro, Parquet, or streaming Kafka topics are unsupported in MVP v0.1.0.
3. **Deterministic Heuristic Mapping:**
   - Mapping proposals rely on name normalization, dictionary synonyms, observed data types, sample values, and constraint matching. Complex multi-field arithmetic transformations (e.g., combining `first_name` and `last_name` into `full_name`) currently require explicit human transformation rules in the approved plan.
4. **Local Execution Scale:**
   - The default in-memory profiler processes files up to 100MB. Multi-gigabyte distributed datasets require distributed query backends (DuckDB or Polars), planned for v0.2.0.

---

## 2. Epistemological Disclosures

1. **Inferences vs Facts:**
   - Type inference is heuristic: while a 100% integer match on a sample confirms candidate integer type, semantic types (such as whether a 5-digit number is a postal code or an employee ID) remain inferences requiring human approval.
2. **Date Format Regional Ambiguity:**
   - Ambiguous numeric dates (e.g., `04/05/2024`) are evaluated against US vs ISO standards based on explicit format priority lists. Recon flags non-ISO formats with `R004_DATE_PARSING_RISK` so engineers can explicitly confirm the date convention.
