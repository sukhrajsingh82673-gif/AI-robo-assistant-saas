"""
Entitlements package for plan tier evaluation and quota management.
"""

from .engine import EntitlementsEngine, EntitlementDecision

__all__ = ["EntitlementsEngine", "EntitlementDecision"]
