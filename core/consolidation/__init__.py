"""
ZONATA Group Consolidation Package (Step 8D)
============================================
Additive consolidation engine for multi-company groups.
"""

from core.consolidation.engine import (
    ConsolidationEngine,
    ConsolidationMethod,
    LegalEntity,
    IntercompanyTransaction,
)

__all__ = [
    "ConsolidationEngine",
    "ConsolidationMethod",
    "LegalEntity",
    "IntercompanyTransaction",
]
