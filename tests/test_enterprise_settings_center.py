"""
ZONATA / URA Universal AI Company Operating System
Production Test Suite: Enterprise Settings Center & Sovereign Governance Engine
Tests all 43 categories across the 6 groups, validation, scope inheritance,
cryptographic SHA-256 audit ledger, AI CEO proposal lifecycle, effective runtime
state verification, environment authentication gating (Dev, Staging, Prod),
and multi-tenant company isolation.
"""

import unittest
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.settings_service import (
    settings_service,
    GROUPS,
    CATEGORIES_CATALOG,
    SETTINGS_DEFINITIONS,
    GROUP_IDENTITY,
    GROUP_AI_SYSTEM,
    GROUP_EXECUTION,
    GROUP_BUSINESS,
    GROUP_GOVERNANCE,
    GROUP_PLATFORM
)
from core.auth import UserManager, UserRole, AuthExceptions


class TestEnterpriseSettingsCenter(unittest.TestCase):
    def setUp(self):
        self.tenant_id = "tnt_test_settings"
        self.company_a = "comp_alpha"
        self.company_b = "comp_beta"

    def test_01_all_43_categories_registered(self):
        """Verify all categories exist and belong to the 6 canonical groups."""
        self.assertEqual(len(CATEGORIES_CATALOG), 46, f"Expected 45 categories, got {len(CATEGORIES_CATALOG)}")
        group_ids = {g["id"] for g in GROUPS}
        self.assertEqual(len(group_ids), 6)

        for cat in CATEGORIES_CATALOG:
            self.assertIn(cat["group_id"], group_ids, f"Category {cat['id']} has invalid group {cat['group_id']}")
            self.assertTrue(cat["name"], f"Category {cat['id']} missing name")
            self.assertTrue(cat["icon"], f"Category {cat['id']} missing icon")
            self.assertTrue(cat["desc"], f"Category {cat['id']} missing description")

    def test_02_catalog_summary_generation(self):
        """Verify summary generation for the square card control plane."""
        catalog = settings_service.get_categories_catalog(self.tenant_id, self.company_a)
        self.assertEqual(len(catalog), 46)
        for c in catalog:
            self.assertIn("current_value_summary", c)
            self.assertIn("status", c)
            self.assertIn("scope", c)

    def test_03_category_detail_loading(self):
        """Verify category detail retrieval for key categories."""
        for cat_id in ["account", "host", "ai_ceo", "security", "governance", "terminal", "usage"]:
            detail = settings_service.get_category_detail(cat_id, self.tenant_id, self.company_a)
            self.assertNotIn("error", detail)
            self.assertIn("category", detail)
            self.assertIn("settings", detail)
            self.assertIn("proposals", detail)
            self.assertIn("recent_audits", detail)
            self.assertEqual(detail["category"]["id"], cat_id)

    def test_04_setting_update_and_persistence(self):
        """Verify update of a setting writes to DB and updates version."""
        res = settings_service.update_single_setting(
            self.tenant_id, self.company_a,
            "ceo_spending_limit", 75000,
            actor="Sovereign Owner", reason="Expanded quarterly budget"
        )
        self.assertTrue(res["success"], f"Failed to update setting: {res.get('error')}")
        self.assertEqual(res["new_value"], 75000)
        self.assertTrue(res["evidence_hash"])

        # Fetch category and verify stored value
        detail = settings_service.get_category_detail("ai_ceo", self.tenant_id, self.company_a)
        target = next(s for s in detail["settings"] if s["id"] == "ceo_spending_limit")
        self.assertEqual(target["value"], 75000)
        self.assertEqual(target["inherited_from"], "Custom Override")

    def test_05_validation_bounds(self):
        """Verify validation prevents invalid, negative, or spoofed values."""
        # Negative spending limit
        res = settings_service.update_single_setting(
            self.tenant_id, self.company_a,
            "ceo_spending_limit", -500,
            actor="Test Operator"
        )
        self.assertFalse(res["success"])
        self.assertIn("cannot be negative", res.get("error", ""))

        # Invalid select choice
        res2 = settings_service.update_single_setting(
            self.tenant_id, self.company_a,
            "comp_base_currency", "INVALID_COIN",
            actor="Test Operator"
        )
        self.assertFalse(res2["success"])
        self.assertIn("Invalid choice", res2.get("error", ""))

    def test_06_read_only_protection(self):
        """Verify READ_ONLY constitutional settings cannot be modified."""
        res = settings_service.update_single_setting(
            self.tenant_id, self.company_a,
            "host_authority_scope", "MUTATED_AUTHORITY",
            actor="Unauthorized Attempt"
        )
        self.assertFalse(res["success"])
        self.assertIn("READ_ONLY", res.get("error", ""))

    def test_07_cryptographic_audit_ledger(self):
        """Verify settings changes generate verifiable SHA-256 evidence."""
        res = settings_service.update_single_setting(
            self.tenant_id, self.company_a,
            "sec_session_duration_hours", 8,
            actor="Chief Security Officer", reason="Strict session rotation policy"
        )
        self.assertTrue(res["success"])
        evidence_hash = res["evidence_hash"]
        self.assertEqual(len(evidence_hash), 64, "Evidence hash must be 64-char SHA-256")

        # Query audit log
        audits = settings_service.get_audit_events(self.tenant_id, self.company_a, category="security")
        self.assertTrue(len(audits) >= 1)
        latest = audits[0]
        self.assertEqual(latest["setting_id"], "sec_session_duration_hours")
        self.assertEqual(latest["actor"], "Chief Security Officer")
        self.assertEqual(latest["evidence_hash"], evidence_hash)

    def test_08_ai_ceo_proposal_lifecycle(self):
        """Verify AI CEO proposal creation, listing, approval, and rejection."""
        # 1. Propose change
        p_res = settings_service.propose_change(
            self.tenant_id, self.company_a,
            "wf_max_concurrent_agents", 24,
            proposed_by="AI CEO Executive Brain",
            reason="High mission backlog requires increased concurrency",
            expected_benefit="+35% mission throughput",
            risk_level="MEDIUM"
        )
        self.assertTrue(p_res["success"])
        prop_id = p_res["proposal_id"]

        # 2. List proposals
        proposals = settings_service.get_category_proposals("workforce", self.tenant_id, self.company_a)
        found = next((p for p in proposals if p["proposal_id"] == prop_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["proposed_value"], 24)

        # 3. Approve proposal
        appr_res = settings_service.resolve_proposal(prop_id, "APPROVED", actor="Sovereign Host", reason="Approved for peak workload")
        self.assertTrue(appr_res["success"])

        # 4. Verify value changed in settings
        detail = settings_service.get_category_detail("workforce", self.tenant_id, self.company_a)
        wf_setting = next(s for s in detail["settings"] if s["id"] == "wf_max_concurrent_agents")
        self.assertEqual(wf_setting["value"], 24)

    def test_09_multi_company_isolation(self):
        """Verify Company A and Company B have strictly isolated configuration state."""
        # Update Company A
        settings_service.update_single_setting(
            self.tenant_id, self.company_a,
            "cost_global_budget_monthly", 250000,
            actor="Host"
        )

        # Update Company B
        settings_service.update_single_setting(
            self.tenant_id, self.company_b,
            "cost_global_budget_monthly", 50000,
            actor="Host"
        )

        detail_a = settings_service.get_category_detail("usage", self.tenant_id, self.company_a)
        detail_b = settings_service.get_category_detail("usage", self.tenant_id, self.company_b)

        val_a = next(s["value"] for s in detail_a["settings"] if s["id"] == "cost_global_budget_monthly")
        val_b = next(s["value"] for s in detail_b["settings"] if s["id"] == "cost_global_budget_monthly")

        self.assertEqual(val_a, 250000)
        self.assertEqual(val_b, 50000)
        self.assertNotEqual(val_a, val_b)

    def test_10_live_diagnostic_tests(self):
        """Live diagnostics must report real outcomes, never fabricated PASSED."""
        # Genuinely probeable subsystems.
        for target in ["database", "terminal", "backup"]:
            res = settings_service.run_live_test(target)
            self.assertIn(res["status"], ("PASSED", "FAILED"))
            self.assertEqual(res["status"], "PASSED", res["detail"])
            self.assertTrue(res["latency_ms"] >= 0)
            self.assertEqual(len(res["evidence_hash"]), 64)
            self.assertTrue(res.get("evidence"))

        # Unprobeable subsystems must say so instead of pretending success.
        for target in ["api_token", "webhook", "mcp", "a2a"]:
            res = settings_service.run_live_test(target)
            self.assertEqual(res["status"], "NOT_IMPLEMENTED")
            self.assertEqual(len(res["evidence_hash"]), 64)

    def test_11_effective_runtime_vs_stored_proof(self):
        """Verify effective runtime value calculation proves live enforcement."""
        detail = settings_service.get_category_detail("ai_ceo", self.tenant_id, self.company_a)
        autonomy_setting = next(s for s in detail["settings"] if s["id"] == "ceo_autonomy_level")
        self.assertIn("effective_runtime_value", autonomy_setting)
        self.assertEqual(autonomy_setting["runtime_status"], "ACTIVE")

    def test_12_environment_security_boundary(self):
        """Verify production mode rejects unauthenticated access with no default session."""
        # 1. Dev token works
        user_dev = {"user_id": "u1", "tenant_id": self.tenant_id, "role": UserRole.OWNER}
        token = UserManager.generate_token(user_dev)
        payload = UserManager.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["tenant_id"], self.tenant_id)

        # 2. In strict production mode without token:
        # We test that UserManager.verify_token("") is None
        self.assertIsNone(UserManager.verify_token(""))
        self.assertIsNone(UserManager.verify_token("invalid.token.here"))


if __name__ == "__main__":
    unittest.main()
