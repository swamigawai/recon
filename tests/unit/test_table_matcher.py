"""Unit tests for Multi-Entity Table Matchmaker."""

from recon.mapping.matcher import (
    match_tables,
    JoinCardinality,
    TableMatchResult,
)
from recon.profiling.models import (
    ColumnProfile,
    InferredType,
    SourceProfile,
)


def _make_profile(name: str, fingerprint: str, total_rows: int, cols: dict) -> SourceProfile:
    col_profiles = {}
    for col_name, (inferred_type, distinct_cnt, null_cnt, samples) in cols.items():
        col_profiles[col_name] = ColumnProfile(
            name=col_name,
            inferred_type=inferred_type,
            total_count=total_rows,
            null_count=null_cnt,
            null_percentage=round((null_cnt / total_rows) * 100, 2) if total_rows else 0.0,
            distinct_count=distinct_cnt,
            sample_values=samples,
        )
    return SourceProfile(
        source_name=name,
        fingerprint=fingerprint,
        total_rows=total_rows,
        total_columns=len(cols),
        duplicate_rows_count=0,
        columns=col_profiles,
    )


def test_match_identical_tables_by_fingerprint():
    prof_a = _make_profile("TableA", "sha256_abcdef", 100, {
        "id": (InferredType.INTEGER, 100, 0, ["1", "2", "3"]),
        "name": (InferredType.STRING, 80, 0, ["Alice", "Bob"]),
    })
    prof_b = _make_profile("TableB", "sha256_abcdef", 100, {
        "id": (InferredType.INTEGER, 100, 0, ["1", "2", "3"]),
        "name": (InferredType.STRING, 80, 0, ["Alice", "Bob"]),
    })

    result = match_tables(prof_a, prof_b)
    assert result.is_identical is True
    assert result.compatible_for_join is False
    assert "Identical duplicate tables" in result.summary_message


def test_match_identical_tables_by_content_and_columns():
    prof_a = _make_profile("CustomersA", "sha256_111", 50, {
        "user_id": (InferredType.INTEGER, 50, 0, ["101", "102", "103"]),
        "email": (InferredType.STRING, 50, 0, ["a@x.com", "b@x.com"]),
    })
    prof_b = _make_profile("CustomersB", "sha256_222", 50, {
        "user_id": (InferredType.INTEGER, 50, 0, ["101", "102", "103"]),
        "email": (InferredType.STRING, 50, 0, ["a@x.com", "b@x.com"]),
    })

    result = match_tables(prof_a, prof_b)
    assert result.is_identical is True
    assert result.compatible_for_join is False


def test_match_one_to_many_join_customers_and_orders():
    # Table A: Customers (user_id is Primary Key, 100 rows, 100 distinct)
    prof_customers = _make_profile("Customers", "sha256_cust", 100, {
        "CustomerID": (InferredType.INTEGER, 100, 0, ["C1", "C2", "C3", "C4"]),
        "Name": (InferredType.STRING, 95, 0, ["Alice", "Bob", "Charlie", "David"]),
    })

    # Table B: Orders (order_id is PK, customer_id has duplicates)
    prof_orders = _make_profile("Orders", "sha256_orders", 500, {
        "OrderID": (InferredType.INTEGER, 500, 0, ["O1", "O2", "O3", "O4"]),
        "customer_id": (InferredType.INTEGER, 80, 0, ["C1", "C2", "C3"]),
        "Amount": (InferredType.FLOAT, 320, 0, ["19.99", "45.00", "99.50"]),
    })

    result = match_tables(prof_customers, prof_orders)
    assert result.is_identical is False
    assert result.compatible_for_join is True
    assert result.top_join_key is not None
    assert result.top_join_key.table_a_column == "CustomerID"
    assert result.top_join_key.table_b_column == "customer_id"
    assert result.top_join_key.cardinality == JoinCardinality.ONE_TO_MANY
    assert result.top_join_key.confidence >= 0.70


def test_match_incompatible_tables():
    prof_weather = _make_profile("Weather", "sha256_w", 50, {
        "temperature": (InferredType.FLOAT, 30, 0, ["22.5", "25.1"]),
        "humidity": (InferredType.FLOAT, 20, 0, ["60.0", "75.5"]),
    })
    prof_books = _make_profile("Books", "sha256_b", 50, {
        "isbn": (InferredType.STRING, 50, 0, ["978-3-16", "978-1-40"]),
        "title": (InferredType.STRING, 50, 0, ["Book A", "Book B"]),
    })

    result = match_tables(prof_weather, prof_books)
    assert result.is_identical is False
    assert result.compatible_for_join is False


def test_api_match_tables_endpoint():
    from fastapi.testclient import TestClient
    from recon.server.app import app

    client = TestClient(app)
    csv_customers = "customer_id,name,email\n1,Alice,a@x.com\n2,Bob,b@x.com\n3,Charlie,c@x.com\n"
    csv_orders = "order_id,customer_id,amount\n101,1,25.5\n102,1,40.0\n103,2,15.0\n"

    files = {
        "table_a_file": ("customers.csv", csv_customers.encode("utf-8"), "text/csv"),
        "table_b_file": ("orders.csv", csv_orders.encode("utf-8"), "text/csv"),
    }
    res = client.post("/api/match-tables", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["compatible_for_join"] is True
    assert data["top_join_key"]["table_a_column"] == "customer_id"
    assert data["top_join_key"]["table_b_column"] == "customer_id"
    assert data["top_join_key"]["cardinality"] == "1:N"


def test_api_match_tables_identical_duplicate():
    from fastapi.testclient import TestClient
    from recon.server.app import app

    client = TestClient(app)
    csv_data = "id,name,value\n1,Alpha,10\n2,Beta,20\n"

    files = {
        "table_a_file": ("data_a.csv", csv_data.encode("utf-8"), "text/csv"),
        "table_b_file": ("data_b.csv", csv_data.encode("utf-8"), "text/csv"),
    }
    res = client.post("/api/match-tables", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["is_identical"] is True
    assert data["compatible_for_join"] is False
    assert "Identical" in data["summary_message"]

