"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 18 — Enterprise Metering & Billing Ledger
Immutable usage-event metering for SaaS billing, enterprise contracts, and departmental chargebacks.

Constitutional Invariant:
  BILLING_DERIVED_FROM_IMMUTABLE_USAGE_EVENTS_NOT_COUNTERS
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType

logger = logging.getLogger("zonata.usage.meter")

class UsageMetricType:
    AI_EMPLOYEE_ACTIVE_DAY = "AI_EMPLOYEE_ACTIVE_DAY"
    MODEL_INPUT_TOKENS = "MODEL_INPUT_TOKENS"
    MODEL_OUTPUT_TOKENS = "MODEL_OUTPUT_TOKENS"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    BROWSER_SESSION_MINUTES = "BROWSER_SESSION_MINUTES"
    SANDBOX_COMPUTE_SECONDS = "SANDBOX_COMPUTE_SECONDS"
    DATA_INGESTION_BYTES = "DATA_INGESTION_BYTES"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"

class UsageMeter:
    """
    Authoritative usage metering service recording immutable operational events.
    """
    UNIT_RATES_USD = {
        UsageMetricType.AI_EMPLOYEE_ACTIVE_DAY: 1.0,           # $1.00 per active employee/day
        UsageMetricType.MODEL_INPUT_TOKENS: 0.000003,          # $3.00 / 1M tokens
        UsageMetricType.MODEL_OUTPUT_TOKENS: 0.000015,         # $15.00 / 1M tokens
        UsageMetricType.TOOL_EXECUTION: 0.0005,                # $0.50 / 1k tools
        UsageMetricType.BROWSER_SESSION_MINUTES: 0.02,         # $0.02 / minute
        UsageMetricType.SANDBOX_COMPUTE_SECONDS: 0.0001,       # $0.006 / minute
        UsageMetricType.DATA_INGESTION_BYTES: 0.0000000001,    # $0.10 / GB
        UsageMetricType.KNOWLEDGE_QUERY: 0.001                 # $1.00 / 1k queries
    }

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_meter_events (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id Optional TEXT,
                metric_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_rate_usd REAL NOT NULL,
                total_cost_usd REAL NOT NULL,
                metadata JSON,
                timestamp REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usg_tenant ON usage_meter_events(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usg_metric ON usage_meter_events(metric_type);")

    def record_usage(
        self,
        tenant_id: str,
        company_id: str,
        metric_type: str,
        quantity: float,
        employee_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record an immutable usage event."""
        event_id = f"usg_{uuid.uuid4().hex[:12]}"
        now = time.time()
        rate = self.UNIT_RATES_USD.get(metric_type, 0.0)
        total_cost = quantity * rate

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO usage_meter_events (
                event_id, tenant_id, company_id, employee_id, metric_type,
                quantity, unit_rate_usd, total_cost_usd, metadata, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, tenant_id, company_id, employee_id, metric_type,
                quantity, rate, total_cost, json.dumps(metadata or {}), now
            ))

        return event_id

    def generate_tenant_invoice_summary(self, tenant_id: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """Aggregate immutable usage events into a billing summary."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("""
            SELECT metric_type, sum(quantity) as total_qty, sum(total_cost_usd) as total_amount
            FROM usage_meter_events
            WHERE tenant_id = ? AND timestamp >= ? AND timestamp <= ?
            GROUP BY metric_type
            """, (tenant_id, start_time, end_time))
            rows = cursor.fetchall()

            line_items = []
            grand_total = 0.0
            for r in rows:
                line_items.append({
                    "metric_type": r["metric_type"],
                    "quantity": r["total_qty"],
                    "amount_usd": round(r["total_amount"], 4)
                })
                grand_total += r["total_amount"]

            return {
                "tenant_id": tenant_id,
                "billing_period": {"start": start_time, "end": end_time},
                "line_items": line_items,
                "grand_total_usd": round(grand_total, 2),
                "generated_at": time.time()
            }

# Global singleton
usage_meter = UsageMeter()
