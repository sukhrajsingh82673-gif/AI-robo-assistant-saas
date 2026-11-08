"""
ZONATA Universal AI Operating System — Assistant & AI CEO Gateway Integration Test Suite
Verifies:
1. Context Classification (Personal, Company, Mixed, Document, Meeting, Retrieval, Application Change, Ambiguity)
2. Personal Request Isolation (strict private boundary, zero company ledger contamination)
3. Company Request AI CEO Delegation (delegation is never reported as verified completion)
4. Centralized Native Document Production (PDF, DOCX, XLSX, PPTX, CSV with real SHA-256)
5. Intelligent File Search & Retrieval (strict per-user and per-company isolation)
6. Meeting Scheduling (provider-confirmed only; no fabricated links or dial-ins)
7. Conversation persistence and ambiguity arbitration
8. Coworker lifecycle honesty (no auto-completion without an executor)
"""

import unittest
import os
import sys
import time
import json
import hashlib
import tempfile
import urllib.request
import urllib.parse
from typing import Dict, Any

# Ensure project root is in python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import configure_isolated_test_db, db
from core.assistant_service import FloatingAssistantService, AssistantContextClassifier, IntentCategory
from core.document_generator import document_generator, DocumentFormat, StorageBoundary, DocumentCategory
from core.meeting_service import AiCeoMeetingService
from core.calendar_provider import CalendarProviderError


class FakeCalendarProvider:
    """Test double that behaves like a provider which really confirmed an event."""

    name = "FAKE_CALENDAR"

    def __init__(self, fail: bool = False, with_meet: bool = True):
        self.fail = fail
        self.with_meet = with_meet
        self.calls = []

    def is_configured(self) -> bool:
        return True

    def create_event(self, summary, description, start_ts, end_ts, attendees=None, request_id=None):
        self.calls.append({
            "summary": summary,
            "description": description,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "attendees": attendees,
            "request_id": request_id,
        })
        if self.fail:
            raise CalendarProviderError("PROVIDER_REJECTED")
        return {
            "confirmed": True,
            "provider": self.name,
            "event_id": "evt_provider_12345",
            "html_link": "https://calendar.example.com/event/evt_provider_12345",
            "meet_url": "https://meet.example.com/abc-defg-hij" if self.with_meet else "",
            "dial_in": {"phone": "+1 555 0100", "pin": "2468"} if self.with_meet else {},
            "status": "confirmed",
            "raw": {},
        }

class TestZonataAssistantIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db = configure_isolated_test_db()
        cls.tenant_id = "tnt_test_zonata"
        cls.company_id = "comp_royal_hotel"
        cls.user_id = "usr_owner_host"

        # Seed test tenant and company
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.tenant_id, "Test ZONATA Tenant", "ENTERPRISE", "ACTIVE", time.time())
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO companies (
                    company_id, tenant_id, name, industry, company_type, status,
                    currency, revenue, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.company_id, cls.tenant_id, "Royal Hotel Jaipur",
                    "Hospitality", "EXISTING", "OPERATIONAL", "INR", 15000000.0, time.time()
                )
            )
            conn.commit()

        cls.assistant = FloatingAssistantService(tenant_id=cls.tenant_id)
        cls.meeting_svc = AiCeoMeetingService(tenant_id=cls.tenant_id)

    # =========================================================================
    # 1. CONTEXT CLASSIFICATION TESTS
    # =========================================================================

    def test_context_classification_personal(self):
        prompts = [
            "What is a good high-protein recipe for my personal diet?",
            "Organize my personal workout schedule and gym routine",
            "Draft a private memo to myself about my weekend travel"
        ]
        for p in prompts:
            res = AssistantContextClassifier.classify(p)
            self.assertEqual(res["category"], IntentCategory.PERSONAL.value)
            self.assertFalse(res["is_ambiguous"])
            self.assertEqual(res["suggested_routing"], "PERSONAL_ASSISTANT")

    def test_context_classification_company(self):
        prompts = [
            "Analyze Q3 gross margins and prepare an executive summary for the board",
            "Review hotel occupancy rate and revenue per available room (RevPAR)",
            "Delegate workforce mission to audit vendor invoices for Royal Hotel Jaipur"
        ]
        for p in prompts:
            res = AssistantContextClassifier.classify(p)
            self.assertEqual(res["category"], IntentCategory.COMPANY.value)
            self.assertFalse(res["is_ambiguous"])
            self.assertEqual(res["suggested_routing"], "AI_CEO")

    def test_context_classification_documents_and_meetings(self):
        doc_res = AssistantContextClassifier.classify("Generate a PDF report summarizing sales velocity")
        self.assertEqual(doc_res["category"], IntentCategory.DOCUMENT_REQUEST.value)

        meet_res = AssistantContextClassifier.classify("Schedule alignment meeting with CFO tomorrow on Google Meet")
        self.assertEqual(meet_res["category"], IntentCategory.MEETING_REQUEST.value)

    def test_context_classification_ambiguous_with_clarification(self):
        res = AssistantContextClassifier.classify("review expenses")
        self.assertTrue(res["is_ambiguous"])
        self.assertIsNotNone(res["clarification"])
        self.assertIn("Personal", res["clarification"])
        self.assertIn("Company", res["clarification"])

    def test_context_classification_mixed_and_specialised(self):
        mixed = AssistantContextClassifier.classify(
            "Use my personal budget notes to review company payroll expenses"
        )
        self.assertEqual(mixed["category"], IntentCategory.MIXED.value)
        self.assertTrue(mixed["is_ambiguous"])

        retrieval = AssistantContextClassifier.classify("find the document Financial Audit")
        self.assertEqual(retrieval["category"], IntentCategory.INFORMATION_RETRIEVAL.value)

        change = AssistantContextClassifier.classify("change the UI and deploy the app")
        self.assertEqual(change["category"], IntentCategory.APPLICATION_CHANGE.value)
        self.assertNotEqual(change["suggested_routing"], "AI_CEO")

    def test_unclear_request_defaults_to_clarification_not_company(self):
        res = AssistantContextClassifier.classify("handle it")
        self.assertEqual(res["category"], IntentCategory.AMBIGUOUS.value)
        self.assertTrue(res["is_ambiguous"])
        self.assertEqual(res["suggested_routing"], "OWNER_CLARIFICATION")

    def test_document_search_without_boundary_is_owner_scoped(self):
        own = document_generator.generate_document(
            title="Owner Only Unscoped Leak Check",
            format_type=DocumentFormat.TXT,
            category=DocumentCategory.PERSONAL_DOCUMENT,
            content="private owner content",
            storage_boundary=StorageBoundary.PERSONAL,
            user_id="usr_unscoped_owner",
            tenant_id=self.tenant_id,
        )
        other = document_generator.generate_document(
            title="Other User Unscoped Leak Check",
            format_type=DocumentFormat.TXT,
            category=DocumentCategory.PERSONAL_DOCUMENT,
            content="private other content",
            storage_boundary=StorageBoundary.PERSONAL,
            user_id="usr_unscoped_other",
            tenant_id=self.tenant_id,
        )
        results = document_generator.search_documents(
            tenant_id=self.tenant_id,
            user_id="usr_unscoped_owner",
            query="Unscoped Leak Check",
        )
        ids = {r["doc_id"] for r in results}
        self.assertIn(own["doc_id"], ids)
        self.assertNotIn(other["doc_id"], ids)

    def test_company_search_requires_verified_company_without_null_leak(self):
        orphan = document_generator.generate_document(
            title="Legacy Orphan Company Record",
            format_type=DocumentFormat.TXT,
            category=DocumentCategory.COMPANY_DOCUMENT,
            content="record without company id",
            storage_boundary=StorageBoundary.COMPANY,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            company_id=None,
        )
        results = document_generator.search_documents(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            query="Legacy Orphan",
            storage_boundary="COMPANY",
            company_id=self.company_id,
        )
        self.assertFalse(any(r["doc_id"] == orphan["doc_id"] for r in results))

        # No company context at all must return nothing company-scoped.
        none_results = document_generator.search_documents(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            storage_boundary="COMPANY",
            company_id=None,
        )
        self.assertEqual(none_results, [])

    # =========================================================================
    # 2. PERSONAL WORKSPACE ISOLATION TESTS
    # =========================================================================

    def test_personal_request_strict_isolation(self):
        sess_id = f"sess_pers_{int(time.time())}"
        res = self.assistant.interact(
            prompt="My personal workout goal is 5 days of cardio per week. Create a note for me.",
            workspace_mode="PERSONAL",
            company_id=self.company_id,
            user_id=self.user_id,
            session_id=sess_id
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["workspace_mode"], "PERSONAL")
        self.assertEqual(res["routed_to"], "PERSONAL_SANDBOX")
        self.assertIsNone(res["action_card"], "Personal requests must never dispatch company workforce missions")

        # Verify deliverable artifact was saved in personal storage directory
        if res.get("deliverable_card"):
            deliv = res["deliverable_card"]
            self.assertEqual(deliv["storage_boundary"], "PERSONAL")
            self.assertIn("personal", deliv["file_path"])
            self.assertTrue(os.path.exists(deliv["file_path"]))

        # Verify no corporate mission was created for this prompt
        with db.get_connection() as conn:
            missions = conn.execute(
                "SELECT * FROM coworker_tasks WHERE tenant_id = ? AND prompt LIKE '%workout goal%'",
                (self.tenant_id,)
            ).fetchall()
            self.assertEqual(len(missions), 0, "Personal requests must not contaminate corporate coworker_tasks")

    # =========================================================================
    # 3. COMPANY REQUEST AI CEO GATEWAY DELEGATION TESTS
    # =========================================================================

    def test_company_request_ai_ceo_gateway(self):
        sess_id = f"sess_comp_{int(time.time())}"
        prompt = "Analyze Q3 gross margins and formulate strategic priorities for Royal Hotel Jaipur"
        res = self.assistant.interact(
            prompt=prompt,
            workspace_mode="COMPANY",
            company_id=self.company_id,
            user_id=self.user_id,
            session_id=sess_id
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["workspace_mode"], "COMPANY")
        self.assertEqual(res["routed_to"], "AI_CEO")
        self.assertIn("Royal Hotel Jaipur", res["reply"])

        # A delegated mission is relayed as delegated and unverified.
        action = res.get("action_card")
        if action:
            self.assertEqual(action["status"], "DELEGATED")
            self.assertEqual(action["verification_status"], "UNVERIFIED")
            self.assertIn(res["execution_state"], ("DELEGATED", "AWAITING_APPROVAL", "ACCEPTED"))

        # Check deliverable report was generated in company storage
        if res.get("deliverable_card"):
            deliv = res["deliverable_card"]
            self.assertEqual(deliv["storage_boundary"], "COMPANY")
            self.assertIn("companies", deliv["file_path"])
            self.assertTrue(os.path.exists(deliv["file_path"]))
            self.assertTrue(deliv["download_url"].startswith("/api/assistant/documents/"))

    # =========================================================================
    # 4. NATIVE DOCUMENT GENERATION TESTS (PDF, DOCX, XLSX, PPTX, CSV)
    # =========================================================================

    def test_native_document_generation_all_formats(self):
        formats = [
            DocumentFormat.PDF,
            DocumentFormat.DOCX,
            DocumentFormat.XLSX,
            DocumentFormat.PPTX,
            DocumentFormat.CSV
        ]

        for fmt in formats:
            doc = document_generator.generate_document(
                title=f"Sample Deliverable {fmt.value}",
                format_type=fmt,
                category=DocumentCategory.FINANCIAL_RECORD,
                content="Line 1: Q1 Revenue ₹12.5M\nLine 2: Q2 Revenue ₹14.8M\nLine 3: Q3 Revenue ₹16.2M",
                storage_boundary=StorageBoundary.COMPANY,
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                company_id=self.company_id
            )

            self.assertTrue(os.path.exists(doc["file_path"]))
            self.assertGreater(doc["size_bytes"], 0)
            self.assertIsNotNone(doc["sha256"])
            self.assertEqual(len(doc["sha256"]), 64)

            # Re-verify SHA-256 matches actual file on disk
            with open(doc["file_path"], "rb") as f:
                disk_sha = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(doc["sha256"], disk_sha, f"SHA256 mismatch for format {fmt.value}")

    # =========================================================================
    # 5. INTELLIGENT FILE SEARCH & RETRIEVAL TESTS
    # =========================================================================

    def test_document_search_and_retrieval(self):
        # 1. Create a known test document
        doc = document_generator.generate_document(
            title="Q3 FY26 Board Financial Audit Report",
            format_type=DocumentFormat.PDF,
            category=DocumentCategory.EXECUTIVE_REPORT,
            content="Gross Profit ₹8.4M | EBITDA ₹3.2M | Tax ₹1.1M",
            storage_boundary=StorageBoundary.COMPANY,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )

        # 2. Search for the document via DocumentGenerator
        results = document_generator.search_documents(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            query="Financial Audit",
            storage_boundary="COMPANY",
            company_id=self.company_id
        )

        self.assertGreater(len(results), 0)
        found = any(r["doc_id"] == doc["doc_id"] for r in results)
        self.assertTrue(found, "Document should be indexed and retrievable by keywords")

        # 3. Retrieve through ZONATA AI Assistant conversational search
        res = self.assistant.interact(
            prompt="Find document Financial Audit",
            workspace_mode="COMPANY",
            company_id=self.company_id,
            user_id=self.user_id
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["deliverable_card"])
        self.assertEqual(res["deliverable_card"]["doc_id"], doc["doc_id"])

    # =========================================================================
    # 6. AUTONOMOUS MEETING ORCHESTRATION & GOOGLE MEET INTEGRATION
    # =========================================================================

    def test_meeting_scheduling_is_blocked_without_provider(self):
        before = None
        with db.get_connection() as conn:
            before = conn.execute(
                "SELECT COUNT(*) AS c FROM meeting_integrations WHERE tenant_id = ?",
                (self.tenant_id,),
            ).fetchone()["c"]

        res = self.meeting_svc.schedule_meeting_autonomous(
            prompt="Quarterly Executive Strategy Review with Regional Directors",
            company_id=self.company_id,
            user_id=self.user_id,
            duration_minutes=60,
            platform="GOOGLE_MEET",
            ai_representative_enabled=True,
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["provider_status"], "BLOCKED")
        self.assertFalse(res["scheduled"])
        self.assertNotIn("google_meet_url", res)
        self.assertNotIn("meeting_id", res)

        with db.get_connection() as conn:
            after = conn.execute(
                "SELECT COUNT(*) AS c FROM meeting_integrations WHERE tenant_id = ?",
                (self.tenant_id,),
            ).fetchone()["c"]
        self.assertEqual(before, after, "A blocked meeting must not create an integration row")

    def test_meeting_scheduling_with_confirmed_provider(self):
        provider = FakeCalendarProvider()
        meet_res = self.meeting_svc.schedule_meeting_autonomous(
            prompt="Quarterly Executive Strategy Review with Regional Directors",
            company_id=self.company_id,
            user_id=self.user_id,
            duration_minutes=60,
            platform="GOOGLE_MEET",
            ai_representative_enabled=True,
            calendar_provider=provider,
        )

        self.assertTrue(meet_res["success"])
        self.assertTrue(meet_res["scheduled"])
        self.assertEqual(meet_res["provider_status"], "CONFIRMED")
        self.assertEqual(meet_res["google_meet_url"], "https://meet.example.com/abc-defg-hij")
        self.assertEqual(meet_res["calendar_event_id"], "evt_provider_12345")
        self.assertTrue(meet_res["ai_representative_enabled"])
        self.assertIn("AI representative", meet_res["statutory_disclosure"])
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("Objective:", provider.calls[0]["description"])

        # Briefing dossier is a real file, not a fabricated URL.
        self.assertIsNotNone(meet_res["briefing_dossier_id"])
        self.assertTrue(meet_res["briefing_dossier_url"].startswith("/api/assistant/documents/"))
        dossier = document_generator.get_document(meet_res["briefing_dossier_id"], self.tenant_id)
        self.assertTrue(os.path.exists(dossier["file_path"]))

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM meeting_integrations WHERE meeting_id = ?",
                (meet_res["meeting_id"],)
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["meet_url"], meet_res["google_meet_url"])
        self.assertEqual(row["calendar_event_id"], "evt_provider_12345")
        self.assertEqual(row["ai_representative_enabled"], 1)
        # Disclosure is not attested merely because scheduling succeeded.
        self.assertEqual(row["statutory_disclosure_signed"], 0)

    def test_meeting_provider_failure_is_not_reported_as_success(self):
        provider = FakeCalendarProvider(fail=True)
        res = self.meeting_svc.schedule_meeting_autonomous(
            prompt="Board risk review",
            company_id=self.company_id,
            user_id=self.user_id,
            calendar_provider=provider,
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["provider_status"], "BLOCKED")
        self.assertEqual(res["reason"], "CALENDAR_PROVIDER_FAILED")
        self.assertNotIn("meeting_id", res)

    # =========================================================================
    # 7. CONVERSATION HISTORY BUFFER & AMBIGUITY ARBITRATION
    # =========================================================================

    def test_assistant_conversation_history_persistence(self):
        sess_id = f"sess_hist_{int(time.time())}"
        self.assistant.interact("Hello, what is ZONATA AI?", session_id=sess_id, user_id=self.user_id)
        self.assistant.interact("Tell me about our company revenue.", session_id=sess_id, company_id=self.company_id, user_id=self.user_id)

        history = self.assistant.get_conversation_history(sess_id)
        self.assertGreaterEqual(len(history), 4, "Should record at least 2 user and 2 assistant turns")
        self.assertEqual(history[0]["sender"], "user")
        self.assertEqual(history[1]["sender"], "assistant")

    def test_ambiguity_arbitration_flow(self):
        # Ambiguous prompt
        res = self.assistant.interact("review expenses", user_id=self.user_id)
        self.assertEqual(res["intent_category"], "AMBIGUOUS")
        self.assertIn("choices", res)
        self.assertEqual(len(res["choices"]), 2)

    def test_storage_boundary_strict_isolation(self):
        # Create 1 personal doc and 1 company doc
        p_doc = document_generator.generate_document(
            title="Private Tax Notes For Host",
            format_type=DocumentFormat.PDF,
            content="Private tax plan details.",
            storage_boundary=StorageBoundary.PERSONAL,
            user_id="usr_private_host_1",
            tenant_id=self.tenant_id
        )
        c_doc = document_generator.generate_document(
            title="Corporate Financial Audit Summary",
            format_type=DocumentFormat.PDF,
            content="Corporate P&L statement.",
            storage_boundary=StorageBoundary.COMPANY,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )

        # Search from a different user in personal boundary - should NOT find p_doc
        results_other = document_generator.search_documents(
            tenant_id=self.tenant_id,
            user_id="usr_stranger",
            storage_boundary="PERSONAL"
        )
        self.assertFalse(any(r["doc_id"] == p_doc["doc_id"] for r in results_other))

        # Search by author - should find p_doc
        results_author = document_generator.search_documents(
            tenant_id=self.tenant_id,
            user_id="usr_private_host_1",
            storage_boundary="PERSONAL"
        )
        self.assertTrue(any(r["doc_id"] == p_doc["doc_id"] for r in results_author))

    def test_post_meeting_records_and_minutes_pdf(self):
        # Scheduling requires a confirmed provider in this build.
        provider = FakeCalendarProvider()
        meet_res = self.meeting_svc.schedule_meeting_autonomous(
            prompt="Executive Alignment for Q4 Objectives",
            company_id=self.company_id,
            user_id=self.user_id,
            calendar_provider=provider,
        )
        mid = meet_res["meeting_id"]

        # Add sample transcript
        self.meeting_svc.add_transcript_entry(
            meeting_id=mid,
            company_id=self.company_id,
            speaker="AI CEO",
            mode="TEXT",
            message="We project 18% QoQ expansion in Jaipur wedding bookings."
        )

        # Generate post meeting minutes
        rec_res = self.meeting_svc.generate_post_meeting_records(mid)
        self.assertTrue(rec_res["success"])
        self.assertIsNotNone(rec_res["minutes_doc_id"])
        doc = document_generator.get_document(rec_res["minutes_doc_id"], self.tenant_id)
        self.assertTrue(os.path.exists(doc["file_path"]))
        with open(doc["file_path"], "rb") as fh:
            raw = fh.read()
        self.assertIn(b"We project 18% QoQ expansion", raw)
        self.assertIn(b"No decisions were recorded", raw)

    def test_legacy_backward_compatibility(self):
        # Test handle_ai_chat
        chat_res = self.assistant.handle_ai_chat("What is our hotel status?", company_id=self.company_id)
        self.assertIn("reply", chat_res)
        self.assertIn("citations", chat_res)

        # Test create_coworker_task: queued, never auto-completed.
        task = self.assistant.create_coworker_task("Verify hotel PMS filesystem", workspace_mode="COMPANY", company_id=self.company_id)
        self.assertIn(task["status"], ("PLANNING", "QUEUED"))
        self.assertEqual(task["permission_tier"], "SAFE_BROWSE")
        self.assertIsNone(task["receipt_id"])
        self.assertFalse(any(stage["stage"] == "COMPLETED" for stage in task["execution_log"]))

        # Test gated coworker task requiring approval
        gated = self.assistant.create_coworker_task("Pay vendor invoice of ₹150,000", workspace_mode="COMPANY", company_id=self.company_id)
        self.assertEqual(gated["status"], "AWAITING_APPROVAL")
        self.assertEqual(gated["permission_tier"], "FINANCIAL_ACTION")

        # Approval authorises but does not claim execution.
        approved = self.assistant.approve_coworker_task(gated["task_id"], approved=True)
        self.assertEqual(approved["status"], "APPROVED")
        self.assertEqual(approved["approval_status"], "APPROVED")
        self.assertIsNone(approved["receipt_id"])
        self.assertIsNone(approved["completed_at"])

        denied = self.assistant.create_coworker_task("Delete vault keys", workspace_mode="COMPANY", company_id=self.company_id)
        denied = self.assistant.approve_coworker_task(denied["task_id"], approved=False)
        self.assertEqual(denied["status"], "REVERTED")
        self.assertEqual(denied["approval_status"], "DENIED")


if __name__ == "__main__":
    unittest.main()
