"""ZONATA Sovereign Core — Process Pack Simulator.

Executes simulation scenarios to measure Lean KPIs (cycle time, first-pass yield,
cost per unit, error rate) before production deployment.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.process_packs.engine import ProcessExecutionEngine, ProcessInstance
from core.process_packs.schema import ProcessPack, SimulationScenario

logger = logging.getLogger("zonata.core.process_packs.simulator")


@dataclass
class SimulationResult:
    scenario_id: str
    pack_id: str
    status: str
    expected_status: str
    passed: bool
    cycle_time_seconds: float
    total_cost_usd: float
    first_pass_yield: float
    errors: List[str]
    actual_outputs: Dict[str, Any]


class ProcessPackSimulator:
    """Simulation harness for Process Packs."""

    def __init__(self, engine: Optional[ProcessExecutionEngine] = None):
        self.engine = engine or ProcessExecutionEngine()

    def run_scenario(
        self,
        pack: ProcessPack,
        scenario: SimulationScenario,
        tenant_id: str = "tnt_simulation",
        company_id: str = "comp_simulation",
        step_handler: Optional[Callable] = None
    ) -> SimulationResult:
        """Executes a simulation scenario end-to-end and computes KPIs."""
        start_time = time.time()
        errors: List[str] = []

        instance = self.engine.create_instance(
            tenant_id=tenant_id,
            company_id=company_id,
            pack=pack,
            initial_inputs=scenario.initial_inputs
        )

        # Run through all steps until terminal status
        while instance.status == "RUNNING" and instance.current_step_index < len(pack.steps):
            instance = self.engine.execute_next_step(instance, pack, step_handler=step_handler)

        duration = time.time() - start_time
        passed = True

        if instance.status != scenario.expected_status:
            passed = False
            errors.append(f"Status mismatch: expected '{scenario.expected_status}', got '{instance.status}'.")

        # Validate expected outputs
        for k, v in scenario.expected_outputs.items():
            if k not in instance.context_data:
                passed = False
                errors.append(f"Missing expected output '{k}' in context data.")
            elif instance.context_data[k] != v:
                passed = False
                errors.append(f"Value mismatch for '{k}': expected '{v}', got '{instance.context_data[k]}'.")

        # Compute First-Pass Yield (1.0 if no defects/rework, 0.0 otherwise)
        had_rework = any(
            any(w in ("rework", "defects") for w in rec.waste_detected)
            for rec in instance.records
        )
        fpy = 0.0 if (had_rework or not passed) else 1.0

        return SimulationResult(
            scenario_id=scenario.scenario_id,
            pack_id=pack.pack_id,
            status=instance.status,
            expected_status=scenario.expected_status,
            passed=passed,
            cycle_time_seconds=duration,
            total_cost_usd=instance.total_cost_usd,
            first_pass_yield=fpy,
            errors=errors,
            actual_outputs=dict(instance.context_data)
        )
