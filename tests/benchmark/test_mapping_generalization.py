"""Fair Generalization and Mapping Quality Benchmark on Unfamiliar Schemas.

Evaluates Recon's deterministic mapping engine on an entirely unfamiliar logistics schema
without adding target fields or synonyms to proposer.py.

Ground-Truth Answer Key is pre-declared before evaluation:
- consignment_id  -> manifest_no
- recipient_code   -> party_id
- dispatch_status  -> workflow_stage
- departure_time   -> departed_at
- gross_weight_kg  -> weight_metric
- declared_value   -> valuation
- destination_city -> dropoff_locality
- destination_state-> dropoff_province
"""

import json
from pathlib import Path
import time
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import AdapterError, MappingError
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingStatus
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report
from recon.reporting.models import ReadinessState
from recon.risks.evaluator import evaluate_risks

GROUND_TRUTH_MAPPINGS: dict[str, str] = {
    "consignment_id": "manifest_no",
    "recipient_code": "party_id",
    "dispatch_status": "workflow_stage",
    "departure_time": "departed_at",
    "gross_weight_kg": "weight_metric",
    "declared_value": "valuation",
    "destination_city": "dropoff_locality",
    "destination_state": "dropoff_province",
}


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def benchmarks_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "benchmarks"


def test_fair_generalization_on_unfamiliar_schema(fixtures_dir: Path, benchmarks_dir: Path):
    """Measures zero-tuning mapping quality against pre-declared ground truth without synthetic synonym assists."""
    csv_path = fixtures_dir / "warehouse_manifest_unfamiliar.csv"
    contract_path = fixtures_dir / "target_contract_dispatch_manifest.json"

    # 1. Ingestion & Profiling
    dataset = load_dataset(csv_path)
    assert dataset.row_count == 5
    profile = profile_dataset(dataset)
    contract = load_target_contract(contract_path)

    # 2. Automated Mapping Proposal
    plan = propose_mappings(profile, contract)
    assert len(plan.proposals) == len(GROUND_TRUTH_MAPPINGS)

    # 3. Objective Scoring Against Pre-Declared Ground Truth
    correct_mappings: list[str] = []
    incorrect_mappings: list[tuple[str, str, str]] = []  # (target, proposed, expected)
    unresolved_mappings: list[str] = []

    for target_field, expected_source in GROUND_TRUTH_MAPPINGS.items():
        proposal = plan.proposals.get(target_field)
        if proposal is None or proposal.status == MappingStatus.UNRESOLVED or proposal.source_field is None:
            unresolved_mappings.append(target_field)
        elif proposal.source_field == expected_source:
            correct_mappings.append(target_field)
        else:
            incorrect_mappings.append((target_field, proposal.source_field, expected_source))

    total_fields = len(GROUND_TRUTH_MAPPINGS)
    proposed_count = len(correct_mappings) + len(incorrect_mappings)
    precision = (len(correct_mappings) / proposed_count) if proposed_count > 0 else 0.0
    recall = len(correct_mappings) / total_fields

    # 4. Engine Safety Verification (Fail-Safe Behavior)
    # The engine MUST NOT hallucinate false bindings, and MUST block adapter generation when required fields are unresolved
    approved_plan = approve_mapping_plan(plan)
    with pytest.raises(AdapterError) as exc_info:
        generate_adapter(approved_plan, contract)
    assert "Cannot generate adapter: approved mapping plan is incomplete" in str(exc_info.value)
    assert len(exc_info.value.context.get("missing_required_fields", [])) > 0

    # Risk evaluation and Readiness Report must classify integration as BLOCKED
    risks = evaluate_risks(profile, contract, plan)
    report = build_readiness_report(
        profile=profile,
        contract=contract,
        mapping_plan=plan,
        risk_assessment=risks,
    )
    assert report.readiness_state == ReadinessState.BLOCKED
    assert any("Missing Required Target Field" in r for r in report.blocking_reasons)

    # 5. Persist Baseline Generalization Summary
    results_dir = benchmarks_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "benchmark": "Unfamiliar Schema Fair Generalization Baseline",
        "domain": "Logistics Dispatch Manifest",
        "target_contract": contract.contract_name,
        "total_target_fields": total_fields,
        "correct_mappings_count": len(correct_mappings),
        "incorrect_mappings_count": len(incorrect_mappings),
        "unresolved_mappings_count": len(unresolved_mappings),
        "mapping_precision": round(precision, 4),
        "mapping_recall": round(recall, 4),
        "unresolved_fields": unresolved_mappings,
        "incorrect_matches": [
            {"target": t, "proposed": p, "expected": e} for t, p, e in incorrect_mappings
        ],
        "safe_fail_stop_verified": True,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(results_dir / "generalization_baseline_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
