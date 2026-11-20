"""ZONATA Sovereign Core — Kaizen Optimizer & Shadow-Mode Comparator.

Implements Stage 7:
- Formulates measurable Kaizen improvement proposals from empirical waste data.
- Runs side-by-side Shadow Mode simulations comparing Candidate Pack vs Production Baseline.
- Promotes improvements only when evidence demonstrates superior FPY, cycle time, or cost.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.kaizen.metrics import KaizenMetricsStore, WasteEvent
from core.process_packs.schema import ProcessPack
from core.process_packs.simulator import ProcessPackSimulator, SimulationResult

logger = logging.getLogger("zonata.core.kaizen.optimizer")


@dataclass
class KaizenProposal:
    proposal_id: str
    pack_id: str
    title: str
    target_waste: str
    rationale: str
    recommended_changes: Dict[str, Any]
    projected_fpy_improvement: float
    projected_cycle_time_reduction_percent: float
    created_at: float = field(default_factory=time.time)


@dataclass
class ShadowComparisonReport:
    pack_id: str
    baseline_fpy: float
    candidate_fpy: float
    fpy_delta: float
    baseline_cycle_time_seconds: float
    candidate_cycle_time_seconds: float
    cycle_time_delta_seconds: float
    promotable: bool
    summary: str


class KaizenOptimizer:
    """Continuous improvement engine with empirical shadow-mode evaluation."""

    def __init__(
        self,
        metrics_store: Optional[KaizenMetricsStore] = None,
        simulator: Optional[ProcessPackSimulator] = None
    ):
        self.metrics_store = metrics_store or KaizenMetricsStore()
        self.simulator = simulator or ProcessPackSimulator()

    def generate_proposal(
        self,
        tenant_id: str,
        pack_id: str
    ) -> Optional[KaizenProposal]:
        """Formulates an improvement proposal based on recorded waste events."""
        kpis = self.metrics_store.get_aggregate_kpis(tenant_id, pack_id)
        if kpis["total_runs"] == 0:
            return None

        # Check FPY bottleneck
        if kpis["first_pass_yield"] < 0.95:
            return KaizenProposal(
                proposal_id=f"kzn_{pack_id}_fpy_boost",
                pack_id=pack_id,
                title="Early Input Pre-Validation to Eliminate Downstream Rework",
                target_waste="rework",
                rationale=f"Current FPY is {kpis['first_pass_yield']*100:.1f}%. Adding pre-validation eliminates defective intake.",
                recommended_changes={"add_pre_validation": True, "strict_schema": True},
                projected_fpy_improvement=0.04,
                projected_cycle_time_reduction_percent=15.0
            )

        # Check Cycle Time bottleneck
        if kpis["avg_cycle_time_seconds"] > 10.0:
            return KaizenProposal(
                proposal_id=f"kzn_{pack_id}_speed_opt",
                pack_id=pack_id,
                title="Parallelization of Non-Dependent Verification Steps",
                target_waste="waiting",
                rationale="Compress cycle time by parallelizing document checks.",
                recommended_changes={"parallelize_steps": ["step_compliance", "step_enrichment"]},
                projected_fpy_improvement=0.01,
                projected_cycle_time_reduction_percent=25.0
            )

        return None

    def run_shadow_comparison(
        self,
        baseline_pack: ProcessPack,
        candidate_pack: ProcessPack
    ) -> ShadowComparisonReport:
        """Executes candidate vs baseline across simulation scenarios in shadow mode."""
        scenarios = baseline_pack.simulation_scenarios
        if not scenarios:
            raise ValueError(f"No simulation scenarios defined for pack '{baseline_pack.pack_id}'.")

        baseline_results: List[SimulationResult] = []
        candidate_results: List[SimulationResult] = []

        for sc in scenarios:
            b_res = self.simulator.run_scenario(baseline_pack, sc)
            c_res = self.simulator.run_scenario(candidate_pack, sc)
            baseline_results.append(b_res)
            candidate_results.append(c_res)

        b_fpy = sum(r.first_pass_yield for r in baseline_results) / len(baseline_results)
        c_fpy = sum(r.first_pass_yield for r in candidate_results) / len(candidate_results)
        b_time = sum(r.cycle_time_seconds for r in baseline_results) / len(baseline_results)
        c_time = sum(r.cycle_time_seconds for r in candidate_results) / len(candidate_results)

        fpy_delta = round(c_fpy - b_fpy, 4)
        time_delta = round(c_time - b_time, 4)

        # Promotable if FPY did not degrade and cycle time did not significantly increase
        promotable = (c_fpy >= b_fpy) and (time_delta <= 0.1)

        summary = (
            f"Candidate evaluation: FPY delta={fpy_delta:+.2%}, "
            f"Cycle time delta={time_delta:+.3f}s. "
            f"Decision: {'PROMOTABLE' if promotable else 'REJECTED (No improvement)'}."
        )

        return ShadowComparisonReport(
            pack_id=baseline_pack.pack_id,
            baseline_fpy=b_fpy,
            candidate_fpy=c_fpy,
            fpy_delta=fpy_delta,
            baseline_cycle_time_seconds=b_time,
            candidate_cycle_time_seconds=c_time,
            cycle_time_delta_seconds=time_delta,
            promotable=promotable,
            summary=summary
        )
