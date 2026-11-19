"""Idempotent schema bootstrap for Settings V2.

The settings tables live in migration files so that a fresh database, the
migration runner, and the Phase 1 dry-run tool all converge on exactly the same
definition.  This helper applies only the settings migration files and records
their checksums in ``settings_schema_migrations``; it never touches the general
``schema_migrations`` table, whose version numbers are shared with unrelated
migrations.

Importing this module is side-effect free.
"""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from migrations.migration_manager import split_sql_statements

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_ROOT = os.path.join(_REPO_ROOT, "migrations")

COMMON_SCHEMA_FILE = os.path.join("common", "0003_settings_v2_schema.sql")
SQLITE_APPEND_ONLY_FILE = os.path.join("sqlite", "0004_settings_v2_append_only.sql")
SQLITE_TENANT_KEYS_FILE = os.path.join("sqlite", "0005_settings_v2_tenant_keys.sql")
PG_APPEND_ONLY_FILE = os.path.join("pg", "0006_settings_v2_append_only.sql")
PG_TENANT_KEYS_FILE = os.path.join("pg", "0007_settings_v2_tenant_keys.sql")

SCHEMA_MIGRATIONS_TABLE = "settings_schema_migrations"

# Tables the rest of Settings V2 is allowed to assume exist.
REQUIRED_TABLES: Tuple[str, ...] = (
    "settings_values",
    "settings_audit",
    "secrets",
    "settings_presets",
    "roles",
    "permissions",
    "role_permissions",
    "user_company_roles",
    "settings_approvals",
    "settings_environments",
    "settings_revision",
)

_DIALECT_ALIASES = {
    "sqlite": "sqlite",
    "sqlite3": "sqlite",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "pg": "postgresql",
}


def normalize_dialect(dialect: Optional[str]) -> str:
    value = str(dialect or "sqlite").strip().lower()
    if value not in _DIALECT_ALIASES:
        raise ValueError(f"Unsupported settings schema dialect: {dialect!r}")
    return _DIALECT_ALIASES[value]


def schema_files(dialect: Optional[str] = "sqlite") -> List[Tuple[str, str]]:
    """Return ``(migration_id, absolute_path)`` pairs in apply order."""
    normalized = normalize_dialect(dialect)
    append_only = SQLITE_APPEND_ONLY_FILE if normalized == "sqlite" else PG_APPEND_ONLY_FILE
    tenant_keys = SQLITE_TENANT_KEYS_FILE if normalized == "sqlite" else PG_TENANT_KEYS_FILE
    return [
        (COMMON_SCHEMA_FILE.replace(os.sep, "/"), os.path.join(MIGRATIONS_ROOT, COMMON_SCHEMA_FILE)),
        (append_only.replace(os.sep, "/"), os.path.join(MIGRATIONS_ROOT, append_only)),
        (tenant_keys.replace(os.sep, "/"), os.path.join(MIGRATIONS_ROOT, tenant_keys)),
    ]


def _checksum(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _applied_migrations(conn: Any) -> Dict[str, str]:
    rows = conn.execute(
        f"SELECT migration_id, checksum FROM {SCHEMA_MIGRATIONS_TABLE}"
    ).fetchall()
    return {str(row[0]): str(row[1]) for row in rows}


def ensure_schema(
    conn: Any,
    dialect: Optional[str] = "sqlite",
    commit: bool = True,
) -> Dict[str, Any]:
    """Create every Settings V2 table if it is missing.

    ``conn`` may be a ``sqlite3.Connection`` or the project's PostgreSQL
    connection wrapper; both expose ``execute``, ``commit`` and ``rollback``.
    Applying the same files twice is safe.  A changed checksum raises instead of
    silently drifting, so a modified migration cannot be applied to an already
    migrated database unnoticed.
    """
    normalized = normalize_dialect(dialect)
    files = schema_files(normalized)
    result: Dict[str, Any] = {
        "dialect": normalized,
        "applied": [],
        "skipped": [],
        "statement_counts": {},
    }

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_MIGRATIONS_TABLE} (
            migration_id TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at REAL NOT NULL
        )
        """
    )

    applied = _applied_migrations(conn)
    try:
        for migration_id, path in files:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Settings migration not found: {path}")
            checksum = _checksum(path)
            existing = applied.get(migration_id)
            if existing is not None:
                if existing != checksum:
                    raise RuntimeError(
                        f"Settings migration checksum mismatch for {migration_id}: "
                        f"database has {existing}, file has {checksum}. "
                        "Create a new migration instead of editing an applied one."
                    )
                result["skipped"].append(migration_id)
                continue

            with open(path, "r", encoding="utf-8") as handle:
                sql_content = handle.read()
            statements = split_sql_statements(sql_content, dialect=normalized)
            for statement in statements:
                conn.execute(statement)
            conn.execute(
                f"INSERT INTO {SCHEMA_MIGRATIONS_TABLE} (migration_id, checksum, applied_at) "
                "VALUES (?, ?, ?)",
                (migration_id, checksum, time.time()),
            )
            if commit:
                conn.commit()
            result["applied"].append(migration_id)
            result["statement_counts"][migration_id] = len(statements)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    return result


def verify_schema(conn: Any, dialect: Optional[str] = "sqlite") -> Dict[str, Any]:
    """Check that every required table exists.  Read-only."""
    normalized = normalize_dialect(dialect)
    if normalized == "sqlite":
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        present = {str(row[0]) for row in rows}
    else:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
        present = {str(row[0]) for row in rows}
    missing = [table for table in REQUIRED_TABLES if table not in present]
    return {
        "dialect": normalized,
        "ok": not missing,
        "missing": missing,
        "required": list(REQUIRED_TABLES),
    }
