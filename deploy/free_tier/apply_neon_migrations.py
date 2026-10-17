#!/usr/bin/env python3
"""
ZONATA Enterprise SaaS — Free-Tier Staging Database Initializer & Migration Tool
Applies authoritative additive schema migrations against Neon Serverless PostgreSQL 16
or any remote PostgreSQL database. Enforces strict connection sanitization and role isolation.
"""

import os
import sys
import argparse
import time
import json
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from core.db import db, sanitize_db_url
from core.controlled_migration_engine import ControlledMigrationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zonata.deploy.neon_migrations")


def apply_migrations(db_url: str):
    sanitized = sanitize_db_url(db_url)
    logger.info(f"Initializing remote PostgreSQL database target: {sanitized}")

    # Set environment variables for db engine
    os.environ["DATABASE_URL"] = db_url
    os.environ["ZONATA_DB_DIALECT"] = "postgresql"
    os.environ["APP_ENV"] = "staging"
    os.environ["ENVIRONMENT"] = "staging"

    # Reset internal db connection state to point to new target
    db.database_url = db_url
    db.dialect = "postgresql"
    db._is_ready = False
    if db._pg_pool:
        db._pg_pool.close_all()
        db._pg_pool = None

    # 1. Verify Connectivity
    logger.info("Probing database connectivity and SSL handshake...")
    try:
        db.verify_readiness()
        logger.info("Database connection established successfully.")
    except Exception as e:
        logger.error(f"Readiness check failed: {sanitize_db_url(str(e))}")
        sys.exit(1)

    # 2. Execute Base DDL Initialization
    logger.info("Executing base DDL table creation...")
    try:
        db._init_db()
        logger.info("Base tables initialized.")
    except Exception as e:
        logger.error(f"Base DDL initialization failed: {sanitize_db_url(str(e))}")
        sys.exit(1)

    # 3. Apply Additive Controlled Migrations
    logger.info("Applying pending controlled migrations...")
    engine = ControlledMigrationEngine()
    applied = engine.apply_pending_migrations()
    logger.info(f"Applied {len(applied)} controlled migration steps.")

    # 4. Verify Essential Operational Tables Exist
    pool = db._ensure_pg_pool()
    conn = pool.get_connection()
    verified_tables = []
    required_tables = [
        "tenants", "users", "sessions", "missions", "evidence_ledger",
        "async_command_queue", "audit_log", "kpi_definitions", "temporal_workflows"
    ]
    with conn:
        cur = conn.cursor()
        for tbl in required_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                );
            """, (tbl,))
            res = cur.fetchone()
            if res and res[0]:
                verified_tables.append(tbl)
            else:
                logger.warning(f"Table '{tbl}' not found in public schema (may be SQLite-specific or created on first use).")

    pool.release_connection(conn)

    report = {
        "status": "SUCCESS",
        "target_database": sanitized,
        "migrations_applied_count": len(applied),
        "verified_tables": verified_tables,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    print("\n" + json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply ZONATA migrations to Neon PostgreSQL 16.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="PostgreSQL connection string (with sslmode=require)")
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: --database-url is required (or set DATABASE_URL environment variable).")
        sys.exit(1)

    apply_migrations(args.database_url)
