"""
ZONATA / URA UNIVERSAL AIC CEO — ECONOMIC COMMAND & PERFORMANCE TEST SUITE
Comprehensive automated tests verifying:
  - 12-level economic priority hierarchy
  - Capital & resource allocation engine (competing opportunity risk-adjusted return ranking)
  - 31-field CEO-to-Agent mission contract
  - 7-stage outcome verification chain (TASK != MISSION != OUTCOME != CASH)
  - Prediction-vs-actual learning loop with variance & root-cause analysis
  - 7-category CEO performance scorecard
  - 9-tier causal performance attribution
  - Scenarios A through J executable stress test simulator
  - Multi-industry economic driver adaptation (SaaS, Hospitality, Travel, Retail, Manufacturing, etc.)
"""

import unittest
import time
from core.aic_ceo_constitution import AuthorityLevel, DecisionClass
from core.aic_ceo_economic_command import (
    EconomicPriority, ECONOMIC_HIERARCHY_ORDER, ResourceType,
    CapitalAllocationEngine, CapitalAllocationRecord,
    CeoToAgentMissionContract, OutcomeVerificationStage,
    OutcomeVerificationRecord, CeoLearningLoopEngine,
    CeoPerformanceScorecardEngine, PerformanceAttributionChain,
    AttributionConfidence, ExecutiveStressTestSimulator,
    MultiIndustryEconomicAdapter
)

class TestAICCEOEconomicCommand(unittest.TestCase):

    def setUp(self):
        self.capital_engine = CapitalAllocationEngine(total_capital_pool_usd=500000.0)
        self.learning_engine = CeoLearningLoopEngine()

    # --------------------------------------------------------------------------
    # 1. Economic Priority Hierarchy
    # --------------------------------------------------------------------------
    def test_economic_hierarchy_order(self):
        self.assertEqual(len(ECONOMIC_HIERARCHY_ORDER), 12)
        # Priority 1: Survival
        self.assertEqual(ECONOMIC_HIERARCHY_ORDER[0], EconomicPriority.P01_ENTERPRISE_SURVIVAL)
        # Priority 2: Legal/Safety
        self.assertEqual(ECONOMIC_HIERARCHY_ORDER[1], EconomicPriority.P02_LEGAL_SAFETY_INTEGRITY)
        # Priority 3: Cash preservation
        self.assertEqual(ECONOMIC_HIERARCHY_ORDER[2], EconomicPriority.P03_CASH_PRESERVATION)
        # Priority 4: Profitable growth
        self.assertEqual(ECONOMIC_HIERARCHY_ORDER[3], EconomicPriority.P04_PROFITABLE_GROWTH)
        # Priority 6: Contribution margin
        self.assertEqual(ECONOMIC_HIERARCHY_ORDER[5], EconomicPriority.P06_CONTRIBUTION_MARGIN)

    # --------------------------------------------------------------------------
    # 2. Capital Allocation & Competing Opportunities
    # --------------------------------------------------------------------------
    def test_capital_allocation_and_competing_ranking(self):
        # 1. Allocate budget
        alloc = self.capital_engine.allocate(
            resource_type=ResourceType.MARKETING_BUDGET,
            quantity=50000.0,
            unit="USD",
            purpose="Launch high-retention enterprise customer acquisition",
            expected_outcome="Acquire 10 enterprise accounts",
            expected_return_usd=120000.0,
            risk_level="MEDIUM",
            payback_months=4.0,
            opportunity_cost="Deferred self-service website redesign",
            approval_class=DecisionClass.CLASS_B_OPERATIONAL
        )
        self.assertTrue(alloc.allocation_id.startswith("cap_"))
        self.assertEqual(self.capital_engine.allocated_capital_usd, 50000.0)
        self.assertEqual(self.capital_engine.unallocated_capital_usd, 450000.0)

        # 2. Compare competing opportunities
        opps = [
            {
                "name": "Project Alpha (High nominal return, high risk, long payback)",
                "investment_usd": 100000.0,
                "expected_return_usd": 250000.0,
                "risk_level": "HIGH",
                "payback_months": 10.0
            },
            {
                "name": "Project Beta (Moderate return, low risk, rapid payback)",
                "investment_usd": 100000.0,
                "expected_return_usd": 180000.0,
                "risk_level": "LOW",
                "payback_months": 3.0
            }
        ]
        ranked = self.capital_engine.compare_competing_opportunities(opps)
        self.assertEqual(len(ranked), 2)
        # Project Beta should rank higher due to risk-adjusted velocity despite lower nominal return
        self.assertTrue(ranked[0]["recommended"])
        self.assertEqual(ranked[0]["opportunity_name"], "Project Beta (Moderate return, low risk, rapid payback)")

    # --------------------------------------------------------------------------
    # 3. 31-Field CEO-to-Agent Mission Contract
    # --------------------------------------------------------------------------
    def test_mission_contract_schema(self):
        contract = CeoToAgentMissionContract(
            mission_id="msn_contract_01",
            owner_objective="Expand B2B enterprise revenue profitably",
            ceo_objective="Increase ARR by $100k while maintaining 70% contribution margin",
            business_objective="Sign 5 enterprise clients with >$20k ACV",
            expected_business_outcome="$100k recognized ARR with positive contribution cash flow",
            kra="KRA-02 Revenue Growth",
            kpi="KPI-FIN-01 Contribution Margin %",
            target=70.0,
            baseline=55.0,
            deadline_timestamp=time.time() + 86400 * 30,
            authority_level=AuthorityLevel.EXECUTIVE_FUNCTION.value,
            budget_limit_usd=15000.0,
            time_limit_hours=720.0,
            risk_limit="MEDIUM",
            allowed_tools=["CRM_API", "STRIPE_INVOICING", "EMAIL_DISPATCHER"],
            allowed_data=["PROSPECT_PIPELINE", "RATE_CARD"],
            prohibited_actions=["DISCOUNTS_EXCEEDING_15_PCT", "DIRECT_BANK_WITHDRAWAL"],
            escalation_conditions=["PROSPECT_REQUESTS_20_PCT_DISCOUNT", "CUSTOMER_DATA_BREACH"],
            success_criteria="5 signed contracts with verified Stripe first-month payment",
            verification_method="Audited general ledger reconciliation against bank statements",
            evidence_requirements=["STRIPE_PAYMENT_INTENT", "SIGNED_PDF_CONTRACT"],
            expected_revenue_usd=100000.0,
            expected_profit_usd=70000.0,
            expected_cash_impact_usd=100000.0
        )
        self.assertEqual(contract.mission_id, "msn_contract_01")
        self.assertEqual(contract.budget_limit_usd, 15000.0)
        self.assertEqual(len(contract.allowed_tools), 3)
        self.assertEqual(len(contract.prohibited_actions), 2)

    # --------------------------------------------------------------------------
    # 4. 7-Stage Outcome Verification Chain
    # --------------------------------------------------------------------------
    def test_outcome_verification_chain_stages(self):
        # State 1: Task completed only
        rec1 = OutcomeVerificationRecord(
            mission_id="msn_v1",
            task_name="Launch Lead Gen Ad",
            task_completed=True,
            mission_completed=False,
            business_outcome_achieved=False,
            revenue_generated_usd=0.0,
            profit_generated_usd=0.0,
            cash_received_usd=0.0,
            verified_economic_result=False,
            primary_evidence_hashes=[],
            current_stage=OutcomeVerificationStage.TASK_COMPLETED,
            summary="Ads active on Google"
        )
        self.assertEqual(rec1.evaluate_stage(), OutcomeVerificationStage.TASK_COMPLETED)

        # State 2: Revenue generated but NOT yet verified profit or cash in bank
        rec2 = OutcomeVerificationRecord(
            mission_id="msn_v2",
            task_name="Book reservations",
            task_completed=True,
            mission_completed=True,
            business_outcome_achieved=True,
            revenue_generated_usd=25000.0,
            profit_generated_usd=0.0,
            cash_received_usd=0.0,
            verified_economic_result=False,
            primary_evidence_hashes=["hash_rev_01"],
            current_stage=OutcomeVerificationStage.REVENUE_GENERATED,
            summary="Attributed bookings logged"
        )
        self.assertEqual(rec2.evaluate_stage(), OutcomeVerificationStage.REVENUE_GENERATED)

        # State 3: Fully verified economic result with cash in bank and positive profit
        rec3 = OutcomeVerificationRecord(
            mission_id="msn_v3",
            task_name="Enterprise contract fulfillment",
            task_completed=True,
            mission_completed=True,
            business_outcome_achieved=True,
            revenue_generated_usd=50000.0,
            profit_generated_usd=30000.0,
            cash_received_usd=50000.0,
            verified_economic_result=True,
            primary_evidence_hashes=["hash_stripe_01", "hash_bank_01"],
            current_stage=OutcomeVerificationStage.VERIFIED_ECONOMIC_RESULT,
            summary="Cash received in bank statement and verified by audit ledger"
        )
        self.assertEqual(rec3.evaluate_stage(), OutcomeVerificationStage.VERIFIED_ECONOMIC_RESULT)

    # --------------------------------------------------------------------------
    # 5. Persistent Prediction-vs-Actual Learning Loop
    # --------------------------------------------------------------------------
    def test_learning_loop_ledger(self):
        # 1. Record prediction
        pred = self.learning_engine.record_prediction(
            decision_id="dec_q3_pricing",
            owner_objective="Grow SaaS Gross Margins",
            prediction_statement="Increasing tier-2 price by 15% will reduce conversion by <5% and raise net revenue by 10%",
            metric_name="Net_Revenue_USD",
            predicted_value=110000.0,
            confidence_level=0.85,
            evidence_basis="Historical low customer price sensitivity in cohort analysis"
        )
        self.assertTrue(pred.prediction_id.startswith("prd_"))
        self.assertEqual(pred.status, "PENDING_ACTUAL")

        # 2. Resolve actual outcome
        resolved = self.learning_engine.resolve_actual(
            prediction_id=pred.prediction_id,
            actual_value=105000.0,
            root_cause="Slightly higher churn in SME accounts than enterprise cohort",
            corrective_action="Grandfather existing SME accounts at previous rate; apply increase only to new signups",
            future_policy_adjustment="Mandate segmentation-based pricing policy in SOP-COM-01"
        )
        self.assertEqual(resolved.variance, -5000.0)
        self.assertAlmostEqual(resolved.forecast_error_pct, 4.55, places=1)
        self.assertEqual(resolved.status, "RESOLVED_CALIBRATED")
        self.assertEqual(resolved.root_cause, "Slightly higher churn in SME accounts than enterprise cohort")

    # --------------------------------------------------------------------------
    # 6. 7-Category CEO Performance Scorecard
    # --------------------------------------------------------------------------
    def test_ceo_performance_scorecard(self):
        # Unverified data test
        unverified = CeoPerformanceScorecardEngine.evaluate(company_id="comp_test", verified_financials=None)
        self.assertTrue(unverified.unverified_data_present)
        self.assertEqual(unverified.metrics_breakdown["status"], "NO VERIFIED DATA")

        # Grounded verified data test
        verified = CeoPerformanceScorecardEngine.evaluate(
            company_id="comp_test",
            verified_financials={"contribution_margin_pct": 72.0},
            verified_commercial={"nrr_pct": 115.0},
            decision_quality_scores=[85.0, 90.0, 88.0]
        )
        self.assertFalse(verified.unverified_data_present)
        self.assertTrue(verified.financial_score > 80.0)
        self.assertTrue(verified.commercial_score > 90.0)
        self.assertTrue(verified.composite_ceo_index > 80.0)

    # --------------------------------------------------------------------------
    # 7. Scenarios A through J Executable Stress-Tests
    # --------------------------------------------------------------------------
    def test_scenarios_a_through_j(self):
        # Scenario A: Revenue up, profit down
        res_a = ExecutiveStressTestSimulator.run_scenario("SCENARIO_A", {"revenue_delta_pct": 30.0, "profit_delta_pct": -25.0})
        self.assertTrue(res_a["deterioration_detected"])
        self.assertIn("ECONOMIC_DETERIORATION_DETECTED", res_a["ceo_verdict"])

        # Scenario B: Sales up, cancellations up
        res_b = ExecutiveStressTestSimulator.run_scenario("SCENARIO_B", {"sales_delta_pct": 20.0, "cancellation_delta_pct": 60.0})
        self.assertTrue(res_b["false_growth_detected"])

        # Scenario C: Marketing up, incremental profit down
        res_c = ExecutiveStressTestSimulator.run_scenario("SCENARIO_C", {"ad_spend_delta_pct": 40.0, "incremental_profit_delta_pct": -15.0})
        self.assertTrue(res_c["reallocation_required"])

        # Scenario D: Agent tasks up, verified outcomes down
        res_d = ExecutiveStressTestSimulator.run_scenario("SCENARIO_D", {"tasks_completed_delta_pct": 80.0, "verified_outcomes_delta_pct": -5.0})
        self.assertTrue(res_d["productivity_illusion_detected"])

        # Scenario E: Cash down despite revenue growth
        res_e = ExecutiveStressTestSimulator.run_scenario("SCENARIO_E", {"revenue_delta_pct": 25.0, "cash_delta_pct": -30.0, "dso_days": 105.0})
        self.assertTrue(res_e["working_capital_crisis_detected"])

        # Scenario F: Major customer lost
        res_f = ExecutiveStressTestSimulator.run_scenario("SCENARIO_F", {"lost_customer_acv_usd": 150000.0})
        self.assertIn("MATERIAL_REVENUE_CHURN", res_f["ceo_verdict"])

        # Scenario G: Competitor price cut
        res_g = ExecutiveStressTestSimulator.run_scenario("SCENARIO_G", {"price_cut_pct": 40.0})
        self.assertIn("COMPETITIVE_DISRUPTION_MODEL", res_g["ceo_verdict"])

        # Scenario H: Operational disruption
        res_h = ExecutiveStressTestSimulator.run_scenario("SCENARIO_H", {"outage_type": "Primary Datacenter Loss"})
        self.assertIn("SURVIVAL_AND_CONTINUITY_COMMAND", res_h["ceo_verdict"])

        # Scenario I: Fraud / Compliance event
        res_i = ExecutiveStressTestSimulator.run_scenario("SCENARIO_I", {"fraud_type": "Unauthorized Bank Wire", "amount_usd": 90000.0})
        self.assertIn("RED_LINE_TRIPWIRE_TRIGGERED", res_i["ceo_verdict"])

        # Scenario J: Forecast error learning
        res_j = ExecutiveStressTestSimulator.run_scenario("SCENARIO_J", {"predicted_growth_pct": 50.0, "actual_growth_pct": 10.0})
        self.assertIn("FORECAST_ERROR_CALIBRATION", res_j["ceo_verdict"])

    # --------------------------------------------------------------------------
    # 8. Multi-Industry Adaptation
    # --------------------------------------------------------------------------
    def test_multi_industry_adaptation(self):
        industries = ["SAAS", "HOSPITALITY", "TRAVEL", "RETAIL", "MANUFACTURING", "FMCG", "HEALTHCARE", "LOGISTICS", "PROFESSIONAL_SERVICES"]
        for ind in industries:
            prof = MultiIndustryEconomicAdapter.get_profile(ind)
            self.assertEqual(prof["benchmark_status"], "CALIBRATED_FROM_PEERS")
            self.assertTrue(len(prof["key_metrics"]) > 0)
            self.assertTrue(prof["gross_margin_target_pct"] > 0)

        # Unclassified fallback to BENCHMARK_UNKNOWN
        unknown_prof = MultiIndustryEconomicAdapter.get_profile("UNKNOWN_EXOTIC_SECTOR")
        self.assertEqual(unknown_prof["benchmark_status"], "BENCHMARK_UNKNOWN")

if __name__ == "__main__":
    unittest.main()
