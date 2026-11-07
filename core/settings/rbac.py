"""Role-based access control for Settings V2.

Identity comes from the verified bearer token only.  Request headers such as
``X-User-Role`` are never consulted here.  The legacy API is being migrated to
call this module, and the new ``/api/settings/v2`` surface uses it exclusively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, Optional

from core.settings.errors import PermissionDenied, ScopeError
from core.settings.models import ActorType, ScopeType, SettingDefinition

ROLE_OWNER = "OWNER"
ROLE_GLOBAL_ADMIN = "GLOBAL_ADMIN"
ROLE_EXECUTIVE = "EXECUTIVE"
ROLE_MANAGER = "MANAGER"
ROLE_OPERATOR = "OPERATOR"
ROLE_OBSERVER = "OBSERVER"
ROLE_AUDITOR = "AUDITOR"
ROLE_SYSTEM_AGENT = "SYSTEM_AGENT"

ALL_PERMISSIONS = frozenset(
    {
        "settings.read",
        "settings.write",
        "settings.lock",
        "secrets.manage",
        "security.manage",
        "billing.manage",
        "agents.manage",
        "users.manage",
        "audit.read",
        "infrastructure.manage",
        "danger.manage",
    }
)

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    ROLE_OWNER: ALL_PERMISSIONS,
    ROLE_GLOBAL_ADMIN: ALL_PERMISSIONS,
    ROLE_EXECUTIVE: frozenset(
        {
            "settings.read",
            "settings.write",
            "settings.lock",
            "security.manage",
            "billing.manage",
            "agents.manage",
            "users.manage",
            "audit.read",
            "infrastructure.manage",
        }
    ),
    ROLE_MANAGER: frozenset(
        {
            "settings.read",
            "settings.write",
            "agents.manage",
            "audit.read",
        }
    ),
    ROLE_OPERATOR: frozenset(
        {
            "settings.read",
            "settings.write",
        }
    ),
    ROLE_OBSERVER: frozenset({"settings.read"}),
    ROLE_AUDITOR: frozenset({"settings.read", "audit.read"}),
    ROLE_SYSTEM_AGENT: frozenset({"settings.read"}),
}

# Categories whose changes an agent may never apply directly.
AGENT_RESTRICTED_CATEGORIES = frozenset(
    {
        "host",
        "security",
        "governance",
        "privacy",
        "compliance",
        "audit",
        "enterprise",
        "finance",
        "usage",
        "billing",
        "users",
        "approvals",
        "danger",
    }
)

# Keys that describe the AI CEO's own limits.  An agent-originated proposal may
# not increase them, and a human must originate any change.
CEO_SELF_LIMIT_KEYS = frozenset(
    {
        "ceo_spending_limit",
        "ceo_autonomy_level",
        "ceo_continuous_cognition_mins",
        "mission_retry_limit",
    }
)


@dataclass(frozen=True)
class Principal:
    """Verified caller identity."""

    user_id: str
    tenant_id: str
    company_id: str
    role: str
    permissions: FrozenSet[str] = field(default_factory=frozenset)
    actor_type: ActorType = ActorType.HUMAN

    @classmethod
    def from_auth_context(cls, context: Dict[str, Any]) -> "Principal":
        role = str(context.get("role") or ROLE_OBSERVER).upper()
        raw_actor = context.get("actor_type")
        if raw_actor:
            try:
                actor_type = ActorType(str(raw_actor).lower())
            except ValueError:
                actor_type = ActorType.AGENT if role == ROLE_SYSTEM_AGENT else ActorType.HUMAN
        else:
            # A token without an explicit actor type is human unless its role
            # is the agent role.  Defaulting to "human" first would let an
            # agent token take the human write path.
            actor_type = ActorType.AGENT if role == ROLE_SYSTEM_AGENT else ActorType.HUMAN
        raw_permissions = context.get("permissions") or []
        if isinstance(raw_permissions, str):
            raw_permissions = [raw_permissions]
        permissions = frozenset(str(item) for item in raw_permissions if str(item) != "*")
        return cls(
            user_id=str(context.get("user_id") or "unknown"),
            tenant_id=str(context.get("tenant_id") or ""),
            company_id=str(context.get("company_id") or ""),
            role=role,
            permissions=permissions,
            actor_type=actor_type,
        )

    @property
    def is_privileged(self) -> bool:
        return self.role in (ROLE_OWNER, ROLE_GLOBAL_ADMIN)

    @property
    def is_approver(self) -> bool:
        return self.role in (ROLE_OWNER, ROLE_EXECUTIVE, ROLE_GLOBAL_ADMIN)


def has_permission(principal: Principal, permission: str) -> bool:
    if principal.role in (ROLE_OWNER, ROLE_GLOBAL_ADMIN):
        return True
    if permission in ROLE_PERMISSIONS.get(principal.role, frozenset()):
        return True
    # Specific token permissions are honoured; the "*" wildcard is not, so a
    # token issued with a broad permission list cannot silently become an owner.
    return permission in principal.permissions


def require_permission(principal: Principal, permission: str) -> None:
    if not has_permission(principal, permission):
        raise PermissionDenied(
            f"Permission '{permission}' is required for this operation.",
        )


def can_access_company(conn: Any, principal: Principal, company_id: str) -> bool:
    if principal.role == ROLE_GLOBAL_ADMIN:
        return True
    if principal.tenant_id and company_id:
        # The company must belong to the principal's tenant.
        try:
            row = conn.execute(
                "SELECT 1 FROM companies WHERE company_id = ? AND tenant_id = ?",
                (company_id, principal.tenant_id),
            ).fetchone()
            if row is None:
                return False
        except Exception:
            # Older test databases may not have companies; fall back to the
            # token's own company rather than granting arbitrary access.
            return company_id == principal.company_id
    if principal.is_privileged or principal.role == ROLE_EXECUTIVE:
        return True
    if company_id == principal.company_id:
        return True
    try:
        row = conn.execute(
            "SELECT 1 FROM user_company_roles WHERE user_id = ? AND company_id = ? AND tenant_id = ?",
            (principal.user_id, company_id, principal.tenant_id),
        ).fetchone()
        if row is not None:
            return True
        assigned = conn.execute(
            "SELECT COUNT(*) FROM user_company_roles WHERE user_id = ? AND tenant_id = ?",
            (principal.user_id, principal.tenant_id),
        ).fetchone()
        # If the user has explicit assignments, the token's default company does
        # not widen them.  If there are none, the token company is the only
        # membership we can prove, and it is not the company being requested.
        if assigned and int(assigned[0]) > 0:
            return False
        return company_id == principal.company_id
    except Exception:
        return company_id == principal.company_id


def require_scope(
    conn: Any,
    principal: Principal,
    scope_type: ScopeType,
    scope_id: str,
    company_id: str,
) -> None:
    if not scope_id:
        raise ScopeError("scope_id is required for a scoped setting.")
    if scope_type is ScopeType.PLATFORM:
        if principal.role != ROLE_GLOBAL_ADMIN:
            raise PermissionDenied("Only a global administrator may write platform scope.")
        return
    if scope_type is ScopeType.ORGANIZATION:
        if not principal.is_privileged:
            raise PermissionDenied("Only the organization owner may write organization scope.")
        if scope_id != principal.tenant_id:
            raise PermissionDenied("Organization scope must match the authenticated tenant.")
        return
    if not can_access_company(conn, principal, company_id):
        raise PermissionDenied("The requested company is outside the authenticated membership.")
    # Department, agent and user scope IDs are validated by the caller against
    # their company-specific tables; the company membership check above is the
    # security boundary.


def require_write(
    conn: Any,
    principal: Principal,
    definition: SettingDefinition,
    scope_type: ScopeType,
    scope_id: str,
    company_id: str,
) -> None:
    require_permission(principal, definition.required_permission)
    require_scope(conn, principal, scope_type, scope_id, company_id)
    if principal.actor_type is ActorType.AGENT:
        if definition.secret or definition.requires_approval:
            raise PermissionDenied("Agents may propose this change but may not apply it.")
        if definition.risk.upper() in ("HIGH", "CRITICAL") or definition.category in AGENT_RESTRICTED_CATEGORIES:
            raise PermissionDenied("Agents may propose this change but may not apply it.")


def require_lock(conn: Any, principal: Principal, scope_type: ScopeType, scope_id: str, company_id: str) -> None:
    require_permission(principal, "settings.lock")
    require_scope(conn, principal, scope_type, scope_id, company_id)
    if scope_type in (ScopeType.PLATFORM, ScopeType.ORGANIZATION) and not principal.is_privileged:
        raise PermissionDenied("Only the owner may lock platform or organization scope.")


def require_secret_management(conn: Any, principal: Principal, company_id: str) -> None:
    require_permission(principal, "secrets.manage")
    if not can_access_company(conn, principal, company_id):
        raise PermissionDenied("The requested company is outside the authenticated membership.")
    if principal.actor_type is ActorType.AGENT:
        raise PermissionDenied("Agents may never write secrets.")


def require_approver(principal: Principal) -> None:
    if not principal.is_approver:
        raise PermissionDenied("Only an Owner, Executive, or Global Admin may decide approvals.")


def is_ceo_self_limit(key: str) -> bool:
    return key in CEO_SELF_LIMIT_KEYS
