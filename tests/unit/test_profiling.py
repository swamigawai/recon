"""Unit tests for deterministic profiling verified against ground-truth answer keys."""

from pathlib import Path
import pytest

from recon.ingestion.csv_loader import load_csv
from recon.ingestion.models import RawDataset
from recon.profiling.models import InferredType, SourceProfile
from recon.profiling.profiler import profile_dataset
from recon.profiling.type_inference import infer_column_type


@pytest.fixture
def synthetic_nyc_311_dataset() -> RawDataset:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "synthetic_nyc_311.csv"
    return load_csv(fixture_path)


def test_profile_nyc_311_matches_answer_key(synthetic_nyc_311_dataset: RawDataset):
    """Verifies profiling facts against an independently verified answer key."""
    profile = profile_dataset(synthetic_nyc_311_dataset)

    # 1. Dataset-level facts
    assert profile.total_rows == 10
    assert profile.total_columns == 15
    assert profile.duplicate_rows_count == 0

    # 2. Unique Key (Integer identifier)
    key_prof = profile.get_column("Unique Key")
    assert key_prof is not None
    assert key_prof.inferred_type == InferredType.INTEGER
    assert key_prof.null_count == 0
    assert key_prof.null_percentage == 0.0
    assert key_prof.distinct_count == 10
    assert key_prof.min_value == 10000001
    assert key_prof.max_value == 10000010

    # 3. Created Date (US Datetime format with AM/PM)
    created_prof = profile.get_column("Created Date")
    assert created_prof is not None
    assert created_prof.inferred_type == InferredType.DATETIME
    assert created_prof.null_count == 0
    assert "%m/%d/%Y %I:%M:%S %p" in created_prof.format_patterns

    # 4. Closed Date (Datetime with 6 nulls = 60.0%)
    closed_prof = profile.get_column("Closed Date")
    assert closed_prof is not None
    assert closed_prof.inferred_type == InferredType.DATETIME
    assert closed_prof.null_count == 6
    assert closed_prof.null_percentage == 60.0
    assert closed_prof.distinct_count == 4

    # 5. Incident Zip (9 values, 1 null = 10.0%)
    zip_prof = profile.get_column("Incident Zip")
    assert zip_prof is not None
    assert zip_prof.null_count == 1
    assert zip_prof.null_percentage == 10.0
    assert zip_prof.inferred_type == InferredType.INTEGER

    # 6. Latitude & Longitude (Floats)
    lat_prof = profile.get_column("Latitude")
    assert lat_prof is not None
    assert lat_prof.inferred_type == InferredType.FLOAT
    assert lat_prof.null_count == 0
    assert lat_prof.min_value is not None
    assert lat_prof.max_value is not None

    # 7. Borough (Categorical strings)
    borough_prof = profile.get_column("Borough")
    assert borough_prof is not None
    assert borough_prof.inferred_type == InferredType.STRING
    assert borough_prof.distinct_count == 5
    assert borough_prof.null_count == 0


def test_duplicate_row_detection(tmp_path: Path):
    """Verifies exact duplicate row detection count."""
    csv_file = tmp_path / "dupes.csv"
    csv_file.write_text("a,b\n1,x\n2,y\n1,x\n1,x\n", encoding="utf-8")

    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)

    assert profile.total_rows == 4
    # 4 rows, 2 distinct tuples ('1','x') and ('2','y') => 2 duplicates
    assert profile.duplicate_rows_count == 2


def test_constant_column_detection(tmp_path: Path):
    """Verifies that columns with identical values across all rows trigger constant warnings."""
    csv_file = tmp_path / "constant.csv"
    csv_file.write_text("id,city\n1,NYC\n2,NYC\n3,NYC\n", encoding="utf-8")

    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)

    city_prof = profile.get_column("city")
    assert city_prof is not None
    assert city_prof.is_constant is True
    assert city_prof.distinct_count == 1
    assert any("Column 'city' is constant" in w for w in profile.warnings)


def test_whitespace_anomaly_detection(tmp_path: Path):
    """Verifies detection of leading and trailing whitespace in column values."""
    csv_file = tmp_path / "spaces.csv"
    csv_file.write_text("id,name\n1, Alice \n2,Bob\n", encoding="utf-8")

    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)

    name_prof = profile.get_column("name")
    assert name_prof is not None
    assert name_prof.has_whitespace_anomalies is True


def test_null_token_recognition(tmp_path: Path):
    """Verifies that null tokens like 'N/A', 'NaN', 'None', and '' are accurately counted."""
    csv_file = tmp_path / "nulls.csv"
    csv_file.write_text('val\n""\nN/A\nNaN\nNone\nhello\n', encoding="utf-8")

    dataset = load_csv(csv_file)
    profile = profile_dataset(dataset)

    val_prof = profile.get_column("val")
    assert val_prof is not None
    assert val_prof.total_count == 5
    assert val_prof.null_count == 4
    assert val_prof.null_percentage == 80.0
    assert val_prof.distinct_count == 1
    assert val_prof.sample_values == ["hello"]


def test_type_inference_booleans():
    """Verifies boolean inference for columns containing truthy/falsy tokens."""
    inferred, _, _, min_val, max_val = infer_column_type(["true", "false", "yes", "no"])
    assert inferred == InferredType.BOOLEAN
    assert min_val is False
    assert max_val is True
