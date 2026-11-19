"""
URA Assistant Stage 2 service tests.

Covers the deterministic tool planner, @agent routing, company-scope permission
gate, confirmation gate, memory lifecycle and honest stream events.  No network
model call is required: these paths are deterministic and the tests assert that
nothing executes without an explicit confirmation.
"""

import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import configure_isolated_test_db
from core.db import db

TEST_DB = os.path.join(tempfile.mkdtemp(prefix="ura_asst_"), "assistant.db")
configure_isolated_test_db(TEST_DB)

import time  # noqa: E402


def seed_company(tenant_id: str, company_id: str, approve: bool = True):
    now = time.time()
    with db.get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (tenant_id, "URA Test Tenant", now),
            )
        except Exception:
            pass
        try:
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, created_at) "
                "VALUES (?, ?, 'Kora Test', 'Hospitality', 'EXISTING', ?)",
                (company_id, tenant_id, now),
            )
        except Exception:
            pass
        try:
            conn.execute(
                "INSERT INTO approvals (request_id, tenant_id, company_id, agent_id, action_desc, reason, "
                "risk_level, consequence, status, requested_at) VALUES (?, ?, ?, 'usr_owner', ?, 'test', "
                "'LOW', 'test', ?, ?)",
                (
                    f"apr_{company_id}",
                    tenant_id,
                    company_id,
                    "URA Assistant access to company data (kind: cowork)",
                    "APPROVED" if approve else "PENDING",
                    now,
                ),
            )
        except Exception:
            pass
        conn.commit()

from core.ura_assistant_service import (  # noqa: E402
    AGENT_DIRECTORY,
    TOOL_SPECS,
    URAAssistantService,
    _normalise_target,
    _plan_tool,
)


class TestPlanner(unittest.TestCase):
    def test_screen_targets(self):
        self.assertEqual(_normalise_target("/reports"), "reports")
        self.assertEqual(_normalise_target("AI CEO"), "ceo-records")
        self.assertEqual(_normalise_target("co-worker"), "coworker")
        self.assertIsNone(_normalise_target("not-a-screen"))

    def test_navigation_beats_query(self):
        self.assertEqual(_plan_tool("open reports", "overview")[0], "navigate")
        self.assertEqual(_plan_tool("how many approvals are waiting?", "overview")[0], "query_data")

    def test_mutating_tools_are_mapped(self):
        self.assertEqual(_plan_tool("delegate this to the team", "overview")[0], "delegate_task")
        self.assertEqual(_plan_tool("run command uptime", "terminal")[0], "run_terminal")
        self.assertEqual(_plan_tool("generate a weekly report", "overview")[0], "generate_report")
        self.assertEqual(_plan_tool("connect gmail", "integrations")[0], "connect_integration")
        self.assertEqual(_plan_tool("install agent for procurement", "agent-factory")[0], "install_agent")

    def test_approval_decision_requires_an_id(self):
        name, args = _plan_tool("approve apr_1234abcd", "approvals")
        self.assertEqual(name, "decide_approval")
        self.assertEqual(args["request_id"], "apr_1234abcd")
        self.assertTrue(args["approved"])


class TestAgentRouting(unittest.TestCase):
    def setUp(self):
        self.svc = URAAssistantService("tnt_ura_test")

    def test_each_role_resolves(self):
        for role in AGENT_DIRECTORY:
            resolved, cleaned = self.svc.resolve_agent(f"@{role} what matters today?")
            self.assertEqual(resolved, role)
            self.assertEqual(cleaned, "what matters today?")

    def test_unknown_prefix_is_kept_as_text(self):
        role, cleaned = self.svc.resolve_agent("@nobody hello")
        self.assertIsNone(role)
        self.assertEqual(cleaned, "@nobody hello")


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.svc = URAAssistantService("tnt_ura_test")

    def test_remember_list_forget(self):
        saved = self.svc.remember("Prefers Monday reports", "usr_mem", scope="PERSONAL")
        self.assertTrue(saved["success"])
        memories = self.svc.list_memories("usr_mem", scope="PERSONAL")
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["content"], "Prefers Monday reports")
        other = self.svc.list_memories("usr_other", scope="PERSONAL")
        self.assertEqual(other, [])
        result = self.svc.forget(saved["memory"]["memory_id"], "usr_mem")
        self.assertTrue(result["success"])
        self.assertEqual(self.svc.list_memories("usr_mem", scope="PERSONAL"), [])

    def test_memory_search_and_clear(self):
        self.svc.remember("Quarterly board pack", "usr_clear", scope="PERSONAL")
        self.svc.remember("Hiring plan", "usr_clear", scope="PERSONAL")
        found = self.svc.list_memories("usr_clear", scope="PERSONAL", query="board")
        self.assertEqual(len(found), 1)
        cleared = self.svc.clear_memories("usr_clear", scope="PERSONAL")
        self.assertTrue(cleared["success"])
        self.assertEqual(self.svc.list_memories("usr_clear", scope="PERSONAL"), [])


class TestStreamContract(unittest.TestCase):
    def setUp(self):
        self.svc = URAAssistantService("tnt_ura_test")
        seed_company("tnt_ura_test", "comp_ura_test", approve=True)

    def _events(self, **kwargs):
        return list(self.svc.stream(user_id="usr_stream", workspace_mode="PERSONAL", **kwargs))

    def test_personal_navigation_streams_tool_then_done(self):
        events = self._events(prompt="open reports", page_context={"page": "overview"})
        types = [e["type"] for e in events]
        self.assertEqual(types[0], "context")
        self.assertIn("tool", types)
        self.assertIn("card", types)
        self.assertEqual(types[-1], "done")
        card = next(e["card"] for e in events if e["type"] == "card")
        self.assertEqual(card["type"], "NAVIGATE")
        self.assertEqual(card["path"], "/reports")

    def test_company_scope_is_locked_without_cowork_approval(self):
        events = list(self.svc.stream(
            prompt="list approvals",
            user_id="usr_stream",
            workspace_mode="COMPANY",
            company_id="comp_missing",
            page_context={"page": "approvals"},
        ))
        types = [e["type"] for e in events]
        self.assertIn("permission", types)
        self.assertNotIn("tool", types)
        self.assertEqual(types[-1], "done")
        self.assertEqual(events[-1]["routed_to"], "PERMISSION_REQUIRED")

    def test_mutating_tool_waits_for_confirmation(self):
        events = list(self.svc.stream(
            prompt="delegate this to the team",
            user_id="usr_stream",
            workspace_mode="COMPANY",
            company_id="comp_ura_test",
            page_context={"page": "missions"},
        ))
        types = [e["type"] for e in events]
        self.assertIn("confirm", types)
        confirm = next(e for e in events if e["type"] == "confirm")
        self.assertEqual(confirm["tool"], "delegate_task")
        self.assertEqual(confirm["risk"], "MEDIUM")
        self.assertEqual(types[-1], "done")
        self.assertEqual(events[-1]["routed_to"], "CONFIRMATION_REQUIRED")
        # The confirmation preview must say it has not run.
        answer = "".join(e.get("delta", "") for e in events if e["type"] == "answer")
        self.assertIn("not executed", answer)

    def test_approved_cowork_unlocks_company_scope(self):
        events = list(self.svc.stream(
            prompt="how many approvals are waiting?",
            user_id="usr_stream",
            workspace_mode="COMPANY",
            company_id="comp_ura_test",
            page_context={"page": "approvals"},
        ))
        types = [e["type"] for e in events]
        self.assertIn("tool", types)
        self.assertNotIn("permission", types)
        self.assertEqual(types[-1], "done")
        self.assertNotEqual(events[-1]["routed_to"], "PERMISSION_REQUIRED")

    def test_pending_cowork_request_still_locks_company_scope(self):
        seed_company("tnt_ura_test", "comp_pending", approve=False)
        events = list(self.svc.stream(
            prompt="how many approvals are waiting?",
            user_id="usr_stream",
            workspace_mode="COMPANY",
            company_id="comp_pending",
            page_context={"page": "approvals"},
        ))
        permission = next(e for e in events if e["type"] == "permission")
        self.assertEqual(permission["state"], "PENDING")
        self.assertEqual(events[-1]["routed_to"], "PERMISSION_REQUIRED")

    def test_agent_prefix_sets_agent_event(self):
        events = self._events(prompt="@CFO how is cash?", page_context={"page": "finance"})
        agent = next(e for e in events if e["type"] == "agent")
        self.assertEqual(agent["role"], "CFO")
        self.assertEqual(agent["label"], "AI CFO")
        self.assertEqual(events[0]["context"]["agent"], "CFO")


class TestToolGating(unittest.TestCase):
    def setUp(self):
        self.svc = URAAssistantService("tnt_ura_test")

    def test_company_tool_blocked_in_personal_scope(self):
        result = self.svc.execute_tool(
            "query_data", {"query": "approvals"}, user_id="usr_gate", scope="PERSONAL"
        )
        self.assertFalse(result["ok"])
        self.assertIn("Company scope", result["summary"])

    def test_unknown_tool_is_refused(self):
        result = self.svc.execute_tool("mark_bank_payment", {}, user_id="usr_gate", scope="COMPANY", company_id="c1")
        self.assertFalse(result["ok"])

    def test_navigate_is_read_only(self):
        result = self.svc.execute_tool(
            "navigate", {"target": "finance"}, user_id="usr_gate", scope="PERSONAL"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["card"]["path"], "/finance")

    def test_tool_specs_cover_required_typed_tools(self):
        required = {
            "navigate", "query_data", "delegate_task", "decide_approval",
            "change_setting", "run_security_scan", "generate_report",
            "install_agent", "connect_integration", "run_terminal",
        }
        self.assertTrue(required.issubset(TOOL_SPECS.keys()))
        for name, spec in TOOL_SPECS.items():
            self.assertIn("parameters", spec, name)
            self.assertIn("mutating", spec, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
