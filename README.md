# Recon — The Integration Readiness Engine

> **"Know what will break before you build the integration."**

Recon is an evidence-backed integration readiness engine. Given an unfamiliar source dataset and a target contract, Recon produces deterministic profiling, evidence-backed mappings, actionable risk findings, reviewable adapters, and contract validation before you write pipeline code.

---

## The First Vertical Slice

Recon begins with one measured, reproducible path:
**NYC 311 CSV sample → Deterministic Profile → Target Contract → Mapping Proposals with Evidence → Risk Findings → Approved Mapping → Adapter Code → Tests & Validation → Readiness Report.**

---

## Quick Start & Setup

### Prerequisites
- Python 3.11+
- Git

### Installation

Clone the repository and install dependencies in editable mode:

```bash
git clone https://github.com/your-org/recon.git
cd recon
python -m pip install -e ".[dev]"
```

### Running Tests

Run the complete test suite with one command:

```bash
pytest
```

---

## Core Principles

1. **Deterministic core; AI as assistant:** Code computes counts, nulls, types, constraints, and validation. LLMs never calculate facts.
2. **Evidence before confidence:** Every mapping candidate and risk finding cites verifiable evidence or rule IDs.
3. **Uncertainty is a feature:** Ambiguous mappings are flagged as unresolved, requiring human decision rather than silent guessing.
4. **Generated code must prove itself:** An adapter is not ready until its generated test suite passes and output conforms to the target contract.
5. **Local-first privacy:** Data is processed locally by default; raw row values are never logged or leaked.

---

## Project Structure

```text
recon/
├── README.md                                  # Setup and usage guide
├── PRODUCT.md                                 # Scope, severity rules, non-goals, readiness definition
├── ARCHITECTURE.md                            # Module boundaries, models, data flow
├── PROJECT_CHECKLIST_AND_MASTER_PROMPT.md     # Master build checklist and execution prompt
├── pyproject.toml                             # Packaging, dependencies, and test configuration
├── src/recon/
│   ├── __init__.py
│   ├── exceptions.py                          # Consistent actionable error hierarchy
│   ├── logging.py                             # Privacy-preserving structured logging
│   └── contracts/                             # Target contract models and loaders
├── tests/
│   ├── fixtures/
│   │   ├── synthetic_nyc_311.csv              # Synthetic 10-row NYC 311 fixture
│   │   └── target_contract_service_request.json # Explicit target JSON contract
│   └── unit/
│       └── test_foundation.py                 # Foundation test suite
└── .github/workflows/
    └── ci.yml                                 # Continuous Integration workflow
```

---

## Key Documentation

- [`PRODUCT.md`](file:///D:/recon/PRODUCT.md) — Product requirements, severity definitions, readiness criteria, and non-goals.
- [`ARCHITECTURE.md`](file:///D:/recon/ARCHITECTURE.md) — Architectural models, module boundaries, and data pipelines.
- [`PROJECT_CHECKLIST_AND_MASTER_PROMPT.md`](file:///D:/recon/PROJECT_CHECKLIST_AND_MASTER_PROMPT.md) — Master checklist and phase tracking.

---

## License

MIT License. Copyright (c) 2026 Swami Gawai. See [`LICENSE`](file:///D:/recon/LICENSE) for details.
