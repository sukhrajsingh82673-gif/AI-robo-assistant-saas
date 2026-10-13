"""
Tests for PostgreSQL / SQLite Dual-Compatible SQL Dialect Qualification.
Verifies that all upsert operations use ANSI SQL ON CONFLICT statements compatible
with both PostgreSQL 16 and SQLite 3.24+, that created_at is preserved across conflict
resolutions, that composite primary keys resolve correctly, and that SQL normalizer
handles PostgreSQL translation with full defense in depth.
"""

import os
import re
import time
import uuid
import json
import sqlite3
import unittest
from typing import Dict, Any

import tempfile
from core.db import db, normalize_sql_for_postgres, TABLE_PRIMARY_KEYS, configure_isolated_test_db
from core.database_engine import engine, WorkloadType, DatabaseDialect
from core.automation_fabric.data_integration_engine import SyncCheckpointManager
from core.enterprise_files import EnterpriseFilesEngine

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "dialect_test_isolated.db")
    configure_isolated_test_db(isolated_db)
    SyncCheckpointManager._ensure_tables()
    EnterpriseFilesEngine(tenant_id="tnt_init")._init_db()

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestPostgreSqlDialectCompatibility(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_dialect_{uuid.uuid4().hex[:8]}"
        self.company_id = f"comp_dialect_{uuid.uuid4().hex[:8]}"
        now = time.time()
        # Seed test tenant & company
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tenants (tenant_id, name, plan, status, created_at)
                VALUES (?, 'Dialect Test Tenant', 'ENTERPRISE', 'ACTIVE', ?)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                (self.tenant_id, now)
            )
            conn.execute(
                """
                INSERT INTO companies (
                    company_id, tenant_id, name, country, industry, company_type, status, created_at
                ) VALUES (?, ?, 'Dialect Corp', 'IN', 'TECH', 'EXISTING', 'OPERATIONAL', ?)
                ON CONFLICT (company_id) DO NOTHING
                """,
                (self.company_id, self.tenant_id, now)
            )
            conn.commit()

    def test_01_codebase_has_zero_insert_or_replace(self):
        """Verify that zero INSERT OR REPLACE statements exist in core/ or api_server.py."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_paths = [
            os.path.join(repo_root, "api_server.py"),
            os.path.join(repo_root, "core"),
            os.path.join(repo_root, "zonata")
        ]
        
        violations = []
        pattern = re.compile(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", re.IGNORECASE)

        for target in target_paths:
            if os.path.isfile(target):
                files = [target]
            else:
                files = []
                for root, _, filenames in os.walk(target):
                    for fn in filenames:
                        if fn.endswith(".py"):
                            files.append(os.path.join(root, fn))

            for fpath in files:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f, 1):
                        # Skip comment lines explaining normalizer in db.py
                        if "core/db.py" in fpath and ("#" in line or "Converts" in line):
                            continue
                        if pattern.search(line):
                            violations.append(f"{os.path.relpath(fpath, repo_root)}:{line_idx}: {line.strip()}")

        self.assertEqual(violations, [], f"Found disallowed SQLite INSERT OR REPLACE statements: {violations}")

    def test_02_sql_normalizer_pragma_stripping(self):
        """Verify that SQLite-specific PRAGMA commands are stripped for PostgreSQL."""
        self.assertEqual(normalize_sql_for_postgres("PRAGMA foreign_keys = ON;"), "")
        self.assertEqual(normalize_sql_for_postgres("  pragma journal_mode = WAL "), "")
        self.assertEqual(normalize_sql_for_postgres("PRAGMA busy_timeout = 5000"), "")

    def test_03_sql_normalizer_parameter_placeholder_conversion(self):
        """Verify that ? parameter placeholders are converted to %s."""
        sql = "SELECT * FROM users WHERE tenant_id = ? AND status = ?"
        normalized = normalize_sql_for_postgres(sql)
        self.assertEqual(normalized, "SELECT * FROM users WHERE tenant_id = %s AND status = %s")

    def test_04_sql_normalizer_insert_or_ignore(self):
        """Verify that INSERT OR IGNORE is translated to ANSI ON CONFLICT DO NOTHING."""
        sql = "INSERT OR IGNORE INTO tenants (tenant_id, name) VALUES (?, ?)"
        normalized = normalize_sql_for_postgres(sql)
        self.assertIn("INSERT INTO tenants", normalized)
        self.assertIn("ON CONFLICT DO NOTHING", normalized)
        self.assertNotIn("INSERT OR IGNORE", normalized)
        self.assertIn("%s", normalized)

    def test_05_sql_normalizer_insert_or_replace_fallback(self):
        """Verify defense-in-depth normalization of legacy/dynamic INSERT OR REPLACE queries."""
        sql = "INSERT OR REPLACE INTO missions (mission_id, company_id, tenant_id, title, created_at) VALUES (?, ?, ?, ?, ?)"
        normalized = normalize_sql_for_postgres(sql)
        self.assertIn("INSERT INTO missions", normalized)
        self.assertIn("ON CONFLICT (mission_id) DO UPDATE SET", normalized)
        self.assertIn("company_id = EXCLUDED.company_id", normalized)
        self.assertIn("tenant_id = EXCLUDED.tenant_id", normalized)
        self.assertIn("title = EXCLUDED.title", normalized)
        # created_at MUST be excluded from UPDATE SET to preserve audit history
        self.assertNotIn("created_at = EXCLUDED.created_at", normalized)

    def test_06_sql_normalizer_composite_pk_fallback(self):
        """Verify defense-in-depth normalizer correctly identifies composite primary keys."""
        sql = "INSERT OR REPLACE INTO automation_sync_checkpoints (tenant_id, stream_name, connector_id, cursor_value, records_synced) VALUES (?, ?, ?, ?, ?)"
        normalized = normalize_sql_for_postgres(sql)
        self.assertIn("ON CONFLICT (tenant_id, stream_name, connector_id) DO UPDATE SET", normalized)
        self.assertIn("cursor_value = EXCLUDED.cursor_value", normalized)
        self.assertIn("records_synced = EXCLUDED.records_synced", normalized)

    def test_07_ansi_upsert_preserves_created_at_on_conflict(self):
        """Verify that ANSI ON CONFLICT DO UPDATE SET preserves the initial created_at timestamp."""
        agent_id = f"agt_upsert_{uuid.uuid4().hex[:8]}"
        initial_time = 1700000000.0
        updated_time = 1700009999.0

        # Initial insertion
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO employees (
                    agent_id, company_id, tenant_id, role, department, manager,
                    budget_limit, spending_limit, authority_ceiling, working_state, created_at
                ) VALUES (?, ?, ?, 'Analyst', 'Operations', 'AI CEO', 1000.0, 500.0, 'AUTO', 'IDLE', ?)
                ON CONFLICT (agent_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    working_state = EXCLUDED.working_state
                """,
                (agent_id, self.company_id, self.tenant_id, initial_time)
            )
            conn.commit()

        # Verify initial created_at
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM employees WHERE agent_id = ?", (agent_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["created_at"], initial_time)
            self.assertEqual(row["role"], "Analyst")
            self.assertEqual(row["working_state"], "IDLE")

        # Upsert with different state, role, and newer created_at
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO employees (
                    agent_id, company_id, tenant_id, role, department, manager,
                    budget_limit, spending_limit, authority_ceiling, working_state, created_at
                ) VALUES (?, ?, ?, 'Lead Analyst', 'Operations', 'AI CEO', 1000.0, 500.0, 'AUTO', 'ACTIVE', ?)
                ON CONFLICT (agent_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    working_state = EXCLUDED.working_state
                """,
                (agent_id, self.company_id, self.tenant_id, updated_time)
            )
            conn.commit()

        # Verify: role & working_state were updated, but created_at was PRESERVED
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM employees WHERE agent_id = ?", (agent_id,)).fetchone()
            self.assertEqual(row["role"], "Lead Analyst")
            self.assertEqual(row["working_state"], "ACTIVE")
            self.assertEqual(row["created_at"], initial_time)  # Preserved!

    def test_08_composite_primary_key_upsert(self):
        """Verify upsert behavior on tables with multi-column composite primary keys."""
        stream_name = "stream_telemetry"
        connector_id = "conn_stream_01"
        initial_time = time.time()

        # First insert
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO automation_sync_checkpoints (
                    tenant_id, stream_name, connector_id, cursor_value, cursor_type,
                    records_synced, last_sync_timestamp, content_checksum, status, metadata
                ) VALUES (?, ?, ?, 'cursor_v1', 'TOKEN', 10, ?, 'chk1', 'ACTIVE', '{}')
                ON CONFLICT (tenant_id, stream_name, connector_id) DO UPDATE SET
                    cursor_value = EXCLUDED.cursor_value,
                    records_synced = EXCLUDED.records_synced,
                    last_sync_timestamp = EXCLUDED.last_sync_timestamp,
                    content_checksum = EXCLUDED.content_checksum,
                    status = EXCLUDED.status
                """,
                (self.tenant_id, stream_name, connector_id, initial_time)
            )
            conn.commit()

        # Update via upsert
        next_time = initial_time + 60.0
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO automation_sync_checkpoints (
                    tenant_id, stream_name, connector_id, cursor_value, cursor_type,
                    records_synced, last_sync_timestamp, content_checksum, status, metadata
                ) VALUES (?, ?, ?, 'cursor_v2', 'TOKEN', 50, ?, 'chk2', 'COMPLETED', '{}')
                ON CONFLICT (tenant_id, stream_name, connector_id) DO UPDATE SET
                    cursor_value = EXCLUDED.cursor_value,
                    records_synced = EXCLUDED.records_synced,
                    last_sync_timestamp = EXCLUDED.last_sync_timestamp,
                    content_checksum = EXCLUDED.content_checksum,
                    status = EXCLUDED.status
                """,
                (self.tenant_id, stream_name, connector_id, next_time)
            )
            conn.commit()

        # Verify only one row exists and was updated properly
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM automation_sync_checkpoints WHERE tenant_id = ? AND stream_name = ? AND connector_id = ?",
                (self.tenant_id, stream_name, connector_id)
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["cursor_value"], "cursor_v2")
            self.assertEqual(rows[0]["records_synced"], 50)
            self.assertEqual(rows[0]["status"], "COMPLETED")

    def test_09_tenant_isolation_in_conflict_upsert(self):
        """Verify that tenant isolation boundaries are preserved during conflict operations."""
        other_tenant = f"tnt_other_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, 'Other', 'ENTERPRISE', 'ACTIVE', ?) ON CONFLICT (tenant_id) DO NOTHING",
                (other_tenant, time.time())
            )
            conn.commit()

        file_id = f"file_{uuid.uuid4().hex[:8]}"
        now = time.time()

        # Create file under self.tenant_id
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO enterprise_files (
                    file_id, tenant_id, company_id, department, name, category,
                    document_type, size_bytes, sha256, classification, version,
                    storage_path, linked_records, tags, uploaded_by, summary,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 'OPS', 'manifest.json', 'REPORT', 'JSON', 100, 'sha1', 'INTERNAL', 1, '/path', '[]', '[]', 'user', 'sum', ?, ?)
                ON CONFLICT (file_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = EXCLUDED.updated_at
                """,
                (file_id, self.tenant_id, self.company_id, now, now)
            )
            conn.commit()

        # Verification: file is scoped to self.tenant_id
        with db.get_connection() as conn:
            r1 = conn.execute("SELECT * FROM enterprise_files WHERE file_id = ? AND tenant_id = ?", (file_id, self.tenant_id)).fetchone()
            self.assertIsNotNone(r1)
            r2 = conn.execute("SELECT * FROM enterprise_files WHERE file_id = ? AND tenant_id = ?", (file_id, other_tenant)).fetchone()
            self.assertIsNone(r2)


if __name__ == "__main__":
    unittest.main()
