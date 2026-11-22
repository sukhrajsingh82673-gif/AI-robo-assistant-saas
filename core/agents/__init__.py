"""ZONATA Sovereign Core — Agent Runtime and Governance (OpenCode Step 2E)."""

from typing import Optional, Any
import pathlib
from core.db import db, DatabaseDialect

from core.agents.runtime import (
    ZonataAgentRuntime,
    AgentRunStatus,
)
from core.agents.certification import (
    AgentCertificationStatus,
    AgentCertificationService,
    certification_service,
)


def ensure_agent_runtime_tables(conn: Optional[Any] = None) -> None:
    """Ensures agent_runs, agent_run_steps, agent_certifications, and calendar_events exist."""
    migration_file = "0022_agent_runtime_and_tools.sql"
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
            connection.commit()
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                connection.execute(sql_path.read_text(encoding="utf-8"))


# Ensure tables on import
try:
    ensure_agent_runtime_tables()
except Exception:
    pass

__all__ = [
    "ZonataAgentRuntime",
    "AgentRunStatus",
    "AgentCertificationStatus",
    "AgentCertificationService",
    "certification_service",
    "ensure_agent_runtime_tables",
]
