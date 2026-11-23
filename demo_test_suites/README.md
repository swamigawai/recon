# Recon Integration Test Suites (5 Comprehensive Scenarios)

These benchmark test suites are engineered for verifying Recon's data readiness, schema alignment, and zero-loss quarantine capabilities across diverse file formats and enterprise domains.

---

### Suite Overview

| # | Suite Directory | Raw Source Format | Target Schema | Key Features Tested |
| :---: | :--- | :--- | :--- | :--- |
| **01** | `01_healthcare_encounters_csv/` | **CSV** (`.csv`) | HIPAA Clinical Encounter JSON Schema | Regex patterns (`ENC-######`, ICD-10), ISO-8601 timestamps, enum enforcement, billing float precision. (20 clean rows, 5 intentional quarantine faults). |
| **02** | `02_ecommerce_orders_excel/` | **Excel** (`.xlsx`) | Shopify/Stripe Fulfillment Schema | **Multi-sheet workbook detection** (automatically selects raw orders tab over summary dashboard), currency amounts, country codes, boolean flags. (12 clean, 4 faults). |
| **03** | `03_fintech_b2b_invoices_jsonl/` | **JSON Lines** (`.jsonl`) | Peppol B2B Vendor Invoice Schema | Key-value mapping, currency code enums (`USD`, `EUR`, `GBP`, `INR`), subtotal/tax float calculation, status enums. (8 clean, 3 faults). |
| **04** | `04_logistics_freight_manifest_tsv/` | **Tab-Separated** (`.tsv`) | Global Carrier Dispatch Schema | Automatic tab delimiter detection, carrier enums (`FEDEX`, `DHL`, `UPS`, `MAERSK`), weight in kg, hazmat booleans. (8 clean, 3 faults). |
| **05** | `05_relational_customers_and_orders_multitable/` | **Multi-Table CSVs** | Consolidated Analytics Warehouse Schema | **Multi-Entity Table Matchmaker** (Primary Key / Foreign Key detection `C101` across `table_a_customers_master.csv` and `table_b_orders_transactions.csv`, 1:N cardinality). |

---

### How to Test Any Suite in Recon

1. Open your live Recon application on Render (or localhost:8000).
2. Go to **Stage 01 (Intake Cockpit)**.
3. In **Port 1 (Source Raw Data)**: Upload the `source_*` file from any suite.
4. In **Port 2 (Target Contract)**: Upload the matching `target_contract_*.json` from the same suite.
5. Click **"Run Preflight Assessment"**.
6. Review:
   - **Stage 02 (Profile Matrix):** Observe 100% columnar statistics and type inference.
   - **Stage 03 (Mapping Studio):** See semantic auto-matching and SVG flow lines.
   - **Stage 04 (Risk Radar):** Notice how Recon catches the intentional faults (bad regex patterns, missing required IDs).
   - **Stage 06 & 07 (Validation & Export):** Download both the **Clean Valid Records CSV** and the **Quarantined Records CSV** with exact line-level diagnostic justifications!
