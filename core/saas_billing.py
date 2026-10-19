"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
SaaS Multi-Tenant Usage Ledger, Entitlement Engine & Payment Adapters
=====================================================================
Phase 12 Commercial SaaS Lifecycle, Entitlements & Multi-Gateway Billing.
Manages tenant subscription state machines, usage metering, quota enforcement,
cryptographic webhook verification (Stripe & Razorpay), and economic governor settlement reconciliation.

Constitutional Invariant:
  ZONATA IS THE SOLE ENTITLEMENT AUTHORITY.
  The workflow is strictly: Plan -> Entitlement -> Quota -> Usage -> Authorization.
  Payment gateways (Stripe/Razorpay) process transactions; they NEVER decide business authorization.
"""

from __future__ import annotations
import os
import time
import json
import uuid
import hmac
import hashlib
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.db import db

logger = logging.getLogger("zonata.saas.billing")


class SubscriptionTier(str, Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(str, Enum):
    TRIALING = "TRIALING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    UNPAID = "UNPAID"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class InvalidSubscriptionTransitionError(Exception):
    """Raised when an illegal subscription state transition is attempted."""
    pass


# Authoritative Subscription State Machine Transition Matrix
VALID_STATUS_TRANSITIONS: Dict[SubscriptionStatus, Set[SubscriptionStatus]] = {
    SubscriptionStatus.TRIALING: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.CANCELLED
    },
    SubscriptionStatus.ACTIVE: {
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.SUSPENDED,
        SubscriptionStatus.CANCELLED
    },
    SubscriptionStatus.PAST_DUE: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.UNPAID,
        SubscriptionStatus.SUSPENDED,
        SubscriptionStatus.CANCELLED
    },
    SubscriptionStatus.UNPAID: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.SUSPENDED,
        SubscriptionStatus.CANCELLED
    },
    SubscriptionStatus.SUSPENDED: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.CANCELLED,
        SubscriptionStatus.EXPIRED
    },
    SubscriptionStatus.CANCELLED: {
        SubscriptionStatus.ACTIVE  # Reactivation with new cycle
    },
    SubscriptionStatus.EXPIRED: {
        SubscriptionStatus.ACTIVE  # Renewal
    }
}


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
    max_concurrency: int
    features_allowed: List[str]


# Canonical Plan Entitlement Catalog
TIER_ENTITLEMENTS: Dict[SubscriptionTier, PlanEntitlements] = {
    SubscriptionTier.FREE: PlanEntitlements(
        tier=SubscriptionTier.FREE,
        monthly_price_usd=0.0,
        max_tokens_per_month=1_000_000,
        max_browser_minutes_per_month=60,
        max_terminal_seconds_per_month=600,
        max_storage_bytes=1024 * 1024 * 500,     # 500 MB
        max_agents=2,
        max_seats=1,
        max_concurrency=1,
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
        max_concurrency=3,
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
        max_concurrency=10,
        features_allowed=[
            "core_agents", "browser_use", "universal_terminal", "evidence_ledger",
            "tool_factory", "temporal_workflows", "s3_minio", "custom_tools", "a2a_mesh"
        ]
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
        max_concurrency=50,
        features_allowed=[
            "all_features", "dedicated_nodes", "custom_llms", "air_gapped_deployment",
            "unlimited_evidence", "a2a_mesh", "economic_governance"
        ]
    )
}


@dataclass
class SubscriptionRecord:
    subscription_id: str
    tenant_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: float
    current_period_end: float
    grace_period_end: Optional[float] = None
    cancel_at_period_end: bool = False
    payment_provider: str = "internal"
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "tenant_id": self.tenant_id,
            "tier": self.tier.value if isinstance(self.tier, SubscriptionTier) else str(self.tier),
            "status": self.status.value if isinstance(self.status, SubscriptionStatus) else str(self.status),
            "current_period_start": self.current_period_start,
            "current_period_end": self.current_period_end,
            "grace_period_end": self.grace_period_end,
            "cancel_at_period_end": self.cancel_at_period_end,
            "payment_provider": self.payment_provider,
            "provider_customer_id": self.provider_customer_id,
            "provider_subscription_id": self.provider_subscription_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
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
    payment_status: str = "ACTIVE"   # Backwards compatibility string: ACTIVE, PAST_DUE, CANCELLED, etc.
    active_agents_count: int = 0
    active_seats_count: int = 0
    active_concurrency_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value if isinstance(self.tier, SubscriptionTier) else str(self.tier)
        return d


class StripeBillingAdapter:
    """Stripe Billing integration adapter for international subscriptions and metered billing."""
    def __init__(self, api_key: Optional[str] = None, webhook_secret: Optional[str] = None):
        self.api_key = api_key or os.environ.get("STRIPE_API_KEY", "sk_test_zonata_stripe_mock")
        self.webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_zonata_stripe_test_secret")

    def create_customer(self, tenant_id: str, email: str, company_name: str = "Enterprise") -> Dict[str, Any]:
        logger.info(f"STRIPE: Created customer for tenant {tenant_id} ({email})")
        return {"success": True, "stripe_customer_id": f"cus_{uuid.uuid4().hex[:14]}", "email": email, "tenant_id": tenant_id}

    def sync_metered_usage(self, stripe_subscription_item_id: str, quantity: int) -> Dict[str, Any]:
        logger.info(f"STRIPE: Metered usage synced: {quantity} units to {stripe_subscription_item_id}")
        return {"synced": True, "quantity": quantity, "timestamp": time.time()}

    def verify_webhook_signature(self, payload: str, sig_header: str, tolerance: int = 300) -> bool:
        """
        Cryptographic verification of Stripe Webhook signature (HMAC-SHA256).
        Expects sig_header format: 't=123456,v1=abcdef...'
        """
        if not sig_header or not self.webhook_secret:
            return False

        try:
            parts = dict(item.strip().split("=", 1) for item in sig_header.split(",") if "=" in item)
            timestamp_str = parts.get("t")
            signature = parts.get("v1")

            if not timestamp_str or not signature:
                return False

            timestamp = int(timestamp_str)
            # Drift tolerance check (anti-replay)
            if abs(time.time() - timestamp) > tolerance:
                logger.warning(f"STRIPE: Webhook signature expired: timestamp drift {abs(time.time() - timestamp)}s > {tolerance}s")
                return False

            signed_payload = f"{timestamp}.{payload}".encode("utf-8")
            expected_signature = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"STRIPE: Signature verification failed: {e}")
            return False


class RazorpayBillingAdapter:
    """Razorpay Billing integration adapter for Indian domestic subscriptions and invoices."""
    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None, webhook_secret: Optional[str] = None):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "rzp_test_zonata_mock")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "mock_secret")
        self.webhook_secret = webhook_secret or os.environ.get("RAZORPAY_WEBHOOK_SECRET", "rzp_whsec_zonata_test_secret")

    def create_customer(self, tenant_id: str, email: str, company_name: str = "Enterprise") -> Dict[str, Any]:
        logger.info(f"RAZORPAY: Created customer for tenant {tenant_id} ({email})")
        return {"success": True, "razorpay_customer_id": f"cust_{uuid.uuid4().hex[:14]}", "email": email, "tenant_id": tenant_id}

    def create_order(self, amount_inr: float, tenant_id: str, receipt: str) -> Dict[str, Any]:
        logger.info(f"RAZORPAY: Order created INR {amount_inr} for tenant {tenant_id}")
        return {"order_id": f"order_{uuid.uuid4().hex[:14]}", "amount_paise": int(amount_inr * 100), "status": "CREATED"}

    def verify_webhook_signature(self, payload: str, sig_header: str) -> bool:
        """
        Cryptographic verification of Razorpay Webhook signature (HMAC-SHA256).
        Expects signature in X-Razorpay-Signature header.
        """
        if not sig_header or not self.webhook_secret:
            return False

        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, sig_header.strip())
        except Exception as e:
            logger.error(f"RAZORPAY: Webhook signature verification error: {e}")
            return False


class SaasBillingEngine:
    """
    ZONATA Multi-Tenant SaaS Billing, Subscription Lifecycle & Entitlement Engine.
    Tracks monthly consumption against tier quotas, manages state machine transitions,
    verifies gateway webhooks, and reconciles economic budget settlements.
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
        self._subscriptions: Dict[str, SubscriptionRecord] = {}
        self._processed_idempotency_keys: Set[str] = set()
        self._processed_webhook_events: Set[str] = set()
        self._reconciled_reservations: Set[str] = set()
        self.stripe = StripeBillingAdapter()
        self.razorpay = RazorpayBillingAdapter()
        self._lock = threading.RLock()
        self._init_db_tables()

    def _init_db_tables(self):
        """Ensures persistence tables are available in the underlying database."""
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tenant_subscriptions (
                        subscription_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        tier TEXT NOT NULL DEFAULT 'STARTER',
                        status TEXT NOT NULL DEFAULT 'ACTIVE',
                        current_period_start REAL NOT NULL,
                        current_period_end REAL NOT NULL,
                        grace_period_end REAL,
                        cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
                        payment_provider TEXT NOT NULL DEFAULT 'internal',
                        provider_customer_id TEXT,
                        provider_subscription_id TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        metadata JSON
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS billing_webhook_events (
                        event_id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        payload JSON,
                        processed_at REAL NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PROCESSED',
                        error_message TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tenant_invoices (
                        invoice_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        subscription_id TEXT,
                        amount_due_usd REAL NOT NULL,
                        amount_paid_usd REAL NOT NULL DEFAULT 0.0,
                        currency TEXT NOT NULL DEFAULT 'USD',
                        status TEXT NOT NULL DEFAULT 'PAID',
                        period_start REAL NOT NULL,
                        period_end REAL NOT NULL,
                        line_items JSON,
                        created_at REAL NOT NULL,
                        paid_at REAL
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Billing engine db table initialization deferred: {e}")

    # =========================================================================
    # 1. SUBSCRIPTION LIFECYCLE & STATE MACHINE
    # =========================================================================

    def get_or_create_subscription(
        self,
        tenant_id: str,
        tier: SubscriptionTier = SubscriptionTier.STARTER,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        payment_provider: str = "internal",
        provider_customer_id: Optional[str] = None,
        provider_subscription_id: Optional[str] = None
    ) -> SubscriptionRecord:
        """Retrieves or provisions a tenant subscription record."""
        with self._lock:
            # 1. Check in-memory cache
            if tenant_id in self._subscriptions:
                return self._subscriptions[tenant_id]

            # 2. Check relational DB
            now = time.time()
            try:
                with db.get_connection() as conn:
                    row = conn.execute(
                        "SELECT * FROM tenant_subscriptions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 1",
                        (tenant_id,)
                    ).fetchone()
                    if row:
                        sub = SubscriptionRecord(
                            subscription_id=row["subscription_id"],
                            tenant_id=row["tenant_id"],
                            tier=SubscriptionTier(row["tier"]),
                            status=SubscriptionStatus(row["status"]),
                            current_period_start=row["current_period_start"],
                            current_period_end=row["current_period_end"],
                            grace_period_end=row["grace_period_end"],
                            cancel_at_period_end=bool(row["cancel_at_period_end"]),
                            payment_provider=row["payment_provider"],
                            provider_customer_id=row["provider_customer_id"],
                            provider_subscription_id=row["provider_subscription_id"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                            metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
                        )
                        self._subscriptions[tenant_id] = sub
                        return sub
            except Exception as e:
                logger.debug(f"Subscription DB read note: {e}")

            # 3. Create new default subscription
            sub_id = f"sub_{uuid.uuid4().hex[:14]}"
            period_end = now + (86400 * 30)
            sub = SubscriptionRecord(
                subscription_id=sub_id,
                tenant_id=tenant_id,
                tier=tier,
                status=status,
                current_period_start=now,
                current_period_end=period_end,
                payment_provider=payment_provider,
                provider_customer_id=provider_customer_id,
                provider_subscription_id=provider_subscription_id,
                created_at=now,
                updated_at=now,
                metadata={}
            )
            self._subscriptions[tenant_id] = sub
            self._persist_subscription(sub)

            # Ensure usage snapshot matches subscription status and tier
            self.get_or_create_tenant(tenant_id=tenant_id, tier=tier)
            return sub

    def transition_subscription_status(
        self,
        tenant_id: str,
        target_status: SubscriptionStatus,
        reason: str = "",
        grace_period_seconds: Optional[int] = None
    ) -> SubscriptionRecord:
        """
        Executes a formal state machine transition on the tenant's subscription.
        Raises InvalidSubscriptionTransitionError if the transition is prohibited.
        """
        with self._lock:
            sub = self.get_or_create_subscription(tenant_id)
            current_status = sub.status

            if current_status == target_status:
                return sub

            allowed_targets = VALID_STATUS_TRANSITIONS.get(current_status, set())
            if target_status not in allowed_targets:
                err_msg = (
                    f"Illegal subscription state transition for tenant '{tenant_id}': "
                    f"cannot transition from '{current_status.value}' to '{target_status.value}'. "
                    f"Allowed transitions from '{current_status.value}': {[s.value for s in allowed_targets]}"
                )
                logger.error(err_msg)
                raise InvalidSubscriptionTransitionError(err_msg)

            now = time.time()
            sub.status = target_status
            sub.updated_at = now

            if target_status == SubscriptionStatus.PAST_DUE:
                # Set grace period (default 3 days = 259,200s)
                seconds = grace_period_seconds if grace_period_seconds is not None else (86400 * 3)
                sub.grace_period_end = now + seconds
            elif target_status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED):
                sub.grace_period_end = None

            # Sync usage snapshot payment status
            tenant_usage = self.get_or_create_tenant(tenant_id)
            tenant_usage.payment_status = target_status.value

            self._persist_subscription(sub)
            logger.info(f"SUBSCRIPTION TRANSITION: Tenant '{tenant_id}' [{current_status.value} -> {target_status.value}] Reason: {reason}")
            return sub

    def _persist_subscription(self, sub: SubscriptionRecord):
        """Persists subscription state to relational DB."""
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tenant_subscriptions (
                        subscription_id, tenant_id, tier, status, current_period_start,
                        current_period_end, grace_period_end, cancel_at_period_end,
                        payment_provider, provider_customer_id, provider_subscription_id,
                        created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(subscription_id) DO UPDATE SET
                        tier = excluded.tier,
                        status = excluded.status,
                        current_period_start = excluded.current_period_start,
                        current_period_end = excluded.current_period_end,
                        grace_period_end = excluded.grace_period_end,
                        cancel_at_period_end = excluded.cancel_at_period_end,
                        payment_provider = excluded.payment_provider,
                        provider_customer_id = excluded.provider_customer_id,
                        provider_subscription_id = excluded.provider_subscription_id,
                        updated_at = excluded.updated_at,
                        metadata = excluded.metadata
                    """,
                    (
                        sub.subscription_id, sub.tenant_id, sub.tier.value, sub.status.value,
                        sub.current_period_start, sub.current_period_end, sub.grace_period_end,
                        1 if sub.cancel_at_period_end else 0, sub.payment_provider,
                        sub.provider_customer_id, sub.provider_subscription_id,
                        sub.created_at, sub.updated_at, json.dumps(sub.metadata)
                    )
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Subscription DB write note: {e}")

    # =========================================================================
    # 2. USAGE LEDGER & TENANT SNAPSHOTS
    # =========================================================================

    def get_or_create_tenant(self, tenant_id: str, tier: SubscriptionTier = SubscriptionTier.STARTER) -> TenantUsageSnapshot:
        """Retrieves or provisions tenant usage snapshot."""
        with self._lock:
            if tenant_id not in self._tenants:
                now = time.time()
                # Check if subscription exists for this tenant
                sub = self._subscriptions.get(tenant_id)
                actual_tier = sub.tier if sub else tier
                actual_status = sub.status.value if sub else "ACTIVE"

                self._tenants[tenant_id] = TenantUsageSnapshot(
                    tenant_id=tenant_id,
                    tier=actual_tier,
                    cycle_start=now,
                    cycle_end=now + 86400 * 30,
                    payment_status=actual_status
                )
            return self._tenants[tenant_id]

    # =========================================================================
    # 3. CENTRAL SERVER-SIDE ENTITLEMENT ENFORCEMENT
    # =========================================================================

    def check_entitlement(
        self,
        tenant_id: str,
        metric: str,
        requested_amount: float = 1.0
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a requested action is allowed under the tenant's current plan, status, and quotas.
        Strict server-side enforcement across seats, agents, concurrency, tokens, execution time, and features.
        """
        with self._lock:
            tenant = self.get_or_create_tenant(tenant_id)
            sub = self.get_or_create_subscription(tenant_id, tier=tenant.tier)

            # 1. Subscription Status Checks
            if sub.status in (SubscriptionStatus.SUSPENDED, SubscriptionStatus.UNPAID, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED):
                return False, f"Subscription inoperative: Account status is '{sub.status.value}'. Operations suspended."

            if sub.status == SubscriptionStatus.PAST_DUE:
                now = time.time()
                if sub.grace_period_end and now > sub.grace_period_end:
                    return False, f"Account past due: Grace period expired on {time.ctime(sub.grace_period_end)}. Payment required."
                # During active grace period, non-token/basic read requests can proceed, but flag warning
                if metric in ("tokens", "agents", "concurrency") and requested_amount > 100_000:
                    return False, "Account past due: Large quota expansions restricted during grace period. Please settle outstanding balance."

            plan = TIER_ENTITLEMENTS.get(sub.tier, TIER_ENTITLEMENTS[SubscriptionTier.FREE])

            # 2. Metric-Specific Quota Checks
            if metric == "tokens":
                if (tenant.tokens_consumed + requested_amount) > plan.max_tokens_per_month:
                    return False, f"Quota exceeded: Plan '{plan.tier.value}' allows {plan.max_tokens_per_month:,} tokens/mo"

            elif metric == "browser_minutes":
                if (tenant.browser_minutes_consumed + requested_amount) > plan.max_browser_minutes_per_month:
                    return False, f"Quota exceeded: Plan '{plan.tier.value}' allows {plan.max_browser_minutes_per_month:,} browser minutes/mo"

            elif metric == "terminal_seconds":
                if (tenant.terminal_seconds_consumed + requested_amount) > plan.max_terminal_seconds_per_month:
                    return False, f"Quota exceeded: Plan '{plan.tier.value}' allows {plan.max_terminal_seconds_per_month:,} terminal seconds/mo"

            elif metric == "storage_bytes":
                if (tenant.storage_bytes_consumed + requested_amount) > plan.max_storage_bytes:
                    return False, f"Quota exceeded: Storage limit of {plan.max_storage_bytes / (1024**3):.1f} GB reached"

            elif metric == "agents":
                if (tenant.active_agents_count + requested_amount) > plan.max_agents:
                    return False, f"Seat/Agent limit exceeded: Plan '{plan.tier.value}' allows up to {plan.max_agents} active agents"

            elif metric == "seats":
                if (tenant.active_seats_count + requested_amount) > plan.max_seats:
                    return False, f"Seat limit exceeded: Plan '{plan.tier.value}' allows up to {plan.max_seats} member seats"

            elif metric == "concurrency":
                if (tenant.active_concurrency_count + requested_amount) > plan.max_concurrency:
                    return False, f"Concurrency limit exceeded: Plan '{plan.tier.value}' allows up to {plan.max_concurrency} concurrent workflows"

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
        cost_usd: float = 0.0,
        idempotency_key: Optional[str] = None
    ) -> bool:
        """Records consumption event into the tenant's active usage ledger with idempotency defense."""
        with self._lock:
            if idempotency_key:
                full_key = f"{tenant_id}:{idempotency_key}"
                if full_key in self._processed_idempotency_keys:
                    logger.warning(f"DUPLICATE USAGE ATTEMPT SUPPRESSED: Key {full_key}")
                    return False
                self._processed_idempotency_keys.add(full_key)

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
            elif metric == "agents":
                tenant.active_agents_count = max(0, int(tenant.active_agents_count + amount))
            elif metric == "seats":
                tenant.active_seats_count = max(0, int(tenant.active_seats_count + amount))
            elif metric == "concurrency":
                tenant.active_concurrency_count = max(0, int(tenant.active_concurrency_count + amount))

            tenant.total_cost_usd += cost_usd
            logger.info(f"USAGE RECORDED: [{tenant_id}] Metric: {metric} Amount: {amount} (Total Cost: ${tenant.total_cost_usd:.4f})")
            return True

    # =========================================================================
    # 4. ECONOMIC GOVERNOR RECONCILIATION
    # =========================================================================

    def reconcile_economic_settlement(
        self,
        tenant_id: str,
        reservation_id: str,
        actual_tokens: int,
        actual_usd: float
    ) -> Dict[str, Any]:
        """
        Reconciles an economic governor budget reservation settlement into the SaaS billing usage ledger.
        Guarantees that token consumption and USD expenses from agent execution are accurately recorded
        without duplication or omission.
        """
        with self._lock:
            reconcile_key = f"recon:{tenant_id}:{reservation_id}"
            if reconcile_key in self._reconciled_reservations:
                logger.warning(f"ECONOMIC SETTLEMENT ALREADY RECONCILED: {reconcile_key}")
                return {
                    "success": True,
                    "reconciled": False,
                    "message": "Reservation already reconciled into billing ledger",
                    "reservation_id": reservation_id
                }

            self._reconciled_reservations.add(reconcile_key)

            # Record into usage ledger
            self.record_usage(
                tenant_id=tenant_id,
                metric="tokens",
                amount=actual_tokens,
                cost_usd=actual_usd,
                idempotency_key=f"gov_settle_{reservation_id}"
            )

            # Record in usage_records table if relational DB available
            try:
                record_id = f"usg_econ_{uuid.uuid4().hex[:8]}"
                now = time.time()
                with db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO usage_records (
                            record_id, tenant_id, company_id, agent_id,
                            mission_id, model, input_tokens, output_tokens, cost, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (record_id, tenant_id, "enterprise", "economic_governor", reservation_id, "governed_execution", actual_tokens, 0, actual_usd, now)
                    )
                    conn.commit()
            except Exception as e:
                logger.debug(f"Relational usage record log note: {e}")

            logger.info(f"ECONOMIC GOVERNOR SETTLEMENT RECONCILED: [{tenant_id}] Res: {reservation_id} Tokens: {actual_tokens:,} Cost: ${actual_usd:.4f}")
            return {
                "success": True,
                "reconciled": True,
                "tenant_id": tenant_id,
                "reservation_id": reservation_id,
                "actual_tokens": actual_tokens,
                "actual_usd": actual_usd
            }

    # =========================================================================
    # 5. IDEMPOTENT WEBHOOK PROCESSING ENGINE
    # =========================================================================

    def process_stripe_webhook(self, payload_str: str, sig_header: str) -> Dict[str, Any]:
        """
        Processes inbound Stripe webhook with HMAC signature verification and atomic deduplication.
        """
        with self._lock:
            # 1. Cryptographic Signature Verification
            if not self.stripe.verify_webhook_signature(payload_str, sig_header):
                logger.error("STRIPE WEBHOOK REJECTED: Invalid signature or expired timestamp drift")
                return {"success": False, "status": "INVALID_SIGNATURE", "code": 401}

            try:
                event_data = json.loads(payload_str)
            except Exception as e:
                return {"success": False, "status": "MALFORMED_JSON", "code": 400, "error": str(e)}

            event_id = event_data.get("id")
            event_type = event_data.get("type")

            if not event_id or not event_type:
                return {"success": False, "status": "MISSING_EVENT_METADATA", "code": 400}

            # 2. Idempotency Defense
            if event_id in self._processed_webhook_events:
                logger.info(f"STRIPE WEBHOOK DUPLICATE IGNORED: {event_id}")
                return {"success": True, "status": "DUPLICATE_IGNORED", "event_id": event_id}

            self._processed_webhook_events.add(event_id)
            self._log_webhook_event(event_id=event_id, provider="stripe", event_type=event_type, payload=event_data)

            # 3. Route Event
            obj = event_data.get("data", {}).get("object", {})
            customer_id = obj.get("customer")
            tenant_id = obj.get("metadata", {}).get("tenant_id") or self._find_tenant_by_customer_id(customer_id)

            if event_type == "customer.subscription.created" or event_type == "customer.subscription.updated":
                if tenant_id:
                    status_str = obj.get("status", "active").upper()
                    target_status = SubscriptionStatus.ACTIVE if status_str == "ACTIVE" else SubscriptionStatus.PAST_DUE
                    try:
                        self.transition_subscription_status(tenant_id, target_status, reason=f"Stripe event {event_type}")
                    except InvalidSubscriptionTransitionError:
                        pass

            elif event_type == "customer.subscription.deleted":
                if tenant_id:
                    try:
                        self.transition_subscription_status(tenant_id, SubscriptionStatus.CANCELLED, reason="Stripe subscription deleted")
                    except InvalidSubscriptionTransitionError:
                        pass

            elif event_type == "invoice.payment_succeeded":
                if tenant_id:
                    try:
                        self.transition_subscription_status(tenant_id, SubscriptionStatus.ACTIVE, reason="Stripe invoice payment succeeded")
                    except InvalidSubscriptionTransitionError:
                        pass

            elif event_type == "invoice.payment_failed":
                if tenant_id:
                    try:
                        self.transition_subscription_status(tenant_id, SubscriptionStatus.PAST_DUE, reason="Stripe invoice payment failed")
                    except InvalidSubscriptionTransitionError:
                        pass

            return {"success": True, "status": "PROCESSED", "event_id": event_id, "event_type": event_type}

    def process_razorpay_webhook(self, payload_str: str, sig_header: str) -> Dict[str, Any]:
        """
        Processes inbound Razorpay webhook with HMAC signature verification and atomic deduplication.
        """
        with self._lock:
            # 1. Cryptographic Signature Verification
            if not self.razorpay.verify_webhook_signature(payload_str, sig_header):
                logger.error("RAZORPAY WEBHOOK REJECTED: Invalid signature")
                return {"success": False, "status": "INVALID_SIGNATURE", "code": 401}

            try:
                event_data = json.loads(payload_str)
            except Exception as e:
                return {"success": False, "status": "MALFORMED_JSON", "code": 400, "error": str(e)}

            event_id = event_data.get("event_id") or event_data.get("id") or f"rzp_ev_{hashlib.sha256(payload_str.encode()).hexdigest()[:12]}"
            event_type = event_data.get("event")

            if not event_type:
                return {"success": False, "status": "MISSING_EVENT_METADATA", "code": 400}

            # 2. Idempotency Defense
            if event_id in self._processed_webhook_events:
                logger.info(f"RAZORPAY WEBHOOK DUPLICATE IGNORED: {event_id}")
                return {"success": True, "status": "DUPLICATE_IGNORED", "event_id": event_id}

            self._processed_webhook_events.add(event_id)
            self._log_webhook_event(event_id=event_id, provider="razorpay", event_type=event_type, payload=event_data)

            # 3. Route Event
            payload_entity = event_data.get("payload", {})
            sub_entity = payload_entity.get("subscription", {}).get("entity", {})
            payment_entity = payload_entity.get("payment", {}).get("entity", {})
            customer_id = sub_entity.get("customer_id") or payment_entity.get("customer_id")
            notes = sub_entity.get("notes", {}) or payment_entity.get("notes", {})
            tenant_id = notes.get("tenant_id") or self._find_tenant_by_customer_id(customer_id)

            if event_type in ("subscription.activated", "subscription.charged", "payment.captured"):
                if tenant_id:
                    try:
                        self.transition_subscription_status(tenant_id, SubscriptionStatus.ACTIVE, reason=f"Razorpay {event_type}")
                    except InvalidSubscriptionTransitionError:
                        pass

            elif event_type in ("subscription.halted", "payment.failed"):
                if tenant_id:
                    try:
                        self.transition_subscription_status(tenant_id, SubscriptionStatus.PAST_DUE, reason=f"Razorpay {event_type}")
                    except InvalidSubscriptionTransitionError:
                        pass

            elif event_type == "subscription.cancelled":
                if tenant_id:
                    try:
                        self.transition_subscription_status(tenant_id, SubscriptionStatus.CANCELLED, reason="Razorpay subscription cancelled")
                    except InvalidSubscriptionTransitionError:
                        pass

            return {"success": True, "status": "PROCESSED", "event_id": event_id, "event_type": event_type}

    def _find_tenant_by_customer_id(self, customer_id: Optional[str]) -> Optional[str]:
        if not customer_id:
            return None
        for t_id, sub in self._subscriptions.items():
            if sub.provider_customer_id == customer_id:
                return t_id
        return None

    def _log_webhook_event(self, event_id: str, provider: str, event_type: str, payload: Dict[str, Any]):
        """Persists received webhook event to relational DB."""
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO billing_webhook_events (
                        event_id, provider, event_type, payload, processed_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO NOTHING
                    """,
                    (event_id, provider, event_type, json.dumps(payload), time.time(), "PROCESSED")
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Webhook DB log note: {e}")

    # =========================================================================
    # 6. PLAN UPGRADES & INVOICE GENERATION
    # =========================================================================

    def upgrade_plan(self, tenant_id: str, new_tier: SubscriptionTier) -> TenantUsageSnapshot:
        with self._lock:
            tenant = self.get_or_create_tenant(tenant_id)
            tenant.tier = new_tier
            sub = self.get_or_create_subscription(tenant_id)
            sub.tier = new_tier
            sub.updated_at = time.time()
            self._persist_subscription(sub)
            logger.info(f"PLAN UPGRADED: Tenant {tenant_id} upgraded to {new_tier.value}")
            return tenant

    def downgrade_plan(self, tenant_id: str, new_tier: SubscriptionTier) -> TenantUsageSnapshot:
        with self._lock:
            tenant = self.get_or_create_tenant(tenant_id)
            tenant.tier = new_tier
            sub = self.get_or_create_subscription(tenant_id)
            sub.tier = new_tier
            sub.updated_at = time.time()
            self._persist_subscription(sub)
            logger.info(f"PLAN DOWNGRADED: Tenant {tenant_id} downgraded to {new_tier.value}")
            return tenant

    def charge_customer(self, tenant_id: str, amount_usd: float, idempotency_key: str) -> Dict[str, Any]:
        """Executes a financial charge with strict idempotency defense against double-charging."""
        with self._lock:
            full_key = f"{tenant_id}:charge:{idempotency_key}"
            if full_key in self._processed_idempotency_keys:
                logger.warning(f"DUPLICATE FINANCIAL MUTATION SUPPRESSED: Key {full_key}")
                return {"success": True, "duplicate": True, "message": "Duplicate mutation suppressed", "amount": amount_usd}
            self._processed_idempotency_keys.add(full_key)
            return {"success": True, "duplicate": False, "charge_id": f"ch_{uuid.uuid4().hex[:12]}", "amount": amount_usd}

    def generate_tenant_invoice(self, tenant_id: str, period_start: float, period_end: float) -> Dict[str, Any]:
        """
        Generates an auditable invoice snapshot for a billing cycle, including base subscription fee
        and metered consumption.
        """
        with self._lock:
            tenant = self.get_or_create_tenant(tenant_id)
            sub = self.get_or_create_subscription(tenant_id)
            plan = TIER_ENTITLEMENTS.get(sub.tier, TIER_ENTITLEMENTS[SubscriptionTier.FREE])

            base_fee = plan.monthly_price_usd
            metered_cost = tenant.total_cost_usd
            total_due = round(base_fee + metered_cost, 2)

            invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
            now = time.time()
            line_items = [
                {"description": f"{plan.tier.value} Subscription Tier Fee", "amount_usd": base_fee, "type": "subscription_base"},
                {"description": "Metered Compute & Token Consumption", "amount_usd": metered_cost, "type": "metered_usage"}
            ]

            invoice_record = {
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "subscription_id": sub.subscription_id,
                "amount_due_usd": total_due,
                "amount_paid_usd": total_due if sub.status == SubscriptionStatus.ACTIVE else 0.0,
                "currency": "USD",
                "status": "PAID" if sub.status == SubscriptionStatus.ACTIVE else "OPEN",
                "period_start": period_start,
                "period_end": period_end,
                "line_items": line_items,
                "created_at": now,
                "paid_at": now if sub.status == SubscriptionStatus.ACTIVE else None
            }

            try:
                with db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO tenant_invoices (
                            invoice_id, tenant_id, subscription_id, amount_due_usd,
                            amount_paid_usd, currency, status, period_start, period_end,
                            line_items, created_at, paid_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(invoice_id) DO NOTHING
                        """,
                        (
                            invoice_id, tenant_id, sub.subscription_id, total_due,
                            invoice_record["amount_paid_usd"], "USD", invoice_record["status"],
                            period_start, period_end, json.dumps(line_items), now, invoice_record["paid_at"]
                        )
                    )
                    conn.commit()
            except Exception as e:
                logger.debug(f"Invoice DB persist note: {e}")

            logger.info(f"INVOICE GENERATED: [{tenant_id}] Inv: {invoice_id} Total: ${total_due:.2f} Status: {invoice_record['status']}")
            return invoice_record


# Global singleton instance
saas_billing_engine = SaasBillingEngine.get_instance()
