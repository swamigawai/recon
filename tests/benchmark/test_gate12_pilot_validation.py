"""Gate 12 — Real-World Pilot Validation, Data Integrity & Production Readiness Benchmark.

Comprehensive validation across:
1. Independent data-integrity verification and zero-loss accounting invariant.
2. Adversarial value-level precision and edge-case handling (leading zeros, unicode, decimals, enums).
3. Mapping specification round-trip fidelity, security validation, and fingerprint checks.
4. Universal contract ingestion hardening (circular $ref loop detection, remote $ref blocking).
5. Subprocess CLI preflight gate exit codes (0, 1, 2) and clean JSON output parsing.
6. Security boundaries and in-process execution sandbox restrictions.
"""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.contracts.models import ContractType, TargetContract, TargetField
from recon.contracts.universal import resolve_local_ref
from recon.exceptions import AdapterError, ContractError, MappingError
from recon.ingestion.csv_loader import load_csv
from recon.mapping import (
    ApprovedMappingPlan,
    FieldMappingProposal,
    MappingPlan,
    MappingSpecification,
    MappingStatus,
    MappingType,
    approve_mapping_plan,
    export_mapping_spec,
    load_mapping_spec,
    propose_mappings,
    validate_and_apply_mapping_spec,
)
from recon.profiling.profiler import profile_dataset
from recon.validation.executor import compile_adapter_sandbox, validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


def run_recon_subprocess(*args: str) -> subprocess.CompletedProcess:
    """Helper to run recon CLI in an isolated subprocess."""
    cmd = [sys.executable, "-m", "recon.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path.cwd()))


# =============================================================================
# STEP 1: INDEPENDENT DATA INTEGRITY & ZERO-LOSS VERIFICATION
# =============================================================================

def test_gate12_independent_data_integrity_and_zero_loss(fixtures_dir: Path):
    """Verifies that total = valid + quarantined invariant holds exactly against independently defined ground truth.
    
    Expected outputs are NOT computed using Recon engine methods, but asserted
    against independent expectations.
    """
    contract_path = fixtures_dir / "target_contract_gate09_pilot_b2b.json"
    csv_path = fixtures_dir / "gate09_pilot_b2b_vendor_invoices.csv"
    expected_path = fixtures_dir / "gate09_pilot_expected_output.json"

    contract = load_target_contract(contract_path)
    dataset = load_csv(csv_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # Supply human reviewer overrides for unfamiliar fields
    overrides = {
        "invoice_id": {"source_field": "doc_number", "status": MappingStatus.APPROVED},
        "supplier_gstin": {"source_field": "gst_reg_no", "status": MappingStatus.APPROVED},
        "buyer_pan": {"source_field": "entity_pan", "status": MappingStatus.APPROVED},
        "destination_pin": {"source_field": "postal_code_primary", "status": MappingStatus.APPROVED},
    }
    approved = approve_mapping_plan(plan, reviewer="gate12_auditor", overrides=overrides)
    adapter = generate_adapter(approved, contract)
    val = validate_adapter(adapter, contract, dataset.rows)

    # 1. Primary Invariant: total input = valid output + quarantined
    assert val.total_input_records == 12
    assert val.valid_records_count == 5
    assert val.quarantined_records_count == 7
    assert val.total_input_records == val.valid_records_count + val.quarantined_records_count
    assert val.valid_records_count == ground_truth["valid_records_count"]
    assert val.quarantined_records_count == ground_truth["quarantined_records_count"]

    # 2. All valid records exported match ground truth exactly
    all_valid = val.all_valid_records
    assert len(all_valid) == 5
    for idx, (actual, expected) in enumerate(zip(all_valid, ground_truth["valid_records"])):
        assert actual == expected, f"Record {idx} mismatch: actual={actual}, expected={expected}"

    # 3. Duplicate row preservation: INV-00042 appears in row 0 and row 1
    assert all_valid[0]["invoice_id"] == "INV-00042"
    assert all_valid[1]["invoice_id"] == "INV-00042"
    assert all_valid[0] == all_valid[1]

    # 4. Quarantine isolation & diagnostic verification
    all_quarantined = val.all_quarantined_records
    assert len(all_quarantined) == 7
    quarantine_indices = [q["record_index"] for q in all_quarantined]
    assert quarantine_indices == [6, 7, 8, 9, 10, 11, 12]

    # Row 5 was missing invoice_id
    assert any("invoice_id" in err for err in all_quarantined[0]["errors"])
    # Row 6 had invalid GSTIN pattern
    assert any("supplier_gstin" in err for err in all_quarantined[1]["errors"])
    # Row 7 had invalid PAN length
    assert any("buyer_pan" in err for err in all_quarantined[2]["errors"])
    # Row 8 had invalid PIN length
    assert any("destination_pin" in err for err in all_quarantined[3]["errors"])
    # Row 9 had invalid IFSC pattern
    assert any("bank_ifsc" in err for err in all_quarantined[4]["errors"])
    # Row 10 had currency symbol string in float field
    assert any("net_amount" in err for err in all_quarantined[5]["errors"])
    # Row 11 had invalid enum value WRITTEN_OFF
    assert any("invoice_status" in err for err in all_quarantined[6]["errors"])


# =============================================================================
# STEP 2: ADVERSARIAL VALUE-LEVEL PRECISION & EDGE CASES
# =============================================================================

def test_gate12_adversarial_value_preservation():
    """Tests critical data-type boundary conditions: leading zeros, decimals, Unicode, enums, nulls."""
    contract = TargetContract(
        contract_name="adversarial_test_contract",
        version="1.0.0",
        fields={
            "postal_code": TargetField(name="postal_code", target_type=ContractType.STRING, required=True),
            "amount": TargetField(name="amount", target_type=ContractType.FLOAT, required=True),
            "quantity": TargetField(name="quantity", target_type=ContractType.INTEGER, required=True),
            "is_active": TargetField(name="is_active", target_type=ContractType.BOOLEAN, required=True),
            "status": TargetField(name="status", target_type=ContractType.STRING, required=True, allowed_values=["APPROVED", "PENDING", "REJECTED"]),
            "notes": TargetField(name="notes", target_type=ContractType.STRING, required=False, nullable=True),
        },
    )

    plan = ApprovedMappingPlan(
        contract_name=contract.contract_name,
        source_name="adversarial_source.csv",
        source_fingerprint="dummy_fp",
        approved_by="qa_architect",
        approved_mappings={
            "postal_code": FieldMappingProposal(target_field="postal_code", target_type="string", target_required=True, target_nullable=False, source_field="raw_zip", mapping_type=MappingType.DIRECT, status=MappingStatus.APPROVED),
            "amount": FieldMappingProposal(target_field="amount", target_type="float", target_required=True, target_nullable=False, source_field="raw_amount", mapping_type=MappingType.DIRECT, status=MappingStatus.APPROVED),
            "quantity": FieldMappingProposal(target_field="quantity", target_type="integer", target_required=True, target_nullable=False, source_field="raw_qty", mapping_type=MappingType.DIRECT, status=MappingStatus.APPROVED),
            "is_active": FieldMappingProposal(target_field="is_active", target_type="boolean", target_required=True, target_nullable=False, source_field="raw_active", mapping_type=MappingType.DIRECT, status=MappingStatus.APPROVED),
            "status": FieldMappingProposal(target_field="status", target_type="string", target_required=True, target_nullable=False, source_field="raw_status", mapping_type=MappingType.DIRECT, status=MappingStatus.APPROVED),
            "notes": FieldMappingProposal(target_field="notes", target_type="string", target_required=False, target_nullable=True, source_field="raw_notes", mapping_type=MappingType.DIRECT, status=MappingStatus.APPROVED),
        },
    )

    adapter = generate_adapter(plan, contract)
    sandbox = compile_adapter_sandbox(adapter.python_code)
    transform_dataset = sandbox["transform_dataset"]

    adversarial_records = [
        # 1. Leading zeros preservation in postal code string ("00123")
        {
            "raw_zip": "00123",
            "raw_amount": "149.99",
            "raw_qty": "42",
            "raw_active": "true",
            "raw_status": "APPROVED",
            "raw_notes": "Leading zeros test",
            "extra_unmapped_column": "MUST_BE_EXCLUDED",
        },
        # 2. High decimal precision + Unicode characters (Hindi, French, Euro)
        {
            "raw_zip": "75001",
            "raw_amount": "999999.8765",
            "raw_qty": "100",
            "raw_active": "1",
            "raw_status": "PENDING",
            "raw_notes": "Facture payée en € / नई दिल्ली",
        },
        # 3. Boolean representations: "no", "0.0", "0"
        {
            "raw_zip": "90210",
            "raw_amount": "0.0",
            "raw_qty": "0",
            "raw_active": "no",
            "raw_status": "REJECTED",
            "raw_notes": None,
        },
        # 4. Null tokens in nullable string field ("N/A")
        {
            "raw_zip": "10001",
            "raw_amount": "50.5",
            "raw_qty": "5",
            "raw_active": "TRUE",
            "raw_status": "APPROVED",
            "raw_notes": "N/A",
        },
        # 5. Invalid enum value ("UNKNOWN_STATUS") -> Quarantine
        {
            "raw_zip": "10002",
            "raw_amount": "10.0",
            "raw_qty": "1",
            "raw_active": "true",
            "raw_status": "UNKNOWN_STATUS",  # Not in allowed values
            "raw_notes": "Invalid enum value",
        },
        # 6. Corrupted integer -> Quarantine
        {
            "raw_zip": "10003",
            "raw_amount": "10.0",
            "raw_qty": "not_an_int",
            "raw_active": "true",
            "raw_status": "APPROVED",
            "raw_notes": "Corrupted qty",
        },
    ]

    valid, quarantined = transform_dataset(adversarial_records)

    # 4 valid, 2 quarantined = 6 total
    assert len(valid) == 4
    assert len(quarantined) == 2
    assert len(adversarial_records) == len(valid) + len(quarantined)

    # Assert 1: Leading zeros preserved verbatim
    assert valid[0]["postal_code"] == "00123"
    # Assert 2: Extra unmapped column excluded
    assert "extra_unmapped_column" not in valid[0]
    # Assert 3: Float precision preserved
    assert valid[0]["amount"] == 149.99
    assert valid[1]["amount"] == 999999.8765
    # Assert 4: Unicode preserved exactly
    assert valid[1]["notes"] == "Facture payée en € / नई दिल्ली"
    # Assert 5: Booleans properly parsed
    assert valid[0]["is_active"] is True
    assert valid[1]["is_active"] is True
    assert valid[2]["is_active"] is False
    # Assert 6: Null token normalized
    assert valid[3]["notes"] is None


# =============================================================================
# STEP 3: MAPPING SPECIFICATION ROUND-TRIP, SECURITY & FINGERPRINTS
# =============================================================================

def test_gate12_mapping_spec_roundtrip_fidelity(fixtures_dir: Path):
    """Verifies mapping specification export -> import -> export produces 100% identical JSON."""
    contract = load_target_contract(fixtures_dir / "target_contract_service_request.json")
    dataset = load_csv(fixtures_dir / "synthetic_nyc_311.csv")
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    spec1 = export_mapping_spec(contract, profile, plan, reviewer="lead_qa_architect")
    json1 = spec1.to_json()

    # Re-import from JSON using from_json
    spec2 = MappingSpecification.from_json(json1)
    json2 = spec2.to_json()

    # Roundtrip comparison
    assert json1 == json2
    assert spec1.contract_fingerprint == spec2.contract_fingerprint
    assert spec1.source_fingerprint == spec2.source_fingerprint
    assert len(spec1.mappings) == len(spec2.mappings)


def test_gate12_mapping_spec_fingerprint_mismatch_warning(fixtures_dir: Path):
    """Verifies that contract or source changes trigger precise mismatch detections."""
    contract = load_target_contract(fixtures_dir / "target_contract_service_request.json")
    dataset = load_csv(fixtures_dir / "synthetic_nyc_311.csv")
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    spec = export_mapping_spec(contract, profile, plan, reviewer="test_user")

    # Tamper contract fingerprint to simulate modified target contract
    tampered_dict = spec.model_dump()
    tampered_dict["contract_fingerprint"] = "0000000000000000000000000000000000000000000000000000000000000000"
    tampered_spec = MappingSpecification.model_validate(tampered_dict)

    _, validation = validate_and_apply_mapping_spec(tampered_spec, contract, profile, plan)
    assert validation.contract_match is False
    assert any("fingerprint mismatch" in m for m in validation.mismatches)


def test_gate12_mapping_spec_unapproved_fields_remain_unapproved(fixtures_dir: Path):
    """Verifies that unreviewed or unapproved mappings in imported specs are NOT silently approved."""
    contract = load_target_contract(fixtures_dir / "target_contract_gate09_pilot_b2b.json")
    dataset = load_csv(fixtures_dir / "gate09_pilot_b2b_vendor_invoices.csv")
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # Export mapping plan before human review (several required fields UNRESOLVED)
    spec = export_mapping_spec(contract, profile, plan, reviewer="preflight_system")

    # Import spec into fresh session
    fresh_plan = propose_mappings(profile, contract)
    updated_plan, val = validate_and_apply_mapping_spec(spec, contract, profile, fresh_plan)

    # Unresolved fields must remain UNRESOLVED
    assert updated_plan.proposals["invoice_id"].status == MappingStatus.UNRESOLVED
    assert updated_plan.proposals["supplier_gstin"].status == MappingStatus.UNRESOLVED
    assert len(updated_plan.unresolved_proposals()) > 0


def test_gate12_mapping_spec_rejects_unsafe_transformations(fixtures_dir: Path):
    """Verifies that non-whitelisted or malicious transformation expressions are rejected during validation."""
    contract = load_target_contract(fixtures_dir / "target_contract_service_request.json")
    dataset = load_csv(fixtures_dir / "synthetic_nyc_311.csv")
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    malicious_spec_dict = {
        "schema_version": "1.0",
        "contract_name": contract.contract_name,
        "contract_fingerprint": contract.fingerprint,
        "source_fingerprint": profile.fingerprint,
        "mappings": [
            {
                "target_field": "ticket_id",
                "source_field": "Unique Key",
                "mapping_type": "direct",
                "transformation_rule": "__import__('os').system('calc')",  # Unsafe injection
                "approved": True,
            }
        ],
    }
    spec = MappingSpecification.model_validate(malicious_spec_dict)
    updated_plan, validation = validate_and_apply_mapping_spec(spec, contract, profile, plan)

    assert validation.is_valid is False
    assert any("Unsafe or forbidden transformation rule" in c for c in validation.conflicts)
    assert updated_plan.proposals["ticket_id"].mapping_type == MappingType.UNSUPPORTED
    assert updated_plan.proposals["ticket_id"].status == MappingStatus.UNRESOLVED


# =============================================================================
# STEP 4: UNIVERSAL CONTRACT INGESTION HARDENING
# =============================================================================

def test_gate12_circular_ref_detection():
    """Verifies that circular $ref loops are detected immediately and fail closed without recursion overflow."""
    circular_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "CircularContract",
        "type": "object",
        "definitions": {
            "NodeA": {
                "type": "object",
                "properties": {
                    "next": {"$ref": "#/definitions/NodeB"}
                }
            },
            "NodeB": {
                "type": "object",
                "properties": {
                    "parent": {"$ref": "#/definitions/NodeA"}
                }
            }
        },
        "properties": {
            "root_node": {"$ref": "#/definitions/NodeA"}
        }
    }

    # Direct loop check on resolve_local_ref
    visited = {"#/definitions/NodeA"}
    with pytest.raises(ContractError) as exc_info:
        resolve_local_ref("#/definitions/NodeA", circular_schema, visited=visited)
    assert "Circular $ref reference detected" in str(exc_info.value)


def test_gate12_remote_ref_rejection():
    """Verifies that remote $ref references (http/https) are strictly rejected for security."""
    remote_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "RemoteRefContract",
        "type": "object",
        "properties": {
            "external_model": {"$ref": "https://example.com/schemas/user.json"}
        }
    }
    with pytest.raises(ContractError) as exc_info:
        resolve_local_ref("https://example.com/schemas/user.json", remote_schema)
    assert "Remote $ref references are forbidden for security reasons" in str(exc_info.value)


# =============================================================================
# STEP 5: CLI / CI PREFLIGHT GATE SUBPROCESS MATRIX
# =============================================================================

def test_gate12_cli_gate_exit_code_matrix(fixtures_dir: Path, tmp_path: Path):
    """Executes the recon gate CLI in real OS subprocesses and tests the complete exit code matrix."""
    contract_file = fixtures_dir / "target_contract_service_request.json"
    clean_csv = fixtures_dir / "synthetic_nyc_311.csv"
    corrupted_csv = fixtures_dir / "corrupted_nyc_311.csv"
    unfamiliar_csv = fixtures_dir / "warehouse_manifest_unfamiliar.csv"

    # Export a valid mapping spec for synthetic_nyc_311
    contract = load_target_contract(contract_file)
    dataset = load_csv(clean_csv)
    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    spec = export_mapping_spec(contract, profile, plan, reviewer="ci_gate_tester")
    spec_path = tmp_path / "valid_spec.json"
    spec.save_to_file(spec_path)

    # 1. Exit Code 0: Clean dataset + valid spec -> Pass
    res_0 = run_recon_subprocess(
        "gate",
        "--source", str(clean_csv),
        "--contract", str(contract_file),
        "--mapping-spec", str(spec_path),
        "--json",
    )
    assert res_0.returncode == 0
    data_0 = json.loads(res_0.stdout)
    assert data_0["status"] == "PASS"
    assert data_0["exit_code"] == 0

    # 2. Exit Code 1: Missing required field mappings (unfamiliar CSV)
    res_1a = run_recon_subprocess(
        "gate",
        "--source", str(unfamiliar_csv),
        "--contract", str(contract_file),
        "--json",
    )
    assert res_1a.returncode == 1
    data_1a = json.loads(res_1a.stdout)
    assert data_1a["status"] == "FAIL"
    assert data_1a["exit_code"] == 1
    assert len(data_1a["mapping"]["unresolved_required_fields"]) > 0

    # 3. Exit Code 1: Quarantine threshold exceeded (corrupted CSV with 0% tolerance)
    res_1b = run_recon_subprocess(
        "gate",
        "--source", str(corrupted_csv),
        "--contract", str(contract_file),
        "--mapping-spec", str(spec_path),
        "--max-quarantine-pct", "0.0",
        "--json",
    )
    assert res_1b.returncode == 1
    data_1b = json.loads(res_1b.stdout)
    assert data_1b["status"] == "FAIL"
    assert data_1b["exit_code"] == 1

    # 4. Exit Code 2: Bad input file / nonexistent source
    res_2a = run_recon_subprocess(
        "gate",
        "--source", "nonexistent_source_path_xyz.csv",
        "--contract", str(contract_file),
        "--json",
    )
    assert res_2a.returncode == 2
    data_2a = json.loads(res_2a.stdout)
    assert data_2a["status"] == "ERROR"
    assert data_2a["exit_code"] == 2

    # 5. Exit Code 2: Invalid threshold argument
    res_2b = run_recon_subprocess(
        "gate",
        "--source", str(clean_csv),
        "--contract", str(contract_file),
        "--max-quarantine-pct", "-50.0",
    )
    assert res_2b.returncode == 2
    assert "Must be between 0.0 and 100.0" in res_2b.stderr


def test_gate12_cli_gate_json_isolation_stdout():
    """Verifies that --json outputs strictly parseable JSON on stdout with no banner contamination."""
    res = run_recon_subprocess(
        "gate",
        "--source", "tests/fixtures/synthetic_nyc_311.csv",
        "--contract", "tests/fixtures/target_contract_service_request.json",
        "--json",
    )
    # Output must be parseable directly without regex stripping
    try:
        data = json.loads(res.stdout)
    except Exception as exc:
        pytest.fail(f"--json output was not pure JSON: {exc}. Output was: {res.stdout}")
    assert "status" in data
    assert "exit_code" in data
    assert "contract" in data
    assert "source" in data


# =============================================================================
# STEP 6: SECURITY & SANDBOX RESTRICTIONS
# =============================================================================

def test_gate12_sandbox_rejects_dangerous_builtins():
    """Verifies that generated adapter sandbox rejects eval, exec, open, and arbitrary module imports at compile and runtime."""
    # 1. Compile-time rejection if top-level tries to access open
    with pytest.raises(NameError) as exc_info:
        compile_adapter_sandbox("f = open('test.txt', 'w')")
    assert "name 'open' is not defined" in str(exc_info.value)

    # 2. Runtime rejection inside transform_record
    malicious_adapter_code = """
def transform_record(record):
    with open("stolen_file.txt", "w") as f:
        f.write("leaked")
    return {}, []

def transform_dataset(records):
    return [], []
"""
    sandbox = compile_adapter_sandbox(malicious_adapter_code)
    with pytest.raises(NameError) as exc_info2:
        sandbox["transform_record"]({})
    assert "name 'open' is not defined" in str(exc_info2.value)


def test_gate12_sandbox_rejects_unauthorized_imports():
    """Verifies that unauthorized system imports (os, sys, socket) are blocked by sandbox import hook."""
    malicious_import_code = """
import os

def transform_record(record):
    return {}, []

def transform_dataset(records):
    return [], []
"""
    with pytest.raises(ImportError) as exc_info:
        compile_adapter_sandbox(malicious_import_code)
    assert "Import of module 'os' is disallowed in adapter sandbox" in str(exc_info.value)
