"""Six-scope effective-value resolver for Settings V2.

Resolution order is deliberately two-pass:

1. A lock wins, and the broadest lock wins.  Platform beats Organization,
   Organization beats Company, and so on.
2. Without a lock, the most specific stored value wins, from User up to
   Platform.
3. If nothing is stored, the legacy ``enterprise_settings`` table is consulted
   during the migration window, then an environment default, then the registry
   default.

Every result carries provenance so the UI can distinguish Default, Inherited,
Overridden, and Locked.  Importing this module is side-effect free.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.settings.errors import NotFoundError, ScopeError
from core.settings.models import (
    SCOPE_BROAD_TO_SPECIFIC,
    SCOPE_LABELS,
    SCOPE_SPECIFIC_TO_BROAD,
    EffectiveSetting,
    ScopeType,
    SettingDefinition,
    SettingStatus,
)
from core.settings.registry import settings_registry

SECRET_MASK = "••••••••"

# Setting keys that have a documented environment fallback.  The resolver only
# reports the environment value; runtime consumers may keep their own fallback
# chain until they are migrated to the resolver.
ENV_DEFAULTS: Dict[str, Tuple[str, Any]] = {
    "llm_provider": ("ZONATA_LLM_PROVIDER", str),
    "llm_model": ("ZONATA_LLM_MODEL", str),
    "llm_base_url": ("ZONATA_LLM_BASE_URL", str),
    "llm_api_key": ("ZONATA_LLM_API_KEY", str),
    "llm_timeout_seconds": ("ZONATA_LLM_TIMEOUT", float),
}


@dataclass(frozen=True)
class ResolveContext:
    """The scope chain for one request."""

    tenant_id: str
    company_id: str
    department_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    platform_id: str = "platform"
    view_scope: Optional[ScopeType] = None

    def scope_id(self, scope: ScopeType) -> Optional[str]:
        if scope is ScopeType.PLATFORM:
            return self.platform_id
        if scope is ScopeType.ORGANIZATION:
            return self.tenant_id
        if scope is ScopeType.COMPANY:
            return self.company_id
        if scope is ScopeType.DEPARTMENT:
            return self.department_id
        if scope is ScopeType.AGENT:
            return self.agent_id
        if scope is ScopeType.USER:
            return self.user_id
        return None

    def cache_key(self) -> Tuple[str, ...]:
        return (
            self.tenant_id or "",
            self.company_id or "",
            self.department_id or "",
            self.agent_id or "",
            self.user_id or "",
            self.view_scope.value if self.view_scope else "",
        )


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


class SettingsResolver:
    """Resolve effective settings for a context and cache by revision."""

    def __init__(
        self,
        *,
        legacy_fallback: Optional[bool] = None,
        env_defaults: Optional[Dict[str, Tuple[str, Any]]] = None,
        cache_enabled: bool = True,
    ) -> None:
        if legacy_fallback is None:
            legacy_fallback = str(os.environ.get("ZONATA_SETTINGS_LEGACY_FALLBACK", "1")) != "0"
        self.legacy_fallback = bool(legacy_fallback)
        # The old runtime fell back to the tnt_primary host root for every
        # tenant.  That is a cross-tenant leak, so Settings V2 defaults to
        # tenant-scoped fallbacks only.  The flag exists for a short migration
        # window where exact parity with the old runtime is required.
        self.legacy_global_fallback = (
            str(os.environ.get("ZONATA_SETTINGS_LEGACY_GLOBAL_FALLBACK", "0")) == "1"
        )
        self.env_defaults = dict(ENV_DEFAULTS if env_defaults is None else env_defaults)
        self.cache_enabled = cache_enabled
        self._cache: Dict[Tuple[Any, ...], Tuple[int, EffectiveSetting]] = {}

    # ------------------------------------------------------------------ cache
    def invalidate(self, tenant_id: Optional[str] = None) -> None:
        if tenant_id is None:
            self._cache.clear()
            return
        for key in list(self._cache):
            if key and key[0] == tenant_id:
                self._cache.pop(key, None)

    def _revision(self, conn: Any, tenant_id: str) -> int:
        try:
            row = conn.execute(
                "SELECT revision FROM settings_revision WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
            return int(_row_value(row, 0, "revision") or 0)
        except Exception:
            return 0

    # -------------------------------------------------------------- candidates
    def candidate_scopes(
        self, definition: SettingDefinition, context: ResolveContext
    ) -> List[Tuple[ScopeType, str]]:
        result: List[Tuple[ScopeType, str]] = []
        for scope in SCOPE_BROAD_TO_SPECIFIC:
            if scope not in definition.allowed_scopes:
                continue
            scope_id = context.scope_id(scope)
            if scope_id:
                result.append((scope, str(scope_id)))
        return result

    # ---------------------------------------------------------------- resolve
    def resolve(
        self,
        conn: Any,
        key: str,
        context: ResolveContext,
        *,
        default: Any = None,
        use_cache: Optional[bool] = None,
    ) -> EffectiveSetting:
        definition = settings_registry.get(key)
        if definition is None:
            raise NotFoundError(f"Unknown setting key '{key}'.")

        if definition.secret:
            # Secrets are write-only.  The effective API returns metadata, not
            # a value, even if a ciphertext exists.
            return EffectiveSetting(
                key=key,
                value=SECRET_MASK,
                source_scope=ScopeType.PLATFORM,
                source_id="secret",
                is_locked=False,
                default_value=SECRET_MASK,
                version=1,
                requires_restart=definition.requires_restart,
                status=definition.status,
            )

        cache_allowed = self.cache_enabled if use_cache is None else use_cache
        revision = self._revision(conn, context.tenant_id) if cache_allowed else 0
        cache_key = (context.tenant_id, key) + context.cache_key()
        if cache_allowed:
            cached = self._cache.get(cache_key)
            if cached and cached[0] == revision:
                return cached[1]

        candidates = self.candidate_scopes(definition, context)
        rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for scope, scope_id in candidates:
            row = conn.execute(
                """
                SELECT scope_type, scope_id, value_json, locked, version, updated_at, updated_by
                FROM settings_values
                WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND setting_key = ?
                """,
                (context.tenant_id, scope.value, scope_id, key),
            ).fetchone()
            if row is not None:
                rows[(scope.value, scope_id)] = {
                    "scope": scope,
                    "scope_id": scope_id,
                    "value": _load_value(_row_value(row, 2, "value_json")),
                    "locked": bool(_row_value(row, 3, "locked")),
                    "version": int(_row_value(row, 4, "version") or 1),
                    "updated_at": _row_value(row, 5, "updated_at"),
                    "updated_by": _row_value(row, 6, "updated_by"),
                }

        result = self._resolve_from_rows(definition, context, rows)
        if result is None and self.legacy_fallback:
            result = self._resolve_legacy(conn, definition, context)
        if result is None:
            result = self._resolve_env_or_default(definition, context, default)

        if cache_allowed:
            self._cache[cache_key] = (revision, result)
        return result

    def _resolve_from_rows(
        self,
        definition: SettingDefinition,
        context: ResolveContext,
        rows: Dict[Tuple[str, str], Dict[str, Any]],
    ) -> Optional[EffectiveSetting]:
        # 1. Broadest lock wins.
        for scope in SCOPE_BROAD_TO_SPECIFIC:
            for candidate, data in rows.items():
                if data["scope"] is not scope or not data["locked"]:
                    continue
                return self._effective(
                    definition,
                    context,
                    data["value"],
                    scope,
                    candidate[1],
                    version=data["version"],
                    is_locked=True,
                    locked_by_scope=scope,
                    locked_by_id=candidate[1],
                    overridden_here=self._is_here(context, scope),
                )

        # 2. Most specific value wins.
        for scope in SCOPE_SPECIFIC_TO_BROAD:
            for candidate, data in rows.items():
                if data["scope"] is not scope:
                    continue
                return self._effective(
                    definition,
                    context,
                    data["value"],
                    scope,
                    candidate[1],
                    version=data["version"],
                    overridden_here=self._is_here(context, scope),
                    inherits_from=None if self._is_here(context, scope) else scope.value,
                )
        return None

    def _is_here(self, context: ResolveContext, scope: ScopeType) -> bool:
        if context.view_scope is not None:
            return scope is context.view_scope
        # Default view is the most specific scope the context can address.
        return scope is self._context_specific_scope(context)

    def _context_specific_scope(self, context: ResolveContext) -> ScopeType:
        if context.user_id:
            return ScopeType.USER
        if context.agent_id:
            return ScopeType.AGENT
        if context.department_id:
            return ScopeType.DEPARTMENT
        return ScopeType.COMPANY

    def _effective(
        self,
        definition: SettingDefinition,
        context: ResolveContext,
        value: Any,
        source_scope: ScopeType,
        source_id: str,
        *,
        version: int = 1,
        is_locked: bool = False,
        locked_by_scope: Optional[ScopeType] = None,
        locked_by_id: Optional[str] = None,
        overridden_here: bool = False,
        inherits_from: Optional[str] = None,
    ) -> EffectiveSetting:
        return EffectiveSetting(
            key=definition.key,
            value=value,
            source_scope=source_scope,
            source_id=source_id,
            is_locked=is_locked,
            locked_by_scope=locked_by_scope,
            locked_by_id=locked_by_id,
            default_value=definition.default,
            overridden_here=overridden_here,
            inherits_from=inherits_from,
            version=version,
            requires_restart=definition.requires_restart,
            status=definition.status,
        )

    def _resolve_legacy(
        self, conn: Any, definition: SettingDefinition, context: ResolveContext
    ) -> Optional[EffectiveSetting]:
        """Read the legacy table only when no v2 row exists.

        Legacy semantics were Company -> ``comp_primary`` -> global primary.
        Keeping that order during the migration window preserves runtime
        behavior without granting the legacy table any authority after a v2
        row exists.
        """
        if ScopeType.COMPANY not in definition.allowed_scopes:
            return None
        try:
            row = conn.execute(
                """
                SELECT company_id, setting_value_json, version
                FROM enterprise_settings
                WHERE tenant_id = ? AND company_id = ? AND setting_key = ?
                """,
                (context.tenant_id, context.company_id, definition.key),
            ).fetchone()
            source_id = context.company_id
            if row is None and context.company_id != "comp_primary":
                row = conn.execute(
                    """
                    SELECT company_id, setting_value_json, version
                    FROM enterprise_settings
                    WHERE tenant_id = ? AND company_id = 'comp_primary' AND setting_key = ?
                    """,
                    (context.tenant_id, definition.key),
                ).fetchone()
                source_id = "comp_primary"
            if (
                row is None
                and context.tenant_id != "tnt_primary"
                and self.legacy_global_fallback
            ):
                row = conn.execute(
                    """
                    SELECT company_id, setting_value_json, version
                    FROM enterprise_settings
                    WHERE tenant_id = 'tnt_primary' AND company_id = 'comp_primary' AND setting_key = ?
                    """,
                    (definition.key,),
                ).fetchone()
                source_id = "comp_primary"
        except Exception:
            return None
        if row is None:
            return None

        company_used = str(_row_value(row, 0, "company_id") or source_id)
        version = int(_row_value(row, 2, "version") or 1)
        here = company_used == context.company_id
        return self._effective(
            definition,
            context,
            _load_value(_row_value(row, 1, "setting_value_json")),
            ScopeType.COMPANY,
            company_used,
            version=version,
            overridden_here=here,
            inherits_from=None if here else ScopeType.COMPANY.value,
        )

    def _resolve_env_or_default(
        self,
        definition: SettingDefinition,
        context: ResolveContext,
        default: Any,
    ) -> EffectiveSetting:
        spec = self.env_defaults.get(definition.key)
        if spec and not definition.secret:
            env_name, caster = spec
            raw = os.environ.get(env_name, "")
            if str(raw).strip():
                try:
                    value = caster(raw)
                except (TypeError, ValueError):
                    value = raw
                return self._effective(
                    definition,
                    context,
                    value,
                    ScopeType.PLATFORM,
                    "env",
                    overridden_here=False,
                )
        fallback = definition.default if default is None else default
        return self._effective(
            definition,
            context,
            fallback,
            ScopeType.PLATFORM,
            "default",
            overridden_here=False,
        )

    # -------------------------------------------------------------- bulk read
    def resolve_many(
        self,
        conn: Any,
        keys: Iterable[str],
        context: ResolveContext,
        *,
        use_cache: Optional[bool] = None,
    ) -> Dict[str, EffectiveSetting]:
        result: Dict[str, EffectiveSetting] = {}
        for key in keys:
            result[key] = self.resolve(conn, key, context, use_cache=use_cache)
        return result

    def list_stored_overrides(
        self,
        conn: Any,
        tenant_id: str,
        company_id: Optional[str] = None,
        key: Optional[str] = None,
        scope_type: Optional[ScopeType] = None,
        scope_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT tenant_id, company_id, scope_type, scope_id, setting_key,
                   value_json, locked, version, updated_by, updated_at
            FROM settings_values WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        if key:
            query += " AND setting_key = ?"
            params.append(key)
        if scope_type is not None:
            query += " AND scope_type = ?"
            params.append(scope_type.value)
        if scope_id:
            query += " AND scope_id = ?"
            params.append(scope_id)
        query += " ORDER BY setting_key ASC, scope_type ASC"

        rows = conn.execute(query, tuple(params)).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "tenant_id": str(row[0]),
                    "company_id": row[1],
                    "scope_type": str(row[2]),
                    "scope_id": str(row[3]),
                    "setting_key": str(row[4]),
                    "value": _load_value(row[5]),
                    "locked": bool(row[6]),
                    "version": int(row[7] or 1),
                    "updated_by": row[8],
                    "updated_at": row[9],
                }
            )
        return result


settings_resolver = SettingsResolver()
