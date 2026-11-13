"""Company-scoped permission model.

Tenant roles are coarse (OWNER/EXECUTIVE/MANAGER/...). Company setup needs a
second axis: a per-company allow-list of admins, and a hard rule that an AI
agent can prepare drafts but can never submit, change settings, or delete a
company.

Every decision below is deny-by-default and is enforced on the server. The
client may hide buttons, but it is never the authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

AGENT_ROLES = {"SYSTEM_AGENT", "AI_AGENT", "AUTONOMOUS_AGENT"}
AGENT_ID_PREFIXES = ("agent_", "agt_", "ai_agent_")
AGENT_PRINCIPAL_TYPES = {"AGENT", "AI_AGENT", "SYSTEM_AGENT", "AUTONOMOUS_AGENT"}

OWNER_ROLES = {"OWNER"}
GLOBAL_ADMIN_ROLES = {"GLOBAL_ADMIN"}
ADMIN_ROLES = OWNER_ROLES | GLOBAL_ADMIN_ROLES | {"EXECUTIVE"}


class PermissionDenied(Exception):
    """Raised when a principal may not perform a company action."""

    def __init__(self, action: str, reason: str = ""):
        self.action = action
        self.reason = reason or f"Role is not permitted to {action}"
        super().__init__(self.reason)


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role: str
    company_id: Optional[str] = None
    principal_type: str = "USER"

    @classmethod
    def from_auth_context(cls, ctx: Optional[Dict[str, Any]]) -> "Principal":
        ctx = ctx or {}
        return cls(
            user_id=str(ctx.get("user_id") or "usr_unknown"),
            tenant_id=str(ctx.get("tenant_id") or ""),
            role=str(ctx.get("role") or "OBSERVER").upper(),
            company_id=ctx.get("company_id"),
            principal_type=str(ctx.get("principal_type") or "USER").upper(),
        )

    @property
    def is_agent(self) -> bool:
        if self.principal_type in AGENT_PRINCIPAL_TYPES:
            return True
        if self.role in AGENT_ROLES:
            return True
        return str(self.user_id).lower().startswith(AGENT_ID_PREFIXES)

    @property
    def is_owner(self) -> bool:
        return self.role in OWNER_ROLES or self.role in GLOBAL_ADMIN_ROLES

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_ROLES

    def assert_tenant(self, tenant_id: str) -> None:
        if not self.tenant_id or self.tenant_id != tenant_id:
            raise PermissionDenied("access", "Authenticated tenant does not match the requested tenant")


def _deny(action: str, reason: str = ""):
    raise PermissionDenied(action, reason)


def can_view(principal: Principal) -> bool:
    # Any authenticated member of the tenant may read; agents included.
    return bool(principal.tenant_id)


def can_create(principal: Principal) -> bool:
    """Only the owner and admins may add a company. Agents never."""
    if principal.is_agent:
        return False
    return principal.role in ADMIN_ROLES


def can_draft(principal: Principal) -> bool:
    """Agents and members may prepare drafts (nothing is committed)."""
    return bool(principal.tenant_id)


def can_edit(principal: Principal, granted: bool = False) -> bool:
    if principal.is_agent:
        return False
    if principal.is_owner:
        return True
    return principal.role in ADMIN_ROLES and granted


def can_submit(principal: Principal, granted: bool = False) -> bool:
    # Submitting commits the company and starts real work; agents may never.
    return can_edit(principal, granted=granted)


def can_delete(principal: Principal, granted: bool = False) -> bool:
    """Deletion is owner-only unless the owner explicitly granted an admin."""
    if principal.is_agent:
        return False
    if principal.is_owner:
        return True
    return principal.role in ADMIN_ROLES and granted


def can_manage_settings(principal: Principal) -> bool:
    if principal.is_agent:
        return False
    return principal.is_owner


def can_manage_connections(principal: Principal, granted: bool = False) -> bool:
    return can_edit(principal, granted=granted)


def require(condition: bool, action: str, reason: str = "") -> None:
    if not condition:
        _deny(action, reason)


def assert_can_view(principal: Principal, tenant_id: str) -> None:
    principal.assert_tenant(tenant_id)
    require(can_view(principal), "view company")


def assert_can_create(principal: Principal, tenant_id: str) -> None:
    principal.assert_tenant(tenant_id)
    require(
        can_create(principal),
        "add a company",
        "Only the owner or an allowed admin may add a company",
    )


def assert_can_draft(principal: Principal, tenant_id: str) -> None:
    principal.assert_tenant(tenant_id)


def assert_can_edit(principal: Principal, tenant_id: str, granted: bool = False) -> None:
    principal.assert_tenant(tenant_id)
    require(
        can_edit(principal, granted=granted),
        "edit company",
        "Only the owner or an allowed admin may edit a company",
    )


def assert_can_submit(principal: Principal, tenant_id: str, granted: bool = False) -> None:
    principal.assert_tenant(tenant_id)
    require(
        can_submit(principal, granted=granted),
        "submit company",
        "Agents and unapproved members cannot submit a company",
    )


def assert_can_delete(principal: Principal, tenant_id: str, granted: bool = False) -> None:
    principal.assert_tenant(tenant_id)
    require(
        can_delete(principal, granted=granted),
        "delete company",
        "Only the owner or an allowed admin may delete a company; agents never can",
    )
