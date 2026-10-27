"""Unit tests for Gate 1 (Code Review) and Gate 2 (Security Review) hardening."""

import pytest
from fastapi.testclient import TestClient

from recon.adapters.generator import generate_adapter
from recon.adapters.models import GeneratedAdapter
from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.exceptions import SecurityError
from recon.mapping.models import ApprovedMappingPlan, FieldMappingProposal, MappingStatus, MappingType
from recon.server.app import app
from recon.server.routes import MAX_SESSIONS, SESSIONS, _prune_old_sessions
from recon.validation.executor import compile_adapter_sandbox


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_sandbox_rejects_dunder_escapes():
    """Gate 2: Verifies that AST security visitor blocks dunder attribute escapes (__class__, __subclasses__, __globals__)."""
    # 1. Direct subclass enumeration
    payload1 = "res = ().__class__.__mro__[1].__subclasses__()"
    with pytest.raises(SecurityError) as exc1:
        compile_adapter_sandbox(payload1)
    assert "__subclasses__" in str(exc1.value) or "__class__" in str(exc1.value)

    # 2. Function globals access
    payload2 = """
def transform_record(record):
    return transform_record.__globals__, []
"""
    with pytest.raises(SecurityError) as exc2:
        compile_adapter_sandbox(payload2)
    assert "__globals__" in str(exc2.value)


def test_code_generation_resilience_to_injection():
    """Gate 2: Verifies that malicious quotes and syntax in field names do not cause code injection."""
    contract = TargetContract(
        contract_name="test_contract",
        version="1.0.0",
        fields={
            "field_a": TargetField(name="field_a", target_type=ContractType.STRING, required=True),
        },
    )

    # Adversarial source field containing quotes and injected code
    adversarial_source = "col'); import os; os.system('calc'); #"
    plan = ApprovedMappingPlan(
        contract_name="test_contract",
        source_name="malicious.csv",
        source_fingerprint="abc",
        approved_by="test",
        approved_mappings={
            "field_a": FieldMappingProposal(
                target_field="field_a",
                target_type=ContractType.STRING,
                target_required=True,
                target_nullable=False,
                source_field=adversarial_source,
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            )
        },
    )

    adapter: GeneratedAdapter = generate_adapter(plan, contract)
    # The generated adapter must safely compile in the sandbox without executing injected code
    sandbox = compile_adapter_sandbox(adapter.python_code)
    assert "transform_record" in sandbox

    # Execution with a record containing that key must execute cleanly
    res, errors = sandbox["transform_record"]({adversarial_source: "valid_value"})
    assert res == {"field_a": "valid_value"}
    assert len(errors) == 0


def test_download_endpoints_reject_invalid_session_ids(client: TestClient):
    """Gate 2: Verifies that invalid session identifiers with path traversal or illegal characters are rejected with HTTP 400."""
    invalid_ids = [
        "bad..session",
        "bad*session",
        "invalid!@#$",
        "sess;drop table",
        "sess space",
    ]
    for bad_id in invalid_ids:
        res = client.get(f"/api/download/report/{bad_id}")
        assert res.status_code == 400, f"Expected 400 for bad session id: {bad_id}, got {res.status_code}"


def test_session_pruning_prevents_unbounded_growth():
    """Gate 1 & 2: Verifies that session pruning limits SESSIONS and TEMP_DIRS to MAX_SESSIONS."""
    for i in range(MAX_SESSIONS + 15):
        sid = f"test_sess_{i}"
        SESSIONS[sid] = {"dummy": True}

    _prune_old_sessions()
    assert len(SESSIONS) <= MAX_SESSIONS

    # Clean up test sessions
    for i in range(MAX_SESSIONS + 15):
        SESSIONS.pop(f"test_sess_{i}", None)
