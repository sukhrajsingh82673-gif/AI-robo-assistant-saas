"""
RoboAssistant Company OS 1.0 — Owner Decision Center ('ATTENTION REQUIRED')
Aggregates and prioritizes pending approvals, unresolved data conflicts, failed missions,
budget alerts, and unverified business outcomes based on real business impact.
Section 63 Invariant: Prioritize on actual severity; never fabricate urgency.
"""

from typing import Dict, Any, List, Optional
import time
from .approvals import ApprovalPipeline
from .intelligence import RiskEngine
from .financials import BudgetHierarchyEngine
from .db import db

class DecisionItemPriority:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class OwnerDecisionCenter:
    """
    Unified attention aggregator for executive owners.
    """

    @staticmethod
    def get_attention_required_items(tenant_id: str, company_id: Optional[str] = None) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []

        # 1. Pending Approvals
        pending_approvals = ApprovalPipeline.list_approvals(tenant_id, status="PENDING")
        for app in pending_approvals:
            if company_id and app.get("company_id") != company_id:
                continue
            prio = DecisionItemPriority.CRITICAL if app.get("risk_level") == "HIGH" else DecisionItemPriority.HIGH
            items.append({
                "category": "APPROVAL_REQUIRED",
                "item_id": app["request_id"],
                "title": f"Grant Approval Needed: {app['action_desc']}",
                "reason": app.get("reason", "Operational action requires authorization"),
                "consequence": app.get("consequence", "State mutation pending"),
                "priority": prio,
                "severity_score": 0.9 if prio == DecisionItemPriority.CRITICAL else 0.7,
                "created_at": app.get("requested_at", time.time())
            })

        # 2. Discovered Operational Risks
        risks = RiskEngine.list_intelligence_items(tenant_id, company_id=company_id)
        for rk in risks:
            if rk.get("item_type") == "RISK":
                prio = DecisionItemPriority.HIGH if rk.get("severity_or_confidence", 0) > 0.8 else DecisionItemPriority.MEDIUM
                items.append({
                    "category": "OPERATIONAL_RISK",
                    "item_id": rk["item_id"],
                    "title": rk["title"],
                    "reason": rk.get("evidence", "Telemetry anomaly detected"),
                    "consequence": rk.get("potential_impact", "Performance impact"),
                    "priority": prio,
                    "severity_score": rk.get("severity_or_confidence", 0.6),
                    "created_at": rk.get("discovered_at", time.time())
                })

        # 3. Failed or Blocked Missions
        with db.get_connection() as conn:
            query = "SELECT * FROM missions WHERE tenant_id = ? AND status IN ('FAILED', 'BLOCKED')"
            params = [tenant_id]
            if company_id:
                query += " AND company_id = ?"
                params.append(company_id)
            for m in conn.execute(query, params).fetchall():
                items.append({
                    "category": "MISSION_INCIDENT",
                    "item_id": m["mission_id"],
                    "title": f"Mission {m['status']}: {m['title']}",
                    "reason": m["verification_summary"] or "Execution blocked by policy or dependency failure",
                    "consequence": "Strategic objective paused",
                    "priority": DecisionItemPriority.HIGH,
                    "severity_score": 0.75,
                    "created_at": m["started_at"]
                })

        # Sort items by severity score descending
        items.sort(key=lambda x: x["severity_score"], reverse=True)

        return {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "total_items": len(items),
            "critical_count": sum(1 for i in items if i["priority"] == DecisionItemPriority.CRITICAL),
            "high_count": sum(1 for i in items if i["priority"] == DecisionItemPriority.HIGH),
            "items": items,
            "evaluated_at": time.time()
        }
