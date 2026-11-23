"""
ZONATA Eval Harness Subsystem Schema
OpenCode Step 2K: Schema initialization and migrations for eval runs and qualification.
"""

import os
import pathlib
from core.db import db, DatabaseDialect


def ensure_eval_tables(conn=None):
    """Initializes the Eval Harness and Qualification database tables."""
    migration_file = "0028_eval_harness.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    if conn is not None:
        if hasattr(conn, "executescript") and getattr(db, "dialect", None) == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                conn.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                conn.execute(sql_path.read_text(encoding="utf-8"))
        return

    with db.get_connection() as connection:
        if getattr(db, "dialect", None) == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                connection.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                connection.execute(sql_path.read_text(encoding="utf-8"))
