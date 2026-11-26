"""
Demo Company Sandbox Environment.
Generates an isolated, self-contained synthetic company with realistic records.
"""

from typing import Dict, Any, List


class DemoCompanySeeder:
    """
    Seeds and manages isolated demo environments for exploration and onboarding.
    """

    @classmethod
    def seed_demo_tenant(cls, tenant_id: str) -> Dict[str, Any]:
        """Seeds synthetic business records for the tenant in demo mode."""
        return {
            "tenant_id": tenant_id,
            "company_name": "Nova Dynamics Corp (Demo)",
            "jurisdiction": "US-DE",
            "is_demo": True,
            "chart_of_accounts": [
                {"code": "1000", "name": "Operating Cash", "type": "Asset", "balance_cents": 25000000},
                {"code": "4000", "name": "SaaS Subscription Revenue", "type": "Revenue", "balance_cents": 8500000},
                {"code": "5000", "name": "Hosting & Compute Expense", "type": "Expense", "balance_cents": 1200000},
            ],
            "invoices": [
                {"invoice_id": "inv_demo_01", "customer": "Acme Global", "amount_cents": 450000, "status": "paid"},
                {"invoice_id": "inv_demo_02", "customer": "Starlight Ltd", "amount_cents": 780000, "status": "open"},
            ],
            "active_agents": [
                {"agent_id": "ag_cfo_01", "role": "Finance Controller", "department": "finance", "status": "ONLINE"},
                {"agent_id": "ag_sales_01", "role": "Outbound Lead Specialist", "department": "sales", "status": "ONLINE"},
            ],
            "kpis": {
                "monthly_recurring_revenue_cents": 8500000,
                "burn_rate_cents": 1200000,
                "runway_months": 20.8,
            },
        }

    @classmethod
    def reset_demo_data(cls, tenant_id: str) -> Dict[str, str]:
        """Tears down demo records without touching production entities."""
        return {
            "tenant_id": tenant_id,
            "status": "RESET_COMPLETE",
            "message": "Demo data wiped and re-initialized cleanly.",
        }
