"""
ZONATA Organization Model: Board to Agent (OpenCode Step 2D)
"""

from typing import Optional, Any
import pathlib
from core.db import db, DatabaseDialect

from core.organization.types import (
    OrgLevel,
    OccupantType,
    AssignmentStatus,
    HandoverStatus,
    OrganizationError,
    SingleCEOViolationError,
    ReportingCycleError,
    AgentHierarchyViolationError,
    AIOrganizationSelfEditError,
    VacantPositionError,
    PositionNotFoundError,
    DepartmentNotFoundError,
)
from core.organization.pack_roles import (
    INDUSTRY_ORG_TEMPLATES,
    resolve_org_template_for_pack,
)
from core.organization.service import (
    OrganizationService,
    organization_service,
)


def ensure_organization_tables(conn: Optional[Any] = None) -> None:
    """Ensures departments, positions, position_assignments, reporting_lines, board_principals, and handover_packs exist."""
    migration_file = "0021_organization_model.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    def _apply_additive_columns(c):
        for stmt in (
            "ALTER TABLE departments ADD COLUMN code TEXT",
            "ALTER TABLE departments ADD COLUMN lead_position_id TEXT",
            "ALTER TABLE departments ADD COLUMN budget_minor_units INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE departments ADD COLUMN updated_at REAL NOT NULL DEFAULT 0.0",
        ):
            try:
                c.execute(stmt)
            except Exception:
                pass

    if conn is not None:
        if hasattr(conn, "executescript") and getattr(db, "dialect", None) == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                conn.executescript(sql_path.read_text(encoding="utf-8"))
            _apply_additive_columns(conn.cursor())
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
            _apply_additive_columns(connection.cursor())
            connection.commit()
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                connection.execute(sql_path.read_text(encoding="utf-8"))


# Ensure tables on module import
try:
    ensure_organization_tables()
except Exception:
    pass
