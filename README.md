<div align="center">

<img src="docs/assets/banner.svg" alt="Recon — The Integration Readiness Engine" width="100%">

<br/>
<br/>

<!-- Modern Tech Stack & Status Badges -->
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.0-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![CI / CD](https://img.shields.io/badge/CI%2FCD-Passing-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/swamigawai/recon/actions)
[![Tests](https://img.shields.io/badge/Tests-214%20Passing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/swamigawai/recon)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)

<br/>

<h3><b>Know what will break before you build the integration.</b></h3>

<p align="center">
  <b>Recon</b> is an air-gapped data integration readiness platform that detects schema drift, type mismatches, and data quality defects in third-party partner datasets <i>before</i> pipeline deployment.
</p>

<p align="center">
  <a href="#-quick-start"><b>Quick Start</b></a> •
  <a href="#-the-7-stage-integration-lifecycle"><b>7-Stage Architecture</b></a> •
  <a href="#-visual-studio-tour"><b>Visual Studio Tour</b></a> •
  <a href="#-why-recon-the-paradigm-shift"><b>Why Recon</b></a> •
  <a href="demo_test_suites/"><b>Demo Test Suites (5 Domains)</b></a> •
  <a href="#-cli--cicd-gate"><b>CI/CD Gate</b></a> •
  <a href="docs/FDE_PLAYBOOK.md"><b>FDE Playbook</b></a>
</p>

</div>

---

## 🛠️ Tech Stack & Architecture Foundation

Recon is engineered with modern, production-grade technologies optimized for execution speed, auditability, and zero vendor lock-in:

<div align="center">

| Component | Technology | Role & Capability |
| :--- | :--- | :--- |
| **Language Runtime** | **Python 3.11 / 3.12** | High-performance type hinting, pattern matching, and native AST compilation. |
| **High-Throughput Streaming** | **Polars + PyArrow** | Chunked streaming engine processing multi-gigabyte files with sub-linear memory overhead. |
| **Schema Validation** | **Pydantic v2 (Rust Core)** | Blazing-fast runtime schema validation and contract coercion. |
| **API & Web Server** | **FastAPI + Uvicorn ASGI** | Async REST endpoints, background session cleanup, and sub-millisecond route dispatch. |
| **Code Synthesis** | **Python Abstract Syntax Tree (AST)** | Compiles approved mappings into standalone, reviewable PEP-8 Python scripts. |
| **Testing Harness** | **Pytest + Starlette TestClient** | 214 deterministic unit, integration, and security tests with 100% pass rate. |
| **Relational Matchmaker** | **Vectorized Set Containment & PK Discovery** | Discovers Primary/Foreign keys, 1:N cardinality, and identical duplicate tables. |
| **Frontend Studio** | **Swiss Modern UI + Tailwind CSS** | Zero-latency browser interface with dynamic flow graph and virtualized telemetry. |
| **Containerization** | **Docker & Docker Compose** | Reproducible, isolated local and staging environments with multi-stage builds. |

</div>

---

## ⚡ The 7-Stage Integration Lifecycle

Recon replaces brittle scripts and opaque black-box guessing with an auditable, multi-tier deterministic preflight architecture:

```mermaid
flowchart TD
    classDef inputStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef contractStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef profileStyle fill:#022c22,stroke:#34d399,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef engineStyle fill:#18181b,stroke:#a1a1aa,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef gateStyle fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef signStyle fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef sandboxStyle fill:#1e293b,stroke:#fbbf24,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef outValid fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef outQuar fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef outPack fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#f8fafc,rx:6,ry:6;
    classDef mathProof fill:#0c4a6e,stroke:#0284c7,stroke-width:3px,color:#f8fafc,rx:8,ry:8;

    subgraph INTAKE["⚡ TIER 1: DUAL-PORT INTAKE & CRYPTOGRAPHIC STAGING"]
        direction LR
        SRC["📂 RAW DATA INTAKE PORT\n• Multi-Format: CSV, XLSX, TSV, JSONL\n• Auto-Encoding & UTF-8 BOM Strip\n• Deterministic SHA-256 Fingerprint"]:::inputStyle
        TGT["📜 TARGET CONTRACT PORT\n• JSON Schema / OpenAPI 3.x\n• Invariant Field Types & Patterns\n• Strict Domain Enum Whitelists"]:::contractStyle
    end

    subgraph PREFLIGHT["🔬 TIER 2: 100% COLUMNAR FORENSICS & TOPOLOGY MATCHING"]
        direction LR
        PROF["📊 ZERO-SAMPLING PROFILER\n• 100% Row/Cell Analysis\n• Null Ratios & Cardinality\n• Whitespace & Type Anomalies"]:::profileStyle
        MATCH["🧠 VECTORIZED MATCHMAKER\n• Jaro-Winkler & Levenshtein\n• PK/FK Join Discovery (1:1, 1:N)\n• Duplicate Table Detection"]:::engineStyle
    end

    subgraph GOVERNANCE["🛡️ TIER 3: DETERMINISTIC RISK RADAR & GO/NO-GO AUDIT GATE"]
        direction LR
        RADAR["🚨 9-RULE SAFETY MATRIX\nR001-R009 Violation Analysis\nType Incompatibilities · Null Drift"]:::gateStyle
        AUDIT{"🔒 PREFLIGHT GATE\nMissing Required Fields?"}:::gateStyle
        SIGN["✍️ LEAD ENGINEER SIGN-OFF\nAudit Handle Stamp + Risk Acknowledgment\nIrreversible In-Memory Commit"]:::signStyle
    end

    subgraph COMPILER["⚡ TIER 4: PURE-PYTHON AST SYNTHESIS & AIR-GAPPED SANDBOX"]
        direction LR
        AST["🐍 AST COMPILER (Python 3.11)\n• Typed Casting & Date Normalizers\n• Sanitized Variable Names\n• Standalone PEP-8 adapter.py"]:::sandboxStyle
        RUNTIME["🧪 ISOLATED SANDBOX RUNTIME\n• Process Boundary / Air-Gapped\n• Dangerous Builtins Stripped\n• Zero Network / Zero Telemetry"]:::sandboxStyle
    end

    subgraph EGRESS["📦 TIER 5: VERIFIED DUAL-STREAM EGRESS & CI/CD DEPLOY PACK"]
        direction TB
        subgraph STREAMS["Dual Delivery Channels"]
            VALID["✅ CLEAN VALID RECORDS\n(1-Click CSV & JSONL)\nReady for Production Database / Warehouse"]:::outValid
            QUAR["⚠️ QUARANTINE FORENSIC LEDGER\n(1-Click CSV & JSONL)\nLine Numbers + Exact Error Violations"]:::outQuar
            BUNDLE["📦 ENTERPRISE CI/CD DEPLOY PACK (.zip)\nadapter.py + Dockerfile + GitHub Actions + Schema"]:::outPack
        end
        PROOF["⚖️ MATHEMATICAL CONSERVATION PROOF (Zero Silent Drops)\nN_total ≡ N_valid + N_quarantined  ·  Parity: 100.000%"]:::mathProof
    end

    SRC & TGT --> PROF & MATCH
    PROF & MATCH --> RADAR
    RADAR --> AUDIT
    AUDIT -->|Hard Blocker: Unmapped Fields| RADAR
    AUDIT -->|Approved & Signed| SIGN
    SIGN --> AST
    AST --> RUNTIME
    RUNTIME --> VALID & QUAR & BUNDLE
    VALID & QUAR --> PROOF
```

---

## 🎯 Why Recon: The Paradigm Shift

Traditional ETL pipelines fail silently because they treat integration as an ad-hoc scripting exercise after data is already ingested. Recon shifts validation upstream to preflight.

| Dimension | Custom Ad-Hoc Scripts | Generic Cloud ETL | Recon Readiness Engine |
| :--- | :---: | :---: | :---: |
| **Data Quality Scan** | Ad-hoc runtime crashes | Post-ingestion error tables | **Deterministic 100% Columnar Preflight** |
| **Schema Drift & Gaps** | Discovered in production | Silent column drops | **Refuses to guess; explicit human approval gate** |
| **Data Loss Policy** | Drops rows or crashes silently | Unlogged loss or partial loads | **Zero-Loss Guarantee ($N_{\text{in}} \equiv N_{\text{val}} + N_{\text{quar}}$)** |
| **Output Deliverable** | Fragile glue-code | Proprietary platform lock-in | **Dual Output: Direct Clean CSVs + Standalone Python AST Adapter** |
| **Execution Architecture** | Cloud SaaS dependency | Cloud SaaS phone-home | **100% Air-Gapped / Zero External Telemetry** |

---

## 📸 Visual Studio Tour

Recon provides an engineering-grade, high-contrast dark studio interface designed for rapid keyboard navigation, clear visual hierarchies, and zero latency.

<details open>
<summary><b>01 Ingest Cockpit — Multi-Format Intake & Cryptographic Staging</b></summary>
<br/>
<p>Dual-port ingestion supporting raw CSV, Excel (XLSX), TSV, and JSONL data alongside JSON Schema / OpenAPI 3.x contracts with cryptographic SHA-256 fingerprinting, automatic encoding detection, and UTF-8 BOM auto-stripping.</p>
<img src="benchmarks/results/screenshots/step01_ingest_desktop.png" alt="Ingest Cockpit" width="100%">
</details>

<details>
<summary><b>02 Profile Matrix — 100% Columnar Forensics</b></summary>
<br/>
<p>Calculates null percentages, distinct value cardinalities, whitespace anomalies, and dynamic type distributions across 100% of records without lossy sampling or arbitrary truncation.</p>
<img src="benchmarks/results/screenshots/step02_profile_matrix.png" alt="Profile Matrix" width="100%">
</details>

<details>
<summary><b>03 Mapping Studio &amp; Relational Matchmaker — Semantic Alignment &amp; Join Discovery</b></summary>
<br/>
<p>High-confidence matches are auto-proposed with transparent match evidence and SVG flow graphs. Features vectorized Primary Key &amp; Foreign Key discovery across multiple tables with cardinality evaluation (1:1, 1:N) and identical duplicate table detection.</p>
<img src="benchmarks/results/screenshots/step03_mapping_studio.png" alt="Mapping Studio" width="100%">
</details>

<details>
<summary><b>04 Risk Radar &amp; Approval Gate — Pre-Flight Safety Audit</b></summary>
<br/>
<p>Evaluates 9 deterministic risk rules (R001–R009). Strictly blocks adapter generation if required contract fields are unmapped; logs warnings for domain enum deviations with explicit engineering handle sign-off.</p>
<img src="benchmarks/results/screenshots/step04_risk_radar.png" alt="Risk Radar" width="100%">
</details>

<details>
<summary><b>05 Adapter Workbench — Pure-Python AST Synthesis</b></summary>
<br/>
<p>Inspects the generated, reviewable Python adapter synthesized by the AST compiler. Standalone PEP-8 code featuring typed casting, datetime normalization, and zero proprietary framework lock-in.</p>
<img src="benchmarks/results/screenshots/step05_adapter_workbench.png" alt="Adapter Workbench" width="100%">
</details>

<details>
<summary><b>06 Validation Lab &amp; Quarantine Forensics — Zero-Loss Mathematical Proof</b></summary>
<br/>
<p>Executes the synthesized adapter inside an isolated, air-gapped sandbox. Conforming records stream to valid output; faulty records route to the quarantine ledger with line numbers and diagnostic justifications. Verified by mathematical invariant: <code>N_total ≡ N_valid + N_quarantined</code>.</p>
<img src="benchmarks/results/screenshots/step06_validation_lab.png" alt="Validation Lab" width="100%">
</details>

<details>
<summary><b>07 Integration Summary &amp; Dual Egress — Certified Production Deliverables</b></summary>
<br/>
<p>Delivers for both business analysts and data platform engineers: direct 1-click clean CSV and JSONL downloads for immediate data operations, quarantined CSVs with attached error justifications, the target schema contract (.json), and a complete Enterprise CI/CD Deploy Pack (.zip) containing <code>adapter.py</code>, Docker container definitions, GitHub Actions workflow, and a verified Markdown audit dossier.</p>
<img src="benchmarks/results/screenshots/step07_readiness_dossier.png" alt="Readiness Dossier" width="100%">
</details>

---

## 🚀 Quick Start

### 1. One-Click Zero-Friction Launch (Recommended)

Recon includes smart self-healing launchers for every operating system that automatically check your Python runtime, establish an isolated virtual environment, install dependencies, resolve port conflicts, and launch the Web Studio:

```bash
# On Windows (Command Prompt / PowerShell or double-click in Explorer):
start.bat

# On macOS / Linux:
chmod +x start.sh && ./start.sh
```

---

### 2. Manual Developer Installation

```bash
# Clone the repository
git clone https://github.com/swamigawai/recon.git
cd recon

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install --upgrade pip
pip install -e ".[dev]"  # Or fallback: pip install -r requirements.txt
```

---

### 3. Verify Environment Health (`recon doctor`)

Run the self-diagnostic suite to ensure your runtime, dependencies, disk permissions, UTF-8 BOM engines, and pipeline invariants are 100% operational:

```bash
recon doctor

# Machine-readable JSON output for automated CI preflights:
recon doctor --json
```

---

### 4. Launch the Web Studio Manually

```bash
# One-command FDE launcher (checks runtime, auto-installs missing packages, resolves port & opens browser)
python scripts/fde_launcher.py

# Or start the local server directly
recon serve --host 0.0.0.0 --port 8000
```
Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)** to launch the Recon Studio.

---

## 🤖 CLI & CI/CD Gate

Recon provides a headless CLI command to audit data batches in continuous integration pipelines:

```bash
recon gate \
  --source tests/fixtures/synthetic_nyc_311.csv \
  --contract tests/fixtures/target_contract_service_request.json \
  --max-quarantine-pct 5.0 \
  --json > gate_result.json
```

### CLI Exit Code Contract

| Exit Code | Status | Meaning |
| :---: | :--- | :--- |
| **`0`** | `PASS` | Batch conforms strictly to target contract; quarantine rate within threshold. |
| **`1`** | `FAIL` | Hard risk blocker detected, required fields unmapped, or quarantine threshold breached. |
| **`2`** | `ERROR` | Invalid arguments, malformed input syntax, or unreadable source file. |

---

## 🐳 Docker Deployment

Run Recon inside a lightweight, containerized Alpine environment:

```bash
# Run with Docker Compose
docker-compose up --build -d

# Verify server health
curl http://localhost:8000/api/health
```

---

## 🔒 Security & Privacy Posture

- **Local-First Execution:** Your data never leaves your infrastructure. Recon makes zero outbound calls, uses no external telemetry, and requires no API keys.
- **In-Process AST Sandbox:** Synthesized adapters execute in a Python namespace with dangerous builtins stripped (`__import__`, `open`, `eval`, `exec`, `os`, `sys`, `subprocess`, `socket`).
- **Network Isolation:** Remote `$ref` dereferencing in schema contracts is disabled by default to eliminate Server-Side Request Forgery (SSRF).

Detailed security architecture and threat models are documented in [`docs/SECURITY.md`](docs/SECURITY.md).

---

## 📚 Documentation Index

- [`docs/FDE_PDR_BRIEF.md`](docs/FDE_PDR_BRIEF.md) — Product Design & Delivery Review (PDR) executive mission brief for pilot stakeholders.
- [`docs/FDE_PLAYBOOK.md`](docs/FDE_PLAYBOOK.md) — Forward Deployed Engineer standard operating procedures, edge-case resolution, and production deployment patterns.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Core engine internals, schemas, and data pipelines.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — Contributor instructions, testing setup, and coding conventions.
- [`docs/SECURITY.md`](docs/SECURITY.md) — Detailed threat modeling, isolation boundaries, and audit policies.
- [`docs/PILOT_DEVELOPER_GUIDE.md`](docs/PILOT_DEVELOPER_GUIDE.md) — Guide for conducting real-world integration pilot evaluations.
- [`docs/WEBSITE_INTEGRATION.md`](docs/WEBSITE_INTEGRATION.md) — Drop-in web embedding and iframe specifications.
- [`docs/FAQ.md`](docs/FAQ.md) — Frequently asked technical and architectural questions.

---

## 📄 License

Recon is open-source software licensed under the **[MIT License](LICENSE)**.  
Copyright (c) 2026 Swami Gawai.
