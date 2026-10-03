"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Enterprise Alerting & Notification Engine
Monitors operational health against thresholds and triggers structured SRE alerts.
"""

import time
import json
import logging
from typing import Dict, List, Optional, Any
from .db import db
from .observability_stack import sre_metrics, PrometheusMetricsRegistry

logger = logging.getLogger("zonata.alerts")

class AlertSeverity:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AlertingEngine:
    """
    Evaluates real-time health and outbox queues to fire actionable SRE alerts.
    """

    DEFINED_ALERTS = [
        {
            "alert_id": "ALT_OUTBOX_BACKLOG",
            "name": "Outbox Dispatch Backlog",
            "severity": AlertSeverity.HIGH,
            "owner": "SRE_ONCALL",
            "runbook": "docs/runbooks/OUTBOX_BACKLOG.md",
            "metric": "zonata_outbox_queue_depth",
            "threshold": 50,
            "response": "Scale outbox dispatch workers",
            "escalation": "Escalate to Platform Lead"
        },
        {
            "alert_id": "ALT_RECONCILIATION_DRIFT",
            "name": "External Action Drift Detected",
            "severity": AlertSeverity.CRITICAL,
            "owner": "REVENUE_CONTROLLER",
            "runbook": "docs/runbooks/RECONCILIATION_DRIFT.md",
            "metric": "zonata_reconciliation_drift_total",
            "threshold": 1,
            "response": "Halt autonomous rate mutations and inspect PMS log",
            "escalation": "Escalate to Human Owner"
        },
        {
            "alert_id": "ALT_KILLSWITCH_ENGAGED",
            "name": "Platform KillSwitch Barrier Active",
            "severity": AlertSeverity.CRITICAL,
            "owner": "SECURITY_OFFICER",
            "runbook": "docs/runbooks/KILLSWITCH_ENGAGED.md",
            "metric": "zonata_killswitch_activations_total",
            "threshold": 1,
            "response": "Review active incidents and obtain Human Owner dual-key signoff",
            "escalation": "Immediate Owner Notification"
        },
        {
            "alert_id": "ALT_BUDGET_EXHAUSTED",
            "name": "Tenant Hard Budget Limit Reached",
            "severity": AlertSeverity.HIGH,
            "owner": "FINANCE_DIRECTOR",
            "runbook": "docs/runbooks/BUDGET_EXHAUSTION.md",
            "metric": "zonata_budget_exhaustions_total",
            "threshold": 1,
            "response": "Review expenditure breakdown and request budget top-up",
            "escalation": "Escalate to AI CEO"
        }
    ]

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def evaluate_active_alerts(self, metrics: Optional[PrometheusMetricsRegistry] = None) -> List[Dict[str, Any]]:
        """Evaluates metrics against alert rules and returns currently firing alerts."""
        m = metrics or sre_metrics
        firing = []

        for rule in self.DEFINED_ALERTS:
            metric_name = rule["metric"]
            val = m._counters.get(metric_name)
            if val is None:
                val = m._gauges.get(metric_name, 0.0)

            if val >= rule["threshold"]:
                firing.append({
                    "alert_id": rule["alert_id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "owner": rule["owner"],
                    "runbook": rule["runbook"],
                    "current_value": val,
                    "threshold": rule["threshold"],
                    "response": rule["response"],
                    "escalation": rule["escalation"],
                    "fired_at": time.time()
                })

        return firing
