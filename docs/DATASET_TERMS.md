# Dataset Terms and Provenance Record

## 1. NYC 311 Service Requests (Primary Benchmark Dataset)

- **Source Portal:** NYC Open Data / Data.gov
- **Source URL:** https://catalog.data.gov/dataset/311-service-requests-from-2010-to-present
- **Direct Portal:** https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9
- **Terms of Use / License:** Public domain / NYC Open Data Terms of Use (public access, no proprietary restrictions on redistribution for benchmarking or evaluation, City of New York attribution maintained).
- **Retrieval Date:** 9 October 2026.
- **Selection Method:**
  - **Synthetic Fixture (`tests/fixtures/synthetic_nyc_311.csv`):** 10 curated representative records capturing standard fields, missing values (null closed dates, null postal codes), edge-case values ("Unspecified" borough), mixed casing ("Closed", "Open"), and trailing whitespace.
  - **Benchmark Sample (`benchmarks/fixtures/nyc_311_sample.csv`):** Extracted slice preserving original headers and raw values, with SHA-256 fingerprint recorded in the benchmark fault ledger.
- **Immutability Guarantee:** All raw inputs are stored in read-only fixture directories. Recon strictly treats raw inputs as immutable and never modifies or overwrites source files during ingestion, profiling, adapter execution, or reporting.
