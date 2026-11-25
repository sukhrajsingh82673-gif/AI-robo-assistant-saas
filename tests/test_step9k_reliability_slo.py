"""
Tests for Sub-Step 9K: Reliability, SLO Tracking, Disaster Recovery, and Chaos Testing.
"""

import pytest
from core.reliability.slo_tracker import SloTracker
from core.reliability.dr_drill import DisasterRecoveryDrill
from core.reliability.chaos import ChaosSimulator


class TestStep9kReliabilitySlo:

    def test_slo_tracker_budget_calculation_and_deployment_freeze(self):
        """Verify error budget computation, burn-rate alerts, and automated deployment freeze."""
        tracker = SloTracker()

        # 1. 10,000 events with 9,995 good events (99.95% SLI vs 99.9% target)
        # Target allowed errors: 10 errors (0.1%). Actual errors: 5 errors.
        # Remaining budget = 50%
        tracker.record_event("api_availability", is_good=True, count=9995)
        tracker.record_event("api_availability", is_good=False, count=5)

        st1 = tracker.get_budget_status("api_availability")
        assert st1.current_sli_percent == 99.95
        assert st1.budget_remaining_percent == 50.0
        assert not st1.is_deployment_frozen
        assert tracker.is_release_permitted()[0] is True

        # 2. Burn additional errors pushing total errors to 15 (0.15% error rate > 0.1% target)
        tracker.record_event("api_availability", is_good=False, count=10)
        st2 = tracker.get_budget_status("api_availability")
        assert st2.current_sli_percent < 99.9
        assert st2.budget_remaining_percent < 0.0
        assert st2.is_deployment_frozen is True
        assert "ALERT: Error budget EXHAUSTED" in st2.burn_rate_alert

        # 3. Deployment gate BLOCKS release
        allowed, reason = tracker.is_release_permitted()
        assert not allowed
        assert "Deployment BLOCKED" in reason

    def test_disaster_recovery_drill_failover_and_rto_rpo(self):
        """Verify simulated primary crash triggers replica promotion within RTO <= 30s and RPO <= 1s."""
        drill = DisasterRecoveryDrill()
        result = drill.simulate_primary_crash_and_failover()

        assert result.success is True
        assert result.primary_crashed is True
        assert result.replica_promoted is True
        assert result.rto_seconds <= 30.0  # RTO compliance
        assert result.rpo_seconds <= 1.0   # RPO compliance
        assert result.data_loss_detected is False
        assert drill.primary_online is True

    def test_chaos_simulation_webhook_payment_and_cache(self):
        """Verify chaos resilience: webhook DLQ, payment provider outage queuing, and cache eviction."""
        # 1. Webhook endpoint timeout -> Retries with backoff and routes to DLQ
        res_wh = ChaosSimulator.simulate_webhook_timeout(max_retries=3)
        assert res_wh.handled_cleanly is True
        assert res_wh.retried_with_backoff is True
        assert res_wh.dead_letter_queued is True
        assert res_wh.data_preserved is True

        # 2. Payment gateway 503 outage -> Queued in reconciliation ledger
        res_pay = ChaosSimulator.simulate_payment_gateway_outage()
        assert res_pay.handled_cleanly is True
        assert res_pay.data_preserved is True
        assert "pending reconciliation ledger" in res_pay.recovery_message

        # 3. Cache flush -> Seamless DB fallback
        res_cache = ChaosSimulator.simulate_cache_eviction()
        assert res_cache.handled_cleanly is True
        assert res_cache.data_preserved is True
