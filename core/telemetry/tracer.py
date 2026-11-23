"""
ZONATA OpenTelemetry GenAI-Compliant Distributed Tracer
======================================================
Implements ADR 0015:
- Emits stable zonata.* namespace attributes on all spans.
- Emits OpenTelemetry GenAI semantic conventions under OTEL_GENAI_CONVENTIONS_ENABLED=1.
- Sanitizes all attributes against secret leaks and enforces tenant prompt capture policies.
- Thread-safe span recording and W3C traceparent context tracking.
"""

import os
import time
import uuid
import logging
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from core.telemetry.context import CorrelationContext
from core.telemetry.sanitizer import TelemetrySanitizer, TelemetryLeakageError

logger = logging.getLogger("zonata.telemetry.tracer")


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


class ZonataSpan:
    """Represents an active or completed distributed trace span."""

    def __init__(
        self,
        name: str,
        context: CorrelationContext,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        sanitizer: Optional[TelemetrySanitizer] = None,
        tenant_allow_prompt_capture: bool = False,
        genai_conventions_enabled: bool = False,
        strict_mode: bool = False,
    ):
        self.name = name
        self.context = context
        self.kind = kind
        self.parent_span_id = parent_span_id or context.parent_span_id
        self.span_id = context.span_id
        self.trace_id = context.trace_id
        self.sanitizer = sanitizer or TelemetrySanitizer(default_strict=strict_mode)
        self.tenant_allow_prompt_capture = tenant_allow_prompt_capture
        self.genai_conventions_enabled = genai_conventions_enabled
        self.strict_mode = strict_mode

        self.start_time_ns = time.time_ns()
        self.end_time_ns: Optional[int] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[SpanEvent] = []
        self.status = SpanStatus()
        self._ended = False

        # Populate stable zonata.* namespace attributes
        self._set_raw_attribute("zonata.tenant_id", context.tenant_id)
        self._set_raw_attribute("zonata.company_id", context.company_id)
        if context.user_id:
            self._set_raw_attribute("zonata.user_id", context.user_id)
        if context.run_id:
            self._set_raw_attribute("zonata.run_id", context.run_id)
        if context.step_id:
            self._set_raw_attribute("zonata.step_id", context.step_id)
        if context.action_class:
            self._set_raw_attribute("zonata.action_class", context.action_class)
        if context.authority_profile:
            self._set_raw_attribute("zonata.authority_profile", context.authority_profile)

        # Merge initial attributes
        if attributes:
            for k, v in attributes.items():
                self.set_attribute(k, v)

    def _set_raw_attribute(self, key: str, value: Any):
        clean_v = self.sanitizer.sanitize_attribute(
            key,
            value,
            strict=self.strict_mode,
            tenant_allow_prompt_capture=self.tenant_allow_prompt_capture
        )
        if clean_v is not None:
            self.attributes[key] = clean_v

    def set_attribute(self, key: str, value: Any):
        """Sets a sanitized attribute on the span."""
        if self._ended:
            return
        self._set_raw_attribute(key, value)

    def set_genai_attributes(
        self,
        system: Optional[str] = None,
        model: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_micros: Optional[int] = None,
        finish_reasons: Optional[List[str]] = None,
        prompt_body: Optional[str] = None,
        response_body: Optional[str] = None,
    ):
        """
        Emits GenAI telemetry attributes.
        Always records zonata.* tokens and cost; conditionally emits gen_ai.*
        semantic conventions if enabled.
        """
        # Always record stable zonata.* metrics
        if prompt_tokens is not None:
            self.set_attribute("zonata.tokens_input", prompt_tokens)
        if completion_tokens is not None:
            self.set_attribute("zonata.tokens_output", completion_tokens)
        if cost_micros is not None:
            self.set_attribute("zonata.cost_micros", cost_micros)

        # Prompt & response body gated by tenant policy
        if prompt_body is not None:
            self.set_attribute("zonata.prompt_body", prompt_body)
        if response_body is not None:
            self.set_attribute("zonata.response_body", response_body)

        # Emit standard GenAI conventions if enabled
        if self.genai_conventions_enabled:
            if system:
                self.set_attribute("gen_ai.system", system)
            if model:
                self.set_attribute("gen_ai.request.model", model)
                self.set_attribute("gen_ai.response.model", model)
            if prompt_tokens is not None:
                self.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
            if completion_tokens is not None:
                self.set_attribute("gen_ai.usage.output_tokens", completion_tokens)
            if total_tokens is not None:
                self.set_attribute("gen_ai.usage.total_tokens", total_tokens)
            elif prompt_tokens is not None and completion_tokens is not None:
                self.set_attribute("gen_ai.usage.total_tokens", prompt_tokens + completion_tokens)
            if finish_reasons:
                self.set_attribute("gen_ai.response.finish_reasons", finish_reasons)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Adds a sanitized event to the span."""
        if self._ended:
            return
        clean_attrs = self.sanitizer.sanitize_dict(
            attributes or {},
            strict=self.strict_mode,
            tenant_allow_prompt_capture=self.tenant_allow_prompt_capture
        )
        self.events.append(SpanEvent(name=name, timestamp_ns=time.time_ns(), attributes=clean_attrs))

    def record_exception(self, exception: Exception):
        """Records an exception event and marks span status as ERROR."""
        self.add_event("exception", {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception)
        })
        self.set_status(StatusCode.ERROR, str(exception))

    def set_status(self, code: StatusCode, description: Optional[str] = None):
        """Sets span outcome status."""
        if not self._ended:
            self.status = SpanStatus(status_code=code, description=description)

    def end(self, end_time_ns: Optional[int] = None):
        """Closes the span and calculates final duration."""
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
            "attributes": self.attributes,
            "events": [
                {
                    "timeUnixNano": e.timestamp_ns,
                    "name": e.name,
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
            "status": {
                "code": self.status.status_code.value,
                "message": self.status.description or "",
            },
        }


class ZonataTracer:
    """Central OpenTelemetry-compliant tracer for ZONATA services."""

    def __init__(
        self,
        service_name: str = "zonata-company-os",
        genai_conventions_enabled: Optional[bool] = None,
        strict_mode: bool = False,
    ):
        self.service_name = service_name
        self._genai_enabled = (
            genai_conventions_enabled
            if genai_conventions_enabled is not None
            else os.environ.get("OTEL_GENAI_CONVENTIONS_ENABLED", "0").lower() in ("1", "true", "yes")
        )
        self.strict_mode = strict_mode
        self.sanitizer = TelemetrySanitizer(default_strict=strict_mode)
        self._completed_spans: List[ZonataSpan] = []
        self._lock = threading.Lock()

    @property
    def genai_conventions_enabled(self) -> bool:
        return self._genai_enabled

    def set_genai_conventions_enabled(self, enabled: bool):
        self._genai_enabled = enabled

    def start_span(
        self,
        name: str,
        context: Optional[CorrelationContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[ZonataSpan] = None,
        attributes: Optional[Dict[str, Any]] = None,
        tenant_allow_prompt_capture: bool = False,
    ) -> ZonataSpan:
        """Starts a new span linked to the current or parent context."""
        if parent:
            ctx = parent.context.create_child_context()
            parent_id = parent.span_id
        elif context:
            ctx = context
            parent_id = context.parent_span_id
        else:
            ctx = CorrelationContext()
            parent_id = None

        span = ZonataSpan(
            name=name,
            context=ctx,
            kind=kind,
            parent_span_id=parent_id,
            attributes=attributes,
            sanitizer=self.sanitizer,
            tenant_allow_prompt_capture=tenant_allow_prompt_capture,
            genai_conventions_enabled=self._genai_enabled,
            strict_mode=self.strict_mode,
        )
        span.set_attribute("service.name", self.service_name)
        return span

    def record_span(self, span: ZonataSpan):
        """Records a completed span in the local collector."""
        with self._lock:
            self._completed_spans.append(span)
            if len(self._completed_spans) > 5000:
                self._completed_spans.pop(0)

    def get_spans(
        self,
        trace_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns serialized OTLP JSON dictionaries for recorded spans."""
        with self._lock:
            results = []
            for s in self._completed_spans:
                if trace_id and s.trace_id != trace_id:
                    continue
                if tenant_id and s.context.tenant_id != tenant_id:
                    continue
                results.append(s.to_otlp_json())
            return results

    def clear(self):
        """Clears all recorded spans."""
        with self._lock:
            self._completed_spans.clear()


# Default singleton tracer instance
_GLOBAL_TRACER: Optional[ZonataTracer] = None
_GLOBAL_LOCK = threading.Lock()


def get_tracer(service_name: str = "zonata-company-os") -> ZonataTracer:
    """Returns singleton tracer instance."""
    global _GLOBAL_TRACER
    with _GLOBAL_LOCK:
        if _GLOBAL_TRACER is None:
            _GLOBAL_TRACER = ZonataTracer(service_name=service_name)
        return _GLOBAL_TRACER
