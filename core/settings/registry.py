"""Typed, schema-driven settings registry.

The legacy ``SETTINGS_DEFINITIONS`` remain the data source so no key is lost.
This module adds the enterprise metadata the old entries never had:

* ``section`` and ``allowed_scopes``
* ``required_permission`` and ``sensitive``
* ``requires_restart`` and ``enforced_by``
* ``status``: live / coming_soon / hidden / action
* declarative validation

A definition may be ``live`` only when it names a real enforcement point.
Everything else is explicitly ``coming_soon`` or ``hidden``, which is what keeps
the UI honest.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.settings.definitions import (
    CATEGORIES_CATALOG,
    SETTINGS_DEFINITIONS,
)
from core.settings.models import (
    SCOPE_BROAD_TO_SPECIFIC,
    SettingDefinition,
    SettingStatus,
    ScopeType,
    ValidationSpec,
)
from core.settings.sections import (
    CATEGORY_TO_SECTION,
    SECTIONS,
    SECTION_IDS,
    section_for_category,
)

KNOWN_PERMISSIONS = frozenset(
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

# Write permission required for a definition.  Reads always require
# settings.read; audit-specific reads additionally require audit.read in Phase 2.
PERMISSION_BY_CATEGORY: Dict[str, str] = {
    "host": "security.manage",
    "security": "security.manage",
    "audit": "security.manage",
    "governance": "security.manage",
    "privacy": "security.manage",
    "compliance": "security.manage",
    "enterprise": "security.manage",
    "finance": "billing.manage",
    "usage": "billing.manage",
    "billing": "billing.manage",
    "ai": "agents.manage",
    "ai_providers": "agents.manage",
    "ai_ceo": "agents.manage",
    "workforce": "agents.manage",
    "agent_factory": "agents.manage",
    "missions": "agents.manage",
    "workflows": "agents.manage",
    "tools": "agents.manage",
    "a2a": "agents.manage",
    "mcp": "agents.manage",
    "desktop": "agents.manage",
    "browser": "agents.manage",
    "terminal": "agents.manage",
    "openhands": "agents.manage",
    "users": "users.manage",
    "approvals": "settings.write",
}
DEFAULT_WRITE_PERMISSION = "settings.write"

# The only keys with a runtime reader outside the settings subsystem.  Every
# entry here was verified by the Phase 0 audit.  Keep this map small and exact.
ENFORCED_BY: Dict[str, str] = {
    "ai_master_enablement": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_provider": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_model": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_base_url": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_api_key": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_temperature": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_max_tokens": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "llm_timeout_seconds": "core/llm_runtime.py:LLMRuntime.resolve_config",
    "ceo_autonomy_level": "core/executive_decision.py:ExecutiveDecisionEngine.evaluate",
    "ceo_spending_limit": "core/executive_decision.py:ExecutiveDecisionEngine.evaluate",
    "fin_high_expense_approval": "core/executive_decision.py:ExecutiveDecisionEngine.evaluate; core/enterprise_finance.py",
    "host_emergency_stop": "core/executive_decision.py; core/spend_governor.py; core/agent_factory_runtime.py; core/browser_use_execution_runtime.py; api_server.py:terminal",
    "host_killswitch_finances": "core/spend_governor.py:SpendGovernor.evaluate_spend",
    "gov_kill_switch_active": "core/browser_use_execution_runtime.py:BrowserKillSwitch.is_killed",
    "cost_global_budget_monthly": "core/spend_governor.py:SpendGovernor.evaluate_spend",
    "wf_max_concurrent_agents": "core/agent_factory_runtime.py:GovernedAgentFactory",
    "wf_autonomous_spawning": "core/agent_factory_runtime.py:GovernedAgentFactory",
    "term_execution_enabled": "api_server.py:POST /api/terminal/execute",
    "term_max_lease_seconds": "api_server.py:POST /api/terminal/execute",
}

# Text values that should be redacted in audit/API even though they are not
# credentials.  Extend deliberately; do not infer from category names.
SENSITIVE_TEXT_KEYS = {
    "acc_email",
    "comp_tax_id_number",
    "notify_escalation_sms_number",
}

# Values that need a process restart or a subsystem reconnect before they take
# effect.  This is metadata for the UI; Phase 2 will enforce it.
REQUIRES_RESTART = {
    "llm_provider",
    "llm_model",
    "llm_base_url",
    "llm_api_key",
    "llm_timeout_seconds",
    "ai_gemini_api_token",
    "api_rate_limit_rpm",
    "api_bearer_auth_enabled",
    "api_cors_allowed_origins",
    "api_egress_ip_whitelist",
    "api_developer_key_vault",
    "ent_data_residency_zone",
    "mon_health_probe_interval_s",
    "mon_liveness_probe_interval_sec",
    "mon_circuit_breaker_threshold",
    "mon_drift_check_cadence_min",
    "diag_wal_auto_checkpoint",
    "diag_inference_ping_interval_sec",
    "adv_kernel_cache_ttl_sec",
    "adv_isolate_quarantine_mode",
    "rec_auto_snapshot_frequency",
    "recovery_cold_sync_enabled",
    "recovery_rpo_minutes",
    "recovery_rto_minutes",
    "recovery_drill_auto_schedule",
    "flag_hal_multimodal",
}

# Plan or feature gates.  A gated definition is still real; the gate decides
# whether the control is visible for the tenant's plan.
PLAN_GATES: Dict[str, str] = {
    "flag_hal_multimodal": "feature:hal_multimodal",
    "bill_plan_tier": "plan",
    "ent_scim_provisioning": "plan:enterprise",
    "ent_saml_sso_enforced": "plan:enterprise",
    "ent_multi_workspace_isolation": "plan:enterprise",
    "ent_data_residency_zone": "plan:enterprise",
    "ent_tenant_storage_quota_gb": "plan:enterprise",
    "priv_gdpr_compliance_mode": "compliance:gdpr",
    "comp_regulatory_profile": "compliance:profile",
    "rec_auto_snapshot_frequency": "plan:backup",
    "recovery_drill_auto_schedule": "plan:backup",
    "api_developer_key_vault": "plan:developer",
    "usr_require_hardware_passkey": "plan:identity",
    "sec_passkey_enabled": "plan:identity",
}

# Host-scoped definitions can be overridden by Organization and Company.
# Company-scoped definitions can also be set per department or agent.
# User-scoped definitions inherit Organization/Company defaults but resolve at
# the user.
HOST_SCOPES: Tuple[ScopeType, ...] = (
    ScopeType.PLATFORM,
    ScopeType.ORGANIZATION,
    ScopeType.COMPANY,
)
COMPANY_SCOPES: Tuple[ScopeType, ...] = (
    ScopeType.ORGANIZATION,
    ScopeType.COMPANY,
    ScopeType.DEPARTMENT,
    ScopeType.AGENT,
)
USER_SCOPES: Tuple[ScopeType, ...] = (
    ScopeType.ORGANIZATION,
    ScopeType.COMPANY,
    ScopeType.USER,
)


def _allowed_scopes(definition: Dict[str, Any], secret: bool) -> Tuple[ScopeType, ...]:
    key = str(definition["id"])
    if secret and key in {
        "llm_api_key",
        "ai_gemini_api_token",
        "mcp_auth_token",
        "integ_webhook_signature_secret",
        "api_developer_key_vault",
    }:
        return HOST_SCOPES
    legacy_scope = str(definition.get("scope", "Company"))
    if legacy_scope == "Host":
        return HOST_SCOPES
    if legacy_scope == "User":
        return USER_SCOPES
    return COMPANY_SCOPES


def _validation_for(definition: Dict[str, Any]) -> ValidationSpec:
    value_type = str(definition.get("type", "text"))
    options = tuple(definition.get("options") or ())
    default = definition.get("default")
    integer = isinstance(default, int) and not isinstance(default, bool)
    return ValidationSpec(
        value_type=value_type,
        min_value=definition.get("min"),
        max_value=definition.get("max"),
        options=options,
        max_length=2048 if value_type in ("text", "token") else None,
        integer=integer,
        allow_empty=value_type not in ("number", "currency", "slider"),
    )


def _status_for(definition: Dict[str, Any], enforced_by: Optional[str]) -> SettingStatus:
    value_type = str(definition.get("type", ""))
    editable_by = str(definition.get("editable_by", "OWNER"))
    if value_type == "button_action":
        return SettingStatus.ACTION
    if editable_by == "READ_ONLY" or value_type == "status":
        return SettingStatus.HIDDEN
    if enforced_by:
        return SettingStatus.LIVE
    return SettingStatus.COMING_SOON


def _required_permission(definition: Dict[str, Any], secret: bool) -> str:
    if secret:
        return "secrets.manage"
    category = str(definition.get("category", ""))
    if category in ("secrets",):
        return "secrets.manage"
    return PERMISSION_BY_CATEGORY.get(category, DEFAULT_WRITE_PERMISSION)


def build_definition(raw: Dict[str, Any]) -> SettingDefinition:
    key = str(raw["id"])
    category = str(raw.get("category", ""))
    secret = bool(raw.get("secret"))
    sensitive = secret or key in SENSITIVE_TEXT_KEYS
    enforced_by = ENFORCED_BY.get(key)
    value_type = str(raw.get("type", "text"))
    return SettingDefinition(
        key=key,
        section=section_for_category(category),
        category=category,
        label=str(raw.get("name", key)),
        description=str(raw.get("desc", "") or ""),
        value_type=value_type,
        default=raw.get("default"),
        validation=_validation_for(raw),
        allowed_scopes=_allowed_scopes(raw, secret),
        required_permission=_required_permission(raw, secret),
        sensitive=sensitive,
        secret=secret,
        requires_restart=key in REQUIRES_RESTART,
        enforced_by=enforced_by,
        status=_status_for(raw, enforced_by),
        risk=str(raw.get("risk", "LOW")),
        editable_by=str(raw.get("editable_by", "OWNER")),
        plan_gate=PLAN_GATES.get(key),
        unit=raw.get("unit"),
        legacy_scope=raw.get("scope"),
        requires_approval=bool(raw.get("requires_approval")),
        is_ceo_managed=bool(raw.get("is_ceo_managed")),
        action_id=key if value_type == "button_action" else None,
    )


class SettingsRegistry:
    """Immutable registry built once from the canonical definitions."""

    def __init__(self, raw_definitions: Optional[Sequence[Dict[str, Any]]] = None):
        source = raw_definitions if raw_definitions is not None else SETTINGS_DEFINITIONS
        self._definitions: Tuple[SettingDefinition, ...] = tuple(
            build_definition(raw) for raw in source
        )
        self._by_key: Dict[str, SettingDefinition] = {d.key: d for d in self._definitions}
        self._categories = tuple(CATEGORIES_CATALOG)
        self._category_ids = {str(category["id"]) for category in self._categories}
        self._by_category: Dict[str, List[SettingDefinition]] = {}
        self._by_section: Dict[str, List[SettingDefinition]] = {section_id: [] for section_id in SECTION_IDS}
        for definition in self._definitions:
            self._by_category.setdefault(definition.category, []).append(definition)
            self._by_section.setdefault(definition.section, []).append(definition)
        self.validate()

    def validate(self) -> None:
        """Fail fast if the registry would ship a decorative live control."""
        errors: List[str] = []
        seen: set = set()
        for definition in self._definitions:
            if definition.key in seen:
                errors.append(f"duplicate key: {definition.key}")
            seen.add(definition.key)
            if definition.category not in self._category_ids:
                errors.append(f"{definition.key}: unknown category {definition.category}")
            if definition.section not in SECTION_IDS:
                errors.append(f"{definition.key}: unknown section {definition.section}")
            if not definition.allowed_scopes:
                errors.append(f"{definition.key}: no allowed scopes")
            if definition.required_permission not in KNOWN_PERMISSIONS:
                errors.append(f"{definition.key}: unknown permission {definition.required_permission}")
            if definition.status is SettingStatus.LIVE and not definition.enforced_by:
                errors.append(f"{definition.key}: live without enforced_by")
            if definition.status is SettingStatus.LIVE and definition.key not in ENFORCED_BY:
                errors.append(f"{definition.key}: live but not in ENFORCED_BY")
            if definition.status is SettingStatus.ACTION and not definition.action_id:
                errors.append(f"{definition.key}: action without action_id")
        missing_sections = [sid for sid in SECTION_IDS if not self._by_section.get(sid)]
        # Reports & Documents has no legacy category yet; it is allowed to be
        # empty in Phase 1 and will be populated when section 9 is built.
        missing_sections = [sid for sid in missing_sections if sid != "reports_documents"]
        if missing_sections:
            errors.append(f"sections without definitions: {missing_sections}")
        if errors:
            raise ValueError("Invalid settings registry:\n" + "\n".join(errors))

    def get(self, key: str) -> Optional[SettingDefinition]:
        return self._by_key.get(key)

    def require(self, key: str) -> SettingDefinition:
        definition = self.get(key)
        if definition is None:
            raise KeyError(f"Unknown setting key: {key}")
        return definition

    def all(self) -> Tuple[SettingDefinition, ...]:
        return self._definitions

    def categories(self) -> Tuple[Dict[str, Any], ...]:
        return self._categories

    def by_category(self, category: str) -> List[SettingDefinition]:
        return list(self._by_category.get(category, []))

    def by_section(self, section_id: str) -> List[SettingDefinition]:
        return list(self._by_section.get(section_id, []))

    def live_keys(self) -> List[str]:
        return [d.key for d in self._definitions if d.status is SettingStatus.LIVE]

    def public_catalog(self) -> Dict[str, Any]:
        sections = []
        for section in SECTIONS:
            section_id = str(section["id"])
            section_defs = self.by_section(section_id)
            sections.append(
                {
                    **section,
                    "categories": [
                        category
                        for category in CATEGORY_TO_SECTION
                        if CATEGORY_TO_SECTION[category] == section_id
                    ],
                    "setting_count": len(section_defs),
                    "live_count": sum(1 for d in section_defs if d.status is SettingStatus.LIVE),
                    "coming_soon_count": sum(
                        1 for d in section_defs if d.status is SettingStatus.COMING_SOON
                    ),
                    "hidden_count": sum(1 for d in section_defs if d.status is SettingStatus.HIDDEN),
                    "action_count": sum(1 for d in section_defs if d.status is SettingStatus.ACTION),
                }
            )
        return {
            "sections": sections,
            "categories": [
                {
                    **category,
                    "section": CATEGORY_TO_SECTION.get(str(category["id"]), "advanced_danger"),
                }
                for category in self._categories
            ],
            "settings": [definition.to_public_dict() for definition in self._definitions],
            "counts": self.counts(),
        }

    def counts(self) -> Dict[str, int]:
        values = {status.value: 0 for status in SettingStatus}
        for definition in self._definitions:
            values[definition.status.value] += 1
        values["total"] = len(self._definitions)
        values["categories"] = len(self._categories)
        values["sections"] = len(SECTIONS)
        return values

    def coverage_report(self) -> Dict[str, Any]:
        live = [d.key for d in self._definitions if d.status is SettingStatus.LIVE]
        coming_soon = [d.key for d in self._definitions if d.status is SettingStatus.COMING_SOON]
        hidden = [d.key for d in self._definitions if d.status is SettingStatus.HIDDEN]
        actions = [d.key for d in self._definitions if d.status is SettingStatus.ACTION]
        categories_without_live = [
            str(category["id"])
            for category in self._categories
            if not any(d.status is SettingStatus.LIVE for d in self.by_category(str(category["id"])))
        ]
        return {
            "counts": self.counts(),
            "live_keys": live,
            "coming_soon_keys": coming_soon,
            "hidden_keys": hidden,
            "action_keys": actions,
            "categories_without_live": categories_without_live,
            "enforced_by_count": sum(1 for d in self._definitions if d.enforced_by),
            "secret_keys": [d.key for d in self._definitions if d.secret],
            "sensitive_text_keys": [d.key for d in self._definitions if d.sensitive and not d.secret],
            "requires_restart_keys": [d.key for d in self._definitions if d.requires_restart],
            "plan_gated_keys": [d.key for d in self._definitions if d.plan_gate],
        }


settings_registry = SettingsRegistry()
