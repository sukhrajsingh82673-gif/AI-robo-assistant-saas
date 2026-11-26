"""
ZONATA Unit & Contract Tests — Sub-Step 3G: Remote View & Human Takeover (Rule 24, 25, 27, 28).
"""

from __future__ import annotations

import os
import unittest

from core.remote_view.streamer import RemoteViewStreamer
from core.remote_view.takeover import HumanTakeoverManager
from core.remote_view.types import (
    AgentExecutionSuppressedError,
    MaskRegion,
    RemoteTargetType,
    TakeoverEventType,
    TakeoverHandbackAssertion,
    TakeoverState,
    ViewportBounds,
)


class TestStep3RemoteView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"

    def test_01_viewport_boundary_enforcement(self):
        """Rule 28: Capture must be bounded strictly to granted viewport rectangle."""
        bounds = ViewportBounds(x=100, y=100, width=800, height=600)

        # In-bounds coordinates
        self.assertTrue(bounds.contains(150, 200))
        self.assertTrue(bounds.contains(900, 700))

        # Out-of-bounds coordinates (Rule 28)
        self.assertFalse(bounds.contains(50, 50))
        self.assertFalse(bounds.contains(950, 750))

    def test_02_pre_transmission_masking_rule24_28(self):
        """Rule 24 & 28: Secret inputs and challenge widgets must be masked before transmission."""
        bounds = ViewportBounds(x=0, y=0, width=1280, height=720)
        streamer = RemoteViewStreamer(session_id="sess_test_mask", viewport=bounds)

        # Register secret password input and challenge widget
        streamer.add_mask_region(
            MaskRegion(x=200, y=300, width=250, height=40, reason="SECRET_INPUT")
        )
        streamer.add_mask_region(
            MaskRegion(x=500, y=400, width=300, height=70, reason="CHALLENGE_WIDGET")
        )

        frame = streamer.process_and_stream_frame(canvas_description="secure_login_form")

        self.assertEqual(frame.session_id, "sess_test_mask")
        self.assertEqual(frame.frame_index, 1)
        self.assertTrue(frame.is_redacted)
        self.assertEqual(len(frame.masked_regions), 2)
        reasons = [m["reason"] for m in frame.masked_regions]
        self.assertIn("SECRET_INPUT", reasons)
        self.assertIn("CHALLENGE_WIDGET", reasons)
        self.assertTrue(frame.image_base64.startswith("data:image/synthetic+redacted;base64,"))

    def test_03_takeover_suppresses_agent_commands(self):
        """Rule 27: Human takeover instantly halts and suppresses agent execution."""
        mgr = HumanTakeoverManager()
        bounds = ViewportBounds(x=0, y=0, width=1024, height=768)
        sess_id = mgr.create_session(
            tenant_id="tenant_omega",
            company_id="company_omega",
            target_type=RemoteTargetType.BROWSER_TAB,
            target_id="tab_browser_1",
            viewport=bounds,
        )

        # Agent permitted when session starts
        mgr.assert_agent_permitted(sess_id)

        # Human initiates takeover
        mgr.initiate_takeover(session_id=sess_id, human_principal_id="principal_owner_42")

        # Agent must be suppressed immediately
        with self.assertRaises(AgentExecutionSuppressedError) as ctx:
            mgr.assert_agent_permitted(sess_id)
        self.assertIn("Human principal 'principal_owner_42' currently has control", str(ctx.exception))

    def test_04_handback_with_state_assertion(self):
        """Rule 25 & 27: Human releases control with explicit state assertion, resuming agent."""
        mgr = HumanTakeoverManager()
        bounds = ViewportBounds(x=0, y=0, width=1024, height=768)
        sess_id = mgr.create_session(
            tenant_id="tenant_omega",
            company_id="company_omega",
            target_type=RemoteTargetType.HOST_DESKTOP,
            target_id="display_0",
            viewport=bounds,
        )

        mgr.initiate_takeover(session_id=sess_id, human_principal_id="principal_owner_42")

        # Human solves challenge and releases control with assertion
        assertion = TakeoverHandbackAssertion(
            session_id=sess_id,
            human_principal_id="principal_owner_42",
            status_asserted="CHALLENGE_SOLVED",
            notes="Completed Cloudflare Turnstile verification manually.",
        )
        mgr.release_takeover_with_assertion(assertion)

        # Agent is now permitted to resume
        mgr.assert_agent_permitted(sess_id)

        events = mgr.get_events(sess_id)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_type"], TakeoverEventType.TAKEOVER_INITIATED.value)
        self.assertEqual(events[1]["event_type"], TakeoverEventType.CONTROL_RELEASED.value)
        self.assertEqual(events[1]["handback_state_assertion"]["status_asserted"], "CHALLENGE_SOLVED")

    def test_05_session_lifecycle_and_db_persistence(self):
        """Audit persistence: sessions and takeover events stored in relational store."""
        mgr = HumanTakeoverManager()
        bounds = ViewportBounds(x=10, y=10, width=500, height=500)
        sess_id = mgr.create_session(
            tenant_id="tenant_audit",
            company_id="company_audit",
            target_type=RemoteTargetType.BROWSER_TAB,
            target_id="tab_audit_9",
            viewport=bounds,
        )

        mgr.initiate_takeover(sess_id, "human_admin")
        mgr.release_takeover_with_assertion(
            TakeoverHandbackAssertion(
                session_id=sess_id,
                human_principal_id="human_admin",
                status_asserted="MFA_COMPLETED",
            )
        )
        mgr.close_session(sess_id)

        # Inspect database
        cur = mgr.db.cursor()
        cur.execute("SELECT is_active, closed_at FROM remote_view_sessions WHERE session_id = ?", (sess_id,))
        row = cur.fetchone()
        self.assertEqual(row[0], 0)  # is_active = 0
        self.assertIsNotNone(row[1])  # closed_at populated


if __name__ == "__main__":
    unittest.main()
