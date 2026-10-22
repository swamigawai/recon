"""
Gate 19 Hardened Integration Benchmark Scenarios & Fixture Generator.
Builds 16 balanced scenarios:
- 10 Positive Hazard Scenarios (Fault Recall / Sensitivity)
- 6 Negative Conforming Scenarios (Specificity / False Alarm Avoidance)
Includes exact record-level content ground truth for value preservation auditing.
"""
import json
from pathlib import Path
import csv

BENCHMARK_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BENCHMARK_DIR / "fixtures"

def generate_gate19_scenarios():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = {}

    # =========================================================================
    # 1. POSITIVE HAZARDS (Expected Verdict: BLOCKED, ERROR, or QUARANTINE)
    # =========================================================================

    # Scenario 1: Missing Required Target Field (TP)
    c01 = {
        "contract_name": "g19_01_missing_required",
        "version": "1.0.0",
        "fields": {
            "invoice_id": {"name": "invoice_id", "target_type": "string", "required": True, "nullable": False},
            "total_amount": {"name": "total_amount", "target_type": "float", "required": True, "nullable": False},
            "issue_date": {"name": "issue_date", "target_type": "datetime", "required": True, "nullable": False}
        }
    }
    d01 = [
        {"gross_revenue": "100.50", "tx_timestamp": "2026-10-01T10:00:00Z"},
        {"gross_revenue": "200.75", "tx_timestamp": "2026-10-01T10:05:00Z"},
    ]
    gt01 = {
        "scenario_id": "g19_01_missing_required",
        "is_hazard_present": True,
        "hazard_category": "MISSING_REQUIRED_FIELD",
        "description": "Source dataset completely lacks mandatory invoice_id field.",
        "expected_verdict": "BLOCKED",
        "expected_blocker_rule": "R001_MISSING_REQUIRED_FIELD",
        "expected_unresolved_fields": ["invoice_id"],
        "total_input_records": 2,
        "should_generate_adapter": False,
    }

    # Scenario 2: Ambiguous Competing Source Columns (TP)
    c02 = {
        "contract_name": "g19_02_ambiguous_columns",
        "version": "1.0.0",
        "fields": {
            "order_ref": {"name": "order_ref", "target_type": "string", "required": True, "nullable": False},
            "postal_code": {"name": "postal_code", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d02 = [
        {"order_ref": "ORD001", "bill_to_zip": "10001", "ship_to_zip": "90210"},
        {"order_ref": "ORD002", "bill_to_zip": "10002", "ship_to_zip": "90211"},
    ]
    gt02 = {
        "scenario_id": "g19_02_ambiguous_columns",
        "is_hazard_present": True,
        "hazard_category": "AMBIGUOUS_MAPPING",
        "description": "Target postal_code has multiple candidate source columns (bill_to_zip vs ship_to_zip).",
        "expected_verdict": "REQUIRES_REVIEW",
        "expected_alternatives": ["bill_to_zip", "ship_to_zip"],
        "total_input_records": 2,
        "should_generate_adapter": True,  # Allowed once reviewer selects one
    }

    # Scenario 3: Incompatible Data Types (TP)
    c03 = {
        "contract_name": "g19_03_type_incompatibility",
        "version": "1.0.0",
        "fields": {
            "account_id": {"name": "account_id", "target_type": "string", "required": True, "nullable": False},
            "balance": {"name": "balance", "target_type": "float", "required": True, "nullable": False}
        }
    }
    d03 = [
        {"account_id": "ACC1", "balance": "150.25"},
        {"account_id": "ACC2", "balance": "PENDING_AUDIT"},  # Malformed float
        {"account_id": "ACC3", "balance": "999.99"},
        {"account_id": "ACC4", "balance": "N/A"},            # Malformed float
    ]
    gt03 = {
        "scenario_id": "g19_03_type_incompatibility",
        "is_hazard_present": True,
        "hazard_category": "TYPE_INCOMPATIBILITY",
        "description": "String values in required float field must be quarantined with ERR_TYPE_CONVERSION.",
        "expected_verdict": "QUARANTINE_PRESENT",
        "total_input_records": 4,
        "expected_valid_count": 2,
        "expected_quarantine_count": 2,
        "expected_quarantine_codes": ["ERR_TYPE_CONVERSION"],
        "expected_valid_records": [
            {"account_id": "ACC1", "balance": 150.25},
            {"account_id": "ACC3", "balance": 999.99},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 4: Strict Disallowed Enum Value (TP)
    c04 = {
        "contract_name": "g19_04_strict_enum_violation",
        "version": "1.0.0",
        "fields": {
            "user_id": {"name": "user_id", "target_type": "string", "required": True, "nullable": False},
            "account_status": {
                "name": "account_status",
                "target_type": "string",
                "required": True,
                "nullable": False,
                "allowed_values": ["ACTIVE", "SUSPENDED", "CLOSED"]
            }
        }
    }
    d04 = [
        {"user_id": "U1", "account_status": "ACTIVE"},
        {"user_id": "U2", "account_status": "ARCHIVED"},      # Illegal enum value
        {"user_id": "U3", "account_status": "CLOSED"},
    ]
    gt04 = {
        "scenario_id": "g19_04_strict_enum_violation",
        "is_hazard_present": True,
        "hazard_category": "ENUM_VIOLATION",
        "description": "Illegal enum state 'ARCHIVED' must be quarantined with ERR_ENUM_VIOLATION.",
        "expected_verdict": "QUARANTINE_PRESENT",
        "total_input_records": 3,
        "expected_valid_count": 2,
        "expected_quarantine_count": 1,
        "expected_quarantine_codes": ["ERR_ENUM_VIOLATION"],
        "expected_valid_records": [
            {"user_id": "U1", "account_status": "ACTIVE"},
            {"user_id": "U3", "account_status": "CLOSED"},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 9: Unsupported Schema Construct (TP)
    c09 = {
        "contract_name": "g19_09_unsupported_complex_schema",
        "version": "1.0.0",
        "fields": {
            "graph_node": {"name": "graph_node", "target_type": "deeply_nested_heterogeneous_graph", "required": True}
        }
    }
    gt09 = {
        "scenario_id": "g19_09_unsupported_complex_schema",
        "is_hazard_present": True,
        "hazard_category": "UNSUPPORTED_STRUCTURE",
        "description": "Unsupported contract construct must be caught by loader with explicit ContractError.",
        "expected_verdict": "ERROR",
        "expected_error_type": "ContractError",
        "total_input_records": 0,
        "should_generate_adapter": False,
    }

    # Scenario 10: Upstream Schema Drift (Added Required Field) (TP)
    c10 = {
        "contract_name": "g19_10_schema_drift",
        "version": "2.0.0",
        "fields": {
            "lead_id": {"name": "lead_id", "target_type": "string", "required": True, "nullable": False},
            "source_channel": {"name": "source_channel", "target_type": "string", "required": True, "nullable": False},
            "compliance_jurisdiction": {"name": "compliance_jurisdiction", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d10 = [
        {"lead_id": "LD901", "source_channel": "SEARCH"},
        {"lead_id": "LD902", "source_channel": "EMAIL"},
    ]
    gt10 = {
        "scenario_id": "g19_10_schema_drift",
        "is_hazard_present": True,
        "hazard_category": "SCHEMA_DRIFT",
        "description": "Contract v2 adds compliance_jurisdiction; unmapped mandatory field must block preflight.",
        "expected_verdict": "BLOCKED",
        "expected_blocker_rule": "R001_MISSING_REQUIRED_FIELD",
        "expected_unresolved_fields": ["compliance_jurisdiction"],
        "total_input_records": 2,
        "should_generate_adapter": False,
    }

    # Scenario 13: Mapping Collision (Two Target Fields Claim Same Source) (TP)
    c13 = {
        "contract_name": "g19_13_mapping_collision",
        "version": "1.0.0",
        "fields": {
            "billing_zip": {"name": "billing_zip", "target_type": "string", "required": True, "nullable": False},
            "shipping_zip": {"name": "shipping_zip", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d13 = [
        {"postal_code": "94103"},
        {"postal_code": "10001"},
    ]
    gt13 = {
        "scenario_id": "g19_13_mapping_collision",
        "is_hazard_present": True,
        "hazard_category": "MAPPING_COLLISION",
        "description": "Two distinct required target fields mapped to the single source column 'postal_code'.",
        "expected_verdict": "RISK_FLAGGED",
        "expected_risk_rule": "R008_MAPPING_COLLISION",
        "total_input_records": 2,
        "should_generate_adapter": True,
    }

    # Scenario 14: Regex Pattern Violation (TP)
    c14 = {
        "contract_name": "g19_14_regex_pattern_violation",
        "version": "1.0.0",
        "fields": {
            "tax_id": {
                "name": "tax_id",
                "target_type": "string",
                "required": True,
                "nullable": False,
                "pattern": "^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
            }
        }
    }
    d14 = [
        {"tax_id": "27AAPFU0939F1ZV"},  # Valid 15-char Indian GSTIN
        {"tax_id": "INVALID_GSTIN_123"}, # Pattern violation
    ]
    gt14 = {
        "scenario_id": "g19_14_regex_pattern_violation",
        "is_hazard_present": True,
        "hazard_category": "PATTERN_VIOLATION",
        "description": "Invalid format violating regex pattern must be quarantined with ERR_PATTERN_VIOLATION.",
        "expected_verdict": "QUARANTINE_PRESENT",
        "total_input_records": 2,
        "expected_valid_count": 1,
        "expected_quarantine_count": 1,
        "expected_quarantine_codes": ["ERR_PATTERN_VIOLATION"],
        "expected_valid_records": [{"tax_id": "27AAPFU0939F1ZV"}],
        "should_generate_adapter": True,
    }

    # Scenario 16: Non-Nullable Field Null Violation (TP)
    c16 = {
        "contract_name": "g19_16_non_nullable_violation",
        "version": "1.0.0",
        "fields": {
            "device_id": {"name": "device_id", "target_type": "string", "required": True, "nullable": False},
            "sensor_reading": {"name": "sensor_reading", "target_type": "float", "required": True, "nullable": False}
        }
    }
    d16 = [
        {"device_id": "DEV01", "sensor_reading": "24.5"},
        {"device_id": "DEV02", "sensor_reading": None},  # Null in non-nullable field
        {"device_id": "DEV03", "sensor_reading": "26.1"},
    ]
    gt16 = {
        "scenario_id": "g19_16_non_nullable_violation",
        "is_hazard_present": True,
        "hazard_category": "NULL_VIOLATION",
        "description": "Null passed into required non-nullable float must be quarantined with ERR_REQUIRED_FIELD_MISSING.",
        "expected_verdict": "QUARANTINE_PRESENT",
        "total_input_records": 3,
        "expected_valid_count": 2,
        "expected_quarantine_count": 1,
        "expected_quarantine_codes": ["ERR_REQUIRED_FIELD_MISSING"],
        "expected_valid_records": [
            {"device_id": "DEV01", "sensor_reading": 24.5},
            {"device_id": "DEV03", "sensor_reading": 26.1},
        ],
        "should_generate_adapter": True,
    }

    # =========================================================================
    # 2. CONFORMING & NEGATIVE SCENARIOS (Expected Verdict: PASS, 0 FP)
    # =========================================================================

    # Scenario 5: Leading-Zero String Identifiers (TN)
    c05 = {
        "contract_name": "g19_05_leading_zero_preservation",
        "version": "1.0.0",
        "fields": {
            "employee_pin": {"name": "employee_pin", "target_type": "string", "required": True, "nullable": False, "pattern": "^[0-9]{5}$"},
            "dept": {"name": "dept", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d05 = [
        {"employee_pin": "00142", "dept": "SECURITY"},
        {"employee_pin": "00007", "dept": "OPS"},
        {"employee_pin": "09876", "dept": "FINANCE"},
    ]
    gt05 = {
        "scenario_id": "g19_05_leading_zero_preservation",
        "is_hazard_present": False,
        "hazard_category": "CONFORMING_LEADING_ZEROS",
        "description": "5-digit codes with leading zeros must be preserved as exact strings without truncation.",
        "expected_verdict": "PASS",
        "total_input_records": 3,
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"employee_pin": "00142", "dept": "SECURITY"},
            {"employee_pin": "00007", "dept": "OPS"},
            {"employee_pin": "09876", "dept": "FINANCE"},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 6: High Decimal Precision (TN)
    c06 = {
        "contract_name": "g19_06_high_precision_decimals",
        "version": "1.0.0",
        "fields": {
            "pair": {"name": "pair", "target_type": "string", "required": True, "nullable": False},
            "interest_rate": {"name": "interest_rate", "target_type": "float", "required": True, "nullable": False}
        }
    }
    d06 = [
        {"pair": "USD_JPY", "interest_rate": "0.0000123456789"},
        {"pair": "EUR_CHF", "interest_rate": "99999999.987654321"},
    ]
    gt06 = {
        "scenario_id": "g19_06_high_precision_decimals",
        "is_hazard_present": False,
        "hazard_category": "CONFORMING_PRECISION",
        "description": "High precision decimal floats must preserve exact numerical value without rounding loss.",
        "expected_verdict": "PASS",
        "total_input_records": 2,
        "expected_valid_count": 2,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"pair": "USD_JPY", "interest_rate": 0.0000123456789},
            {"pair": "EUR_CHF", "interest_rate": 99999999.987654321},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 7: Duplicate Records Handling (TN)
    c07 = {
        "contract_name": "g19_07_duplicate_preservation",
        "version": "1.0.0",
        "fields": {
            "event_id": {"name": "event_id", "target_type": "string", "required": True, "nullable": False},
            "status": {"name": "status", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d07 = [
        {"event_id": "EVT100", "status": "OK"},
        {"event_id": "EVT100", "status": "OK"},  # Exact Duplicate
        {"event_id": "EVT101", "status": "OK"},
    ]
    gt07 = {
        "scenario_id": "g19_07_duplicate_preservation",
        "is_hazard_present": False,
        "hazard_category": "CONFORMING_DUPLICATES",
        "description": "Duplicate rows must be detected during profiling but preserved during transformation.",
        "expected_verdict": "PASS",
        "expected_duplicates_profiled": 1,
        "total_input_records": 3,
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"event_id": "EVT100", "status": "OK"},
            {"event_id": "EVT100", "status": "OK"},
            {"event_id": "EVT101", "status": "OK"},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 8: Nested Dotted Namespace Fields (TN)
    c08 = {
        "contract_name": "g19_08_supported_dotted_nested",
        "version": "1.0.0",
        "fields": {
            "customer.id": {"name": "customer.id", "target_type": "string", "required": True, "nullable": False},
            "customer.email": {"name": "customer.email", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d08 = [
        {"customer.id": "CUST_01", "customer.email": "c1@example.com"},
        {"customer.id": "CUST_02", "customer.email": "c2@example.com"},
    ]
    gt08 = {
        "scenario_id": "g19_08_supported_dotted_nested",
        "is_hazard_present": False,
        "hazard_category": "CONFORMING_DOTTED_FIELDS",
        "description": "Supported dotted field namespaces must map and transform without Python syntax errors.",
        "expected_verdict": "PASS",
        "total_input_records": 2,
        "expected_valid_count": 2,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"customer.id": "CUST_01", "customer.email": "c1@example.com"},
            {"customer.id": "CUST_02", "customer.email": "c2@example.com"},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 11: Completely Clean Conforming Dataset (TN)
    c11 = {
        "contract_name": "g19_11_clean_conforming",
        "version": "1.0.0",
        "fields": {
            "ticket_id": {"name": "ticket_id", "target_type": "string", "required": True, "nullable": False},
            "priority": {"name": "priority", "target_type": "string", "required": True, "nullable": False, "allowed_values": ["LOW", "HIGH"]},
            "created_at": {"name": "created_at", "target_type": "datetime", "required": True, "nullable": False}
        }
    }
    d11 = [
        {"ticket_id": "TCK1", "priority": "HIGH", "created_at": "2026-10-01T12:00:00Z"},
        {"ticket_id": "TCK2", "priority": "LOW", "created_at": "2026-10-01T12:05:00Z"},
        {"ticket_id": "TCK3", "priority": "HIGH", "created_at": "2026-10-01T12:10:00Z"},
    ]
    gt11 = {
        "scenario_id": "g19_11_clean_conforming",
        "is_hazard_present": False,
        "hazard_category": "CLEAN_CONFORMING",
        "description": "Standard conforming data must pass with 0 false alarms, exit code 0, and 100% valid records.",
        "expected_verdict": "PASS",
        "total_input_records": 3,
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"ticket_id": "TCK1", "priority": "HIGH", "created_at": "2026-10-01T12:00:00Z"},
            {"ticket_id": "TCK2", "priority": "LOW", "created_at": "2026-10-01T12:05:00Z"},
            {"ticket_id": "TCK3", "priority": "HIGH", "created_at": "2026-10-01T12:10:00Z"},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 12: Unusual Valid Data (Unicode & Whitespace Padding) (TN)
    c12 = {
        "contract_name": "g19_12_unicode_and_whitespace",
        "version": "1.0.0",
        "fields": {
            "user_id": {"name": "user_id", "target_type": "string", "required": True, "nullable": False},
            "location_name": {"name": "location_name", "target_type": "string", "required": True, "nullable": False}
        }
    }
    d12 = [
        {"user_id": "  U101  ", "location_name": "München"},
        {"user_id": "U102", "location_name": "東京 🚀"},
        {"user_id": " U103 ", "location_name": "مرحبا"},
    ]
    gt12 = {
        "scenario_id": "g19_12_unicode_and_whitespace",
        "is_hazard_present": False,
        "hazard_category": "CONFORMING_UNICODE_WHITESPACE",
        "description": "Multilingual Unicode and padded strings must be stripped and preserved without false alarms.",
        "expected_verdict": "PASS",
        "total_input_records": 3,
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"user_id": "U101", "location_name": "München"},
            {"user_id": "U102", "location_name": "東京 🚀"},
            {"user_id": "U103", "location_name": "مرحبا"},
        ],
        "should_generate_adapter": True,
    }

    # Scenario 15: Nullable Field Null Tolerance (TN)
    c15 = {
        "contract_name": "g19_15_nullable_tolerance",
        "version": "1.0.0",
        "fields": {
            "item_id": {"name": "item_id", "target_type": "string", "required": True, "nullable": False},
            "discount_notes": {"name": "discount_notes", "target_type": "string", "required": False, "nullable": True}
        }
    }
    d15 = [
        {"item_id": "ITM1", "discount_notes": "VIP Client"},
        {"item_id": "ITM2", "discount_notes": None},
        {"item_id": "ITM3", "discount_notes": "NULL"},
    ]
    gt15 = {
        "scenario_id": "g19_15_nullable_tolerance",
        "is_hazard_present": False,
        "hazard_category": "CONFORMING_NULLABLE",
        "description": "Nullable optional field receiving nulls must transform cleanly without quarantine.",
        "expected_verdict": "PASS",
        "total_input_records": 3,
        "expected_valid_count": 3,
        "expected_quarantine_count": 0,
        "expected_valid_records": [
            {"item_id": "ITM1", "discount_notes": "VIP Client"},
            {"item_id": "ITM2", "discount_notes": None},
            {"item_id": "ITM3", "discount_notes": None},
        ],
        "should_generate_adapter": True,
    }

    all_scenarios = [
        ("g19_01_missing_required", c01, d01, gt01),
        ("g19_02_ambiguous_columns", c02, d02, gt02),
        ("g19_03_type_incompatibility", c03, d03, gt03),
        ("g19_04_strict_enum_violation", c04, d04, gt04),
        ("g19_05_leading_zero_preservation", c05, d05, gt05),
        ("g19_06_high_precision_decimals", c06, d06, gt06),
        ("g19_07_duplicate_preservation", c07, d07, gt07),
        ("g19_08_supported_dotted_nested", c08, d08, gt08),
        ("g19_09_unsupported_complex_schema", c09, None, gt09),
        ("g19_10_schema_drift", c10, d10, gt10),
        ("g19_11_clean_conforming", c11, d11, gt11),
        ("g19_12_unicode_and_whitespace", c12, d12, gt12),
        ("g19_13_mapping_collision", c13, d13, gt13),
        ("g19_14_regex_pattern_violation", c14, d14, gt14),
        ("g19_15_nullable_tolerance", c15, d15, gt15),
        ("g19_16_non_nullable_violation", c16, d16, gt16),
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

            csv_path = FIXTURES_DIR / f"{s_id}_data.csv"
            if dataset:
                headers = list(dataset[0].keys())
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    for r in dataset:
                        writer.writerow(r)

        scenarios[s_id] = gt

    gt_path = BENCHMARK_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2)

    print(f"Generated {len(all_scenarios)} Gate 19 benchmark scenarios in {FIXTURES_DIR}")

if __name__ == "__main__":
    generate_gate19_scenarios()
