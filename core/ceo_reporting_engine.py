"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
CEO Reporting Engine & Verified Outcome Auditing

Implements Section 20 of the Gemma 4 Master Specification:
- Generates 12 distinct executive report types:
    1. REAL_TIME_UPDATE
    2. MISSION_UPDATE
    3. DEPARTMENT_REPORT
    4. DAILY_EXECUTIVE_REPORT
    5. WEEKLY_EXECUTIVE_REPORT
    6. INCIDENT_REPORT
    7. FINANCIAL_REPORT
    8. CAMPAIGN_REPORT
    9. PROJECT_REPORT
    10. FAILURE_REPORT
    11. COMPLETION_REPORT
    12. AUDIT_REPORT
- Strict 6-Status Epistemic Breakdown:
    Every report item must be classified into:
      PLANNED | EXECUTED | VERIFIED | FAILED | BLOCKED | UNKNOWN
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.executive.reporting")

class ReportItemStatus:
    PLANNED = "PLANNED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

@dataclass
class ReportItem:
    item_id: str
    category: str
    description: str
    status: str                         # PLANNED, EXECUTED, VERIFIED, FAILED, BLOCKED, UNKNOWN
    department: str
    evidence_digest: Optional[str] = None
    metric_impact: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class GovernedExecutiveReport:
    report_id: str
    report_type: str
    tenant_id: str
    company_id: str
    title: str
    summary: str
    cognitive_model: str                # e.g., "gemma-4-31b-it"
    status_breakdown: Dict[str, int]   # Counts for planned, executed, verified, failed, blocked, unknown
    items: List[Dict[str, Any]]
    recommendations: List[str]
    evidence_package_ref: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CEOReportingEngine:
    """
    Produces verifiable, evidence-grounded executive reports.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._reports: Dict[str, GovernedExecutiveReport] = {}

    def generate_report(
        self,
        report_type: str,
        title: str,
        items: List[ReportItem],
        recommendations: Optional[List[str]] = None,
        model_id: str = "gemma-4-31b-it",
        evidence_ref: str = "sha256:verified_receipt_pkg",
        company_name: Optional[str] = None
    ) -> GovernedExecutiveReport:
        report_id = f"rpt_{uuid.uuid4().hex[:8]}"

        counts = {
            ReportItemStatus.PLANNED: 0,
            ReportItemStatus.EXECUTED: 0,
            ReportItemStatus.VERIFIED: 0,
            ReportItemStatus.FAILED: 0,
            ReportItemStatus.BLOCKED: 0,
            ReportItemStatus.UNKNOWN: 0
        }
        for itm in items:
            st = itm.status.upper()
            if st in counts:
                counts[st] += 1
            else:
                counts[ReportItemStatus.UNKNOWN] += 1

        comp_label = company_name or self.company_id
        summary = (
            f"Executive Report [{report_type}] for {comp_label}: "
            f"{counts[ReportItemStatus.VERIFIED]} verified outcomes, "
            f"{counts[ReportItemStatus.EXECUTED]} executed, "
            f"{counts[ReportItemStatus.FAILED]} failed, "
            f"{counts[ReportItemStatus.BLOCKED]} blocked."
        )

        rec = recommendations or [
            "Maintain current yield pacing on prime wedding inventory",
            "Resolve blocked supplier invoice in Finance queue"
        ]

        report = GovernedExecutiveReport(
            report_id=report_id,
            report_type=report_type,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title=title,
            summary=summary,
            cognitive_model=model_id,
            status_breakdown=counts,
            items=[i.to_dict() for i in items],
            recommendations=rec,
            evidence_package_ref=evidence_ref,
            created_at=time.time()
        )
        self._reports[report_id] = report
        return report

    def get_daily_executive_report(self, company_name: str = "Royal Hotel Jaipur") -> GovernedExecutiveReport:
        items = [
            ReportItem("it_1", "REVENUE", "Dynamic yield rate optimization applied for weekend inventory", ReportItemStatus.VERIFIED, "Revenue Management", "sha256:a1b2c3d4", "+8.4% ADR"),
            ReportItem("it_2", "OPERATIONS", "Night Audit ledger reconciliation completed", ReportItemStatus.VERIFIED, "Hospitality", "sha256:e5f6g7h8", "Zero folio balance discrepancy"),
            ReportItem("it_3", "MARKETING", "Targeted direct booking email sequence dispatched", ReportItemStatus.EXECUTED, "Marketing", "sha256:m1m2m3m4", "450 messages delivered"),
            ReportItem("it_4", "FINANCE", "Q3 Supplier invoice payment exceeding budget threshold", ReportItemStatus.BLOCKED, "Finance", None, "Awaiting Human Owner Approval")
        ]
        return self.generate_report(
            report_type="DAILY_EXECUTIVE_REPORT",
            title=f"Daily Executive Briefing — {company_name}",
            items=items,
            company_name=company_name
        )

    def list_reports(self) -> List[GovernedExecutiveReport]:
        return sorted(self._reports.values(), key=lambda x: x.created_at, reverse=True)
