# Recon Gate 07 — Independent Ground Truth Specification

**Scenario:** Healthcare Clinical Encounters to Central Hospital Encounter Contract  
**Purpose:** Pre-declared, independent ground-truth specification for Gate 07 output correctness validation. Prepared prior to running the Recon engine.  
**Domain:** Healthcare Information Systems (EHR & Clinical Encounter Records).  
**Source Dataset:** `tests/fixtures/healthcare_encounters_raw.csv` (10 rows, CSV format)  
**Target Contract:** `tests/fixtures/target_contract_healthcare_encounter.json` (11 fields)  

---

## 1. Schema & Field Alignment Specification

| Target Field | Target Type | Req | Nullable | Expected Source Column | Match Classification | Expected Proposer Behavior |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| `encounter_id` | string | Yes | No | `visit_ref` | Unfamiliar | `None` / `UNRESOLVED` (requires manual override) |
| `patient_id` | string | Yes | No | `subject_id` | Unfamiliar | `None` / `UNRESOLVED` (requires manual override) |
| `encounter_date` | datetime | Yes | No | `encounter_date` | Exact Match | `encounter_date` / `PROPOSED` |
| `department` | string | Yes | No | `department` | Exact Match (casing)| `department` / `PROPOSED` (with `uppercase_strip`) |
| `clinician_notes` | string | No | Yes | `clinician_notes` | Exact Match | `clinician_notes` / `PROPOSED` |
| `copay_amount` | float | No | Yes | `copay_amount` | Exact Match | `copay_amount` / `PROPOSED` |
| `visit_duration_minutes` | integer | Yes | No | `duration_min` | Unfamiliar | `None` / `UNRESOLVED` (requires manual override) |
| `billing_code` | string | Yes | No | `billing_code` | Exact Match (regex) | `billing_code` / `PROPOSED` |
| `emergency_flag` | boolean | Yes | No | `emergency_flag` | Exact Match | `emergency_flag` / `PROPOSED` |
| `facility_code` | string | Yes | No | `facility_code_primary` | Ambiguous Match | `facility_code_primary` / `PROPOSED` (Alt: `facility_code_billing`) |
| `insurance_provider` | string | No | Yes | `insurance_provider` | Exact Match | `insurance_provider` / `PROPOSED` |

**Extra Source Columns (Not in Target Contract):**
- `room_number` (Ignored; must not appear in valid transformed outputs)
- `facility_code_billing` (Ignored alternative column)

---

## 2. Pre-Declared Mapping & Blocker Expectations

1. **Automatic Proposals:** 8 fields (`encounter_date`, `department`, `clinician_notes`, `copay_amount`, `billing_code`, `emergency_flag`, `facility_code`, `insurance_provider`).
2. **Unresolved Required Fields:** 3 fields (`encounter_id`, `patient_id`, `visit_duration_minutes`).
3. **Readiness State:** `BLOCKED` (due to 3 unmapped required fields triggering Rule `R001_MISSING_REQUIRED_FIELD`).
4. **Adapter Generation Block:** Automated adapter generation must be strictly refused until a human reviewer approves overrides for the 3 missing required fields.
5. **Approved Mapping Plan (Human Overrides):**
   - `encounter_id` <- `visit_ref`
   - `patient_id` <- `subject_id`
   - `visit_duration_minutes` <- `duration_min`

---

## 3. Pre-Declared Fault Ledger & Quarantine Expectations

| Row Index | Row Identifier | Test Purpose / Injected Fault | Expected Disposition | Expected Error Code | Expected Error Message Substring |
| :---: | :---: | :--- | :---: | :--- | :--- |
| **1** | `ENC-1001` | Clean, valid record; lowercase department `"cardiology"` | **VALID** | None | Transformed to `"CARDIOLOGY"`, extra `room_number` omitted |
| **2** | `ENC-1002` | Clean, valid record; legitimate text resembling null: `"None of the above"` | **VALID** | None | Preserved as exact string `"None of the above"` |
| **3** | `ENC-1003` | Clean, valid record; nulls in optional nullable fields (`clinician_notes=""`, `copay_amount="NULL"`) | **VALID** | None | Transformed to `None` for both optional fields |
| **4** | `ENC-1004` | Clean, valid record; legitimate text `"N/A - see chart notes from EMT"` and `"Not Applicable Inc."` | **VALID** | None | Preserved as exact strings |
| **5** | Row 5 | **Fault 1:** Missing required non-nullable `encounter_id` (`visit_ref=""`) | **QUARANTINED** | `ERR_REQUIRED_FIELD_MISSING` | `"Required non-nullable field 'encounter_id' is missing or null"` |
| **6** | `ENC-1006` | **Fault 2:** Illegal enum category (`department="DERMATOLOGY"`) | **QUARANTINED** | `ERR_ENUM_VIOLATION` | `"Value 'DERMATOLOGY' for 'department' not in allowed values"` |
| **7** | `ENC-1007` | **Fault 3:** Regex pattern mismatch on billing code (`billing_code="INVALID_CODE_999"`) | **QUARANTINED** | `ERR_PATTERN_VIOLATION` | `"does not match pattern"` |
| **8** | `ENC-1008` | **Fault 4:** Currency symbol in float (`copay_amount="$35.00"`) | **QUARANTINED** | `ERR_TYPE_CONVERSION` | `"Cannot parse float for 'copay_amount' from '$35.00'"` |
| **9** | `ENC-1009` | **Fault 5:** Non-standard US datetime (`encounter_date="10/01/2024 03:30:00 PM"`) | **QUARANTINED** | `ERR_DATETIME_PARSE` | `"Cannot parse datetime for 'encounter_date'"` |
| **10** | `ENC-1010` | **Fault 6:** Non-integer string in integer duration (`duration_min="forty-five"`) | **QUARANTINED** | `ERR_TYPE_CONVERSION` | `"Cannot parse integer for 'visit_duration_minutes'"` |

---

## 4. Expected Record Accounting

$$\text{Total Input Records (10)} = \text{Valid Output Records (4)} + \text{Quarantined Records (6)}$$
$$\Delta = 0 \text{ (Zero Data Loss)}$$
