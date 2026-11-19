"""FastAPI routes connecting web frontend to Recon engine."""

import json
from pathlib import Path
import re
import tempfile
from typing import Any
import uuid

import os
from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.contracts.models import TargetContract
from recon.exceptions import AdapterError, ReconError
from recon.ingestion.loader import load_dataset
from recon.ingestion.models import RawDataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingPlan, MappingStatus, MappingType
from recon.mapping.proposer import propose_mappings
from recon.mapping.specification import (
    export_mapping_spec,
    load_mapping_spec,
    validate_and_apply_mapping_spec,
)
from recon.profiling.models import SourceProfile
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report, render_markdown_report
from recon.reporting.models import ReadinessReport
from recon.risks.evaluator import evaluate_risks
from recon.risks.models import RiskAssessment
from recon.logging import log_safe_event
from recon.storage.store import ReconStore, get_default_store
from recon.validation.executor import validate_adapter
from recon.validation.models import ValidationResult

router = APIRouter(prefix="/api")

# Persistent zero-config SQLite WAL store & in-memory cache
store: ReconStore = get_default_store()
SESSIONS: dict[str, dict[str, Any]] = {}
TEMP_DIRS: dict[str, tempfile.TemporaryDirectory] = {}
MAX_SESSIONS = 50


def _prune_old_sessions() -> None:
    """Evicts oldest sessions if session count exceeds MAX_SESSIONS to prevent memory/disk exhaustion."""
    while len(SESSIONS) > MAX_SESSIONS:
        oldest_id = next(iter(SESSIONS))
        SESSIONS.pop(oldest_id, None)
        old_temp = TEMP_DIRS.pop(oldest_id, None)
        if old_temp:
            try:
                old_temp.cleanup()
            except Exception:
                pass
    try:
        store.prune_sessions(keep_latest=MAX_SESSIONS)
    except Exception:
        pass


MAX_SOURCE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_CONTRACT_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB (allow large CSV target contracts)
ALLOWED_SOURCE_EXTENSIONS = {".csv", ".tsv", ".txt", ".json", ".jsonl", ".xlsx", ".xlsm"}
ALLOWED_CONTRACT_EXTENSIONS = {".json", ".csv", ".tsv", ".xlsx", ".xlsm"}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ApprovalRequest(BaseModel):
    session_id: str
    reviewer: str = "web_user"
    overrides: dict[str, str] = Field(default_factory=dict)


def _find_fixtures_dir() -> Path:
    """Finds fixtures directory relative to package."""
    root = Path(__file__).resolve().parents[3]
    fixtures = root / "tests" / "fixtures"
    if fixtures.is_dir():
        return fixtures
    return Path("tests/fixtures").resolve()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "engine": "Recon — The Integration Readiness Engine"}

class KeyVerificationRequest(BaseModel):
    access_key: str


def _check_access(request: Request) -> None:
    """Verifies that the client provided the valid configured RECON_ACCESS_KEY if one is set."""
    configured_key = os.environ.get("RECON_ACCESS_KEY", "").strip()
    if not configured_key:
        return
    provided_key = request.headers.get("X-Recon-Key", "").strip()
    if provided_key != configured_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Valid Recon Pilot Access Key required in 'X-Recon-Key' header.",
        )


@router.get("/auth-status")
def get_auth_status(request: Request) -> dict[str, Any]:
    """Returns whether this Recon instance requires an invitation key and if the client is authenticated."""
    configured_key = os.environ.get("RECON_ACCESS_KEY", "").strip()
    if not configured_key:
        return {"requires_auth": False, "authenticated": True}
    provided_key = request.headers.get("X-Recon-Key", "").strip()
    is_valid = (provided_key == configured_key)
    return {"requires_auth": True, "authenticated": is_valid}


@router.post("/verify-key")
def verify_access_key(body: KeyVerificationRequest) -> dict[str, Any]:
    """Validates an incoming pilot invitation access key."""
    configured_key = os.environ.get("RECON_ACCESS_KEY", "").strip()
    if not configured_key:
        return {"valid": True, "message": "No access key required for this instance."}
    if body.access_key.strip() == configured_key:
        return {"valid": True, "message": "Pilot Access Key accepted."}
    raise HTTPException(status_code=401, detail="Invalid Pilot Access Key. Check with project administrator.")





@router.get("/contracts/suggest")
def suggest_contracts(headers: str = "") -> list[dict[str, Any]]:
    """Given a comma-separated list of column headers from Port 1,
    scores all preloaded contracts by Jaccard token overlap and returns
    the top 3 ranked suggestions with confidence scores."""
    import re as _re

    def tokenise(s: str) -> set:
        return set(
            t for t in _re.sub(r"[^a-z0-9]+", " ", s.lower()).split()
            if len(t) > 1
        )

    source_tokens = tokenise(headers)
    if not source_tokens:
        return []

    fixtures = _find_fixtures_dir()
    suggestions: list[dict[str, Any]] = []

    for file in sorted(fixtures.glob("target_contract_*.json")):
        try:
            with open(file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            field_names = list(data.get("fields", {}).keys())
            contract_tokens: set = set()
            for name in field_names:
                contract_tokens |= tokenise(name)
            contract_tokens |= tokenise(data.get("contract_name", ""))

            if not contract_tokens:
                continue

            intersection = len(source_tokens & contract_tokens)
            union = len(source_tokens | contract_tokens)
            score = round(intersection / union, 4) if union else 0.0

            if score > 0:
                suggestions.append({
                    "id": file.stem,
                    "contract_name": data.get("contract_name", file.stem),
                    "version": data.get("version", "1.0.0"),
                    "description": data.get("description", ""),
                    "fields_count": len(field_names),
                    "score": score,
                    "match_pct": round(score * 100),
                    "content": json.dumps(data, indent=2),
                })
        except Exception:
            continue

    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return suggestions[:3]


def _should_infer_enum_values(col_name: str, target_type: str, distinct_vals: set[str], total_rows: int) -> bool:
    """Determines whether a column should be restricted to a fixed categorical enum (allowed_values).

    Prevents schema overfitting on open text, entity names, descriptions, and IDs while preserving
    clean enum discovery for true business taxonomies (e.g. status, branch, tier, mode).
    """
    if target_type != "string":
        return False

    n_distinct = len(distinct_vals)
    if n_distinct < 2 or n_distinct > 15:
        return False

    # Split camelCase, snake_case, kebab-case to isolate constituent words
    split_camel = re.sub(r"([a-z])([A-Z])", r"\1 \2", col_name)
    clean_name = split_camel.lower().replace("_", " ").replace("-", " ").strip()
    words = set(re.findall(r"[a-z0-9]+", clean_name))

    # 1. Blacklist: open-ended text, names, descriptions, and identifiers
    blacklist_words = {
        "name", "first", "last", "full", "student", "customer", "client", "user", "author", "vendor",
        "owner", "assignee", "person", "patient", "doctor", "employee", "agent", "member", "contact",
        "id", "identifier", "key", "uuid", "guid", "token", "hash", "ref", "reference", "sku", "serial",
        "barcode", "ssn", "item", "product",
        "desc", "description", "detail", "summary", "comment", "note", "notes", "remark", "text", "message", "memo", "info",
        "address", "street", "city", "location", "zip", "postal", "url", "link", "path", "email", "mail", "phone", "mobile",
        "title", "headline", "subject", "topic", "query",
        "amount", "price", "cost", "tax", "total", "balance", "rate", "fee", "salary", "qty", "quantity", "count", "score", "cgpa", "gpa",
        "year", "month", "day", "date", "time", "timestamp",
    }

    for w in words:
        if w in blacklist_words:
            return False
        if w.endswith("name") or (w.endswith("id") and len(w) > 2):
            return False

    # 2. Whitelist: categorical keywords (high confidence business taxonomies)
    whitelist_words = {
        "status", "state", "stage", "category", "type", "kind", "gender", "sex", "preference", "flag", "mode", "tier", "level",
        "frequency", "method", "priority", "severity", "segment", "group", "size", "season", "branch", "hostel", "department", "role",
    }
    if words.intersection(whitelist_words):
        return True

    # 3. Fallback for unclassified columns: strict cardinality and ratio
    if n_distinct <= 6 and total_rows >= 20 and (n_distinct / total_rows) <= 0.05:
        if all(len(v) <= 30 and not any(c in v for c in ["@", "/", "\\"]) and not re.search(r"\d{3,}", v) for v in distinct_vals):
            return True

    return False


@router.post("/contracts/infer-from-source")
async def infer_contract_from_source(
    request: Request,
    source_file: UploadFile | None = File(None),
    sample_dataset_id: str | None = Form(None),
) -> dict[str, Any]:
    """Generates an auto-inferred target contract from an uploaded or sample source dataset."""
    _check_access(request)
    fixtures = _find_fixtures_dir()
    temp_dir = tempfile.TemporaryDirectory()

    try:
        if source_file and source_file.filename:
            safe_source_name = Path(source_file.filename).name.strip()
            if not safe_source_name or safe_source_name in (".", ".."):
                raise HTTPException(status_code=400, detail="Invalid source file name.")
            suffix = Path(safe_source_name).suffix.lower()
            if suffix not in ALLOWED_SOURCE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported format '{suffix}'. Supported: {', '.join(sorted(ALLOWED_SOURCE_EXTENSIONS))}",
                )
            source_path = Path(temp_dir.name) / safe_source_name
            file_bytes = await source_file.read(MAX_SOURCE_SIZE_BYTES + 1)
            if len(file_bytes) > MAX_SOURCE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {MAX_SOURCE_SIZE_BYTES // (1024 * 1024)} MB.",
                )
            with open(source_path, "wb") as f:
                f.write(file_bytes)
        elif sample_dataset_id:
            if not IDENTIFIER_PATTERN.match(sample_dataset_id):
                raise HTTPException(status_code=400, detail="Invalid sample_dataset_id format.")
            matching = list(fixtures.glob(f"{sample_dataset_id}.*"))
            if not matching:
                raise HTTPException(status_code=400, detail=f"Sample dataset '{sample_dataset_id}' not found.")
            source_path = matching[0]
        else:
            raise HTTPException(status_code=400, detail="Must provide either 'source_file' or 'sample_dataset_id'.")

        dataset = load_dataset(source_path)
        if not dataset.headers:
            raise HTTPException(status_code=400, detail="Source dataset contains no valid header columns.")

        profile = profile_dataset(dataset)
        contract_name = f"{Path(dataset.file_name).stem}_inferred_contract"
        fields: dict[str, Any] = {}

        for col in dataset.headers:
            col_prof = profile.columns.get(col)
            if col_prof:
                target_type = col_prof.inferred_type.value
                required = (col_prof.null_count == 0)
                nullable = (col_prof.null_count > 0)
                allowed = None
                # Discover distinct values from dataset rows
                col_values = {str(r.get(col, "")).strip() for r in dataset.rows if r.get(col) is not None and str(r.get(col, "")).strip()}
                if _should_infer_enum_values(col, target_type, col_values, profile.total_rows):
                    allowed = sorted(list(col_values))
                
                f_dict: dict[str, Any] = {
                    "name": col,
                    "target_type": target_type,
                    "required": required,
                    "nullable": nullable,
                    "description": f"Auto-inferred target field for '{col}' ({target_type})",
                }
                if allowed:
                    f_dict["allowed_values"] = allowed
                fields[col] = f_dict
            else:
                fields[col] = {
                    "name": col,
                    "target_type": "string",
                    "required": True,
                    "nullable": False,
                    "description": f"Target field '{col}'",
                }

        contract_payload = {
            "contract_name": contract_name,
            "version": "1.0.0",
            "description": f"Auto-inferred target contract generated from '{dataset.file_name}' ({len(fields)} fields, {profile.total_rows} sampled rows)",
            "fields": fields,
        }

        return {
            "success": True,
            "contract_name": contract_name,
            "fields_count": len(fields),
            "contract_json": json.dumps(contract_payload, indent=2),
            "contract_dict": contract_payload,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to infer target contract: {exc}") from exc
    finally:
        temp_dir.cleanup()

@router.get("/sample-contracts")
def list_sample_contracts() -> list[dict[str, Any]]:
    """Returns list of pre-configured sample target contracts for quick developer testing."""
    fixtures = _find_fixtures_dir()
    contracts = []
    for file in fixtures.glob("target_contract_*.json"):
        try:
            with open(file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            contracts.append({
                "id": file.stem,
                "file_name": file.name,
                "contract_name": data.get("contract_name", file.stem),
                "version": data.get("version", "1.0.0"),
                "description": data.get("description", ""),
                "fields_count": len(data.get("fields", {})),
                "content": json.dumps(data, indent=2),
            })
        except Exception:
            continue
    return contracts


@router.get("/sample-datasets")
def list_sample_datasets() -> list[dict[str, Any]]:
    """Returns list of pre-configured sample datasets for quick testing."""
    fixtures = _find_fixtures_dir()
    datasets = []
    for ext in ("*.csv", "*.json"):
        for file in fixtures.glob(ext):
            if file.name.startswith("target_contract"):
                continue
            datasets.append({
                "id": file.stem,
                "file_name": file.name,
                "format": file.suffix.lstrip("."),
                "path": str(file),
            })
    return datasets


@router.post("/assess")
async def assess_integration(
    request: Request,
    source_file: UploadFile | None = File(None),
    sample_dataset_id: str | None = Form(None),
    contract_file: UploadFile | None = File(None),
    contract_text: str | None = Form(None),
    sample_contract_id: str | None = Form(None),
    schema_name: str | None = Form(None),
    mapping_spec_file: UploadFile | None = File(None),
) -> dict[str, Any]:
    _check_access(request)
    """Uploads source data and contract; profiles, proposes mappings, and assesses integration risks."""
    session_id = str(uuid.uuid4())
    temp_dir = tempfile.TemporaryDirectory()
    TEMP_DIRS[session_id] = temp_dir
    dir_path = Path(temp_dir.name)

    fixtures = _find_fixtures_dir()

    try:
        # 1. Resolve Source Dataset
        if source_file and source_file.filename:
            safe_source_name = Path(source_file.filename).name.strip()
            if not safe_source_name or safe_source_name in (".", ".."):
                raise HTTPException(status_code=400, detail="Invalid source file name.")
            suffix = Path(safe_source_name).suffix.lower()
            if suffix not in ALLOWED_SOURCE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format '{suffix}'. Supported formats: {', '.join(sorted(ALLOWED_SOURCE_EXTENSIONS))}",
                )
            source_path = dir_path / safe_source_name
            content = await source_file.read(MAX_SOURCE_SIZE_BYTES + 1)
            if len(content) > MAX_SOURCE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Source file exceeds maximum allowed size of {MAX_SOURCE_SIZE_BYTES // (1024 * 1024)} MB.",
                )
            with open(source_path, "wb") as f:
                f.write(content)
        elif sample_dataset_id:
            if not IDENTIFIER_PATTERN.match(sample_dataset_id):
                raise HTTPException(status_code=400, detail="Invalid sample_dataset_id format.")
            matching = list(fixtures.glob(f"{sample_dataset_id}.*"))
            if not matching:
                raise HTTPException(status_code=400, detail=f"Sample dataset '{sample_dataset_id}' not found.")
            source_path = matching[0]
        else:
            raise HTTPException(status_code=400, detail="Must provide either 'source_file' or 'sample_dataset_id'.")

        # 2. Resolve Target Contract
        if contract_file and contract_file.filename:
            safe_contract_name = Path(contract_file.filename).name.strip()
            if not safe_contract_name or safe_contract_name in (".", ".."):
                raise HTTPException(status_code=400, detail="Invalid contract file name.")
            suffix = Path(safe_contract_name).suffix.lower()
            if suffix not in ALLOWED_CONTRACT_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported contract format '{suffix}'. Supported formats: {', '.join(sorted(ALLOWED_CONTRACT_EXTENSIONS))}",
                )
            contract_path = dir_path / safe_contract_name
            c_bytes = await contract_file.read(MAX_CONTRACT_SIZE_BYTES + 1)
            if len(c_bytes) > MAX_CONTRACT_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Contract file exceeds maximum allowed size of {MAX_CONTRACT_SIZE_BYTES // (1024 * 1024)} MB.",
                )
            if c_bytes.startswith(b"\xef\xbb\xbf") and suffix == ".json":
                c_bytes = c_bytes[3:]
            with open(contract_path, "wb") as f:
                f.write(c_bytes)
        elif contract_text and contract_text.strip():
            clean_text = contract_text.strip().lstrip("\ufeff")
            if clean_text.startswith("{") or clean_text.startswith("["):
                contract_path = dir_path / "custom_contract.json"
                try:
                    json_obj = json.loads(clean_text)
                    with open(contract_path, "w", encoding="utf-8") as f:
                        json.dump(json_obj, f, indent=2)
                except json.JSONDecodeError as exc:
                    raise HTTPException(status_code=400, detail=f"Contract text is invalid JSON: {exc}")
            else:
                contract_path = dir_path / "custom_contract.csv"
                with open(contract_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)
        elif sample_contract_id:
            if not IDENTIFIER_PATTERN.match(sample_contract_id):
                raise HTTPException(status_code=400, detail="Invalid sample_contract_id format.")
            target_file = fixtures / f"{sample_contract_id}.json"
            if not target_file.is_file():
                # Try prefix
                matching = list(fixtures.glob(f"*{sample_contract_id}*.json"))
                if not matching:
                    raise HTTPException(status_code=400, detail=f"Sample contract '{sample_contract_id}' not found.")
                target_file = matching[0]
            contract_path = target_file
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide 'contract_file', 'contract_text', or 'sample_contract_id'."
            )

        # 3. Execute Engine Pipeline (Ingestion -> Profiling -> Mapping -> Risks)
        try:
            dataset: RawDataset = load_dataset(source_path)
            profile: SourceProfile = profile_dataset(dataset)
            contract: TargetContract = load_target_contract(contract_path, schema_name=schema_name)
            plan: MappingPlan = propose_mappings(profile, contract)

            # Apply mapping specification if provided
            if mapping_spec_file and mapping_spec_file.filename:
                spec_bytes = await mapping_spec_file.read(MAX_CONTRACT_SIZE_BYTES + 1)
                if len(spec_bytes) > MAX_CONTRACT_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Mapping specification exceeds maximum size of {MAX_CONTRACT_SIZE_BYTES // (1024 * 1024)} MB.",
                    )
                spec_dict = json.loads(spec_bytes.decode("utf-8-sig").lstrip("\ufeff"))
                spec = load_mapping_spec(spec_dict)
                plan, _ = validate_and_apply_mapping_spec(spec, contract, profile, plan)

            risks: RiskAssessment = evaluate_risks(profile, contract, plan)
        except ReconError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Internal profiling error: {exc}")

    except Exception:
        # Clean up temporary directory on failure to avoid leaking disk resources
        try:
            temp_dir.cleanup()
        except Exception:
            pass
        TEMP_DIRS.pop(session_id, None)
        raise

    # Store in session and evict oldest if limit exceeded
    SESSIONS[session_id] = {
        "dataset": dataset,
        "profile": profile,
        "contract": contract,
        "plan": plan,
        "risks": risks,
        "source_path": source_path,
        "contract_path": contract_path,
    }
    _prune_old_sessions()

    # 4. Format Mapping Proposals with Genuine Engine Evidence (No Fake Confidence Scores)
    proposals_summary: list[dict[str, Any]] = []
    unresolved_fields: list[str] = []
    unresolved_required_fields: list[str] = []

    for target_name, target_field in contract.fields.items():
        prop = plan.proposals.get(target_name)
        is_unresolved = (
            prop is None
            or prop.status == MappingStatus.UNRESOLVED
            or not prop.source_field
        )

        if is_unresolved:
            unresolved_fields.append(target_name)
            if target_field.required:
                unresolved_required_fields.append(target_name)

        proposals_summary.append({
            "target_field": target_name,
            "target_type": target_field.target_type.value,
            "required": target_field.required,
            "nullable": target_field.nullable,
            "description": target_field.description,
            "allowed_values": target_field.allowed_values,
            "pattern": target_field.pattern,
            "proposed_source_field": prop.source_field if prop else None,
            "mapping_type": prop.mapping_type.value if prop else MappingType.MISSING_SOURCE.value,
            "status": prop.status.value if prop else MappingStatus.UNRESOLVED.value,
            "evidence": prop.evidence if prop else ["No mapping proposal generated."],
            "is_unresolved": is_unresolved,
        })

    # Format Risks
    risk_summary = [
        {
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "severity": f.severity.value,
            "status": f.status.value,
            "affected_fields": f.affected_fields,
            "evidence": f.evidence,
            "explanation": f.explanation,
            "suggested_action": f.suggested_action,
        }
        for f in risks.findings
    ]

    assessment_response = {
        "session_id": session_id,
        "source": {
            "file_name": dataset.file_name,
            "format": Path(dataset.file_name).suffix.lstrip(".") or "csv",
            "total_rows": profile.total_rows,
            "total_columns": profile.total_columns,
            "duplicate_rows_count": profile.duplicate_rows_count,
            "fingerprint": profile.fingerprint,
            "columns": list(profile.columns.keys()),
            "columns_profile": {
                name: {
                    "inferred_type": col.inferred_type.value,
                    "null_count": col.null_count,
                    "null_percentage": col.null_percentage,
                    "distinct_count": col.distinct_count,
                    "sample_values": col.sample_values[:5],
                }
                for name, col in profile.columns.items()
            },
        },
        "contract": {
            "contract_name": contract.contract_name,
            "version": contract.version,
            "description": contract.description,
            "total_fields": len(contract.fields),
        },
        "proposals": proposals_summary,
        "unresolved_fields": unresolved_fields,
        "unresolved_required_fields": unresolved_required_fields,
        "has_unresolved_required": len(unresolved_required_fields) > 0,
        "risks": risk_summary,
        "is_blocked": risks.is_blocked or len(unresolved_required_fields) > 0,
        "critical_risks_count": len(risks.critical_findings),
        "high_risks_count": len(risks.high_findings),
    }

    # Persist session to SQLite WAL store
    try:
        store.save_assessment(
            session_id=session_id,
            assessment_data=assessment_response,
            source_path=source_path,
            contract_path=contract_path,
        )
    except Exception as exc:
        log_safe_event("session_storage_warning", {"error": str(exc), "session_id": session_id})

    SESSIONS[session_id]["assessment_response"] = assessment_response
    return assessment_response


def _aggregate_quarantine_errors(quarantined_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups quarantine errors by rule/field root causes, counting affected records and percentages."""
    if not quarantined_records:
        return []

    total_quarantined = len(quarantined_records)
    groups: dict[str, dict[str, Any]] = {}

    for rec in quarantined_records:
        rec_idx = rec.get("record_index") or rec.get("row_index", 0)
        errors = rec.get("errors") or rec.get("failure_reasons") or ["Schema violation"]
        for err in errors:
            field = "General"
            match = re.search(r"for '([^']+)'|field '([^']+)'|'([^']+)' is missing|'([^']+)' does not match", err, re.IGNORECASE)
            if match:
                for g in match.groups():
                    if g:
                        field = g
                        break
            else:
                m2 = re.search(r"'([^']+)'", err)
                if m2:
                    field = m2.group(1)

            err_lower = err.lower()
            if "not in allowed values" in err_lower or "enum" in err_lower:
                category = "Allowed Values"
            elif "required" in err_lower or "missing" in err_lower or "cannot be empty" in err_lower:
                category = "Missing Required"
            elif "datetime" in err_lower or "iso-8601" in err_lower or "date" in err_lower:
                category = "Date / Time"
            elif "does not match pattern" in err_lower or "pattern" in err_lower:
                category = "Pattern Mismatch"
            elif "type" in err_lower or "cannot convert" in err_lower:
                category = "Type Mismatch"
            else:
                category = "Contract Violation"

            group_key = f"{field}::{category}"
            if group_key not in groups:
                groups[group_key] = {
                    "field": field,
                    "category": category,
                    "sample_error": err,
                    "count": 0,
                    "row_indices": [],
                }
            groups[group_key]["count"] += 1
            if len(groups[group_key]["row_indices"]) < 50:
                groups[group_key]["row_indices"].append(rec_idx)

    result = []
    for g in groups.values():
        cnt = g["count"]
        pct = round((cnt / total_quarantined) * 100.0, 1) if total_quarantined > 0 else 0.0
        result.append({
            "field": g["field"],
            "category": g["category"],
            "sample_error": g["sample_error"],
            "count": cnt,
            "percentage": pct,
            "row_indices": g["row_indices"][:10],
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return result


@router.post("/approve-and-generate")
def approve_and_generate(http_req: Request, request: ApprovalRequest) -> dict[str, Any]:
    _check_access(http_req)
    """Applies human approval & overrides, generates reviewable adapter, runs sandbox tests, and produces readiness report."""
    session = SESSIONS.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session expired or not found. Please re-assess.")

    dataset: RawDataset = session["dataset"]
    profile: SourceProfile = session["profile"]
    contract: TargetContract = session["contract"]
    plan: MappingPlan = session["plan"]
    risks: RiskAssessment = session["risks"]

    # 1. Prepare Overrides for Human Approval
    applied_overrides: dict[str, dict[str, Any]] = {}
    for target_name, selected_source in request.overrides.items():
        if selected_source and selected_source.strip():
            src_clean = selected_source.strip()
            # Validate source column exists
            if src_clean not in profile.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selected source column '{src_clean}' for target '{target_name}' does not exist in dataset headers."
                )
            applied_overrides[target_name] = {
                "source_field": src_clean,
                "mapping_type": MappingType.DIRECT,
                "status": MappingStatus.APPROVED,
                "evidence": [f"Manually mapped to source column '{src_clean}' by {request.reviewer}"],
            }

    # 2. Approve Mapping Plan (Enforces required field completeness)
    try:
        approved_plan = approve_mapping_plan(
            plan=plan,
            reviewer=request.reviewer,
            overrides=applied_overrides,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Mapping approval error: {exc}")

    # 3. Generate Adapter (Reviewable Python code)
    try:
        adapter = generate_adapter(approved_plan, contract)
    except AdapterError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate adapter: {exc.message}. Action: {exc.actionable_suggestion}"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Adapter generation error: {exc}")

    # 4. Execute Sandbox Validation
    try:
        validation: ValidationResult = validate_adapter(adapter, contract, dataset.rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Adapter sandbox validation error: {exc}")

    # 5. Re-evaluate risks on approved plan and build Readiness Report
    try:
        active_plan = MappingPlan(
            contract_name=approved_plan.contract_name,
            source_name=approved_plan.source_name,
            source_fingerprint=approved_plan.source_fingerprint,
            proposals=dict(approved_plan.approved_mappings),
        )
        active_risks = evaluate_risks(profile, contract, active_plan)

        report: ReadinessReport = build_readiness_report(
            profile=profile,
            contract=contract,
            mapping_plan=active_plan,
            risk_assessment=active_risks,
            approved_plan=approved_plan,
            validation_result=validation,
        )
        report_md = render_markdown_report(report)
        report_json = report.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation error: {exc}")

    # Store artifacts in session
    session["approved_plan"] = approved_plan
    session["adapter"] = adapter
    session["validation"] = validation
    session["report"] = report
    session["report_md"] = report_md
    session["report_json"] = report_json

    results_response = {
        "session_id": request.session_id,
        "readiness_state": report.readiness_state.value,
        "readiness_rationale": report.readiness_rationale,
        "blocking_reasons": report.blocking_reasons,
        "review_reasons": report.review_reasons,
        "adapter": {
            "adapter_name": adapter.adapter_name,
            "contract_name": adapter.contract_name,
            "contract_version": adapter.contract_version,
            "python_code": adapter.python_code,
        },
        "validation": {
            "total_input_records": validation.total_input_records,
            "valid_records_count": validation.valid_records_count,
            "quarantined_records_count": validation.quarantined_records_count,
            "contract_pass_rate": validation.contract_pass_rate,
            "is_contract_valid": validation.is_contract_valid,
            "all_tests_passed": validation.all_tests_passed,
            "test_case_results": [
                {
                    "test_name": tc.test_name,
                    "passed": tc.passed,
                    "expected_behavior": tc.expected_behavior,
                    "actual_behavior": tc.actual_behavior,
                    "error_message": tc.error_message,
                }
                for tc in validation.test_case_results
            ],
            "sample_valid_output": validation.sample_valid_output[:5],
            "sample_quarantined_records": [
                {
                    "row_index": qr.get("record_index", 0),
                    "record_index": qr.get("record_index", 0),
                    "failure_reasons": qr.get("errors", []),
                    "errors": qr.get("errors", []),
                    "raw_record": qr.get("raw_record", {}),
                }
                for qr in (validation.all_quarantined_records[:100] if getattr(validation, "all_quarantined_records", None) else validation.sample_quarantined_records)
            ],
            "quarantine_error_groups": _aggregate_quarantine_errors(
                validation.all_quarantined_records if getattr(validation, "all_quarantined_records", None) else validation.sample_quarantined_records
            ),
        },
        "report_markdown": report_md,
    }

    # Persist compilation results & quarantine index in SQLite WAL store
    try:
        quar_recs = validation.all_quarantined_records if getattr(validation, "all_quarantined_records", None) else validation.sample_quarantined_records
        store.save_results(
            session_id=request.session_id,
            results_data=results_response,
            adapter_code=adapter.python_code,
            report_md=report_md,
            report_json=report_json,
            mapping_spec_json=session.get("mapping_spec_json", ""),
            quarantine_records=quar_recs,
        )
    except Exception as exc:
        log_safe_event("session_results_storage_warning", {"error": str(exc), "session_id": request.session_id})

    session["results_response"] = results_response
    return results_response


@router.get("/quarantine/records/{session_id}")
def get_quarantine_records(
    session_id: str,
    search: str | None = None,
    field: str | None = None,
    category: str | None = None,
    sort_by: str = "row_index",
    sort_dir: str = "asc",
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Provides interactive search, filtering, and sorting over quarantined records."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session or "validation" not in session:
        raise HTTPException(status_code=404, detail="Validation results not found. Run approval and validation first.")

    val = session["validation"]
    records = val.all_quarantined_records if getattr(val, "all_quarantined_records", None) else val.sample_quarantined_records

    filtered = []
    for idx, r in enumerate(records):
        rec_index = r.get("record_index", r.get("row_index", idx + 1))
        errs = r.get("errors", r.get("failure_reasons", []))
        raw = r.get("raw_record", {})
        err_str = " ".join(errs).lower()

        # Filter by field
        if field and field.strip() and field.lower() != "all":
            f_clean = field.strip().lower()
            if f"'{f_clean}'" not in err_str and f_clean not in err_str:
                continue

        # Filter by category
        if category and category.strip() and category.lower() != "all":
            cat_clean = category.strip().lower()
            if cat_clean == "allowed values" and not ("not in allowed" in err_str or "enum" in err_str):
                continue
            elif cat_clean == "missing required" and not ("required" in err_str or "missing" in err_str):
                continue
            elif cat_clean == "date / time" and not ("datetime" in err_str or "date" in err_str):
                continue
            elif cat_clean == "pattern mismatch" and not ("pattern" in err_str):
                continue

        # Search across row index, errors, and values
        if search and search.strip():
            s_clean = search.strip().lower()
            row_token = f"row #{rec_index} {rec_index}".lower()
            vals_token = " ".join(str(v) for v in raw.values()).lower()
            if s_clean not in err_str and s_clean not in row_token and s_clean not in vals_token:
                continue

        filtered.append({
            "row_index": rec_index,
            "record_index": rec_index,
            "failure_reasons": errs,
            "errors": errs,
            "raw_record": raw,
        })

    # Sorting
    reverse = (sort_dir.lower() == "desc")
    if sort_by == "row_index":
        filtered.sort(key=lambda x: int(x["row_index"]), reverse=reverse)
    elif sort_by in ("rule", "field", "error"):
        filtered.sort(key=lambda x: (x["errors"][0] if x["errors"] else ""), reverse=reverse)

    total_matching = len(filtered)
    paged = filtered[offset : offset + limit]

    return {
        "session_id": session_id,
        "total_quarantined": len(records),
        "total_matching": total_matching,
        "offset": offset,
        "limit": limit,
        "records": paged,
        "error_groups": _aggregate_quarantine_errors(records),
    }


@router.get("/download/report/{session_id}")
def download_report(session_id: str, format: str = "md") -> Response:
    """Downloads the generated Readiness Report in Markdown or JSON format."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    report_md = session.get("report_md") if session else None
    report_json = session.get("report_json") if session else None

    # Fall back to persistent SQLite store
    if not report_md or not report_json:
        stored = store.get_session(session_id)
        if stored:
            report_md = report_md or stored.get("report_md")
            report_json = report_json or stored.get("report_json")

    if not report_md:
        raise HTTPException(status_code=404, detail="Readiness report not found. Run approval and validation first.")

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:8]
    if format == "json":
        content = json.dumps(report_json, indent=2) if isinstance(report_json, dict) else str(report_json)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="readiness_report_{safe_id}.json"'}
        )

    return PlainTextResponse(
        content=report_md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="readiness_report_{safe_id}.md"'}
    )


@router.get("/download/adapter/{session_id}")
def download_adapter(session_id: str) -> Response:
    """Downloads the reviewable generated Python adapter code."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    adapter = session.get("adapter") if session else None
    python_code = adapter.python_code if adapter else None
    adapter_name = adapter.adapter_name if adapter else None

    # Fall back to persistent SQLite store
    if not python_code:
        stored = store.get_session(session_id)
        if stored and stored.get("adapter_code"):
            python_code = stored["adapter_code"]
            adapter_name = f"{stored.get('contract_name', 'integration')}_adapter"

    if not python_code:
        raise HTTPException(status_code=404, detail="Adapter code not generated yet.")

    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", adapter_name or "adapter")
    return PlainTextResponse(
        content=python_code,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.py"'}
    )


@router.get("/download/valid-records/{session_id}")
def download_valid_records(session_id: str) -> Response:
    """Downloads valid transformed records in JSONL format."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session or "validation" not in session:
        raise HTTPException(status_code=404, detail="Validation results not found. Run approval and validation first.")

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:8]
    val = session["validation"]
    records = val.all_valid_records if getattr(val, "all_valid_records", None) else val.sample_valid_output
    lines = [json.dumps(rec, default=str) for rec in records]
    content = "\n".join(lines)
    return PlainTextResponse(
        content=content,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": f'attachment; filename="valid_records_{safe_id}.jsonl"'}
    )


@router.get("/download/quarantine-records/{session_id}")
def download_quarantine_records(session_id: str) -> Response:
    """Downloads quarantined records with diagnostics in JSONL format."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session or "validation" not in session:
        raise HTTPException(status_code=404, detail="Validation results not found. Run approval and validation first.")

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:8]
    val = session["validation"]
    records = val.all_quarantined_records if getattr(val, "all_quarantined_records", None) else val.sample_quarantined_records
    lines = [json.dumps(rec, default=str) for rec in records]
    content = "\n".join(lines)
    return PlainTextResponse(
        content=content,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": f'attachment; filename="quarantine_records_{safe_id}.jsonl"'}
    )


@router.get("/download/mapping-spec/{session_id}")
def download_mapping_spec(session_id: str) -> Response:
    """Downloads versioned mapping specification JSON generated from current session mapping state."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session or "plan" not in session or "contract" not in session or "profile" not in session:
        raise HTTPException(status_code=404, detail="Mapping plan not found for session.")

    plan_to_export = session.get("approved_plan") or session["plan"]
    spec = export_mapping_spec(
        contract=session["contract"],
        profile=session["profile"],
        plan=plan_to_export,
        reviewer=session.get("reviewer", "web_user"),
    )

    return Response(
        content=spec.to_json(),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="recon_mapping_spec.json"'},
    )


@router.post("/upload-mapping-spec")
async def upload_mapping_spec(
    session_id: str = Form(...),
    spec_file: UploadFile | None = File(None),
    spec_json: str | None = Form(None),
) -> dict[str, Any]:
    """Uploads, validates, and applies a reusable mapping specification to an active session."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    if spec_file and spec_file.filename:
        content_bytes = await spec_file.read(MAX_CONTRACT_SIZE_BYTES + 1)
        if len(content_bytes) > MAX_CONTRACT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Mapping specification file exceeds size limit.")
        try:
            content_str = content_bytes.decode("utf-8-sig").lstrip("\ufeff")
            spec_dict = json.loads(content_str)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON/UTF-8 mapping specification: {exc}")
    elif spec_json and spec_json.strip():
        try:
            spec_dict = json.loads(spec_json.strip().lstrip("\ufeff"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in mapping specification: {exc}")
    else:
        raise HTTPException(status_code=400, detail="Must provide either 'spec_file' or 'spec_json'.")

    try:
        spec = load_mapping_spec(spec_dict)
        updated_plan, val_result = validate_and_apply_mapping_spec(
            spec=spec,
            contract=session["contract"],
            profile=session["profile"],
            base_plan=session["plan"],
        )
        updated_risks = evaluate_risks(session["profile"], session["contract"], updated_plan)
    except ReconError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error applying mapping specification: {exc}")

    session["plan"] = updated_plan
    session["risks"] = updated_risks

    proposals_summary: list[dict[str, Any]] = []
    unresolved_fields: list[str] = []
    unresolved_required_fields: list[str] = []

    for target_name, target_field in session["contract"].fields.items():
        prop = updated_plan.proposals.get(target_name)
        is_unresolved = (
            prop is None
            or prop.status == MappingStatus.UNRESOLVED
            or not prop.source_field
        )
        if is_unresolved:
            unresolved_fields.append(target_name)
            if target_field.required:
                unresolved_required_fields.append(target_name)

        proposals_summary.append({
            "target_field": target_name,
            "target_type": target_field.target_type.value,
            "required": target_field.required,
            "nullable": target_field.nullable,
            "allowed_values": target_field.allowed_values,
            "pattern": target_field.pattern,
            "description": target_field.description,
            "source_field": prop.source_field if prop else None,
            "source_inferred_type": prop.source_inferred_type.value if prop and prop.source_inferred_type else None,
            "mapping_type": prop.mapping_type.value if prop else MappingType.MISSING_SOURCE.value,
            "status": prop.status.value if prop else MappingStatus.UNRESOLVED.value,
            "transformation_rule": prop.transformation_rule if prop else None,
            "evidence": prop.evidence if prop else [],
            "alternative_candidates": prop.alternative_candidates if prop else [],
            "human_notes": prop.human_notes if prop else None,
        })

    return {
        "session_id": session_id,
        "validation_result": val_result.model_dump(),
        "proposals_summary": proposals_summary,
        "unresolved_fields": unresolved_fields,
        "unresolved_required_fields": unresolved_required_fields,
        "risks_summary": {
            "findings_count": len(updated_risks.findings),
            "critical_count": len(updated_risks.critical_findings),
            "high_count": len(updated_risks.high_findings),
            "is_blocked": updated_risks.is_blocked,
        },
        "can_proceed_to_adapter": len(unresolved_required_fields) == 0,
    }


@router.get("/sessions/recent")
def list_recent_sessions(limit: int = 20) -> dict[str, Any]:
    """Returns list of recent inspection sessions saved in SQLite WAL store."""
    sessions = store.list_recent_sessions(limit=limit)
    return {"success": True, "sessions": sessions, "total": len(sessions)}


@router.get("/session/{session_id}/restore")
def restore_session(session_id: str) -> dict[str, Any]:
    """Restores full session state (assessment + results) across server reboots or tab switches."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    stored = store.get_session(session_id)
    if not stored or not stored.get("assessment"):
        raise HTTPException(status_code=404, detail="Session not found in persistent store.")

    # Cache in memory
    SESSIONS[session_id] = {
        "assessment_response": stored["assessment"],
        "results_response": stored.get("results"),
        "report_md": stored.get("report_md"),
        "report_json": stored.get("report_json"),
        "adapter_code": stored.get("adapter_code"),
        "source_path": stored.get("source_path"),
        "contract_path": stored.get("contract_path"),
    }

    return {
        "success": True,
        "session_id": session_id,
        "assessment": stored["assessment"],
        "results": stored.get("results"),
        "readiness_state": stored.get("readiness_state"),
        "pass_rate": stored.get("pass_rate"),
        "adapter_code": stored.get("adapter_code"),
        "created_at": stored.get("created_at"),
        "updated_at": stored.get("updated_at"),
    }


@router.get("/storage/status")
def get_storage_status() -> dict[str, Any]:
    """Returns SQLite WAL storage health, persistence status, and session counts."""
    return {"success": True, "storage": store.get_storage_stats()}


@router.delete("/session/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    """Explicitly terminates a session and cleans up its temporary directory, memory, and database records."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.pop(session_id, None)
    temp_dir = TEMP_DIRS.pop(session_id, None)
    store_deleted = store.delete_session(session_id)
    if temp_dir:
        try:
            temp_dir.cleanup()
        except Exception:
            pass
    if not session and not temp_dir and not store_deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "cleaned", "session_id": session_id}
