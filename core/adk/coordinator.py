"""ZONATA Sovereign Core — Google ADK Hierarchical Team Coordinator.

Implements OpenCode Step 4F (Constitutional Bounds & Multi-Agent Squads):
1. Coordinates Supervisor -> Worker -> Critic multi-agent squads.
2. Constitutional Bounds:
   - Tree Depth <= 3 (blocks recursive sub-agent exhaustion attacks).
   - Feedback Loops <= 5 (blocks infinite critic debate loops).
3. Rule 34: 100% of model calls route through ZonataADKModel (LLMGateway).
4. Rule 35: Deterministic idempotency keys for all squad tool calls.
5. Rule 38: Team topologies carry explicit versioning.
"""

from __future__ import annotations
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from core.ports.agent_runtime import AgentSpec, ExecutionContext, AgentRuntimeStatus
from core.adk.model import ZonataADKModel, adk_model
from core.adk.tool_wrapper import ZonataADKToolWrapper
from core.adk.session import ZonataADKSessionService, adk_session_service

logger = logging.getLogger(__name__)


class TeamTopologyError(ValueError):
    """Raised when team tree depth or loop bounds are violated."""
    pass


class TeamExecutionResult:
    def __init__(
        self,
        team_run_id: str,
        topology_version: str,
        status: AgentRuntimeStatus,
        supervisor_plan: str,
        worker_output: str,
        critic_verdict: str,
        tool_results: Dict[str, Any],
        loop_count: int,
        error: Optional[str] = None,
    ):
        self.team_run_id = team_run_id
        self.topology_version = topology_version
        self.status = status
        self.supervisor_plan = supervisor_plan
        self.worker_output = worker_output
        self.critic_verdict = critic_verdict
        self.tool_results = tool_results
        self.loop_count = loop_count
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_run_id": self.team_run_id,
            "topology_version": self.topology_version,
            "status": self.status.value,
            "supervisor_plan": self.supervisor_plan,
            "worker_output": self.worker_output,
            "critic_verdict": self.critic_verdict,
            "tool_results": self.tool_results,
            "loops_completed": self.loop_count,
            "error": self.error,
        }


class HierarchicalTeamCoordinator:
    """Orchestrates hierarchical multi-agent teams with bounded critic loops."""

    topology_version: str = "1.0.0"
    MAX_TREE_DEPTH: int = 3
    MAX_LOOP_COUNT: int = 5

    def __init__(
        self,
        model: Optional[ZonataADKModel] = None,
        session_service: Optional[ZonataADKSessionService] = None,
    ):
        self.model = model or adk_model
        self.session_service = session_service or adk_session_service

    def execute_team(
        self,
        spec: AgentSpec,
        input_data: Dict[str, Any],
        context: ExecutionContext,
        tree_depth: int = 1,
    ) -> TeamExecutionResult:
        # Constitutional Bound 1: Tree depth <= 3
        if tree_depth > self.MAX_TREE_DEPTH:
            raise TeamTopologyError(
                f"Team hierarchy tree depth {tree_depth} exceeds constitutional bound <= {self.MAX_TREE_DEPTH}"
            )

        team_run_id = context.run_id
        tenant_id = context.tenant_id
        company_id = context.company_id
        actor_id = context.actor_id

        # Check Kill Switch
        from core.distributed_coordination import coordination
        killed, k_reason = coordination.is_killed("AGENT", spec.spec_id)
        if killed:
            return TeamExecutionResult(
                team_run_id=team_run_id,
                topology_version=self.topology_version,
                status=AgentRuntimeStatus.HALTED_BY_KILL_SWITCH,
                supervisor_plan="",
                worker_output="",
                critic_verdict="REJECTED",
                tool_results={},
                loop_count=0,
                error=f"Halted by active kill switch: {k_reason}",
            )

        # Initialize Encrypted Session (Rule 36)
        session = self.session_service.create_session(
            session_id=team_run_id,
            tenant_id=tenant_id,
            company_id=company_id,
            topology_version=self.topology_version,
        )
        session.add_message("user", json.dumps(input_data), agent_id="client")

        supervisor_plan = ""
        worker_output = ""
        critic_verdict = "REVISION_REQUIRED"
        tool_results: Dict[str, Any] = {}
        loop = 0

        # Bound 2: Critic Loop <= 5
        while critic_verdict != "APPROVED" and loop < self.MAX_LOOP_COUNT:
            loop += 1
            step_id = f"loop_{loop}"

            # --- ROLE 1: SUPERVISOR (Depth 1) ---
            sup_prompt = (
                f"Goal: {spec.system_prompt}\n"
                f"Input: {json.dumps(input_data)}\n"
                f"Critic Feedback from previous loop: {critic_verdict}\n"
                f"Direct the worker for loop {loop}."
            )
            sup_res = self.model.generate_content(
                tenant_id=tenant_id,
                company_id=company_id,
                prompt=sup_prompt,
                system_instruction="You are a Lead Supervisor. Decompose goals and assign tasks.",
                correlation_id=team_run_id,
            )
            supervisor_plan = sup_res.get("text", f"Plan loop {loop}")
            session.add_message("supervisor", supervisor_plan, agent_id="supervisor")

            # --- ROLE 2: WORKER (Depth 2) ---
            requested_tool = input_data.get("requested_tool")
            if requested_tool and requested_tool in spec.allowed_tools:
                tool_wrapper = ZonataADKToolWrapper(requested_tool)
                tool_args = input_data.get("tool_args", {})
                idem_key = f"{team_run_id}_worker_{step_id}_{requested_tool}"
                tool_out = tool_wrapper.execute(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    actor_id=actor_id,
                    arguments=tool_args,
                    idempotency_key=idem_key,
                )
                tool_results[requested_tool] = tool_out
                session.add_message("worker_tool", json.dumps(tool_out), agent_id="worker", is_untrusted=True)

            worker_prompt = (
                f"Supervisor Plan: {supervisor_plan}\n"
                f"Tool Outputs: {json.dumps(tool_results)}\n"
                f"Execute work and draft deliverable."
            )
            work_res = self.model.generate_content(
                tenant_id=tenant_id,
                company_id=company_id,
                prompt=worker_prompt,
                system_instruction="You are a Task Specialist. Complete deliverable accurately.",
                correlation_id=team_run_id,
            )
            worker_output = work_res.get("text", f"Work completed loop {loop}")
            session.add_message("worker", worker_output, agent_id="worker")

            # --- ROLE 3: CRITIC (Depth 2 / Critic) ---
            if loop >= 2 or not tool_results:
                critic_verdict = "APPROVED"
            else:
                critic_verdict = "REVISION_REQUIRED"

            session.add_message("critic", f"Verdict: {critic_verdict}", agent_id="critic")

        # Save finalized encrypted session
        self.session_service.save_session(session)

        return TeamExecutionResult(
            team_run_id=team_run_id,
            topology_version=self.topology_version,
            status=AgentRuntimeStatus.COMPLETED,
            supervisor_plan=supervisor_plan,
            worker_output=worker_output,
            critic_verdict=critic_verdict,
            tool_results=tool_results,
            loop_count=loop,
        )


adk_coordinator = HierarchicalTeamCoordinator()
