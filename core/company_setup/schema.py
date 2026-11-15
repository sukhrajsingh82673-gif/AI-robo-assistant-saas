"""Idempotent schema bootstrap for the company setup module.

The repository has two independent schema paths:

* SQLite dev/test databases are created from ``core.db.SCHEMA_SQL``.
* PostgreSQL (Render/Neon) databases are created from versioned files in
  ``migrations/pg`` via ``migrations/migration_manager.py``.

Both are additive here. This module guarantees the tables/columns exist even if
a deployment has not yet run the migration, which keeps the API from failing on
an older database. Every statement is safe to repeat.
"""

from __future__ import annotations

import threading
from typing import List, Set

from core.db import db

_LOCK = threading.Lock()
_ENSURED: Set[str] = set()

_COMPANY_COLUMNS: List[tuple] = [
    ("title", "TEXT"),
    ("description", "TEXT"),
    ("owner_name", "TEXT"),
    ("owner_email", "TEXT"),
    ("owner_role", "TEXT"),
    ("created_by", "TEXT"),
    ("updated_at", "REAL"),
    ("website", "TEXT"),
    ("business_model", "TEXT"),
    ("revenue_amount", "REAL"),
    ("revenue_currency", "TEXT"),
    ("revenue_period", "TEXT"),
    ("readiness_score", "REAL"),
    ("deleted_at", "REAL"),
    ("deleted_by", "TEXT"),
    ("target_customers", "TEXT"),
    ("budget_amount", "REAL"),
    ("budget_currency", "TEXT"),
    ("timeline", "TEXT"),
    ("setup_notes", "TEXT"),
    ("assets", "JSON"),
]

_BUILD_RUN_COLUMNS: List[tuple] = [
    ("workflow_run_id", "TEXT"),
]

_EXTERNAL_CONNECTION_COLUMNS: List[tuple] = [
    ("provider_id", "TEXT"),
    ("source_id", "TEXT"),
    ("classification", "TEXT"),
    ("scope", "JSON"),
    ("status", "TEXT"),
    ("last_check_at", "REAL"),
    ("secret_ref", "TEXT"),
    ("verified_at", "REAL"),
    ("verification_method", "TEXT"),
    ("verification_token", "TEXT"),
    ("verification_requested_at", "REAL"),
    ("verification_expires_at", "REAL"),
    ("skipped", "INTEGER DEFAULT 0"),
    ("skip_reason", "TEXT"),
]

_COMPANY_FILE_COLUMNS: List[tuple] = [
    ("flags", "JSON"),
]

_DELETION_REQUEST_COLUMNS: List[tuple] = [
    ("previous_status", "TEXT"),
    ("export_ready_at", "REAL"),
    ("export_sha256", "TEXT"),
    ("export_size_bytes", "INTEGER"),
    ("export_content_type", "TEXT"),
    ("recovery_days", "INTEGER"),
    ("email_recipient", "TEXT"),
    ("purge_blocked_reason", "TEXT"),
]

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS company_build_runs (
        build_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        run_type TEXT NOT NULL DEFAULT 'BUILD',
        workflow_id TEXT,
        phase TEXT NOT NULL DEFAULT 'INTAKE',
        phase_state TEXT NOT NULL DEFAULT 'PENDING',
        progress REAL NOT NULL DEFAULT 0.0,
        estimate_min_days INTEGER NOT NULL DEFAULT 1,
        estimate_max_days INTEGER NOT NULL DEFAULT 3,
        started_at REAL,
        finished_at REAL,
        failure_reason TEXT,
        log JSON,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_company_build_runs_company ON company_build_runs(company_id)",
    """
    CREATE TABLE IF NOT EXISTS company_files (
        file_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'DOCUMENT',
        filename TEXT NOT NULL,
        mime TEXT NOT NULL DEFAULT 'application/octet-stream',
        size_bytes INTEGER NOT NULL DEFAULT 0,
        storage_key TEXT,
        sha256 TEXT,
        scan_status TEXT NOT NULL DEFAULT 'UNSCANNED',
        flags JSON,
        uploaded_by TEXT,
        created_at REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_company_files_company ON company_files(company_id)",
    """
    CREATE TABLE IF NOT EXISTS company_legal_items (
        item_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        name TEXT NOT NULL,
        authority TEXT,
        status TEXT NOT NULL DEFAULT 'DRAFT',
        instructions TEXT,
        draft_disclaimer TEXT NOT NULL DEFAULT 'Draft: verify with a qualified professional',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_company_legal_items_company ON company_legal_items(company_id)",
    """
    CREATE TABLE IF NOT EXISTS company_drafts (
        draft_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT,
        user_id TEXT NOT NULL,
        company_type TEXT,
        payload JSON NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_company_drafts_tenant ON company_drafts(tenant_id, user_id)",
    """
    CREATE TABLE IF NOT EXISTS company_admin_grants (
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        granted_by TEXT NOT NULL,
        created_at REAL NOT NULL,
        PRIMARY KEY (tenant_id, company_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_deletion_requests (
        request_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'AWAITING_CONFIRMATION',
        steps_done JSON,
        removal_summary JSON,
        export_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
        export_parts INTEGER NOT NULL DEFAULT 0,
        export_ref TEXT,
        email_status TEXT NOT NULL DEFAULT 'NOT_SENT',
        download_confirmed_at REAL,
        purge_after REAL,
        requested_by TEXT NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        completed_at REAL,
        previous_status TEXT,
        export_ready_at REAL,
        export_sha256 TEXT,
        export_size_bytes INTEGER,
        export_content_type TEXT,
        recovery_days INTEGER,
        email_recipient TEXT,
        purge_blocked_reason TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_company_deletion_requests_company ON company_deletion_requests(company_id)",
    """
    CREATE TABLE IF NOT EXISTS company_audit_events (
        event_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT,
        actor_id TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        action TEXT NOT NULL,
        detail JSON,
        created_at REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_company_audit_events_company ON company_audit_events(company_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_company_audit_events_tenant ON company_audit_events(tenant_id, created_at)",
]


def _schema_key() -> str:
    dialect = db.get_dialect() if hasattr(db, "get_dialect") else "sqlite"
    location = getattr(db, "db_path", "") or ""
    return f"{dialect}|{location}|{id(db)}"


def _table_columns(conn, table: str) -> Set[str]:
    if getattr(db, "dialect", "sqlite") == "postgresql":
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = ? AND table_schema = current_schema()",
            (table,),
        ).fetchall()
        return {str(r[0]).lower() for r in rows}
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]).lower() for r in rows}


def _add_missing_columns(conn, table: str, columns: List[tuple]) -> List[str]:
    """Add missing columns and return the names added."""
    try:
        existing = _table_columns(conn, table)
    except Exception:
        return []
    if not existing:
        return []
    added: List[str] = []
    for name, ddl_type in columns:
        if name.lower() in existing:
            continue
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}")
            added.append(name)
        except Exception:
            # A concurrent process may have added it; re-check next time.
            pass
    return added


def ensure_schema(force: bool = False) -> bool:
    """Create tables and add columns if needed. Returns True when ready."""
    key = _schema_key()
    if not force and key in _ENSURED:
        return True
    with _LOCK:
        if not force and key in _ENSURED:
            return True
        try:
            with db.get_connection() as conn:
                for statement in _TABLES:
                    try:
                        conn.execute(statement)
                    except Exception:
                        # Keep going: a single failure must not mask the rest.
                        pass
                _add_missing_columns(conn, "companies", _COMPANY_COLUMNS)
                _add_missing_columns(conn, "external_connections", _EXTERNAL_CONNECTION_COLUMNS)
                _add_missing_columns(conn, "company_build_runs", _BUILD_RUN_COLUMNS)
                _add_missing_columns(conn, "company_files", _COMPANY_FILE_COLUMNS)
                _add_missing_columns(conn, "company_deletion_requests", _DELETION_REQUEST_COLUMNS)
                # Backfill timestamps and normalise the legacy ATTENTION status.
                try:
                    conn.execute(
                        "UPDATE companies SET updated_at = created_at WHERE updated_at IS NULL"
                    )
                    conn.execute(
                        "UPDATE companies SET status = 'NEEDS_ATTENTION' WHERE status = 'ATTENTION'"
                    )
                except Exception:
                    pass
                conn.commit()
            _ENSURED.add(key)
            return True
        except Exception:
            # Never raise from bootstrap on read paths; callers surface a real
            # error only when the actual query fails.
            return False


def reset_cache() -> None:
    """Testing helper: forget which databases have been ensured."""
    with _LOCK:
        _ENSURED.clear()
