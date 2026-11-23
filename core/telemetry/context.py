"""
ZONATA OpenTelemetry Correlation Context & W3C TraceContext Propagation
======================================================================
Implements standard W3C Trace Context (traceparent, tracestate) propagation
across distributed asynchronous boundaries (Temporal activities, LangGraph nodes,
Google ADK squads, and MCP tools).
"""

import os
import re
import uuid
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional

W3C_TRACEPARENT_PATTERN = re.compile(
    r"^00-([0-9a-fA-F]{32})-([0-9a-fA-F]{16})-([0-9a-fA-F]{2})$"
)


@dataclass
class CorrelationContext:
    """Universal correlation context carried across all execution layers."""
    tenant_id: str = "tnt_primary"
    company_id: str = "comp_primary"
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    flags: str = "01"  # Sampled by default
    tracestate: Optional[str] = None
    action_class: Optional[str] = None
    authority_profile: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex.lower()
        else:
            self.trace_id = self.trace_id.lower()

        if not self.span_id:
            self.span_id = uuid.uuid4().hex[:16].lower()
        else:
            self.span_id = self.span_id.lower()

    def to_w3c_traceparent(self) -> str:
        """Formats context as a W3C traceparent header string."""
        t_id = self.trace_id[:32].zfill(32)
        s_id = self.span_id[:16].zfill(16)
        flags = self.flags.zfill(2)
        return f"00-{t_id}-{s_id}-{flags}"

    @classmethod
    def from_w3c_traceparent(
        cls,
        traceparent: str,
        tracestate: Optional[str] = None,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        **kwargs
    ) -> "CorrelationContext":
        """Parses a W3C traceparent string into a new child CorrelationContext."""
        match = W3C_TRACEPARENT_PATTERN.match(traceparent.strip())
        if not match:
            # Fallback gracefully with new trace ID
            return cls(tenant_id=tenant_id, company_id=company_id, **kwargs)

        parent_trace_id = match.group(1).lower()
        parent_span_id = match.group(2).lower()
        flags = match.group(3).lower()

        # Generate a new child span ID while preserving the trace ID
        child_span_id = uuid.uuid4().hex[:16].lower()

        return cls(
            tenant_id=tenant_id,
            company_id=company_id,
            trace_id=parent_trace_id,
            span_id=child_span_id,
            parent_span_id=parent_span_id,
            flags=flags,
            tracestate=tracestate,
            **kwargs
        )

    def inject_carrier(self, carrier: Dict[str, Any]) -> Dict[str, Any]:
        """Injects W3C headers and zonata correlation fields into carrier dict."""
        carrier["traceparent"] = self.to_w3c_traceparent()
        if self.tracestate:
            carrier["tracestate"] = self.tracestate
        carrier["x-zonata-tenant-id"] = self.tenant_id
        carrier["x-zonata-company-id"] = self.company_id
        if self.run_id:
            carrier["x-zonata-run-id"] = self.run_id
        if self.step_id:
            carrier["x-zonata-step-id"] = self.step_id
        return carrier

    @classmethod
    def extract_carrier(cls, carrier: Dict[str, Any]) -> "CorrelationContext":
        """Extracts CorrelationContext from incoming carrier dict (e.g. headers)."""
        # Case-insensitive header lookup
        normalized = {str(k).lower(): v for k, v in carrier.items()}
        tp = normalized.get("traceparent")
        ts = normalized.get("tracestate")
        tenant_id = normalized.get("x-zonata-tenant-id", "tnt_primary")
        company_id = normalized.get("x-zonata-company-id", "comp_primary")
        run_id = normalized.get("x-zonata-run-id")
        step_id = normalized.get("x-zonata-step-id")

        if tp:
            return cls.from_w3c_traceparent(
                traceparent=tp,
                tracestate=ts,
                tenant_id=tenant_id,
                company_id=company_id,
                run_id=run_id,
                step_id=step_id
            )

        return cls(
            tenant_id=tenant_id,
            company_id=company_id,
            run_id=run_id,
            step_id=step_id,
            tracestate=ts
        )

    def create_child_context(self, **overrides) -> "CorrelationContext":
        """Creates a direct child context within the same trace."""
        new_span_id = uuid.uuid4().hex[:16].lower()
        ctx = CorrelationContext(
            tenant_id=overrides.get("tenant_id", self.tenant_id),
            company_id=overrides.get("company_id", self.company_id),
            user_id=overrides.get("user_id", self.user_id),
            run_id=overrides.get("run_id", self.run_id),
            step_id=overrides.get("step_id", self.step_id),
            trace_id=self.trace_id,
            span_id=new_span_id,
            parent_span_id=self.span_id,
            flags=self.flags,
            tracestate=self.tracestate,
            action_class=overrides.get("action_class", self.action_class),
            authority_profile=overrides.get("authority_profile", self.authority_profile),
            metadata={**self.metadata, **overrides.get("metadata", {})}
        )
        return ctx
