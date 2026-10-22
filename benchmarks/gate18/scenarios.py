"""
Scenarios and fixture generator for Recon Gate 18 Benchmark.
Builds 11 realistic, synthetic integration scenarios with independent ground truth.
"""
import json
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BENCHMARK_DIR / "fixtures"

def generate_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    scenarios = {}
    
    # -------------------------------------------------------------
    # Scenario 01: Missing Required Field
    # -------------------------------------------------------------
    contract_01 = {
        "contract_name": "s01_missing_required",
        "version": "1.0.0",
        "fields": {
            "transaction_id": {"name": "transaction_id", "target_type": "string", "required": True, "nullable": False},
            "amount": {"name": "amount", "target_type": "float", "required": True, "nullable": False},
            "timestamp": {"name": "timestamp", "target_type": "datetime", "required": True, "nullable": False}
        }
    }
    data_01 = [
        {"gross_amount": "150.00", "created_date": "2026-10-01T10:00:00Z"},
        {"gross_amount": "250.50", "created_date": "2026-10-01T10:05:00Z"},
        {"gross_amount": "99.99", "created_date": "2026-10-01T10:10:00Z"},
        {"gross_amount": "12.00", "created_date": "2026-10-01T10:15:00Z"},
        {"gross_amount": "500.00", "created_date": "2026-10-01T10:20:00Z"},
    ]
    gt_01 = {
        "scenario_id": "s01_missing_required",
        "description": "Source dataset completely lacks mandatory transaction_id field.",
        "hazard_type": "MISSING_REQUIRED_FIELD",
        "expected_preflight_verdict": "BLOCKED",
        "expected_unmapped_required": ["transaction_id"],
        "expected_valid_count": 0,
        "expected_quarantine_count": 5,
        "total_records": 5,
    }
    
    # -------------------------------------------------------------
    # Scenario 02: Ambiguous Field Mappings
    # -------------------------------------------------------------
    contract_02 = {
        "contract_name": "s02_ambiguous_mapping",
        "version": "1.0.0",
        "fields": {
            "customer_id": {"name": "customer_id", "target_type": "string", "required": True, "nullable": False},
            "postal_code": {"name": "postal_code", "target_type": "string", "required": True, "nullable": False}
        }
    }
    data_02 = [
        {"customer_id": "CUST01", "billing_postal_code": "10001", "shipping_postal_code": "90210"},
        {"customer_id": "CUST02", "billing_postal_code": "10002", "shipping_postal_code": "90211"},
        {"customer_id": "CUST03", "billing_postal_code": "10003", "shipping_postal_code": "90212"},
    ]
    gt_02 = {
        "scenario_id": "s02_ambiguous_mapping",
        "description": "Source data provides multiple candidate postal codes (billing vs shipping).",
        "hazard_type": "AMBIGUOUS_MAPPING",
        "expected_preflight_verdict": "BLOCKED",
        "expected_ambiguous_target": ["postal_code"],
        "total_records": 3
    }
    
    # -------------------------------------------------------------
    # Scenario 03: Incompatible Data Types
    # -------------------------------------------------------------
    contract_03 = {
        "contract_name": "s03_incompatible_types",
        "version": "1.0.0",
        "fields": {
            "account_id": {"name": "account_id", "target_type": "string", "required": True, "nullable": False},
            "balance": {"name": "balance", "target_type": "float", "required": True, "nullable": False}
        }
    }
    data_03 = [
        {"account_id": "ACC1", "balance": "150.25"},
        {"account_id": "ACC2", "balance": "0.0"},
        {"account_id": "ACC3", "balance": "999.99"},
        {"account_id": "ACC4", "balance": "PENDING_AUDIT"},  # Malformed float
        {"account_id": "ACC5", "balance": "N/A"},            # Malformed float
    ]
    gt_03 = {
        "scenario_id": "s03_incompatible_types",
        "description": "Non-numeric string values in mandatory float column.",
        "hazard_type": "TYPE_INCOMPATIBILITY",
        "expected_valid_count": 3,
        "expected_quarantine_count": 2,
        "total_records": 5,
        "expected_quarantine_codes": ["ERR_TYPE_CONVERSION"]
    }

    # -------------------------------------------------------------
    # Scenario 04: Enum and Normalization Mismatches
    # -------------------------------------------------------------
    contract_04 = {
        "contract_name": "s04_enum_mismatch",
        "version": "1.0.0",
        "fields": {
            "order_id": {"name": "order_id", "target_type": "string", "required": True, "nullable": False},
            "order_status": {
                "name": "order_status",
                "target_type": "string",
                "required": True,
                "nullable": False,
                "allowed_values": ["COMPLETED", "CANCELLED", "ON_HOLD"]
            }
        }
    }
    data_04 = [
        {"order_id": "ORD01", "order_status": "COMPLETED"},
        {"order_id": "ORD02", "order_status": "completed"},   # Case mismatch
        {"order_id": "ORD03", "order_status": "CANCELLED"},
        {"order_id": "ORD04", "order_status": "REFUNDED"},    # Disallowed enum
        {"order_id": "ORD05", "order_status": "ON_HOLD"},
    ]
    gt_04 = {
        "scenario_id": "s04_enum_mismatch",
        "description": "Casing differences and disallowed enum states in status field.",
        "hazard_type": "ENUM_VIOLATION",
        "expected_valid_count": 3,  # ORD01, ORD03, ORD05
        "expected_quarantine_count": 2, # ORD02 (lowercase), ORD04 (disallowed)
        "total_records": 5,
        "expected_quarantine_codes": ["ERR_ENUM_VIOLATION"]
    }

    # -------------------------------------------------------------
    # Scenario 05: Leading-Zero Identifiers
    # -------------------------------------------------------------
    contract_05 = {
        "contract_name": "s05_leading_zeros",
        "version": "1.0.0",
        "fields": {
            "badge_code": {"name": "badge_code", "target_type": "string", "required": True, "nullable": False, "pattern": "^[0-9]{5}$"},
            "employee_name": {"name": "employee_name", "target_type": "string", "required": True, "nullable": False}
        }
    }
    data_05 = [
        {"badge_code": "00123", "employee_name": "Alice"},
        {"badge_code": "09876", "employee_name": "Bob"},
        {"badge_code": "00001", "employee_name": "Charlie"},
        {"badge_code": "00042", "employee_name": "David"},
    ]
    gt_05 = {
        "scenario_id": "s05_leading_zeros",
        "description": "5-digit postal or badge codes with leading zeros must not be cast to integers.",
        "hazard_type": "LEADING_ZERO_TRUNCATION",
        "expected_valid_count": 4,
        "expected_quarantine_count": 0,
        "total_records": 4,
        "expected_string_values": ["00123", "09876", "00001", "00042"]
    }

    # -------------------------------------------------------------
    # Scenario 06: Decimal Precision
    # -------------------------------------------------------------
    contract_06 = {
        "contract_name": "s06_decimal_precision",
        "version": "1.0.0",
        "fields": {
            "asset_id": {"name": "asset_id", "target_type": "string", "required": True, "nullable": False},
            "exchange_rate": {"name": "exchange_rate", "target_type": "float", "required": True, "nullable": False}
        }
    }
    data_06 = [
        {"asset_id": "EUR_USD", "exchange_rate": "1.082456"},
        {"asset_id": "BTC_USD", "exchange_rate": "0.00001234"},
        {"asset_id": "WHALE_ACC", "exchange_rate": "99999999.98765432"},
    ]
    gt_06 = {
        "scenario_id": "s06_decimal_precision",
        "description": "High-precision financial floats must not suffer premature rounding truncation.",
        "hazard_type": "PRECISION_LOSS",
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "total_records": 3,
        "expected_float_values": [1.082456, 0.00001234, 99999999.98765432]
    }

    # -------------------------------------------------------------
    # Scenario 07: Duplicate Records
    # -------------------------------------------------------------
    contract_07 = {
        "contract_name": "s07_duplicate_records",
        "version": "1.0.0",
        "fields": {
            "user_id": {"name": "user_id", "target_type": "string", "required": True, "nullable": False},
            "email": {"name": "email", "target_type": "string", "required": True, "nullable": False}
        }
    }
    data_07 = [
        {"user_id": "USR001", "email": "alice@example.com"},
        {"user_id": "USR001", "email": "alice@example.com"},  # Exact Duplicate
        {"user_id": "USR002", "email": "bob@example.com"},
        {"user_id": "USR003", "email": "charlie@example.com"},
    ]
    gt_07 = {
        "scenario_id": "s07_duplicate_records",
        "description": "Duplicate rows must be detected during profiling without being silently dropped.",
        "hazard_type": "DUPLICATE_RECORDS",
        "expected_duplicates_profiled": 1,
        "expected_valid_count": 4,
        "expected_quarantine_count": 0,
        "total_records": 4
    }

    # -------------------------------------------------------------
    # Scenario 08: Nested Contract Dotted Fields
    # -------------------------------------------------------------
    contract_08 = {
        "contract_name": "s08_nested_dotted",
        "version": "1.0.0",
        "fields": {
            "meta.source_system": {"name": "meta.source_system", "target_type": "string", "required": True, "nullable": False},
            "payload.user_id": {"name": "payload.user_id", "target_type": "string", "required": True, "nullable": False}
        }
    }
    data_08 = [
        {"meta.source_system": "SAP_ERP", "payload.user_id": "U100"},
        {"meta.source_system": "ORACLE_FIN", "payload.user_id": "U101"},
        {"meta.source_system": "NETSUITE", "payload.user_id": "U102"},
    ]
    gt_08 = {
        "scenario_id": "s08_nested_dotted",
        "description": "Supported dotted field namespaces for nested target payloads.",
        "hazard_type": "SUPPORTED_NESTED_STRUCTURE",
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "total_records": 3
    }

    # -------------------------------------------------------------
    # Scenario 09: Unsupported Deep Complex Structure
    # -------------------------------------------------------------
    contract_09_invalid = {
        "contract_name": "s09_unsupported_complex",
        "version": "1.0.0",
        "fields": {
            "items": {"name": "items", "target_type": "array_of_arbitrary_objects", "required": True}
        }
    }
    gt_09 = {
        "scenario_id": "s09_unsupported_complex",
        "description": "Unsupported schema constructs must trigger clear ContractError diagnostics.",
        "hazard_type": "UNSUPPORTED_STRUCTURE",
        "expected_preflight_verdict": "ERROR",
        "expected_error_diagnostic": "Invalid target_type"
    }

    # -------------------------------------------------------------
    # Scenario 10: Upstream Schema Drift (Contract Evolution)
    # -------------------------------------------------------------
    # Contract v1: had ticket_id, priority
    # Contract v2: adds mandatory regulatory_code
    contract_10_v2 = {
        "contract_name": "s10_schema_drift",
        "version": "2.0.0",
        "fields": {
            "ticket_id": {"name": "ticket_id", "target_type": "string", "required": True, "nullable": False},
            "priority": {"name": "priority", "target_type": "string", "required": True, "nullable": False},
            "regulatory_code": {"name": "regulatory_code", "target_type": "string", "required": True, "nullable": False}
        }
    }
    data_10_legacy = [
        {"ticket_id": "TCK01", "priority": "HIGH"},
        {"ticket_id": "TCK02", "priority": "LOW"},
    ]
    gt_10 = {
        "scenario_id": "s10_schema_drift",
        "description": "Previously working integration breaks when upstream contract adds required field.",
        "hazard_type": "SCHEMA_DRIFT",
        "expected_preflight_verdict": "BLOCKED",
        "expected_unmapped_required": ["regulatory_code"],
        "total_records": 2
    }

    # -------------------------------------------------------------
    # Scenario 11: Clean Valid Conforming Records
    # -------------------------------------------------------------
    contract_11 = {
        "contract_name": "s11_clean_valid",
        "version": "1.0.0",
        "fields": {
            "ticket_id": {"name": "ticket_id", "target_type": "string", "required": True, "nullable": False},
            "priority": {"name": "priority", "target_type": "string", "required": True, "nullable": False, "allowed_values": ["LOW", "HIGH"]},
            "created_at": {"name": "created_at", "target_type": "datetime", "required": True, "nullable": False}
        }
    }
    data_11 = [
        {"ticket_id": "TCK100", "priority": "HIGH", "created_at": "2026-10-01T12:00:00Z"},
        {"ticket_id": "TCK101", "priority": "LOW", "created_at": "2026-10-01T12:05:00Z"},
        {"ticket_id": "TCK102", "priority": "HIGH", "created_at": "2026-10-01T12:10:00Z"},
        {"ticket_id": "TCK103", "priority": "LOW", "created_at": "2026-10-01T12:15:00Z"},
        {"ticket_id": "TCK104", "priority": "HIGH", "created_at": "2026-10-01T12:20:00Z"},
    ]
    gt_11 = {
        "scenario_id": "s11_clean_valid",
        "description": "Completely conforming dataset must pass with 0 false alarms and exit code 0.",
        "hazard_type": "CLEAN_CONFORMING",
        "expected_preflight_verdict": "PASS",
        "expected_valid_count": 5,
        "expected_quarantine_count": 0,
        "total_records": 5
    }

    all_scenarios = [
        ("s01_missing_required", contract_01, data_01, gt_01),
        ("s02_ambiguous_mapping", contract_02, data_02, gt_02),
        ("s03_incompatible_types", contract_03, data_03, gt_03),
        ("s04_enum_mismatch", contract_04, data_04, gt_04),
        ("s05_leading_zeros", contract_05, data_05, gt_05),
        ("s06_decimal_precision", contract_06, data_06, gt_06),
        ("s07_duplicate_records", contract_07, data_07, gt_07),
        ("s08_nested_dotted", contract_08, data_08, gt_08),
        ("s09_unsupported_complex", contract_09_invalid, None, gt_09),
        ("s10_schema_drift", contract_10_v2, data_10_legacy, gt_10),
        ("s11_clean_valid", contract_11, data_11, gt_11),
    ]

    for s_id, contract_def, dataset, gt in all_scenarios:
        # Save contract
        contract_path = FIXTURES_DIR / f"{s_id}_contract.json"
        with open(contract_path, "w", encoding="utf-8") as f:
            json.dump(contract_def, f, indent=2)
            
        # Save dataset (if applicable)
        if dataset is not None:
            data_path = FIXTURES_DIR / f"{s_id}_data.json"
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=2)
                
            # Also save as CSV for CLI testing
            csv_path = FIXTURES_DIR / f"{s_id}_data.csv"
            if dataset:
                headers = list(dataset[0].keys())
                import csv
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    for r in dataset:
                        writer.writerow(r)

        scenarios[s_id] = gt

    gt_path = BENCHMARK_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2)

    print(f"Generated {len(all_scenarios)} benchmark scenarios in {FIXTURES_DIR}")

if __name__ == "__main__":
    generate_fixtures()
