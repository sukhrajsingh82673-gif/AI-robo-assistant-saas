"""
URA Assistant Stage 4 tests — meetings, calendar, transcription and governance.

Every result here is checked against the real tables: a brief counts what is
stored, notes are transcript entries, the summary is compiled from the record,
and an action item becomes a governed Co-worker task or an approval request.
Transcription is exercised with the labelled sample adapter only; nothing opens
a microphone and no audio exists in this build.
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import configure_isolated_test_db, db

TEST_DB = os.path.join(tempfile.mkdtemp(prefix="ura_meetings_"), "assistant.db")
configure_isolated_test_db(TEST_DB)

from core.settings_service import settings_service  # noqa: E402
from core.ura_assistant_meetings import (  # noqa: E402
    AssistantMeetingService,
    NoTranscriptionAdapter,
    SampleTranscriptionAdapter,
    calendar_status,
    get_transcription_adapter,
    recording_notice,
    transcription_status,
)
from core.ura_assistant_service import URAAssistantService, _plan_tool  # noqa: E402

TENANT = "tnt_stage4"
COMPANY = "comp_stage4"
COWORK_ACTION = "URA Assistant Company scope (kind: cowork)"


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
                "VALUES (?, 'Stage 4', 'ENTERPRISE', 'ACTIVE', ?)",
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
            "VALUES ('apr_cowork4', ?, ?, 'AI_CEO', ?, 'Owner granted scope', 'LOW', "
            "'Read company data', 'APPROVED', ?)",
            (TENANT, COMPANY, COWORK_ACTION, now),
        )
        conn.execute(
            "INSERT INTO approvals (request_id, tenant_id, company_id, agent_id, action_desc, "
            "reason, risk_level, consequence, status, requested_at) "
            "VALUES ('apr_pending4', ?, ?, 'AI_CFO', 'Approve the Q4 retreat budget', "
            "'Finance needs a decision', 'HIGH', 'Spend approval', 'PENDING', ?)",
            (TENANT, COMPANY, now),
        )
        conn.execute(
            "INSERT INTO missions (mission_id, company_id, tenant_id, title, owner_agent, "
            "department, target_outcome, status, progress, started_at) "
            "VALUES ('mis_stage4', ?, ?, 'Lift RevPAR by 5%', 'AI COO', 'Operations', "
            "'+5% RevPAR', 'EXECUTE', 40, ?)",
            (COMPANY, TENANT, now),
        )
        conn.commit()


def set_recording(enabled: bool) -> None:
    res = settings_service.update_single_setting(
        TENANT, COMPANY, "assistant_meeting_recording_notice", enabled,
        actor="test", actor_role="OWNER",
    )
    assert res.get("success"), res


def sample_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("URA_ASSISTANT_TRANSCRIPTION")}
    env["URA_ASSISTANT_TRANSCRIPTION_PROVIDER"] = "sample"
    return patch.dict(os.environ, env, clear=True)


def no_transcription_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("URA_ASSISTANT_TRANSCRIPTION")}
    env.pop("URA_ASSISTANT_TRANSCRIPTION_PROVIDER", None)
    return patch.dict(os.environ, env, clear=True)


class TestAdapters(unittest.TestCase):
    def test_calendar_is_not_connected_by_default(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("ZONATA_GOOGLE_CALENDAR")}
        with patch.dict(os.environ, env, clear=True):
            status = calendar_status()
        self.assertFalse(status["configured"])
        self.assertEqual(status["provider"], "none")
        self.assertIn("not connected", status["label"].lower())

    def test_transcription_defaults_to_not_connected(self):
        with no_transcription_env():
            self.assertIsInstance(get_transcription_adapter(), NoTranscriptionAdapter)
            status = transcription_status()
        self.assertFalse(status["configured"])
        self.assertEqual(status["provider"], "none")

    def test_sample_transcription_is_explicit_and_labelled(self):
        with sample_env():
            adapter = get_transcription_adapter()
            self.assertIsInstance(adapter, SampleTranscriptionAdapter)
            self.assertTrue(adapter.is_sample)
            lines = adapter.transcribe({"meeting_id": "m_sample"})
        self.assertTrue(lines)
        self.assertTrue(all(line["sample"] is True for line in lines))
        self.assertTrue(all("Sample transcript line" in line["text"] for line in lines))
        self.assertTrue(any("no audio was captured" in line["text"] for line in lines))

    def test_recording_notice_reflects_the_setting(self):
        set_recording(True)
        enabled = recording_notice(TENANT, COMPANY)
        self.assertTrue(enabled["enabled"])
        self.assertTrue(enabled["announcement"])
        set_recording(False)
        disabled = recording_notice(TENANT, COMPANY)
        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["announcement"], "")
        set_recording(True)


class TestBriefAndLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()
        cls.service = AssistantMeetingService(TENANT)

    def test_brief_counts_live_company_rows(self):
        brief = self.service.brief(COMPANY)
        self.assertEqual(brief["company"]["name"], "Kora Living")
        self.assertEqual(len(brief["pending_approvals"]), 1)
        self.assertEqual(brief["pending_approvals"][0]["request_id"], "apr_pending4")
        self.assertEqual(len(brief["missions"]), 1)
        self.assertIn("Lift RevPAR", brief["summary"])
        self.assertTrue(brief["agenda"])
        self.assertIn("Approve the Q4 retreat budget", brief["agenda"][0])
        self.assertNotIn("fabricated", brief["summary"].lower())

    def test_brief_for_an_empty_company_invents_nothing(self):
        brief = self.service.brief("comp_missing4")
        self.assertEqual(brief["pending_approvals"], [])
        self.assertEqual(brief["missions"], [])
        self.assertIn("No pending approvals", brief["agenda"][0])

    def test_library_searches_titles_and_transcripts(self):
        svc = self.service._meeting_service()
        meeting = svc.get_or_create_active_meeting(COMPANY, "usr_owner4")
        svc.add_transcript_entry(
            meeting_id=meeting["meeting_id"], company_id=COMPANY,
            speaker="HOST", mode="NOTE", message="We agreed the retreat moves to Goa.",
        )
        found = self.service.library(COMPANY, "retreat")
        self.assertGreaterEqual(found["count"], 1)
        row = next(m for m in found["meetings"] if m["meeting_id"] == meeting["meeting_id"])
        self.assertTrue(row["matches"])
        self.assertIn("retreat", row["matches"][0]["snippet"].lower())

    def test_library_with_no_match_returns_empty(self):
        found = self.service.library(COMPANY, "zzz-no-such-word")
        self.assertEqual(found["count"], 0)


class TestLiveMeeting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()
        cls.service = AssistantMeetingService(TENANT)

    def test_listen_without_a_provider_records_nothing(self):
        with no_transcription_env():
            res = self.service.listen(COMPANY, "usr_owner4")
        self.assertFalse(res["success"])
        self.assertEqual(res["reason"], "TRANSCRIPTION_NOT_CONFIGURED")
        self.assertIn("did not open a microphone", res["message"])
        self.assertFalse(res["transcription"]["configured"])

    def test_listen_with_sample_provider_writes_announcement_and_segments(self):
        set_recording(True)
        with sample_env():
            res = self.service.listen(COMPANY, "usr_owner4")
        self.assertTrue(res["success"], res)
        self.assertTrue(res["sample"])
        self.assertEqual(len(res["segments"]), 4)
        self.assertTrue(all(segment["sample"] for segment in res["segments"]))
        transcripts = self.service._meeting_service().get_transcripts(res["meeting"]["meeting_id"])
        announcements = [
            t for t in transcripts if t.get("related_context") == "Recording announcement"
        ]
        self.assertEqual(len(announcements), 1)
        self.assertIn("sample", announcements[0]["message"].lower())

    def test_listen_is_idempotent_for_the_announcement(self):
        with sample_env():
            first = self.service.listen(COMPANY, "usr_owner4")
            second = self.service.listen(COMPANY, "usr_owner4")
        transcripts = self.service._meeting_service().get_transcripts(first["meeting"]["meeting_id"])
        announcements = [
            t for t in transcripts if t.get("related_context") == "Recording announcement"
        ]
        self.assertEqual(len(announcements), 1)
        self.assertTrue(second["success"])

    def test_note_is_stored_and_rejects_empty_text(self):
        with sample_env():
            live = self.service.listen(COMPANY, "usr_owner4")
        meeting_id = live["meeting"]["meeting_id"]
        saved = self.service.add_note(COMPANY, "Approve the retreat budget next.", meeting_id, "usr_owner4")
        self.assertTrue(saved["success"])
        self.assertEqual(saved["note"]["mode"], "NOTE")
        notes = self.service.notes(COMPANY, meeting_id)
        self.assertTrue(any("retreat budget" in n["message"] for n in notes["notes"]))
        empty = self.service.add_note(COMPANY, "   ", meeting_id, "usr_owner4")
        self.assertFalse(empty["success"])

    def test_summary_uses_the_stored_record(self):
        with sample_env():
            live = self.service.listen(COMPANY, "usr_owner4")
        meeting_id = live["meeting"]["meeting_id"]
        self.service.add_note(COMPANY, "Decision: keep the Goa retreat.", meeting_id, "usr_owner4")
        res = self.service.summarise(COMPANY, meeting_id, end_meeting=True, user_id="usr_owner4")
        self.assertTrue(res["success"], res)
        self.assertEqual(res["meeting"]["status"], "Ended")
        self.assertIn("keep the Goa retreat", res["summary"])
        self.assertIn("Transcript entries:", res["summary"])
        self.assertIsNotNone(res["minutes"], res.get("minutes_error"))
        self.assertIsNone(res["minutes_error"])

    def test_action_item_becomes_a_governed_task(self):
        with sample_env():
            live = self.service.listen(COMPANY, "usr_owner4")
        res = self.service.action_item(
            COMPANY, "Send the revised budget to finance", live["meeting"]["meeting_id"], "usr_owner4",
        )
        self.assertTrue(res["success"], res)
        self.assertEqual(res["kind"], "TASK")
        self.assertTrue(str(res["request"]["task_id"]).startswith("cwk_"))
        self.assertNotEqual(str(res["request"].get("status") or "").upper(), "COMPLETED")

    def test_action_item_can_require_approval(self):
        res = self.service.action_item(
            COMPANY, "Approve the retreat spend", None, "usr_owner4", requires_approval=True,
        )
        self.assertTrue(res["success"], res)
        self.assertEqual(res["kind"], "APPROVAL")
        request_id = res["request"]["request_id"]
        self.assertTrue(str(request_id).startswith("apr_"))
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT status, action_desc FROM approvals WHERE request_id = ?", (request_id,)
            ).fetchone()
        self.assertEqual(row["status"], "PENDING")
        self.assertIn("Meeting action", row["action_desc"])

    def test_action_item_rejects_an_empty_title(self):
        res = self.service.action_item(COMPANY, "  ", None, "usr_owner4")
        self.assertFalse(res["success"])


class TestAssistantTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_world()
        cls.service = URAAssistantService(TENANT)

    def test_planner_routes_meeting_requests(self):
        cases = {
            "prepare my next meeting": "meeting_brief",
            "meeting library": "meeting_library",
            "start listening": "meeting_listen",
            "meeting summary": "meeting_summary",
            "create an action item to call the bank": "meeting_action",
            "add a note that budget is approved": "meeting_note",
            "schedule a meeting about Q4": "schedule_meeting",
        }
        for prompt, expected in cases.items():
            tool, _ = _plan_tool(prompt, "overview")
            self.assertEqual(tool, expected, prompt)

    def test_tools_require_company_scope(self):
        res = self.service.execute_tool("meeting_brief", {}, user_id="usr_owner4", scope="PERSONAL")
        self.assertFalse(res["ok"])
        self.assertIn("Company scope", res["summary"])

    def test_brief_tool_returns_a_labelled_card(self):
        with sample_env():
            res = self.service.execute_tool(
                "meeting_brief", {}, user_id="usr_owner4", scope="COMPANY", company_id=COMPANY,
            )
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["card"]["type"], "MEETING_BRIEF")
        self.assertTrue(res["card"]["agenda"])
        self.assertTrue(res["citations"])

    def test_listen_tool_reports_transcription_honestly(self):
        with no_transcription_env():
            blocked = self.service.execute_tool(
                "meeting_listen", {}, user_id="usr_owner4", scope="COMPANY", company_id=COMPANY,
            )
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["card"]["type"], "MEETING_LISTEN_BLOCKED")
        self.assertIn("not connected", blocked["summary"].lower())
        with sample_env():
            live = self.service.execute_tool(
                "meeting_listen", {}, user_id="usr_owner4", scope="COMPANY", company_id=COMPANY,
            )
        self.assertTrue(live["ok"], live)
        self.assertEqual(live["card"]["type"], "MEETING_LIVE")
        self.assertTrue(live["card"]["sample"])
        self.assertIn("sample text, not captured audio", live["answer"])

    def test_schedule_tool_does_not_claim_a_booking(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("ZONATA_GOOGLE_CALENDAR")}
        with patch.dict(os.environ, env, clear=True):
            res = self.service.execute_tool(
                "schedule_meeting", {"prompt": "Q4 planning"},
                user_id="usr_owner4", scope="COMPANY", company_id=COMPANY,
            )
        self.assertFalse(res["ok"])
        self.assertEqual(res["card"]["type"], "MEETING_INVITE")
        self.assertEqual(res["card"]["status"], "BLOCKED")
        self.assertIsNone(res["card"]["google_meet_url"])
        self.assertIn("did not schedule", res["answer"].lower())

    def test_company_permission_uses_the_cowork_approval(self):
        granted = self.service.company_permission(COMPANY)
        self.assertTrue(granted["granted"], granted)
        missing = self.service.company_permission("comp_missing4")
        self.assertFalse(missing["granted"])

    def test_note_tool_is_gated_and_saves(self):
        with sample_env():
            self.service.execute_tool(
                "meeting_listen", {}, user_id="usr_owner4", scope="COMPANY", company_id=COMPANY,
            )
        res = self.service.execute_tool(
            "meeting_note", {"note": "Owner note from the tool."},
            user_id="usr_owner4", scope="COMPANY", company_id=COMPANY,
        )
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["card"]["type"], "MEETING_NOTE")
        personal = self.service.execute_tool(
            "meeting_note", {"note": "x"}, user_id="usr_owner4", scope="PERSONAL", company_id=COMPANY,
        )
        self.assertFalse(personal["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
