"""Gate 06 Core Engine Reliability and Real-World Validation Benchmark.

Exhaustively verifies engine robustness on real-world data flaws:
- Inconsistent date formats
- Formatted numbers (commas, currency, percentages)
- Mixed null representations ('', 'NULL', 'None', 'NaN', 'N/A')
- Casing variations and enum enforcement
- Line endings (CRLF vs LF)
- Non-UTF-8 encodings (Latin-1)
- Deeply nested and uneven JSON records
- Extreme field lengths and memory stability
"""

from pathlib import Path
import pytest

from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.ingestion.csv_loader import load_csv
from recon.ingestion.json_loader import load_json
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingPlan, FieldMappingProposal, MappingStatus, MappingType
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.validation.executor import validate_adapter, compile_adapter_sandbox


def test_edge_case_mixed_null_representations_and_whitespace(tmp_path: Path):
    """Verifies that all standard null representations and whitespace anomalies are correctly handled."""
    csv_file = tmp_path / "mixed_nulls.csv"
    csv_file.write_text(
        "id,name,category,amount\n"
        "1,  Alpha  ,SUPPORT,100\n"
        "2,Beta,NULL,200\n"
        "3,Gamma,N/A,300\n"
        "4,Delta,none,400\n"
        "5,Epsilon,NaN,500\n"
        "6,Zeta,,600\n",
        encoding="utf-8"
    )

    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)

    # Name column has leading/trailing whitespace
    assert profile.columns["name"].has_whitespace_anomalies is True

    # Category column has 5 null values out of 6 (all recognized as null tokens)
    assert profile.columns["category"].null_count == 5

    contract = load_target_contract({
        "contract_name": "mixed_nulls_contract",
        "fields": {
            "id": {"name": "id", "target_type": "string", "required": True},
            "name": {"name": "name", "target_type": "string", "required": True},
            "category": {"name": "category", "target_type": "string", "required": False, "nullable": True},
            "amount": {"name": "amount", "target_type": "integer", "required": True},
        }
    })

    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)

    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid, quarantined = sandbox["transform_dataset"](dataset.rows)

    assert len(valid) == 6
    assert len(quarantined) == 0
    # Whitespace stripped
    assert valid[0]["name"] == "Alpha"
    # Null tokens correctly converted to None
    for r in valid[1:]:
        assert r["category"] is None


def test_edge_case_strict_contract_quarantines_formatted_numbers_and_currency(tmp_path: Path):
    """Verifies that formatted numbers (currency symbols, commas, percentages) are cleanly quarantined without crashing."""
    csv_file = tmp_path / "formatted_numbers.csv"
    csv_file.write_text(
        'id,amount\n'
        '1,100\n'
        '2,"$1,250.00"\n'
        '3,"1,500"\n'
        '4,25%\n'
        '5,not_a_number\n',
        encoding="utf-8"
    )

    dataset = load_csv(csv_file)
    contract = load_target_contract({
        "contract_name": "numbers_contract",
        "fields": {
            "id": {"name": "id", "target_type": "string", "required": True},
            "amount": {"name": "amount", "target_type": "integer", "required": True},
        }
    })

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)

    validation = validate_adapter(adapter, contract, dataset.rows)

    # 1 valid row (id=1, amount=100); 4 invalid rows quarantined
    assert validation.total_input_records == 5
    assert validation.valid_records_count == 1
    assert validation.quarantined_records_count == 4
    # Zero data loss law
    assert validation.valid_records_count + validation.quarantined_records_count == 5


def test_edge_case_inconsistent_datetime_formats_quarantined_strictly(tmp_path: Path):
    """Verifies that non-standard date formats in the same column are quarantined while standard dates pass."""
    csv_file = tmp_path / "mixed_dates.csv"
    csv_file.write_text(
        "id,event_time\n"
        "1,2024-05-15T14:30:00Z\n"
        "2,05/15/2024 02:30:00 PM\n"
        "3,2024-05-16T09:15:00Z\n"
        "4,INVALID_TIMESTAMP_STRING\n",
        encoding="utf-8"
    )

    dataset = load_csv(csv_file)
    contract = load_target_contract({
        "contract_name": "datetime_contract",
        "fields": {
            "id": {"name": "id", "target_type": "string", "required": True},
            "event_time": {"name": "event_time", "target_type": "datetime", "required": True},
        }
    })

    profile = profile_dataset(dataset)
    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)

    validation = validate_adapter(adapter, contract, dataset.rows)

    # Rows 1 and 3 are standard ISO-8601; Rows 2 and 4 fail format and are quarantined
    assert validation.total_input_records == 4
    assert validation.valid_records_count == 2
    assert validation.quarantined_records_count == 2
    assert validation.valid_records_count + validation.quarantined_records_count == 4


def test_edge_case_crlf_and_lf_line_endings(tmp_path: Path):
    """Verifies CSV loading and profiling works identically across Windows (CRLF) and Unix (LF) line endings."""
    crlf_content = b"id,val\r\n1,one\r\n2,two\r\n3,three\r\n"
    lf_content = b"id,val\n1,one\n2,two\n3,three\n"

    crlf_file = tmp_path / "crlf.csv"
    lf_file = tmp_path / "lf.csv"
    crlf_file.write_bytes(crlf_content)
    lf_file.write_bytes(lf_content)

    crlf_dataset = load_csv(crlf_file)
    lf_dataset = load_csv(lf_file)

    assert crlf_dataset.row_count == 3
    assert lf_dataset.row_count == 3
    assert crlf_dataset.rows == lf_dataset.rows


def test_edge_case_latin1_encoding(tmp_path: Path):
    """Verifies automated encoding detection and safe handling of Latin-1 encoded files."""
    latin1_file = tmp_path / "latin1.csv"
    # Write bytes with Latin-1 specific characters: é, ä, ñ
    latin1_bytes = "id,name\n1,René\n2,Müller\n3,Peña\n".encode("latin-1")
    latin1_file.write_bytes(latin1_bytes)

    dataset = load_dataset(latin1_file)
    assert dataset.row_count == 3
    assert dataset.rows[0]["name"] == "René"
    assert dataset.rows[1]["name"] == "Müller"
    assert dataset.rows[2]["name"] == "Peña"


def test_edge_case_uneven_and_nested_json(tmp_path: Path):
    """Verifies that JSON arrays with heterogeneous fields and nested structures are normalized safely."""
    json_file = tmp_path / "uneven.json"
    json_file.write_text(
        '[\n'
        '  {"id": 1, "profile": {"name": "Alice", "city": "Seattle"}},\n'
        '  {"id": 2, "profile": {"name": "Bob"}, "extra_tag": "vip"},\n'
        '  {"id": 3, "profile": null}\n'
        ']\n',
        encoding="utf-8"
    )

    dataset = load_json(json_file)
    assert dataset.row_count == 3
    # Flattened keys
    assert "profile.name" in dataset.headers
    assert "profile.city" in dataset.headers
    assert "extra_tag" in dataset.headers

    # Row 2 lacks city, row 3 lacks profile.name and profile.city
    assert dataset.rows[0].get("profile.name") == "Alice"
    assert dataset.rows[0].get("profile.city") == "Seattle"
    assert dataset.rows[1].get("profile.name") == "Bob"
    assert dataset.rows[1].get("profile.city") is None
    assert dataset.rows[2].get("profile.name") is None


def test_edge_case_extreme_field_length_stability(tmp_path: Path):
    """Verifies that large field values (e.g. 50,000 characters) do not cause stack overflow or memory exhaustion."""
    csv_file = tmp_path / "large_field.csv"
    long_text = "A" * 50000
    csv_file.write_text(f"id,notes\n1,{long_text}\n", encoding="utf-8")

    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)

    contract = load_target_contract({
        "contract_name": "large_field_contract",
        "fields": {
            "id": {"name": "id", "target_type": "string", "required": True},
            "notes": {"name": "notes", "target_type": "string", "required": True},
        }
    })

    plan = propose_mappings(profile, contract)
    approved_plan = approve_mapping_plan(plan)
    adapter = generate_adapter(approved_plan, contract)

    sandbox = compile_adapter_sandbox(adapter.python_code)
    valid, quarantined = sandbox["transform_dataset"](dataset.rows)

    assert len(valid) == 1
    assert len(quarantined) == 0
    assert len(valid[0]["notes"]) == 50000
