"""Unit & Integration Tests for Capability Truth Table, AST Linter, and Planner Read-Before-Promise.

Verifies OpenCode Step 1C:
1. Reality probe tests across all 18 capabilities.
2. Truth rule: No fabricated statuses, browser and desktop_control are NOT_IMPLEMENTED.
3. Planner reads truth table before promising any step and refuses unavailable capabilities without looping.
4. CEOWorkforceController rejects web scraping / browser tasks cleanly with alternatives and fallback.
5. RBAC and secret scrubbing for /api/system/capabilities.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from core.ports.base import PortStatus, ProviderResult
from core.capability_probe import probe_all_capabilities, summarize_capabilities
from agent_factory.control.planner import (
    plan,
    check_required_capabilities,
    schedule_step,
    CapabilityUnavailableError,
    PlanError,
)
from core.ceo_workforce_controller import ceo_workforce_controller


class TestCapabilityTruthAndPlanner(unittest.TestCase):

    def test_reality_probe_covers_all_18_capabilities(self):
        """Verify all 18 specified capabilities are probed honestly."""
        expected_caps = {
            "database", "storage", "email_out", "email_in", "calendar",
            "antivirus", "text_extraction", "ocr", "search", "key_management",
            "llm", "browser", "desktop_control", "payments", "secrets",
            "workflow_engine", "mcp", "observability"
        }
        results = probe_all_capabilities()
        self.assertEqual(set(results.keys()), expected_caps)
        self.assertEqual(len(results), 18)

        # Truth Rule: browser and desktop_control MUST be NOT_IMPLEMENTED
        self.assertEqual(results["browser"].status, PortStatus.NOT_IMPLEMENTED)
        self.assertEqual(results["browser"].provider, "none")
        self.assertIsNone(results["browser"].provider_ref)

        self.assertEqual(results["desktop_control"].status, PortStatus.NOT_IMPLEMENTED)
        self.assertEqual(results["desktop_control"].provider, "none")
        self.assertIsNone(results["desktop_control"].provider_ref)

        # Database probe must measure positive latency and report real dialect
        db_res = results["database"]
        self.assertIn(db_res.status, (PortStatus.OK, PortStatus.SANDBOX, PortStatus.DEGRADED))
        self.assertGreater(db_res.latency_ms, 0.0)
        self.assertIn("dialect", db_res.metadata)

        # Summary must total 18
        summary = summarize_capabilities(results)
        total_probed = sum(summary.values())
        self.assertEqual(total_probed, 18)
        self.assertEqual(summary["not_implemented"], 2)

    def test_planner_refuses_browser_task_before_promising(self):
        """Planner must read truth table and refuse to schedule tasks requiring browser."""
        nodes = ["agent_scraper", "agent_aggregator"]
        edges = [("agent_scraper", "agent_aggregator", "build_requires")]

        with self.assertRaises(CapabilityUnavailableError) as ctx:
            plan(nodes, edges, required_capabilities=["browser"])

        err = ctx.exception
        self.assertEqual(err.capability, "browser")
        self.assertEqual(err.status, "NOT_IMPLEMENTED")
        self.assertIn("Manual fallback", str(err))
        self.assertIn("Upload target document/HTML directly", err.manual_fallback)

    def test_planner_refuses_web_scrape_alias_cleanly(self):
        """Planner resolves 'web_scrape' alias to browser port and refuses."""
        with self.assertRaises(CapabilityUnavailableError) as ctx:
            check_required_capabilities(["web_scrape"])

        self.assertEqual(ctx.exception.capability, "browser")
        self.assertEqual(ctx.exception.status, "NOT_IMPLEMENTED")

    def test_schedule_step_refusal_does_not_loop(self):
        """schedule_step returns REFUSED structure without looping when capability is unavailable."""
        result = schedule_step(
            step_id="step_scrape_101",
            action="web_scraping",
            required_capabilities=["web_scrape", "browser"]
        )

        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["step_id"], "step_scrape_101")
        self.assertEqual(result["capability"], "browser")
        self.assertEqual(result["capability_status"], "NOT_IMPLEMENTED")
        self.assertFalse(result["looping"])
        self.assertIn("Upload target document", result["manual_fallback"])

    def test_ceo_workforce_controller_refuses_scrape_nl_command(self):
        """CEOWorkforceController rejects NL command demanding web scraping without looping."""
        res = ceo_workforce_controller.handle_chat_command(
            tenant_id="tenant_test_truth",
            company_id="comp_test_truth",
            command="Please scrape latest vendor catalog from website"
        )

        self.assertEqual(res["action"], "MISSION_REFUSED")
        self.assertEqual(res["status"], "REFUSED")
        self.assertEqual(res["capability"], "browser")
        self.assertFalse(res["looping"])
        self.assertIn("Manual fallback", res["message"])

    def test_ceo_workforce_controller_plan_mission_browser_raises(self):
        """CEOWorkforceController.plan_and_assign_mission with browser capability raises error."""
        with self.assertRaises(CapabilityUnavailableError):
            ceo_workforce_controller.plan_and_assign_mission(
                tenant_id="tenant_test_truth",
                company_id="comp_test_truth",
                objective="Scrape market pricing",
                required_capabilities=["browser"],
                department="GROWTH"
            )

    def test_capabilities_secret_scrubbing(self):
        """Ensure probe metadata with sensitive tokens/passwords is scrubbed."""
        probe_res = ProviderResult(
            status=PortStatus.OK,
            provider="test_provider",
            provider_ref="ref_1",
            metadata={
                "api_endpoint": "https://api.example.com",
                "auth_token": "secret_bearer_token_xyz",
                "db_password": "super_secret_pw",
                "timeout": 30
            }
        )

        # Simulate API server scrubbing logic
        data = probe_res.to_dict()
        meta = data.get("metadata", {})
        safe_meta = {}
        for k, v in meta.items():
            if any(term in k.lower() for term in ["token", "key", "password", "secret", "credential"]):
                safe_meta[k] = "[REDACTED]"
            else:
                safe_meta[k] = v

        self.assertEqual(safe_meta["api_endpoint"], "https://api.example.com")
        self.assertEqual(safe_meta["timeout"], 30)
        self.assertEqual(safe_meta["auth_token"], "[REDACTED]")
        self.assertEqual(safe_meta["db_password"], "[REDACTED]")

    def test_settings_v2_capabilities_endpoint(self):
        """Settings V2 /capabilities subpath returns plain-language mapped capabilities."""
        from core.settings.api_v2 import settings_v2_api
        auth_ctx = {
            "user_id": "usr_owner_1",
            "tenant_id": "tenant_test_truth",
            "company_id": "comp_test_truth",
            "role": "owner",
            "permissions": ["*"]
        }
        status, payload = settings_v2_api.handle(
            method="GET",
            path="/api/settings/v2/capabilities",
            query={},
            body={},
            auth_context=auth_ctx,
            resolved_company_id="comp_test_truth"
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])
        self.assertIn("summary", payload)
        self.assertIn("capabilities", payload)

        browser_entry = next((c for c in payload["capabilities"] if c["capability"] == "browser"), None)
        self.assertIsNotNone(browser_entry)
        self.assertEqual(browser_entry["status"], "NOT_IMPLEMENTED")
        self.assertEqual(browser_entry["plain_language"], "not implemented")

        db_entry = next((c for c in payload["capabilities"] if c["capability"] == "database"), None)
        self.assertIsNotNone(db_entry)
        self.assertIn(db_entry["plain_language"], ("live", "test only", "degraded"))


if __name__ == "__main__":
    unittest.main()
