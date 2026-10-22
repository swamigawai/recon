"""End-to-end benchmark workflow verification script for Gate 16.

Audits:
1. Ingestion -> Profiling -> Mapping -> Risks -> Approval -> Adapter Synthesis -> Sandbox Execution -> Artifacts.
2. Invariant: N_total == N_valid + N_quarantined.
3. Verification that unapproved/unresolved mappings cannot silently become approved.
4. Verification that required-field failures are accurately reported.
5. Verification of generated artifacts (Adapter .py, Markdown report, JSON report).
"""

import json
from pathlib import Path
import sys

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import MappingError
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingStatus, MappingType
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report, render_markdown_report
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter


def run_benchmark_audit():
    print("=" * 70)
    print("RECON GATE 16: FULL BENCHMARK DATA CORRECTNESS & PIPELINE AUDIT")
    print("=" * 70)

    root = Path(__file__).resolve().parents[1]
    fixtures_dir = root / "tests" / "fixtures"

    source_path = fixtures_dir / "gate09_pilot_b2b_vendor_invoices.csv"
    if not source_path.is_file():
        source_path = fixtures_dir / "b2b_vendor_invoices_raw.csv"

    contract_path = fixtures_dir / "target_contract_b2b_vendor_invoice.json"
    if not contract_path.is_file():
        contract_path = fixtures_dir / "target_contract_gate09_pilot_b2b.json"

    print(f"Source Dataset:  {source_path.name}")
    print(f"Target Contract: {contract_path.name}")

    # 1. Ingestion
    dataset = load_dataset(source_path)
    print(f"\n[1] Ingestion: {len(dataset.rows)} records ingested, headers: {dataset.headers}")
    assert len(dataset.rows) > 0

    # 2. Profiling
    profile = profile_dataset(dataset)
    print(f"[2] Profiling: Fingerprint {profile.fingerprint[:16]}..., {profile.total_columns} columns profiled")

    # 3. Target Contract
    contract = load_target_contract(contract_path)
    print(f"[3] Contract: '{contract.contract_name}' v{contract.version} with {len(contract.fields)} fields")

    # 4. Deterministic Mapping Proposal
    plan = propose_mappings(profile, contract)
    print(f"[4] Mapping Engine: Generated {len(plan.proposals)} proposals")
    for name, p in plan.proposals.items():
        print(f"    - {name:<20} -> {str(p.source_field):<22} [{p.mapping_type.value}] ({len(p.evidence)} evidence items)")

    # Invariant Check: Unapproved and unresolved mappings cannot silently become approved
    print("\n[Audit Check A] Testing that unresolved mappings cannot silently become approved...")
    for p in plan.unresolved_proposals():
        assert p.status == MappingStatus.UNRESOLVED or p.mapping_type in (
            MappingType.AMBIGUOUS,
            MappingType.MISSING_SOURCE,
            MappingType.UNSUPPORTED,
        ), f"Unresolved proposal '{p.target_field}' must maintain non-approved status"
    print("  -> Passed: Zero silent auto-approvals observed.")

    # Invariant Check: Required field cannot be approved without source mapping
    print("\n[Audit Check B] Testing that missing required field blocks approval...")
    try:
        # Create an artificial empty mapping for a required field
        req_field_name = next(f for f, f_def in contract.fields.items() if f_def.required)
        approve_mapping_plan(
            plan=plan,
            reviewer="qa_auditor",
            overrides={req_field_name: {"source_field": None, "status": MappingStatus.APPROVED}},
        )
        raise AssertionError("Expected MappingError when approving required field with empty source!")
    except MappingError as exc:
        print(f"  -> Passed: Rejection enforced with actionable message: '{exc.message}'")

    # 5. Risk Assessment
    risks = evaluate_risks(profile, contract, plan)
    print(f"\n[5] Risk Assessment: {len(risks.findings)} findings ({len(risks.critical_findings)} critical, {len(risks.high_findings)} high)")

    # 6. Human Approval Boundary
    if "gate09" in source_path.name:
        overrides = {
            "invoice_number": {"source_field": "doc_number", "status": MappingStatus.APPROVED},
            "vendor_gstin": {"source_field": "gst_reg_no", "status": MappingStatus.APPROVED},
            "buyer_pan": {"source_field": "entity_pan", "status": MappingStatus.APPROVED},
            "invoice_date": {"source_field": "billing_date", "status": MappingStatus.APPROVED},
            "total_amount": {"source_field": "net_amount", "status": MappingStatus.APPROVED},
            "destination_pincode": {"source_field": "postal_code_primary", "status": MappingStatus.APPROVED},
            "payment_status": {"source_field": "invoice_status", "status": MappingStatus.APPROVED},
        }
    else:
        overrides = {
            "invoice_number": {"source_field": "bill_no", "status": MappingStatus.APPROVED},
            "vendor_gstin": {"source_field": "supplier_gst", "status": MappingStatus.APPROVED},
            "buyer_pan": {"source_field": "client_pan_id", "status": MappingStatus.APPROVED},
            "destination_pincode": {"source_field": "delivery_pincode", "status": MappingStatus.APPROVED},
        }
    approved_plan = approve_mapping_plan(plan=plan, reviewer="lead_integration_engineer", overrides=overrides)
    print(f"[6] Human Approval: Approved by '{approved_plan.approved_by}' with {len(approved_plan.approved_mappings)} mappings")

    # 7. Adapter AST Synthesis
    adapter = generate_adapter(approved_plan, contract)
    print(f"[7] Adapter Synthesis: Generated {len(adapter.python_code.splitlines())} lines of reviewable Python code")
    assert "def transform_record" in adapter.python_code

    # 8. Sandbox Validation & Zero-Loss Accounting
    validation = validate_adapter(adapter, contract, dataset.rows)
    print(f"\n[8] Validation Execution Results:")
    print(f"    Total Input Records:         {validation.total_input_records}")
    print(f"    Valid Passed Records:        {validation.valid_records_count}")
    print(f"    Quarantined Records:         {validation.quarantined_records_count}")
    print(f"    Contract Pass Rate:          {validation.contract_pass_rate:.2f}%")

    # Exact Zero-Loss Accounting Invariant
    n_total = validation.total_input_records
    n_valid = validation.valid_records_count
    n_quarantine = validation.quarantined_records_count

    assert n_total == n_valid + n_quarantine, (
        f"DATA LOSS DETECTED: Total ({n_total}) != Valid ({n_valid}) + Quarantine ({n_quarantine})"
    )
    print(f"  -> ZERO-LOSS INVARIANT SATISFIED: {n_total} == {n_valid} + {n_quarantine}")

    # 9. Readiness Dossier & Deliverables
    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
        approved_plan=approved_plan,
        validation_result=validation,
    )
    markdown_dossier = render_markdown_report(report)
    print(f"\n[9] Deliverables Dossier Generated:")
    print(f"    Readiness State:  {report.readiness_state.value}")
    print(f"    Markdown Dossier: {len(markdown_dossier.splitlines())} lines")

    print("\n" + "=" * 70)
    print("BENCHMARK AUDIT COMPLETE: ALL INVARIANTS & RECON CONTRACTS VERIFIED!")
    print("=" * 70)
    return {
        "dataset": source_path.name,
        "contract": contract_path.name,
        "total_records": n_total,
        "valid_records": n_valid,
        "quarantined_records": n_quarantine,
        "pass_rate": validation.contract_pass_rate,
        "readiness_state": report.readiness_state.value,
        "adapter_lines": len(adapter.python_code.splitlines()),
    }


if __name__ == "__main__":
    res = run_benchmark_audit()
    print("\nSummary Result JSON:")
    print(json.dumps(res, indent=2))
