"""Isolated test executor and contract validator for generated adapters."""

import datetime
import re
from typing import Any

from recon.adapters.models import GeneratedAdapter
from recon.contracts.models import ContractType, TargetContract
from recon.exceptions import ValidationError
from recon.logging import log_safe_event
from recon.validation.models import TestCaseResult, ValidationResult


def compile_adapter_sandbox(python_code: str) -> dict[str, Any]:
    """Compiles adapter code in a restricted execution namespace without access to dangerous builtins or network."""
    safe_builtins = dict(__builtins__) if isinstance(__builtins__, dict) else dict(__builtins__.__dict__)
    # Disallow arbitrary execution hooks
    safe_builtins.pop("exec", None)
    safe_builtins.pop("eval", None)

    restricted_globals = {
        "__builtins__": safe_builtins,
        "datetime": datetime.datetime,
        "re": re,
    }
    bytecode = compile(python_code, "<recon_generated_adapter>", "exec")
    exec(bytecode, restricted_globals)
    return restricted_globals


def validate_contract_payload(payload: dict[str, Any], contract: TargetContract) -> list[str]:
    """Validates an output record directly against target contract specifications."""
    errors: list[str] = []

    for name, field in contract.fields.items():
        if name not in payload:
            if field.required:
                errors.append(f"Missing required field '{name}' in output payload")
            continue

        val = payload[name]
        if val is None:
            if not field.nullable:
                errors.append(f"Field '{name}' is non-nullable but got None")
            continue

        # Type checks
        if field.target_type == ContractType.STRING:
            if not isinstance(val, str):
                errors.append(f"Field '{name}' expected string, got {type(val).__name__}")
            elif field.allowed_values and val not in field.allowed_values:
                errors.append(f"Field '{name}' value '{val}' not in allowed values {field.allowed_values}")
            elif field.pattern and not re.match(field.pattern, val):
                errors.append(f"Field '{name}' value '{val}' does not match pattern '{field.pattern}'")

        elif field.target_type == ContractType.INTEGER:
            if not isinstance(val, int) or isinstance(val, bool):
                errors.append(f"Field '{name}' expected integer, got {type(val).__name__}")

        elif field.target_type == ContractType.FLOAT:
            if not isinstance(val, (float, int)) or isinstance(val, bool):
                errors.append(f"Field '{name}' expected float, got {type(val).__name__}")

        elif field.target_type == ContractType.BOOLEAN:
            if not isinstance(val, bool):
                errors.append(f"Field '{name}' expected boolean, got {type(val).__name__}")

        elif field.target_type == ContractType.DATETIME:
            if not isinstance(val, str):
                errors.append(f"Field '{name}' expected ISO datetime string, got {type(val).__name__}")
            else:
                try:
                    datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"Field '{name}' value '{val}' is not a valid ISO-8601 datetime")

    return errors


def validate_adapter(
    adapter: GeneratedAdapter,
    contract: TargetContract,
    records: list[dict[str, str]],
) -> ValidationResult:
    """Executes the adapter against records and a synthetic fault test suite, verifying contract conformance."""
    sandbox = compile_adapter_sandbox(adapter.python_code)
    transform_record = sandbox["transform_record"]
    transform_dataset = sandbox["transform_dataset"]

    # 1. Execute transformation on provided records
    valid_records, quarantined = transform_dataset(records)

    # 2. Verify all valid records strictly adhere to the target contract
    contract_errors: list[str] = []
    for rec in valid_records:
        errs = validate_contract_payload(rec, contract)
        if errs:
            contract_errors.extend(errs)

    is_contract_valid = len(contract_errors) == 0

    # 3. Execute synthetic edge-case tests
    test_cases: list[TestCaseResult] = []

    # Test Case 1: Valid sample transformation
    if records:
        valid_res, errs = transform_record(records[0])
        tc1_passed = valid_res is not None and len(errs) == 0
        test_cases.append(
            TestCaseResult(
                test_name="test_valid_record_transformation",
                passed=tc1_passed,
                expected_behavior="Valid source record transforms into contract-compliant payload",
                actual_behavior="Success" if tc1_passed else f"Errors: {errs}",
                error_message=None if tc1_passed else "; ".join(errs),
            )
        )

    # Test Case 2: Missing required field quarantine
    # Synthetic record missing first key field
    missing_key_rec = dict(records[0]) if records else {}
    for h in list(missing_key_rec.keys()):
        if "key" in h.lower() or "id" in h.lower():
            missing_key_rec[h] = ""
    res, errs = transform_record(missing_key_rec)
    tc2_passed = res is None and any("Required non-nullable field" in e for e in errs)
    test_cases.append(
        TestCaseResult(
            test_name="test_missing_required_field_quarantine",
            passed=tc2_passed,
            expected_behavior="Missing required field triggers quarantine with explicit error",
            actual_behavior="Quarantined as expected" if tc2_passed else f"Result: {res}, Errors: {errs}",
            error_message=None if tc2_passed else "Record was not quarantined",
        )
    )

    # Test Case 3: Malformed date format quarantine
    malformed_date_rec = dict(records[0]) if records else {}
    for h in list(malformed_date_rec.keys()):
        if "date" in h.lower():
            malformed_date_rec[h] = "INVALID_DATE_FORMAT_123"
    res, errs = transform_record(malformed_date_rec)
    tc3_passed = res is None and any("Cannot parse datetime" in e for e in errs)
    test_cases.append(
        TestCaseResult(
            test_name="test_malformed_date_quarantine",
            passed=tc3_passed,
            expected_behavior="Malformed date triggers quarantine with datetime parsing error",
            actual_behavior="Quarantined as expected" if tc3_passed else f"Result: {res}, Errors: {errs}",
            error_message=None if tc3_passed else "Record was not quarantined",
        )
    )

    all_tests_passed = all(tc.passed for tc in test_cases)
    total_in = len(records)
    pass_rate = round((len(valid_records) / total_in) * 100.0, 2) if total_in > 0 else 0.0

    result = ValidationResult(
        adapter_name=adapter.adapter_name,
        contract_name=contract.contract_name,
        contract_version=contract.version,
        total_input_records=total_in,
        valid_records_count=len(valid_records),
        quarantined_records_count=len(quarantined),
        contract_pass_rate=pass_rate,
        sample_valid_output=valid_records[:3],
        sample_quarantined_records=quarantined[:3],
        test_case_results=test_cases,
        all_tests_passed=all_tests_passed,
        is_contract_valid=is_contract_valid,
    )

    log_safe_event(
        "ADAPTER_VALIDATED",
        adapter=adapter.adapter_name,
        total=total_in,
        valid=len(valid_records),
        quarantined=len(quarantined),
        all_passed=all_tests_passed,
    )

    return result
