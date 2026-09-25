"""
RoboAssistant Company OS 2.0 — Sales, Events & Business Causality Test Suite
Validates lead qualification, discount ceiling policy enforcement, Voice AI dialogue boundaries,
continuous event dispatch, interactive meetings, and the core invariant: TASK_SUCCESS != BUSINESS_OUTCOME.
"""

import unittest
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.portfolio import CompanyPortfolioManager
from core.sales_workforce import AISalesWorkforce, SalesLeadStatus
from core.voice_agent import GovernedVoiceAgent, VoiceUtteranceType
from core.event_engine import EnterpriseEventEngine, EventSeverity, EnterpriseEventType
from core.interactive_meeting import InteractiveMeetingSystem
from core.business_causality import BusinessCausalityEngine, OutcomeStatus

class TestSalesAndCausality(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_sales_{int(time.time()*1000)}"
        self.portfolio = CompanyPortfolioManager(tenant_id=self.tenant_id, load_from_db=False)
        self.company = self.portfolio.onboard_company(
            name="Heritage Boutique Hotel",
            country="IN",
            industry="Hospitality",
            company_type="EXISTING"
        )
        self.cid = self.company.company_id

    def test_sales_workforce_discount_ceiling_enforcement(self):
        sales = AISalesWorkforce(tenant_id=self.tenant_id, company_id=self.cid)

        # 1. Lead ingestion
        lead = sales.ingest_lead(
            contact_name="Aarav Sharma",
            channel="WHATSAPP",
            initial_inquiry="Looking to book 3 suites for wedding party, need quote"
        )
        self.assertEqual(lead["status"], SalesLeadStatus.QUALIFIED)
        self.assertGreaterEqual(lead["qualification_score"], 0.7)

        # 2. Customer asks for allowable discount (8%)
        res_allowed = sales.process_customer_message(lead["lead_id"], "Can you offer 8% discount for direct payment?")
        self.assertTrue(res_allowed["success"])
        self.assertEqual(res_allowed["discount_offered"], 8.0)
        self.assertFalse(res_allowed["escalated"])

        # 3. Customer asks for excessive discount (25%) -> MUST ESCALATE
        res_escalated = sales.process_customer_message(lead["lead_id"], "If I book 5 rooms, will you give 25% discount?")
        self.assertTrue(res_escalated["success"])
        self.assertTrue(res_escalated["escalated"])
        self.assertEqual(res_escalated["lead_status"], SalesLeadStatus.ESCALATED)
        self.assertIn("requires executive approval", res_escalated["agent_response"])

    def test_voice_ai_epistemic_separation(self):
        voice = GovernedVoiceAgent(tenant_id=self.tenant_id, company_id=self.cid)
        call = voice.initiate_call_session(caller_id="+91-9876543210", direction="INBOUND", consent_given=True)
        self.assertEqual(call["call_state"], "ACTIVE")

        turn = voice.process_utterance(call["session_id"], "What is the rate for a suite?")
        self.assertIn("Deluxe Heritage", turn["system_fact"])
        types_in_turn = [item["type"] for item in turn["transcript_turn"]]
        self.assertIn(VoiceUtteranceType.CUSTOMER_SAID, types_in_turn)
        self.assertIn(VoiceUtteranceType.SYSTEM_FACT, types_in_turn)
        self.assertIn(VoiceUtteranceType.PROPOSED_RESPONSE, types_in_turn)

        voice.complete_call(call["session_id"])

    def test_continuous_event_engine_and_autonomous_dispatch(self):
        engine = EnterpriseEventEngine(self.portfolio, tenant_id=self.tenant_id)

        # Medium severity event -> Autonomous mission creation
        evt_med = engine.emit_event(
            company_id=self.cid,
            event_type=EnterpriseEventType.REVENUE_ANOMALY,
            category="FINANCIAL",
            severity=EventSeverity.MEDIUM,
            details={"anomaly_pct": -4.2, "source": "direct_booking_channel"}
        )
        self.assertTrue(evt_med["handled"])
        self.assertIsNotNone(evt_med["resulting_mission_id"])

        # Critical severity event -> Escalates to Chief of Staff
        evt_crit = engine.emit_event(
            company_id=self.cid,
            event_type=EnterpriseEventType.SYSTEM_OUTAGE,
            category="TECHNICAL",
            severity=EventSeverity.CRITICAL,
            details={"host_node": "primary_pms_connector", "status": "UNREACHABLE"}
        )
        self.assertFalse(evt_crit["handled"])  # Requires human/executive intervention

    def test_interactive_executive_meeting(self):
        meeting_sys = InteractiveMeetingSystem(self.portfolio, tenant_id=self.tenant_id, company_id=self.cid)
        record = meeting_sys.conduct_executive_operating_meeting()
        self.assertIn("Finance", record["department_reports"])
        self.assertIn("Operations", record["department_reports"])
        self.assertGreaterEqual(len(record["ceo_challenges"]), 2)
        self.assertGreaterEqual(len(record["agreed_missions"]), 1)

    def test_business_causality_task_success_vs_business_outcome(self):
        causality = BusinessCausalityEngine(tenant_id=self.tenant_id, company_id=self.cid)

        # Record a mission where tasks finished (TASK_SUCCESS)
        chain_id = causality.record_causal_link(
            strategy_goal="Uplift Direct Bookings by 15%",
            mission_id="mis_booking_campaign_01",
            task_id="tsk_email_blast",
            action_id="act_send_emails",
            cost_attributed=3500.0,
            verified_outcome=OutcomeStatus.PENDING_EVIDENCE
        )
        summary_initial = causality.get_causality_summary()
        # Invariant check: Task is complete, but business outcome is NOT yet verified!
        self.assertEqual(summary_initial["verified_attributed_revenue"], 0.0)
        self.assertEqual(summary_initial["verified_outcomes_count"], 0)
        self.assertEqual(summary_initial["pending_evidence_count"], 1)

        # Present verified financial transaction evidence
        outcome_res = causality.verify_outcome_with_transaction(
            chain_id=chain_id,
            verified_transaction_id="tx_bank_dep_88921",
            verified_revenue=24500.0
        )
        self.assertTrue(outcome_res["success"])
        self.assertEqual(outcome_res["verified_outcome"], OutcomeStatus.VERIFIED_SUCCESS)
        self.assertEqual(outcome_res["net_contribution"], 21000.0)

        # Verify summary reflects true business outcome
        summary_final = causality.get_causality_summary()
        self.assertEqual(summary_final["verified_attributed_revenue"], 24500.0)
        self.assertEqual(summary_final["net_verified_contribution"], 21000.0)
        self.assertEqual(summary_final["verified_outcomes_count"], 1)

if __name__ == "__main__":
    unittest.main()
