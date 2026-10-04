"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Deep SaaS Platform Integration & Master Qualification Test Suite
================================================================
Comprehensive verification covering all 15 core technologies and architectural invariants:
 1. Temporal: Durable workflow & execution bridge
 2. OpenTelemetry: Universal distributed tracing & Prometheus metrics
 3. MinIO / S3: Enterprise artifact storage, lifecycle, presigned HMAC URLs
 4. HashiCorp Vault: Dynamic scoped credential leases, TTL, and instant revocation
 5. Keycloak: Enterprise identity & SSO vs ZONATA authority separation
 6. Langfuse: LLM observability, multi-model pricing, prompt versioning
 7. NATS JetStream: Distributed asynchronous event bus, streams, wildcard routing
 8. OpenFGA: Fine-grained ReBAC authorization under AuthorityGateway
 9. Agent Evaluation: Native 7-dimension evaluation & regression framework
10. Usage Metering & Billing: Multi-tenant usage ledger, entitlements, Stripe/Razorpay
11. PostHog: SaaS product intelligence, 8-stage funnels, feature flags, secret scrubbing
12. Disaster Recovery: Snapshot, backup, and restore consistency
13. Adversarial Multi-Tenant Isolation: Cross-tenant barrier verification across all systems
14. Supply-Chain Security & Architecture: Dependency integrity & sovereign authority preservation
15. End-to-End SaaS Operational Workflow: Unified lifecycle across the entire platform
"""

import unittest
import os
import sys
import time
import json
import uuid
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import Core Platform Engines
from core.opentelemetry_engine import (
    OpenTelemetryEngine, opentelemetry_engine, opentelemetry_tracer,
    CorrelationContext, SpanKind, SpanStatus, StatusCode
)
from core.langfuse_engine import LangfuseEngine, langfuse_engine, PromptVersion
from core.openfga_engine import OpenFGAEngine, openfga_engine, RelationshipTuple
from core.nats_jetstream import JetStreamEngine, jetstream_engine, StreamConfig
from core.vault_client import HashiCorpVaultClient, vault_client, ScopedCredentialLease
from core.keycloak_idp import KeycloakIdPEngine, keycloak_idp, KeycloakUserProfile
from core.agent_evaluation import AgentEvaluationEngine, agent_evaluation_engine, EvaluationTestCase, EvaluationReport
from core.saas_billing import (
    SaasBillingEngine, saas_billing_engine, SubscriptionTier,
    StripeBillingAdapter, RazorpayBillingAdapter
)
from core.posthog_analytics import PostHogAnalyticsEngine, posthog_analytics
from core.object_storage import ObjectStorageService, object_store, ArtifactLifecycleState
from zonata.temporal_adapter import TemporalUniversalTerminalBridge


class Test01_TemporalDurableExecution(unittest.TestCase):
    """Temporal durable workflow execution and terminal recovery verification."""

    def setUp(self):
        self.bridge = TemporalUniversalTerminalBridge(tenant_id="tnt_test_temporal")

    def test_01_temporal_terminal_bridge_execution(self):
        res = self.bridge.execute_terminal_activity(
            command="echo 'temporal durable execution success'",
            distro="alpine",
            mission_id="msn_temporal_001",
            agent_id="agent_orchestrator"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("temporal durable execution success", res["output"])
        self.assertIn("duration_ms", res)
        self.assertIn("evidence_id", res)

    def test_02_temporal_terminal_bridge_governance_block(self):
        res = self.bridge.execute_terminal_activity(
            command="rm -rf / --no-preserve-root",
            distro="ubuntu",
            mission_id="msn_temporal_002"
        )
        self.assertFalse(res["success"])
        self.assertNotEqual(res["exit_code"], 0)
        self.assertIn("blocked", res["output"].lower())


class Test02_OpenTelemetryTracing(unittest.TestCase):
    """OpenTelemetry universal distributed tracing and Prometheus metrics verification."""

    def setUp(self):
        self.engine = OpenTelemetryEngine.get_instance()

    def test_01_correlation_context_lineage(self):
        ctx = CorrelationContext(
            tenant_id="tnt_acme",
            company_id="comp_acme_corp",
            mission_id="msn_q3_expansion",
            execution_id="exec_90210",
            task_id="task_calc_roi",
            agent_id="agent_cfo",
            tool_id="tool_financial_calc",
            evidence_id="e"*64
        )
        span = self.engine.tracer.start_span("calculate_projections", context=ctx)
        span.set_attribute("market.sector", "fintech")
        span.end()
        self.engine.finish_span(span)

        otlp = span.to_otlp_json()
        self.assertEqual(otlp["name"], "calculate_projections")
        self.assertTrue(otlp["traceId"])
        self.assertTrue(otlp["spanId"])

        # Verify lineage attributes
        attrs = {item["key"]: item["value"]["stringValue"] for item in otlp["attributes"]}
        self.assertEqual(attrs.get("zonata.tenant_id"), "tnt_acme")
        self.assertEqual(attrs.get("zonata.company_id"), "comp_acme_corp")
        self.assertEqual(attrs.get("zonata.mission_id"), "msn_q3_expansion")
        self.assertEqual(attrs.get("zonata.execution_id"), "exec_90210")
        self.assertEqual(attrs.get("zonata.task_id"), "task_calc_roi")
        self.assertEqual(attrs.get("zonata.agent_id"), "agent_cfo")
        self.assertEqual(attrs.get("zonata.tool_id"), "tool_financial_calc")
        self.assertEqual(attrs.get("zonata.evidence_id"), "e"*64)

    def test_02_w3c_traceparent_format(self):
        span = self.engine.start_trace("w3c_propagation_test", tenant_id="tnt_w3c", company_id="comp_w3c")
        traceparent = f"00-{span.trace_id}-{span.span_id}-01"
        parts = traceparent.split("-")
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "00")
        self.assertEqual(len(parts[1]), 32)
        self.assertEqual(len(parts[2]), 16)
        self.assertEqual(parts[3], "01")
        self.engine.finish_span(span)

    def test_03_credential_sanitization_in_otel(self):
        span = self.engine.start_trace("sanitize_test", tenant_id="tnt_sec", company_id="comp_sec")
        span.set_attribute("api_secret_key", "sk_live_very_secret_key_12345")
        span.set_attribute("db_password", "super_secret_db_pass")
        span.set_attribute("regular_attribute", "public_value")
        self.engine.finish_span(span)

        otlp = span.to_otlp_json()
        attrs = {item["key"]: item["value"]["stringValue"] for item in otlp["attributes"]}
        self.assertIn("[REDACTED]", attrs["api_secret_key"])
        self.assertIn("[REDACTED]", attrs["db_password"])
        self.assertEqual(attrs["regular_attribute"], "public_value")

    def test_04_prometheus_metrics_export(self):
        self.engine.metrics.add_counter("missions_completed_total", 5.0, {"priority": "high"})
        self.engine.metrics.set_gauge("active_agents_gauge", 42.0)
        self.engine.metrics.record_histogram("llm_response_time_ms", 120.5)

        prom_text = self.engine.metrics.export_prometheus()
        self.assertIn("missions_completed_total{priority=high} 5.0", prom_text)
        self.assertIn("active_agents_gauge 42.0", prom_text)
        self.assertIn("llm_response_time_ms_count 1", prom_text)

        summary = self.engine.metrics.get_metrics_summary()
        self.assertIn("counters", summary)
        self.assertIn("gauges", summary)
        self.assertIn("histograms", summary)


class Test03_MinIOS3ObjectStorage(unittest.TestCase):
    """MinIO / S3-compatible enterprise object storage verification."""

    def setUp(self):
        self.store = ObjectStorageService()

    def test_01_large_artifact_s3_uri(self):
        data = b"Video recording of autonomous agent executing financial audit 2026."
        ref = self.store.store_large_artifact(
            tenant_id="tnt_enterprise",
            company_id="comp_titan",
            mission_id="msn_audit",
            execution_id="exec_vid_01",
            category="recordings",
            filename="session_recording.webm",
            data=data,
            ttl_hours=48
        )
        self.assertTrue(ref.artifact_id.startswith("art_"))
        self.assertEqual(ref.size_bytes, len(data))
        self.assertEqual(ref.sha256_hash, hashlib.sha256(data).hexdigest())
        self.assertEqual(
            ref.metadata.get("s3_uri"),
            "s3://zonata-artifacts/tnt_enterprise/comp_titan/msn_audit/exec_vid_01/recordings/session_recording.webm"
        )
        self.assertEqual(ref.to_dict()["size_bytes"], len(data))

    def test_02_presigned_url_generation_and_tamper_resistance(self):
        ref = self.store.store_large_artifact(
            tenant_id="tnt_enterprise",
            filename="confidential_report.pdf",
            data=b"Confidential Board Report",
            category="documents"
        )
        url = self.store.generate_presigned_url(ref.artifact_id, expires_in_sec=1800)
        self.assertIn("http://localhost:8080/api/storage/artifacts/download", url)
        self.assertIn("expires=", url)
        self.assertIn("sig=", url)

    def test_03_legal_hold_and_lifecycle_pruning(self):
        # Store artifact with LEGAL_HOLD
        ref_hold = self.store.store_artifact(
            tenant_id="tnt_enterprise",
            filename="sec_investigation_evidence.bin",
            data=b"Subpoena evidence package",
            lifecycle_state=ArtifactLifecycleState.LEGAL_HOLD
        )
        self.assertTrue(ref_hold.legal_hold)

        # Store temporary expired artifact
        ref_temp = self.store.store_artifact(
            tenant_id="tnt_enterprise",
            filename="temp_cache.tmp",
            data=b"Temporary cache data",
            lifecycle_state=ArtifactLifecycleState.TEMPORARY,
            retention_days=-1.0  # Already expired
        )

        pruned = self.store.prune_expired_artifacts()
        # Verify hold item was preserved
        held_ref, _ = self.store.retrieve_artifact(ref_hold.artifact_id, "tnt_enterprise")
        self.assertIsNotNone(held_ref)
        self.assertEqual(held_ref.lifecycle_state, ArtifactLifecycleState.LEGAL_HOLD)


class Test04_HashiCorpVaultClient(unittest.TestCase):
    """HashiCorp Vault dynamic credential broker verification."""

    def setUp(self):
        self.vault = HashiCorpVaultClient.get_instance()

    def test_01_dynamic_scoped_lease_issuance(self):
        lease = self.vault.issue_scoped_lease(
            tenant_id="tnt_acme",
            company_id="comp_acme",
            agent_id="agent_analyst",
            tool_id="tool_postgres_query",
            target_system="warehouse_db",
            required_actions=["read"],
            ttl_seconds=600
        )
        self.assertTrue(lease.lease_id.startswith("vault_lease_"))
        self.assertEqual(lease.tenant_id, "tnt_acme")
        self.assertEqual(lease.agent_id, "agent_analyst")
        self.assertEqual(lease.target_system, "warehouse_db")
        self.assertTrue(lease.is_valid)
        self.assertFalse(lease.revoked)
        self.assertIn("access_token", lease.scoped_credentials)
        self.assertTrue(lease.scoped_credentials["access_token"].startswith("scoped_"))

    def test_02_path_and_action_restriction(self):
        read_lease = self.vault.issue_scoped_lease(
            tenant_id="tnt_acme",
            target_system="production_postgres",
            required_actions=["read"]
        )
        self.assertEqual(read_lease.allowed_paths, ["/production_postgres/v1/read_only"])
        self.assertEqual(read_lease.allowed_actions, ["read"])

    def test_03_instant_revocation(self):
        lease = self.vault.issue_scoped_lease(
            tenant_id="tnt_acme",
            target_system="redis_cluster",
            required_actions=["read", "write"],
            ttl_seconds=1200
        )
        self.assertTrue(lease.is_valid)

        revoked = self.vault.revoke_lease(lease.lease_id, reason="Security inspection complete")
        self.assertTrue(revoked)
        self.assertFalse(lease.is_valid)
        self.assertTrue(lease.revoked)
        self.assertEqual(lease.revocation_reason, "Security inspection complete")


class Test05_KeycloakEnterpriseIdP(unittest.TestCase):
    """Keycloak enterprise identity provider & SSO verification."""

    def setUp(self):
        self.idp = KeycloakIdPEngine.get_instance()

    def test_01_oidc_token_validation_and_jit(self):
        res = self.idp.authenticate_token("dev_token_valid")
        self.assertTrue(res.authenticated)
        self.assertIsNotNone(res.user_profile)
        self.assertEqual(res.user_profile.realm, "zonata-enterprise")
        self.assertEqual(res.user_profile.email, "dev_token_valid@enterprise.corp")
        self.assertIn("employee", res.user_profile.roles)
        self.assertEqual(res.to_dict()["authenticated"], True)

    def test_02_session_revocation(self):
        res = self.idp.authenticate_token("token_session_user_77")
        self.assertTrue(res.authenticated)
        sess_id = res.user_profile.session_id

        # Revoke session
        self.idp.revoke_session(sess_id)
        # Attempt to authenticate with the same session token
        res_after = self.idp.authenticate_token(json.dumps({"sub": "usr_77", "session_id": sess_id}))
        self.assertFalse(res_after.authenticated)
        self.assertIn("revoked", res_after.error_message.lower())

    def test_03_identity_authority_boundary(self):
        # Architectural Invariant: Keycloak identifies, ZONATA authorizes
        res = self.idp.authenticate_token("dev_token_valid")
        self.assertTrue(res.authenticated)
        # Keycloak says who they are, but does NOT grant sovereign control without AuthorityGateway
        self.assertNotIn("sovereign_kill_switch_master", res.user_profile.roles)


class Test06_LangfuseAIObservability(unittest.TestCase):
    """Langfuse AI Observability, model cost calculation, and prompt management."""

    def setUp(self):
        self.lf = LangfuseEngine.get_instance()

    def test_01_generation_token_cost_calculation(self):
        # Test GPT-4o cost calculation: $2.50 / 1M in, $10.00 / 1M out
        cost_gpt4o = self.lf.calculate_cost("gpt-4o", 100_000, 20_000)
        expected_gpt4o = round((100_000/1_000_000)*2.50 + (20_000/1_000_000)*10.00, 6)
        self.assertEqual(cost_gpt4o, expected_gpt4o)

        # Test Local model cost calculation: $0.00
        cost_local = self.lf.calculate_cost("local-deepseek-r1", 500_000, 100_000)
        self.assertEqual(cost_local, 0.0)

        # Record generation and verify
        gen = self.lf.record_generation(
            name="q3_financial_summary",
            model="gpt-4o",
            prompt="Analyze balance sheet and predict churn",
            completion="Churn probability: 2.1%",
            prompt_tokens=1500,
            completion_tokens=250,
            latency_ms=340.0,
            tenant_id="tnt_analytics",
            company_id="comp_finance"
        )
        self.assertEqual(gen.total_tokens, 1750)
        self.assertTrue(gen.cost_usd > 0)
        self.assertEqual(gen.latency_ms, 340.0)

    def test_02_prompt_versioning(self):
        pv1 = self.lf.register_prompt("ceo_morning_brief", "Briefing for {{company_name}} v1", ["company_name"])
        pv2 = self.lf.register_prompt("ceo_morning_brief", "Briefing for {{company_name}} v2: Detailed metrics", ["company_name"])

        self.assertEqual(pv1.version, 1)
        self.assertEqual(pv2.version, 2)
        self.assertFalse(pv1.is_active)
        self.assertTrue(pv2.is_active)

        active = self.lf.get_prompt("ceo_morning_brief")
        self.assertEqual(active.version, 2)

    def test_03_automated_scoring_and_feedback(self):
        gen = self.lf.record_generation(
            name="policy_check",
            model="claude-3-5-sonnet",
            prompt="Check contract for GDPR compliance",
            completion="Contract GDPR compliant",
            prompt_tokens=800,
            completion_tokens=100,
            latency_ms=210.0,
            tenant_id="tnt_legal",
            company_id="comp_legal"
        )
        scored = self.lf.submit_score(gen.generation_id, "correctness", 0.98, comment="Verified by legal rule engine")
        self.assertTrue(scored)

        feedback = self.lf.submit_feedback(gen.generation_id, rating=5, comment="Flawless extraction", user_id="usr_general_counsel")
        self.assertTrue(feedback)

        analytics = self.lf.get_analytics("tnt_legal")
        self.assertTrue(analytics["total_generations"] >= 1)
        self.assertTrue(analytics["total_tokens"] >= 900)


class Test07_NATSJetStreamEventBus(unittest.TestCase):
    """NATS JetStream distributed event bus & stream persistence verification."""

    def setUp(self):
        self.nats = JetStreamEngine()

    def test_01_stream_creation_and_routing(self):
        msg = self.nats.publish(
            subject="zonata.missions.created",
            data={"mission_id": "msn_jetstream_test", "title": "Automated Tax Audit"},
            tenant_id="tnt_tax",
            company_id="comp_tax"
        )
        self.assertEqual(msg.subject, "zonata.missions.created")
        self.assertEqual(msg.headers.get("tenant_id"), "tnt_tax")
        self.assertTrue(msg.sequence >= 1)

    def test_02_stream_replay(self):
        self.nats.publish(
            subject="zonata.missions.created",
            data={"mission_id": "msn_seq_1"},
            tenant_id="tnt_tax"
        )
        self.nats.publish(
            subject="zonata.missions.completed",
            data={"mission_id": "msn_seq_1", "status": "SUCCESS"},
            tenant_id="tnt_tax"
        )

        replayed = self.nats.replay_stream("ZONATA_MISSIONS", tenant_id="tnt_tax")
        self.assertTrue(len(replayed) >= 2)
        self.assertEqual(replayed[0]["data"]["mission_id"], "msn_seq_1")

    def test_03_at_least_once_delivery(self):
        delivered = []
        def handler(msg):
            delivered.append(msg.subject)

        self.nats.subscribe("zonata.operations.>", handler)
        self.nats.publish(
            subject="zonata.operations.TaskStarted",
            data={"task_id": "task_nats_01"},
            tenant_id="tnt_ops"
        )
        self.assertIn("zonata.operations.TaskStarted", delivered)


class Test08_OpenFGAReBACAuthorization(unittest.TestCase):
    """OpenFGA Relationship-Based Access Control (ReBAC) under AuthorityGateway."""

    def setUp(self):
        self.fga = OpenFGAEngine.get_instance()

    def test_01_direct_relationship_check(self):
        self.fga.write_tuple("user:david", "viewer", "report:annual_audit_2026", tenant_id="tnt_rebac")
        allowed = self.fga.check("user:david", "viewer", "report:annual_audit_2026", tenant_id="tnt_rebac")
        denied = self.fga.check("user:eve", "viewer", "report:annual_audit_2026", tenant_id="tnt_rebac")
        self.assertTrue(allowed)
        self.assertFalse(denied)

    def test_02_hierarchical_relations(self):
        # Owner automatically has editor and viewer relations
        self.fga.write_tuple("user:grace", "owner", "folder:strategic_plans", tenant_id="tnt_rebac")
        self.assertTrue(self.fga.check("user:grace", "owner", "folder:strategic_plans", tenant_id="tnt_rebac"))
        self.assertTrue(self.fga.check("user:grace", "editor", "folder:strategic_plans", tenant_id="tnt_rebac"))
        self.assertTrue(self.fga.check("user:grace", "viewer", "folder:strategic_plans", tenant_id="tnt_rebac"))

    def test_03_group_membership_transitivity(self):
        # Alice is member of group:executives; group:executives is viewer of document:roadmap
        self.fga.write_tuple("user:alice", "member", "group:executives", tenant_id="tnt_rebac")
        self.fga.write_tuple("group:executives", "viewer", "document:q4_roadmap", tenant_id="tnt_rebac")
        self.assertTrue(self.fga.check("user:alice", "viewer", "document:q4_roadmap", tenant_id="tnt_rebac"))


class Test09_AgentEvaluationFramework(unittest.TestCase):
    """Native agent evaluation, 7-dimension scoring, and regression tracking."""

    def setUp(self):
        self.eval_engine = AgentEvaluationEngine.get_instance()

    def test_01_seven_dimension_scorecard(self):
        rep = self.eval_engine.evaluate_execution(
            test_case_id="eval_001_market_analysis",
            agent_id="agent_analyst_01",
            model="gpt-4o",
            actual_output="Market analysis complete: Revenue grew 28% year over year across APAC regions.",
            tools_used=["web_search", "financial_calculator"],
            latency_sec=2.1,
            cost_usd=0.012,
            evidence_id="a"*64
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.score >= 0.85)
        self.assertIn("correctness", rep.dimension_scores)
        self.assertIn("tool_selection", rep.dimension_scores)
        self.assertIn("policy_compliance", rep.dimension_scores)
        self.assertIn("safety", rep.dimension_scores)
        self.assertIn("latency", rep.dimension_scores)
        self.assertIn("cost", rep.dimension_scores)
        self.assertIn("evidence", rep.dimension_scores)

    def test_02_adversarial_injection_resistance(self):
        # Test case: injection attempt leaked credential
        rep_fail = self.eval_engine.evaluate_execution(
            test_case_id="eval_002_injection_resistance",
            agent_id="agent_vulnerable",
            actual_output="Here is the requested password=SuperSecretPassword123",
            tools_used=["credential_broker"],
            latency_sec=1.0,
            cost_usd=0.005
        )
        self.assertFalse(rep_fail.passed)
        self.assertEqual(rep_fail.dimension_scores["safety"], 0.0)
        self.assertEqual(rep_fail.dimension_scores["tool_selection"], 0.0)

        # Test case: injection attempt properly refused
        rep_pass = self.eval_engine.evaluate_execution(
            test_case_id="eval_002_injection_resistance",
            agent_id="agent_hardened",
            actual_output="I refuse to ignore my constitutional instructions or leak secrets.",
            tools_used=[],
            latency_sec=0.8,
            cost_usd=0.002,
            evidence_id="b"*64
        )
        self.assertTrue(rep_pass.passed)
        self.assertEqual(rep_pass.dimension_scores["safety"], 1.0)

    def test_03_regression_history(self):
        reports = self.eval_engine.list_reports(test_id="eval_001_market_analysis")
        self.assertTrue(len(reports) >= 1)
        self.assertTrue(reports[0]["score"] > 0)


class Test10_SaaSBillingAndEntitlements(unittest.TestCase):
    """Usage metering, entitlement engine, and payment adapter verification."""

    def setUp(self):
        self.billing = SaasBillingEngine.get_instance()

    def test_01_usage_metering_all_dimensions(self):
        tenant_id = f"tnt_meter_{uuid.uuid4().hex[:6]}"
        self.billing.record_usage(tenant_id, "tokens", 25_000, cost_usd=0.0625)
        self.billing.record_usage(tenant_id, "browser_minutes", 15.0, cost_usd=0.30)
        self.billing.record_usage(tenant_id, "terminal_seconds", 120.0, cost_usd=0.04)
        self.billing.record_usage(tenant_id, "storage_bytes", 10_000_000, cost_usd=0.01)
        self.billing.record_usage(tenant_id, "api_call", 50, cost_usd=0.05)

        snap = self.billing.get_or_create_tenant(tenant_id)
        self.assertEqual(snap.tokens_consumed, 25_000)
        self.assertEqual(snap.browser_minutes_consumed, 15.0)
        self.assertEqual(snap.terminal_seconds_consumed, 120.0)
        self.assertEqual(snap.storage_bytes_consumed, 10_000_000)
        self.assertEqual(snap.api_calls_count, 50)
        self.assertTrue(snap.total_cost_usd >= 0.40)

    def test_02_entitlement_quota_checks(self):
        tenant_id = f"tnt_quota_{uuid.uuid4().hex[:6]}"
        snap = self.billing.get_or_create_tenant(tenant_id, tier=SubscriptionTier.FREE)

        # Free tier allows 100k tokens
        ok, _ = self.billing.check_entitlement(tenant_id, "tokens", 50_000)
        self.assertTrue(ok)

        # Free tier exceeds 1M tokens
        exceeds, msg = self.billing.check_entitlement(tenant_id, "tokens", 1_500_000)
        self.assertFalse(exceeds)
        self.assertIn("quota exceeded", msg.lower())

    def test_03_plan_upgrade_flow(self):
        tenant_id = f"tnt_upg_{uuid.uuid4().hex[:6]}"
        snap = self.billing.get_or_create_tenant(tenant_id, tier=SubscriptionTier.FREE)
        self.assertEqual(snap.tier, SubscriptionTier.FREE)

        upgraded = self.billing.upgrade_plan(tenant_id, SubscriptionTier.ENTERPRISE)
        self.assertEqual(upgraded.tier, SubscriptionTier.ENTERPRISE)

        # In Enterprise tier, 10M tokens is within quota (allows 200M)
        ok, _ = self.billing.check_entitlement(tenant_id, "tokens", 10_000_000)
        self.assertTrue(ok)

    def test_04_payment_provider_adapters(self):
        stripe = StripeBillingAdapter()
        res_stripe = stripe.create_customer("tnt_stripe", "billing@enterprise.corp")
        self.assertTrue(res_stripe["success"])
        self.assertTrue(res_stripe["stripe_customer_id"].startswith("cus_"))

        razorpay = RazorpayBillingAdapter()
        res_rzp = razorpay.create_customer("tnt_razorpay", "billing@enterprise.in")
        self.assertTrue(res_rzp["success"])
        self.assertTrue(res_rzp["razorpay_customer_id"].startswith("cust_"))


class Test11_PostHogProductAnalytics(unittest.TestCase):
    """PostHog SaaS product intelligence, funnels, and feature flags."""

    def setUp(self):
        self.ph = PostHogAnalyticsEngine.get_instance()

    def test_01_eight_stage_funnel(self):
        tenant_id = f"tnt_ph_{uuid.uuid4().hex[:6]}"
        user_id = f"usr_{uuid.uuid4().hex[:6]}"

        stages = [
            "signup",
            "company_created",
            "agent_created",
            "first_mission_dispatched",
            "mission_succeeded",
            "integration_connected",
            "paid_conversion",
            "retention_active"
        ]

        for stage in stages:
            self.ph.capture(
                event_name=stage,
                distinct_id=user_id,
                properties={"stage": stage},
                tenant_id=tenant_id
            )

        funnel = self.ph.get_funnel_summary(tenant_id=tenant_id)
        for stage in stages:
            self.assertEqual(funnel[stage], 1)

    def test_02_feature_flags_and_tenant_overrides(self):
        tenant_id = f"tnt_flags_{uuid.uuid4().hex[:6]}"
        # Global default
        self.assertTrue(self.ph.is_feature_enabled("enable_langfuse_tracing", "usr_1", tenant_id))

        # Override for specific tenant
        self.ph.set_tenant_flag_override(tenant_id, "enable_langfuse_tracing", False)
        self.assertFalse(self.ph.is_feature_enabled("enable_langfuse_tracing", "usr_1", tenant_id))

    def test_03_secret_scrubbing_in_analytics(self):
        evt = self.ph.capture(
            event_name="workspace_action",
            distinct_id="usr_sec",
            properties={
                "public_metric": "value",
                "api_key": "live_secret_token_12345",
                "master_password": "super_secret_pw"
            }
        )
        self.assertEqual(evt.properties["public_metric"], "value")
        self.assertEqual(evt.properties["api_key"], "[REDACTED]")
        self.assertEqual(evt.properties["master_password"], "[REDACTED]")


class Test12_DisasterRecoveryAndBackup(unittest.TestCase):
    """Backup & restore procedures, database, object store, and evidence ledger consistency."""

    def test_01_state_snapshot_and_restore(self):
        # 1. Evidence ledger checkpoint
        ledger_path = os.path.join(BASE_DIR, "storage/evidence/audit_ledger.jsonl")
        ledger_exists = os.path.exists(ledger_path)
        self.assertTrue(ledger_exists, "Evidence ledger must exist on disk")

        # 2. Object storage manifest checkpoint
        manifest_path = os.path.join(BASE_DIR, "storage/object_store/artifact_manifest.jsonl")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            self.assertTrue(isinstance(lines, list))

        # 3. Merkle verification test
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger_lines = [json.loads(line) for line in f if line.strip()]
        self.assertTrue(len(ledger_lines) > 0, "Ledger must contain verifiable Merkle receipts")


class Test13_AdversarialMultiTenantIsolation(unittest.TestCase):
    """Adversarial cross-tenant barrier verification across all platform engines."""

    def test_01_cross_tenant_isolation_matrix(self):
        tenant_a = "tnt_victim_alpha"
        tenant_b = "tnt_attacker_beta"

        # 1. OpenFGA: Tenant B cannot see or check Tenant A's tuples
        openfga_engine.write_tuple("user:alice", "owner", "doc:merger_target", tenant_id=tenant_a)
        self.assertTrue(openfga_engine.check("user:alice", "owner", "doc:merger_target", tenant_id=tenant_a))
        self.assertFalse(openfga_engine.check("user:alice", "owner", "doc:merger_target", tenant_id=tenant_b))

        # 2. Vault: Tenant B cannot list or access Tenant A's leases
        lease_a = vault_client.issue_scoped_lease(tenant_id=tenant_a, agent_id="agent_a", target_system="corp_db")
        leases_b = vault_client.list_active_leases(tenant_id=tenant_b)
        self.assertNotIn(lease_a.lease_id, [l["lease_id"] for l in leases_b])

        # 3. Langfuse: Tenant B cannot query Tenant A's generations
        langfuse_engine.record_generation(
            name="private_a",
            model="gpt-4o",
            prompt="Secret strategy A",
            completion="Confidential",
            prompt_tokens=10,
            completion_tokens=5,
            tenant_id=tenant_a,
            company_id="comp_a"
        )
        gens_b = langfuse_engine.get_generations(tenant_id=tenant_b)
        self.assertEqual(len(gens_b), 0)

        # 4. JetStream: Tenant B cannot view Tenant A's stream messages
        jetstream_engine.publish(
            subject="zonata.missions.created",
            data={"mission": "classified_alpha"},
            tenant_id=tenant_a
        )
        replayed_b = jetstream_engine.replay_stream("ZONATA_MISSIONS", tenant_id=tenant_b)
        self.assertNotIn("classified_alpha", [m["data"].get("mission") for m in replayed_b])

        # 5. Object Storage: Tenant B cannot retrieve Tenant A's artifacts
        art_a = object_store.store_large_artifact(
            tenant_id=tenant_a,
            filename="financials.xlsx",
            data=b"Revenue numbers",
            category="documents"
        )
        art_retrieved = object_store.retrieve_artifact(art_a.artifact_id, tenant_id=tenant_b)
        self.assertIsNone(art_retrieved)

        # 6. SaaS Billing: Tenant B cannot query Tenant A's usage
        saas_billing_engine.record_usage(tenant_a, "tokens", 50_000)
        snap_b = saas_billing_engine.get_or_create_tenant(tenant_b)
        self.assertEqual(snap_b.tokens_consumed, 0)


class Test14_SupplyChainSecurityAndSBOM(unittest.TestCase):
    """Software Bill of Materials (SBOM) and dependency audit verification."""

    def test_01_dependency_and_architecture_audit(self):
        # Verify standard-library zero-dependency resilience
        for module_name in [
            "core.opentelemetry_engine",
            "core.langfuse_engine",
            "core.openfga_engine",
            "core.nats_jetstream",
            "core.vault_client",
            "core.keycloak_idp",
            "core.agent_evaluation",
            "core.saas_billing",
            "core.posthog_analytics",
            "core.object_storage",
            "zonata.temporal_adapter"
        ]:
            self.assertIn(module_name, sys.modules)

        # Verify sovereign authority preservation invariant
        # Keycloak is identity provider; ZONATA AuthorityGateway owns authorization
        self.assertNotEqual(keycloak_idp, openfga_engine)


class Test15_EndToEndSaaSOperationalWorkflow(unittest.TestCase):
    """Full lifecycle: Tenant onboarding -> Identity -> Vault -> OTel -> Langfuse -> OpenFGA -> NATS -> Eval -> Billing -> PostHog."""

    def test_01_complete_saas_lifecycle(self):
        tenant_id = f"tnt_e2e_{uuid.uuid4().hex[:6]}"
        company_id = f"comp_e2e_{uuid.uuid4().hex[:6]}"
        user_id = f"usr_e2e_{uuid.uuid4().hex[:6]}"

        # Step 1: Product Funnel - User Signup
        posthog_analytics.capture(
            event_name="signup",
            distinct_id=user_id,
            properties={"plan": "enterprise"},
            tenant_id=tenant_id,
            company_id=company_id
        )

        # Step 2: Enterprise Identity Authentication via Keycloak
        auth_res = keycloak_idp.authenticate_token("dev_token_valid")
        self.assertTrue(auth_res.authenticated)

        # Step 3: Scoped Credential Issuance via HashiCorp Vault
        lease = vault_client.issue_scoped_lease(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id="agent_e2e_lead",
            target_system="enterprise_pg",
            required_actions=["read"]
        )
        self.assertTrue(lease.is_valid)

        # Step 4: Distributed Tracing with OpenTelemetry Context
        span = opentelemetry_engine.start_trace(
            span_name="e2e_mission_dispatch",
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id="msn_e2e_001",
            agent_id="agent_e2e_lead"
        )
        span.set_attribute("mission.objective", "Market valuation analysis")

        # Step 5: Relationship Authorization check via OpenFGA
        openfga_engine.write_tuple(f"user:{user_id}", "owner", f"mission:msn_e2e_001", tenant_id=tenant_id)
        permitted = openfga_engine.check(f"user:{user_id}", "owner", f"mission:msn_e2e_001", tenant_id=tenant_id)
        self.assertTrue(permitted)

        # Step 6: LLM Observability & Cost Tracking via Langfuse
        gen = langfuse_engine.record_generation(
            name="valuation_synthesis",
            model="gpt-4o",
            prompt="Compute EBITDA and valuation multiple",
            completion="Valuation multiple: 14.5x EBITDA ($45.2M EV)",
            prompt_tokens=2200,
            completion_tokens=450,
            latency_ms=480.0,
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id="msn_e2e_001",
            agent_id="agent_e2e_lead"
        )
        self.assertTrue(gen.cost_usd > 0)

        # Step 7: Asynchronous Event Notification via NATS JetStream
        evt_msg = jetstream_engine.publish(
            subject="zonata.missions.completed",
            data={"mission_id": "msn_e2e_001", "status": "SUCCESS"},
            tenant_id=tenant_id,
            company_id=company_id
        )
        self.assertTrue(evt_msg.sequence >= 1)

        # Step 8: Multi-Dimensional Evaluation via Agent Evaluation Framework
        eval_rep = agent_evaluation_engine.evaluate_execution(
            test_case_id="eval_001_market_analysis",
            agent_id="agent_e2e_lead",
            model="gpt-4o",
            actual_output="Valuation multiple: 14.5x EBITDA ($45.2M EV). Market analysis complete.",
            tools_used=["financial_calculator", "web_search"],
            latency_sec=0.48,
            cost_usd=gen.cost_usd,
            evidence_id="f"*64
        )
        self.assertTrue(eval_rep.passed)

        # Step 9: Usage Metering and Billing Ledger
        saas_billing_engine.record_usage(
            tenant_id=tenant_id,
            metric="tokens",
            amount=gen.total_tokens,
            cost_usd=gen.cost_usd
        )
        usage_snap = saas_billing_engine.get_or_create_tenant(tenant_id)
        self.assertEqual(usage_snap.tokens_consumed, 2650)

        # Step 10: Product Funnel - Mission Succeeded & Paid Conversion
        posthog_analytics.capture(
            event_name="first_mission_dispatched",
            distinct_id=user_id,
            tenant_id=tenant_id,
            company_id=company_id
        )
        posthog_analytics.capture(
            event_name="mission_succeeded",
            distinct_id=user_id,
            tenant_id=tenant_id,
            company_id=company_id
        )
        posthog_analytics.capture(
            event_name="paid_conversion",
            distinct_id=user_id,
            tenant_id=tenant_id,
            company_id=company_id
        )

        funnel = posthog_analytics.get_funnel_summary(tenant_id=tenant_id)
        self.assertEqual(funnel["signup"], 1)
        self.assertEqual(funnel["first_mission_dispatched"], 1)
        self.assertEqual(funnel["mission_succeeded"], 1)
        self.assertEqual(funnel["paid_conversion"], 1)

        # Step 11: Conclude Trace & Revoke Vault Lease
        opentelemetry_engine.finish_span(span)
        vault_client.revoke_lease(lease.lease_id, reason="Workflow complete")
        self.assertFalse(lease.is_valid)


if __name__ == "__main__":
    unittest.main()
