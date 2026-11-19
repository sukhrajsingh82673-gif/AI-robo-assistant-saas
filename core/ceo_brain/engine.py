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

        # Never extrapolate a forecast from invented baseline values. A forecast
        # is only produced when the tenant has actual booked financial data.
        has_financials = (state.gross_revenue > 0.0 or state.operating_cost > 0.0)
        if has_financials:
            forecast_90d = ForecastEngine.generate_financial_forecast(
                company_name=state.name,
                current_monthly_revenue=state.gross_revenue / 3.0,
                current_monthly_cost=state.operating_cost / 3.0,
                horizon=ForecastHorizon.NINETY_DAYS
            )
        else:
            forecast_90d = {
                "status": "INSUFFICIENT_DATA",
                "detail": (
                    "No booked revenue or cost exists for this company, so no forecast "
                    "is produced. Connect a finance system or enter verified figures."
                ),
            }

        if has_financials:
            financial_coverage = "AVAILABLE"
        elif state.facts:
            financial_coverage = "PARTIAL_FACTS_ONLY"
        else:
            financial_coverage = "MISSING"

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
            "data_availability": {
                "financials": has_financials,
                "financial_coverage": financial_coverage,
                "verified_facts": len(state.facts),
                "departments": bool(state.departments),
                "workforce": state.workforce_count > 0,
            },
            "timestamp": time.time(),
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
