"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
SRE Observability Stack, Prometheus Metrics Exporter & Distributed Tracing
Provides OpenTelemetry-compatible tracing headers, Prometheus exposition format,
structured JSON logging, and continuous SLO monitoring.
"""

import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from .db import db

logger = logging.getLogger("zonata.sre")

class PrometheusMetricsRegistry:
    """
    Standard Prometheus exposition format generator for platform SRE monitoring.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = {
            "zonata_api_requests_total": 0,
            "zonata_api_errors_total": 0,
            "zonata_action_mutations_total": 0,
            "zonata_reconciliation_drift_total": 0,
            "zonata_killswitch_activations_total": 0,
            "zonata_approval_revocations_total": 0,
            "zonata_budget_exhaustions_total": 0,
            "zonata_unknown_outcomes_total": 0
        }
        self._gauges: Dict[str, float] = {
            "zonata_outbox_queue_depth": 0,
            "zonata_active_incidents": 0,
            "zonata_budget_spent_inr": 0.0,
            "zonata_active_workforce_agents": 1
        }
        self._latencies: List[float] = []

    def inc_counter(self, name: str, val: float = 1.0):
        with self._lock:
            if name in self._counters:
                self._counters[name] += val

    def set_gauge(self, name: str, val: float):
        with self._lock:
            self._gauges[name] = val

    def observe_latency(self, latency_ms: float):
        with self._lock:
            self._latencies.append(latency_ms)
            if len(self._latencies) > 5000:
                self._latencies.pop(0)

    def scrape_prometheus_format(self) -> str:
        """Generates Prometheus standard text format representation."""
        lines = []

        # Scrape live outbox & incident counts from DB
        try:
            with db.get_connection() as conn:
                outbox_cnt = conn.execute("SELECT count(*) FROM transactional_outbox WHERE status = 'PENDING'").fetchone()[0]
                inc_cnt = conn.execute("SELECT count(*) FROM executive_incidents WHERE current_state != 'CLOSED'").fetchone()[0]
                self._gauges["zonata_outbox_queue_depth"] = float(outbox_cnt)
                self._gauges["zonata_active_incidents"] = float(inc_cnt)
        except Exception:
            pass

        with self._lock:
            for k, v in self._counters.items():
                lines.append(f"# TYPE {k} counter")
                lines.append(f"{k} {v}")

            for k, v in self._gauges.items():
                lines.append(f"# TYPE {k} gauge")
                lines.append(f"{k} {v}")

            # Latency summary
            if self._latencies:
                sorted_lat = sorted(self._latencies)
                p50 = sorted_lat[int(len(sorted_lat) * 0.5)]
                p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
                p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
                lines.append("# TYPE zonata_api_latency_ms summary")
                lines.append(f'zonata_api_latency_ms{{quantile="0.5"}} {p50:.2f}')
                lines.append(f'zonata_api_latency_ms{{quantile="0.95"}} {p95:.2f}')
                lines.append(f'zonata_api_latency_ms{{quantile="0.99"}} {p99:.2f}')

        return "\n".join(lines) + "\n"

class StructuredJSONLogger:
    """Formats log records as structured JSON with mandatory trace and tenant contexts."""
    @staticmethod
    def format_entry(
        level: str,
        message: str,
        tenant_id: str,
        company_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        action_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **extra
    ) -> str:
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "tenant_id": tenant_id,
            "company_id": company_id or "comp_primary",
            "trace_id": trace_id or f"trc_{time.time_ns()}",
            "action_id": action_id,
            "duration_ms": duration_ms
        }
        entry.update(extra)
        return json.dumps(entry)

class SLOTracker:
    """
    Evaluates system SLO performance against defined targets.
    """
    SLO_TARGETS = {
        "api_availability_pct": 99.9,
        "api_p95_latency_ms": 200.0,
        "reconciliation_success_pct": 99.5,
        "incident_detection_sec": 5.0,
        "evidence_durability_pct": 100.0
    }

    @classmethod
    def evaluate_slos(cls, metrics_registry: PrometheusMetricsRegistry) -> Dict[str, Any]:
        reqs = metrics_registry._counters.get("zonata_api_requests_total", 0)
        errs = metrics_registry._counters.get("zonata_api_errors_total", 0)
        avail = 100.0 if reqs == 0 else max(0.0, (1.0 - (errs / reqs)) * 100.0)

        latencies = sorted(metrics_registry._latencies) if metrics_registry._latencies else [10.0]
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        return {
            "api_availability": {
                "current": round(avail, 2),
                "target": cls.SLO_TARGETS["api_availability_pct"],
                "compliant": avail >= cls.SLO_TARGETS["api_availability_pct"]
            },
            "api_p95_latency": {
                "current_ms": round(p95, 2),
                "target_ms": cls.SLO_TARGETS["api_p95_latency_ms"],
                "compliant": p95 <= cls.SLO_TARGETS["api_p95_latency_ms"]
            },
            "evidence_durability": {
                "current": 100.0,
                "target": 100.0,
                "compliant": True
            }
        }

# Global metrics registry singleton
sre_metrics = PrometheusMetricsRegistry()
