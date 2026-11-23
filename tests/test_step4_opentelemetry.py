"""
Step 4H Acceptance & Contract Test Suite: OpenTelemetry GenAI Instrumentation & Canary
=====================================================================================
Validates:
1. W3C traceparent formatting and context propagation across carrier boundaries.
2. Stable zonata.* namespace attributes and dual-mode GenAI semantic conventions.
3. Standing Rule 24 secret redaction and canary zero-leakage guarantee.
4. Standing Rule 36 payload body gating per tenant privacy policy.
5. Runtime instrumentation interceptors for LLMGateway and ActionGateway.
6. Standing Rule 40 / ADR 0016 Legal/AGPL isolation check (zero in-process AGPL imports).
7. Mutation check: unredacted credentials in strict mode fail closed with TelemetryLeakageError.
"""

import os
import ast
import json
import pytest
from unittest import TestCase
from dataclasses import dataclass

from core.telemetry.context import CorrelationContext
from core.telemetry.sanitizer import TelemetrySanitizer, TelemetryLeakageError
from core.telemetry.tracer import ZonataTracer, SpanKind, StatusCode
from core.telemetry.canary import TelemetryCanaryProbe, TelemetryCanaryScanner
from core.telemetry.interceptor import trace_span, instrument_llm_call, instrument_tool_call


class TestStep4OpenTelemetry(TestCase):
    """Sub-Step 4H Test Suite."""

    def setUp(self):
        self.tracer = ZonataTracer(service_name="test-telemetry-service")
        self.tracer.clear()

    def test_01_w3c_traceparent_propagation(self):
        """W3C traceparent format (00-hex32-hex16-flags) and carrier inject/extract."""
        ctx = CorrelationContext(
            tenant_id="tnt_acme",
            company_id="comp_finance",
            run_id="run_101",
            step_id="step_01"
        )

        traceparent = ctx.to_w3c_traceparent()
        parts = traceparent.split("-")
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "00")
        self.assertEqual(len(parts[1]), 32)
        self.assertEqual(len(parts[2]), 16)
        self.assertEqual(parts[3], "01")

        # Inject into carrier
        carrier = {}
        ctx.inject_carrier(carrier)
        self.assertIn("traceparent", carrier)
        self.assertEqual(carrier["x-zonata-tenant-id"], "tnt_acme")
        self.assertEqual(carrier["x-zonata-company-id"], "comp_finance")
        self.assertEqual(carrier["x-zonata-run-id"], "run_101")

        # Extract from carrier
        extracted = CorrelationContext.extract_carrier(carrier)
        self.assertEqual(extracted.tenant_id, "tnt_acme")
        self.assertEqual(extracted.company_id, "comp_finance")
        self.assertEqual(extracted.trace_id, ctx.trace_id)
        self.assertEqual(extracted.parent_span_id, ctx.span_id)
        self.assertNotEqual(extracted.span_id, ctx.span_id)  # Child gets new span_id

    def test_02_span_creation_and_hierarchical_linking(self):
        """Hierarchical parent-child span linking with stable zonata.* attributes."""
        root = self.tracer.start_span(
            "agent_root_turn",
            context=CorrelationContext(
                tenant_id="tnt_beta",
                company_id="comp_ops",
                run_id="run_999",
                action_class="COORDINATION"
            )
        )
        self.assertEqual(root.attributes["zonata.tenant_id"], "tnt_beta")
        self.assertEqual(root.attributes["zonata.company_id"], "comp_ops")
        self.assertEqual(root.attributes["zonata.run_id"], "run_999")
        self.assertEqual(root.attributes["zonata.action_class"], "COORDINATION")

        # Create child span
        child = self.tracer.start_span("agent_planner_node", parent=root)
        self.assertEqual(child.trace_id, root.trace_id)
        self.assertEqual(child.parent_span_id, root.span_id)
        self.assertEqual(child.attributes["zonata.tenant_id"], "tnt_beta")

        child.end()
        root.end()

        self.tracer.record_span(root)
        self.tracer.record_span(child)

        spans = self.tracer.get_spans(trace_id=root.trace_id)
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0]["status"]["code"], "OK")
        self.assertGreater(spans[0]["durationMs"], 0)

    def test_03_genai_semantic_conventions_flag(self):
        """Dual-mode attribute emission: stable zonata.* and OTEL_GENAI_CONVENTIONS_ENABLED."""
        # 1. Disabled (default)
        self.tracer.set_genai_conventions_enabled(False)
        span_off = self.tracer.start_span("model_call_standard")
        span_off.set_genai_attributes(
            system="anthropic",
            model="claude-3-5-sonnet",
            prompt_tokens=100,
            completion_tokens=25,
            cost_micros=1500
        )
        span_off.end()

        # Stable zonata.* attributes must be present
        self.assertEqual(span_off.attributes["zonata.tokens_input"], 100)
        self.assertEqual(span_off.attributes["zonata.tokens_output"], 25)
        self.assertEqual(span_off.attributes["zonata.cost_micros"], 1500)
        # gen_ai.* should NOT be present when flag is disabled
        self.assertNotIn("gen_ai.system", span_off.attributes)
        self.assertNotIn("gen_ai.request.model", span_off.attributes)
        self.assertNotIn("gen_ai.usage.input_tokens", span_off.attributes)

        # 2. Enabled
        self.tracer.set_genai_conventions_enabled(True)
        span_on = self.tracer.start_span("model_call_genai")
        span_on.set_genai_attributes(
            system="anthropic",
            model="claude-3-5-sonnet",
            prompt_tokens=200,
            completion_tokens=50,
            cost_micros=3000,
            finish_reasons=["stop"]
        )
        span_on.end()

        self.assertEqual(span_on.attributes["gen_ai.system"], "anthropic")
        self.assertEqual(span_on.attributes["gen_ai.request.model"], "claude-3-5-sonnet")
        self.assertEqual(span_on.attributes["gen_ai.usage.input_tokens"], 200)
        self.assertEqual(span_on.attributes["gen_ai.usage.output_tokens"], 50)
        self.assertEqual(span_on.attributes["gen_ai.usage.total_tokens"], 250)
        self.assertEqual(span_on.attributes["gen_ai.response.finish_reasons"], ["stop"])

    def test_04_secret_canary_probe_zero_leakage_rule_24(self):
        """Standing Rule 24 secret canary probe guarantees 0% plaintext leakage."""
        probe = TelemetryCanaryProbe(self.tracer)
        result = probe.run_drill()

        self.assertTrue(result.passed, f"Canary drill failed with findings: {result.findings}")
        self.assertEqual(result.leaks_found, 0)
        self.assertGreater(result.scanned_spans, 0)
        self.assertGreater(result.total_attributes_scanned, 0)

        # Raw string search in exported OTLP payload
        exported = json.dumps(self.tracer.get_spans())
        self.assertNotIn("ZONATA_CANARY_SECRET", exported)
        self.assertNotIn("sk_live_", exported)

    def test_05_tenant_policy_prompt_body_gating_rule_36(self):
        """Standing Rule 36 body redaction per tenant privacy policy."""
        # Policy: False (default) -> Omit prompt body
        span_redacted = self.tracer.start_span("llm_private", tenant_allow_prompt_capture=False)
        span_redacted.set_genai_attributes(
            prompt_body="Confidential financial report of company XYZ",
            response_body="Summary of confidential data"
        )
        span_redacted.end()
        self.assertEqual(
            span_redacted.attributes["zonata.prompt_body"],
            "[BODY_OMITTED_BY_TENANT_POLICY]"
        )
        self.assertEqual(
            span_redacted.attributes["zonata.response_body"],
            "[BODY_OMITTED_BY_TENANT_POLICY]"
        )

        # Policy: True (explicit opt-in) -> Capture prompt body
        span_allowed = self.tracer.start_span("llm_allowed", tenant_allow_prompt_capture=True)
        span_allowed.set_genai_attributes(
            prompt_body="Public customer service greeting query",
            response_body="Hello, how may I help you today?"
        )
        span_allowed.end()
        self.assertEqual(
            span_allowed.attributes["zonata.prompt_body"],
            "Public customer service greeting query"
        )
        self.assertEqual(
            span_allowed.attributes["zonata.response_body"],
            "Hello, how may I help you today?"
        )

    def test_06_runtime_interceptors_and_decorators(self):
        """Runtime interceptor decorators wrap LLM and Tool calls in spans."""
        @dataclass
        class MockLLMResult:
            content: str
            usage: dict

        @instrument_llm_call(tracer=self.tracer)
        def mock_llm_generate(prompt: str, model: str = "gpt-4o", **kwargs):
            return MockLLMResult(
                content="Generated answer",
                usage={"prompt_tokens": 80, "completion_tokens": 20, "cost_micros": 500}
            )

        @instrument_tool_call(tracer=self.tracer)
        def mock_tool_execute(param: str, tool_name: str = "query_db", **kwargs):
            return {"rows": 5, "status": "success"}

        ctx = CorrelationContext(tenant_id="tnt_interceptor", run_id="run_int_01")

        # Execute instrumented functions
        llm_res = mock_llm_generate(
            prompt="Hello world",
            model="claude-3-5-sonnet",
            correlation_context=ctx
        )
        self.assertEqual(llm_res.content, "Generated answer")

        tool_res = mock_tool_execute(
            param="SELECT *",
            tool_name="search_documents",
            correlation_context=ctx,
            capability_id="database"
        )
        self.assertEqual(tool_res["rows"], 5)

        # Verify spans recorded
        spans = self.tracer.get_spans(trace_id=ctx.trace_id)
        self.assertEqual(len(spans), 2)
        span_names = [s["name"] for s in spans]
        self.assertTrue(any("llm.generate" in name for name in span_names))
        self.assertTrue(any("tool.execute" in name for name in span_names))

    def test_07_standing_rule_40_agpl_isolation_check(self):
        """Standing Rule 40 / ADR 0016 check: verify zero AGPL libraries linked in-process."""
        agpl_forbidden = {"grafana", "loki", "tempo", "victoriametrics"}
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        core_dir = os.path.join(repo_root, "core")

        violations = []
        for root, _, files in os.walk(core_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        try:
                            tree = ast.parse(f.read(), filename=full_path)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        pkg = alias.name.split(".")[0].lower()
                                        if pkg in agpl_forbidden:
                                            violations.append((full_path, pkg))
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module:
                                        pkg = node.module.split(".")[0].lower()
                                        if pkg in agpl_forbidden:
                                            violations.append((full_path, pkg))
                        except Exception:
                            pass

        self.assertEqual(
            violations,
            [],
            f"AGPL boundary violation (Rule 40): in-process AGPL packages detected: {violations}"
        )

    def test_08_mutation_check_strict_leakage_fails_closed(self):
        """Mutation check: unredacted secrets in strict mode fail closed with TelemetryLeakageError."""
        strict_sanitizer = TelemetrySanitizer(default_strict=True)

        # 1. Sensitive key must raise TelemetryLeakageError
        with self.assertRaises(TelemetryLeakageError):
            strict_sanitizer.sanitize_attribute("db_password", "plaintext_secret_123")

        # 2. Canary value must raise TelemetryLeakageError
        with self.assertRaises(TelemetryLeakageError):
            strict_sanitizer.sanitize_attribute("metadata", "ZONATA_CANARY_SECRET_xyz")

        # 3. Live API key pattern must raise TelemetryLeakageError
        with self.assertRaises(TelemetryLeakageError):
            strict_sanitizer.sanitize_attribute("notes", "Use key sk_live_abcdef1234567890 for auth")
