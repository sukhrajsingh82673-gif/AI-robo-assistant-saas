"""
ZONATA CEO Cadence Engine
OpenCode Step 2J: Scheduled cadence reviews (daily, weekly, monthly) reading stored metrics.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List

from core.db import db
from core.executive.risk import CompanyRiskService
from core.executive.reporting import CEOReportingService
from core.executive.types import RiskTriggerType, RiskSeverity


class CEOCadenceEngine:
    """
    Executes scheduled executive review cycles across metrics, risks, and owner reports.
    """

    @classmethod
    def run_daily_cadence(cls, tenant_id: str, company_id: str) -> Dict[str, Any]:
        """Runs the daily executive review cycle."""
        results = {"kpi_checks": 0, "sla_breaches_checked": 0, "risks_identified": 0}

        # 1. Scan for critical KPI snapshots
        with db.get_connection() as conn:
            crit_kpis = conn.execute(
                "SELECT * FROM kpi_snapshots WHERE tenant_id = ? AND company_id = ? AND status = 'CRITICAL'",
                (tenant_id, company_id)
            ).fetchall()

        for k in crit_kpis:
            results["kpi_checks"] += 1
            CompanyRiskService.record_risk_and_propose_task(
                tenant_id=tenant_id,
                company_id=company_id,
                trigger_type=RiskTriggerType.KPI_OFF_TRACK,
                severity=RiskSeverity.HIGH,
                details={"kpi_id": k["kpi_id"], "value": k["current_value"], "status": "CRITICAL"},
                corrective_task_title=f"Resolve Critical KPI Breach on {k['kpi_id']}",
            )
            results["risks_identified"] += 1

        # 2. Generate daily owner report with number-lock
        report = CEOReportingService.generate_owner_report(tenant_id, company_id)
        results["report"] = report
        return results
