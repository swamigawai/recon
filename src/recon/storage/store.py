"""Embedded zero-config SQLite persistence engine with Write-Ahead Logging (WAL).

Ensures zero session loss across server restarts, high-throughput quarantine indexing,
and deterministic audit trail tracking.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Optional


class ReconStore:
    """Thread-safe SQLite store for persistent sessions, audit reports, and quarantine logs."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            # Default to .recon/recon_audit.db in current working directory or user home
            base_dir = Path(os.environ.get("RECON_HOME", Path.cwd() / ".recon"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "recon_audit.db"
        elif str(db_path) == ":memory:":
            self.db_path = Path(":memory:")
        else:
            self.db_path = Path(db_path)
            if self.db_path.parent != Path("."):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Opens a connection configured for high-performance WAL concurrency."""
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=15.0,
        )
        conn.row_factory = sqlite3.Row
        if str(self.db_path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        return conn

    def _init_db(self) -> None:
        """Initializes tables and high-efficiency indexes."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS sessions (
                            session_id TEXT PRIMARY KEY,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            source_filename TEXT NOT NULL,
                            contract_name TEXT NOT NULL,
                            readiness_state TEXT DEFAULT 'PENDING',
                            pass_rate REAL DEFAULT 0.0,
                            total_input_records INTEGER DEFAULT 0,
                            valid_records_count INTEGER DEFAULT 0,
                            quarantined_records_count INTEGER DEFAULT 0,
                            is_blocked INTEGER DEFAULT 0,
                            assessment_json TEXT NOT NULL,
                            results_json TEXT,
                            adapter_code TEXT,
                            report_md TEXT,
                            report_json TEXT,
                            mapping_spec_json TEXT,
                            source_path TEXT,
                            contract_path TEXT
                        );

                        CREATE TABLE IF NOT EXISTS quarantine_records (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT NOT NULL,
                            row_index INTEGER NOT NULL,
                            failure_reasons TEXT NOT NULL,
                            raw_record TEXT NOT NULL,
                            error_category TEXT,
                            target_field TEXT,
                            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                        );

                        CREATE INDEX IF NOT EXISTS idx_quarantine_session
                            ON quarantine_records(session_id, row_index);

                        CREATE INDEX IF NOT EXISTS idx_quarantine_category
                            ON quarantine_records(session_id, error_category);

                        CREATE INDEX IF NOT EXISTS idx_sessions_updated
                            ON sessions(updated_at DESC);
                    """)
            finally:
                conn.close()

    def save_assessment(
        self,
        session_id: str,
        assessment_data: dict[str, Any],
        source_path: str | Path | None = None,
        contract_path: str | Path | None = None,
    ) -> None:
        """Saves initial dataset inspection and profiling assessment."""
        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).isoformat()
        src_meta = assessment_data.get("source", {})
        ctr_meta = assessment_data.get("contract", {})

        source_filename = src_meta.get("file_name", "unknown_source")
        contract_name = ctr_meta.get("contract_name", "unknown_contract")
        total_rows = int(src_meta.get("total_rows", 0))
        is_blocked = 1 if assessment_data.get("is_blocked", False) else 0

        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO sessions (
                            session_id, created_at, updated_at, source_filename, contract_name,
                            total_input_records, is_blocked, assessment_json, source_path, contract_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(session_id) DO UPDATE SET
                            updated_at = excluded.updated_at,
                            source_filename = excluded.source_filename,
                            contract_name = excluded.contract_name,
                            total_input_records = excluded.total_input_records,
                            is_blocked = excluded.is_blocked,
                            assessment_json = excluded.assessment_json,
                            source_path = COALESCE(excluded.source_path, sessions.source_path),
                            contract_path = COALESCE(excluded.contract_path, sessions.contract_path);
                        """,
                        (
                            session_id,
                            now_iso,
                            now_iso,
                            source_filename,
                            contract_name,
                            total_rows,
                            is_blocked,
                            json.dumps(assessment_data, ensure_ascii=False),
                            str(source_path) if source_path else None,
                            str(contract_path) if contract_path else None,
                        ),
                    )
            finally:
                conn.close()

    def save_results(
        self,
        session_id: str,
        results_data: dict[str, Any],
        adapter_code: str = "",
        report_md: str = "",
        report_json: str | dict[str, Any] = "",
        mapping_spec_json: str = "",
        quarantine_records: list[dict[str, Any]] | None = None,
    ) -> None:
        """Saves adapter compilation, sandbox validation, and readiness report results."""
        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).isoformat()
        state = results_data.get("readiness_state", "READY")
        val_meta = results_data.get("validation", {})
        pass_rate = float(val_meta.get("contract_pass_rate", 0.0))
        valid_cnt = int(val_meta.get("valid_records_count", 0))
        quar_cnt = int(val_meta.get("quarantined_records_count", 0))
        total_inp = int(val_meta.get("total_input_records", valid_cnt + quar_cnt))

        if isinstance(report_json, dict):
            report_json_str = json.dumps(report_json, ensure_ascii=False)
        else:
            report_json_str = str(report_json)

        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        UPDATE sessions SET
                            updated_at = ?,
                            readiness_state = ?,
                            pass_rate = ?,
                            total_input_records = ?,
                            valid_records_count = ?,
                            quarantined_records_count = ?,
                            results_json = ?,
                            adapter_code = ?,
                            report_md = ?,
                            report_json = ?,
                            mapping_spec_json = ?
                        WHERE session_id = ?;
                        """,
                        (
                            now_iso,
                            state,
                            pass_rate,
                            total_inp,
                            valid_cnt,
                            quar_cnt,
                            json.dumps(results_data, ensure_ascii=False),
                            adapter_code,
                            report_md,
                            report_json_str,
                            mapping_spec_json,
                            session_id,
                        ),
                    )

                    # Store quarantined records if provided
                    if quarantine_records:
                        self._insert_quarantine_records_conn(conn, session_id, quarantine_records)
            finally:
                conn.close()

    def _insert_quarantine_records_conn(
        self, conn: sqlite3.Connection, session_id: str, records: list[dict[str, Any]]
    ) -> None:
        """Internal batch inserter for quarantined records."""
        # Clear existing quarantine records for this session first
        conn.execute("DELETE FROM quarantine_records WHERE session_id = ?;", (session_id,))

        entries = []
        for idx, r in enumerate(records):
            row_idx = r.get("record_index") or r.get("row_index", idx + 1)
            errs = r.get("errors") or r.get("failure_reasons") or ["Schema violation"]
            raw = r.get("raw_record") or {}

            # Categorize error
            err_str = " ".join(errs).lower()
            if "not in allowed values" in err_str or "enum" in err_str:
                cat = "Allowed Values"
            elif "required" in err_str or "missing" in err_str or "cannot be empty" in err_str:
                cat = "Missing Required"
            elif "datetime" in err_str or "iso-8601" in err_str or "date" in err_str:
                cat = "Date / Time"
            elif "does not match pattern" in err_str or "pattern" in err_str:
                cat = "Pattern Mismatch"
            elif "type" in err_str or "cannot convert" in err_str:
                cat = "Type Mismatch"
            else:
                cat = "Contract Violation"

            # Extract target field
            target_field = ""
            m = re.search(r"for '([^']+)'|field '([^']+)'|'([^']+)' is missing|'([^']+)' does not match", " ".join(errs), re.IGNORECASE)
            if m:
                target_field = next((g for g in m.groups() if g), "")

            entries.append((
                session_id,
                int(row_idx),
                json.dumps(errs, ensure_ascii=False),
                json.dumps(raw, ensure_ascii=False),
                cat,
                target_field,
            ))

        if entries:
            conn.executemany(
                """
                INSERT INTO quarantine_records (
                    session_id, row_index, failure_reasons, raw_record, error_category, target_field
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                entries,
            )

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieves and deserializes session data."""
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?;", (session_id,)
                ).fetchone()
                if not row:
                    return None

                assessment = json.loads(row["assessment_json"]) if row["assessment_json"] else {}
                results = json.loads(row["results_json"]) if row["results_json"] else None
                report_json = json.loads(row["report_json"]) if row["report_json"] else None

                return {
                    "session_id": row["session_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "source_filename": row["source_filename"],
                    "contract_name": row["contract_name"],
                    "readiness_state": row["readiness_state"],
                    "pass_rate": row["pass_rate"],
                    "total_input_records": row["total_input_records"],
                    "valid_records_count": row["valid_records_count"],
                    "quarantined_records_count": row["quarantined_records_count"],
                    "is_blocked": bool(row["is_blocked"]),
                    "assessment": assessment,
                    "results": results,
                    "adapter_code": row["adapter_code"],
                    "report_md": row["report_md"],
                    "report_json": report_json,
                    "mapping_spec_json": row["mapping_spec_json"],
                    "source_path": row["source_path"],
                    "contract_path": row["contract_path"],
                }
            finally:
                conn.close()

    def list_recent_sessions(self, limit: int = 25) -> list[dict[str, Any]]:
        """Lists recent sessions for instant interactive restoration and audit review."""
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(
                    """
                    SELECT session_id, created_at, updated_at, source_filename, contract_name,
                           readiness_state, pass_rate, total_input_records, valid_records_count,
                           quarantined_records_count, (results_json IS NOT NULL) AS is_compiled
                    FROM sessions
                    ORDER BY updated_at DESC
                    LIMIT ?;
                    """,
                    (limit,),
                ).fetchall()

                return [
                    {
                        "session_id": r["session_id"],
                        "created_at": r["created_at"],
                        "updated_at": r["updated_at"],
                        "source_filename": r["source_filename"],
                        "contract_name": r["contract_name"],
                        "readiness_state": r["readiness_state"],
                        "pass_rate": float(r["pass_rate"]),
                        "total_input_records": int(r["total_input_records"]),
                        "valid_records_count": int(r["valid_records_count"]),
                        "quarantined_records_count": int(r["quarantined_records_count"]),
                        "is_compiled": bool(r["is_compiled"]),
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def query_quarantine_records(
        self,
        session_id: str,
        search: str | None = None,
        field: str | None = None,
        category: str | None = None,
        sort_by: str = "row_index",
        sort_dir: str = "asc",
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """Performs high-speed SQL search, filtering, and pagination over quarantined records."""
        with self._lock:
            conn = self._get_connection()
            try:
                clauses = ["session_id = ?"]
                params: list[Any] = [session_id]

                if field and field.strip() and field.lower() != "all":
                    clauses.append("(target_field = ? OR failure_reasons LIKE ?)")
                    params.extend([field.strip(), f"%'{field.strip()}'%"])

                if category and category.strip() and category.lower() != "all":
                    clauses.append("error_category = ?")
                    params.append(category.strip())

                if search and search.strip():
                    s = f"%{search.strip().lower()}%"
                    clauses.append("(LOWER(failure_reasons) LIKE ? OR LOWER(raw_record) LIKE ? OR CAST(row_index AS TEXT) LIKE ?)")
                    params.extend([s, s, s])

                where_sql = " AND ".join(clauses)

                # Count total matching
                count_cur = conn.execute(f"SELECT COUNT(*) FROM quarantine_records WHERE {where_sql};", params)
                total_matching = count_cur.fetchone()[0]

                # Determine order
                safe_sort = "row_index" if sort_by != "row_index" else "row_index"
                safe_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"

                # Query page
                query_sql = f"""
                    SELECT row_index, failure_reasons, raw_record, error_category, target_field
                    FROM quarantine_records
                    WHERE {where_sql}
                    ORDER BY {safe_sort} {safe_dir}
                    LIMIT ? OFFSET ?;
                """
                page_params = list(params) + [limit, offset]
                rows = conn.execute(query_sql, page_params).fetchall()

                records = [
                    {
                        "row_index": r["row_index"],
                        "record_index": r["row_index"],
                        "failure_reasons": json.loads(r["failure_reasons"]),
                        "errors": json.loads(r["failure_reasons"]),
                        "raw_record": json.loads(r["raw_record"]),
                        "error_category": r["error_category"],
                        "target_field": r["target_field"],
                    }
                    for r in rows
                ]
                return records, total_matching
            finally:
                conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and its associated quarantine records."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM quarantine_records WHERE session_id = ?;", (session_id,))
                    cur = conn.execute("DELETE FROM sessions WHERE session_id = ?;", (session_id,))
                    return cur.rowcount > 0
            finally:
                conn.close()

    def prune_sessions(self, keep_latest: int = 50) -> int:
        """Evicts older sessions to prevent unbounded disk growth while keeping recent audit history."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # Find IDs to delete
                    rows = conn.execute(
                        """
                        SELECT session_id FROM sessions
                        ORDER BY updated_at DESC
                        LIMIT -1 OFFSET ?;
                        """,
                        (keep_latest,),
                    ).fetchall()

                    ids_to_delete = [r["session_id"] for r in rows]
                    if not ids_to_delete:
                        return 0

                    placeholders = ",".join("?" for _ in ids_to_delete)
                    conn.execute(
                        f"DELETE FROM quarantine_records WHERE session_id IN ({placeholders});",
                        ids_to_delete,
                    )
                    conn.execute(
                        f"DELETE FROM sessions WHERE session_id IN ({placeholders});",
                        ids_to_delete,
                    )
                    return len(ids_to_delete)
            finally:
                conn.close()

    def get_storage_stats(self) -> dict[str, Any]:
        """Returns runtime storage diagnostics and WAL mode status."""
        with self._lock:
            conn = self._get_connection()
            try:
                sess_cnt = conn.execute("SELECT COUNT(*) FROM sessions;").fetchone()[0]
                quar_cnt = conn.execute("SELECT COUNT(*) FROM quarantine_records;").fetchone()[0]
                journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]

                size_bytes = 0
                if self.db_path != Path(":memory:") and self.db_path.exists():
                    size_bytes = self.db_path.stat().st_size
                    # Add WAL file size if present
                    wal_file = self.db_path.with_name(f"{self.db_path.name}-wal")
                    if wal_file.exists():
                        size_bytes += wal_file.stat().st_size

                return {
                    "engine": "SQLite WAL",
                    "db_path": str(self.db_path),
                    "total_sessions": sess_cnt,
                    "total_quarantine_records": quar_cnt,
                    "db_size_bytes": size_bytes,
                    "db_size_kb": round(size_bytes / 1024.0, 1),
                    "journal_mode": str(journal_mode).upper(),
                    "wal_active": str(journal_mode).upper() == "WAL",
                }
            finally:
                conn.close()


_DEFAULT_STORE: Optional[ReconStore] = None
_STORE_LOCK = threading.Lock()


def get_default_store() -> ReconStore:
    """Returns singleton instance of the default workspace ReconStore."""
    global _DEFAULT_STORE
    with _STORE_LOCK:
        if _DEFAULT_STORE is None:
            _DEFAULT_STORE = ReconStore()
        return _DEFAULT_STORE
