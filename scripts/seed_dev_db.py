#!/usr/bin/env python3
"""
ZONATA Enterprise Development Database Seed Script.
Builds a synthetic development SQLite database from canonical schemas and migrations.
Guarantees clean, reproducible dev environment setup.
"""

import argparse
import hashlib
import os
import sqlite3
import sys
import time

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.db import db, DatabaseDialect
from migrations.migration_manager import MigrationManager
from tests.schema_bootstrap import init_all_subsystem_schemas, seed_baseline_tenant_scope


def seed_dev_database(db_path: str = None) -> str:
    """Builds and seeds a development database at db_path."""
    if not db_path:
        db_path = os.environ.get(
            "ZONATA_DB_PATH",
            os.path.join(REPO_ROOT, "storage", "roboassistant.db"),
        )

    db_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # If an existing file exists and we want a fresh seed, remove it
    if os.path.exists(db_path):
        print(f"[seed_dev_db] Removing existing dev database: {db_path}")
        os.remove(db_path)

    print(f"[seed_dev_db] Initializing new dev database at: {db_path}")

    # Point core.db to this database path
    db.db_path = db_path
    db.dialect = DatabaseDialect.SQLITE
    db._init_db()

    # Apply all pending migrations
    print("[seed_dev_db] Applying versioned migrations...")
    manager = MigrationManager()
    with db.get_connection() as conn:
        manager.init_migration_table(conn)
        applied = manager.get_applied_migrations(conn)
        available = manager.get_available_migrations(dialect="sqlite")
        for version, name, filepath in available:
            if version not in applied:
                print(f"  -> Applying migration {version}_{name} from {os.path.basename(filepath)}")
                checksum = manager.calculate_checksum(filepath)
                with open(filepath, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                from migrations.migration_manager import split_sql_statements
                stmts = split_sql_statements(sql_content, dialect="sqlite")
                t0 = time.time()
                for s in stmts:
                    conn.execute(s)
                dt = (time.time() - t0) * 1000.0
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum, applied_at, execution_time_ms, status) "
                    "VALUES (?, ?, ?, ?, ?, 'APPLIED')",
                    (version, name, checksum, time.time(), dt),
                )
        conn.commit()

    # Initialize all auxiliary subsystem schemas
    print("[seed_dev_db] Bootstrapping auxiliary subsystem schemas...")
    init_all_subsystem_schemas()

    # Seed baseline tenant scope
    print("[seed_dev_db] Seeding baseline tenants and companies...")
    seed_baseline_tenant_scope()

    # Seed synthetic dev user and company data
    print("[seed_dev_db] Seeding synthetic development records...")
    now = time.time()
    with db.get_connection() as conn:
        # Dev user and credentials (PBKDF2-HMAC-SHA256 for 'DevAdmin2026!')
        salt = "dev_salt_zonata_2026"
        pwd_hash = hashlib.pbkdf2_hmac("sha256", b"DevAdmin2026!", salt.encode("utf-8"), 100000).hex()
        conn.execute(
            """
            INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at)
            VALUES (?, ?, ?, ?, 'OWNER', 'ACTIVE', ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            ("usr_dev_admin", "tnt_primary", "admin@zonata.internal", "Dev Administrator", now),
        )
        conn.execute(
            """
            INSERT INTO auth_credentials (user_id, password_hash, salt, failed_attempts, locked_until, created_at, updated_at)
            VALUES (?, ?, ?, 0, 0, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            ("usr_dev_admin", pwd_hash, salt, now, now),
        )

        conn.commit()

        # Run integrity check
        cur = conn.execute("PRAGMA integrity_check;")
        res = cur.fetchone()
        assert res and res[0] == "ok", f"Integrity check failed: {res}"

        # Count tables
        cur = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        table_count = cur.fetchone()[0]

    size_kb = os.path.getsize(db_path) / 1024.0
    print(f"[seed_dev_db] SUCCESS: Database seeded with {table_count} tables ({size_kb:.1f} KB).")
    print(f"[seed_dev_db] Dev user: admin@zonata.internal / DevAdmin2026! (tenant: tnt_primary)")
    return db_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic dev database")
    parser.add_argument("--path", default=None, help="Target SQLite database path")
    args = parser.parse_args()
    seed_dev_database(args.path)
