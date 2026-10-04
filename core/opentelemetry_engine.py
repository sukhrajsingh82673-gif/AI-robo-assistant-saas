"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
OpenTelemetry Universal Telemetry & Distributed Tracing Engine
=============================================================
Provides vendor-neutral OpenTelemetry-compliant tracing, metrics, and structured logging.
Enforces the universal correlation context across all layers:
  Tenant -> Company -> Mission -> Execution -> Task -> Agent -> Model -> Tool -> Evidence

Constitutional Invariants:
1. Every stage of execution must carry:
   trace_id, span_id, tenant_id, company_id, mission_id, execution_id, task_id, agent_id, tool_id, evidence_id.
2. OpenTelemetry is an observability layer, NOT an audit or governance authority.
3. ZONATA EvidenceLedger remains the sole cryptographic authority for business truth.
4. Telemetry must NEVER leak plaintext raw credentials or sensitive unscrubbed tokens.
"""

import os
import time
import json
import uuid
import random
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("zonata.telemetry.otel")

class SpanKind(str, Enum):
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"

class StatusCode(str, Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"

@dataclass
class SpanStatus:
    status_code: StatusCode = StatusCode.UNSET
    description: Optional[str] = None

@dataclass
class SpanEvent:
    name: str
    timestamp_ns: int
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CorrelationContext:
    tenant_id: str = "tnt_primary"
    company_id: str = "comp_primary"
    mission_id: Optional[str] = None
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None
    evidence_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_w3c_traceparent(self) -> str:
        """Emits W3C standard traceparent: 00-{trace_id}-{span_id}-{flags}."""
        t_id = (self.trace_id or uuid.uuid4().hex).lower()[:32].zfill(32)
        s_id = (self.span_id or uuid.uuid4().hex[:16]).lower()[:16].zfill(16)
        flags = "01"  # Sampled
        return f"00-{t_id}-{s_id}-{flags}"

    @classmethod
    def from_w3c_traceparent(cls, traceparent: str, **kwargs) -> "CorrelationContext":
        """Parses W3C traceparent header."""
        parts = traceparent.split("-")
        trace_id = None
        span_id = None
        if len(parts) >= 4 and parts[0] == "00":
            trace_id = parts[1]
            span_id = parts[2]
        return cls(trace_id=trace_id, parent_span_id=span_id, **kwargs)

class OTelSpan:
    """Represents a distributed tracing span in the OpenTelemetry specification."""

    def __init__(
        self,
        name: str,
        context: CorrelationContext,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.context = context
        self.kind = kind
        self.parent_span_id = parent_span_id or context.parent_span_id
        self.span_id = uuid.uuid4().hex[:16]
        self.context.span_id = self.span_id
        if not self.context.trace_id:
            self.context.trace_id = uuid.uuid4().hex
        self.trace_id = self.context.trace_id

        self.start_time_ns = time.time_ns()
        self.end_time_ns: Optional[int] = None
        self.attributes: Dict[str, Any] = attributes or {}
        self.events: List[SpanEvent] = []
        self.status = SpanStatus()
        self._ended = False

        # Populate context attributes automatically
        self.set_attribute("zonata.tenant_id", context.tenant_id)
        self.set_attribute("zonata.company_id", context.company_id)
        if context.mission_id:
            self.set_attribute("zonata.mission_id", context.mission_id)
        if context.execution_id:
            self.set_attribute("zonata.execution_id", context.execution_id)
        if context.task_id:
            self.set_attribute("zonata.task_id", context.task_id)
        if context.agent_id:
            self.set_attribute("zonata.agent_id", context.agent_id)
        if context.tool_id:
            self.set_attribute("zonata.tool_id", context.tool_id)
        if context.evidence_id:
            self.set_attribute("zonata.evidence_id", context.evidence_id)

    def set_attribute(self, key: str, value: Any):
        if self._ended:
            return
        # Sanitize against credential leaks
        val_str = str(value)
        if any(w in key.lower() for w in ["secret", "password", "token", "key", "auth"]):
            if len(val_str) > 8:
                value = f"{val_str[:4]}...[REDACTED]"
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        if self._ended:
            return
        event = SpanEvent(name=name, timestamp_ns=time.time_ns(), attributes=attributes or {})
        self.events.append(event)

    def record_exception(self, exception: Exception):
        self.add_event("exception", {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception)
        })
        self.set_status(StatusCode.ERROR, str(exception))

    def set_status(self, code: StatusCode, description: Optional[str] = None):
        if not self._ended:
            self.status = SpanStatus(status_code=code, description=description)

    def end(self, end_time_ns: Optional[int] = None):
        if self._ended:
            return
        self.end_time_ns = end_time_ns or time.time_ns()
        self._ended = True
        if self.status.status_code == StatusCode.UNSET:
            self.status.status_code = StatusCode.OK

    @property
    def duration_ms(self) -> float:
        end = self.end_time_ns or time.time_ns()
        return (end - self.start_time_ns) / 1_000_000.0

    def to_dict(self) -> Dict[str, Any]:
        """Returns dictionary representation of span."""
        return self.to_otlp_json()

    def to_otlp_json(self) -> Dict[str, Any]:
        """Produces standard OTLP-compliant JSON payload."""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "startTimeUnixNano": self.start_time_ns,
            "endTimeUnixNano": self.end_time_ns or time.time_ns(),
            "durationMs": self.duration_ms,
            "attributes": [{"key": k, "value": {"stringValue": str(v)}} for k, v in self.attributes.items()],
            "events": [
                {
                    "timeUnixNano": e.timestamp_ns,
                    "name": e.name,
                    "attributes": [{"key": k, "value": {"stringValue": str(v)}} for k, v in e.attributes.items()]
                }
                for e in self.events
            ],
            "status": {
                "code": self.status.status_code.value,
                "message": self.status.description or ""
            }
        }

class OTelTracer:
    """Manages tracer instances and span creation."""

    def __init__(self, service_name: str = "zonata-company-os"):
        self.service_name = service_name
        self._completed_spans: List[OTelSpan] = []
        self._lock = threading.Lock()

    def start_span(
        self,
        name: str,
        context: Optional[CorrelationContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[OTelSpan] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> OTelSpan:
        ctx = context or CorrelationContext()
        parent_id = parent.span_id if parent else ctx.parent_span_id
        if parent:
            ctx.trace_id = parent.trace_id
            ctx.parent_span_id = parent.span_id

        span = OTelSpan(name=name, context=ctx, kind=kind, parent_span_id=parent_id, attributes=attributes)
        span.set_attribute("service.name", self.service_name)
        return span

    def record_span(self, span: OTelSpan):
        with self._lock:
            self._completed_spans.append(span)
            if len(self._completed_spans) > 2000:
                self._completed_spans.pop(0)

    def get_spans(self, trace_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            res = []
            for s in self._completed_spans:
                if trace_id and s.trace_id != trace_id:
                    continue
                if tenant_id and s.context.tenant_id != tenant_id:
                    continue
                res.append(s.to_otlp_json())
            return res

class OTelMetricsEngine:
    """Manages OpenTelemetry metrics: Counters, Histograms, and Gauges."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

    def add_counter(self, name: str, value: float = 1.0, attributes: Optional[Dict[str, str]] = None):
        key = self._format_key(name, attributes)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, attributes: Optional[Dict[str, str]] = None):
        key = self._format_key(name, attributes)
        with self._lock:
            self._gauges[key] = value

    def record_histogram(self, name: str, value: float, attributes: Optional[Dict[str, str]] = None):
        key = self._format_key(name, attributes)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            if len(self._histograms[key]) > 1000:
                self._histograms[key].pop(0)

    def _format_key(self, name: str, attributes: Optional[Dict[str, str]]) -> str:
        if not attributes:
            return name
        attrs_str = ",".join(f"{k}={v}" for k, v in sorted(attributes.items()))
        return f"{name}{{{attrs_str}}}"

    def export_prometheus(self) -> str:
        """Exposes metrics in standard Prometheus exposition format."""
        lines = []
        with self._lock:
            for k, v in self._counters.items():
                lines.append(f"{k} {v}")
            for k, v in self._gauges.items():
                lines.append(f"{k} {v}")
            for k, vals in self._histograms.items():
                if vals:
                    count = len(vals)
                    sum_val = sum(vals)
                    avg = sum_val / count
                    base = k.split("{")[0]
                    lines.append(f"{base}_count {count}")
                    lines.append(f"{base}_sum {sum_val}")
                    lines.append(f"{base}_avg {avg:.4f}")
        return "\n".join(lines) + "\n"

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Returns JSON-serializable snapshot of recorded metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: {
                        "count": len(vals),
                        "sum": round(sum(vals), 4),
                        "avg": round(sum(vals) / len(vals), 4) if vals else 0.0
                    }
                    for k, vals in self._histograms.items()
                }
            }

class OpenTelemetryEngine:

    """
    Singleton platform coordinator for ZONATA OpenTelemetry telemetry.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "OpenTelemetryEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.tracer = OTelTracer()
        self.metrics = OTelMetricsEngine()

    def start_trace(
        self,
        span_name: str,
        tenant_id: str,
        company_id: str,
        mission_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        evidence_id: Optional[str] = None
    ) -> OTelSpan:
        ctx = CorrelationContext(
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            execution_id=execution_id,
            task_id=task_id,
            agent_id=agent_id,
            tool_id=tool_id,
            evidence_id=evidence_id
        )
        return self.tracer.start_span(span_name, context=ctx)

    def finish_span(self, span: OTelSpan):
        span.end()
        self.tracer.record_span(span)
        # Record standard telemetry metrics
        self.metrics.add_counter("zonata_spans_total", 1.0, {"name": span.name, "status": span.status.status_code.value})
        self.metrics.record_histogram("zonata_span_duration_ms", span.duration_ms, {"name": span.name})

# Global singleton instance
opentelemetry_engine = OpenTelemetryEngine.get_instance()
opentelemetry_tracer = opentelemetry_engine.tracer

