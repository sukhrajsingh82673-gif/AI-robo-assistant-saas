"""
Test suite for Sub-Step 9C: Billing, Plans, Metering, Cost Caps, and Lifecycle (Rules 78, 79).
"""

import time
import pytest
from core.billing.port import (
    SandboxBillingAdapter,
    PaddleBillingAdapter,
    StripeBillingAdapter,
    LagoBillingAdapter,
)
from core.billing.plans import PlanRegistry, SubscriptionPlan
from core.billing.metering import UsageLedger, GENESIS_HASH
from core.billing.cost_caps import CostCapManager
from core.billing.lifecycle import BillingLifecycleManager, AccountStatus


class TestStep9cBilling:

    def test_sandbox_billing_adapter_lifecycle_and_money_truth(self):
        """Verify SandboxBillingAdapter operations and integer penny invoice math (Rule 79)."""
        adapter = SandboxBillingAdapter()

        # 1. Create customer & subscription
        cus = adapter.create_customer("tenant_123", "cfo@example.com", "Acme Corp")
        assert cus["sandbox"] is True
        assert cus["tenant_id"] == "tenant_123"

        sub = adapter.create_subscription("tenant_123", "plan_team_v1")
        assert sub["status"] == "active"
        sub_id = sub["subscription_id"]

        # 2. Report usage with deduplication
        u1 = adapter.report_usage(sub_id, "ai_tokens", 15000, "idem_key_001")
        assert u1["status"] == "recorded"

        u2 = adapter.report_usage(sub_id, "ai_tokens", 15000, "idem_key_001")
        assert u2["status"] == "deduplicated"

        # 3. Exact integer math invoice calculation
        # Subtotal: $99.00 (9900 cents), Tax: 8.25% (825 basis points)
        # tax_cents = (9900 * 825) // 10000 = 8167500 // 10000 = 816 cents ($8.16)
        # total_cents = 9900 + 816 = 10716 cents ($107.16)
        inv = adapter.calculate_invoice("tenant_123", subtotal_cents=9900, tax_rate_bps=825)
        assert inv["subtotal_cents"] == 9900
        assert inv["tax_cents"] == 816
        assert inv["total_cents"] == 10716
        assert inv["subtotal_cents"] + inv["tax_cents"] == inv["total_cents"]

        # 4. Cancel subscription
        canc = adapter.cancel_subscription(sub_id, at_period_end=True)
        assert canc["status"] == "canceling"

    def test_unconfigured_adapters_report_not_configured(self):
        """Verify Paddle, Stripe, and Lago raise NOT_CONFIGURED without credentials (Rule 24)."""
        paddle = PaddleBillingAdapter(api_key=None, vendor_id=None)
        with pytest.raises(NotImplementedError, match="NOT_CONFIGURED"):
            paddle.create_customer("t1", "test@test.com", "Co")

        stripe = StripeBillingAdapter(api_key=None)
        with pytest.raises(NotImplementedError, match="NOT_CONFIGURED"):
            stripe.create_customer("t1", "test@test.com", "Co")

        lago = LagoBillingAdapter(api_url=None, api_key=None)
        with pytest.raises(NotImplementedError, match="NOT_CONFIGURED"):
            lago.create_customer("t1", "test@test.com", "Co")

    def test_plan_registry_and_overage_pricing(self):
        """Verify canonical plan tiers and integer penny overage calculations."""
        plans = PlanRegistry.list_plans()
        assert len(plans) == 4
        codes = [p.code for p in plans]
        assert "community" in codes
        assert "starter" in codes
        assert "team" in codes
        assert "enterprise" in codes

        # Team tier: $99 base (9900 cents), 5M included, $3.00/M overage (300 cents)
        team_plan = PlanRegistry.get_plan("team")
        # 1. Under included tokens
        c1 = team_plan.calculate_period_fee(used_tokens=4_500_000)
        assert c1["base_fee_cents"] == 9900
        assert c1["overage_cents"] == 0
        assert c1["total_cents"] == 9900

        # 2. Over included tokens by 1.2M tokens -> ceil to 2M tokens overage = 2 * 300 = 600 cents
        c2 = team_plan.calculate_period_fee(used_tokens=6_200_000)
        assert c2["overage_tokens"] == 1_200_000
        assert c2["overage_cents"] == 600
        assert c2["total_cents"] == 10500

    def test_usage_ledger_cryptographic_chaining_and_tamper_detection(self):
        """Verify append-only usage ledger chains hashes and detects tamper (Rule 79)."""
        ledger = UsageLedger()

        r1 = ledger.record_usage("tenant_alpha", "sub_1", "ai_tokens", 1000, "tokens", "key_1", timestamp=1000.0)
        assert r1.prev_hash == GENESIS_HASH
        assert r1.record_hash is not None

        r2 = ledger.record_usage("tenant_alpha", "sub_1", "ai_tokens", 2500, "tokens", "key_2", timestamp=1010.0)
        assert r2.prev_hash == r1.record_hash

        r3 = ledger.record_usage("tenant_alpha", "sub_1", "api_calls", 5, "calls", "key_3", timestamp=1020.0)
        assert r3.prev_hash == r2.record_hash

        # Valid chain
        valid, err = ledger.verify_chain_integrity("tenant_alpha")
        assert valid
        assert err is None
        assert ledger.get_aggregated_metric("tenant_alpha", "ai_tokens") == 3500

        # Mutation test: Tamper with record quantity in chain
        r2.quantity = 999999
        valid_tampered, err_tampered = ledger.verify_chain_integrity("tenant_alpha")
        assert not valid_tampered
        assert "Tampered hash" in err_tampered

    def test_cost_caps_soft_and_hard_cap_safeguards(self):
        """Verify 80% soft cap alert and 100% hard cap auto-halt (Rule 78)."""
        manager = CostCapManager()
        # Hard cap: $100 (10000 cents), soft cap defaults to $80 (8000 cents)
        manager.set_caps("tenant_spend", hard_cap_cents=10000)

        # 1. Under soft cap -> no alert
        alert1 = manager.record_spend("tenant_spend", 5000)
        assert alert1 is None

        # 2. Spend crosses 80% soft cap -> SOFT_CAP alert
        alert2 = manager.record_spend("tenant_spend", 3500)
        assert alert2 is not None
        assert alert2.level == "SOFT_CAP"
        assert alert2.current_spend_cents == 8500

        # 3. Spend crosses 100% hard cap -> HARD_CAP alert
        alert3 = manager.record_spend("tenant_spend", 2000)
        assert alert3 is not None
        assert alert3.level == "HARD_CAP"
        assert alert3.current_spend_cents == 10500

        # 4. Projected spend blocked
        allowed, reason = manager.is_spend_allowed("tenant_spend", estimated_cents=500)
        assert not allowed
        assert "exceeds hard cap" in reason

    def test_billing_lifecycle_grace_period_and_legal_hold(self):
        """Verify delinquency lifecycle transitions and inviolable legal hold protection (Rule 78)."""
        mgr = BillingLifecycleManager()
        t0 = 1700000000.0  # Base time
        mgr.register_account("tenant_delinquent", legal_hold=False)

        # 1. Payment fails -> PAST_DUE_GRACE (14 days)
        st1 = mgr.mark_payment_failed("tenant_delinquent", current_time=t0)
        assert st1 == AccountStatus.PAST_DUE_GRACE

        # Purge denied during grace
        can_purge, reason = mgr.can_purge_tenant_data("tenant_delinquent")
        assert not can_purge
        assert "PAST_DUE_GRACE" in reason

        # 2. 15 days later (grace expired) -> RESTRICTED_READ_ONLY
        t_grace_expired = t0 + (15 * 86400)
        st2 = mgr.evaluate_lifecycle("tenant_delinquent", current_time=t_grace_expired)
        assert st2 == AccountStatus.RESTRICTED_READ_ONLY

        can_purge, _ = mgr.can_purge_tenant_data("tenant_delinquent")
        assert not can_purge

        # 3. 35 days later (read-only expired) -> EXPORT_ONLY
        t_ro_expired = t_grace_expired + (35 * 86400)
        st3 = mgr.evaluate_lifecycle("tenant_delinquent", current_time=t_ro_expired)
        assert st3 == AccountStatus.EXPORT_ONLY

        can_purge, _ = mgr.can_purge_tenant_data("tenant_delinquent")
        assert not can_purge
        assert "Export Window" in reason or "Customer data" in reason

        # 4. Account terminated pending purge
        mgr._accounts["tenant_delinquent"]["status"] = AccountStatus.TERMINATED_PENDING_PURGE
        # Without legal hold: can purge
        can_purge, _ = mgr.can_purge_tenant_data("tenant_delinquent")
        assert can_purge

        # 5. Place under Legal Hold -> Purge is strictly blocked
        mgr.set_legal_hold("tenant_delinquent", True)
        can_purge_held, reason_held = mgr.can_purge_tenant_data("tenant_delinquent")
        assert not can_purge_held
        assert "Legal Hold" in reason_held
