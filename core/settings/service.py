"""Settings V2 service orchestration.

This module owns the write path: validation, RBAC, optimistic concurrency,
approvals, secret handling, append-only audit, revision bumps, and resolver
cache invalidation.  The HTTP layer in ``api_v2`` only translates requests and
errors; it contains no policy.

Importing this module is side-effect free.  Database access is lazy, so tests
can inject a SQLite connection or connection factory.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.settings import rbac
from core.settings.approvals import SettingsApprovals, settings_approvals
from core.settings.audit import SettingsAudit, settings_audit
from core.settings.errors import (
    ApprovalRequired,
    ConflictError,
    NotFoundError,
    PermissionDenied,
    ScopeError,
    UnsupportedOperation,
    ValidationError,
)
from core.settings.models import (
    SCOPE_BROAD_TO_SPECIFIC,
    ActorType,
    ApprovalStatus,
    EffectiveSetting,
    ScopeType,
    SettingDefinition,
    SettingStatus,
)
from core.settings.registry import settings_registry
from core.settings.resolver import ResolveContext, SettingsResolver, settings_resolver
from core.settings.secrets import SettingsSecretVault, settings_vault

SECRET_MASK = "••••••••"

PENDING_APPROVAL_STATUS = "PENDING"


def _json_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _load_value(raw: Any) -> Any:
    if raw is None:
        return None
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _row_value(row: Any, index: int, name: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(name)
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return row[index]


def _coerce(definition: SettingDefinition, value: Any) -> Any:
    """Coerce browser form input into the definition's type before validation."""
    value_type = definition.value_type
    if value_type in ("number", "slider", "currency") and isinstance(value, str):
        text = value.strip()
        if text == "":
            return value
        try:
            number = float(text)
        except ValueError:
            return value
        default = definition.default
        if isinstance(default, int) and not isinstance(default, bool) and number.is_integer():
            return int(number)
        return number
    if value_type == "toggle" and isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    if value_type == "multiselect" and isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _validate(definition: SettingDefinition, value: Any) -> Any:
    value = _coerce(definition, value)
    valid, error = definition.validation.validate(value)
    if not valid:
        raise ValidationError(error or f"Invalid value for '{definition.key}'.")
    return value


class SettingsV2Service:
    def __init__(
        self,
        *,
        connection_factory: Optional[Any] = None,
        audit: Optional[SettingsAudit] = None,
        resolver: Optional[SettingsResolver] = None,
        vault: Optional[SettingsSecretVault] = None,
        approvals: Optional[SettingsApprovals] = None,
        clock: Any = time.time,
    ) -> None:
        self._connection_factory = connection_factory
        self.audit = audit or settings_audit
        self.resolver = resolver or settings_resolver
        self.vault = vault or settings_vault
        self.approvals = approvals or settings_approvals
        self._clock = clock

    # ------------------------------------------------------------ connections
    @contextmanager
    def _use_conn(self, conn: Optional[Any] = None):
        if conn is not None:
            yield conn
            return
        if self._connection_factory is not None:
            manager = self._connection_factory()
        else:
            from core.db import db

            manager = db.get_connection()
        with manager as connection:
            yield connection

    def ensure_schema(self, conn: Optional[Any] = None, dialect: Optional[str] = None) -> Dict[str, Any]:
        from core.settings.schema import ensure_schema as _ensure

        with self._use_conn(conn) as connection:
            resolved_dialect = dialect
            if resolved_dialect is None:
                resolved_dialect = str(getattr(connection, "dialect", "sqlite") or "sqlite")
            return _ensure(connection, resolved_dialect)

    # -------------------------------------------------------------- principals
    def _require_read(self, principal: rbac.Principal, conn: Any, company_id: str) -> None:
        rbac.require_permission(principal, "settings.read")
        if company_id and not rbac.can_access_company(conn, principal, company_id):
            raise PermissionDenied("The requested company is outside the authenticated membership.")

    def context(
        self,
        principal: rbac.Principal,
        company_id: Optional[str] = None,
        *,
        department_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        view_scope: Optional[ScopeType] = None,
    ) -> ResolveContext:
        company = company_id or principal.company_id
        if not company:
            raise ScopeError("A company is required to resolve settings.")
        resolved_user = user_id
        resolved_agent = agent_id
        resolved_department = department_id
        if view_scope is ScopeType.USER and not resolved_user:
            resolved_user = principal.user_id
        return ResolveContext(
            tenant_id=principal.tenant_id,
            company_id=company,
            department_id=resolved_department,
            agent_id=resolved_agent,
            user_id=resolved_user,
            view_scope=view_scope,
        )

    def _scope_target(
        self,
        principal: rbac.Principal,
        conn: Any,
        definition: SettingDefinition,
        scope_type: ScopeType,
        scope_id: Optional[str],
        company_id: Optional[str],
    ) -> Tuple[str, Optional[str]]:
        if scope_type not in definition.allowed_scopes:
            allowed = ", ".join(scope.value for scope in definition.allowed_scopes)
            raise ScopeError(
                f"'{definition.key}' cannot be written at {scope_type.value} scope; allowed: {allowed}."
            )
        if scope_type is ScopeType.PLATFORM:
            target_company = company_id
            target_id = scope_id or "platform"
        elif scope_type is ScopeType.ORGANIZATION:
            target_company = company_id
            target_id = scope_id or principal.tenant_id
            if target_id != principal.tenant_id:
                raise PermissionDenied("Organization scope must match the authenticated tenant.")
        else:
            target_company = scope_id if scope_type is ScopeType.COMPANY else (company_id or principal.company_id)
            if scope_type is ScopeType.COMPANY:
                target_company = scope_id or company_id or principal.company_id
            target_id = scope_id or target_company or ""
        if scope_type is not ScopeType.PLATFORM and not target_id:
            raise ScopeError("scope_id is required for this scope.")
        if target_company and not rbac.can_access_company(conn, principal, target_company):
            raise PermissionDenied("The requested company is outside the authenticated membership.")
        return str(target_id), str(target_company) if target_company else None

    # ------------------------------------------------------------------ reads
    def registry_catalog(self, principal: rbac.Principal, section: Optional[str] = None) -> Dict[str, Any]:
        rbac.require_permission(principal, "settings.read")
        catalog = settings_registry.public_catalog()
        catalog["capabilities"] = rbac.capabilities(principal)
        if section:
            definitions = [item for item in catalog["settings"] if item["section"] == section]
            catalog = {
                "sections": [item for item in catalog["sections"] if item["id"] == section],
                "categories": [
                    item for item in catalog["categories"] if item.get("section") == section
                ],
                "settings": definitions,
                "counts": {
                    "total": len(definitions),
                    "section": section,
                },
            }
        return catalog

    def effective(
        self,
        principal: rbac.Principal,
        key: str,
        *,
        company_id: Optional[str] = None,
        department_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        view_scope: Optional[ScopeType] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(key)
        if definition is None:
            raise NotFoundError(f"Unknown setting key '{key}'.")
        with self._use_conn(conn) as connection:
            company = company_id or principal.company_id
            self._require_read(principal, connection, company)
            ctx = self.context(
                principal,
                company,
                department_id=department_id,
                agent_id=agent_id,
                user_id=user_id,
                view_scope=view_scope,
            )
            if definition.secret:
                return self._secret_effective(connection, principal, definition, ctx)
            resolved = self.resolver.resolve(connection, key, ctx)
            payload = resolved.to_public_dict(sensitive=definition.sensitive)
            payload.update(
                {
                    "label": definition.label,
                    "category": definition.category,
                    "section": definition.section,
                    "type": definition.value_type,
                    "risk": definition.risk,
                    "required_permission": definition.required_permission,
                    "enforced_by": definition.enforced_by,
                    "allowed_scopes": [scope.value for scope in definition.allowed_scopes],
                    "revision": self.audit.current_revision(connection, principal.tenant_id),
                }
            )
            return payload

    def effective_section(
        self,
        principal: rbac.Principal,
        *,
        section: Optional[str] = None,
        category: Optional[str] = None,
        company_id: Optional[str] = None,
        department_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        view_scope: Optional[ScopeType] = None,
        include_hidden: bool = False,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        if category:
            definitions = settings_registry.by_category(category)
        elif section:
            definitions = settings_registry.by_section(section)
        else:
            definitions = list(settings_registry.all())
        with self._use_conn(conn) as connection:
            company = company_id or principal.company_id
            self._require_read(principal, connection, company)
            ctx = self.context(
                principal,
                company,
                department_id=department_id,
                agent_id=agent_id,
                user_id=user_id,
                view_scope=view_scope,
            )
            revision = self.audit.current_revision(connection, principal.tenant_id)
            results: List[Dict[str, Any]] = []
            for definition in definitions:
                if definition.status is SettingStatus.HIDDEN and not include_hidden:
                    continue
                if definition.secret:
                    payload = self._secret_effective(connection, principal, definition, ctx)
                elif definition.status is SettingStatus.ACTION:
                    payload = definition.to_public_dict()
                    payload.update(
                        {
                            "value": None,
                            "source_scope": None,
                            "source_id": None,
                            "is_locked": False,
                            "provenance": "Action",
                            "status": definition.status.value,
                        }
                    )
                else:
                    resolved = self.resolver.resolve(connection, definition.key, ctx)
                    payload = resolved.to_public_dict(sensitive=definition.sensitive)
                    payload.update(definition.to_public_dict())
                payload["revision"] = revision
                results.append(payload)
            return results

    def _secret_effective(
        self,
        conn: Any,
        principal: rbac.Principal,
        definition: SettingDefinition,
        ctx: ResolveContext,
    ) -> Dict[str, Any]:
        metadata = None
        for scope in SCOPE_BROAD_TO_SPECIFIC:
            if scope not in definition.allowed_scopes:
                continue
            scope_id = ctx.scope_id(scope)
            if not scope_id:
                continue
            metadata = self.vault.get_metadata(
                conn, principal.tenant_id, scope, scope_id, definition.key
            )
            if metadata is not None:
                break
        payload = {
            "key": definition.key,
            "value": SECRET_MASK,
            "default_value": SECRET_MASK,
            "source_scope": metadata.scope_type.value if metadata else None,
            "source_id": metadata.scope_id if metadata else None,
            "is_locked": False,
            "locked_by_scope": None,
            "locked_by_id": None,
            "overridden_here": False,
            "inherits_from": None,
            "provenance": "Write-only secret",
            "version": metadata.version if metadata else 1,
            "requires_restart": definition.requires_restart,
            "status": definition.status.value,
            "label": definition.label,
            "category": definition.category,
            "section": definition.section,
            "type": definition.value_type,
            "risk": definition.risk,
            "required_permission": definition.required_permission,
            "enforced_by": definition.enforced_by,
            "allowed_scopes": [scope.value for scope in definition.allowed_scopes],
            "sensitive": True,
            "secret": True,
            "secret_metadata": self._secret_public_metadata(principal, metadata, definition),
            "revision": self.audit.current_revision(conn, principal.tenant_id),
        }
        return payload

    @staticmethod
    def _secret_public_metadata(
        principal: rbac.Principal, metadata: Any, definition: SettingDefinition
    ) -> Dict[str, Any]:
        """Secret existence is visible to readers; the hint is not.

        Only a caller with ``secrets.manage`` sees last4 or who created the
        secret.  Everyone else sees whether the credential is configured and
        nothing that narrows a guess.
        """
        if metadata is None:
            return {"name": definition.key, "configured": False, "last4": "", "value": ""}
        public = metadata.to_public_dict()
        if not rbac.has_permission(principal, "secrets.manage"):
            public = {
                **public,
                "last4": "",
                "key_id": None,
                "created_by": None,
            }
        return public

    def diff(
        self,
        principal: rbac.Principal,
        company_a: str,
        company_b: str,
        keys: Optional[Sequence[str]] = None,
        *,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        selected = keys or [d.key for d in settings_registry.all() if d.is_live]
        with self._use_conn(conn) as connection:
            self._require_read(principal, connection, company_a)
            self._require_read(principal, connection, company_b)
            ctx_a = self.context(principal, company_a)
            ctx_b = self.context(principal, company_b)
            result = []
            for key in selected:
                definition = settings_registry.get(key)
                if definition is None:
                    continue
                a = self.resolver.resolve(connection, key, ctx_a)
                b = self.resolver.resolve(connection, key, ctx_b)
                result.append(
                    {
                        "key": key,
                        "company_a": {"value": a.value, "source": a.source_scope.value},
                        "company_b": {"value": b.value, "source": b.source_scope.value},
                        "equal": _json_value(a.value) == _json_value(b.value),
                    }
                )
            return result

    # ---------------------------------------------------------------- writes
    def _current_row(
        self,
        conn: Any,
        tenant_id: str,
        definition: SettingDefinition,
        scope_type: ScopeType,
        scope_id: str,
    ) -> Any:
        return conn.execute(
            """
            SELECT value_json, locked, version, updated_at FROM settings_values
            WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND setting_key = ?
            """,
            (tenant_id, scope_type.value, scope_id, definition.key),
        ).fetchone()

    def set_value(
        self,
        principal: rbac.Principal,
        key: str,
        value: Any,
        *,
        scope_type: ScopeType = ScopeType.COMPANY,
        scope_id: Optional[str] = None,
        company_id: Optional[str] = None,
        expected_version: Optional[int] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        allow_non_live: bool = False,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(key)
        if definition is None:
            raise NotFoundError(f"Unknown setting key '{key}'.")
        if definition.status is SettingStatus.ACTION:
            raise UnsupportedOperation(
                "This key is an executable action, not a value.",
                hint="Use POST /api/settings/v2/actions/{action_id} with typed confirmation.",
            )
        if definition.secret:
            raise UnsupportedOperation(
                "Secret values are write-only.",
                hint="Use POST /api/settings/v2/secrets.",
            )
        if definition.status is not SettingStatus.LIVE and not allow_non_live:
            raise UnsupportedOperation(
                f"'{key}' is not enforced yet ({definition.status.value}); it is not writable through Settings V2.",
            )

        with self._use_conn(conn) as connection:
            target_id, target_company = self._scope_target(
                principal, connection, definition, scope_type, scope_id, company_id
            )
            rbac.require_write(
                connection, principal, definition, scope_type, target_id, target_company or ""
            )
            value = _validate(definition, value)
            if principal.actor_type is ActorType.AGENT and rbac.is_ceo_self_limit(key):
                raise PermissionDenied("An agent may not change the AI CEO's own limits.")

            if self._needs_approval(principal, definition):
                approval = self.approvals.create(
                    connection,
                    tenant_id=principal.tenant_id,
                    company_id=target_company,
                    principal=principal,
                    definition=definition,
                    scope_type=scope_type,
                    scope_id=target_id,
                    proposed_value=value,
                    reason=reason or "A change requiring human approval.",
                )
                self.audit.write(
                    connection,
                    tenant_id=principal.tenant_id,
                    company_id=target_company,
                    scope_type=scope_type.value,
                    scope_id=target_id,
                    setting_key=key,
                    actor=principal.user_id,
                    actor_type=principal.actor_type.value,
                    old_value=None,
                    new_value=None,
                    reason=reason or "Change queued for approval.",
                    request_id=request_id,
                    ip_address=ip_address,
                    approval_status=PENDING_APPROVAL_STATUS,
                    sensitive=definition.sensitive,
                )
                self.audit.bump_revision(connection, principal.tenant_id)
                self.resolver.invalidate(principal.tenant_id)
                # Persist the queued proposal before surfacing 202; raising
                # through the connection context would otherwise roll it back.
                connection.commit()
                raise ApprovalRequired(
                    f"'{key}' requires human approval before it can be applied.",
                    approval_id=approval.approval_id,
                )

            result = self._apply_value(
                connection,
                principal,
                definition,
                scope_type,
                target_id,
                target_company,
                value,
                expected_version=expected_version,
                reason=reason,
                request_id=request_id,
                ip_address=ip_address,
                approval_status="APPROVED",
            )
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return result

    def _needs_approval(self, principal: rbac.Principal, definition: SettingDefinition) -> bool:
        if principal.actor_type is ActorType.AGENT:
            return True
        return bool(definition.requires_approval) and not principal.is_privileged

    def _apply_value(
        self,
        conn: Any,
        principal: rbac.Principal,
        definition: SettingDefinition,
        scope_type: ScopeType,
        scope_id: str,
        company_id: Optional[str],
        value: Any,
        *,
        expected_version: Optional[int],
        reason: str,
        request_id: Optional[str],
        ip_address: Optional[str],
        approval_status: str,
    ) -> Dict[str, Any]:
        row = self._current_row(conn, principal.tenant_id, definition, scope_type, scope_id)
        old_value = definition.default
        old_version = 0
        if row is not None:
            old_value = _load_value(_row_value(row, 0, "value_json"))
            old_version = int(_row_value(row, 2, "version") or 1)

        if expected_version is not None and int(expected_version) != old_version:
            raise ConflictError(
                f"'{definition.key}' is at version {old_version}, expected {expected_version}.",
            )

        new_version = old_version + 1
        now = float(self._clock())
        value_json = _json_value(value)
        if row is None:
            conn.execute(
                """
                INSERT INTO settings_values
                    (tenant_id, company_id, scope_type, scope_id, setting_key,
                     value_json, locked, version, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    principal.tenant_id,
                    company_id,
                    scope_type.value,
                    scope_id,
                    definition.key,
                    value_json,
                    new_version,
                    principal.user_id,
                    now,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE settings_values
                SET tenant_id = ?, company_id = ?, value_json = ?, version = ?,
                    updated_by = ?, updated_at = ?
                WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND setting_key = ?
                """,
                (
                    principal.tenant_id,
                    company_id,
                    value_json,
                    new_version,
                    principal.user_id,
                    now,
                    principal.tenant_id,
                    scope_type.value,
                    scope_id,
                    definition.key,
                ),
            )

        audit_row = self.audit.write(
            conn,
            tenant_id=principal.tenant_id,
            company_id=company_id,
            scope_type=scope_type.value,
            scope_id=scope_id,
            setting_key=definition.key,
            actor=principal.user_id,
            actor_type=principal.actor_type.value,
            old_value=old_value,
            new_value=value,
            reason=reason or "Setting updated.",
            request_id=request_id,
            ip_address=ip_address,
            version=new_version,
            approval_status=approval_status,
            sensitive=definition.sensitive,
        )
        revision = self.audit.bump_revision(conn, principal.tenant_id)
        return {
            "success": True,
            "key": definition.key,
            "value": SECRET_MASK if definition.sensitive else value,
            "previous_value": SECRET_MASK if definition.sensitive else old_value,
            "version": new_version,
            "scope_type": scope_type.value,
            "scope_id": scope_id,
            "company_id": company_id,
            "audit_id": audit_row["audit_id"],
            "entry_hash": audit_row["entry_hash"],
            "approval_status": approval_status,
            "revision": revision,
            "requires_restart": definition.requires_restart,
        }

    def reset_value(
        self,
        principal: rbac.Principal,
        key: str,
        *,
        scope_type: ScopeType = ScopeType.COMPANY,
        scope_id: Optional[str] = None,
        company_id: Optional[str] = None,
        expected_version: Optional[int] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(key)
        if definition is None:
            raise NotFoundError(f"Unknown setting key '{key}'.")
        with self._use_conn(conn) as connection:
            target_id, target_company = self._scope_target(
                principal, connection, definition, scope_type, scope_id, company_id
            )
            rbac.require_write(
                connection, principal, definition, scope_type, target_id, target_company or ""
            )
            row = self._current_row(connection, principal.tenant_id, definition, scope_type, target_id)
            if row is None:
                return {
                    "success": True,
                    "key": key,
                    "removed": False,
                    "message": "No local override exists; the value already inherits.",
                    "revision": self.audit.current_revision(connection, principal.tenant_id),
                }
            if bool(_row_value(row, 1, "locked")):
                raise PermissionDenied("Unlock the setting before resetting it to inherited.")
            old_value = _load_value(_row_value(row, 0, "value_json"))
            old_version = int(_row_value(row, 2, "version") or 1)
            if expected_version is not None and int(expected_version) != old_version:
                raise ConflictError(
                    f"'{key}' is at version {old_version}, expected {expected_version}.",
                )
            connection.execute(
                "DELETE FROM settings_values "
                "WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND setting_key = ?",
                (principal.tenant_id, scope_type.value, target_id, key),
            )
            audit_row = self.audit.write(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                scope_type=scope_type.value,
                scope_id=target_id,
                setting_key=key,
                actor=principal.user_id,
                actor_type=principal.actor_type.value,
                old_value=old_value,
                new_value=None,
                reason=reason or "Reset to inherited.",
                request_id=request_id,
                ip_address=ip_address,
                version=old_version + 1,
                approval_status="APPROVED",
                sensitive=definition.sensitive,
            )
            revision = self.audit.bump_revision(connection, principal.tenant_id)
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return {
                "success": True,
                "key": key,
                "removed": True,
                "version": old_version + 1,
                "scope_type": scope_type.value,
                "scope_id": target_id,
                "audit_id": audit_row["audit_id"],
                "revision": revision,
            }

    def set_lock(
        self,
        principal: rbac.Principal,
        key: str,
        locked: bool,
        *,
        scope_type: ScopeType = ScopeType.COMPANY,
        scope_id: Optional[str] = None,
        company_id: Optional[str] = None,
        expected_version: Optional[int] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(key)
        if definition is None:
            raise NotFoundError(f"Unknown setting key '{key}'.")
        if definition.status is not SettingStatus.LIVE:
            raise UnsupportedOperation(f"'{key}' is not enforced yet and cannot be locked.")
        with self._use_conn(conn) as connection:
            target_id, target_company = self._scope_target(
                principal, connection, definition, scope_type, scope_id, company_id
            )
            rbac.require_lock(connection, principal, scope_type, target_id, target_company or "")
            row = self._current_row(connection, principal.tenant_id, definition, scope_type, target_id)
            if row is None:
                raise NotFoundError(
                    f"'{key}' has no stored value at {scope_type.value}/{target_id}; set a value before locking it."
                )
            current_locked = bool(_row_value(row, 1, "locked"))
            current_version = int(_row_value(row, 2, "version") or 1)
            if current_locked == bool(locked):
                return {
                    "success": True,
                    "key": key,
                    "locked": current_locked,
                    "changed": False,
                    "version": current_version,
                }
            if expected_version is not None and int(expected_version) != current_version:
                raise ConflictError(
                    f"'{key}' is at version {current_version}, expected {expected_version}.",
                )
            new_version = current_version + 1
            connection.execute(
                """
                UPDATE settings_values SET locked = ?, version = ?, updated_at = ?, updated_by = ?
                WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND setting_key = ?
                """,
                (
                    1 if locked else 0,
                    new_version,
                    float(self._clock()),
                    principal.user_id,
                    principal.tenant_id,
                    scope_type.value,
                    target_id,
                    key,
                ),
            )
            audit_row = self.audit.write(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                scope_type=scope_type.value,
                scope_id=target_id,
                setting_key=key,
                actor=principal.user_id,
                actor_type=principal.actor_type.value,
                old_value=None,
                new_value=None,
                reason=reason or ("Locked setting." if locked else "Unlocked setting."),
                request_id=request_id,
                ip_address=ip_address,
                version=new_version,
                approval_status="APPROVED",
                sensitive=definition.sensitive,
            )
            revision = self.audit.bump_revision(connection, principal.tenant_id)
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return {
                "success": True,
                "key": key,
                "locked": bool(locked),
                "changed": True,
                "version": new_version,
                "audit_id": audit_row["audit_id"],
                "revision": revision,
            }

    # ------------------------------------------------------------- approvals
    def propose(
        self,
        principal: rbac.Principal,
        key: str,
        value: Any,
        *,
        scope_type: ScopeType = ScopeType.COMPANY,
        scope_id: Optional[str] = None,
        company_id: Optional[str] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Create a proposal.  Agents use this path; they never apply."""
        definition = settings_registry.get(key)
        if definition is None:
            raise NotFoundError(f"Unknown setting key '{key}'.")
        if definition.secret:
            raise UnsupportedOperation("Secrets are never queued as plaintext proposals.")
        if definition.status is SettingStatus.ACTION:
            raise UnsupportedOperation("Actions are not approval proposals.")
        if definition.status is not SettingStatus.LIVE:
            raise UnsupportedOperation(
                f"'{key}' is not enforced yet ({definition.status.value}); it cannot be proposed.",
            )
        with self._use_conn(conn) as connection:
            rbac.require_permission(principal, "settings.read")
            target_id, target_company = self._scope_target(
                principal, connection, definition, scope_type, scope_id, company_id
            )
            if not rbac.can_access_company(connection, principal, target_company or ""):
                raise PermissionDenied("The requested company is outside the authenticated membership.")
            value = _validate(definition, value)
            if principal.actor_type is ActorType.AGENT and rbac.is_ceo_self_limit(key):
                raise PermissionDenied("An agent may not propose a change to the AI CEO's own limits.")
            if principal.actor_type is ActorType.HUMAN:
                # A human proposer must already hold the permission the change
                # needs; otherwise an approval would launder missing authority.
                rbac.require_write(
                    connection, principal, definition, scope_type, target_id, target_company or ""
                )
            approval = self.approvals.create(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                principal=principal,
                definition=definition,
                scope_type=scope_type,
                scope_id=target_id,
                proposed_value=value,
                reason=reason or "Proposed change.",
            )
            self.audit.write(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                scope_type=scope_type.value,
                scope_id=target_id,
                setting_key=key,
                actor=principal.user_id,
                actor_type=principal.actor_type.value,
                old_value=None,
                new_value=None,
                reason=reason or "Proposed change.",
                request_id=request_id,
                ip_address=ip_address,
                approval_status=PENDING_APPROVAL_STATUS,
                sensitive=definition.sensitive,
            )
            revision = self.audit.bump_revision(connection, principal.tenant_id)
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return {
                "success": True,
                "status": PENDING_APPROVAL_STATUS,
                "approval": approval.to_public_dict(sensitive=definition.sensitive),
                "revision": revision,
            }

    def list_approvals(
        self,
        principal: rbac.Principal,
        *,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        rbac.require_permission(principal, "settings.read")
        with self._use_conn(conn) as connection:
            company = company_id or principal.company_id
            if not rbac.can_access_company(connection, principal, company):
                raise PermissionDenied("The requested company is outside the authenticated membership.")
            records = self.approvals.list(
                connection, principal.tenant_id, company_id=company, status=status
            )
            return [record.to_public_dict() for record in records]

    def decide_approval(
        self,
        principal: rbac.Principal,
        approval_id: str,
        approve: bool,
        *,
        decision_reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        rbac.require_approver(principal)
        with self._use_conn(conn) as connection:
            approval = self.approvals.get(connection, principal.tenant_id, approval_id)
            if approval.company_id and not rbac.can_access_company(
                connection, principal, approval.company_id
            ):
                raise PermissionDenied("The approval belongs to a company outside your membership.")
            definition = settings_registry.get(approval.key)
            if definition is None:
                raise NotFoundError(f"Unknown setting key '{approval.key}'.")
            if definition.secret:
                raise UnsupportedOperation("Secret approvals are not supported.")
            if definition.status is not SettingStatus.LIVE:
                raise UnsupportedOperation(
                    f"'{approval.key}' is no longer enforced; the proposal cannot be applied."
                )
            if approve and approval.status is ApprovalStatus.PENDING:
                # The proposal captured a value, not a version.  Refuse to
                # overwrite a value that changed while the proposal waited.
                current = self._current_row(
                    connection,
                    principal.tenant_id,
                    definition,
                    approval.scope_type,
                    approval.scope_id,
                )
                if current is not None:
                    changed_at = float(_row_value(current, 3, "updated_at") or 0.0)
                    if changed_at > float(approval.created_at or 0.0):
                        raise ConflictError(
                            "The setting changed after this proposal was created; create a new proposal."
                        )
            updated, is_final = self.approvals.decide(
                connection,
                tenant_id=principal.tenant_id,
                approval_id=approval_id,
                principal=principal,
                approve=approve,
                decision_reason=decision_reason,
            )
            result: Dict[str, Any] = {
                "success": True,
                "approval": updated.to_public_dict(),
                "final": is_final,
                "applied": False,
            }
            if is_final and updated.status is ApprovalStatus.APPROVED:
                if rbac.is_ceo_self_limit(updated.key) and updated.proposed_by == principal.user_id:
                    raise PermissionDenied("You cannot approve your own change to the AI CEO's limits.")
                company = updated.company_id or principal.company_id
                value = _validate(
                    definition,
                    self.approvals.raw_proposed_value(connection, principal.tenant_id, approval_id),
                )
                rbac.require_write(
                    connection,
                    principal,
                    definition,
                    updated.scope_type,
                    updated.scope_id,
                    company or "",
                )
                applied = self._apply_value(
                    connection,
                    principal,
                    definition,
                    updated.scope_type,
                    updated.scope_id,
                    company,
                    value,
                    expected_version=None,
                    reason=decision_reason or f"Approved by {principal.user_id}.",
                    request_id=request_id,
                    ip_address=ip_address,
                    approval_status="APPROVED",
                )
                applied["approval_id"] = approval_id
                result["applied"] = True
                result["result"] = applied
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return result

    # --------------------------------------------------------------- secrets
    def list_secrets(
        self,
        principal: rbac.Principal,
        *,
        company_id: Optional[str] = None,
        scope_type: Optional[ScopeType] = None,
        scope_id: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        with self._use_conn(conn) as connection:
            company = company_id or principal.company_id
            rbac.require_secret_management(connection, principal, company)
            stored = self.vault.list_metadata(
                connection,
                principal.tenant_id,
                company_id=company,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            by_name = {item.name: item for item in stored}
            results: List[Dict[str, Any]] = []
            for definition in settings_registry.all():
                if not definition.secret:
                    continue
                metadata = by_name.get(definition.key)
                payload = metadata.to_public_dict() if metadata else {
                    "name": definition.key,
                    "scope_type": (scope_type.value if scope_type else ScopeType.COMPANY.value),
                    "scope_id": scope_id or company or "",
                    "last4": "",
                    "configured": False,
                    "value": "",
                }
                payload.update(
                    {
                        "label": definition.label,
                        "description": definition.description,
                        "category": definition.category,
                        "section": definition.section,
                        "requires_restart": definition.requires_restart,
                        "last4": payload.get("last4", ""),
                    }
                )
                results.append(payload)
            return results

    def put_secret(
        self,
        principal: rbac.Principal,
        name: str,
        value: str,
        *,
        rotate: bool = False,
        scope_type: ScopeType = ScopeType.COMPANY,
        scope_id: Optional[str] = None,
        company_id: Optional[str] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(name)
        if definition is None or not definition.secret:
            raise NotFoundError(f"'{name}' is not a secret setting.")
        if scope_type not in definition.allowed_scopes:
            raise ScopeError(
                f"'{name}' cannot be stored at {scope_type.value} scope; allowed: "
                + ", ".join(scope.value for scope in definition.allowed_scopes)
            )
        with self._use_conn(conn) as connection:
            target_id, target_company = self._scope_target(
                principal, connection, definition, scope_type, scope_id, company_id
            )
            rbac.require_secret_management(connection, principal, target_company or "")
            existing = self.vault.get_metadata(
                connection, principal.tenant_id, scope_type, target_id, name
            )
            if rotate and existing is None:
                raise NotFoundError(f"Secret '{name}' is not configured and cannot be rotated.")
            metadata = self.vault.put(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                scope_type=scope_type,
                scope_id=target_id,
                name=name,
                value=value,
                created_by=principal.user_id,
            )
            audit_row = self.audit.write(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                scope_type=scope_type.value,
                scope_id=target_id,
                setting_key=name,
                actor=principal.user_id,
                actor_type=principal.actor_type.value,
                old_value=None,
                new_value=None,
                reason=reason or ("Secret rotated." if existing else "Secret configured."),
                request_id=request_id,
                ip_address=ip_address,
                version=metadata.version,
                approval_status="APPROVED",
                sensitive=True,
            )
            revision = self.audit.bump_revision(connection, principal.tenant_id)
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return {
                "success": True,
                "secret": metadata.to_public_dict(),
                "audit_id": audit_row["audit_id"],
                "revision": revision,
            }

    def revoke_secret(
        self,
        principal: rbac.Principal,
        name: str,
        *,
        scope_type: ScopeType = ScopeType.COMPANY,
        scope_id: Optional[str] = None,
        company_id: Optional[str] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(name)
        if definition is None or not definition.secret:
            raise NotFoundError(f"'{name}' is not a secret setting.")
        with self._use_conn(conn) as connection:
            target_id, target_company = self._scope_target(
                principal, connection, definition, scope_type, scope_id, company_id
            )
            rbac.require_secret_management(connection, principal, target_company or "")
            removed = self.vault.revoke(
                connection,
                tenant_id=principal.tenant_id,
                scope_type=scope_type,
                scope_id=target_id,
                name=name,
            )
            audit_row = self.audit.write(
                connection,
                tenant_id=principal.tenant_id,
                company_id=target_company,
                scope_type=scope_type.value,
                scope_id=target_id,
                setting_key=name,
                actor=principal.user_id,
                actor_type=principal.actor_type.value,
                old_value=None,
                new_value=None,
                reason=reason or "Secret revoked.",
                request_id=request_id,
                ip_address=ip_address,
                approval_status="APPROVED",
                sensitive=True,
            )
            revision = self.audit.bump_revision(connection, principal.tenant_id)
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return {
                "success": True,
                "name": name,
                "removed": removed,
                "configured": False,
                "audit_id": audit_row["audit_id"],
                "revision": revision,
            }

    # ------------------------------------------------------------------ audit
    def list_audit(
        self,
        principal: rbac.Principal,
        *,
        company_id: Optional[str] = None,
        key: Optional[str] = None,
        actor: Optional[str] = None,
        actor_type: Optional[str] = None,
        from_ts: Optional[float] = None,
        to_ts: Optional[float] = None,
        limit: int = 100,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        rbac.require_permission(principal, "audit.read")
        with self._use_conn(conn) as connection:
            company = company_id or principal.company_id
            if company and not rbac.can_access_company(connection, principal, company):
                raise PermissionDenied("The requested company is outside the authenticated membership.")
            return self.audit.list_events(
                connection,
                tenant_id=principal.tenant_id,
                company_id=company,
                setting_key=key,
                actor=actor,
                actor_type=actor_type,
                from_ts=from_ts,
                to_ts=to_ts,
                limit=limit,
            )

    def verify_audit(
        self, principal: rbac.Principal, *, conn: Optional[Any] = None
    ) -> Dict[str, Any]:
        rbac.require_permission(principal, "audit.read")
        with self._use_conn(conn) as connection:
            return self.audit.verify_chain(connection, principal.tenant_id)

    def current_revision(self, principal: rbac.Principal, *, conn: Optional[Any] = None) -> int:
        rbac.require_permission(principal, "settings.read")
        with self._use_conn(conn) as connection:
            return self.audit.current_revision(connection, principal.tenant_id)

    # ------------------------------------------------------------------ actions
    def execute_action(
        self,
        principal: rbac.Principal,
        action_id: str,
        *,
        confirmation: str = "",
        company_id: Optional[str] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        definition = settings_registry.get(action_id)
        if definition is None or definition.status is not SettingStatus.ACTION:
            raise NotFoundError(f"'{action_id}' is not an executable action.")
        if principal.actor_type is ActorType.AGENT:
            raise PermissionDenied("Agents may never execute a danger-zone action.")
        if str(confirmation or "") != action_id:
            raise ValidationError(
                "Typed confirmation does not match the action id.",
            )
        with self._use_conn(conn) as connection:
            company = company_id or principal.company_id
            rbac.require_permission(principal, "danger.manage")
            if not rbac.can_access_company(connection, principal, company):
                raise PermissionDenied("The requested company is outside the authenticated membership.")

            # The legacy implementation owns the host-side side effect.  It is
            # imported lazily because importing it seeds the legacy schema.
            from core.settings_service import settings_service as legacy

            result = legacy.execute_button_action(
                action_id, principal.tenant_id, company, actor=principal.user_id
            )
            audit_row = self.audit.write(
                connection,
                tenant_id=principal.tenant_id,
                company_id=company,
                scope_type=ScopeType.COMPANY.value,
                scope_id=company,
                setting_key=action_id,
                actor=principal.user_id,
                actor_type=principal.actor_type.value,
                old_value=None,
                new_value=result.get("detail") if isinstance(result, dict) else None,
                reason=reason or "Danger-zone action executed with typed confirmation.",
                request_id=request_id,
                ip_address=ip_address,
                approval_status="APPROVED",
                sensitive=False,
            )
            revision = self.audit.bump_revision(connection, principal.tenant_id)
            connection.commit()
            self.resolver.invalidate(principal.tenant_id)
            return {
                "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
                "action_id": action_id,
                "detail": result,
                "audit_id": audit_row["audit_id"],
                "revision": revision,
            }

    # ------------------------------------------------------------------- bulk
    def bulk_preview(
        self,
        principal: rbac.Principal,
        changes: Sequence[Dict[str, Any]],
        *,
        company_id: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        return self._bulk(principal, changes, company_id=company_id, apply=False, conn=conn)

    def bulk_apply(
        self,
        principal: rbac.Principal,
        changes: Sequence[Dict[str, Any]],
        *,
        company_id: Optional[str] = None,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        results = self._bulk(
            principal,
            changes,
            company_id=company_id,
            apply=True,
            reason=reason,
            request_id=request_id,
            ip_address=ip_address,
            conn=conn,
        )
        return {
            "success": True,
            "applied_count": len(results),
            "results": results,
        }

    def _bulk(
        self,
        principal: rbac.Principal,
        changes: Sequence[Dict[str, Any]],
        *,
        company_id: Optional[str],
        apply: bool,
        reason: str = "",
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        if not isinstance(changes, (list, tuple)) or not changes:
            raise ValidationError("A non-empty list of changes is required.")
        preview: List[Dict[str, Any]] = []
        with self._use_conn(conn) as connection:
            for change in changes:
                key = str(change.get("key") or change.get("setting_key") or "")
                if not key:
                    raise ValidationError("Every change requires a setting key.")
                definition = settings_registry.get(key)
                if definition is None:
                    raise NotFoundError(f"Unknown setting key '{key}'.")
                if definition.secret:
                    raise UnsupportedOperation("Use the secret endpoints for secret changes.")
                if definition.status is not SettingStatus.LIVE:
                    raise UnsupportedOperation(f"'{key}' is not enforced yet.")
                value = _validate(definition, change.get("value"))
                scope_type = ScopeType(str(change.get("scope_type") or ScopeType.COMPANY.value))
                scope_id = change.get("scope_id")
                target_id, target_company = self._scope_target(
                    principal, connection, definition, scope_type, scope_id, company_id
                )
                rbac.require_write(
                    connection, principal, definition, scope_type, target_id, target_company or ""
                )
                if self._needs_approval(principal, definition):
                    raise ApprovalRequired(
                        f"'{key}' requires approval and cannot be part of an atomic bulk apply.",
                        approval_id="",
                    )
                row = self._current_row(connection, principal.tenant_id, definition, scope_type, target_id)
                current = _load_value(_row_value(row, 0, "value_json")) if row is not None else definition.default
                entry = {
                    "key": key,
                    "scope_type": scope_type.value,
                    "scope_id": target_id,
                    "current_value": SECRET_MASK if definition.sensitive else current,
                    "proposed_value": SECRET_MASK if definition.sensitive else value,
                    "changed": _json_value(current) != _json_value(value),
                    "requires_restart": definition.requires_restart,
                    "applied": False,
                }
                if apply and entry["changed"]:
                    entry["result"] = self._apply_value(
                        connection,
                        principal,
                        definition,
                        scope_type,
                        target_id,
                        target_company,
                        value,
                        expected_version=None,
                        reason=reason or "Bulk settings apply.",
                        request_id=request_id,
                        ip_address=ip_address,
                        approval_status="APPROVED",
                    )
                    entry["applied"] = True
                preview.append(entry)
            if apply:
                connection.commit()
                self.resolver.invalidate(principal.tenant_id)
        return preview


settings_v2_service = SettingsV2Service()
