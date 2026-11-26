"""
OpenCode Step 2B — Sovereign LLM Gateway, Tiers, Hierarchical Budgets, and Prompt Registry.
"""

from typing import Optional, Any
import pathlib
from core.db import db, DatabaseDialect


def ensure_model_gateway_tables(conn: Optional[Any] = None) -> None:
    """Ensures llm_budget_hierarchies, model_calls, and tenant_model_policies exist with multi-tenant RLS."""
    migration_file = "0019_model_gateway_and_budgets.sql"
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
