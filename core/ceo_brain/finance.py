"""
RoboAssistant Company OS 2.0 — Financial Intelligence & CFO Engine
Provides CFO-grade P&L breakdown, margin analysis, unit economics, and cost leakage detection.
"""

from typing import Dict, Any, List, Optional

class FinancialIntelligenceEngine:
    """
    Analyzes corporate economics, tracks spending variances, and pinpoints margin leakage.
    """

    @classmethod
    def analyze_profit_and_loss(
        cls,
        gross_revenue: float,
        operating_cost: float,
        cost_breakdown: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        contribution = gross_revenue - operating_cost
        margin_pct = (contribution / gross_revenue * 100.0) if gross_revenue > 0 else 0.0

        breakdown = cost_breakdown or {
            "Personnel & Contractors": operating_cost * 0.40,
            "Direct Operations / COGS": operating_cost * 0.35,
            "Software & Infrastructure": operating_cost * 0.15,
            "Administrative & Facilities": operating_cost * 0.10
        }

        # Identify highest cost driver
        sorted_costs = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        top_cost_driver = sorted_costs[0] if sorted_costs else ("General Operations", operating_cost)

        return {
            "gross_revenue": gross_revenue,
            "operating_cost": operating_cost,
            "net_contribution": contribution,
            "contribution_margin_pct": round(margin_pct, 2),
            "cost_breakdown": breakdown,
            "primary_cost_driver": {
                "category": top_cost_driver[0],
                "amount": top_cost_driver[1],
                "percentage_of_total_cost": round((top_cost_driver[1] / operating_cost * 100.0), 1) if operating_cost > 0 else 0.0
            },
            "financial_health_status": "PROFITABLE" if contribution > 0 else "DEFICIT_OR_PRE_REVENUE"
        }

    @classmethod
    def diagnose_cost_leakage(
        cls,
        industry: str,
        operating_cost: float,
        facts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Scans for common operational cost leakages based on industry patterns.
        """
        leakages = []
        ind = industry.lower()

        if "hotel" in ind or "hospitality" in ind:
            leakages.append({
                "leakage_category": "OTA Commission Drag",
                "estimated_waste_monthly": round(operating_cost * 0.08, 2),
                "cause": "Over-reliance on third-party OTAs (Booking/Agoda) at 18-22% commission.",
                "mitigation": "Launch targeted repeat guest direct-booking incentive campaign."
            })
            leakages.append({
                "leakage_category": "Energy / Utility Off-Peak Drift",
                "estimated_waste_monthly": round(operating_cost * 0.03, 2),
                "cause": "HVAC running in unoccupied banquet and block suites.",
                "mitigation": "Automate PMS check-out integration with smart climate setback."
            })
        elif "mfg" in ind or "manufacturing" in ind:
            leakages.append({
                "leakage_category": "Tooling Wear Downtime",
                "estimated_waste_monthly": round(operating_cost * 0.10, 2),
                "cause": "Reactive maintenance replacing spindle inserts after catastrophic failure.",
                "mitigation": "Implement predictive vibration monitoring to replace inserts at 80% life."
            })
        elif "saas" in ind or "software" in ind:
            leakages.append({
                "leakage_category": "Cloud Sprawl & Zombie Instances",
                "estimated_waste_monthly": round(operating_cost * 0.07, 2),
                "cause": "Over-provisioned test clusters and orphaned RDS snapshots.",
                "mitigation": "Enforce auto-termination policies on staging environments."
            })
        else:
            leakages.append({
                "leakage_category": "Software Tool Sprawl",
                "estimated_waste_monthly": round(operating_cost * 0.05, 2),
                "cause": "Unused SaaS seats and overlapping collaboration tools.",
                "mitigation": "Audit active user licenses and consolidate vendor contracts."
            })

        return leakages
