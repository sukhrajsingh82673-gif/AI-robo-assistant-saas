"""
ZONATA Telemetry Secret Canary Probe & Scanner
=============================================
Enforces Standing Rule 24 and Standing Rule 36:
- Secret canary injection tests verify zero plaintext leakage across all telemetry.
- Scans traces, spans, attributes, events, and serialized exports for high-entropy secrets and canary markers.
"""

import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.telemetry.context import CorrelationContext
from core.telemetry.tracer import ZonataTracer, SpanKind, StatusCode
from core.telemetry.sanitizer import TelemetrySanitizer, TelemetryLeakageError, SENSITIVE_VALUE_PATTERNS

logger = logging.getLogger("zonata.telemetry.canary")


@dataclass
class CanaryScanFinding:
    path: str
    leaked_pattern: str
    sample: str


@dataclass
class CanaryScanResult:
    scanned_spans: int
    total_attributes_scanned: int
    leaks_found: int
    findings: List[CanaryScanFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.leaks_found == 0


class TelemetryCanaryScanner:
    """Scans serialized spans or arbitrary telemetry dictionaries for secret leakage."""

    def __init__(self, canary_prefix: str = "ZONATA_CANARY_"):
        self.canary_prefix = canary_prefix

    def scan_spans(self, spans: List[Dict[str, Any]]) -> CanaryScanResult:
        """Deeply scans a list of serialized OTLP spans for secret leaks."""
        result = CanaryScanResult(scanned_spans=len(spans), total_attributes_scanned=0, leaks_found=0)

        for span_idx, span in enumerate(spans):
            self._scan_object(span, f"spans[{span_idx}]", result)

        return result

    def _scan_object(self, obj: Any, current_path: str, result: CanaryScanResult):
        if isinstance(obj, dict):
            for k, v in obj.items():
                result.total_attributes_scanned += 1
                self._scan_object(v, f"{current_path}.{k}", result)
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                self._scan_object(item, f"{current_path}[{i}]", result)
        elif isinstance(obj, str):
            # Check for canary tokens or credential patterns
            for pattern in SENSITIVE_VALUE_PATTERNS:
                matches = pattern.findall(obj)
                for match in matches:
                    result.leaks_found += 1
                    result.findings.append(
                        CanaryScanFinding(
                            path=current_path,
                            leaked_pattern=pattern.pattern,
                            sample=str(match)[:16] + "...",
                        )
                    )


class TelemetryCanaryProbe:
    """Active verification probe running end-to-end secret canary drills."""

    def __init__(self, tracer: Optional[ZonataTracer] = None):
        self.tracer = tracer or ZonataTracer(service_name="zonata-canary-probe")
        self.scanner = TelemetryCanaryScanner()

    def run_drill(self) -> CanaryScanResult:
        """
        Executes a comprehensive canary drill:
        1. Injects known canary secrets into headers, attributes, events, and GenAI params.
        2. Records execution spans.
        3. Scans all emitted spans for leakage.
        """
        canary_key = f"ZONATA_CANARY_KEY_{uuid.uuid4().hex}"
        canary_secret = f"ZONATA_CANARY_SECRET_{uuid.uuid4().hex}"
        canary_bearer = f"Bearer ZONATA_CANARY_TOKEN_{uuid.uuid4().hex}"
        canary_apikey = f"sk_live_{uuid.uuid4().hex[:24]}"

        # Context with canaries
        ctx = CorrelationContext(
            tenant_id="tnt_canary_test",
            company_id="comp_canary_test",
            run_id="run_canary_001",
            step_id="step_canary_001",
            metadata={"secret_canary": canary_secret}
        )

        # 1. Root span with injected sensitive attributes
        root_span = self.tracer.start_span("canary_root_operation", context=ctx)
        root_span.set_attribute("password", canary_secret)
        root_span.set_attribute("auth_token", canary_bearer)
        root_span.set_attribute("config.api_key", canary_apikey)
        root_span.set_attribute("safe_id", "item_12345")

        root_span.add_event("auth_attempt", {
            "token": canary_bearer,
            "canary_val": canary_key
        })

        # 2. Child GenAI span with prompt containing canary
        child_span = self.tracer.start_span("canary_llm_inference", parent=root_span)
        child_span.set_genai_attributes(
            system="anthropic",
            model="claude-3-5-sonnet",
            prompt_tokens=150,
            completion_tokens=42,
            prompt_body=f"Translate this secret: {canary_secret}",
            response_body=f"Processed secret: {canary_key}"
        )

        child_span.end()
        root_span.end()

        # Record spans
        self.tracer.record_span(root_span)
        self.tracer.record_span(child_span)

        # Retrieve and scan spans
        exported = self.tracer.get_spans(trace_id=ctx.trace_id)
        scan_result = self.scanner.scan_spans(exported)

        if not scan_result.passed:
            logger.error(
                "CRITICAL: Telemetry canary drill failed! %d leaks detected: %s",
                scan_result.leaks_found,
                scan_result.findings
            )
        else:
            logger.info("Telemetry canary drill passed: 0 leaks across %d spans.", scan_result.scanned_spans)

        return scan_result
