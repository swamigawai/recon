# Recon Gate 09 — Independent Ground Truth Specification

**Scenario:** B2B Vendor Invoicing & Logistics Controlled Pilot  
**Purpose:** Pre-declared independent ground truth specification for Gate 09 controlled local pilot validation. Written before execution.  
**Domain:** Supply chain, enterprise B2B procurement, and tax logistics.  
**Source Dataset:** `tests/fixtures/gate09_pilot_b2b_vendor_invoices.csv` (12 rows, 14 columns)  
**Target Contract:** `tests/fixtures/target_contract_gate09_pilot_b2b.json` (11 fields)  

---

## 1. Schema & Field Alignment Specification

| Target Field | Target Type | Req | Nullable | Expected Source Column | Match Classification | Expected Proposer Behavior |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| `invoice_id` | string | Yes | No | `doc_number` | Unfamiliar | `None` / `UNRESOLVED` (requires manual override) |
| `supplier_gstin` | string | Yes | No | `gst_reg_no` | Unfamiliar | `None` / `UNRESOLVED` (requires manual override) |
| `buyer_pan` | string | Yes | No | `entity_pan` | Unfamiliar | `None` / `UNRESOLVED` (requires manual override) |
| `billing_date` | datetime | Yes | No | `billing_date` | Exact Match | `billing_date` / `PROPOSED` |
| `net_amount` | float | Yes | No | `net_amount` | Exact Match | `net_amount` / `PROPOSED` |
| `tax_amount` | float | No | Yes | `tax_amount` | Exact Match | `tax_amount` / `PROPOSED` |
| `hsn_sac_code` | string | Yes | No | `hsn_sac_code` | Exact Match | `hsn_sac_code` / `PROPOSED` |
| `destination_pin`| string | Yes | No | `postal_code_primary` | Ambiguous / Unfamiliar | `UNRESOLVED` (requires manual override; competing with `postal_code_secondary`) |
| `bank_ifsc` | string | Yes | No | `bank_ifsc` | Exact Match | `bank_ifsc` / `PROPOSED` |
| `invoice_status` | string (enum)| Yes | No | `invoice_status` | Exact Match (casing) | `invoice_status` / `PROPOSED` (with `uppercase_strip`) |
| `dispatch_notes` | string | No | Yes | `dispatch_notes` | Exact Match | `dispatch_notes` / `PROPOSED` |

**Extraneous Source Columns to Omit:**
- `driver_phone_number`
- `warehouse_dock_no`
- `postal_code_secondary`

---

## 2. Pre-Declared Mapping & Blocker Expectations

1. **Automatic Proposals:** 7 fields (`billing_date`, `net_amount`, `tax_amount`, `hsn_sac_code`, `bank_ifsc`, `invoice_status`, `dispatch_notes`).
2. **Unresolved Required Fields:** 4 fields (`invoice_id`, `supplier_gstin`, `buyer_pan`, `destination_pin`).
3. **Readiness State:** `BLOCKED` (triggering Rule `R001_MISSING_REQUIRED_FIELD`).
4. **Adapter Generation Block:** Refused until human approval provides explicit overrides.
5. **Approved Overrides:**
   - `invoice_id <- doc_number`
   - `supplier_gstin <- gst_reg_no`
   - `buyer_pan <- entity_pan`
   - `destination_pin <- postal_code_primary`

---

## 3. Pre-Declared Fault Ledger & Disposition Accounting

| Row Index | Row Identifier | Injected Scenario / Condition | Expected Disposition | Expected Error Code | Expected Error Message Substring |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | `INV-00042` | Clean record; identifier with leading zeros (`"INV-00042"`) | **VALID** | None | Preserved as string `"INV-00042"` |
| **2** | `INV-00042` | **Exact duplicate** of Row 1 | **VALID** | None | Preserved identically without silent discard |
| **3** | `INV-00043` | Clean record; text resembling error (`"ERROR: Client reported damaged outer box but contents verified intact and accepted"`) | **VALID** | None | Preserved intact without false quarantine |
| **4** | `INV-00044` | Clean record; lowercase enum (`"pending"` $\rightarrow$ `"PENDING"`), empty tax amount $\rightarrow$ `None` | **VALID** | None | Converted and normalized |
| **5** | `INV-00045` | Clean record; null-like human phrase (`"None of the items were returned during inspection"`) | **VALID** | None | Preserved intact as string |
| **6** | Row 6 | **Fault 1:** Missing required invoice ID (`doc_number=""`) | **QUARANTINED** | `ERR_REQUIRED_FIELD_MISSING` | `"Required non-nullable field 'invoice_id' is missing or null"` |
| **7** | `INV-00047` | **Fault 2:** Malformed GSTIN (`27AAPFU0939F199` - 14th char is 9, not Z) | **QUARANTINED** | `ERR_PATTERN_VIOLATION` | `"does not match pattern"` |
| **8** | `INV-00048` | **Fault 3:** Malformed 9-char PAN (`AAPF0939F`) | **QUARANTINED** | `ERR_PATTERN_VIOLATION` | `"does not match pattern"` |
| **9** | `INV-00049` | **Fault 4:** Malformed 5-digit PIN code (`40001`) | **QUARANTINED** | `ERR_PATTERN_VIOLATION` | `"does not match pattern"` |
| **10** | `INV-00050` | **Fault 5:** Malformed IFSC code (`SBIN1001234` - 5th char is 1, not 0) | **QUARANTINED** | `ERR_PATTERN_VIOLATION` | `"does not match pattern"` |
| **11** | `INV-00051` | **Fault 6:** Currency string in float (`"₹ 1,50,000.00"`) | **QUARANTINED** | `ERR_TYPE_CONVERSION` | `"Cannot parse float for 'net_amount'"` |
| **12** | `INV-00052` | **Fault 7:** Illegal status enum category (`"WRITTEN_OFF"`) | **QUARANTINED** | `ERR_ENUM_VIOLATION` | `"not in allowed values"` |

---

## 4. Expected Record Accounting

$$\text{Total Input Records (12)} = \text{Valid Transformed Records (5)} + \text{Quarantined Records (7)}$$
$$\Delta = 0 \text{ (Zero Data Loss)}$$
