"""Typed models shared by the settings registry, resolver, API, and UI.

Only data and validation live here.  Importing this module must not touch the
database or the legacy settings service.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class ScopeType(str, Enum):
    """Broad-to-specific settings scopes from the enterprise specification."""

    PLATFORM = "platform"
    ORGANIZATION = "organization"
    COMPANY = "company"
    DEPARTMENT = "department"
    AGENT = "agent"
    USER = "user"


# Broadest first.  The resolver uses this order to select a lock.
SCOPE_BROAD_TO_SPECIFIC: Tuple[ScopeType, ...] = (
    ScopeType.PLATFORM,
    ScopeType.ORGANIZATION,
    ScopeType.COMPANY,
    ScopeType.DEPARTMENT,
    ScopeType.AGENT,
    ScopeType.USER,
)

# Most specific first.  The resolver uses this order when there is no lock.
SCOPE_SPECIFIC_TO_BROAD: Tuple[ScopeType, ...] = tuple(reversed(SCOPE_BROAD_TO_SPECIFIC))

SCOPE_INDEX: Dict[str, int] = {scope.value: index for index, scope in enumerate(SCOPE_BROAD_TO_SPECIFIC)}

SCOPE_LABELS: Dict[str, str] = {
    ScopeType.PLATFORM.value: "Platform",
    ScopeType.ORGANIZATION.value: "Organization",
    ScopeType.COMPANY.value: "Company",
    ScopeType.DEPARTMENT.value: "Department",
    ScopeType.AGENT.value: "Agent / Employee",
    ScopeType.USER.value: "User",
}


class SettingStatus(str, Enum):
    """Controls whether a definition may be rendered as a working control."""

    LIVE = "live"
    COMING_SOON = "coming_soon"
    HIDDEN = "hidden"
    ACTION = "action"


class ActorType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ValidationSpec:
    """Declarative validation derived from a setting definition.

    The legacy service has imperative validation.  This spec is the canonical
    description; the resolver and API validate against it in Phase 2.
    """

    value_type: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Tuple[Any, ...] = ()
    max_length: Optional[int] = None
    integer: bool = False
    allow_empty: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.value_type,
            "min": self.min_value,
            "max": self.max_value,
            "options": list(self.options),
            "max_length": self.max_length,
            "integer": self.integer,
            "allow_empty": self.allow_empty,
        }

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Return (valid, error).  Mirrors the legacy service's error shape."""
        value_type = self.value_type

        if value_type in ("number", "currency", "slider"):
            if value is None or value == "":
                return False, "Value cannot be empty."
            if isinstance(value, bool):
                return False, "Value must be numeric, not boolean."
            try:
                number = float(value)
            except (TypeError, ValueError):
                return False, "Value must be a valid numeric value."
            if self.min_value is not None and number < self.min_value:
                return False, f"Value {number} is below minimum {self.min_value}."
            if self.max_value is not None and number > self.max_value:
                return False, f"Value {number} exceeds maximum {self.max_value}."
            if self.integer and not float(number).is_integer():
                return False, "Value must be an integer."
            return True, None

        if value_type in ("select", "radio"):
            if not self.allow_empty and (value is None or value == ""):
                return False, "Value cannot be empty."
            if self.options and str(value) not in {str(option) for option in self.options}:
                return False, f"Value '{value}' is not one of {list(self.options)}."
            return True, None

        if value_type == "toggle":
            if not isinstance(value, bool):
                return False, "Value must be a boolean."
            return True, None

        if value_type in ("text", "token"):
            if value is None:
                return self.allow_empty, None if self.allow_empty else "Value cannot be empty."
            if self.max_length is not None and len(str(value)) > self.max_length:
                return False, f"Value exceeds maximum length {self.max_length}."
            if not self.allow_empty and str(value) == "":
                return False, "Value cannot be empty."
            return True, None

        if value_type == "multiselect":
            if isinstance(value, (list, tuple, set)):
                items = [str(item) for item in value]
            elif isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    items = [str(item) for item in parsed] if isinstance(parsed, list) else [
                        part.strip() for part in value.split(",") if part.strip()
                    ]
                except Exception:
                    items = [part.strip() for part in value.split(",") if part.strip()]
            else:
                return False, "Value must be a list of selections."
            if self.options:
                allowed = {str(option) for option in self.options}
                for item in items:
                    if item not in allowed:
                        return False, f"Value '{item}' is not one of {list(self.options)}."
            return True, None

        # status and button_action are display/action types, not values.
        return True, None


@dataclass(frozen=True)
class SettingDefinition:
    """One registry entry.  This is the single source of truth for a setting."""

    key: str
    section: str
    category: str
    label: str
    description: str
    value_type: str
    default: Any
    validation: ValidationSpec
    allowed_scopes: Tuple[ScopeType, ...]
    required_permission: str
    sensitive: bool = False
    secret: bool = False
    requires_restart: bool = False
    enforced_by: Optional[str] = None
    status: SettingStatus = SettingStatus.COMING_SOON
    risk: str = "LOW"
    editable_by: str = "OWNER"
    plan_gate: Optional[str] = None
    unit: Optional[str] = None
    legacy_scope: Optional[str] = None
    requires_approval: bool = False
    is_ceo_managed: bool = False
    action_id: Optional[str] = None

    @property
    def is_live(self) -> bool:
        return self.status is SettingStatus.LIVE

    @property
    def is_action(self) -> bool:
        return self.status is SettingStatus.ACTION

    def to_public_dict(self) -> Dict[str, Any]:
        """Serializable metadata.  Secret defaults are never returned."""
        default = "••••••••" if self.secret else self.default
        return {
            "key": self.key,
            "section": self.section,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "type": self.value_type,
            "default": default,
            "validation": self.validation.to_dict(),
            "allowed_scopes": [scope.value for scope in self.allowed_scopes],
            "required_permission": self.required_permission,
            "sensitive": self.sensitive,
            "secret": self.secret,
            "requires_restart": self.requires_restart,
            "enforced_by": self.enforced_by,
            "status": self.status.value,
            "risk": self.risk,
            "editable_by": self.editable_by,
            "plan_gate": self.plan_gate,
            "unit": self.unit,
            "legacy_scope": self.legacy_scope,
            "requires_approval": self.requires_approval,
            "is_ceo_managed": self.is_ceo_managed,
            "action_id": self.action_id,
        }


@dataclass(frozen=True)
class EffectiveSetting:
    """The resolved value plus the provenance the UI must show."""

    key: str
    value: Any
    source_scope: ScopeType
    source_id: str
    is_locked: bool
    locked_by_scope: Optional[ScopeType] = None
    locked_by_id: Optional[str] = None
    default_value: Any = None
    overridden_here: bool = False
    inherits_from: Optional[str] = None
    version: int = 1
    requires_restart: bool = False
    status: SettingStatus = SettingStatus.LIVE

    def provenance(self) -> str:
        if self.is_locked and self.locked_by_scope:
            return f"Locked by {SCOPE_LABELS.get(self.locked_by_scope.value, self.locked_by_scope.value)}"
        if self.overridden_here:
            return f"Overridden at {SCOPE_LABELS.get(self.source_scope.value, self.source_scope.value)}"
        if self.source_scope is ScopeType.PLATFORM and self.source_id in ("default", "env"):
            return "Platform default"
        return f"Inherited from {SCOPE_LABELS.get(self.source_scope.value, self.source_scope.value)}"

    def to_public_dict(self, sensitive: bool = False) -> Dict[str, Any]:
        value = "••••••••" if sensitive else self.value
        default_value = "••••••••" if sensitive else self.default_value
        return {
            "key": self.key,
            "value": value,
            "source_scope": self.source_scope.value,
            "source_id": self.source_id,
            "is_locked": self.is_locked,
            "locked_by_scope": self.locked_by_scope.value if self.locked_by_scope else None,
            "locked_by_id": self.locked_by_id,
            "default_value": default_value,
            "overridden_here": self.overridden_here,
            "inherits_from": self.inherits_from,
            "provenance": self.provenance(),
            "version": self.version,
            "requires_restart": self.requires_restart,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class SecretRef:
    """Public metadata for a write-only secret.  Never contains ciphertext."""

    name: str
    scope_type: ScopeType
    scope_id: str
    last4: str = ""
    key_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[float] = None
    rotated_at: Optional[float] = None
    last_used_at: Optional[float] = None
    configured: bool = False
    version: int = 1

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scope_type": self.scope_type.value,
            "scope_id": self.scope_id,
            "last4": self.last4,
            "key_id": self.key_id,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "rotated_at": self.rotated_at,
            "last_used_at": self.last_used_at,
            "configured": self.configured,
            "version": self.version,
            "value": "••••••••" if self.configured else "",
        }


@dataclass(frozen=True)
class ApprovalRequest:
    """A pending change that needs a human decision."""

    approval_id: str
    key: str
    scope_type: ScopeType
    scope_id: str
    proposed_value: Any
    proposed_by: str
    actor_type: ActorType
    risk: str = "MEDIUM"
    status: ApprovalStatus = ApprovalStatus.PENDING
    required_approvals: int = 1
    approvals: Tuple[str, ...] = ()
    reason: str = ""
    created_at: float = 0.0
    expires_at: Optional[float] = None
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    decision_reason: Optional[str] = None
    company_id: Optional[str] = None

    def to_public_dict(self, sensitive: bool = False) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "key": self.key,
            "scope_type": self.scope_type.value,
            "scope_id": self.scope_id,
            "company_id": self.company_id,
            "proposed_value": "••••••••" if sensitive else self.proposed_value,
            "proposed_by": self.proposed_by,
            "actor_type": self.actor_type.value,
            "risk": self.risk,
            "status": self.status.value,
            "required_approvals": self.required_approvals,
            "approvals": list(self.approvals),
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "decision_reason": self.decision_reason,
        }
