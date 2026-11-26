"""
Work Order Lifecycle Management Engine
======================================
Lifecycle: draft -> released -> in_progress -> completed -> closed.
Tracks material issuance, scrap rates, and operation dispatches.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class WorkOrderOperation(BaseModel):
    operation_id: str
    operation_name: str
    workstation_id: str
    planned_hours: float
    actual_hours: float = 0.0
    status: str = "pending"  # 'pending', 'in_progress', 'completed'


class WorkOrder(BaseModel):
    work_order_id: str
    tenant_id: str
    company_id: str
    product_id: str
    planned_quantity: float
    completed_quantity: float = 0.0
    scrapped_quantity: float = 0.0
    status: str = "draft"  # 'draft', 'released', 'in_progress', 'completed', 'closed'
    operations: List[WorkOrderOperation] = Field(default_factory=list)
    issued_materials: Dict[str, float] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkOrderManager:
    """Manages manufacturing work orders, material issuance, and completion tracking."""

    def __init__(self):
        self.orders: Dict[str, WorkOrder] = {}

    def create_work_order(self, wo: WorkOrder) -> WorkOrder:
        key = f"{wo.tenant_id}:{wo.company_id}:{wo.work_order_id}"
        self.orders[key] = wo
        return wo

    def release_work_order(self, tenant_id: str, company_id: str, wo_id: str) -> WorkOrder:
        key = f"{tenant_id}:{company_id}:{wo_id}"
        wo = self.orders.get(key)
        if not wo:
            raise KeyError(f"Work order {wo_id} not found")
        if wo.status != "draft":
            raise RuntimeError(f"Cannot release work order in status: {wo.status}")
        wo.status = "released"
        return wo

    def start_work_order(self, tenant_id: str, company_id: str, wo_id: str) -> WorkOrder:
        key = f"{tenant_id}:{company_id}:{wo_id}"
        wo = self.orders.get(key)
        if not wo:
            raise KeyError(f"Work order {wo_id} not found")
        if wo.status != "released":
            raise RuntimeError("Work order must be released before starting")
        wo.status = "in_progress"
        return wo

    def record_production_output(
        self,
        tenant_id: str,
        company_id: str,
        wo_id: str,
        good_qty: float,
        scrapped_qty: float
    ) -> WorkOrder:
        key = f"{tenant_id}:{company_id}:{wo_id}"
        wo = self.orders.get(key)
        if not wo:
            raise KeyError(f"Work order {wo_id} not found")

        wo.completed_quantity += good_qty
        wo.scrapped_quantity += scrapped_qty

        if wo.completed_quantity + wo.scrapped_quantity >= wo.planned_quantity:
            wo.status = "completed"

        return wo

    def calculate_scrap_rate(self, wo: WorkOrder) -> float:
        total = wo.completed_quantity + wo.scrapped_quantity
        if total == 0:
            return 0.0
        return round(wo.scrapped_quantity / total, 4)
