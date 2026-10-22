# Recon — Frequently Asked Questions (FAQ)

**Product:** Recon — The Integration Readiness Engine  
**Status:** `[VERIFIED TECHNICAL FAQ]`

---

### Q1: In plain terms, what does Recon do?
**A:** Recon is an **integration preflight engine**. When you receive a third-party data file (like a CSV or JSON dump from a partner, customer, or vendor), Recon audits it against your internal target schema contract *before* you write custom ingestion code or build an ETL pipeline. It tells you what will break (missing required fields, ambiguous columns, regex pattern violations, type errors, enum mismatches) and generates a verified Python adapter to safely transform conforming records and quarantine non-conforming records with zero data loss.

---

### Q2: How does Recon differ from schema validators like Pydantic or jsonschema?
**A:** 
- **Schema validators** (Pydantic, jsonschema) are **downstream runtime tools**. They assume incoming data has *already* been mapped, renamed, and formatted to match target field names. If an external partner names an invoice number `doc_number` instead of `invoice_id`, a schema validator simply fails and rejects the entire record or payload.
- **Recon** operates **upstream at the preflight stage**. It infers source types, matches heterogeneous column names, flags ambiguous alternatives (e.g. `bill_to_zip` vs `ship_to_zip`), requires human approval for unmapped required fields, and synthesizes the transformation adapter code that maps the partner's fields to your schema.

---

### Q3: How does Recon differ from ETL platforms (Airflow, dbt) or iPaaS tools (Zapier, Fivetran)?
**A:** Recon does not schedule recurring cron jobs, orchestrate DAGs, or sync SaaS databases. Recon is a **developer tool used during integration development and onboarding**. It answers the preflight question: *"Is this partner feed ready for ingestion, what are the mapping rules, and how should edge cases be quarantined?"* Once Recon synthesizes a certified Python adapter and a versioned mapping specification, developers can run the adapter inside their existing Airflow tasks, Lambda functions, or backend workers.

---

### Q4: Why do ambiguous mappings require human approval instead of AI auto-mapping?
**A:** When an incoming dataset contains multiple candidate columns matching a single target field (for example, `billing_postal_code` and `shipping_postal_code` both matching target `postal_code`), guessing is dangerous. An AI model or naive heuristic might arbitrarily choose one, silently corrupting delivery addresses or financial billing. Recon adheres to a **fail-closed, zero-guessing policy**: it marks ambiguous fields `UNRESOLVED`, displays the candidate evidence, and halts adapter compilation until an engineer explicitly approves the selection.

---

### Q5: What is "zero-loss quarantine accounting"?
**A:** Many ad-hoc scripts drop invalid records silently or crash halfway through a batch. Recon enforces the mathematical invariant:
$$N_{\text{total\_input}} \equiv N_{\text{valid\_output}} + N_{\text{quarantined\_records}}$$
Every input record is deterministically accounted for. Conforming records are transformed into valid output, while invalid records are routed to a structured quarantine ledger containing the original raw row, the failing field name, and standardized error codes (e.g. `ERR_PATTERN_VIOLATION`, `ERR_TYPE_CONVERSION`, `ERR_REQUIRED_FIELD_MISSING`).

---

### Q6: Where are session data and uploaded files stored?
**A:** In the local developer studio (`recon serve`), sessions are held in-memory in the local FastAPI process. When the server process stops, in-memory state is purged. Work is persisted by exporting a versioned `recon_mapping_spec.json` and generated adapter files to disk. No data is ever uploaded to external cloud services or remote databases.

---

### Q7: What are the security limitations of Recon's adapter sandbox?
**A:** Generated adapters are executed in an in-process Python namespace where dangerous builtins (`__import__`, `open`, `eval`, `exec`, `os`, `sys`, `subprocess`, `socket`) are stripped. However, **this is NOT an OS-level sandbox** (no Linux cgroups, namespaces, or container isolation). Recon is engineered for **local developer preflight use on local files**, **NOT for public multi-tenant SaaS hosting** where untrusted users can execute arbitrary code.

---

### Q8: What would be required to run Recon as a public multi-tenant SaaS?
**A:** Running Recon as a multi-tenant cloud service would require:
1. Sandboxed container isolation (e.g. Docker, gVisor, or Firecracker microVMs) with strict CPU, memory, and runtime time-to-live ceilings.
2. Authenticated user sessions and persistent tenant-isolated database storage.
3. Network policy egress filters preventing local network scanning.
4. Comprehensive third-party penetration testing.

---

### Q9: Can Recon be used headlessly in CI/CD pipelines?
**A:** Yes. The `recon gate` CLI command is specifically designed for automated quality gates in CI/CD pipelines (e.g. GitHub Actions). It evaluates incoming datasets against contracts and versioned mapping specifications, supports strict mode and configurable quarantine rate limits (`--max-quarantine-pct`), and emits machine-readable JSON reports with standard POSIX exit codes (`0` for pass, `1` for preflight failure, `2` for configuration errors).
