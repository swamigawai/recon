"""Comprehensive unit tests for Recon's 1-Click Smart Remediation Engine."""

import pytest
from fastapi.testclient import TestClient

from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.ingestion.models import RawDataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import FieldMappingProposal, MappingPlan, MappingStatus, MappingType
from recon.profiling.profiler import profile_dataset
from recon.remediation.applier import apply_remediations
from recon.remediation.detector import detect_remediations
from recon.remediation.models import RemediationCategory
from recon.server.app import create_app
from recon.server.routes import SESSIONS
from recon.validation.executor import validate_adapter
from recon.adapters.generator import generate_adapter


def _create_mock_session(rows: list[dict[str, str]], contract: TargetContract, session_id: str = "test_rem_sess"):
    """Helper creating a fully populated integration session."""
    headers = list(rows[0].keys()) if rows else []
    dataset = RawDataset(
        file_path="dirty_dataset.csv",
        file_name="dirty_dataset.csv",
        fingerprint="dirty_fingerprint_123",
        file_size_bytes=1024,
        encoding="utf-8",
        headers=headers,
        row_count=len(rows),
        rows=rows,
    )
    profile = profile_dataset(dataset)
    
    # Direct 1:1 mapping proposals
    proposals = {}
    for tgt_name, tgt_field in contract.fields.items():
        src_col = tgt_name if tgt_name in headers else None
        proposals[tgt_name] = FieldMappingProposal(
            target_field=tgt_name,
            target_type=tgt_field.target_type,
            target_required=tgt_field.required,
            target_nullable=tgt_field.nullable,
            source_field=src_col,
            mapping_type=MappingType.DIRECT if src_col else MappingType.MISSING_SOURCE,
            status=MappingStatus.APPROVED if src_col else MappingStatus.UNRESOLVED,
        )

    plan = MappingPlan(
        contract_name=contract.contract_name,
        source_name=dataset.file_name,
        source_fingerprint=dataset.fingerprint,
        proposals=proposals,
    )
    
    approved_plan = approve_mapping_plan(plan, reviewer="test_user")
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    session = {
        "session_id": session_id,
        "dataset": dataset,
        "profile": profile,
        "contract": contract,
        "plan": plan,
        "approved_plan": approved_plan,
        "adapter": adapter,
        "validation": validation,
    }
    SESSIONS[session_id] = session
    return session


def test_currency_and_thousands_cleaning_remediation():
    """Verifies that raw currency signs ($ / ,) in float fields are diagnosed and fixed via AST remediation."""
    contract = TargetContract(
        contract_name="finance_orders",
        version="1.0.0",
        fields={
            "order_id": TargetField(name="order_id", target_type=ContractType.STRING, required=True, nullable=False),
            "amount": TargetField(name="amount", target_type=ContractType.FLOAT, required=True, nullable=False),
        },
    )
    rows = [
        {"order_id": "ORD-1", "amount": "100.50"},
        {"order_id": "ORD-2", "amount": "$1,250.00"},  # dirty currency & comma
        {"order_id": "ORD-3", "amount": "$49.99"},     # dirty currency symbol
    ]
    
    session = _create_mock_session(rows, contract, "sess_currency")
    val_before = session["validation"]
    assert val_before.contract_pass_rate < 100.0
    assert val_before.quarantined_records_count == 2

    # 1. Detect remediations
    plan = detect_remediations(
        contract=contract,
        mapping_plan=session["plan"],
        profile=session["profile"],
        validation_result=val_before,
        session_id="sess_currency",
    )
    assert len(plan.candidates) == 1
    candidate = plan.candidates[0]
    assert candidate.field_name == "amount"
    assert candidate.category == RemediationCategory.CURRENCY_CLEANING
    assert candidate.proposed_transformation_rule == "clean_currency"
    assert plan.projected_pass_rate == 100.0
    assert plan.projected_rescued_records == 2

    # 2. Apply remediation
    outcome = apply_remediations(session, [candidate.candidate_id], reviewer="test_engineer")
    val_after = session["validation"]
    assert val_after.contract_pass_rate == 100.0
    assert val_after.quarantined_records_count == 0
    assert val_after.valid_records_count == 3
    assert outcome["receipt"]["rescued_records_count"] == 2
    assert outcome["receipt"]["new_readiness_state"] in ("READY", "PASS")


def test_datetime_format_detection_and_remediation():
    """Verifies non-standard US datetime format is identified, converted to ISO-8601, and rescued."""
    contract = TargetContract(
        contract_name="audit_logs",
        version="1.0.0",
        fields={
            "log_id": TargetField(name="log_id", target_type=ContractType.STRING, required=True, nullable=False),
            "created_at": TargetField(name="created_at", target_type=ContractType.DATETIME, required=True, nullable=False),
        },
    )
    rows = [
        {"log_id": "L-1", "created_at": "2024-01-15T10:00:00Z"},
        {"log_id": "L-2", "created_at": "09/25/2024 02:30:00 PM"},  # Non-standard US timestamp
    ]
    
    session = _create_mock_session(rows, contract, "sess_datetime")
    val_before = session["validation"]
    assert val_before.quarantined_records_count == 1

    plan = detect_remediations(
        contract=contract,
        mapping_plan=session["plan"],
        profile=session["profile"],
        validation_result=val_before,
        session_id="sess_datetime",
    )
    assert len(plan.candidates) == 1
    cand = plan.candidates[0]
    assert cand.field_name == "created_at"
    assert cand.category == RemediationCategory.DATETIME_FORMATTING
    assert "%m/%d/%Y %I:%M:%S %p" in cand.proposed_transformation_rule

    # Apply remediation
    apply_remediations(session, [cand.candidate_id], reviewer="lead_dev")
    val_after = session["validation"]
    assert val_after.contract_pass_rate == 100.0
    assert val_after.quarantined_records_count == 0
    # Check that output value is standard ISO-8601
    assert val_after.sample_valid_output[1]["created_at"] == "2024-09-25T14:30:00Z"


def test_enum_case_insensitivity_remediation():
    """Verifies that lower-cased / padded enum values are normalized to match contract categories."""
    contract = TargetContract(
        contract_name="dispatch_flow",
        version="1.0.0",
        fields={
            "task_id": TargetField(name="task_id", target_type=ContractType.STRING, required=True, nullable=False),
            "status": TargetField(
                name="status",
                target_type=ContractType.STRING,
                required=True,
                nullable=False,
                allowed_values=["In-Progress", "Pending", "Resolved"],
            ),
        },
    )
    rows = [
        {"task_id": "T-1", "status": "In-Progress"},
        {"task_id": "T-2", "status": "in-progress"},   # lower-case enum
        {"task_id": "T-3", "status": " pending "},     # padded lower-case
    ]

    session = _create_mock_session(rows, contract, "sess_enum")
    val_before = session["validation"]
    assert val_before.quarantined_records_count == 2

    plan = detect_remediations(
        contract=contract,
        mapping_plan=session["plan"],
        profile=session["profile"],
        validation_result=val_before,
        session_id="sess_enum",
    )
    assert len(plan.candidates) == 1
    cand = plan.candidates[0]
    assert cand.field_name == "status"
    assert cand.category == RemediationCategory.ENUM_NORMALIZATION

    apply_remediations(session, [cand.candidate_id], reviewer="operator")
    val_after = session["validation"]
    assert val_after.contract_pass_rate == 100.0
    assert val_after.quarantined_records_count == 0
    assert val_after.sample_valid_output[1]["status"] == "In-Progress"
    assert val_after.sample_valid_output[2]["status"] == "Pending"


def test_api_remediation_endpoints():
    """Tests /api/remediation/candidates/{session_id} and /api/remediation/apply end-to-end via FastAPI client."""
    contract = TargetContract(
        contract_name="billing",
        version="1.0.0",
        fields={
            "bill_id": TargetField(name="bill_id", target_type=ContractType.STRING, required=True, nullable=False),
            "fee": TargetField(name="fee", target_type=ContractType.FLOAT, required=True, nullable=False),
        },
    )
    rows = [
        {"bill_id": "B-1", "fee": "50.0"},
        {"bill_id": "B-2", "fee": "$75.25"},
    ]
    sess_id = "test_api_remediation_session"
    _create_mock_session(rows, contract, sess_id)

    app = create_app()
    client = TestClient(app)

    # 1. Fetch candidates
    resp = client.get(f"/api/remediation/candidates/{sess_id}")
    assert resp.status_code == 200
    plan_data = resp.json()
    assert plan_data["session_id"] == sess_id
    assert len(plan_data["candidates"]) == 1
    cand_id = plan_data["candidates"][0]["candidate_id"]

    # 2. Apply candidate
    apply_resp = client.post(
        "/api/remediation/apply",
        json={
            "session_id": sess_id,
            "selected_candidate_ids": [cand_id],
            "reviewer": "api_test_user",
        },
    )
    assert apply_resp.status_code == 200
    res = apply_resp.json()
    assert "results" in res
    assert "receipt" in res
    assert res["results"]["validation"]["contract_pass_rate"] == 100.0
    assert res["receipt"]["rescued_records_count"] == 1
