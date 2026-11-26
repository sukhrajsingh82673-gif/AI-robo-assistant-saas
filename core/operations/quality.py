"""
Quality Control & Inspection Quarantine Engine
==============================================
Manages inspection lots, sampling (AQL), and mandatory quarantine holds.
Invariant: Any failed inspection lot is quarantined and strictly forbidden
from being issued to work orders or shipped to customers.
"""

from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class InspectionLot(BaseModel):
    lot_id: str
    tenant_id: str
    company_id: str
    item_id: str
    batch_number: str
    lot_size: int
    sample_size: int
    defect_count: int
    aql_max_defects: int
    status: str = "pending"  # 'pending', 'approved', 'quarantined'
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None
    inspected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QualityControlManager:
    """Evaluates inspection results and enforces lot quarantine isolation."""

    def __init__(self):
        self.lots: Dict[str, InspectionLot] = {}

    def record_inspection_result(
        self,
        lot_id: str,
        tenant_id: str,
        company_id: str,
        item_id: str,
        batch_number: str,
        lot_size: int,
        sample_size: int,
        defect_count: int,
        aql_max_defects: int
    ) -> InspectionLot:
        # Strict AQL pass/fail evaluation
        failed = defect_count > aql_max_defects
        status = "quarantined" if failed else "approved"
        reason = f"Defects ({defect_count}) exceeded AQL limit ({aql_max_defects})" if failed else None

        lot = InspectionLot(
            lot_id=lot_id,
            tenant_id=tenant_id,
            company_id=company_id,
            item_id=item_id,
            batch_number=batch_number,
            lot_size=lot_size,
            sample_size=sample_size,
            defect_count=defect_count,
            aql_max_defects=aql_max_defects,
            status=status,
            is_quarantined=failed,
            quarantine_reason=reason
        )
        key = f"{tenant_id}:{company_id}:{lot_id}"
        self.lots[key] = lot
        return lot

    def can_dispatch_or_consume(self, tenant_id: str, company_id: str, lot_id: str) -> Tuple[bool, Optional[str]]:
        """Strict quarantine gate: blocks issuance or dispatch of quarantined lots."""
        key = f"{tenant_id}:{company_id}:{lot_id}"
        lot = self.lots.get(key)
        if not lot:
            return False, f"Inspection lot {lot_id} not found"

        if lot.is_quarantined:
            return False, f"Quarantine Lock: Lot {lot_id} failed quality inspection ({lot.quarantine_reason})"

        if lot.status != "approved":
            return False, f"Quality Gate: Lot {lot_id} is in status '{lot.status}' and not approved"

        return True, None
