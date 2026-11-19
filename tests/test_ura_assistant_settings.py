"""
URA Assistant Stage 5 tests — assistant settings are real controls.

Every assistant setting under Settings → AI, Agents & Employees must be
enforced by code, carry a plain-language hint, a suggestion and the reason for
it, and actually change behaviour when it is switched.  These tests exercise the
four server-side gates (background work, confirmations, remembered turns,
meetings) and the registry metadata the Settings V2 console renders.
"""

import os
import sys
import tempfile
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import configure_isolated_test_db, db

TEST_DB = os.path.join(tempfile.mkdtemp(prefix="ura_settings_"), "assistant.db")
configure_isolated_test_db(TEST_DB)

from core.settings.registry import settings_registry  # noqa: E402
from core.settings.sections import section_for_category  # noqa: E402
from core.settings_service import settings_service  # noqa: E402
from core.ura_assistant_service import URAAssistantService  # noqa: E402

TENANT = "tnt_stage5"
COMPANY = "comp_stage5"
COWORK_ACTION = "URA Assistant Company scope (kind: cowork)"

ASSISTANT_KEYS = (
    "assistant_show_button",
    "assistant_open_as",
    "assistant_default_scope",
    "assistant_confirmations",
    "assistant_remember_conversations",
    "assistant_background_work",
    "assistant_meetings_enabled",
    "assistant_web_access",
    "assistant_web_allowlist",
    "assistant_web_blocklist",
    "assistant_meeting_recording_notice",
)

_SEEDED = {"done": False}


def seed_world() -> None:
    if _SEEDED["done"]:
        return
    _SEEDED["done"] = True
    now = time.time()
    with db.get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) "
                "VALUES (?, 'Stage 5', 'ENTERPRISE', 'ACTIVE', ?)",
                (TENANT, now),
            )
        except Exception:
            pass
        try:
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, created_at) "
                "VALUES (?, ?, 'Kora Living', 'Hospitality', 'EXISTING', ?)",
                (COMPANY, TENANT, now),
            )
        except Exception:
            pass
        conn.execute(
            "INSERT INTO approvals (request_id, tenant_id, company_id, agent_id, action_desc, "
            "reason, risk_level, consequence, status, requested_at) "
            "VALUES ('apr_cowork5', ?, ?, 'AI_CEO', ?, 'Owner granted scope', 'LOW', "
            "'Read company data', 'APPROVED', ?)",
            (TENANT, COMPANY, COWORK_ACTION, now),
        )
        conn.commit()


def set_setting(key: str, value) -> None:
    res = settings_service.update_single_setting(
        TENANT, COMPANY, key, value, actor="test", actor_role="OWNER"
    )
    assert res.get("success"), res


def reset_setting(key: str, value) -> None:
    set_setting(key, value)


def message_count(session_id: str) -> int:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM assistant_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return int(row["n"] if row else 0)


class TestAssistantRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()

    def test_assistant_category_is_in_ai_agents_employees(self):
        self.assertEqual(section_for_category("assistant"), "ai_agents_employees")

    def test_every_assistant_setting_is_live_and_enforced(self):
        for key in ASSISTANT_KEYS:
            definition = settings_registry.get(key)
            self.assertIsNotNone(definition, key)
            self.assertEqual(definition.category, "assistant", key)
            self.assertEqual(definition.section, "ai_agents_employees", key)
            self.assertEqual(definition.status.value, "live", key)
            self.assertTrue(definition.enforced_by, key)

    def test_every_assistant_setting_says_what_it_does(self):
        for key in ASSISTANT_KEYS:
            definition = settings_registry.get(key)
            self.assertTrue(definition.hint, f"{key} needs a plain-language hint")
            self.assertTrue(definition.reason, f"{key} needs a reason for its suggestion")
            self.assertIsNotNone(definition.suggestion, f"{key} needs a suggestion")

    def test_public_dict_carries_the_suggestion_metadata(self):
        payload = settings_registry.get("assistant_show_button").to_public_dict()
        self.assertEqual(payload["suggestion"], True)
        self.assertIn("launcher", payload["reason"].lower())
        self.assertTrue(payload["hint"])

    def test_defaults_are_the_safe_choices(self):
        expected = {
            "assistant_show_button": True,
            "assistant_open_as": "window",
            "assistant_default_scope": "PERSONAL",
            "assistant_confirmations": True,
            "assistant_remember_conversations": True,
            "assistant_background_work": True,
            "assistant_meetings_enabled": True,
            "assistant_web_access": "off",
            "assistant_meeting_recording_notice": True,
        }
        for key, value in expected.items():
            self.assertEqual(settings_registry.get(key).default, value, key)


class TestBackgroundWorkGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()
        cls.service = URAAssistantService(TENANT)

    def setUp(self):
        reset_setting("assistant_background_work", True)

    def tearDown(self):
        reset_setting("assistant_background_work", True)

    def test_background_job_is_refused_when_the_setting_is_off(self):
        set_setting("assistant_background_work", False)
        res = self.service.create_job(
            "Research every competitor in Goa", "usr_owner5",
            workspace_mode="PERSONAL", company_id=COMPANY,
        )
        self.assertFalse(res.get("success"), res)
        self.assertIn("Background work is turned off", res.get("error", ""))
        self.assertNotIn("job_id", res)

    def test_background_job_starts_when_the_setting_is_on(self):
        res = self.service.create_job(
            "List the open approvals", "usr_owner5",
            workspace_mode="PERSONAL", company_id=COMPANY,
        )
        self.assertTrue(res.get("success"), res)
        job = res.get("job") or {}
        self.assertTrue(str(job.get("job_id", "")).startswith("job_"), job)


class TestConfirmationGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()
        cls.service = URAAssistantService(TENANT)

    def setUp(self):
        reset_setting("assistant_confirmations", True)

    def tearDown(self):
        reset_setting("assistant_confirmations", True)

    def _events(self, prompt: str, session_id: str):
        return list(self.service.stream(
            prompt=prompt,
            user_id="usr_owner5",
            workspace_mode="COMPANY",
            company_id=COMPANY,
            page_context={"page": "overview"},
            session_id=session_id,
        ))

    def test_mutating_tool_asks_before_it_runs_when_confirmations_are_on(self):
        events = self._events("connect slack", "ses_confirm_on")
        types = [event["type"] for event in events]
        self.assertIn("confirm", types)
        self.assertFalse(any(event["type"] == "card" for event in events))
        confirm = next(event for event in events if event["type"] == "confirm")
        self.assertEqual(confirm["tool"], "connect_integration")
        answer = "".join(
            event.get("delta", "") for event in events if event["type"] == "answer"
        ).lower()
        self.assertIn("not executed", answer)

    def test_mutating_tool_runs_without_a_prompt_when_confirmations_are_off(self):
        set_setting("assistant_confirmations", False)
        events = self._events("connect slack", "ses_confirm_off")
        types = [event["type"] for event in events]
        self.assertNotIn("confirm", types)
        card = next(event for event in events if event["type"] == "card")
        self.assertEqual(card["card"]["type"], "INTEGRATION_HANDOFF")
        self.assertTrue(events[-1].get("ok"), events[-1])

    def test_terminal_always_asks_even_when_confirmations_are_off(self):
        set_setting("assistant_confirmations", False)
        events = self._events("run command echo hello", "ses_terminal_always")
        confirm = next(event for event in events if event["type"] == "confirm")
        self.assertEqual(confirm["tool"], "run_terminal")
        self.assertEqual(confirm["risk"], "HIGH")


class TestRememberGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()
        cls.service = URAAssistantService(TENANT)

    def setUp(self):
        reset_setting("assistant_remember_conversations", True)

    def tearDown(self):
        reset_setting("assistant_remember_conversations", True)

    def _run(self, session_id: str):
        return list(self.service.stream(
            prompt="look up approvals",
            user_id="usr_owner5",
            workspace_mode="COMPANY",
            company_id=COMPANY,
            page_context={"page": "overview"},
            session_id=session_id,
        ))

    def test_turns_are_stored_when_remembering_is_on(self):
        events = self._run("ses_remember_on")
        self.assertEqual(events[-1]["type"], "done")
        self.assertGreaterEqual(message_count("ses_remember_on"), 2)

    def test_no_turns_are_stored_when_remembering_is_off(self):
        set_setting("assistant_remember_conversations", False)
        events = self._run("ses_remember_off")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(message_count("ses_remember_off"), 0)


class TestMeetingsGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()

    def setUp(self):
        reset_setting("assistant_meetings_enabled", True)

    def tearDown(self):
        reset_setting("assistant_meetings_enabled", True)

    def test_meetings_are_allowed_with_the_cowork_approval(self):
        from api_server import _ura_meeting_access

        allowed, message, code = _ura_meeting_access(TENANT, COMPANY)
        self.assertTrue(allowed, message)
        self.assertEqual(code, "")

    def test_meetings_are_disabled_by_the_setting(self):
        from api_server import _ura_meeting_access

        set_setting("assistant_meetings_enabled", False)
        allowed, message, code = _ura_meeting_access(TENANT, COMPANY)
        self.assertFalse(allowed)
        self.assertEqual(code, "MEETINGS_DISABLED")
        self.assertIn("turned off", message.lower())

    def test_missing_scope_still_asks_for_permission(self):
        from api_server import _ura_meeting_access

        allowed, message, code = _ura_meeting_access(TENANT, "comp_missing5")
        self.assertFalse(allowed)
        self.assertEqual(code, "PERMISSION_REQUIRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
