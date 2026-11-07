"""Enterprise settings package.

Phase 1 exposes the canonical definitions, typed registry, and schema helpers.
The resolver, RBAC, secrets vault, and API live in later phases.
"""

from core.settings.definitions import (
    CATEGORIES_CATALOG,
    DOMAIN_ALIASES,
    DOMAIN_CHILD_CATEGORIES,
    GROUPS,
    SETTINGS_DEFINITIONS,
)
from core.settings.models import (
    ActorType,
    ApprovalRequest,
    ApprovalStatus,
    EffectiveSetting,
    ScopeType,
    SecretRef,
    SettingDefinition,
    SettingStatus,
    ValidationSpec,
)
from core.settings.registry import SettingsRegistry, settings_registry
from core.settings.schema import ensure_schema, verify_schema
from core.settings.sections import SECTIONS, SECTION_IDS, section_for_category

__all__ = [
    "CATEGORIES_CATALOG",
    "DOMAIN_ALIASES",
    "DOMAIN_CHILD_CATEGORIES",
    "GROUPS",
    "SETTINGS_DEFINITIONS",
    "ActorType",
    "ApprovalRequest",
    "ApprovalStatus",
    "EffectiveSetting",
    "ScopeType",
    "SecretRef",
    "SettingDefinition",
    "SettingStatus",
    "ValidationSpec",
    "SettingsRegistry",
    "settings_registry",
    "ensure_schema",
    "verify_schema",
    "SECTIONS",
    "SECTION_IDS",
    "section_for_category",
]
