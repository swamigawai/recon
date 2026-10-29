"""FastAPI routes connecting web frontend to Recon engine."""

import json
from pathlib import Path
import re
import tempfile
from typing import Any
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
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
from recon.validation.executor import validate_adapter
from recon.validation.models import ValidationResult

router = APIRouter(prefix="/api")

# Session storage for in-flight evaluations
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


MAX_SOURCE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_CONTRACT_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB (allow large CSV target contracts)
ALLOWED_SOURCE_EXTENSIONS = {".csv", ".tsv", ".txt", ".json", ".jsonl"}
ALLOWED_CONTRACT_EXTENSIONS = {".json", ".csv", ".tsv"}
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
    source_file: UploadFile | None = File(None),
    sample_dataset_id: str | None = Form(None),
    contract_file: UploadFile | None = File(None),
    contract_text: str | None = Form(None),
    sample_contract_id: str | None = Form(None),
    schema_name: str | None = Form(None),
    mapping_spec_file: UploadFile | None = File(None),
) -> dict[str, Any]:
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

    return {
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


@router.post("/approve-and-generate")
def approve_and_generate(request: ApprovalRequest) -> dict[str, Any]:
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

    return {
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
                for qr in validation.sample_quarantined_records
            ],
        },
        "report_markdown": report_md,
    }


@router.get("/download/report/{session_id}")
def download_report(session_id: str, format: str = "md") -> Response:
    """Downloads the generated Readiness Report in Markdown or JSON format."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session or "report_md" not in session:
        raise HTTPException(status_code=404, detail="Readiness report not found. Run approval and validation first.")

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:8]
    if format == "json":
        content = json.dumps(session["report_json"], indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="readiness_report_{safe_id}.json"'}
        )

    return PlainTextResponse(
        content=session["report_md"],
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="readiness_report_{safe_id}.md"'}
    )


@router.get("/download/adapter/{session_id}")
def download_adapter(session_id: str) -> Response:
    """Downloads the reviewable generated Python adapter code."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.get(session_id)
    if not session or "adapter" not in session:
        raise HTTPException(status_code=404, detail="Adapter code not generated yet.")

    adapter = session["adapter"]
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", adapter.adapter_name)
    return PlainTextResponse(
        content=adapter.python_code,
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


@router.delete("/session/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    """Explicitly terminates a session and cleans up its temporary directory and artifacts."""
    if not IDENTIFIER_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format.")
    session = SESSIONS.pop(session_id, None)
    temp_dir = TEMP_DIRS.pop(session_id, None)
    if temp_dir:
        try:
            temp_dir.cleanup()
        except Exception:
            pass
    if not session and not temp_dir:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "cleaned", "session_id": session_id}
