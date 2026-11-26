"""ZONATA Sovereign Core — Kaizen Metrics & Lean KPI Store.

Implements Stage 7:
- Continuous measurement of Lean KPIs: Cycle Time, First-Pass Yield (FPY), Cost per Unit, Error Rate.
- Tracks waste events (waiting, rework, over-processing, handoff, defects, unused talent).
- Persists to normalized database tables: af_kaizen_metrics and af_waste_events.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from core.db import db
from agent_factory.ports import EvidenceEvent
from agent_factory.adapters.zonata import ZonataEvidenceAdapter

logger = logging.getLogger("zonata.core.kaizen.metrics")


@dataclass
class WasteEvent:
    event_id: str
    tenant_id: str
    company_id: str
    pack_id: str
    instance_id: str
    step_id: str
    waste_type: str  # "waiting", "rework", "over_processing", "handoff", "defects", "unused_talent"
    severity: str  # "LOW", "MEDIUM", "HIGH"
    details: str
    estimated_cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ProcessRunMetric:
    metric_id: str
    tenant_id: str
    company_id: str
    pack_id: str
    instance_id: str
    cycle_time_seconds: float
    first_pass_yield: float  # 1.0 or 0.0
    cost_usd: float
    error_count: int
    csat: Optional[float]
    timestamp: float = field(default_factory=time.time)


class KaizenMetricsStore:
    """Stores and aggregates process run KPIs and waste events."""

    def __init__(self, db_conn_factory=None, evidence_port=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self.evidence = evidence_port or ZonataEvidenceAdapter()
        self._ensure_tables()

    def _ensure_tables(self):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS af_kaizen_metrics (
                    metric_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    pack_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    cycle_time_seconds REAL NOT NULL,
                    first_pass_yield REAL NOT NULL,
                    cost_usd REAL NOT NULL,
                    error_count INTEGER NOT NULL,
                    csat REAL,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_km_tenant_pack ON af_kaizen_metrics(tenant_id, pack_id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS af_waste_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    pack_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    waste_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    details TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_we_tenant_pack ON af_waste_events(tenant_id, pack_id)")
            conn.commit()

    def record_run(
        self,
        tenant_id: str,
        company_id: str,
        pack_id: str,
        instance_id: str,
        cycle_time_seconds: float,
        first_pass_yield: float,
        cost_usd: float,
        error_count: int = 0,
        csat: Optional[float] = None
    ) -> ProcessRunMetric:
        metric_id = f"km_{uuid.uuid4().hex[:12]}"
        now = time.time()
        metric = ProcessRunMetric(
            metric_id=metric_id,
            tenant_id=tenant_id,
            company_id=company_id,
            pack_id=pack_id,
            instance_id=instance_id,
            cycle_time_seconds=cycle_time_seconds,
            first_pass_yield=first_pass_yield,
            cost_usd=cost_usd,
            error_count=error_count,
            csat=csat,
            timestamp=now
        )

        with self.db_conn_factory() as conn:
            conn.execute(
                """
                INSERT INTO af_kaizen_metrics
                (metric_id, tenant_id, company_id, pack_id, instance_id, cycle_time_seconds, first_pass_yield, cost_usd, error_count, csat, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metric.metric_id, metric.tenant_id, metric.company_id, metric.pack_id,
                    metric.instance_id, metric.cycle_time_seconds, metric.first_pass_yield,
                    metric.cost_usd, metric.error_count, metric.csat, metric.timestamp
                )
            )
            conn.commit()

        return metric

    def record_waste(
        self,
        tenant_id: str,
        company_id: str,
        pack_id: str,
        instance_id: str,
        step_id: str,
        waste_type: str,
        severity: str,
        details: str,
        estimated_cost_usd: float = 0.0
    ) -> WasteEvent:
        event_id = f"wst_{uuid.uuid4().hex[:12]}"
        now = time.time()
        waste = WasteEvent(
            event_id=event_id,
            tenant_id=tenant_id,
            company_id=company_id,
            pack_id=pack_id,
            instance_id=instance_id,
            step_id=step_id,
            waste_type=waste_type,
            severity=severity,
            details=details,
            estimated_cost_usd=estimated_cost_usd,
            timestamp=now
        )

        with self.db_conn_factory() as conn:
            conn.execute(
                """
                INSERT INTO af_waste_events
                (event_id, tenant_id, company_id, pack_id, instance_id, step_id, waste_type, severity, details, estimated_cost_usd, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    waste.event_id, waste.tenant_id, waste.company_id, waste.pack_id,
                    waste.instance_id, waste.step_id, waste.waste_type, waste.severity,
                    waste.details, waste.estimated_cost_usd, waste.timestamp
                )
            )
            conn.commit()

        return waste

    def get_aggregate_kpis(self, tenant_id: str, pack_id: str) -> Dict[str, Any]:
        with self.db_conn_factory() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*), AVG(cycle_time_seconds), AVG(first_pass_yield), AVG(cost_usd), SUM(error_count), AVG(csat)
                FROM af_kaizen_metrics
                WHERE tenant_id = ? AND pack_id = ?
                """,
                (tenant_id, pack_id)
            )
            row = cur.fetchone()
            if not row or row[0] == 0:
                return {
                    "total_runs": 0,
                    "avg_cycle_time_seconds": 0.0,
                    "first_pass_yield": 1.0,
                    "avg_cost_usd": 0.0,
                    "total_errors": 0,
                    "avg_csat": 5.0
                }

            return {
                "total_runs": row[0],
                "avg_cycle_time_seconds": round(row[1] or 0.0, 2),
                "first_pass_yield": round(row[2] or 0.0, 4),
                "avg_cost_usd": round(row[3] or 0.0, 4),
                "total_errors": int(row[4] or 0),
                "avg_csat": round(row[5] or 5.0, 2)
            }
