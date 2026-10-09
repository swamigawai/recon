# Recon Integration Readiness Report

**Source Dataset:** `nyc_311_5k_real.csv`  
**Target Contract:** `service_request_target_contract` (v1.0.0)  
**Fingerprint:** `b0d0477d50f5ff36...`  
**Recon Engine Version:** `v0.1.0`  
**Generated:** `2026-10-09 16:41:06 UTC`  

## Readiness Status: **NEEDS HUMAN REVIEW**

> Integration requires human review for 3 warning(s) or ambiguous decision(s).

### Warnings & Review Items
- **[REVIEW]** [R004_DATE_PARSING_RISK] Non-Standard Datetime Format on ['created_at', 'created_date']: Source timestamp 'created_date' uses format '%Y-%m-%dT%H:%M:%S.%f', while target requires ISO-8601.
- **[REVIEW]** [R004_DATE_PARSING_RISK] Non-Standard Datetime Format on ['closed_at', 'closed_date']: Source timestamp 'closed_date' uses format '%Y-%m-%dT%H:%M:%S.%f', while target requires ISO-8601.
- **[REVIEW]** [R005_ENUM_VIOLATION] Allowed Value Domain Violation on ['status', 'status']: Source column 'status' contains values ['Assigned', 'In Progress', 'Unspecified'] outside target allowed domain ['OPEN', 'CLOSED', 'PENDING'].

## Risk Assessment Summary

| Severity | Findings Count | Impact |
| :--- | :---: | :--- |
| **Critical** | 0 | Blocks deployment |
| **High** | 3 | Probable runtime error / data loss |
| **Medium** | 0 | Data quality degradation / format variance |
| **Low** | 0 | Informational observation |

### Detailed Risk Findings
- **`R004_DATE_PARSING_RISK`** (HIGH): Non-Standard Datetime Format
  - **Affected Fields:** created_at, created_date
  - **Evidence:** Source timestamp 'created_date' uses format '%Y-%m-%dT%H:%M:%S.%f', while target requires ISO-8601.
  - **Action:** Generate explicit datetime transformation parsing '%Y-%m-%dT%H:%M:%S.%f' to ISO-8601.
- **`R004_DATE_PARSING_RISK`** (HIGH): Non-Standard Datetime Format
  - **Affected Fields:** closed_at, closed_date
  - **Evidence:** Source timestamp 'closed_date' uses format '%Y-%m-%dT%H:%M:%S.%f', while target requires ISO-8601.
  - **Action:** Generate explicit datetime transformation parsing '%Y-%m-%dT%H:%M:%S.%f' to ISO-8601.
- **`R005_ENUM_VIOLATION`** (HIGH): Allowed Value Domain Violation
  - **Affected Fields:** status, status
  - **Evidence:** Source column 'status' contains values ['Assigned', 'In Progress', 'Unspecified'] outside target allowed domain ['OPEN', 'CLOSED', 'PENDING'].
  - **Action:** Add category mapping dictionary or quarantine records with unmapped domain values.

## Verified Profiling Facts

- **Total Rows:** 5,000
- **Total Columns:** 44
- **Duplicate Rows:** 0

| Column Name | Inferred Type | Null Count | Null % | Distinct Count | Anomalies |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `unique_key` | `integer` | 0 | 0.0% | 5000 | None |
| `created_date` | `datetime` | 0 | 0.0% | 4214 | None |
| `closed_date` | `datetime` | 2813 | 56.26% | 1450 | None |
| `agency` | `string` | 0 | 0.0% | 13 | None |
| `agency_name` | `string` | 0 | 0.0% | 13 | None |
| `complaint_type` | `string` | 0 | 0.0% | 109 | None |
| `descriptor` | `string` | 83 | 1.66% | 326 | None |
| `descriptor_2` | `string` | 3227 | 64.54% | 239 | None |
| `location_type` | `string` | 249 | 4.98% | 62 | None |
| `incident_zip` | `integer` | 41 | 0.82% | 181 | None |
| `incident_address` | `string` | 131 | 2.62% | 3544 | None |
| `street_name` | `string` | 131 | 2.62% | 1762 | None |
| `cross_street_1` | `string` | 1257 | 25.14% | 1491 | None |
| `cross_street_2` | `string` | 1262 | 25.24% | 1507 | None |
| `intersection_street_1` | `string` | 1250 | 25.0% | 1457 | None |
| `intersection_street_2` | `string` | 1252 | 25.04% | 1482 | None |
| `address_type` | `string` | 32 | 0.64% | 5 | None |
| `city` | `string` | 309 | 6.18% | 46 | None |
| `landmark` | `string` | 1612 | 32.24% | 1440 | None |
| `facility_type` | `string` | 5000 | 100.0% | 0 | None |
| `status` | `string` | 0 | 0.0% | 5 | None |
| `due_date` | `datetime` | 4988 | 99.76% | 12 | None |
| `resolution_description` | `string` | 1632 | 32.64% | 50 | None |
| `resolution_action_updated_date` | `datetime` | 1603 | 32.06% | 1604 | None |
| `community_board` | `string` | 0 | 0.0% | 68 | None |
| `council_district` | `integer` | 99 | 1.98% | 51 | None |
| `police_precinct` | `string` | 0 | 0.0% | 78 | None |
| `bbl` | `integer` | 551 | 11.02% | 3114 | None |
| `borough` | `string` | 0 | 0.0% | 6 | None |
| `x_coordinate_state_plane` | `integer` | 83 | 1.66% | 3497 | None |
| `y_coordinate_state_plane` | `integer` | 83 | 1.66% | 3549 | None |
| `open_data_channel_type` | `string` | 0 | 0.0% | 4 | None |
| `park_facility_name` | `string` | 0 | 0.0% | 1 | Constant |
| `park_borough` | `string` | 0 | 0.0% | 6 | None |
| `vehicle_type` | `string` | 4762 | 95.24% | 6 | None |
| `taxi_company_borough` | `string` | 4997 | 99.94% | 2 | None |
| `taxi_pick_up_location` | `string` | 4975 | 99.5% | 21 | None |
| `bridge_highway_name` | `string` | 4969 | 99.38% | 17 | None |
| `bridge_highway_direction` | `string` | 4980 | 99.6% | 15 | None |
| `road_ramp` | `string` | 4981 | 99.62% | 4 | None |
| `bridge_highway_segment` | `string` | 4970 | 99.4% | 21 | None |
| `latitude` | `float` | 83 | 1.66% | 3614 | None |
| `longitude` | `float` | 83 | 1.66% | 3614 | None |
| `location` | `string` | 83 | 1.66% | 3614 | None |

## Adapter Validation & Test Outcomes

- **Adapter:** `service_request_target_contract_adapter`
- **Input Records Tested:** 5000
- **Valid Outputs:** 3455
- **Quarantined Records:** 1545
- **Contract Pass Rate:** `69.1%`
- **Target Contract Valid:** `PASS`
- **Synthetic Fault Tests:** `ALL PASSED`

### Synthetic Test Suite Details

| Test Case | Status | Expected Behavior | Actual Behavior |
| :--- | :---: | :--- | :--- |
| `test_valid_record_transformation` | **PASS** | Valid source record transforms into contract-compliant payload | Success |
| `test_missing_required_field_quarantine` | **PASS** | Missing required field triggers quarantine with explicit error | Quarantined as expected |
| `test_malformed_date_quarantine` | **PASS** | Malformed date triggers quarantine with datetime parsing error | Quarantined as expected |

## Decisions Required from Human Reviewer
- [ ] Review risk on ['created_at', 'created_date']: Generate explicit datetime transformation parsing '%Y-%m-%dT%H:%M:%S.%f' to ISO-8601.
- [ ] Review risk on ['closed_at', 'closed_date']: Generate explicit datetime transformation parsing '%Y-%m-%dT%H:%M:%S.%f' to ISO-8601.
- [ ] Review risk on ['status', 'status']: Add category mapping dictionary or quarantine records with unmapped domain values.
