#!/usr/bin/env python3
"""Apply the additive Settings V2 schema to PostgreSQL.

The Settings V2 tables are owned by ``core.settings.schema`` rather than the
general migration engine.  This script is the deployment path for them: it is
idempotent, records checksums in ``settings_schema_migrations``, and refuses to
run if an already-applied migration file changed.

Usage:

    python3 deploy/free_tier/apply_settings_v2_schema.py --env-file .env
    python3 deploy/free_tier/apply_settings_v2_schema.py --database-url "$DATABASE_URL"

DDL uses the direct Neon compute endpoint (``-pooler`` removed) because schema
changes must not run through the transaction pooler.  The URL is never printed
with credentials.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from core.db import db, sanitize_db_url  # noqa: E402


def _read_env_file(path):
    values = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main():
    parser = argparse.ArgumentParser(description="Apply the Settings V2 PostgreSQL schema.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--env-file", help="Read DATABASE_URL from this file when it is not in the environment.")
    args = parser.parse_args()

    url = args.database_url
    if not url and args.env_file:
        url = _read_env_file(args.env_file).get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL is required (or pass --env-file).")

    migration_url = url.strip().replace("-pooler.", ".")
    os.environ["DATABASE_URL"] = migration_url
    os.environ["ZONATA_DB_DIALECT"] = "postgresql"
    db.database_url = migration_url
    db.dialect = "postgresql"
    db._is_ready = False
    if getattr(db, "_pg_pool", None):
        db._pg_pool.close_all()
        db._pg_pool = None

    print(f"Target: {sanitize_db_url(migration_url)}")
    db.verify_readiness()

    from core.settings.schema import verify_schema
    from core.settings.service import settings_v2_service

    applied = settings_v2_service.ensure_schema(dialect="postgresql")
    with db.get_connection() as conn:
        verification = verify_schema(conn, "postgresql")

    report = {
        "status": "SUCCESS" if verification["ok"] else "INCOMPLETE",
        "target": sanitize_db_url(migration_url),
        "schema": applied,
        "verification": verification,
    }
    print(json.dumps(report, indent=2))
    return 0 if verification["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
