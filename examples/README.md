# 🧪 Recon Quick Test Examples

This folder contains pre-packaged sample test fixtures designed for a 60-second end-to-end test of Recon.

---

## Files in this Directory

1. **`sample_raw_feed.csv` (Port 1 - Raw Ingest Feed)**
   - 15 realistic enterprise transaction rows.
   - Intentionally loaded with real-world edge cases:
     * Leading-zero numeric string IDs (e.g. `00142`).
     * Dirty whitespace padding (e.g. `" Globex Logistics "`).
     * Unlisted categorical enum tokens (e.g. `REFUND_PENDING` and `BI_WEEKLY`).
     * Unparseable corrupt date token on row 15 (`INVALID_DATE_TOKEN`).
     * Null tokens (`N/A`, `null`, `""`).

2. **`sample_target_schema.json` (Port 2 - Destination Target Contract)**
   - Strict JSON Schema (Draft-07).
   - Enforces required fields, string regex types, and allowed enum domains (`PAID`, `PENDING`, `OVERDUE`, `CANCELLED`).

---

## 30-Second Test Walkthrough

1. Launch Recon:
   ```bash
   python scripts/fde_launcher.py
   ```
2. Open the browser at **`http://127.0.0.1:8000`**.
3. **Stage 01:** Drag `examples/sample_raw_feed.csv` into **Port 1**, and `examples/sample_target_schema.json` into **Port 2**.
4. **Stage 02:** Review the **100% Columnar Profile**.
5. **Stage 03:** In **Mapping Studio**, map source columns to target fields (or supply a fallback default for any unmapped target).
6. **Stage 04:** In **Audit Preflight**, resolve any R001 blockers, enter your name/email, and click **Sign-Off & Approve**.
7. **Stage 05 & 06:** Watch Recon compile the pure-Python AST adapter and validate all 15 records in the sandbox.
   - **Expected Result:** **12 Valid records** and **3 Quarantined records** (with row-level diagnostic error codes). Zero records dropped!
8. **Stage 07:** Download your signed **`readiness_dossier.zip`**.
