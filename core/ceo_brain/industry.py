"""
RoboAssistant Company OS 2.0 — Industry Understanding & Business Model Engine
Adapts strategic reasoning and KPI discovery across diverse business sectors.
Never assumes a single generic operational schema.
"""

from typing import Dict, Any, List, Optional

class IndustryUnderstandingEngine:
    """
    Discovers industry-specific revenue engines, cost structures, and KPI hierarchies.
    """

    INDUSTRY_MODELS = {
        "hospitality": {
            "primary_revenue_engines": ["Room Nights", "Food & Beverage", "Banquet & Events", "Ancillary Services"],
            "core_cost_drivers": ["Labor / Housekeeping", "OTA Commissions", "Linen & Supplies", "Energy & Utilities"],
            "primary_kpis": [
                {"name": "Occupancy Rate", "unit": "%", "benchmark": 75.0},
                {"name": "ADR (Average Daily Rate)", "unit": "INR", "benchmark": 5200.0},
                {"name": "RevPAR", "unit": "INR", "benchmark": 3900.0},
                {"name": "OTA Share of Bookings", "unit": "%", "benchmark": 40.0},
                {"name": "Direct Booking Ratio", "unit": "%", "benchmark": 45.0}
            ],
            "typical_leaks": ["Excessive OTA commissions", "F&B shrinkage", "Unsold room capacity", "Utility overruns"]
        },
        "manufacturing": {
            "primary_revenue_engines": ["Finished Goods Shipments", "Contract Machining", "Spare Parts"],
            "core_cost_drivers": ["Raw Materials", "Machine Maintenance", "Labor Shifts", "Scrap & Rework"],
            "primary_kpis": [
                {"name": "OEE (Overall Equipment Effectiveness)", "unit": "%", "benchmark": 85.0},
                {"name": "Scrap Rate", "unit": "%", "benchmark": 2.0},
                {"name": "Unplanned Downtime", "unit": "hours", "benchmark": 4.0},
                {"name": "Yield Percentage", "unit": "%", "benchmark": 98.0},
                {"name": "Unit Manufacturing Cost", "unit": "INR", "benchmark": 1200.0}
            ],
            "typical_leaks": ["Thermal machine drift", "Tooling wear downtime", "Raw material wastage", "Quality defects"]
        },
        "saas": {
            "primary_revenue_engines": ["Subscription Licenses", "Usage Add-ons", "Enterprise Support"],
            "core_cost_drivers": ["Cloud Infrastructure / AWS", "Sales & Marketing", "Engineering R&D", "Customer Success"],
            "primary_kpis": [
                {"name": "Monthly Churn Rate", "unit": "%", "benchmark": 2.5},
                {"name": "Net Revenue Retention (NRR)", "unit": "%", "benchmark": 115.0},
                {"name": "Customer Acquisition Cost (CAC)", "unit": "INR", "benchmark": 15000.0},
                {"name": "LTV to CAC Ratio", "unit": "ratio", "benchmark": 3.5},
                {"name": "Gross Margin", "unit": "%", "benchmark": 80.0}
            ],
            "typical_leaks": ["Underutilized cloud instances", "Trial drop-off", "Involuntary payment failures", "Feature abandonment"]
        },
        "restaurant": {
            "primary_revenue_engines": ["Dine-In Covers", "Takeaway & Delivery", "Beverage Sales"],
            "core_cost_drivers": ["Food & Ingredient Cost (COGS)", "Kitchen Staff Labor", "Delivery Aggregator Commission", "Rent"],
            "primary_kpis": [
                {"name": "Food Cost Ratio", "unit": "%", "benchmark": 30.0},
                {"name": "Table Turnover Rate", "unit": "turns/day", "benchmark": 3.5},
                {"name": "Average Check Size", "unit": "INR", "benchmark": 1800.0},
                {"name": "Daily Covers", "unit": "covers", "benchmark": 160.0}
            ],
            "typical_leaks": ["Perishable ingredient spoilage", "30% aggregator commissions", "Table dead time"]
        },
        "ecommerce": {
            "primary_revenue_engines": ["Direct-to-Consumer Orders", "Marketplace Sales", "Wholesale Bulk"],
            "core_cost_drivers": ["Digital Ad Spend (Meta/Google)", "Warehousing & Fulfillment", "Payment Gateway Fees", "Returns"],
            "primary_kpis": [
                {"name": "ROAS (Return on Ad Spend)", "unit": "x", "benchmark": 3.8},
                {"name": "Average Order Value (AOV)", "unit": "INR", "benchmark": 2400.0},
                {"name": "Return Rate (RTO)", "unit": "%", "benchmark": 12.0},
                {"name": "Store Conversion Rate", "unit": "%", "benchmark": 2.8}
            ],
            "typical_leaks": ["Return-to-origin courier waste", "Ad creative fatigue", "Abandoned carts", "Out of stock popular SKUs"]
        }
    }

    @classmethod
    def analyze_industry(cls, industry_name: str, business_model: Optional[str] = None) -> Dict[str, Any]:
        ind_key = industry_name.lower().strip()
        matched_model = None
        for k, v in cls.INDUSTRY_MODELS.items():
            if k in ind_key:
                matched_model = v
                break

        if matched_model:
            return {
                "industry": industry_name,
                "identified_domain": True,
                "revenue_engines": matched_model["primary_revenue_engines"],
                "cost_drivers": matched_model["core_cost_drivers"],
                "standard_kpis": matched_model["primary_kpis"],
                "common_leakage_vectors": matched_model["typical_leaks"]
            }

        # Generic commercial business model fallback
        return {
            "industry": industry_name,
            "identified_domain": False,
            "revenue_engines": ["Direct Sales", "Client Engagements", "Service Contracts"],
            "cost_drivers": ["Operational Expenses", "Personnel", "Technology / Software", "Marketing"],
            "standard_kpis": [
                {"name": "Gross Contribution Margin", "unit": "%", "benchmark": 25.0},
                {"name": "Revenue Growth MoM", "unit": "%", "benchmark": 10.0},
                {"name": "Operating Cost Ratio", "unit": "%", "benchmark": 75.0}
            ],
            "common_leakage_vectors": ["SaaS tool sprawl", "Process bottlenecks", "Billing delay"]
        }
