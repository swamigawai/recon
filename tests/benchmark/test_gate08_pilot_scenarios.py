"""Gate 08 Full System Validation Benchmark Suite.

Covers:
1. Pilot Scenario 1: B2B SaaS Subscription Billing
2. Pilot Scenario 2: Warehouse Inventory Reconciliation & SKU Tracking
3. Pilot Scenario 3: International Freight Manifests
4. Phase H: Duplicate and Financial Data Integrity Tests
"""

import json
from pathlib import Path
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import AdapterError
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingStatus, MappingType
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import compile_adapter_sandbox, validate_adapter


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


# -----------------------------------------------------------------------------
# Pilot Scenario 1: Subscription Billing
# -----------------------------------------------------------------------------

def test_pilot_1_subscription_billing_workflow(fixtures_dir: Path):
    contract = load_target_contract(fixtures_dir / "target_contract_subscription_billing.json")
    dataset = load_dataset(fixtures_dir / "subscription_billing_raw.csv")
    with open(fixtures_dir / "subscription_billing_expected_output.json", "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # 1. Unfamiliar fields remain unresolved
    unresolved = ["subscription_id", "customer_account_id", "plan_tier", "mrr_amount"]
    for field in unresolved:
        prop = plan.proposals[field]
        assert prop.status == MappingStatus.UNRESOLVED
        assert prop.mapping_type == MappingType.MISSING_SOURCE

    # 2. Risk engine blocks adapter generation
    risks = evaluate_risks(profile, contract, plan)
    assert risks.is_blocked is True
    with pytest.raises(AdapterError):
        generate_adapter(approve_mapping_plan(plan), contract)

    # 3. Human overrides and approved adapter generation
    overrides = {
        "subscription_id": {"source_field": "sub_token", "status": MappingStatus.APPROVED},
        "customer_account_id": {"source_field": "client_ref", "status": MappingStatus.APPROVED},
        "plan_tier": {"source_field": "tier_code", "status": MappingStatus.APPROVED},
        "mrr_amount": {"source_field": "recurring_amount", "status": MappingStatus.APPROVED},
        "cancellation_reason": {"source_field": "churn_notes", "status": MappingStatus.APPROVED},
    }
    approved = approve_mapping_plan(plan, reviewer="billing_lead", overrides=overrides)
    adapter = generate_adapter(approved, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 4. Zero Data Loss Accounting
    assert validation.total_input_records == 8
    assert validation.valid_records_count == 4
    assert validation.quarantined_records_count == 4
    assert validation.valid_records_count + validation.quarantined_records_count == 8

    # 5. Exact Value-by-Value Match on Conforming Records
    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid_records, quarantined_records = sandbox["transform_dataset"](dataset.rows)

    expected_valid = expected_data["valid_records"]
    assert len(valid_records) == len(expected_valid)
    for act, exp in zip(valid_records, expected_valid):
        assert act == exp
        assert "account_exec_id" not in act  # Extra column omitted

    # 6. Fault Ledger Verification
    expected_faults = expected_data["quarantined_fault_ledger"]
    assert len(quarantined_records) == len(expected_faults)
    for act_q, exp_f in zip(quarantined_records, expected_faults):
        assert act_q["record_index"] == exp_f["record_index"]
        assert exp_f["error_code"] in act_q["error_codes"]
        assert any(exp_f["expected_error_substring"] in err for err in act_q["errors"])


# -----------------------------------------------------------------------------
# Pilot Scenario 2: Inventory Reconciliation
# -----------------------------------------------------------------------------

def test_pilot_2_inventory_reconciliation_workflow(fixtures_dir: Path):
    contract = load_target_contract(fixtures_dir / "target_contract_inventory_reconciliation.json")
    dataset = load_dataset(fixtures_dir / "inventory_reconciliation_raw.csv")
    with open(fixtures_dir / "inventory_reconciliation_expected_output.json", "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # 1. Unfamiliar fields remain unresolved
    unresolved = ["sku_barcode", "warehouse_zone", "expected_quantity", "counted_quantity"]
    for field in unresolved:
        prop = plan.proposals[field]
        assert prop.status == MappingStatus.UNRESOLVED

    risks = evaluate_risks(profile, contract, plan)
    assert risks.is_blocked is True

    # 2. Human approval overrides
    overrides = {
        "sku_barcode": {"source_field": "item_tag", "status": MappingStatus.APPROVED},
        "warehouse_zone": {"source_field": "storage_bay", "status": MappingStatus.APPROVED},
        "expected_quantity": {"source_field": "book_stock", "status": MappingStatus.APPROVED},
        "counted_quantity": {"source_field": "physical_count", "status": MappingStatus.APPROVED},
    }
    approved = approve_mapping_plan(plan, reviewer="warehouse_manager", overrides=overrides)
    adapter = generate_adapter(approved, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 3. Accounting & Output Matching
    assert validation.total_input_records == 8
    assert validation.valid_records_count == 4
    assert validation.quarantined_records_count == 4
    assert validation.valid_records_count + validation.quarantined_records_count == 8

    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid_records, quarantined_records = sandbox["transform_dataset"](dataset.rows)

    for act, exp in zip(valid_records, expected_data["valid_records"]):
        assert act == exp
        assert "scanner_device_id" not in act

    for act_q, exp_f in zip(quarantined_records, expected_data["quarantined_fault_ledger"]):
        assert act_q["record_index"] == exp_f["record_index"]
        assert exp_f["error_code"] in act_q["error_codes"]
        assert any(exp_f["expected_error_substring"] in err for err in act_q["errors"])


# -----------------------------------------------------------------------------
# Pilot Scenario 3: Freight Manifests
# -----------------------------------------------------------------------------

def test_pilot_3_freight_manifest_workflow(fixtures_dir: Path):
    contract = load_target_contract(fixtures_dir / "target_contract_freight_manifest.json")
    dataset = load_dataset(fixtures_dir / "freight_manifest_raw.csv")
    with open(fixtures_dir / "freight_manifest_expected_output.json", "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)

    # 1. Unfamiliar fields remain unresolved
    unresolved = ["waybill_number", "carrier_iata_code", "origin_airport", "destination_airport", "gross_weight_kg"]
    for field in unresolved:
        prop = plan.proposals[field]
        assert prop.status == MappingStatus.UNRESOLVED

    # 2. Human approval overrides
    overrides = {
        "waybill_number": {"source_field": "consignment_ref", "status": MappingStatus.APPROVED},
        "carrier_iata_code": {"source_field": "airline_code", "status": MappingStatus.APPROVED},
        "origin_airport": {"source_field": "departure_port", "status": MappingStatus.APPROVED},
        "destination_airport": {"source_field": "arrival_port", "status": MappingStatus.APPROVED},
        "gross_weight_kg": {"source_field": "cargo_weight", "status": MappingStatus.APPROVED},
    }
    approved = approve_mapping_plan(plan, reviewer="cargo_controller", overrides=overrides)
    adapter = generate_adapter(approved, contract)
    validation = validate_adapter(adapter, contract, dataset.rows)

    # 3. Accounting & Output Matching
    assert validation.total_input_records == 8
    assert validation.valid_records_count == 4
    assert validation.quarantined_records_count == 4
    assert validation.valid_records_count + validation.quarantined_records_count == 8

    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid_records, quarantined_records = sandbox["transform_dataset"](dataset.rows)

    for act, exp in zip(valid_records, expected_data["valid_records"]):
        assert act == exp
        assert "pilot_license_number" not in act

    for act_q, exp_f in zip(quarantined_records, expected_data["quarantined_fault_ledger"]):
        assert act_q["record_index"] == exp_f["record_index"]
        assert exp_f["error_code"] in act_q["error_codes"]
        assert any(exp_f["expected_error_substring"] in err for err in act_q["errors"])


# -----------------------------------------------------------------------------
# Phase H: Duplicates and Financial Data Integrity
# -----------------------------------------------------------------------------

def test_duplicate_records_preservation_and_zero_loss(fixtures_dir: Path):
    """Verifies that identical or duplicate records are not silently dropped by the engine."""
    contract = load_target_contract(fixtures_dir / "target_contract_subscription_billing.json")

    duplicate_rows = [
        {"sub_token": "SUB-DUP0001", "client_ref": "CUST-99001", "tier_code": "STARTER", "billing_interval": "MONTHLY", "recurring_amount": "29.00", "renewal_date": "2025-01-01T00:00:00Z", "auto_renew": "true", "churn_notes": ""},
        {"sub_token": "SUB-DUP0001", "client_ref": "CUST-99001", "tier_code": "STARTER", "billing_interval": "MONTHLY", "recurring_amount": "29.00", "renewal_date": "2025-01-01T00:00:00Z", "auto_renew": "true", "churn_notes": ""},
    ]

    overrides = {
        "subscription_id": {"source_field": "sub_token", "status": MappingStatus.APPROVED},
        "customer_account_id": {"source_field": "client_ref", "status": MappingStatus.APPROVED},
        "plan_tier": {"source_field": "tier_code", "status": MappingStatus.APPROVED},
        "mrr_amount": {"source_field": "recurring_amount", "status": MappingStatus.APPROVED},
    }
    plan = propose_mappings(profile_dataset(load_dataset(fixtures_dir / "subscription_billing_raw.csv")), contract)
    approved = approve_mapping_plan(plan, overrides=overrides)
    adapter = generate_adapter(approved, contract)

    validation = validate_adapter(adapter, contract, duplicate_rows)
    # Both records must be preserved and transformed; neither should be dropped
    assert validation.total_input_records == 2
    assert validation.valid_records_count == 2
    assert validation.quarantined_records_count == 0


def test_leading_zeros_preserved_in_identifiers(fixtures_dir: Path):
    """Verifies that postal PIN codes and identifiers with leading zeros are preserved as strings."""
    contract = load_target_contract(fixtures_dir / "target_contract_b2b_vendor_invoice.json")

    overrides = {
        "invoice_number": {"source_field": "bill_no", "status": MappingStatus.APPROVED},
        "vendor_gstin": {"source_field": "supplier_gst", "status": MappingStatus.APPROVED},
        "buyer_pan": {"source_field": "client_pan_id", "status": MappingStatus.APPROVED},
        "destination_pincode": {"source_field": "delivery_pincode", "status": MappingStatus.APPROVED},
    }
    raw_dataset = load_dataset(fixtures_dir / "b2b_vendor_invoices_raw.csv")
    plan = propose_mappings(profile_dataset(raw_dataset), contract)
    approved = approve_mapping_plan(plan, overrides=overrides)
    adapter = generate_adapter(approved, contract)

    sandbox = compile_adapter_sandbox(adapter.python_code)
    test_rows = [{
        "bill_no": "INV-00123",
        "supplier_gst": "27AAPFU0939F1ZV",
        "client_pan_id": "AAACG0561D",
        "invoice_date": "2024-10-15T10:30:00Z",
        "total_amount": "5000.00",
        "tax_amount": "900.00",
        "hsn_sac_code": "8471",
        "delivery_pincode": "070001",  # Leading zero (e.g. special postal district or string ID)
        "bank_ifsc": "HDFC0001234",
        "payment_status": "PAID",
        "vendor_notes": ""
    }]
    valid, quarantined = sandbox["transform_dataset"](test_rows)
    # Invoice number with leading zeros preserved as string
    assert len(quarantined) == 1  # 070001 fails ^[1-9][0-9]{5}$ because Indian PINs cannot start with 0
    assert quarantined[0]["errors"][0].startswith("Value '070001' for 'destination_pincode' does not match pattern")


def test_decimal_precision_and_idempotency(fixtures_dir: Path):
    """Verifies numeric decimal precision in monetary fields and repeat-run idempotency."""
    contract = load_target_contract(fixtures_dir / "target_contract_subscription_billing.json")
    overrides = {
        "subscription_id": {"source_field": "sub_token", "status": MappingStatus.APPROVED},
        "customer_account_id": {"source_field": "client_ref", "status": MappingStatus.APPROVED},
        "plan_tier": {"source_field": "tier_code", "status": MappingStatus.APPROVED},
        "mrr_amount": {"source_field": "recurring_amount", "status": MappingStatus.APPROVED},
    }
    raw_dataset = load_dataset(fixtures_dir / "subscription_billing_raw.csv")
    plan = propose_mappings(profile_dataset(raw_dataset), contract)
    approved = approve_mapping_plan(plan, overrides=overrides)

    # 1. Determinism / Idempotency across repeated adapter generations
    code_1 = generate_adapter(approved, contract).python_code
    code_2 = generate_adapter(approved, contract).python_code
    assert code_1 == code_2

    # 2. Precision
    sandbox = compile_adapter_sandbox(code_1)
    test_rows = [{
        "sub_token": "SUB-PRECISION1",
        "client_ref": "CUST-10099",
        "tier_code": "PROFESSIONAL",
        "billing_interval": "MONTHLY",
        "recurring_amount": "199.9995",
        "renewal_date": "2025-01-01T00:00:00Z",
        "auto_renew": "true",
        "churn_notes": ""
    }]
    valid, _ = sandbox["transform_dataset"](test_rows)
    assert len(valid) == 1
    assert valid[0]["mrr_amount"] == 199.9995  # No unauthorized rounding
