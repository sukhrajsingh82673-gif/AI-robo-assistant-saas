"""
RoboAssistant Company OS 2.0 — AI CEO Executive Intelligence Test Suite
Verifies Milestone CEO-01:
1. CEO Live State Engine & Epistemic Tracking
2. CEO Context Engine Token-Efficient Packaging & Isolation
3. Industry Understanding & Adaptive Domain Models
4. Causal Analysis & Grounded Evidence Chains
5. CFO-Grade Financial Breakdown & Cost Leakage Detection
6. Multi-Horizon Forecasting with Uncertainty Intervals
7. Strategy Engine Multi-Option Comparison & "Do Nothing" Baseline
8. Decision Room Synthesis, Digital Twin Validation & Governance Clearance
9. Autonomous Replanning on Material Outcome Variance
10. Decoupled Business Outcome Attribution & Confounder Control
11. CEO Learning Engine & Strategic Lesson Persistence
12. Executive Explanation Answering "Why?" Without Hidden Chain-of-Thought
13. Strategic Decision Room NL Directive Pipeline in CeoCommandEngine
"""

import sys
import unittest
import time
import uuid

sys.path.insert(0, "/roboassistant")

from core.db import db
from core.auth import TenantManager, UserManager, UserRole
from core.models import OperatingContext
from core.portfolio import CompanyPortfolioManager
from core.ceo import CeoCommandEngine
from core.ceo_brain import (
    CEOStateEngine,
    CEOContextEngine,
    IndustryUnderstandingEngine,
    CausalAnalysisEngine,
    FinancialIntelligenceEngine,
    ForecastEngine,
    ForecastHorizon,
    StrategyEngine,
    DecisionEngine,
    CEOReplanningEngine,
    OutcomeAttributionEngine,
    CEOLearningEngine,
    CEOExplanationEngine,
    CEOExecutiveBrain
)

class TestCEOExecutiveIntelligence(unittest.TestCase):

    def setUp(self):
        self.tenant = TenantManager.create_tenant(f"CEO-2.0 Tenant {uuid.uuid4().hex[:6]}")
        self.tenant_id = self.tenant["tenant_id"]
        self.owner = UserManager.create_user(self.tenant_id, "owner@enterprise.ai", "Chief Executive", UserRole.OWNER)

        self.portfolio_mgr = CompanyPortfolioManager(tenant_id=self.tenant_id, load_from_db=False)
        self.ceo_engine = CeoCommandEngine(self.portfolio_mgr)

        self.comp_id = f"comp_{uuid.uuid4().hex[:8]}"
        self.ctx = OperatingContext(
            company_id=self.comp_id,
            name="Grand Heritage Palace & Spa",
            industry="Hospitality",
            company_type="EXISTING",
            status="OPERATIONAL",
            revenue=12500000.0,
            cost=9200000.0,
            contribution=3300000.0,
            departments=["Executive", "Operations", "Revenue Management", "Guest Services"],
            workforce={},
            missions=[],
            data_sources=[],
            operating_rules=["MAX_DISCRETIONARY_SPEND: ₹10,00,000"],
            understanding_pct=95.0,
            baseline_summary={"status": "OPERATIONAL_BASELINE"}
        )
        self.portfolio_mgr.register_company(self.ctx)

    def test_01_ceo_live_state_and_epistemic_facts(self):
        """CEO Live State Engine maintains live economics, operations, and source-attributed facts."""
        state = CEOStateEngine.get_or_build_state(self.tenant_id, self.comp_id, name="Grand Heritage Palace", industry="Hospitality")
        state.set_fact("occupancy_rate", "84%", source="Opera PMS", truth_state="MEASURED", confidence=0.98)

        fact = state.get_fact("occupancy_rate")
        self.assertIsNotNone(fact)
        self.assertEqual(fact["value"], "84%")
        self.assertEqual(fact["source"], "Opera PMS")
        self.assertEqual(fact["truth_state"], "MEASURED")

        d = state.to_dict()
        self.assertIn("economics", d)
        self.assertIn("operations", d)
        self.assertEqual(d["identity"]["industry"], "Hospitality")

    def test_02_context_engine_minimal_package_isolation(self):
        """CEO Context Engine builds minimal, permission-isolated context package for decisions."""
        state = CEOStateEngine.get_or_build_state(self.tenant_id, self.comp_id)
        state.gross_revenue = 12500000.0
        state.operating_cost = 9200000.0
        state.contribution_margin = 3300000.0

        ctx_pkg = CEOContextEngine.assemble_context_package(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            intent="Evaluate profitability growth"
        )
        self.assertEqual(ctx_pkg["company_name"], "Grand Heritage Palace & Spa")
        self.assertIn("financial_state", ctx_pkg)
        self.assertIn("gross_revenue", ctx_pkg["financial_state"])
        self.assertIn("epistemic_facts", ctx_pkg)

    def test_03_industry_understanding_adaptive_discovery(self):
        """Industry Understanding Engine adapts to Hospitality, Manufacturing, SaaS without hardcoding."""
        hotel_model = IndustryUnderstandingEngine.analyze_industry("Hospitality")
        self.assertTrue(hotel_model["identified_domain"])
        self.assertIn("RevPAR", [k["name"] for k in hotel_model["standard_kpis"]])

        mfg_model = IndustryUnderstandingEngine.analyze_industry("Precision Manufacturing")
        self.assertTrue(mfg_model["identified_domain"])
        self.assertIn("OEE (Overall Equipment Effectiveness)", [k["name"] for k in mfg_model["standard_kpis"]])

        saas_model = IndustryUnderstandingEngine.analyze_industry("B2B SaaS Enterprise")
        self.assertTrue(saas_model["identified_domain"])
        self.assertIn("Monthly Churn Rate", [k["name"] for k in saas_model["standard_kpis"]])

    def test_04_causal_reasoning_and_grounded_evidence(self):
        """Causal Analysis Engine investigates revenue variance with evidence and alternative explanations."""
        facts = [{"metric": "Occupancy Rate", "value": "58%", "source": "Opera PMS", "confidence": 0.95}]
        res = CausalAnalysisEngine.investigate_revenue_variance(
            current_revenue=8000000.0,
            target_or_prior_revenue=10000000.0,
            known_facts=facts
        )
        self.assertEqual(res["variance_type"], "NEGATIVE_SHORTFALL")
        self.assertEqual(res["primary_driver"], "Occupancy Rate")
        self.assertGreaterEqual(res["causal_confidence"], 0.8)
        self.assertGreater(len(res["alternative_explanations"]), 0)

    def test_05_cfo_grade_financial_analysis_and_leakage(self):
        """Financial Intelligence Engine decomposes P&L and discovers cost leakages."""
        pnl = FinancialIntelligenceEngine.analyze_profit_and_loss(
            gross_revenue=15000000.0,
            operating_cost=10000000.0
        )
        self.assertEqual(pnl["net_contribution"], 5000000.0)
        self.assertAlmostEqual(pnl["contribution_margin_pct"], 33.33, places=1)
        self.assertEqual(pnl["financial_health_status"], "PROFITABLE")

        leaks = FinancialIntelligenceEngine.diagnose_cost_leakage("Hospitality", 10000000.0, [])
        self.assertGreater(len(leaks), 0)
        self.assertIn("OTA Commission Drag", [l["leakage_category"] for l in leaks])

    def test_06_bounded_forecasting_uncertainty_and_assumptions(self):
        """Forecast Engine produces multi-horizon projections labeled ESTIMATED_FORECAST (FORECAST != FACT)."""
        fc = ForecastEngine.generate_financial_forecast(
            company_name="Grand Heritage Palace",
            current_monthly_revenue=4000000.0,
            current_monthly_cost=3000000.0,
            horizon=ForecastHorizon.NINETY_DAYS,
            growth_assumption_pct=6.0
        )
        self.assertEqual(fc["epistemic_status"], "ESTIMATED_FORECAST")
        self.assertFalse(fc["is_fact"])
        self.assertIn("projections", fc)
        self.assertGreater(fc["projections"]["gross_revenue"]["high"], fc["projections"]["gross_revenue"]["low"])
        self.assertGreater(len(fc["explicit_assumptions"]), 0)

    def test_07_strategy_engine_multi_option_and_do_nothing(self):
        """Strategy Engine evaluates multiple strategic options plus Do Nothing baseline."""
        strat = StrategyEngine.evaluate_profitability_strategy(
            company_name="Grand Heritage Palace",
            industry="Hospitality",
            current_revenue=12000000.0,
            current_cost=9000000.0,
            spending_limit=1000000.0
        )
        opts = strat["options"]
        self.assertEqual(len(opts), 4)
        option_titles = [o["title"] for o in opts]
        self.assertIn("Do Nothing (Baseline Status Quo)", option_titles)
        self.assertIsNotNone(strat["top_recommendation"])
        self.assertGreater(strat["top_recommendation"]["expected_business_value"], 0.0)

    def test_08_decision_room_synthesis_and_reversibility(self):
        """Decision Engine produces formal Decision Room package with Digital Twin simulation and rollback check."""
        room = DecisionEngine.prepare_decision_room_package(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            company_name="Grand Heritage Palace & Spa",
            industry="Hospitality",
            current_revenue=12000000.0,
            current_cost=9000000.0,
            spending_limit=1000000.0
        )
        self.assertIn("decision_id", room)
        self.assertIn("simulation_result", room)
        self.assertEqual(room["simulation_result"]["state_label"], "SIMULATED")
        self.assertIn("rollback_feasible", room["simulation_result"])
        self.assertTrue(room["governance_status"]["requires_owner_approval"])
        self.assertIn("governance_status", room)
        self.assertIn("operational_status_pipeline", room)

    def test_09_autonomous_replanning_on_variance(self):
        """CEO Replanning Engine detects material underperformance and generates corrective action."""
        replan = CEOReplanningEngine.evaluate_variance_and_replan(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            mission_id="msn_q3_rev",
            target_revenue_delta=1000000.0,
            actual_revenue_delta=600000.0,
            cost_incurred=300000.0,
            primary_barrier="Direct booking conversion dropped 15%"
        )
        self.assertTrue(replan["replanning_required"])
        self.assertIn("corrective_actions", replan)
        self.assertEqual(len(replan["corrective_actions"]), 2)

    def test_10_outcome_attribution_and_confounders(self):
        """Outcome Attribution Engine separates task completion from measured business value with confounders."""
        initiatives = [
            {"id": "init_pricing", "name": "Dynamic Weekend Pricing Yield", "evidence_score": 0.90},
            {"id": "init_seo", "name": "Direct Booking Landing Page SEO", "evidence_score": 0.40}
        ]
        attr = OutcomeAttributionEngine.attribute_outcome(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            total_observed_gain=500000.0,
            initiatives=initiatives
        )
        self.assertEqual(attr["total_observed_gain"], 500000.0)
        self.assertEqual(len(attr["attributed_initiatives"]), 2)
        pricing_init = [i for i in attr["attributed_initiatives"] if i["initiative_id"] == "init_pricing"][0]
        self.assertEqual(pricing_init["confidence"], "HIGH")
        self.assertGreater(pricing_init["attributed_gain"], 300000.0)
        self.assertIn("confounding_variables_analyzed", attr)

    def test_11_ceo_learning_and_strategic_memory(self):
        """CEO Learning Engine records prediction vs reality lessons and retrieves strategic memory."""
        record = CEOLearningEngine.record_learning_event(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            decision_id="dec_test_01",
            predicted_outcome="Expected +₹4.5L from Meta Ads",
            actual_outcome="Actual +₹2.1L contribution",
            variance_summary="-53% conversion shortfall",
            root_cause="Overestimated lookalike audience intent during off-season",
            strategic_lesson="Require localized guest verification before scaling off-season digital ad budgets",
            updated_policy_rule="AI_OFF_SEASON_AD_CAP: Limit digital ad spend to ₹1.5L during low season without owner signoff."
        )
        self.assertIsNotNone(record["event_id"])

        lessons = CEOLearningEngine.query_lessons(self.tenant_id, self.comp_id)
        self.assertGreater(len(lessons), 0)
        self.assertEqual(lessons[0]["decision_id"], "dec_test_01")

    def test_12_executive_explanation_why_questions(self):
        """CEO Explanation Engine answers critical executive questions without exposing hidden reasoning."""
        room = DecisionEngine.prepare_decision_room_package(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            company_name="Grand Heritage Palace & Spa",
            industry="Hospitality",
            current_revenue=12000000.0,
            current_cost=9000000.0
        )
        expl = CEOExplanationEngine.generate_decision_explanation(room)
        self.assertIn("why_this", expl)
        self.assertIn("why_now", expl)
        self.assertIn("what_evidence", expl)
        self.assertIn("what_happens_if_we_do_nothing", expl)
        self.assertIn("can_we_roll_it_back", expl)
        self.assertIn("how_will_we_verify_it_worked", expl)

    def test_13_natural_language_decision_room_directive(self):
        """CeoCommandEngine synthesizes strategic directives into governed Decision Room packages."""
        res = self.ceo_engine.execute_directive(
            company_id=self.comp_id,
            directive="Convene the strategic decision room to increase hotel profitability"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["command_type"], "STRATEGIC_DECISION_PACKAGE")
        self.assertEqual(res["stage"], "DECISION_ROOM_CONVENED")
        self.assertIn("decision_package", res)
        self.assertIn("simulation_result", res["decision_package"])

if __name__ == "__main__":
    unittest.main()
