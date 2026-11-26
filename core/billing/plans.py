"""
Subscription Plans and Pricing Models as Data (ADR 0048, Rules 78, 79).
Minor integer cents only.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass(frozen=True)
class SubscriptionPlan:
    plan_id: str
    code: str
    name: str
    tier: str  # free, starter, team, enterprise
    base_fee_cents: int
    included_tokens: int
    overage_rate_cents_per_million: int
    currency: str = "USD"
    features: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def calculate_period_fee(self, used_tokens: int) -> Dict[str, int]:
        """Calculates total fee in cents including base fee and token overages."""
        overage_tokens = max(0, used_tokens - self.included_tokens)
        # Overage calculated in million token increments (integer ceil arithmetic)
        if overage_tokens > 0 and self.overage_rate_cents_per_million > 0:
            millions = (overage_tokens + 999_999) // 1_000_000
            overage_cents = millions * self.overage_rate_cents_per_million
        else:
            overage_cents = 0

        total_cents = self.base_fee_cents + overage_cents
        return {
            "base_fee_cents": self.base_fee_cents,
            "overage_tokens": overage_tokens,
            "overage_cents": overage_cents,
            "total_cents": total_cents,
        }


class PlanRegistry:
    """Registry of canonical versioned subscription plans."""

    CANONICAL_PLANS = {
        "community": SubscriptionPlan(
            plan_id="plan_community_v1",
            code="community",
            name="Community Free",
            tier="free",
            base_fee_cents=0,
            included_tokens=100_000,
            overage_rate_cents_per_million=0,
            currency="USD",
            features={"api_rate_limit_rps": 5, "custom_webhooks": False, "marketplace_install": True},
        ),
        "starter": SubscriptionPlan(
            plan_id="plan_starter_v1",
            code="starter",
            name="Starter Growth",
            tier="starter",
            base_fee_cents=2900,  # $29.00
            included_tokens=1_000_000,
            overage_rate_cents_per_million=400,  # $4.00 / M tokens
            currency="USD",
            features={"api_rate_limit_rps": 20, "custom_webhooks": False, "marketplace_install": True},
        ),
        "team": SubscriptionPlan(
            plan_id="plan_team_v1",
            code="team",
            name="Team Standard",
            tier="team",
            base_fee_cents=9900,  # $99.00
            included_tokens=5_000_000,
            overage_rate_cents_per_million=300,  # $3.00 / M tokens
            currency="USD",
            features={"api_rate_limit_rps": 50, "custom_webhooks": True, "marketplace_install": True},
        ),
        "enterprise": SubscriptionPlan(
            plan_id="plan_enterprise_v1",
            code="enterprise",
            name="Enterprise Custom",
            tier="enterprise",
            base_fee_cents=49900,  # $499.00
            included_tokens=50_000_000,
            overage_rate_cents_per_million=150,  # $1.50 / M tokens
            currency="USD",
            features={"api_rate_limit_rps": 500, "custom_webhooks": True, "marketplace_install": True, "sso": True},
        ),
    }

    @classmethod
    def get_plan(cls, code: str) -> SubscriptionPlan:
        plan = cls.CANONICAL_PLANS.get(code.lower())
        if not plan:
            raise KeyError(f"Plan code '{code}' not recognized. Available: {list(cls.CANONICAL_PLANS.keys())}")
        return plan

    @classmethod
    def list_plans(cls) -> List[SubscriptionPlan]:
        return list(cls.CANONICAL_PLANS.values())
