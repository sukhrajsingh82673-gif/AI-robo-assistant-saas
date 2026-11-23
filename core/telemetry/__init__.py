"""
ZONATA OpenTelemetry Distributed Tracing & Observability Package
===============================================================
"""

from core.telemetry.context import CorrelationContext
from core.telemetry.sanitizer import (
    TelemetrySanitizer,
    TelemetryLeakageError,
    ALLOWED_ATTRIBUTE_PREFIXES,
)
from core.telemetry.tracer import (
    ZonataSpan,
    ZonataTracer,
    SpanKind,
    StatusCode,
    SpanStatus,
    SpanEvent,
    get_tracer,
)
from core.telemetry.canary import (
    TelemetryCanaryScanner,
    TelemetryCanaryProbe,
    CanaryScanResult,
    CanaryScanFinding,
)
from core.telemetry.interceptor import (
    trace_span,
    instrument_llm_call,
    instrument_tool_call,
)

__all__ = [
    "CorrelationContext",
    "TelemetrySanitizer",
    "TelemetryLeakageError",
    "ALLOWED_ATTRIBUTE_PREFIXES",
    "ZonataSpan",
    "ZonataTracer",
    "SpanKind",
    "StatusCode",
    "SpanStatus",
    "SpanEvent",
    "get_tracer",
    "TelemetryCanaryScanner",
    "TelemetryCanaryProbe",
    "CanaryScanResult",
    "CanaryScanFinding",
    "trace_span",
    "instrument_llm_call",
    "instrument_tool_call",
]
