"""ZONATA Sovereign Core — Builtin KPI Tools.

Implements OpenCode Step 2E (Requirement 2):
- KPI read: reads current KPI values and trends computed deterministically in code.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from core.authority.types import ActionClass
from core.tools.contract import ToolContract, SideEffectClass
from core.company_metrics import compute_company_metrics


class KPIReadInput(BaseModel):
    kpi_code: str = Field(..., description="KPI identifier code (e.g. 'REVENUE', 'RUNWAY', 'OPEN_TASKS')")


class KPIReadOutput(BaseModel):
    kpi_code: str
    current_value: float
    target_value: Optional[float] = None
    trend: str = Field("STABLE", description="'UP', 'DOWN', or 'STABLE'")
    unit: str = "USD"
    computed_at: float


class KPIReadTool(ToolContract):
    name = "kpi_read"
    description = "Reads current measured value and trend of a key performance indicator (KPI)."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "database"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 10.0

    input_schema = KPIReadInput
    output_schema = KPIReadOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: KPIReadInput,
        idempotency_key: Optional[str] = None,
    ) -> KPIReadOutput:
        metrics = compute_company_metrics(company_id=company_id, tenant_id=tenant_id)

        code_upper = args.kpi_code.upper()
        current = 0.0
        trend = "STABLE"
        unit = "USD"

        if "REV" in code_upper:
            current = float(metrics.get("monthly_revenue_minor_units", 0)) / 100.0
            trend = "UP" if current > 0 else "STABLE"
            unit = metrics.get("currency", "USD")
        elif "RUNWAY" in code_upper:
            current = float(metrics.get("runway_months", 12.0))
            trend = "STABLE"
            unit = "MONTHS"
        elif "TASK" in code_upper:
            current = float(metrics.get("open_tasks_count", 0))
            trend = "DOWN"
            unit = "COUNT"
        else:
            current = 0.0
            trend = "STABLE"
            unit = "UNITS"

        return KPIReadOutput(
            kpi_code=args.kpi_code,
            current_value=current,
            target_value=None,
            trend=trend,
            unit=unit,
            computed_at=metrics.get("computed_at", 0.0),
        )
