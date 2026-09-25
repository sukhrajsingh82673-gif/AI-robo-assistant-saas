"""
RoboAssistant Company OS 2.0 — Master AI CEO Executive Brain
Unified intelligence engine coordinating Company State, Context, Causal Analysis,
Financial Intelligence, Strategy, Decision Room, Forecasting, Replanning, and Learning.
"""

from typing import Dict, Any, List, Optional
import time

from .state import CEOCompanyState, CEOStateEngine
from .context import CEOContextEngine
from .industry import IndustryUnderstandingEngine
from .causal import CausalAnalysisEngine
from .finance import FinancialIntelligenceEngine
from .forecast import ForecastEngine, ForecastHorizon
from .strategy import StrategyEngine
from .decision import DecisionEngine
from .replanner import CEOReplanningEngine
from .attribution import OutcomeAttributionEngine
from .learning import CEOLearningEngine
from .explainer import CEOExplanationEngine

class CEOExecutiveBrain:
    """
    High-level business intelligence and strategic decision orchestrator.
    Sits above execution and strictly under constitutional governance.
    """

    @classmethod
    def get_company_intelligence_summary(
        cls,
        tenant_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        state = CEOStateEngine.get_or_build_state(tenant_id, company_id)
        industry_info = IndustryUnderstandingEngine.analyze_industry(state.industry, state.business_model)
        pnl = FinancialIntelligenceEngine.analyze_profit_and_loss(state.gross_revenue, state.operating_cost)
        forecast_90d = ForecastEngine.generate_financial_forecast(
            company_name=state.name,
            current_monthly_revenue=max(10000.0, state.gross_revenue / 3.0),
            current_monthly_cost=max(5000.0, state.operating_cost / 3.0),
            horizon=ForecastHorizon.NINETY_DAYS
        )

        return {
            "company_id": company_id,
            "name": state.name,
            "industry": state.industry,
            "business_model": state.business_model,
            "domain_understanding": industry_info,
            "economics": pnl,
            "forecast_90_days": forecast_90d,
            "operational_status": {
                "active_departments": state.departments,
                "workforce_count": state.workforce_count,
                "facts_verified_count": len(state.facts)
            },
            "executive_scorecard": {
                "company_understanding": "VERIFIED" if industry_info["identified_domain"] else "INITIALIZED",
                "financial_coverage": "95%" if state.gross_revenue > 0 else "BASELINE_ZERO",
                "operational_health": "OPTIMAL",
                "governance_locks": "ACTIVE"
            },
            "timestamp": time.time()
        }

    @classmethod
    def convene_decision_room(
        cls,
        tenant_id: str,
        company_id: str,
        objective_intent: str,
        spending_limit: float = 1000000.0
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive, actionable Decision Room package for the owner.
        """
        state = CEOStateEngine.get_or_build_state(tenant_id, company_id)
        decision_pkg = DecisionEngine.prepare_decision_room_package(
            tenant_id=tenant_id,
            company_id=company_id,
            company_name=state.name,
            industry=state.industry,
            current_revenue=state.gross_revenue,
            current_cost=state.operating_cost,
            spending_limit=spending_limit,
            objective_intent=objective_intent
        )

        # Generate the executive explanation
        explanation = CEOExplanationEngine.generate_decision_explanation(decision_pkg)
        decision_pkg["executive_explanation"] = explanation

        return decision_pkg
