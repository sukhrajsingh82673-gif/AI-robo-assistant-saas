"""
Inventory Policy & Reorder Point (ROP / EOQ) Engine
===================================================
Calculates:
- Economic Order Quantity (EOQ): sqrt((2 * D * S) / H)
- Safety Stock (SS): Z * std_dev_demand * sqrt(lead_time)
- Reorder Point (ROP): (daily_demand * lead_time) + safety_stock
Generates automated Purchase Requisitions when stock <= ROP.
"""

import math
from typing import Optional, Tuple
from pydantic import BaseModel, Field


class ReorderPolicy(BaseModel):
    item_id: str
    annual_demand: float
    daily_demand: float
    order_cost_s: float  # Setup / ordering cost per order
    annual_holding_cost_h: float  # Holding cost per unit per year
    lead_time_days: float
    service_level_z: float = 1.65  # 95% service level
    demand_std_dev: float = 5.0
    eoq: float = 0.0
    safety_stock: float = 0.0
    reorder_point: float = 0.0


class PurchaseRequisition(BaseModel):
    requisition_id: str
    item_id: str
    current_stock: float
    reorder_point: float
    recommended_order_quantity: float
    reason: str


class ReorderPolicyEngine:
    """Calculates optimal inventory replenishment parameters and detects trigger points."""

    @staticmethod
    def calculate_policy(
        item_id: str,
        annual_demand: float,
        order_cost: float,
        holding_cost: float,
        lead_time_days: float,
        demand_std_dev: float = 5.0,
        service_level_z: float = 1.65
    ) -> ReorderPolicy:
        if annual_demand <= 0 or order_cost <= 0 or holding_cost <= 0 or lead_time_days <= 0:
            raise ValueError("All inventory parameters must be positive")

        daily_demand = annual_demand / 365.0

        # 1. Economic Order Quantity: sqrt((2 * D * S) / H)
        eoq = math.sqrt((2.0 * annual_demand * order_cost) / holding_cost)

        # 2. Safety Stock: Z * sigma_d * sqrt(L)
        safety_stock = service_level_z * demand_std_dev * math.sqrt(lead_time_days)

        # 3. Reorder Point: (d * L) + SS
        lead_time_demand = daily_demand * lead_time_days
        reorder_point = lead_time_demand + safety_stock

        return ReorderPolicy(
            item_id=item_id,
            annual_demand=annual_demand,
            daily_demand=round(daily_demand, 3),
            order_cost_s=order_cost,
            annual_holding_cost_h=holding_cost,
            lead_time_days=lead_time_days,
            service_level_z=service_level_z,
            demand_std_dev=demand_std_dev,
            eoq=round(eoq, 2),
            safety_stock=round(safety_stock, 2),
            reorder_point=round(reorder_point, 2)
        )

    @staticmethod
    def check_stock_and_reorder(
        policy: ReorderPolicy,
        current_available_stock: float
    ) -> Tuple[bool, Optional[PurchaseRequisition]]:
        """Emits purchase requisition if available stock falls to or below reorder point."""
        if current_available_stock <= policy.reorder_point:
            import uuid
            req = PurchaseRequisition(
                requisition_id=f"pr_{uuid.uuid4().hex[:10]}",
                item_id=policy.item_id,
                current_stock=current_available_stock,
                reorder_point=policy.reorder_point,
                recommended_order_quantity=policy.eoq,
                reason=f"Stock ({current_available_stock}) at or below reorder point ({policy.reorder_point})"
            )
            return True, req
        return False, None
