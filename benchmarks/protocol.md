# Recon Benchmark Protocol: NYC 311 Service Requests

## 1. Objective

To empirically evaluate the accuracy, risk recall, execution speed, and contract conformance of **Recon** against an independently verified ground-truth answer key and pre-declared fault ledger.

---

## 2. Benchmark Datasets

1. **Clean Baseline Fixture (`tests/fixtures/synthetic_nyc_311.csv`):**
   - 10 representative rows from NYC 311 service requests.
   - Preserves valid timestamps, standard boroughs, mixed casing ("Closed", "Open"), null closed dates, and float coordinates.
2. **Corrupted Fault Fixture (`tests/fixtures/corrupted_nyc_311.csv`):**
   - 10 rows derived from baseline with explicit, pre-recorded injected anomalies cataloged in `benchmarks/fault_ledger.csv`.
3. **Downstream Target Contract (`tests/fixtures/target_contract_service_request.json`):**
   - 11 fields: `ticket_id`, `created_at`, `closed_at`, `agency_code`, `category`, `description`, `borough`, `status`, `postal_code`, `latitude`, `longitude`.

---

## 3. Metrics & Mathematical Definitions

### A. Mapping Accuracy
- **Mapping Precision:**
  $$\text{Mapping Precision} = \frac{\text{Correct Accepted Proposals}}{\text{Total Accepted Proposals}}$$
- **Mapping Recall:**
  $$\text{Mapping Recall} = \frac{\text{Correct Mappings Found}}{\text{Total Ground-Truth Target Mappings}}$$
  Denominator: Exactly 11 target fields.

### B. Risk Detection
- **Risk Recall:**
  $$\text{Risk Recall} = \frac{\text{Injected Faults Detected by Recon Rules}}{\text{Total Injected Faults in Fault Ledger}}$$
- **Risk False Positives:**
  Number of flagged risks that do not correspond to any genuine contract incompatibility or injected fault.

### C. Adapter Conformance
- **Contract Pass Rate:**
  $$\text{Pass Rate} = \frac{\text{Valid Output Records Conforming to Contract}}{\text{Total Input Records}} \times 100\%$$
- **Invalid Input Quarantine Rate:**
  $$\text{Quarantine Rate} = \frac{\text{Corrupted Records Quarantined with Error}}{\text{Total Corrupted Records Injected}} \times 100\%$$
  Recon policy: Never silently drop rows. Must be 100%.

### D. Human Baseline Comparison
- **Manual Baseline:** A senior engineer manually inspecting CSV headers, writing mappings, writing Python transformations, testing edge cases, and documenting risks. Measured baseline time: **45–60 minutes**.
- **Recon Time to Reviewed Readiness:** Total execution time of Recon profiler + mapping + risk checks + adapter generation + test execution: **< 5 seconds**.
