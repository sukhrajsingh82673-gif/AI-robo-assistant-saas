"""
RoboAssistant Company OS 2.0 — CEO 2.0 & Executive Council Test Suite
Validates the continuous operating cycle, four planning horizons, operational reasoning,
Executive Council independent challenge loops, and AI Chief of Staff coordination.
"""

import unittest
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.portfolio import CompanyPortfolioManager
from core.ceo_engine import CEOExecutiveEngine
from core.executive_council import ExecutiveCouncil, CouncilRoleType
from core.ceo_chief_of_staff import ChiefOfStaff
from core.truth_types import TruthState, PlanningHorizon, ExecutionStage

class TestCEO2AndCouncil(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_test_{int(time.time()*1000)}"
        self.portfolio = CompanyPortfolioManager(tenant_id=self.tenant_id, load_from_db=False)
        self.company = self.portfolio.onboard_company(
            name="Imperial Palace Resort",
            country="IN",
            industry="Hospitality",
            company_type="EXISTING",
            operating_rules=["Always verify rates before channel publication"]
        )
        self.ceo_engine = CEOExecutiveEngine(self.portfolio, tenant_id=self.tenant_id)

    def test_executive_operating_cycle(self):
        result = self.ceo_engine.execute_executive_cycle(self.company.company_id)
        self.assertTrue(result["success"])
        self.assertEqual(result["cycle_stage"], ExecutionStage.COMPLETED.value)
        self.assertIn("revenue", result["cognitive_facts"])
        self.assertIn("workforce_size", result["cognitive_facts"])
        self.assertEqual(result["cognitive_facts"]["workforce_size"]["truth_state"], TruthState.VERIFIED.value)

        # Check 4 planning horizons
        horizons = result["planning_horizons"]
        self.assertIn(PlanningHorizon.IMMEDIATE.value, horizons)
        self.assertIn(PlanningHorizon.TODAY.value, horizons)
        self.assertIn(PlanningHorizon.STRATEGIC.value, horizons)
        self.assertIn(PlanningHorizon.LONG_TERM.value, horizons)

        # Check explainable Operational Reasoning
        reasoning = result["operational_reasoning"]
        self.assertIn("objective", reasoning)
        self.assertIn("why", reasoning)
        self.assertIn("evidence", reasoning)
        self.assertIn("verification_method", reasoning)

    def test_executive_council_independent_critique_and_consensus(self):
        council = ExecutiveCouncil(tenant_id=self.tenant_id, company_id=self.company.company_id)
        members = council.list_members()
        self.assertGreaterEqual(len(members), 8)

        # Case 1: Low-cost reasonable proposal
        review_ok = council.review_proposal(
            topic="Upgrade Channel Manager API",
            proposal="Implement real-time sync with rate parity verification",
            proposal_data={"cost": 12000.0, "authority": "AUTOMATIC_IDEMPOTENT"}
        )
        self.assertIn(review_ok["consensus"], ["UNANIMOUS_CONSENSUS", "APPROVED_WITH_CAUTIONS"])
        self.assertGreaterEqual(len(review_ok["member_analyses"]), 5)

        # Case 2: High-risk excessive expenditure proposal
        review_expensive = council.review_proposal(
            topic="Unilateral Fleet Purchase",
            proposal="Buy luxury fleet without owner signoff",
            proposal_data={"cost": 1500000.0, "authority": "NEVER_ALLOWED"}
        )
        self.assertEqual(review_expensive["consensus"], "REJECTED_BY_COUNCIL")
        self.assertTrue(any(a["role"] == CouncilRoleType.CFO and a["stance"] == "REJECT" for a in review_expensive["member_analyses"]))

        debates = council.list_debates(limit=5)
        self.assertGreaterEqual(len(debates), 2)

    def test_chief_of_staff_dossier_and_queue(self):
        cos = ChiefOfStaff(tenant_id=self.tenant_id, company_id=self.company.company_id)
        item_id = cos.add_inbox_item(
            item_type="DEADLINE",
            title="GST Filing Q3",
            details="Statutory compliance filing deadline in 48 hours",
            priority="HIGH"
        )
        self.assertTrue(item_id.startswith("cos_"))

        dossier = cos.compile_executive_dossier()
        self.assertEqual(dossier["company_id"], self.company.company_id)
        self.assertGreaterEqual(len(dossier["chief_of_staff_queue"]), 1)

        # Resolve item
        cos.resolve_item(item_id, resolution_notes="Filing completed and receipt verified")
        open_items = cos.list_items(status="OPEN")
        self.assertFalse(any(i["item_id"] == item_id for i in open_items))

if __name__ == "__main__":
    unittest.main()
