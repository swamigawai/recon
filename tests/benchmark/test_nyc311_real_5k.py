"""Benchmark integration test evaluating Recon against 5,000 real NYC 311 production records."""

from pathlib import Path
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.ingestion.csv_loader import load_csv
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_5k_path() -> Path:
    return Path(__file__).parent.parent.parent / "benchmarks" / "fixtures" / "nyc_311_5k_real.csv"


def test_real_nyc_311_5k_scale_and_quarantine(real_5k_path: Path, fixtures_dir: Path):
    """Verifies that Recon scales to 5,000 real production records and accurately quarantines unmapped categories."""
    assert real_5k_path.exists(), f"Missing real fixture at {real_5k_path}"

    contract_path = fixtures_dir / "target_contract_service_request.json"
    contract = load_target_contract(contract_path)

    # 1. Ingestion
    dataset = load_csv(real_5k_path)
    assert dataset.row_count == 5000
    assert len(dataset.headers) == 44
    assert dataset.fingerprint == "b0d0477d50f5ff36c933f8bd17fbad5f71b3df9953ae5a8da510243357223eb7"

    # 2. Profiling & Independent Verification
    profile = profile_dataset(dataset)
    assert profile.total_rows == 5000
    assert profile.get_column("closed_date").null_count == 2813
    assert profile.get_column("incident_zip").null_count == 41
    assert profile.get_column("latitude").null_count == 83

    # 3. Mapping & Risks
    plan = propose_mappings(profile, contract)
    risks = evaluate_risks(profile, contract, plan)

    # Must catch real-world categorical drift in status
    status_risks = [f for f in risks.findings if "status" in f.affected_fields and f.rule_id == "R005_ENUM_VIOLATION"]
    assert len(status_risks) == 1

    # 4. Adapter Execution on 5,000 Real Records
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # Conforming records strictly pass target contract
    assert validation.valid_records_count == 3455
    # Non-conforming records (1,539 In Progress, 5 Assigned, 1 Unspecified) quarantined
    assert validation.quarantined_records_count == 1545
    # ZERO records silently dropped
    assert validation.valid_records_count + validation.quarantined_records_count == 5000
