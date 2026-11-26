"""
Multi-Level Bill of Materials (BOM) Explosion Engine
===================================================
Features:
- Recursive multi-level indented BOM explosion
- Critical-path lead time rollups across subassemblies
- Component availability check against lot inventory with shortage alerts
"""

from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field


class BOMNode(BaseModel):
    item_id: str
    description: str
    quantity_per_parent: float
    lead_time_days: int
    is_assembly: bool = False
    children: List["BOMNode"] = Field(default_factory=list)


class ExplodedRequirement(BaseModel):
    item_id: str
    description: str
    level: int
    required_quantity: float
    available_quantity: float
    shortage_quantity: float
    cumulative_lead_time_days: int
    is_shortage: bool


class BOMExplosionResult(BaseModel):
    parent_item_id: str
    target_production_quantity: float
    total_lead_time_days: int
    has_shortages: bool
    shortage_items: List[str] = Field(default_factory=list)
    exploded_requirements: List[ExplodedRequirement] = Field(default_factory=list)


class BOMExplosionEngine:
    """Recursively explodes multi-level BOMs, rolls up lead times, and alerts on inventory shortages."""

    def explode(
        self,
        root: BOMNode,
        target_quantity: float,
        inventory_balances: Dict[str, float]
    ) -> BOMExplosionResult:
        exploded: List[ExplodedRequirement] = []
        shortage_items: List[str] = []

        def _traverse(node: BOMNode, parent_qty: float, level: int, current_lead_time: int) -> int:
            req_qty = parent_qty * node.quantity_per_parent
            cum_lead = current_lead_time + node.lead_time_days

            avail_qty = inventory_balances.get(node.item_id, 0.0)
            shortage = max(0.0, req_qty - avail_qty)
            is_short = shortage > 0

            if is_short and not node.is_assembly:
                shortage_items.append(node.item_id)

            exploded.append(ExplodedRequirement(
                item_id=node.item_id,
                description=node.description,
                level=level,
                required_quantity=round(req_qty, 3),
                available_quantity=round(avail_qty, 3),
                shortage_quantity=round(shortage, 3),
                cumulative_lead_time_days=cum_lead,
                is_shortage=is_short
            ))

            max_child_lead = cum_lead
            for child in node.children:
                child_lead = _traverse(child, req_qty, level + 1, cum_lead)
                if child_lead > max_child_lead:
                    max_child_lead = child_lead

            return max_child_lead

        # Traverse all child nodes
        max_total_lead = root.lead_time_days
        for child in root.children:
            l = _traverse(child, target_quantity, 1, root.lead_time_days)
            if l > max_total_lead:
                max_total_lead = l

        return BOMExplosionResult(
            parent_item_id=root.item_id,
            target_production_quantity=target_quantity,
            total_lead_time_days=max_total_lead,
            has_shortages=len(shortage_items) > 0,
            shortage_items=shortage_items,
            exploded_requirements=exploded
        )
