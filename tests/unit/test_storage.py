"""Unit tests for Recon embedded zero-config SQLite persistence store."""

import json
from pathlib import Path
import tempfile
import pytest

from recon.storage.store import ReconStore


@pytest.fixture
def temp_store(tmp_path: Path) -> ReconStore:
    db_file = tmp_path / "test_recon.db"
    return ReconStore(db_file)


def test_store_initialization(temp_store: ReconStore) -> None:
    stats = temp_store.get_storage_stats()
    assert stats["engine"] == "SQLite WAL"
    assert stats["total_sessions"] == 0
    assert stats["total_quarantine_records"] == 0
    assert stats["wal_active"] is True


def test_save_and_get_assessment(temp_store: ReconStore) -> None:
    session_id = "sess-test-001"
    assessment = {
        "session_id": session_id,
        "source": {
            "file_name": "customers.csv",
            "total_rows": 1250,
        },
        "contract": {
            "contract_name": "customer_target_contract",
        },
        "is_blocked": False,
    }

    temp_store.save_assessment(session_id, assessment)
    retrieved = temp_store.get_session(session_id)

    assert retrieved is not None
    assert retrieved["session_id"] == session_id
    assert retrieved["source_filename"] == "customers.csv"
    assert retrieved["contract_name"] == "customer_target_contract"
    assert retrieved["total_input_records"] == 1250
    assert retrieved["readiness_state"] == "PENDING"
    assert retrieved["assessment"]["source"]["file_name"] == "customers.csv"


def test_save_results_and_quarantine_records(temp_store: ReconStore) -> None:
    session_id = "sess-test-002"
    assessment = {
        "session_id": session_id,
        "source": {"file_name": "orders.xlsx", "total_rows": 100},
        "contract": {"contract_name": "order_contract"},
    }
    temp_store.save_assessment(session_id, assessment)

    results = {
        "session_id": session_id,
        "readiness_state": "PASS",
        "validation": {
            "total_input_records": 100,
            "valid_records_count": 95,
            "quarantined_records_count": 5,
            "contract_pass_rate": 95.0,
        },
    }
    quarantine_records = [
        {
            "record_index": 12,
            "errors": ["Value 'XYZ' for 'Status' not in allowed values: ['ACTIVE', 'INACTIVE']"],
            "raw_record": {"order_id": "ORD-12", "Status": "XYZ"},
        },
        {
            "record_index": 45,
            "errors": ["Required target field 'Amount' cannot be empty or null"],
            "raw_record": {"order_id": "ORD-45", "Amount": None},
        },
    ]

    temp_store.save_results(
        session_id=session_id,
        results_data=results,
        adapter_code="# Compiled AST Adapter",
        report_md="# Readiness Dossier",
        report_json={"readiness_state": "PASS"},
        mapping_spec_json='{"version": "1.0.0"}',
        quarantine_records=quarantine_records,
    )

    retrieved = temp_store.get_session(session_id)
    assert retrieved is not None
    assert retrieved["readiness_state"] == "PASS"
    assert retrieved["pass_rate"] == 95.0
    assert retrieved["valid_records_count"] == 95
    assert retrieved["quarantined_records_count"] == 5
    assert retrieved["adapter_code"] == "# Compiled AST Adapter"

    # Query quarantine records
    recs, total = temp_store.query_quarantine_records(session_id)
    assert total == 2
    assert len(recs) == 2
    assert recs[0]["record_index"] == 12
    assert recs[0]["error_category"] == "Allowed Values"
    assert recs[1]["record_index"] == 45
    assert recs[1]["error_category"] == "Missing Required"

    # Search filter
    filtered, f_total = temp_store.query_quarantine_records(session_id, search="ORD-12")
    assert f_total == 1
    assert filtered[0]["raw_record"]["order_id"] == "ORD-12"

    # Category filter
    cat_filtered, cat_total = temp_store.query_quarantine_records(session_id, category="Missing Required")
    assert cat_total == 1
    assert cat_filtered[0]["record_index"] == 45


def test_persistence_across_simulated_restart(tmp_path: Path) -> None:
    db_file = tmp_path / "persist_test.db"

    # Phase 1: Write session in first store instance
    store1 = ReconStore(db_file)
    store1.save_assessment("sess-reboot", {"source": {"file_name": "data.csv", "total_rows": 500}, "contract": {"contract_name": "ctr"}})
    store1.save_results("sess-reboot", {"readiness_state": "READY", "validation": {"contract_pass_rate": 100.0, "valid_records_count": 500, "quarantined_records_count": 0}}, adapter_code="def transform(): pass")

    # Simulate server crash/shutdown: store1 is discarded
    del store1

    # Phase 2: Open a fresh store instance pointing to same file
    store2 = ReconStore(db_file)
    restored = store2.get_session("sess-reboot")
    assert restored is not None
    assert restored["source_filename"] == "data.csv"
    assert restored["readiness_state"] == "READY"
    assert restored["adapter_code"] == "def transform(): pass"
    assert restored["pass_rate"] == 100.0


def test_list_recent_sessions_and_pruning(temp_store: ReconStore) -> None:
    for i in range(10):
        temp_store.save_assessment(
            f"sess-{i:03d}",
            {"source": {"file_name": f"file_{i}.csv", "total_rows": 100 * (i + 1)}, "contract": {"contract_name": f"ctr_{i}"}}
        )

    recent = temp_store.list_recent_sessions(limit=5)
    assert len(recent) == 5

    # Prune to keep only 6 sessions
    pruned_count = temp_store.prune_sessions(keep_latest=6)
    assert pruned_count == 4

    remaining = temp_store.list_recent_sessions(limit=20)
    assert len(remaining) == 6


def test_delete_session(temp_store: ReconStore) -> None:
    temp_store.save_assessment("sess-del", {"source": {"file_name": "temp.csv", "total_rows": 10}, "contract": {"contract_name": "ctr"}})
    temp_store.save_results("sess-del", {"readiness_state": "READY", "validation": {}}, quarantine_records=[{"record_index": 1, "errors": ["err"]}])

    assert temp_store.get_session("sess-del") is not None
    deleted = temp_store.delete_session("sess-del")
    assert deleted is True
    assert temp_store.get_session("sess-del") is None

    # Quarantine records should be deleted too
    recs, total = temp_store.query_quarantine_records("sess-del")
    assert total == 0
