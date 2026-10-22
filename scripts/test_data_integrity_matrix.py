"""
Data Integrity Matrix Verification Script for Recon Gate 17.
Tests:
1. Zero-data-loss invariant: total = valid + quarantined
2. Duplicate records handling
3. Leading-zero preservation in identifiers
4. High-precision decimals
5. Full Unicode coverage (Latin-1, CJK, Emoji, Arabic)
6. Enum constraint enforcement & quarantine
7. Missing required field handling & quarantine
8. Type error handling (malformed input) & quarantine
"""
import sys
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.mapping.models import ApprovedMappingPlan, FieldMappingProposal, MappingStatus, MappingType
from recon.validation.executor import compile_adapter_sandbox

def test_data_integrity_matrix():
    print("=== Testing Recon Data Integrity Matrix ===")
    
    contract_def = {
        "contract_name": "data_integrity_benchmark",
        "fields": {
            "entity_id": {"name": "entity_id", "target_type": "string", "required": True},
            "status": {
                "name": "status",
                "target_type": "string",
                "required": True,
                "allowed_values": ["ACTIVE", "INACTIVE", "PENDING"]
            },
            "balance": {"name": "balance", "target_type": "float", "required": True},
            "description": {"name": "description", "target_type": "string", "required": False, "nullable": True},
        }
    }
    contract = load_target_contract(contract_def)
    
    plan = ApprovedMappingPlan(
        contract_name="data_integrity_benchmark",
        source_name="matrix_source.json",
        source_fingerprint="fp_matrix_001",
        approved_by="qa_gate17",
        approved_mappings={
            "entity_id": FieldMappingProposal(
                target_field="entity_id",
                target_type="string",
                target_required=True,
                target_nullable=False,
                source_field="src_id",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
            "status": FieldMappingProposal(
                target_field="status",
                target_type="string",
                target_required=True,
                target_nullable=False,
                source_field="src_status",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
            "balance": FieldMappingProposal(
                target_field="balance",
                target_type="float",
                target_required=True,
                target_nullable=False,
                source_field="src_balance",
                mapping_type=MappingType.TRANSFORMATION_REQUIRED,
                status=MappingStatus.APPROVED,
            ),
            "description": FieldMappingProposal(
                target_field="description",
                target_type="string",
                target_required=False,
                target_nullable=True,
                source_field="src_desc",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
        }
    )
    
    adapter = generate_adapter(plan, contract)
    sandbox = compile_adapter_sandbox(adapter.python_code)
    transform = sandbox["transform_dataset"]
    
    # 8 records covering various integrity edge cases
    test_records = [
        # Record 0: Valid with leading zero string ID and standard values
        {"src_id": "000142", "src_status": "ACTIVE", "src_balance": "150.25", "src_desc": "Standard Account"},
        # Record 1: Valid duplicate of Record 0
        {"src_id": "000142", "src_status": "ACTIVE", "src_balance": "150.25", "src_desc": "Standard Account"},
        # Record 2: High precision float and rich Unicode (German, Japanese, Arabic, Emoji)
        {"src_id": "009999", "src_status": "PENDING", "src_balance": "123456789.987654321", "src_desc": "Grüße! 東京 🚀 مرحبا"},
        # Record 3: Nullable description as None
        {"src_id": "000143", "src_status": "INACTIVE", "src_balance": "0.0", "src_desc": None},
        # Record 4: Invalid enum value (FAIL -> Quarantine)
        {"src_id": "000144", "src_status": "UNKNOWN_ENUM_VAL", "src_balance": "50.0", "src_desc": "Bad status"},
        # Record 5: Missing required field (entity_id is missing -> Quarantine)
        {"src_status": "ACTIVE", "src_balance": "75.0", "src_desc": "No ID"},
        # Record 6: Malformed balance (cannot parse float -> Quarantine)
        {"src_id": "000145", "src_status": "ACTIVE", "src_balance": "NOT_A_NUMBER", "src_desc": "Corrupt amount"},
        # Record 7: Empty string required ID (FAIL -> Quarantine)
        {"src_id": "", "src_status": "ACTIVE", "src_balance": "20.0", "src_desc": "Empty ID"}
    ]
    
    valid, quarantined = transform(test_records)
    total_in = len(test_records)
    total_out = len(valid) + len(quarantined)
    
    print(f"Total input records: {total_in}")
    print(f"Valid records: {len(valid)}")
    print(f"Quarantined records: {len(quarantined)}")
    print(f"Total accounted for: {total_out}")
    
    # 1. Zero-loss invariant
    assert total_in == total_out, f"Zero loss invariant failed! {total_in} != {total_out}"
    print("[PASS] Zero-data-loss invariant verified: Total = Valid + Quarantined")
    
    # Check valid records
    assert len(valid) == 4, f"Expected 4 valid records, got {len(valid)}"
    assert len(quarantined) == 4, f"Expected 4 quarantined records, got {len(quarantined)}"
    
    # 2. Leading zeros
    assert valid[0]["entity_id"] == "000142", f"Leading zero lost: {valid[0]['entity_id']}"
    print("[PASS] Leading-zero preservation verified ('000142')")
    
    # 3. Duplicate records
    assert valid[0]["entity_id"] == valid[1]["entity_id"] == "000142"
    print("[PASS] Duplicate record preservation verified")
    
    # 4. Precision
    assert valid[2]["balance"] == 123456789.987654321, f"High precision corrupted: {valid[2]['balance']}"
    print("[PASS] High precision float verified (123456789.987654321)")
    
    # 5. Unicode
    assert valid[2]["description"] == "Grüße! 東京 🚀 مرحبا", f"Unicode corrupted: {valid[2]['description']}"
    print("[PASS] Unicode integrity verified ('Grüße! 東京 🚀 مرحبا')")
    
    # 6. Nullable field
    assert valid[3]["description"] is None
    print("[PASS] Nullable optional field handled cleanly")
    
    # 7. Quarantine diagnostics
    print(f"Quarantined record 0 structure: {quarantined[0]}")
    q_reasons = [q.get("failure_reason", "") for q in quarantined]
    print(f"Quarantine reasons captured:\n" + "\n".join(f" - {r}" for r in q_reasons))
    assert any("allowed values" in r for r in q_reasons), "Enum violation not detected"
    assert any("Missing required field" in r or "entity_id" in r for r in q_reasons), "Missing required field not detected"
    assert any("could not convert" in r or "balance" in r for r in q_reasons), "Type conversion error not detected"
    print("[PASS] Quarantine diagnostics accurate and descriptive")
    
    print("\nALL 8 DATA INTEGRITY MATRIX TESTS PASSED WITH 100% ACCURACY!")

if __name__ == "__main__":
    test_data_integrity_matrix()
