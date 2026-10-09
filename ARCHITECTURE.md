# ARCHITECTURE.md — Recon Architecture & Design

## 1. Architectural Philosophy

Recon is engineered as a **modular, deterministic pipeline** where each stage produces an immutable, validated artifact represented as a typed Pydantic data model.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               RECON PIPELINE                                    │
│                                                                                 │
│   Raw CSV ──▶ [Ingestion] ──▶ RawDataset (Immutable)                           │
│                                   │                                             │
│                                   ▼                                             │
│                           [Deterministic Profiler]                              │
│                                   │                                             │
│                                   ▼                                             │
│                             SourceProfile                                       │
│                                   │                                             │
│   TargetContract ─────────────────┼────────┐                                    │
│                                   ▼        ▼                                    │
│                           [Mapping Engine] [Risk Engine]                        │
│                                   │        │                                    │
│                                   ▼        ▼                                    │
│                             MappingPlan   RiskAssessment                        │
│                                   │        │                                    │
│                                   ▼        │                                    │
│                       [Human Decision Boundary]                                │
│                                   │        │                                    │
│                                   ▼        ▼                                    │
│                          ApprovedMappingPlan ──▶ [Readiness Engine]             │
│                                   │                      ▲                      │
│                                   ▼                      │                      │
│                           [Adapter Generator]            │                      │
│                                   │                      │                      │
│                                   ▼                      │                      │
│                             GeneratedAdapter             │                      │
│                                   │                      │                      │
│                                   ▼                      │                      │
│                         [Adapter Validation & Tests] ────┘                      │
│                                   │                                             │
│                                   ▼                                             │
│                             ReadinessReport (JSON & Markdown)                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules & Responsibilities

| Module | Location | Responsibility | Core Artifacts / Models |
| :--- | :--- | :--- | :--- |
| **Ingestion** | `recon.ingestion` | Safe loading of raw files. Validates headers, encoding, malformed rows, file limits. Never alters raw inputs. | `RawDataset`, `IngestionResult` |
| **Profiling** | `recon.profiling` | Purely deterministic statistics: row/column counts, nulls, distinct counts, candidate type inference, ranges, duplicate rows, whitespace anomalies. | `SourceProfile`, `ColumnProfile` |
| **Contracts** | `recon.contracts` | Target schema parsing and validation. Declares field requirements, types, nullability, enums, regex patterns, ranges. | `TargetContract`, `TargetField` |
| **Mapping** | `recon.mapping` | Deterministic heuristics proposing source-to-target field alignments with explicit evidence attachments and uncertainty labels. | `MappingPlan`, `FieldMappingProposal` |
| **Risks** | `recon.risks` | Rule-based engine identifying contract incompatibilities, unmapped required fields, enum mismatches, lossy conversions. Stable rule IDs. | `RiskAssessment`, `RiskFinding` |
| **Adapters** | `recon.adapters` | Generates clean, explicit, self-contained Python transformation adapter functions from an approved mapping plan. | `GeneratedAdapter` |
| **Validation** | `recon.validation` | Executes generated adapter against test fixtures in an isolated process; validates output strictly against the target contract. | `ValidationResult`, `TestCaseResult` |
| **Reporting** | `recon.reporting` | Formats facts, inferences, risks, decisions, and test outcomes into human-readable Markdown and structured JSON readiness reports. | `ReadinessReport` |
| **CLI** | `recon.cli` | Ergonomic command-line interface orchestrating pipeline stages with clear error reporting and progress indicators. | CLI commands |

---

## 3. Data Models & State Flow

Every stage exchanges typed Pydantic models with strict validation:

### 1. `SourceProfile`
```python
class ColumnProfile(BaseModel):
    name: str
    inferred_type: InferredType # INTEGER, FLOAT, STRING, BOOLEAN, DATETIME, CATEGORICAL
    null_count: int
    null_percentage: float
    distinct_count: int
    min_value: Any | None = None
    max_value: Any | None = None
    sample_values: list[Any] = Field(default_factory=list)
    has_leading_trailing_whitespace: bool = False
    format_patterns: list[str] = Field(default_factory=list)

class SourceProfile(BaseModel):
    source_name: str
    fingerprint: str # SHA-256 hash of raw input
    total_rows: int
    total_columns: int
    duplicate_rows_count: int
    columns: dict[str, ColumnProfile]
    profiling_timestamp: datetime
```

### 2. `TargetContract`
```python
class TargetField(BaseModel):
    name: str
    target_type: ContractType # string, integer, number, boolean, datetime, date
    required: bool = True
    nullable: bool = False
    allowed_values: list[str] | None = None
    pattern: str | None = None
    description: str | None = None

class TargetContract(BaseModel):
    contract_name: str
    version: str
    fields: dict[str, TargetField]
```

### 3. `MappingPlan` & `FieldMappingProposal`
```python
class MappingStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"

class MappingType(str, Enum):
    DIRECT = "direct"
    TRANSFORMATION_REQUIRED = "transformation_required"
    MISSING_SOURCE = "missing_source"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"

class FieldMappingProposal(BaseModel):
    target_field: str
    source_field: str | None = None
    mapping_type: MappingType
    transformation_rule: str | None = None
    evidence: list[str] = Field(default_factory=list)
    status: MappingStatus = MappingStatus.PROPOSED
    human_notes: str | None = None
```

### 4. `RiskFinding`
```python
class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class RiskStatus(str, Enum):
    CONFIRMED = "confirmed"
    POTENTIAL = "potential"

class RiskFinding(BaseModel):
    rule_id: str # e.g. R001_MISSING_REQUIRED_FIELD
    severity: Severity
    status: RiskStatus
    affected_fields: list[str]
    evidence: str
    explanation: str
    suggested_action: str
```

### 5. `ReadinessReport`
```python
class ReadinessState(str, Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"

class ReadinessReport(BaseModel):
    source_fingerprint: str
    contract_name: str
    readiness_state: ReadinessState
    verified_facts_summary: dict[str, Any]
    critical_blockers: list[RiskFinding]
    high_risks: list[RiskFinding]
    medium_risks: list[RiskFinding]
    low_risks: list[RiskFinding]
    approved_mappings_count: int
    unresolved_mappings_count: int
    adapter_validation_passed: bool | None = None
    generated_at: datetime
```

---

## 4. Safety & Trust Boundaries

1. **Local-First Execution:** All profiling, heuristic matching, risk rules, and adapter generation run locally without sending data to third-party endpoints.
2. **Untrusted Data Isolation:** Raw file values, field names, and external schemas are treated as untrusted data. No CSV value is evaluated as code or passed to shell execution.
3. **Execution Sandbox:** Generated Python adapters are tested in an isolated process with strict execution timeouts (default: 5 seconds), resource caps, and no network socket permissions.
4. **Log Privacy:** Raw record rows are never dumped to default log outputs. Logs record operational progress, schema metadata, row counts, and error summaries.
