"""
ZONATA Workforce Work Kernel (OpenCode Step 2F).
Missions, Projects, Tasks, DAG Dependencies, Deterministic Assignment,
Human Inbox, and SLA Escalation Engine.
"""

from typing import Optional, Any
import pathlib
from core.db import db, DatabaseDialect

from core.work.types import (
    TaskStatus,
    TaskPriority,
    AssigneeType,
    InboxItemType,
    InboxStatus,
    WorkKernelError,
    IllegalStateTransitionError,
    AssigneeSelfCompletionForbiddenError,
    TaskDependencyCycleError,
    PrerequisiteNotCompletedError,
    TaskNotFoundError,
    MissionNotFoundError,
    ProjectNotFoundError,
    CapabilityNotLiveBlockedError,
    InboxItemNotFoundError,
    TaskAssignmentIneligibleError,
    MissionCreateRequest,
    ProjectCreateRequest,
    TaskCreateRequest,
    TaskSubmitRequest,
    TaskVerifyRequest,
)

from core.work.state_machine import TaskStateMachine, VALID_TRANSITIONS
from core.work.dag import TaskDAGService
from core.work.assignment import TaskAssignmentEngine
from core.work.inbox import HumanInboxService, human_inbox_service
from core.work.sla import ClockManager, WorkSLAService, work_sla_service
from core.work.service import WorkforceWorkService, workforce_work_service


def ensure_work_kernel_tables(conn: Optional[Any] = None) -> None:
    """Ensures work_missions, work_projects, work_tasks, task_dependencies, task_events, and human_inbox exist."""
    migration_file = "0023_work_kernel.sql"
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
    ensure_work_kernel_tables()
except Exception:
    pass
