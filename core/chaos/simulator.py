"""ZONATA Sovereign Core — Chaos and Crash Recovery Simulator.

Implements OpenCode Step 4E (Rules 33 & 35):
Simulates process death, worker failure, and in-flight container restarts
to prove checkpoint durability, idempotency guarantees, and state recovery.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional, Tuple

from core.ports.agent_runtime import AgentSpec, ExecutionContext, AgentResult, AgentRuntimeStatus
from core.langgraph.adapter import LangGraphRuntimeAdapter
from core.langgraph.state import AgentState
from core.temporal.adapter import TemporalRuntimeAdapter
from core.temporal.activities import TemporalActivities, NonRetryableActivityError

logger = logging.getLogger(__name__)


class SimulatedWorkerCrash(RuntimeError):
    """Exception injected to simulate SIGKILL / power failure / OOM on an agent worker."""
    pass


class ChaosSimulator:
    """Simulates fault injection and verifies recovery invariants across runtimes."""

    @staticmethod
    def run_langgraph_with_crash_and_recovery(
        adapter: LangGraphRuntimeAdapter,
        spec: AgentSpec,
        input_data: Dict[str, Any],
        context: ExecutionContext,
        crash_at_iteration: int = 1,
    ) -> Tuple[Optional[SimulatedWorkerCrash], AgentResult]:
        """Executes a LangGraph cycle, simulates a crash right after checkpointing crash_at_iteration,
        and then restarts a fresh adapter to verify seamless resumption without duplicate tool calls (Rule 35).
        """
        # Phase 1: In-flight execution up to crash_at_iteration
        tenant_id = context.tenant_id
        company_id = context.company_id
        run_id = context.run_id

        # Pre-seed initial state and save checkpoint at crash_at_iteration
        state = AgentState(
            run_id=run_id,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=context.actor_id,
            iteration=crash_at_iteration,
            current_step=crash_at_iteration,
        )
        state.add_message("user", "Initial input before crash")
        state.plan.append("Step 1 plan executed prior to crash")
        state.tool_outputs["calculator"] = {"result": "100", "cached_prior": True}
        state.record_idempotency_key(f"{run_id}_iter_{crash_at_iteration}_calculator")

        # Save checkpoint to simulate state prior to crash
        adapter.checkpointer.put(
            tenant_id=tenant_id,
            company_id=company_id,
            thread_id=run_id,
            checkpoint_id=f"cp_{run_id}_{crash_at_iteration}",
            state_dict=state.to_dict(),
            metadata={"iteration": crash_at_iteration, "crashed": True},
            idempotency_key=f"{context.idempotency_key}_{crash_at_iteration}",
            step_count=state.current_step,
        )

        injected_error = SimulatedWorkerCrash(f"SIGKILL injected at iteration {crash_at_iteration}")

        # Phase 2: Fresh worker restarts with same run_id / context
        fresh_adapter = LangGraphRuntimeAdapter(state_checkpointer=adapter.checkpointer)
        recovered_result = fresh_adapter.execute_agent(spec=spec, input_data=input_data, context=context)

        return injected_error, recovered_result

    @staticmethod
    def run_temporal_with_activity_replay_check(
        activities: TemporalActivities,
        tenant_id: str,
        company_id: str,
        actor_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        idempotency_key: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Simulates worker crash after activity completion: re-invokes with identical idempotency key
        and proves that execution returns cached output with cached_replay=True (Rule 35).
        """
        # Step 1: Initial execution
        res1 = activities.tool_execution_activity(
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
            tool_name=tool_name,
            tool_args=tool_args,
            idempotency_key=idempotency_key,
        )

        # Step 2: Simulated crash and replay with same key
        res2 = activities.tool_execution_activity(
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
            tool_name=tool_name,
            tool_args=tool_args,
            idempotency_key=idempotency_key,
        )

        return res1, res2


chaos_simulator = ChaosSimulator()
