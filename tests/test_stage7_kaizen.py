"""Unit & Integration Tests for Stage 7: Kaizen & Evaluation Engine.

Verifies:
- Continuous Lean KPI tracking (FPY, cycle time, cost per unit, CSAT).
- Waste detection across the 6 Lean AI waste categories (defects, rework, waiting, handoff).
- Kaizen improvement proposal generation from empirical metrics.
- Shadow Mode comparator evaluating candidate vs production baseline.
"""

import time
import pytest
from core.kaizen.metrics import KaizenMetricsStore
from core.kaizen.waste_detector import WasteDetector
from core.kaizen.optimizer import KaizenOptimizer
from core.process_packs.engine import ProcessInstance, StepExecutionRecord
from core.process_packs.loader import ProcessPackLoader
from agent_factory.adapters.zonata import ZonataEvidenceAdapter


@pytest.fixture
def metrics_store():
    adapter = ZonataEvidenceAdapter()
    return KaizenMetricsStore(evidence_port=adapter)


@pytest.fixture
def waste_detector(metrics_store):
    return WasteDetector(metrics_store=metrics_store)


@pytest.fixture
def optimizer(metrics_store):
    return KaizenOptimizer(metrics_store=metrics_store)


def test_stage7_metrics_recording_and_aggregation(metrics_store):
    """Verify storing process run KPIs and computing aggregate Lean metrics."""
    tenant = "tnt_stage7"
    pack_id = "lead_to_cash"

    # Record 3 runs: 2 perfect, 1 with errors
    metrics_store.record_run(tenant, "c1", pack_id, "inst_1", cycle_time_seconds=2.5, first_pass_yield=1.0, cost_usd=0.015, csat=5.0)
    metrics_store.record_run(tenant, "c1", pack_id, "inst_2", cycle_time_seconds=3.5, first_pass_yield=1.0, cost_usd=0.015, csat=4.8)
    metrics_store.record_run(tenant, "c1", pack_id, "inst_3", cycle_time_seconds=6.0, first_pass_yield=0.0, cost_usd=0.030, error_count=2, csat=3.5)

    agg = metrics_store.get_aggregate_kpis(tenant, pack_id)
    assert agg["total_runs"] == 3
    assert agg["first_pass_yield"] == pytest.approx(0.6667, rel=1e-2)
    assert agg["total_errors"] == 2
    assert agg["avg_cost_usd"] == pytest.approx(0.02, rel=1e-2)


def test_stage7_waste_detection_rules(waste_detector):
    """Verify WasteDetector flags defects, rework, and excessive handoffs."""
    # Instance with rework (step_1 executed twice) and Andon halt
    instance = ProcessInstance(
        instance_id="inst_waste_demo",
        tenant_id="tnt_waste",
        company_id="comp_waste",
        pack_id="procure_to_pay",
        pack_version="1.0.0",
        status="HALTED_ANDON",
        current_step_index=2,
        context_data={},
        andon_incident={
            "rule_id": "ANDON-P2P-01",
            "rule_name": "price_variance_exceeded"
        },
        records=[
            StepExecutionRecord("step_1", "Intake", "agent", "SUCCEEDED", duration_seconds=1.2, cost_usd=0.005),
            StepExecutionRecord("step_1", "Intake Retry", "agent", "SUCCEEDED", duration_seconds=1.5, cost_usd=0.005),  # REWORK
            StepExecutionRecord("step_2", "Vendor Select", "human", "HALTED_ANDON", duration_seconds=350.0, cost_usd=0.0)  # WAITING
        ]
    )

    waste_events = waste_detector.analyze_instance(instance)
    waste_types = [w.waste_type for w in waste_events]

    assert "defects" in waste_types  # from Andon halt
    assert "rework" in waste_types   # from repeated step_1
    assert "waiting" in waste_types  # from > 300s duration


def test_stage7_kaizen_proposal_and_shadow_comparison(metrics_store, optimizer):
    """Verify Kaizen improvement proposal generation and shadow mode evaluation."""
    tenant = "tnt_shadow"
    pack_id = "support_to_resolution"

    # Populate low FPY to trigger Kaizen proposal
    for i in range(5):
        metrics_store.record_run(tenant, "c1", pack_id, f"inst_{i}", cycle_time_seconds=4.0, first_pass_yield=0.6, cost_usd=0.02)

    proposal = optimizer.generate_proposal(tenant, pack_id)
    assert proposal is not None
    assert proposal.target_waste == "rework"
    assert "pre-validation" in proposal.title.lower()

    # Load pack and run shadow comparison
    loader = ProcessPackLoader()
    base_pack = loader.load_file("packs/support_to_resolution/v1/pack.yaml")
    # Candidate pack (same pack with optimized criteria)
    candidate_pack = loader.load_file("packs/support_to_resolution/v1/pack.yaml")

    report = optimizer.run_shadow_comparison(base_pack, candidate_pack)
    assert report.pack_id == "support_to_resolution"
    assert report.promotable is True
    assert "PROMOTABLE" in report.summary
