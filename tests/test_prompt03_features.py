"""
Unit tests for ZONATA Prompt 03 Capabilities:
- Universal Schedule Engine (CRUD, NL Parser, Conflict Detection, AI CEO Recommendations)
- AI CEO Meeting Room (Lifecycle, Media stream flags, Transcripts, Context Reports, Decisions)
- Floating Live Assistant (AI Chat citations, Coworker 10-stage lifecycle, Gated Permissions)
- Plugins & Connections Hub (Plugins Catalog, External Connections, Health Telemetry, Field Mappings)
"""

import unittest
import time
import os
import tempfile
from core.db import db, configure_isolated_test_db
from core.schedule_service import UniversalScheduleService
from core.meeting_service import AiCeoMeetingService
from core.assistant_service import FloatingAssistantService
from core.plugins_service import PluginsAndConnectionsService

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "prompt03_test_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()

class TestPrompt03Features(unittest.TestCase):
    def setUp(self):
        self.schedule_service = UniversalScheduleService(tenant_id="tnt_primary")
        self.meeting_service = AiCeoMeetingService(tenant_id="tnt_primary")
        self.assistant_service = FloatingAssistantService(tenant_id="tnt_primary")
        self.plugins_service = PluginsAndConnectionsService(tenant_id="tnt_primary")

        # Ensure tnt_primary and comp_primary exist and clean test state
        with db.get_connection() as conn:
            conn.execute("DELETE FROM universal_schedules WHERE tenant_id = 'tnt_primary'")
            conn.execute("DELETE FROM external_connections WHERE tenant_id = 'tnt_primary'")
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES ('tnt_primary', 'Primary Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (time.time(),)
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO companies (
                    company_id, tenant_id, name, country, industry,
                    company_type, status, currency, revenue, cost,
                    contribution, created_at
                ) VALUES ('comp_primary', 'tnt_primary', 'NovaTech Solutions', 'IN', 'Cloud SaaS', 'EXISTING', 'OPERATIONAL', '₹', 1500000.0, 950000.0, 550000.0, ?)
                """,
                (time.time(),)
            )
            conn.commit()



    # =========================================================================
    # 1. Universal Schedule Tests
    # =========================================================================
    def test_schedule_crud_and_conflict_detection(self):
        now = time.time()
        # 1. Create primary item
        item1 = self.schedule_service.create_schedule({
            "company_id": "comp_primary",
            "title": "Executive Council Review",
            "item_type": "meeting",
            "priority": "HIGH",
            "start_time": now + 5000,
            "end_time": now + 8600,
            "assigned_to": "Host & AI CEO"
        })
        self.assertIsNotNone(item1.get("schedule_id"))
        self.assertEqual(item1["conflict_detected"], False)

        # 2. Create overlapping item
        item2 = self.schedule_service.create_schedule({
            "company_id": "comp_primary",
            "title": "Emergency Budget Sync",
            "item_type": "budget_review",
            "priority": "URGENT",
            "start_time": now + 6000,
            "end_time": now + 9000,
            "assigned_to": "CFO Agent"
        })
        self.assertEqual(item2["conflict_detected"], True)
        self.assertIn("Time window overlap", item2["conflict_reason"])

        # 3. Read / List
        items = self.schedule_service.list_schedules(company_id="comp_primary")
        self.assertTrue(len(items) >= 2)

        # 4. Update
        updated = self.schedule_service.update_schedule(item1["schedule_id"], {
            "title": "Updated Executive Council Review",
            "priority": "URGENT"
        })
        self.assertEqual(updated["title"], "Updated Executive Council Review")
        self.assertEqual(updated["priority"], "URGENT")

        # 5. Delete
        del_ok = self.schedule_service.delete_schedule(item1["schedule_id"])
        self.assertTrue(del_ok)
        del_ok2 = self.schedule_service.delete_schedule(item2["schedule_id"])
        self.assertTrue(del_ok2)

    def test_schedule_natural_language_parser(self):
        parsed = self.schedule_service.parse_natural_language(
            "Schedule emergency budget review tomorrow at 2pm",
            company_id="comp_primary"
        )
        self.assertEqual(parsed["item_type"], "budget_review")
        self.assertIn(parsed["priority"], ["HIGH", "URGENT", "MEDIUM"])
        self.assertTrue(parsed["start_time"] > time.time())

        # Test process run NL
        parsed2 = self.schedule_service.parse_natural_language(
            "Run night audit workflow Friday 2am",
            company_id="comp_primary"
        )
        self.assertEqual(parsed2["item_type"], "process_run")

    def test_schedule_ai_ceo_recommendations(self):
        recs = self.schedule_service.get_ai_ceo_recommendations("comp_primary")
        self.assertIsInstance(recs, list)
        self.assertTrue(len(recs) >= 1)
        self.assertTrue(any("recommendation_id" in r for r in recs))

    # =========================================================================
    # 2. AI CEO Meeting Room Tests
    # =========================================================================
    def test_meeting_room_lifecycle_and_transcripts(self):
        # 1. Get or create active meeting
        meeting = self.meeting_service.get_or_create_active_meeting("comp_primary")
        mid = meeting["meeting_id"]
        self.assertEqual(meeting["status"], "Ready")

        # 2. Start meeting
        live_mtg = self.meeting_service.start_meeting(mid)
        self.assertEqual(live_mtg["status"], "Live")

        # 3. Send Host Message & Verify Contextual AI CEO Response
        interaction = self.meeting_service.send_host_message(mid, "Review our current sales revenue and pipeline.")
        self.assertEqual(interaction["host_message"]["speaker"], "HOST")
        self.assertEqual(interaction["ai_ceo_response"]["speaker"], "AI CEO")
        self.assertIn("tracked revenue", interaction["ai_ceo_response"]["message"].lower())

        # 4. Check transcripts
        transcripts = self.meeting_service.get_transcripts(mid)
        self.assertTrue(len(transcripts) >= 3) # initial greeting + system start + host + ai ceo

        # 5. Shared Context Reports
        reports = self.meeting_service.get_shared_reports("comp_primary")
        self.assertIn("reports", reports)
        self.assertIn("financial_summary", reports["reports"])
        self.assertIn("executive_brief", reports["reports"])

        # 6. Record Governed Decision with Mission Creation
        decision = self.meeting_service.record_decision(
            company_id="comp_primary",
            title="Maintain gross margin above 25%",
            description="Instruct commercial team to reject unapproved discount exceptions.",
            decision_type="STRATEGIC",
            meeting_id=mid,
            create_mission=True
        )
        self.assertEqual(decision["status"], "APPROVED")
        self.assertIsNotNone(decision["signed_grant_hash"])
        self.assertIsNotNone(decision["mission_id"])

        # 7. End Meeting
        ended_mtg = self.meeting_service.end_meeting(mid, "Reviewed revenue and signed margin directive.")
        self.assertEqual(ended_mtg["status"], "Ended")

    # =========================================================================
    # 3. Floating Live Assistant & Coworker Tests
    # =========================================================================
    def test_assistant_chat_citations(self):
        # Query internal help
        chat_internal = self.assistant_service.handle_ai_chat("What is the AI CEO Meeting Room?", "comp_primary")
        self.assertIn("citations", chat_internal)
        self.assertTrue(any(c["source_type"] == "INTERNAL" for c in chat_internal["citations"]))

        # Query market/competitor: external retrieval is not configured, so the
        # citation must explicitly say so instead of inventing a source.
        chat_external = self.assistant_service.handle_ai_chat("What are competitor trends in enterprise AI?", "comp_primary")
        external = [c for c in chat_external["citations"] if c["source_type"] == "EXTERNAL"]
        self.assertTrue(external)
        self.assertFalse(external[0]["verified"])
        self.assertEqual(external[0]["status"], "UNAVAILABLE")

    def test_coworker_task_lifecycle_and_gated_approval(self):
        # 1. Safe task: queued, not auto-completed without an executor.
        safe_task = self.assistant_service.create_coworker_task(
            prompt="Inspect host node logs and system stats",
            workspace_mode="PERSONAL"
        )
        self.assertIn(safe_task["status"], ("PLANNING", "QUEUED"))
        self.assertEqual(safe_task["permission_tier"], "SAFE_BROWSE")
        self.assertEqual(safe_task["approval_status"], "AUTO")
        self.assertIsNone(safe_task["receipt_id"])
        self.assertFalse(any(s["stage"] == "COMPLETED" for s in safe_task["execution_log"]))

        # 2. Sensitive task (requires Host authorization gate)
        sensitive_task = self.assistant_service.create_coworker_task(
            prompt="Transfer 50,000 INR from bank account to vendor",
            workspace_mode="COMPANY",
            company_id="comp_primary"
        )
        self.assertEqual(sensitive_task["status"], "AWAITING_APPROVAL")
        self.assertEqual(sensitive_task["permission_tier"], "FINANCIAL_ACTION")
        self.assertEqual(sensitive_task["approval_status"], "PENDING")

        # 3. Approval authorises but does not fabricate completion.
        approved_task = self.assistant_service.approve_coworker_task(sensitive_task["task_id"], approved=True)
        self.assertEqual(approved_task["status"], "APPROVED")
        self.assertEqual(approved_task["approval_status"], "APPROVED")
        self.assertIsNone(approved_task["completed_at"])
        self.assertIsNone(approved_task["receipt_id"])

        # 4. Reject another sensitive task
        rej_task = self.assistant_service.create_coworker_task(
            prompt="Delete system credential and vault keys",
            workspace_mode="PERSONAL"
        )
        denied_task = self.assistant_service.approve_coworker_task(rej_task["task_id"], approved=False)
        self.assertEqual(denied_task["status"], "REVERTED")
        self.assertEqual(denied_task["approval_status"], "DENIED")

    # =========================================================================
    # 4. Plugins & Connections Hub Tests
    # =========================================================================
    def test_plugins_and_connections_hub(self):
        # 1. Plugins catalog
        plugins = self.plugins_service.list_plugins()
        self.assertTrue(len(plugins) >= 5)
        p1 = plugins[0]
        self.assertIn("capabilities", p1)

        # Toggle enable/disable
        updated_p = self.plugins_service.toggle_plugin_enabled(p1["plugin_id"], False)
        self.assertEqual(updated_p["enabled"], False)

        # 2. External Connections — created explicitly, never demo-seeded
        new_conn = self.plugins_service.create_connection({
            "company_id": "comp_primary",
            "name": "Custom Stripe Payments Gateway",
            "service_type": "BANKING",
            "endpoint_url": "https://api.stripe.com/v1"
        })
        self.assertIsNotNone(new_conn.get("connection_id"))
        self.assertEqual(new_conn["name"], "Custom Stripe Payments Gateway")

        conns = self.plugins_service.list_connections("comp_primary")
        self.assertTrue(any(c["connection_id"] == new_conn["connection_id"] for c in conns))
        c1 = next(c for c in conns if c["connection_id"] == new_conn["connection_id"])
        self.assertIn("health_score", c1)
        self.assertIn("field_mappings", c1)

        # Probe reports only measured facts: a real reachability check, no
        # fabricated handshake success.
        ping = self.plugins_service.test_connection(c1["connection_id"])
        self.assertIn(ping["status"], ("CONNECTED", "UNREACHABLE"))
        self.assertFalse(ping["handshake_verified"])
        self.assertGreaterEqual(ping["latency_ms"], 0)

        # Bulk sync has no adapter wired, so it must not invent record counts.
        sync = self.plugins_service.sync_connection(c1["connection_id"])
        self.assertEqual(sync["status"], "NOT_IMPLEMENTED")
        self.assertEqual(sync["records_synced"], 0)

if __name__ == '__main__':
    unittest.main()
