from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import ApprovedMappingPlan, FieldMappingProposal, MappingStatus, MappingType
from recon.validation.executor import compile_adapter_sandbox, validate_adapter

def test_precision_and_leading_zeros():
    contract = load_target_contract({
        "contract_name": "precision_test",
        "fields": {
            "zip_code": {"name": "zip_code", "target_type": "string", "required": True},
            "amount": {"name": "amount", "target_type": "float", "required": True},
            "ratio": {"name": "ratio", "target_type": "float", "required": True},
        }
    })

    plan = ApprovedMappingPlan(
        contract_name="precision_test",
        source_name="data.csv",
        source_fingerprint="fp123",
        approved_by="tester",
        approved_mappings={
            "zip_code": FieldMappingProposal(
                target_field="zip_code",
                target_type="string",
                target_required=True,
                target_nullable=False,
                source_field="zip",
                mapping_type=MappingType.DIRECT,
                status=MappingStatus.APPROVED,
            ),
            "amount": FieldMappingProposal(
                target_field="amount",
                target_type="float",
                target_required=True,
                target_nullable=False,
                source_field="amt",
                mapping_type=MappingType.TRANSFORMATION_REQUIRED,
                status=MappingStatus.APPROVED,
            ),
            "ratio": FieldMappingProposal(
                target_field="ratio",
                target_type="float",
                target_required=True,
                target_nullable=False,
                source_field="pct",
                mapping_type=MappingType.TRANSFORMATION_REQUIRED,
                status=MappingStatus.APPROVED,
            ),
        }
    )

    adapter = generate_adapter(plan, contract)
    sandbox = compile_adapter_sandbox(adapter.python_code)
    records = [
        {"zip": "00123", "amt": "1234.5678", "pct": "0.00000001"},
        {"zip": "09876", "amt": "999999999999.99", "pct": "3.141592653589793"},
    ]
    valid, quarantined = sandbox["transform_dataset"](records)
    print("Valid count:", len(valid))
    print("Quarantined count:", len(quarantined))
    print("Record 0 zip:", repr(valid[0]["zip_code"]))
    print("Record 0 amount:", repr(valid[0]["amount"]))
    print("Record 0 ratio:", repr(valid[0]["ratio"]))
    assert valid[0]["zip_code"] == "00123", f"Expected '00123', got {valid[0]['zip_code']}"
    assert valid[0]["amount"] == 1234.5678
    assert valid[0]["ratio"] == 0.00000001
    assert valid[1]["zip_code"] == "09876"
    assert valid[1]["amount"] == 999999999999.99
    print("PRECISION AND LEADING ZEROS VERIFIED!")

if __name__ == "__main__":
    test_precision_and_leading_zeros()
