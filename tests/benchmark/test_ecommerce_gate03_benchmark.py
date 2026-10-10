"""Gate 03: Empirical Benchmark and Second-Domain (E-Commerce) Stress Test.

Evaluates Recon on Olist Brazilian E-Commerce orders without domain-specific tuning:
1. Clean Ground Truth: 10 clean orders transformed with 100% contract adherence.
2. Corrupted Dataset & Pre-Declared Fault Ledger:
   - F01: Missing mandatory order_id
   - F02: Illegal enum status ('RETURNED_TO_SENDER')
   - F03: Currency formatting symbol in numeric float ('$129.90')
   - F04: Non-standard datetime string ('09/25/2024 02:30:00 PM')
   - F05: Null in required non-nullable payment_value
   - F06: Pattern regex violation ('CALIFORNIA' vs '^[A-Z]{2}$')
3. Zero Data Loss Law: total_input == valid_records + quarantined_records.
"""

import json
from pathlib import Path
import time
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingStatus
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report
from recon.reporting.models import ReadinessState
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def benchmarks_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "benchmarks"


def test_ecommerce_gate03_clean_ground_truth(fixtures_dir: Path):
    """Verifies that clean e-commerce orders achieve 100% mapping accuracy and contract pass rate."""
    csv_path = fixtures_dir / "olist_orders_sample.csv"
    contract_path = fixtures_dir / "target_contract_ecommerce_order.json"

    start_time = time.perf_counter()

    # 1. Ingestion
    dataset = load_dataset(csv_path)
    assert dataset.row_count == 10
    assert len(dataset.headers) == 9

    # 2. Profiling
    profile = profile_dataset(dataset)
    assert profile.total_rows == 10
    assert profile.duplicate_rows_count == 0

    # 3. Target Contract & Mapping Proposal
    contract = load_target_contract(contract_path)
    assert len(contract.fields) == 9

    plan = propose_mappings(profile, contract)
    assert len(plan.proposals) == 9
    for target_name, proposal in plan.proposals.items():
        assert proposal.status == MappingStatus.PROPOSED, f"Field '{target_name}' was unresolved"
        assert proposal.source_field is not None

    # 4. Risk Assessment & Approval
    risks = evaluate_risks(profile, contract, plan)
    assert len(risks.critical_findings) == 0
    assert risks.is_blocked is False

    approved_plan = approve_mapping_plan(plan)

    # 5. Adapter Generation & Validation Sandbox
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    elapsed_seconds = round(time.perf_counter() - start_time, 4)

    assert validation.total_input_records == 10
    assert validation.valid_records_count == 10
    assert validation.quarantined_records_count == 0
    assert validation.contract_pass_rate == 100.0
    assert validation.is_contract_valid is True
    assert validation.all_tests_passed is True

    # 6. Readiness Report
    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
        approved_plan=approved_plan,
        validation_result=validation,
    )
    assert report.readiness_state == ReadinessState.READY
    assert len(report.blocking_reasons) == 0


def test_ecommerce_gate03_corrupted_fault_ledger_and_zero_loss(fixtures_dir: Path, benchmarks_dir: Path):
    """Verifies 100% recall on the 6 pre-declared e-commerce integration faults with zero data loss."""
    csv_path = fixtures_dir / "olist_orders_corrupted.csv"
    contract_path = fixtures_dir / "target_contract_ecommerce_order.json"

    # 1. Ingest & Profile
    dataset = load_dataset(csv_path)
    assert dataset.row_count == 10
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)

    # 2. Propose & Approve Mappings
    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)

    # 3. Generate Adapter & Execute Validation
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 4. Zero Data Loss Law Verification
    assert validation.total_input_records == 10
    assert validation.valid_records_count == 4
    assert validation.quarantined_records_count == 6
    assert (
        validation.valid_records_count + validation.quarantined_records_count
        == validation.total_input_records
    )

    # 5. Verify the 6 Specific Faults in Quarantine Logs
    quarantined = validation.sample_quarantined_records
    # Expand to all quarantined records by executing directly in sandbox
    from recon.validation.executor import compile_adapter_sandbox

    sandbox = compile_adapter_sandbox(adapter.python_code)
    _, all_quarantined = sandbox["transform_dataset"](dataset.rows)
    assert len(all_quarantined) == 6

    # Extract all error messages
    error_texts = [" ".join(q["errors"]) for q in all_quarantined]

    # Fault F01: Missing mandatory order_id
    assert any("Required non-nullable field 'order_id' is missing or null" in t for t in error_texts)

    # Fault F02: Illegal enum status ('RETURNED_TO_SENDER')
    assert any("Value 'RETURNED_TO_SENDER' for 'order_status' not in allowed values" in t for t in error_texts)

    # Fault F03: Currency formatting symbol in numeric float ('$129.90')
    assert any("Cannot parse float for 'payment_value' from '$129.90'" in t for t in error_texts)

    # Fault F04: Non-standard datetime string ('09/25/2024 02:30:00 PM')
    assert any("Cannot parse datetime for 'order_purchase_timestamp'" in t for t in error_texts)

    # Fault F05: Null in required non-nullable payment_value
    assert any("Required non-nullable field 'payment_value' is missing or null" in t for t in error_texts)

    # Fault F06: Regex pattern mismatch on customer_state ('CALIFORNIA')
    assert any("does not match pattern" in t and "^[A-Z]{2}$" in t for t in error_texts)

    # 6. Export Benchmark Artifacts
    results_dir = benchmarks_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    summary_json = {
        "gate": "Gate 03: Second-Domain Evaluation (E-Commerce)",
        "domain": "E-Commerce / Retail Order Management",
        "clean_records_tested": 10,
        "clean_pass_rate": "100.0%",
        "corrupted_records_tested": 10,
        "predeclared_faults_injected": 6,
        "predeclared_faults_quarantined": 6,
        "fault_detection_recall": "100.0% (6/6)",
        "zero_data_loss_verified": True,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(results_dir / "gate03_ecommerce_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)
