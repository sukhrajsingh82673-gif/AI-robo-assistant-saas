"""
Per-Company Feature Flags for Step 8 Features (Rule 67 Invariant)
Defaults strictly to OFF to ensure bit-for-bit flags-off equivalence with Step 7 baseline.
"""

import os
from typing import Dict, Any

_PER_COMPANY_FLAGS: Dict[str, Dict[str, bool]] = {}


def is_industry_factory_enabled(company_id: str) -> bool:
    """Returns True if the Industry Depth Factory is enabled for the specified company.
    Defaults strictly to False unless explicitly enabled via environment or company setting.
    """
    # Environment override for integration tests
    env_flag = os.environ.get("STEP8_INDUSTRY_FACTORY_ENABLED", "").lower()
    if env_flag in ("1", "true", "yes"):
        return True

    # Per-company setting
    flags = _PER_COMPANY_FLAGS.get(company_id, {})
    return flags.get("industry_factory_enabled", False)


def is_global_readiness_enabled(company_id: str) -> bool:
    """Returns True if Global Corporate Readiness (multi-company consolidation, CLDR) is enabled."""
    env_flag = os.environ.get("STEP8_GLOBAL_READINESS_ENABLED", "").lower()
    if env_flag in ("1", "true", "yes"):
        return True

    flags = _PER_COMPANY_FLAGS.get(company_id, {})
    return flags.get("global_readiness_enabled", False)


def set_industry_factory_flag(company_id: str, enabled: bool) -> None:
    """Sets the industry factory flag for a specific company."""
    if company_id not in _PER_COMPANY_FLAGS:
        _PER_COMPANY_FLAGS[company_id] = {}
    _PER_COMPANY_FLAGS[company_id]["industry_factory_enabled"] = bool(enabled)


def set_global_readiness_flag(company_id: str, enabled: bool) -> None:
    """Sets the global corporate readiness flag for a specific company."""
    if company_id not in _PER_COMPANY_FLAGS:
        _PER_COMPANY_FLAGS[company_id] = {}
    _PER_COMPANY_FLAGS[company_id]["global_readiness_enabled"] = bool(enabled)


def reset_step8_flags() -> None:
    """Resets all per-company flags (used for clean fixture setup)."""
    _PER_COMPANY_FLAGS.clear()
