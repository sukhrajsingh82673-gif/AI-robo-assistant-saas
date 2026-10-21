"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 12 Commercial SaaS Lifecycle, Entitlements & Multi-Gateway Billing Test Suite
===================================================================================
Rigorous automated qualification for:
  1. Subscription State Machine (TRIALING, ACTIVE, PAST_DUE, UNPAID, SUSPENDED, CANCELLED, EXPIRED)
  2. Central Server-Side Entitlement Enforcer (Quotas, Ceilings, Feature Gates, Status Blocks)
  3. Stripe Webhook Engine (HMAC-SHA256, Anti-Replay Timestamp Drift, Event Deduplication, Lifecycle Routing)
  4. Razorpay Webhook Engine (HMAC-SHA256, Anti-Replay, Event Deduplication, Lifecycle Routing)
  5. Economic Governor Settlement Reconciliation (Budget Reservation -> Usage Ledger Idempotency)
  6. Multi-Tenant Billing Boundary Isolation & Auditable Invoice Generation
"""

import unittest
import os
import time
import json
import uuid
import hmac
import hashlib

from core.db import db, configure_isolated_test_db
from core.saas_billing import (
    SaasBillingEngine,
    saas_billing_engine,
    SubscriptionTier,
    SubscriptionStatus,
    TIER_ENTITLEMENTS,
    InvalidSubscriptionTransitionError,
    SubscriptionRecord,
    TenantUsageSnapshot
)


class TestPhase12CommercialBilling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = configure_isolated_test_db()
        import tempfile
        cls.test_evidence_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name
        cls.orig_evidence_path = os.environ.get("ZONATA_EVIDENCE_PATH")
        os.environ["ZONATA_EVIDENCE_PATH"] = cls.test_evidence_file

        cls.tenant_id = f"tnt_p12_{uuid.uuid4().hex[:6]}"
        cls.foreign_tenant = f"tnt_foreign_{uuid.uuid4().hex[:6]}"
        cls.company_id = f"comp_p12_{uuid.uuid4().hex[:6]}"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Phase 12 Commercial Tenant', ?)",
                (cls.tenant_id, time.time())
            )
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Phase 12 Foreign Tenant', ?)",
                (cls.foreign_tenant, time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) "
                "VALUES (?, ?, 'P12 Commercial Corp', 'US', 'SaaS', 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.company_id, cls.tenant_id, time.time())
            )
            conn.commit()

        cls.engine = SaasBillingEngine.get_instance()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "orig_evidence_path") and cls.orig_evidence_path:
            os.environ["ZONATA_EVIDENCE_PATH"] = cls.orig_evidence_path
        elif "ZONATA_EVIDENCE_PATH" in os.environ:
            del os.environ["ZONATA_EVIDENCE_PATH"]

        if hasattr(cls, "test_evidence_file") and os.path.exists(cls.test_evidence_file):
            try:
                os.remove(cls.test_evidence_file)
            except OSError:
                pass

    # =========================================================================
    # WORKSTREAM 1: SUBSCRIPTION LIFECYCLE & STATE MACHINE
    # =========================================================================

    def test_01_default_subscription_provisioning(self):
        """Verifies initial provisioning of default tenant subscription and entitlement parameters."""
        t_id = f"tnt_sub_{uuid.uuid4().hex[:6]}"
        sub = self.engine.get_or_create_subscription(tenant_id=t_id, tier=SubscriptionTier.STARTER)
        self.assertEqual(sub.tenant_id, t_id)
        self.assertEqual(sub.tier, SubscriptionTier.STARTER)
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertGreater(sub.current_period_end, sub.current_period_start)
        self.assertIsNone(sub.grace_period_end)

        # Usage snapshot should reflect active status
        snapshot = self.engine.get_or_create_tenant(t_id)
        self.assertEqual(snapshot.payment_status, "ACTIVE")
        self.assertEqual(snapshot.tier, SubscriptionTier.STARTER)

    def test_02_valid_lifecycle_transitions(self):
        """Validates canonical state transitions: TRIALING -> ACTIVE -> PAST_DUE -> UNPAID -> SUSPENDED -> ACTIVE."""
        t_id = f"tnt_trans_{uuid.uuid4().hex[:6]}"
        sub = self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.TRIALING)
        self.assertEqual(sub.status, SubscriptionStatus.TRIALING)

        # TRIALING -> ACTIVE
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.ACTIVE, reason="Card added")
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)

        # ACTIVE -> PAST_DUE
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.PAST_DUE, reason="Card payment failed")
        self.assertEqual(sub.status, SubscriptionStatus.PAST_DUE)
        self.assertIsNotNone(sub.grace_period_end)

        # PAST_DUE -> UNPAID
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.UNPAID, reason="Grace period expired")
        self.assertEqual(sub.status, SubscriptionStatus.UNPAID)

        # UNPAID -> SUSPENDED
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.SUSPENDED, reason="Dunning complete")
        self.assertEqual(sub.status, SubscriptionStatus.SUSPENDED)

        # SUSPENDED -> ACTIVE (Reinstatement)
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.ACTIVE, reason="Account balance settled")
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertIsNone(sub.grace_period_end)

    def test_03_invalid_lifecycle_transition_rejection(self):
        """Verifies that prohibited transitions are strictly rejected with InvalidSubscriptionTransitionError."""
        t_id = f"tnt_inv_{uuid.uuid4().hex[:6]}"
        sub = self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        # Cancel subscription
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.CANCELLED, reason="User cancelled")
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)

        # Illegal: CANCELLED -> PAST_DUE (cancelled accounts cannot be past due)
        with self.assertRaises(InvalidSubscriptionTransitionError) as ctx:
            self.engine.transition_subscription_status(t_id, SubscriptionStatus.PAST_DUE, reason="Invalid attempt")
        self.assertIn("cannot transition from 'CANCELLED' to 'PAST_DUE'", str(ctx.exception))

    def test_04_grace_period_assignment_and_expiration(self):
        """Verifies grace period timeline assignment and post-expiration entitlement block."""
        t_id = f"tnt_grace_{uuid.uuid4().hex[:6]}"
        sub = self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        # Transition to PAST_DUE with a custom 2-second grace period
        now = time.time()
        sub = self.engine.transition_subscription_status(
            t_id, SubscriptionStatus.PAST_DUE, reason="Payment failed", grace_period_seconds=2
        )
        self.assertIsNotNone(sub.grace_period_end)
        self.assertAlmostEqual(sub.grace_period_end, now + 2, delta=1.0)

        # During active grace period, moderate operations are permitted
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", requested_amount=500)
        self.assertTrue(allowed)

        # Wait for grace period to expire
        time.sleep(2.1)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", requested_amount=500)
        self.assertFalse(allowed)
        self.assertIn("Grace period expired", msg)

    def test_05_cancellation_and_reactivation(self):
        """Tests full cancellation and clean subsequent reactivation."""
        t_id = f"tnt_canc_{uuid.uuid4().hex[:6]}"
        sub = self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        # Cancel
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.CANCELLED, reason="Customer request")
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)

        # Entitlement check immediately denies
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 100)
        self.assertFalse(allowed)
        self.assertIn("CANCELLED", msg)

        # Reactivation to ACTIVE
        sub = self.engine.transition_subscription_status(t_id, SubscriptionStatus.ACTIVE, reason="Customer resubscribed")
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 100)
        self.assertTrue(allowed)

    def test_06_non_destructive_suspension(self):
        """Verifies suspension halts execution without wiping existing consumption counters."""
        t_id = f"tnt_susp_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)
        self.engine.record_usage(t_id, "tokens", amount=25_000, cost_usd=1.25)

        # Suspend
        self.engine.transition_subscription_status(t_id, SubscriptionStatus.SUSPENDED, reason="Administrative hold")
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 100)
        self.assertFalse(allowed)
        self.assertIn("SUSPENDED", msg)

        # Re-activate and ensure historical usage is intact
        self.engine.transition_subscription_status(t_id, SubscriptionStatus.ACTIVE, reason="Hold released")
        snapshot = self.engine.get_or_create_tenant(t_id)
        self.assertEqual(snapshot.tokens_consumed, 25_000)
        self.assertEqual(snapshot.total_cost_usd, 1.25)

    # =========================================================================
    # WORKSTREAM 2: CENTRAL SERVER-SIDE ENTITLEMENT ENFORCEMENT
    # =========================================================================

    def test_07_entitlement_token_quota_enforcement(self):
        """Verifies token quota boundary enforcement under Starter plan (10M token limit)."""
        t_id = f"tnt_tok_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, tier=SubscriptionTier.STARTER, status=SubscriptionStatus.ACTIVE)

        # Consume 9.9M tokens
        self.engine.record_usage(t_id, "tokens", amount=9_900_000)

        # Requesting 50,000 tokens succeeds (9.95M <= 10M)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", requested_amount=50_000)
        self.assertTrue(allowed)

        # Requesting 200,000 tokens fails (10.1M > 10M)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", requested_amount=200_000)
        self.assertFalse(allowed)
        self.assertIn("Quota exceeded", msg)

    def test_08_entitlement_browser_and_terminal_limits(self):
        """Verifies execution time limits on browser and terminal capabilities."""
        t_id = f"tnt_exec_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, tier=SubscriptionTier.FREE, status=SubscriptionStatus.ACTIVE)
        # Free plan allows 60 browser minutes and 600 terminal seconds

        self.engine.record_usage(t_id, "browser_minutes", amount=55.0)
        allowed, msg = self.engine.check_entitlement(t_id, "browser_minutes", requested_amount=10.0)
        self.assertFalse(allowed)
        self.assertIn("Quota exceeded", msg)

        self.engine.record_usage(t_id, "terminal_seconds", amount=590.0)
        allowed, msg = self.engine.check_entitlement(t_id, "terminal_seconds", requested_amount=20.0)
        self.assertFalse(allowed)
        self.assertIn("Quota exceeded", msg)

    def test_09_entitlement_structural_ceilings_agents_seats_concurrency(self):
        """Verifies server-side limits on member seats, agent swarms, and workflow concurrency."""
        t_id = f"tnt_struct_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, tier=SubscriptionTier.FREE, status=SubscriptionStatus.ACTIVE)
        # Free plan: max 2 agents, 1 seat, 1 concurrency

        # Agents check
        self.engine.record_usage(t_id, "agents", amount=2)
        allowed, msg = self.engine.check_entitlement(t_id, "agents", requested_amount=1)
        self.assertFalse(allowed)
        self.assertIn("allows up to 2 active agents", msg)

        # Seats check
        self.engine.record_usage(t_id, "seats", amount=1)
        allowed, msg = self.engine.check_entitlement(t_id, "seats", requested_amount=1)
        self.assertFalse(allowed)
        self.assertIn("allows up to 1 member seats", msg)

        # Concurrency check
        self.engine.record_usage(t_id, "concurrency", amount=1)
        allowed, msg = self.engine.check_entitlement(t_id, "concurrency", requested_amount=1)
        self.assertFalse(allowed)
        self.assertIn("allows up to 1 concurrent workflows", msg)

    def test_10_entitlement_feature_gating(self):
        """Verifies feature gating: basic features allowed on Free, advanced gated to Pro/Enterprise."""
        t_id = f"tnt_feat_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, tier=SubscriptionTier.FREE, status=SubscriptionStatus.ACTIVE)

        # core_agents allowed on Free
        allowed, msg = self.engine.check_entitlement(t_id, "feature", requested_amount="core_agents")
        self.assertTrue(allowed)

        # a2a_mesh not allowed on Free
        allowed, msg = self.engine.check_entitlement(t_id, "feature", requested_amount="a2a_mesh")
        self.assertFalse(allowed)
        self.assertIn("not entitled under FREE plan", msg)

        # Upgrade to Enterprise gives access to all features
        self.engine.upgrade_plan(t_id, SubscriptionTier.ENTERPRISE)
        allowed, msg = self.engine.check_entitlement(t_id, "feature", requested_amount="a2a_mesh")
        self.assertTrue(allowed)
        allowed, msg = self.engine.check_entitlement(t_id, "feature", requested_amount="economic_governance")
        self.assertTrue(allowed)

    def test_11_tenant_boundary_isolation_billing(self):
        """Verifies Tenant A quota exhaustion does not affect Tenant B quotas."""
        tA = f"tnt_isoA_{uuid.uuid4().hex[:6]}"
        tB = f"tnt_isoB_{uuid.uuid4().hex[:6]}"

        self.engine.get_or_create_subscription(tA, tier=SubscriptionTier.STARTER, status=SubscriptionStatus.ACTIVE)
        self.engine.get_or_create_subscription(tB, tier=SubscriptionTier.STARTER, status=SubscriptionStatus.ACTIVE)

        # Exhaust Tenant A's tokens
        self.engine.record_usage(tA, "tokens", amount=10_000_000)
        allowedA, _ = self.engine.check_entitlement(tA, "tokens", 1000)
        self.assertFalse(allowedA)

        # Tenant B must remain completely unimpaired
        allowedB, _ = self.engine.check_entitlement(tB, "tokens", 1000)
        self.assertTrue(allowedB)

    # =========================================================================
    # WORKSTREAM 3: STRIPE CRYPTOGRAPHIC WEBHOOK ENGINE
    # =========================================================================

    def _generate_stripe_header(self, payload: str, secret: str, timestamp: int) -> str:
        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={sig}"

    def test_12_stripe_webhook_valid_signature_processing(self):
        """Tests end-to-end processing of a cryptographically valid Stripe webhook."""
        t_id = f"tnt_strp_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        event_id = f"evt_strp_{uuid.uuid4().hex[:12]}"
        payload = {
            "id": event_id,
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_stripe_123",
                    "status": "active",
                    "metadata": {"tenant_id": t_id}
                }
            }
        }
        payload_str = json.dumps(payload)
        now = int(time.time())
        sig_header = self._generate_stripe_header(payload_str, self.engine.stripe.webhook_secret, now)

        res = self.engine.process_stripe_webhook(payload_str=payload_str, sig_header=sig_header)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "PROCESSED")
        self.assertEqual(res["event_id"], event_id)

    def test_13_stripe_webhook_tampered_signature_rejection(self):
        """Verifies rejection of a Stripe webhook with forged signature."""
        payload = {"id": "evt_tampered", "type": "invoice.payment_failed"}
        payload_str = json.dumps(payload)
        now = int(time.time())
        bad_sig = "t=" + str(now) + ",v1=badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad"

        res = self.engine.process_stripe_webhook(payload_str=payload_str, sig_header=bad_sig)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "INVALID_SIGNATURE")
        self.assertEqual(res["code"], 401)

    def test_14_stripe_webhook_timestamp_drift_replay_protection(self):
        """Verifies rejection of replayed Stripe webhook when timestamp drift exceeds 300s tolerance."""
        payload = {"id": "evt_replay", "type": "invoice.payment_failed"}
        payload_str = json.dumps(payload)
        old_time = int(time.time()) - 600  # 10 minutes ago
        sig_header = self._generate_stripe_header(payload_str, self.engine.stripe.webhook_secret, old_time)

        res = self.engine.process_stripe_webhook(payload_str=payload_str, sig_header=sig_header)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "INVALID_SIGNATURE")

    def test_15_stripe_webhook_idempotency_deduplication(self):
        """Verifies duplicate webhook event IDs are cleanly deduplicated."""
        t_id = f"tnt_idem_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        event_id = f"evt_dup_{uuid.uuid4().hex[:12]}"
        payload = {
            "id": event_id,
            "type": "invoice.payment_succeeded",
            "data": {"object": {"metadata": {"tenant_id": t_id}}}
        }
        payload_str = json.dumps(payload)
        now = int(time.time())
        sig_header = self._generate_stripe_header(payload_str, self.engine.stripe.webhook_secret, now)

        # First delivery
        res1 = self.engine.process_stripe_webhook(payload_str=payload_str, sig_header=sig_header)
        self.assertTrue(res1["success"])
        self.assertEqual(res1["status"], "PROCESSED")

        # Second delivery (identical event_id)
        res2 = self.engine.process_stripe_webhook(payload_str=payload_str, sig_header=sig_header)
        self.assertTrue(res2["success"])
        self.assertEqual(res2["status"], "DUPLICATE_IGNORED")

    def test_16_stripe_webhook_lifecycle_event_routing(self):
        """Verifies payment failure moves subscription to PAST_DUE, payment success restores to ACTIVE."""
        t_id = f"tnt_route_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        # 1. Payment Failed -> PAST_DUE
        fail_event = {
            "id": f"evt_fail_{uuid.uuid4().hex[:8]}",
            "type": "invoice.payment_failed",
            "data": {"object": {"metadata": {"tenant_id": t_id}}}
        }
        fail_str = json.dumps(fail_event)
        sig1 = self._generate_stripe_header(fail_str, self.engine.stripe.webhook_secret, int(time.time()))
        res1 = self.engine.process_stripe_webhook(fail_str, sig1)
        self.assertTrue(res1["success"])

        sub = self.engine.get_or_create_subscription(t_id)
        self.assertEqual(sub.status, SubscriptionStatus.PAST_DUE)

        # 2. Payment Succeeded -> ACTIVE
        success_event = {
            "id": f"evt_succ_{uuid.uuid4().hex[:8]}",
            "type": "invoice.payment_succeeded",
            "data": {"object": {"metadata": {"tenant_id": t_id}}}
        }
        succ_str = json.dumps(success_event)
        sig2 = self._generate_stripe_header(succ_str, self.engine.stripe.webhook_secret, int(time.time()))
        res2 = self.engine.process_stripe_webhook(succ_str, sig2)
        self.assertTrue(res2["success"])

        sub = self.engine.get_or_create_subscription(t_id)
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)

        # 3. Stripe customer.subscription.deleted -> CANCELLED
        del_event = {
            "id": f"evt_del_{uuid.uuid4().hex[:8]}",
            "type": "customer.subscription.deleted",
            "data": {"object": {"metadata": {"tenant_id": t_id}}}
        }
        del_str = json.dumps(del_event)
        sig3 = self._generate_stripe_header(del_str, self.engine.stripe.webhook_secret, int(time.time()))
        res3 = self.engine.process_stripe_webhook(del_str, sig3)
        self.assertTrue(res3["success"])

        sub = self.engine.get_or_create_subscription(t_id)
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)

        # Entitlement check after cancellation must be rejected
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 1000)
        self.assertFalse(allowed)
        self.assertIn("CANCELLED", msg)

    # =========================================================================
    # WORKSTREAM 4: RAZORPAY CRYPTOGRAPHIC WEBHOOK ENGINE
    # =========================================================================

    def _generate_razorpay_header(self, payload: str, secret: str) -> str:
        return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def test_17_razorpay_webhook_valid_signature_processing(self):
        """Verifies successful cryptographic HMAC-SHA256 processing of Razorpay webhook."""
        t_id = f"tnt_rzp_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        event_id = f"evt_rzp_{uuid.uuid4().hex[:12]}"
        payload = {
            "event_id": event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_12345",
                        "notes": {"tenant_id": t_id}
                    }
                }
            }
        }
        payload_str = json.dumps(payload)
        sig = self._generate_razorpay_header(payload_str, self.engine.razorpay.webhook_secret)

        res = self.engine.process_razorpay_webhook(payload_str=payload_str, sig_header=sig)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "PROCESSED")

    def test_18_razorpay_webhook_tampered_signature_rejection(self):
        """Verifies rejection of tampered Razorpay webhook signature."""
        payload = {"event_id": "evt_tampered_rzp", "event": "payment.captured"}
        payload_str = json.dumps(payload)
        res = self.engine.process_razorpay_webhook(payload_str=payload_str, sig_header="tampered_signature")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "INVALID_SIGNATURE")
        self.assertEqual(res["code"], 401)

    def test_19_razorpay_webhook_idempotency_deduplication(self):
        """Verifies duplicate Razorpay events are suppressed."""
        t_id = f"tnt_rzpdup_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        event_id = f"evt_rzp_dup_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event": "subscription.charged",
            "payload": {"subscription": {"entity": {"notes": {"tenant_id": t_id}}}}
        }
        payload_str = json.dumps(payload)
        sig = self._generate_razorpay_header(payload_str, self.engine.razorpay.webhook_secret)

        res1 = self.engine.process_razorpay_webhook(payload_str, sig)
        self.assertTrue(res1["success"])
        self.assertEqual(res1["status"], "PROCESSED")

        res2 = self.engine.process_razorpay_webhook(payload_str, sig)
        self.assertTrue(res2["success"])
        self.assertEqual(res2["status"], "DUPLICATE_IGNORED")

    def test_20_razorpay_webhook_lifecycle_event_routing(self):
        """Verifies Razorpay subscription.halted moves to PAST_DUE and subscription.charged restores ACTIVE."""
        t_id = f"tnt_rzproute_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        # subscription.halted
        halt_ev = {
            "event_id": f"evt_halt_{uuid.uuid4().hex[:8]}",
            "event": "subscription.halted",
            "payload": {"subscription": {"entity": {"notes": {"tenant_id": t_id}}}}
        }
        halt_str = json.dumps(halt_ev)
        sig1 = self._generate_razorpay_header(halt_str, self.engine.razorpay.webhook_secret)
        self.engine.process_razorpay_webhook(halt_str, sig1)

        sub = self.engine.get_or_create_subscription(t_id)
        self.assertEqual(sub.status, SubscriptionStatus.PAST_DUE)

        # subscription.charged
        charge_ev = {
            "event_id": f"evt_charge_{uuid.uuid4().hex[:8]}",
            "event": "subscription.charged",
            "payload": {"subscription": {"entity": {"notes": {"tenant_id": t_id}}}}
        }
        charge_str = json.dumps(charge_ev)
        sig2 = self._generate_razorpay_header(charge_str, self.engine.razorpay.webhook_secret)
        self.engine.process_razorpay_webhook(charge_str, sig2)

        sub = self.engine.get_or_create_subscription(t_id)
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)

        # 3. Razorpay subscription.cancelled -> CANCELLED
        canc_ev = {
            "event_id": f"evt_canc_{uuid.uuid4().hex[:8]}",
            "event": "subscription.cancelled",
            "payload": {"subscription": {"entity": {"notes": {"tenant_id": t_id}}}}
        }
        canc_str = json.dumps(canc_ev)
        sig3 = self._generate_razorpay_header(canc_str, self.engine.razorpay.webhook_secret)
        res3 = self.engine.process_razorpay_webhook(canc_str, sig3)
        self.assertTrue(res3["success"])

        sub = self.engine.get_or_create_subscription(t_id)
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)

        # Entitlement check after cancellation must be rejected
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 1000)
        self.assertFalse(allowed)
        self.assertIn("CANCELLED", msg)

    # =========================================================================
    # WORKSTREAM 5: ECONOMIC GOVERNOR RECONCILIATION & INVOICING
    # =========================================================================

    def test_21_economic_governor_settlement_reconciliation(self):
        """Verifies economic governor budget settlements cleanly update the SaaS billing usage snapshot."""
        t_id = f"tnt_econ_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        res_id = f"res_{uuid.uuid4().hex[:12]}"
        actual_tokens = 75_000
        actual_usd = 3.75

        res = self.engine.reconcile_economic_settlement(
            tenant_id=t_id,
            reservation_id=res_id,
            actual_tokens=actual_tokens,
            actual_usd=actual_usd
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["reconciled"])

        snapshot = self.engine.get_or_create_tenant(t_id)
        self.assertEqual(snapshot.tokens_consumed, actual_tokens)
        self.assertEqual(snapshot.total_cost_usd, actual_usd)

    def test_22_economic_settlement_duplicate_reconciliation_suppressed(self):
        """Verifies duplicate settlement reconciliation calls are safely ignored without double-counting."""
        t_id = f"tnt_econdup_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, status=SubscriptionStatus.ACTIVE)

        res_id = f"res_{uuid.uuid4().hex[:12]}"
        # First reconciliation
        self.engine.reconcile_economic_settlement(t_id, res_id, actual_tokens=50_000, actual_usd=2.50)

        # Duplicate reconciliation
        dup_res = self.engine.reconcile_economic_settlement(t_id, res_id, actual_tokens=50_000, actual_usd=2.50)
        self.assertTrue(dup_res["success"])
        self.assertFalse(dup_res["reconciled"])

        snapshot = self.engine.get_or_create_tenant(t_id)
        # Usage must remain 50,000 tokens, NOT 100,000
        self.assertEqual(snapshot.tokens_consumed, 50_000)
        self.assertEqual(snapshot.total_cost_usd, 2.50)

    def test_23_invoice_generation_accuracy(self):
        """Verifies invoice generation aggregates base plan price and metered usage with line items."""
        t_id = f"tnt_inv_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, tier=SubscriptionTier.PRO, status=SubscriptionStatus.ACTIVE)
        self.engine.record_usage(t_id, "tokens", amount=100_000, cost_usd=15.50)

        now = time.time()
        invoice = self.engine.generate_tenant_invoice(t_id, period_start=now - 86400 * 30, period_end=now)

        self.assertEqual(invoice["tenant_id"], t_id)
        self.assertEqual(invoice["currency"], "USD")
        self.assertEqual(invoice["status"], "PAID")
        # Pro base fee ($199.00) + metered usage ($15.50) = $214.50
        self.assertEqual(invoice["amount_due_usd"], 214.50)
        self.assertEqual(invoice["amount_paid_usd"], 214.50)
        self.assertEqual(len(invoice["line_items"]), 2)

    def test_24_plan_upgrade_and_downgrade_state(self):
        """Verifies dynamic tier changes update quotas immediately."""
        t_id = f"tnt_upg_{uuid.uuid4().hex[:6]}"
        self.engine.get_or_create_subscription(t_id, tier=SubscriptionTier.STARTER, status=SubscriptionStatus.ACTIVE)

        # Consume 12M tokens (Starter limit is 10M, Enterprise is 500M)
        self.engine.record_usage(t_id, "tokens", amount=12_000_000)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 1000)
        self.assertFalse(allowed)

        # Upgrade to Enterprise
        self.engine.upgrade_plan(t_id, SubscriptionTier.ENTERPRISE)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 1000)
        self.assertTrue(allowed)

        # Downgrade back to Starter
        self.engine.downgrade_plan(t_id, SubscriptionTier.STARTER)
        allowed, msg = self.engine.check_entitlement(t_id, "tokens", 1000)
        self.assertFalse(allowed)

    def test_25_financial_charge_idempotency_defense(self):
        """Verifies customer charges defend against double-charging via idempotency keys."""
        t_id = f"tnt_chg_{uuid.uuid4().hex[:6]}"
        key = f"key_{uuid.uuid4().hex[:8]}"

        charge1 = self.engine.charge_customer(tenant_id=t_id, amount_usd=99.0, idempotency_key=key)
        self.assertTrue(charge1["success"])
        self.assertFalse(charge1["duplicate"])

        # Identical charge attempt
        charge2 = self.engine.charge_customer(tenant_id=t_id, amount_usd=99.0, idempotency_key=key)
        self.assertTrue(charge2["success"])
        self.assertTrue(charge2["duplicate"])


if __name__ == "__main__":
    unittest.main()
