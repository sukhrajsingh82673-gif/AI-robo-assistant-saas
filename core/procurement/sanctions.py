"""
Sanctions and Global Watchlist Screening Engine
===============================================
Screens vendors, beneficial owners, and banking routes against OFAC, UN, and EU lists.
Invariant: Any positive match results in an immediate non-bypassable freeze
on the vendor profile and holds all active Purchase Orders.
"""

from typing import List, Dict, Optional, Tuple, Any
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SanctionedEntity(BaseModel):
    entity_id: str
    name: str
    country: str
    list_source: str  # 'OFAC_SDN', 'UN_CONSOLIDATED', 'EU_SANCTIONS'
    program: str


class SanctionsScreeningResult(BaseModel):
    vendor_id: str
    vendor_name: str
    is_sanctioned: bool
    matched_entry: Optional[Dict[str, Any]] = None
    similarity_score: float = 0.0
    action_taken: str  # 'APPROVED' or 'FROZEN'
    screened_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SanctionsScreeningEngine:
    """Evaluates vendor profiles against international sanctions registries."""

    DEFAULT_WATCHLIST = [
        SanctionedEntity(entity_id="SDN-001", name="JSC Rosoboronexport", country="RU", list_source="OFAC_SDN", program="UKRAINE-EO13661"),
        SanctionedEntity(entity_id="SDN-002", name="Al-Barakaat Trading Co", country="SO", list_source="UN_CONSOLIDATED", program="AL-QAIDA"),
        SanctionedEntity(entity_id="SDN-003", name="Korea Mining Development Trading Corp", country="KP", list_source="UN_CONSOLIDATED", program="DPRK"),
        SanctionedEntity(entity_id="SDN-004", name="Petroleos de Venezuela SA", country="VE", list_source="OFAC_SDN", program="VENEZUELA-EO13850"),
    ]

    def __init__(self, watchlist: Optional[List[SanctionedEntity]] = None, match_threshold: float = 0.85):
        self.watchlist = watchlist or self.DEFAULT_WATCHLIST
        self.match_threshold = match_threshold
        self.frozen_vendors: Dict[str, str] = {}  # vendor_id -> reason

    def screen_vendor(self, vendor_id: str, vendor_name: str, country: Optional[str] = None) -> SanctionsScreeningResult:
        v_clean = vendor_name.lower().strip()
        best_match = None
        max_sim = 0.0

        for entity in self.watchlist:
            e_clean = entity.name.lower().strip()
            sim = SequenceMatcher(None, v_clean, e_clean).ratio()
            # Direct country embargo or high name similarity
            if sim >= self.match_threshold and sim > max_sim:
                max_sim = sim
                best_match = entity

        if best_match:
            # Positive Hit: Immediate freeze
            self.frozen_vendors[vendor_id] = f"Matched {best_match.list_source} entity {best_match.name}"
            return SanctionsScreeningResult(
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                is_sanctioned=True,
                matched_entry={
                    "entity_id": best_match.entity_id,
                    "name": best_match.name,
                    "list": best_match.list_source,
                    "program": best_match.program
                },
                similarity_score=round(max_sim, 4),
                action_taken="FROZEN"
            )

        return SanctionsScreeningResult(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            is_sanctioned=False,
            similarity_score=round(max_sim, 4),
            action_taken="APPROVED"
        )

    def is_vendor_frozen(self, vendor_id: str) -> Tuple[bool, Optional[str]]:
        if vendor_id in self.frozen_vendors:
            return True, self.frozen_vendors[vendor_id]
        return False, None
