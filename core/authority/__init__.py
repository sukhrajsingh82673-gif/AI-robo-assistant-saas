"""
ZONATA Canonical Authority, Approvals, Delegations, and Principal Separation (OpenCode Step 2C)
"""

from typing import Optional, Any
import pathlib
from core.db import db, DatabaseDialect

from core.authority.types import (
    ActionClass,
    RESERVED_ACTION_CLASSES,
    PrincipalType,
    GOVERNED_PRINCIPAL_TYPES,
    AutonomyLevel,
    AUTONOMY_RANK,
    AuthorityError,
    Rule15Violation,
    DelegationError,
    DelegationAuthorityExceededError,
    DelegationRevokedError,
    SelfApprovalError,
    AIApprovalError,
    PayloadDigestMismatchError,
    PolicyStepOutcome,
    PolicyDecisionResult,
)
from core.authority.profiles import (
    GRADE_AUTHORITY,
    TIER_RANK,
    AuthorityProfileManager,
    authority_profile_manager,
)
from core.authority.delegation import (
    DelegationManager,
    delegation_manager,
)
from core.authority.approvals import (
    HIGH_STAKES_ACTION_CLASSES,
    compute_payload_digest,
    ApprovalsManager,
    approvals_manager,
)
from core.authority.budget_guard import (
    SpendBudgetGuard,
    spend_budget_guard,
)
from core.authority.constitution import (
    ConstitutionManager,
    constitution_manager,
)
from core.authority.autonomy import (
    compute_effective_autonomy,
)


def ensure_authority_tables(conn: Optional[Any] = None) -> None:
    """Ensures policy_decisions, authority_profiles, authority_delegations, action_approvals, and company_constitutions exist."""
    migration_file = "0020_action_gateway_and_authority.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    if conn is not None:
        if not db.pg_tables_ready(
            conn,
            "policy_decisions",
            "authority_profiles",
            "authority_delegations",
            "action_approvals",
            "company_constitutions",
        ):
            if hasattr(conn, "executescript") and getattr(db, "dialect", None) == DatabaseDialect.SQLITE:
                sql_path = root_dir / "migrations" / "common" / migration_file
                if sql_path.exists():
                    conn.executescript(sql_path.read_text(encoding="utf-8"))
            else:
                sql_path = root_dir / "migrations" / "pg" / migration_file
                if sql_path.exists():
                    conn.execute(sql_path.read_text(encoding="utf-8"))
        spend_budget_guard._ensure_table(conn)
        return

    with db.get_connection() as connection:
        if not db.pg_tables_ready(
            connection,
            "policy_decisions",
            "authority_profiles",
            "authority_delegations",
            "action_approvals",
            "company_constitutions",
        ):
            if getattr(db, "dialect", None) == DatabaseDialect.SQLITE:
                sql_path = root_dir / "migrations" / "common" / migration_file
                if sql_path.exists():
                    connection.executescript(sql_path.read_text(encoding="utf-8"))
            else:
                sql_path = root_dir / "migrations" / "pg" / migration_file
                if sql_path.exists():
                    connection.execute(sql_path.read_text(encoding="utf-8"))
        spend_budget_guard._ensure_table(connection)


# Ensure tables on initial import
try:
    ensure_authority_tables()
except Exception:
    pass
