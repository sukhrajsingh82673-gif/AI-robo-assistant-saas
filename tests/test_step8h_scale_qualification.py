"""
Tests for Sub-Step 8H: Scale, Cost & Reliability Qualification (Rule 67, 68, 73, 76, ADR 0043, 0044)
Validates load & soak profiling, multi-tenant noisy-neighbor token-bucket isolation,
50-entity group consolidation scaling, chaos injection with idempotent recovery, and unit economic cost modeling.
"""

import pytest
import time

from core.scale.load_profile import LoadProfiler
from core.scale.noisy_neighbor import (
    ConcurrencyGovernor,
    RateLimitExceededError,
)
from core.scale.consolidation_scale import ConsolidationScaleBenchmark
from core.scale.chaos import (
    ChaosInjector,
    IdempotentRetryRunner,
    TransientNetworkGlitchError,
)
from core.scale.cost_model import UnitCostModel


class TestStep8HScaleQualification:

    # 1. Load Profiling and Percentiles
    def test_01_load_profiling_and_percentiles(self):
        durations = [10.0, 15.0, 20.0, 25.0, 100.0]
        pcts = LoadProfiler.calculate_percentiles(durations)
        assert pcts["p50"] == 20.0
        assert pcts["max"] == 100.0

        # Run simulated soak run
        def dummy_task():
            # Light compute
            sum(i * i for i in range(100))

        soak_res = LoadProfiler.execute_soak_run(dummy_task, iterations=50, simulated_concurrency=5)
        assert soak_res["iterations"] == 50
        assert soak_res["error_count"] == 0
        assert soak_res["soak_stable"] is True
        assert soak_res["throughput_rps"] > 10.0

    # 2. Multi-Tenant Noisy-Neighbor Isolation (Rule 68)
    def test_02_noisy_neighbor_isolation_governor(self):
        # Capacity of 20 tokens, refill of 1 token/sec
        governor = ConcurrencyGovernor(default_capacity=20.0, default_refill_rate=1.0)

        # Tenant A (aggressive bursting neighbor) attempts 40 requests at once
        tenant_a_admitted = 0
        tenant_a_throttled = 0
        for _ in range(40):
            if governor.try_admit_request("TENANT-A-NOISY"):
                tenant_a_admitted += 1
            else:
                tenant_a_throttled += 1

        assert tenant_a_admitted == 20
        assert tenant_a_throttled == 20

        # Tenant B (well-behaved neighbor) on same cluster attempts 10 requests
        tenant_b_admitted = 0
        tenant_b_throttled = 0
        for _ in range(10):
            if governor.try_admit_request("TENANT-B-CALM"):
                tenant_b_admitted += 1
            else:
                tenant_b_throttled += 1

        # Tenant B is completely unaffected by Tenant A's exhaustion!
        assert tenant_b_admitted == 10
        assert tenant_b_throttled == 0

        # Verify exception raising
        with pytest.raises(RateLimitExceededError) as exc:
            governor.admit_or_raise("TENANT-A-NOISY")
        assert "RATE_LIMIT_EXCEEDED" in str(exc.value)

    # 3. 50-Entity Multi-National Group Consolidation Scaling (ADR 0043)
    def test_03_fifty_entity_consolidation_scale_benchmark(self):
        res = ConsolidationScaleBenchmark.run_50_entity_scale_test()

        assert res["entities_count"] == 50
        assert res["currencies_count"] == 10
        assert res["intercompany_txs_count"] == 500
        assert res["elimination_entries_count"] == 500

        # CRITICAL ACCOUNTING INVARIANT: Net eliminations must be EXACTLY ZERO
        assert res["net_elimination_balance"] == 0

        # Execution SLA: Under 500 milliseconds
        assert res["sub_500ms_sla_passed"] is True
        assert "consolidation_seal" in res

    # 4. Chaos Injection and Idempotency Key Deduplication (Rule 76)
    def test_04_chaos_injection_and_idempotent_retry(self):
        runner = IdempotentRetryRunner(max_retries=3, base_backoff_ms=5.0)
        chaos = ChaosInjector(failure_probability=1.0, max_failures=2)

        call_counter = {"count": 0}

        def unstable_business_tx():
            call_counter["count"] += 1
            return {"status": "JOURNAL_COMMITTED", "tx_id": "TX-9901"}

        # First execution: experiences 2 transient failures, retries, and succeeds on 3rd attempt
        result = runner.execute_idempotent_operation(
            idempotency_key="IDEMP-KEY-2026-001",
            operation=unstable_business_tx,
            chaos_injector=chaos
        )

        assert result["status"] == "JOURNAL_COMMITTED"
        assert result["attempts_required"] == 3
        assert result["cached_replay"] is False
        assert call_counter["count"] == 1

        # Second execution with same idempotency key returns cached replay without re-executing
        replay = runner.execute_idempotent_operation(
            idempotency_key="IDEMP-KEY-2026-001",
            operation=unstable_business_tx
        )
        assert replay["status"] == "JOURNAL_COMMITTED"
        assert replay["cached_replay"] is True
        # Call counter did NOT increment
        assert call_counter["count"] == 1

    # 5. Unit Economic Cost Modeling & Monthly Budget Forecast
    def test_05_unit_economic_cost_modeling(self):
        # 1. Single AP invoice unit cost
        ap_unit = UnitCostModel.calculate_task_unit_cost("AP_INVOICE_MATCH")
        assert ap_unit["task_type"] == "AP_INVOICE_MATCH"
        # Total minor unit cost should be under $0.50 (50 cents)
        assert ap_unit["unit_cost_usd"] < 0.50
        # Human cost is $8.75 (15 min at $35/hr) -> > 90% savings
        assert ap_unit["savings_percent"] > 90.0

        # 2. Monthly enterprise forecast
        monthly_vol = {
            "AP_INVOICE_MATCH": 2000,
            "FREIGHT_BILL_OF_LADING": 1000,
            "PAYROLL_CALCULATION_LINE": 500,
        }
        forecast = UnitCostModel.project_monthly_company_budget("CORP-ENTERPRISE-01", monthly_vol)
        assert forecast["company_id"] == "CORP-ENTERPRISE-01"
        assert forecast["projected_monthly_system_cost_usd"] > 0.0
        assert forecast["projected_monthly_net_savings_usd"] > 10000.0  # Massive savings
        assert forecast["overall_savings_percent"] > 90.0
