"""
ZONATA Industry Depth Factory Package (Step 8)
==============================================
Provides declarative industry overlays (zonata.industry-overlay/v1),
multi-scheme taxonomies (ISIC Rev. 5, Rev. 4, NACE Rev. 2.1, NAICS 2022),
domain calculators, sector boundary enforcement (Rule 72),
maturity tiers (T0-T4), and expert review protocols (Rule 71).
"""

from core.industry.flags import is_industry_factory_enabled, set_industry_factory_flag
from core.industry.tiers import OverlayTier, TierManager
from core.industry.boundary import SectorBoundaryEnforcer, BoundaryViolationError
from core.industry.expert_review import ExpertReviewProtocol, AIReviewerProhibitedError

__all__ = [
    "is_industry_factory_enabled",
    "set_industry_factory_flag",
    "OverlayTier",
    "TierManager",
    "SectorBoundaryEnforcer",
    "BoundaryViolationError",
    "ExpertReviewProtocol",
    "AIReviewerProhibitedError",
]
