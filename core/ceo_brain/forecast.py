"""
RoboAssistant Company OS 2.0 — Business Forecasting Engine
Generates bounded multi-horizon economic projections with explicit uncertainty ranges.
Rule: Forecasts must never be represented as measured facts (FORECAST ≠ FACT).
"""

from typing import Dict, Any, List, Optional
import time

class ForecastHorizon:
    SEVEN_DAYS = "7_days"
    THIRTY_DAYS = "30_days"
    NINETY_DAYS = "90_days"
    TWELVE_MONTHS = "12_months"

class ForecastEngine:
    """
    Produces forward-looking business projections with uncertainty ranges and assumptions.
    """

    @classmethod
    def generate_financial_forecast(
        cls,
        company_name: str,
        current_monthly_revenue: float,
        current_monthly_cost: float,
        horizon: str = ForecastHorizon.NINETY_DAYS,
        growth_assumption_pct: float = 5.0
    ) -> Dict[str, Any]:
        # Multipliers based on horizon
        horizon_months = {
            ForecastHorizon.SEVEN_DAYS: 0.25,
            ForecastHorizon.THIRTY_DAYS: 1.0,
            ForecastHorizon.NINETY_DAYS: 3.0,
            ForecastHorizon.TWELVE_MONTHS: 12.0
        }.get(horizon, 3.0)

        growth_rate = 1.0 + (growth_assumption_pct / 100.0)
        expected_rev = current_monthly_revenue * horizon_months * growth_rate
        expected_cost = current_monthly_cost * horizon_months * (1.0 + (growth_assumption_pct * 0.4 / 100.0))
        expected_contribution = expected_rev - expected_cost

        # Uncertainty intervals (±15% for revenue, ±8% for cost)
        rev_low = expected_rev * 0.85
        rev_high = expected_rev * 1.15
        cost_low = expected_cost * 0.92
        cost_high = expected_cost * 1.08

        return {
            "forecast_id": f"fc_{int(time.time() * 1000)}",
            "company_name": company_name,
            "horizon": horizon,
            "horizon_months": horizon_months,
            "epistemic_status": "ESTIMATED_FORECAST",
            "is_fact": False,
            "projections": {
                "gross_revenue": {
                    "expected": round(expected_rev, 2),
                    "low": round(rev_low, 2),
                    "high": round(rev_high, 2)
                },
                "operating_cost": {
                    "expected": round(expected_cost, 2),
                    "low": round(cost_low, 2),
                    "high": round(cost_high, 2)
                },
                "net_contribution": {
                    "expected": round(expected_contribution, 2),
                    "low": round(rev_low - cost_high, 2),
                    "high": round(rev_high - cost_low, 2)
                }
            },
            "explicit_assumptions": [
                f"Underlying baseline monthly growth paces at ~{growth_assumption_pct}%.",
                "Operating cost scales at 40% marginal rate against revenue expansion.",
                "No black-swan macroeconomic or regulatory disruption occurs within horizon."
            ],
            "data_coverage": "HISTORICAL_LEDGER_RUN_RATE",
            "generated_at": time.time()
        }
