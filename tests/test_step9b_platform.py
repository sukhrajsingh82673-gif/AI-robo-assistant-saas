"""
Platform foundation tests for Sub-Step 9B.
Tests Edge Gateway, Entitlements Engine, OpenFeature Provider, and Migration schemas.
"""

import os
import json
import pytest
from core.edge.gateway import EdgeGateway, RateLimiter, RFC9457Error
from core.entitlements.engine import EntitlementsEngine
from core.flags.openfeature_provider import OpenFeatureProvider, EvaluationContext

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep9bPlatform:

    def test_migrations_sql_exist_and_well_formed(self):
        """Verify 0035 migration and rollback SQL files exist and contain required tables."""
        mig_file = os.path.join(REPO_ROOT, "migrations", "pg", "0035_step9_product_readiness.sql")
        rollback_file = os.path.join(REPO_ROOT, "migrations", "rollback", "0035_step9_product_readiness_downgrade.sql")

        assert os.path.isfile(mig_file), "0035 migration file must exist"
        assert os.path.isfile(rollback_file), "0035 rollback file must exist"

        with open(mig_file, "r", encoding="utf-8") as f:
            mig_content = f.read()

        assert "CREATE SCHEMA IF NOT EXISTS billing;" in mig_content
        assert "CREATE SCHEMA IF NOT EXISTS product;" in mig_content
        assert "CREATE SCHEMA IF NOT EXISTS marketplace;" in mig_content
        assert "ROW LEVEL SECURITY" in mig_content
        assert "billing.usage_ledger" in mig_content
        assert "prev_hash" in mig_content
        assert "record_hash" in mig_content

        with open(rollback_file, "r", encoding="utf-8") as f:
            rb_content = f.read()

        assert "DROP SCHEMA IF EXISTS marketplace CASCADE;" in rb_content
        assert "DROP SCHEMA IF EXISTS product CASCADE;" in rb_content
        assert "DROP SCHEMA IF EXISTS billing CASCADE;" in rb_content

    def test_edge_gateway_headers_and_trace(self):
        """Verify Edge Gateway injects security headers and traceparent."""
        gateway = EdgeGateway()

        def dummy_handler(method, path, headers, body):
            return 200, {"Content-Type": "application/json"}, '{"status": "ok"}'

        gateway.register_route("/healthz", dummy_handler)

        resp = gateway.dispatch(
            method="GET",
            path="/healthz",
            headers={"X-Forwarded-Proto": "https"},
            client_ip="203.0.113.1",
        )

        assert resp.status_code == 200
        assert resp.headers["Strict-Transport-Security"].startswith("max-age=31536000")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert "X-Request-ID" in resp.headers
        assert "traceparent" in resp.headers

    def test_edge_gateway_rate_limiting(self):
        """Verify token bucket rate limiter returns 429 RFC 9457 on burst exhaustion."""
        # 2 tokens per sec, burst capacity 2
        limiter = RateLimiter(default_rate_per_sec=2.0, default_burst=2)
        gateway = EdgeGateway(rate_limiter=limiter)

        def dummy_handler(method, path, headers, body):
            return 200, {}, '{"ok": true}'

        gateway.register_route("/api/test", dummy_handler)

        # Call 1: OK (remaining 1)
        r1 = gateway.dispatch("GET", "/api/test", {}, "198.51.100.1")
        assert r1.status_code == 200

        # Call 2: OK (remaining 0)
        r2 = gateway.dispatch("GET", "/api/test", {}, "198.51.100.1")
        assert r2.status_code == 200

        # Call 3: Rate limited -> 429 RFC 9457 Problem Details
        r3 = gateway.dispatch("GET", "/api/test", {}, "198.51.100.1")
        assert r3.status_code == 429
        assert r3.content_type == "application/problem+json"
        body = json.loads(r3.body)
        assert body["type"] == "https://zonata.ai/errors/rate-limit-exceeded"
        assert body["status"] == 429
        assert "Retry-After" in r3.headers

    def test_entitlements_tier_and_feature_gates(self):
        """Verify EntitlementsEngine enforces minimum tiers and quotas."""
        engine = EntitlementsEngine()
        engine.set_tenant_tier("tenant_free", "free")
        engine.set_tenant_tier("tenant_team", "team")
        engine.set_tenant_tier("tenant_ent", "enterprise")

        # 1. Custom webhooks requires team
        d1 = engine.is_feature_entitled("tenant_free", "webhooks.custom")
        assert not d1.entitled
        assert "requires minimum tier 'team'" in d1.reason

        d2 = engine.is_feature_entitled("tenant_team", "webhooks.custom")
        assert d2.entitled

        # 2. Audit streaming requires enterprise
        d3 = engine.is_feature_entitled("tenant_team", "audit.streaming")
        assert not d3.entitled

        d4 = engine.is_feature_entitled("tenant_ent", "audit.streaming")
        assert d4.entitled

        # 3. Quota check
        q1 = engine.check_quota("tenant_free", "monthly_token_quota", 50_000)
        assert q1.entitled
        assert q1.limit == 100_000

        q2 = engine.check_quota("tenant_free", "monthly_token_quota", 150_000)
        assert not q2.entitled
        assert "exceeds quota limit" in q2.reason

    def test_entitlements_restricted_billing_mode(self):
        """Verify billing restricted mode denies mutations but permits reads."""
        engine = EntitlementsEngine()
        engine.set_tenant_tier("tenant_overdue", "team")
        engine.set_tenant_restricted("tenant_overdue", True)

        # GET is allowed
        allowed_get, _ = engine.check_route_access("tenant_overdue", "/api/public/v1/invoices", {"X-HTTP-Method": "GET"})
        assert allowed_get

        # POST is blocked with restricted notice
        allowed_post, reason = engine.check_route_access("tenant_overdue", "/api/public/v1/invoices", {"X-HTTP-Method": "POST"})
        assert not allowed_post
        assert "restricted read-only mode" in reason

    def test_openfeature_provider_defaults_and_killswitch(self):
        """Verify OpenFeatureProvider safe defaults (OFF), tenant overrides, and kill-switches."""
        provider = OpenFeatureProvider()

        # 1. Safe default: unconfigured flag is False
        assert not provider.get_boolean_value("new_agent_runtime")

        # 2. Global enable
        provider.set_global_flag("new_agent_runtime", True, operator_id="admin_1")
        assert provider.get_boolean_value("new_agent_runtime")

        # 3. Tenant override
        ctx_a = EvaluationContext(targeting_key="tenant_alpha")
        ctx_b = EvaluationContext(targeting_key="tenant_beta")
        provider.set_tenant_flag("dark_launch_beta", "tenant_alpha", True, operator_id="admin_2")
        assert provider.get_boolean_value("dark_launch_beta", context=ctx_a)
        assert not provider.get_boolean_value("dark_launch_beta", context=ctx_b)

        # 4. Emergency kill-switch supersedes everything
        provider.engage_kill_switch("new_agent_runtime", reason="Upstream CVE-2026-9999", operator_id="security_lead")
        assert not provider.get_boolean_value("new_agent_runtime")
        assert not provider.get_boolean_value("new_agent_runtime", context=ctx_a)
        is_killed, reason = provider.is_kill_switched("new_agent_runtime")
        assert is_killed
        assert "CVE-2026-9999" in reason

        # 5. Audit trail records actions
        trail = provider.get_audit_trail()
        assert len(trail) >= 3
        actions = [r["action"] for r in trail]
        assert "SET_GLOBAL" in actions
        assert "SET_TENANT" in actions
        assert "ENGAGE_KILL_SWITCH" in actions
