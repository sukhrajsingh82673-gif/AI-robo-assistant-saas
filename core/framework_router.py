"""ZONATA Sovereign Core — Framework Router & Decision D4-1 Qualifier.

Implements OpenCode Step 4E (Decision D4-1 / ADR 0009):
Defines and enforces the runtime division of labor:
1. TEMPORAL: Long-running durable business processes (duration > hours/days, sleep/timer durability, sagas, asynchronous human-in-the-loop).
2. LANGGRAPH: Short-cycle iterative agents (planning loops, self-correction, critic cycles, researcher/writer with depth <= 5).
3. GOOGLE_ADK: Hierarchical multi-agent teams (supervisor-worker-critic squads, team topologies).
4. LOCAL: Fast, lightweight in-process sovereign utility agents.

Validates that task specifications conform to architectural limits and fails closed on invalid routing.
"""

from __future__ import annotations
from enum import Enum
import logging
from typing import Any, Dict, Optional

from core.ports.agent_runtime import AgentSpec

logger = logging.getLogger(__name__)


class RuntimeTarget(str, Enum):
    LOCAL = "LOCAL"
    LANGGRAPH = "LANGGRAPH"
    TEMPORAL = "TEMPORAL"
    GOOGLE_ADK = "GOOGLE_ADK"


class RoutingValidationError(ValueError):
    """Raised when a task specification requests an incompatible or disallowed runtime target."""
    pass


class FrameworkRouter:
    """Evaluates agent specifications and workload requirements to assign appropriate runtime targets."""

    @staticmethod
    def resolve_target(spec: AgentSpec, input_data: Optional[Dict[str, Any]] = None) -> RuntimeTarget:
        """Determines the appropriate runtime target adhering strictly to Decision D4-1."""
        input_data = input_data or {}
        workflow_type = (spec.workflow_type or "sequential").lower()
        timeout_seconds = spec.limits.get("timeout_seconds", 300)
        is_durable = input_data.get("is_durable", False) or input_data.get("requires_durability", False)
        requires_team = input_data.get("requires_team", False) or "team_topology" in spec.metadata

        # Explicit target request in spec metadata
        explicit_target = spec.metadata.get("target_runtime")
        if explicit_target:
            try:
                target_enum = RuntimeTarget(str(explicit_target).upper())
                # Validate explicit target against workload bounds
                FrameworkRouter.validate_assignment(target_enum, spec, input_data)
                return target_enum
            except ValueError:
                raise RoutingValidationError(f"Unknown target runtime: '{explicit_target}'")

        # Decision D4-1 Matrix:
        # 1. Hierarchical Squads / Multi-Agent Teams -> GOOGLE_ADK
        if workflow_type in ("hierarchical", "team", "supervisor_worker") or requires_team:
            return RuntimeTarget.GOOGLE_ADK

        # 2. Multi-day / High-Timeout / Durable Business Process -> TEMPORAL
        if timeout_seconds > 3600 or is_durable or workflow_type in ("durable", "saga", "long_running"):
            return RuntimeTarget.TEMPORAL

        # 3. Iterative Cyclic Feedback / Critic Loops -> LANGGRAPH
        if workflow_type in ("cyclic", "loop", "critic_review", "iterative"):
            return RuntimeTarget.LANGGRAPH

        # 4. Standard sequential in-process task -> LOCAL
        return RuntimeTarget.LOCAL

    @staticmethod
    def validate_assignment(
        target: RuntimeTarget,
        spec: AgentSpec,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Validates that a designated runtime target meets constitutional architectural constraints."""
        input_data = input_data or {}
        workflow_type = (spec.workflow_type or "").lower()
        timeout_sec = spec.limits.get("timeout_seconds", 300)

        # Rule: Multi-day (>1 hour) processes MUST NOT run in ephemeral LOCAL or LANGGRAPH memory
        if timeout_sec > 3600 and target in (RuntimeTarget.LOCAL, RuntimeTarget.LANGGRAPH):
            raise RoutingValidationError(
                f"Workload with timeout {timeout_sec}s requires durable execution; cannot route to ephemeral {target.value}"
            )

        # Rule: LangGraph loops are bounded (max_steps <= 10)
        max_steps = spec.limits.get("max_steps", 5)
        if target == RuntimeTarget.LANGGRAPH and max_steps > 10:
            raise RoutingValidationError(
                f"LangGraph cyclic runtime is bounded to <= 10 iterations; requested {max_steps}"
            )

        # Rule: Single-turn fast tasks should not pay heavy team orchestration overhead
        if target == RuntimeTarget.GOOGLE_ADK and workflow_type == "sequential" and not input_data.get("requires_team"):
            raise RoutingValidationError(
                "Simple sequential task cannot be assigned to hierarchical GOOGLE_ADK without team topology"
            )


framework_router = FrameworkRouter()
