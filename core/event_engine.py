"""
RoboAssistant Company OS 2.0 — Continuous Enterprise Event Engine
Monitors operational events, performs severity and impact classification,
and autonomously triggers governed missions within authorized policy bounds.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
from .db import db
from .models import Mission, MissionStatus
from .portfolio import CompanyPortfolioManager
from .ceo_chief_of_staff import ChiefOfStaff

class EventSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EnterpriseEventType:
    REVENUE_ANOMALY = "REVENUE_ANOMALY"
    COST_SPIKE = "COST_SPIKE"
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    LEAD_RECEIVED = "LEAD_RECEIVED"
    CUSTOMER_COMPLAINT = "CUSTOMER_COMPLAINT"
    SYSTEM_OUTAGE = "SYSTEM_OUTAGE"
    KPI_DEVIATION = "KPI_DEVIATION"

class EnterpriseEventEngine:
    def __init__(self, portfolio: CompanyPortfolioManager, tenant_id: str = "tnt_primary"):
        self.portfolio = portfolio
        self.tenant_id = tenant_id

    def emit_event(
        self,
        company_id: str,
        event_type: str,
        category: str,
        severity: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Emits an enterprise event and evaluates automatic mission creation.
        """
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        now = time.time()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO enterprise_events (
                    event_id, tenant_id, company_id, event_type, category,
                    severity, details, handled, resulting_mission_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                """,
                (event_id, self.tenant_id, company_id, event_type, category, severity, json.dumps(details), now)
            )
            conn.commit()

        # Autonomous evaluation
        resulting_mission_id = None
        if severity in (EventSeverity.LOW, EventSeverity.MEDIUM):
            resulting_mission_id = self._autonomously_dispatch_mission(company_id, event_id, event_type, details)
        else:
            # High / Critical severity: Escalate to Chief of Staff & Owner Decision Center
            cos = ChiefOfStaff(self.tenant_id, company_id)
            cos.add_inbox_item(
                item_type="DECISION_QUEUE",
                title=f"Critical Alert: {event_type}",
                details=f"Severity {severity}: {json.dumps(details)}",
                priority="URGENT"
            )

        if resulting_mission_id:
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE enterprise_events SET handled = 1, resulting_mission_id = ? WHERE event_id = ?",
                    (resulting_mission_id, event_id)
                )
                conn.commit()

        return {
            "event_id": event_id,
            "company_id": company_id,
            "event_type": event_type,
            "severity": severity,
            "handled": bool(resulting_mission_id),
            "resulting_mission_id": resulting_mission_id,
            "timestamp": now
        }

    def _autonomously_dispatch_mission(self, company_id: str, event_id: str, event_type: str, details: Dict[str, Any]) -> str:
        """
        Autonomously generates an investigation mission within authorized autonomy bounds.
        """
        mission_id = f"mis_evt_{uuid.uuid4().hex[:6]}"
        comp = next((c for c in self.portfolio.list_companies() if c.company_id == company_id), None)
        dept = "Operations"
        if "REVENUE" in event_type or "PAYMENT" in event_type:
            dept = "Finance"
        elif "LEAD" in event_type:
            dept = "Commercial Sales"

        title = f"Autonomous Mitigation: {event_type.replace('_', ' ').title()}"
        target_outcome = f"Diagnose root cause and execute mitigation for {event_type}"

        # Persist into database missions
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO missions (
                    mission_id, company_id, tenant_id, title, owner_agent, department,
                    target_outcome, status, progress, financials, started_at
                ) VALUES (?, ?, ?, ?, 'AI CEO', ?, ?, 'EXECUTE', 10, ?, ?)
                """,
                (
                    mission_id, company_id, self.tenant_id, title, dept, target_outcome,
                    json.dumps({"revenue_generated": 0.0, "cost_incurred": 0.0, "contribution": 0.0}),
                    time.time()
                )
            )
            conn.commit()

        return mission_id

    def list_unhandled_events(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            if company_id:
                rows = conn.execute(
                    "SELECT * FROM enterprise_events WHERE company_id = ? AND handled = 0 ORDER BY created_at DESC",
                    (company_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM enterprise_events WHERE handled = 0 ORDER BY created_at DESC"
                ).fetchall()

            events = []
            for r in rows:
                d = dict(r)
                try:
                    d["details"] = json.loads(d["details"])
                except Exception:
                    pass
                events.append(d)
            return events
