"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
SaaS Multi-Tenant Usage Ledger, Entitlement Engine & Payment Adapters
=====================================================================
Manages tenant subscription tiers, usage metering, quota enforcement,
and external payment provider synchronizations (Stripe & Razorpay).

Constitutional Invariant:
  ZONATA IS THE SOLE ENTITLEMENT AUTHORITY.
  The workflow is strictly: Plan -> Entitlement -> Quota -> Usage -> Authorization.
  Payment gateways (Stripe/Razorpay) process transactions; they NEVER decide business authorization.
"""

import os
import time
import json
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("zonata.saas.billing")

class SubscriptionTier(str, Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

@dataclass
class PlanEntitlements:
    tier: SubscriptionTier
    monthly_price_usd: float
    max_tokens_per_month: int
    max_browser_minutes_per_month: int
    max_terminal_seconds_per_month: int
    max_storage_bytes: int
    max_agents: int
    max_seats: int
    features_allowed: List[str]

# Canonical Plan Entitlement Catalog
TIER_ENTITLEMENTS = {
    SubscriptionTier.FREE: PlanEntitlements(
        tier=SubscriptionTier.FREE,
        monthly_price_usd=0.0,
        max_tokens_per_month=1_000_000,
        max_browser_minutes_per_month=60,
        max_terminal_seconds_per_month=600,
        max_storage_bytes=1024 * 1024 * 500,     # 500 MB
        max_agents=2,
        max_seats=1,
        features_allowed=["core_agents", "basic_terminal", "sqlite_db"]
    ),
    SubscriptionTier.STARTER: PlanEntitlements(
        tier=SubscriptionTier.STARTER,
        monthly_price_usd=49.0,
        max_tokens_per_month=10_000_000,
        max_browser_minutes_per_month=600,
        max_terminal_seconds_per_month=6000,
        max_storage_bytes=1024 * 1024 * 1024 * 5,  # 5 GB
        max_agents=10,
        max_seats=5,
        features_allowed=["core_agents", "browser_use", "universal_terminal", "evidence_ledger", "web_scraping"]
    ),
    SubscriptionTier.PRO: PlanEntitlements(
        tier=SubscriptionTier.PRO,
        monthly_price_usd=199.0,
        max_tokens_per_month=50_000_000,
        max_browser_minutes_per_month=3000,
        max_terminal_seconds_per_month=30000,
        max_storage_bytes=1024 * 1024 * 1024 * 50, # 50 GB
        max_agents=50,
        max_seats=25,
        features_allowed=["core_agents", "browser_use", "universal_terminal", "evidence_ledger", "tool_factory", "temporal_workflows", "s3_minio", "custom_tools"]
    ),
    SubscriptionTier.ENTERPRISE: PlanEntitlements(
        tier=SubscriptionTier.ENTERPRISE,
        monthly_price_usd=999.0,
        max_tokens_per_month=500_000_000,
        max_browser_minutes_per_month=50000,
        max_terminal_seconds_per_month=500000,
        max_storage_bytes=1024 * 1024 * 1024 * 1000, # 1 TB
        max_agents=500,
        max_seats=100,
        features_allowed=["all_features", "dedicated_nodes", "custom_llms", "air_gapped_deployment", "unlimited_evidence"]
    )
}

@dataclass
class TenantUsageSnapshot:
    tenant_id: str
    tier: SubscriptionTier
    cycle_start: float
    cycle_end: float
    tokens_consumed: int = 0
    browser_minutes_consumed: float = 0.0
    terminal_seconds_consumed: float = 0.0
    storage_bytes_consumed: int = 0
    api_calls_count: int = 0
    total_cost_usd: float = 0.0
    payment_status: str = "ACTIVE"   # ACTIVE, PAST_DUE, CANCELED

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d

class StripeBillingAdapter:
    """Stripe Billing integration adapter for international subscriptions and metered billing."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("STRIPE_API_KEY", "sk_test_zonata_stripe_mock")

    def create_customer(self, tenant_id: str, email: str, company_name: str = "Enterprise") -> Dict[str, Any]:
        logger.info(f"STRIPE: Created customer for tenant {tenant_id} ({email})")
        return {"success": True, "stripe_customer_id": f"cus_{uuid.uuid4().hex[:14]}", "email": email, "tenant_id": tenant_id}

    def sync_metered_usage(self, stripe_subscription_item_id: str, quantity: int) -> Dict[str, Any]:
        logger.info(f"STRIPE: Metered usage synced: {quantity} units to {stripe_subscription_item_id}")
        return {"synced": True, "quantity": quantity, "timestamp": time.time()}

class RazorpayBillingAdapter:
    """Razorpay Billing integration adapter for Indian domestic subscriptions and invoices."""
    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "rzp_test_zonata_mock")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "mock_secret")

    def create_customer(self, tenant_id: str, email: str, company_name: str = "Enterprise") -> Dict[str, Any]:
        logger.info(f"RAZORPAY: Created customer for tenant {tenant_id} ({email})")
        return {"success": True, "razorpay_customer_id": f"cust_{uuid.uuid4().hex[:14]}", "email": email, "tenant_id": tenant_id}

    def create_order(self, amount_inr: float, tenant_id: str, receipt: str) -> Dict[str, Any]:
        logger.info(f"RAZORPAY: Order created INR {amount_inr} for tenant {tenant_id}")
        return {"order_id": f"order_{uuid.uuid4().hex[:14]}", "amount_paise": int(amount_inr * 100), "status": "CREATED"}

class SaasBillingEngine:
    """
    ZONATA Multi-Tenant SaaS Billing & Entitlement Engine.
    Tracks monthly consumption against tier quotas and enforces hard limits.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SaasBillingEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._tenants: Dict[str, TenantUsageSnapshot] = {}
        self.stripe = StripeBillingAdapter()
        self.razorpay = RazorpayBillingAdapter()
        self._lock = threading.RLock()

    def get_or_create_tenant(self, tenant_id: str, tier: SubscriptionTier = SubscriptionTier.STARTER) -> TenantUsageSnapshot:
        with self._lock:
            if tenant_id not in self._tenants:
                now = time.time()
                self._tenants[tenant_id] = TenantUsageSnapshot(
                    tenant_id=tenant_id,
                    tier=tier,
                    cycle_start=now,
                    cycle_end=now + (86400 * 30)
                )
            return self._tenants[tenant_id]

    def check_entitlement(
        self,
        tenant_id: str,
        metric: str,
        requested_amount: float = 1.0
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a requested action is allowed under the tenant's current plan and quota.
        """
        tenant = self.get_or_create_tenant(tenant_id)
        if tenant.payment_status == "PAST_DUE":
            return False, "Account past due: Payment required to continue operations"

        plan = TIER_ENTITLEMENTS.get(tenant.tier, TIER_ENTITLEMENTS[SubscriptionTier.FREE])

        if metric == "tokens":
            if (tenant.tokens_consumed + requested_amount) > plan.max_tokens_per_month:
                return False, f"Quota exceeded: Plan allows {plan.max_tokens_per_month:,} tokens/mo"

        elif metric == "browser_minutes":
            if (tenant.browser_minutes_consumed + requested_amount) > plan.max_browser_minutes_per_month:
                return False, f"Quota exceeded: Plan allows {plan.max_browser_minutes_per_month:,} browser minutes/mo"

        elif metric == "terminal_seconds":
            if (tenant.terminal_seconds_consumed + requested_amount) > plan.max_terminal_seconds_per_month:
                return False, f"Quota exceeded: Plan allows {plan.max_terminal_seconds_per_month:,} terminal seconds/mo"

        elif metric == "storage_bytes":
            if (tenant.storage_bytes_consumed + requested_amount) > plan.max_storage_bytes:
                return False, f"Quota exceeded: Storage limit of {plan.max_storage_bytes / (1024**3):.1f} GB reached"

        elif metric == "feature":
            feature_name = str(requested_amount)
            if "all_features" not in plan.features_allowed and feature_name not in plan.features_allowed:
                return False, f"Feature '{feature_name}' not entitled under {plan.tier.value} plan. Upgrade required."

        return True, "Entitlement granted"

    def record_usage(
        self,
        tenant_id: str,
        metric: str,
        amount: float,
        cost_usd: float = 0.0
    ):
        """Records consumption event into the tenant's active usage ledger."""
        with self._lock:
            tenant = self.get_or_create_tenant(tenant_id)
            if metric == "tokens":
                tenant.tokens_consumed += int(amount)
            elif metric == "browser_minutes":
                tenant.browser_minutes_consumed += amount
            elif metric == "terminal_seconds":
                tenant.terminal_seconds_consumed += amount
            elif metric == "storage_bytes":
                tenant.storage_bytes_consumed += int(amount)
            elif metric == "api_call":
                tenant.api_calls_count += int(amount)

            tenant.total_cost_usd += cost_usd
            logger.info(f"USAGE RECORDED: [{tenant_id}] Metric: {metric} Amount: {amount} (Total Cost: ${tenant.total_cost_usd:.4f})")

    def upgrade_plan(self, tenant_id: str, new_tier: SubscriptionTier) -> TenantUsageSnapshot:
        with self._lock:
            tenant = self.get_or_create_tenant(tenant_id)
            tenant.tier = new_tier
            logger.info(f"PLAN UPGRADED: Tenant {tenant_id} upgraded to {new_tier.value}")
            return tenant

# Global singleton instance
saas_billing_engine = SaasBillingEngine.get_instance()

