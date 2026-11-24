"""
Unit Economic Cost Modeling Engine per Company and Task Type (Rule 76 & ADR 0045)
Calculates predictable operating unit costs in integer minor units (USD cents) across:
- Token inference (Prompt & Completion)
- Database IO and storage
- Network egress
Projects monthly operating budgets and comparative human cost savings.
"""

from typing import Dict, Any, List
from dataclasses import dataclass


# Standard pricing benchmarks (in USD minor units / cents)
PRICING_TABLE = {
    "TOKEN_PROMPT_PER_1K_MINOR": 0.15,       # $0.0015 per 1K tokens
    "TOKEN_COMPLETION_PER_1K_MINOR": 0.60,   # $0.0060 per 1K tokens
    "DB_TRANSACTION_PER_100_MINOR": 0.05,     # $0.0005 per 100 queries
    "STORAGE_GB_MONTH_MINOR": 2.0,            # $0.02 per GB-month
    "HUMAN_HOURLY_LOADED_RATE_USD": 35.0,     # $35.00/hour
}

# Task archetype resource profiles
TASK_ARCHETYPES = {
    "AP_INVOICE_MATCH": {
        "prompt_tokens": 1200,
        "completion_tokens": 300,
        "db_queries": 8,
        "human_equivalent_minutes": 15.0,
    },
    "FREIGHT_BILL_OF_LADING": {
        "prompt_tokens": 1500,
        "completion_tokens": 450,
        "db_queries": 12,
        "human_equivalent_minutes": 12.0,
    },
    "MONTH_END_CONSOLIDATION_RUN": {
        "prompt_tokens": 3000,
        "completion_tokens": 800,
        "db_queries": 50,
        "human_equivalent_minutes": 120.0,
    },
    "CUSTOMER_SUPPORT_DISPATCH": {
        "prompt_tokens": 600,
        "completion_tokens": 150,
        "db_queries": 4,
        "human_equivalent_minutes": 8.0,
    },
    "PAYROLL_CALCULATION_LINE": {
        "prompt_tokens": 400,
        "completion_tokens": 100,
        "db_queries": 6,
        "human_equivalent_minutes": 5.0,
    },
}


class UnitCostModel:
    """Calculates granular unit economics and monthly budget projections."""

    @classmethod
    def calculate_task_unit_cost(cls, task_type: str) -> Dict[str, Any]:
        """Calculates itemized cost in minor units (cents) for a single task execution."""
        profile = TASK_ARCHETYPES.get(task_type, {
            "prompt_tokens": 1000,
            "completion_tokens": 250,
            "db_queries": 5,
            "human_equivalent_minutes": 10.0,
        })

        token_cost_minor = (
            (profile["prompt_tokens"] / 1000.0) * PRICING_TABLE["TOKEN_PROMPT_PER_1K_MINOR"]
            + (profile["completion_tokens"] / 1000.0) * PRICING_TABLE["TOKEN_COMPLETION_PER_1K_MINOR"]
        )
        db_cost_minor = (profile["db_queries"] / 100.0) * PRICING_TABLE["DB_TRANSACTION_PER_100_MINOR"]

        total_unit_cost_minor = token_cost_minor + db_cost_minor

        # Human cost comparison
        human_hours = profile["human_equivalent_minutes"] / 60.0
        human_cost_minor = human_hours * (PRICING_TABLE["HUMAN_HOURLY_LOADED_RATE_USD"] * 100.0)

        savings_pct = (
            ((human_cost_minor - total_unit_cost_minor) / human_cost_minor) * 100.0
            if human_cost_minor > 0
            else 0.0
        )

        return {
            "task_type": task_type,
            "total_unit_cost_minor": round(total_unit_cost_minor, 3),
            "unit_cost_usd": round(total_unit_cost_minor / 100.0, 4),
            "token_cost_minor": round(token_cost_minor, 3),
            "db_cost_minor": round(db_cost_minor, 3),
            "human_cost_usd": round(human_cost_minor / 100.0, 2),
            "savings_percent": round(savings_pct, 2),
        }

    @classmethod
    def project_monthly_company_budget(
        cls,
        company_id: str,
        task_volume_monthly: Dict[str, int]
    ) -> Dict[str, Any]:
        """Projects total monthly operating expenditure and cost savings for a tenant company."""
        total_monthly_cost_minor = 0.0
        total_human_cost_usd = 0.0
        breakdown = {}

        for task_type, volume in task_volume_monthly.items():
            unit = cls.calculate_task_unit_cost(task_type)
            task_total_minor = unit["total_unit_cost_minor"] * volume
            task_human_total_usd = unit["human_cost_usd"] * volume

            total_monthly_cost_minor += task_total_minor
            total_human_cost_usd += task_human_total_usd

            breakdown[task_type] = {
                "monthly_volume": volume,
                "unit_cost_usd": unit["unit_cost_usd"],
                "total_cost_usd": round(task_total_minor / 100.0, 2),
                "human_cost_usd": round(task_human_total_usd, 2),
                "savings_percent": unit["savings_percent"],
            }

        total_system_usd = round(total_monthly_cost_minor / 100.0, 2)
        net_savings_usd = round(total_human_cost_usd - total_system_usd, 2)
        overall_savings_pct = (
            round((net_savings_usd / total_human_cost_usd) * 100.0, 2)
            if total_human_cost_usd > 0
            else 0.0
        )

        return {
            "company_id": company_id,
            "projected_monthly_system_cost_usd": total_system_usd,
            "projected_monthly_human_cost_usd": round(total_human_cost_usd, 2),
            "projected_monthly_net_savings_usd": net_savings_usd,
            "overall_savings_percent": overall_savings_pct,
            "task_breakdown": breakdown,
        }
