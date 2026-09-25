"""
RoboAssistant Company OS 2.0 — Strategic Formulation & Multi-Option Engine
Evaluates business objectives, generates comparative strategic options (A, B, C + Do Nothing),
and calculates multi-dimensional Expected Value.
"""

from typing import Dict, Any, List, Optional
import time

class StrategicOption:
    def __init__(
        self,
        option_id: str,
        title: str,
        description: str,
        expected_revenue_delta: float,
        expected_cost_delta: float,
        time_to_impact_days: int,
        risk_level: str,
        reversibility: str,
        confidence: float,
        required_authority: str,
        workforce_department: str
    ):
        self.option_id = option_id
        self.title = title
        self.description = description
        self.expected_revenue_delta = expected_revenue_delta
        self.expected_cost_delta = expected_cost_delta
        self.expected_contribution = expected_revenue_delta - expected_cost_delta
        self.time_to_impact_days = time_to_impact_days
        self.risk_level = risk_level
        self.reversibility = reversibility
        self.confidence = confidence
        self.required_authority = required_authority
        self.workforce_department = workforce_department

        # Expected Value calculation: (Benefit - Cost) * Confidence - Risk Penalty
        risk_penalty = 0.0
        if risk_level == "HIGH":
            risk_penalty = 50000.0
        elif risk_level == "MEDIUM":
            risk_penalty = 15000.0

        self.expected_business_value = round((self.expected_contribution * confidence) - risk_penalty, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "title": self.title,
            "description": self.description,
            "expected_revenue_delta": self.expected_revenue_delta,
            "expected_cost_delta": self.expected_cost_delta,
            "expected_contribution": self.expected_contribution,
            "expected_business_value": self.expected_business_value,
            "time_to_impact_days": self.time_to_impact_days,
            "risk_level": self.risk_level,
            "reversibility": self.reversibility,
            "confidence": self.confidence,
            "required_authority": self.required_authority,
            "workforce_department": self.workforce_department
        }

class StrategyEngine:
    """
    Formulates strategic options for corporate objectives and ranks them by Expected Business Value.
    """

    @classmethod
    def evaluate_profitability_strategy(
        cls,
        company_name: str,
        industry: str,
        current_revenue: float,
        current_cost: float,
        spending_limit: float = 1000000.0,
        horizon_days: int = 90
    ) -> Dict[str, Any]:
        options = []

        # Option A: Channel / Pricing Optimization
        options.append(StrategicOption(
            option_id="opt_a",
            title="Direct Channel & Dynamic Pricing Optimization",
            description="Shift 15% of intermediary/OTA volume to direct bookings and optimize weekend rate yield.",
            expected_revenue_delta=round(current_revenue * 0.12, 2),
            expected_cost_delta=min(spending_limit * 0.25, 250000.0),
            time_to_impact_days=30,
            risk_level="LOW",
            reversibility="HIGH",
            confidence=0.88,
            required_authority="AUTOMATIC_IDEMPOTENT",
            workforce_department="Revenue & Marketing"
        ))

        # Option B: Operational Leakage & Tool Sprawl Reduction
        options.append(StrategicOption(
            option_id="opt_b",
            title="Operational Leakage & Waste Elimination",
            description="Audit supplier contracts, automate utility shutdowns, and consolidate idle software seats.",
            expected_revenue_delta=0.0,
            expected_cost_delta=-round(current_cost * 0.08, 2),  # Cost reduction
            time_to_impact_days=14,
            risk_level="LOW",
            reversibility="HIGH",
            confidence=0.94,
            required_authority="AUTOMATIC_IDEMPOTENT",
            workforce_department="Operations"
        ))

        # Option C: Targeted Customer Acquisition Campaign
        options.append(StrategicOption(
            option_id="opt_c",
            title="High-Intent Acquisition Campaign",
            description="Deploy automated multi-channel marketing campaigns targeted at corporate accounts.",
            expected_revenue_delta=round(current_revenue * 0.20, 2),
            expected_cost_delta=min(spending_limit * 0.60, 600000.0),
            time_to_impact_days=45,
            risk_level="MEDIUM",
            reversibility="MEDIUM",
            confidence=0.75,
            required_authority="ASK_ME",
            workforce_department="Commercial"
        ))

        # Option D: Baseline "Do Nothing" (Section 67)
        options.append(StrategicOption(
            option_id="opt_do_nothing",
            title="Do Nothing (Baseline Status Quo)",
            description="Maintain existing operations without additional capital expenditure or intervention.",
            expected_revenue_delta=0.0,
            expected_cost_delta=0.0,
            time_to_impact_days=0,
            risk_level="MEDIUM",  # Risk of inflation and competitor erosion
            reversibility="IMMEDIATE",
            confidence=1.0,
            required_authority="AUTOMATIC_IDEMPOTENT",
            workforce_department="Executive"
        ))

        # Sort options by expected business value descending (excluding do_nothing from top ranking if value is zero)
        ranked_options = sorted([o for o in options if o.option_id != "opt_do_nothing"], key=lambda x: x.expected_business_value, reverse=True)
        top_recommendation = ranked_options[0] if ranked_options else options[0]

        return {
            "strategic_objective": f"Increase {company_name} profitability over {horizon_days} days within ₹ {spending_limit:,.2f} spend cap.",
            "horizon_days": horizon_days,
            "spending_cap": spending_limit,
            "options": [o.to_dict() for o in options],
            "top_recommendation": top_recommendation.to_dict(),
            "recommendation_rationale": (
                f"Option '{top_recommendation.title}' delivers highest Expected Business Value "
                f"(₹ {top_recommendation.expected_business_value:,.2f}) with high reversibility "
                f"and {int(top_recommendation.confidence * 100)}% confidence."
            ),
            "generated_at": time.time()
        }
