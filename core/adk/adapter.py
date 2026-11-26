"""ZONATA Sovereign Core — Google ADK Runtime Adapter.

Implements OpenCode Step 4F (Standing Rules 33, 34, 35, 36, 38):
1. Connects AgentRuntimePort to Google ADK Hierarchical Teams engine:
   - Dispatches versioned team topologies (Rule 38).
   - Coordinates supervisor-worker-critic loops bounded to depth <= 3 and loops <= 5.
   - Routes 100% of LLM calls through ZonataADKModel (LLMGateway) and tools through ZonataADKToolWrapper (ActionGateway) (Rule 34).
   - Manages state in multi-tenant encrypted sessions via ZonataADKSessionService (Rule 36).
2. Reality & Probes:
   - Probes live Google ADK SDK or provides sovereign deterministic simulation under ZONATA_TEST_MODE=1.
   - Fails closed when unconfigured (Truth Rule 1).
"""

from __future__ import annotations
import os
import time
import logging
from typing import Any, Dict, Iterator, Optional, Set

from core.ports.base import PortStatus, ProviderResult
from core.ports.agent_runtime import (
    AgentRuntimePort,
    AgentSpec,
    ExecutionContext,
    AgentChunk,
    AgentResult,
    AgentRuntimeStatus,
)
from core.adk.coordinator import HierarchicalTeamCoordinator, TeamExecutionResult, adk_coordinator

logger = logging.getLogger(__name__)


class GoogleADKRuntimeAdapter(AgentRuntimePort):
    """Sovereign adapter for Google ADK hierarchical multi-agent teams."""

    def __init__(
        self,
        provider_name: str = "google_adk_runtime",
        sandbox: bool = False,
        coordinator: Optional[HierarchicalTeamCoordinator] = None,
    ):
        super().__init__(provider_name=provider_name, sandbox=sandbox)
        self._coordinator = coordinator or adk_coordinator
        self._runs: Dict[str, TeamExecutionResult] = {}
        self._cancelled_runs: Set[str] = set()

    def probe(self) -> ProviderResult:
        """Probes availability of Google ADK environment or sovereign test mode."""
        has_sdk = False
        try:
            import google.adk  # type: ignore
            has_sdk = True
        except ImportError:
            has_sdk = False

        is_test_mode = os.environ.get("ZONATA_TEST_MODE") == "1"

        if is_test_mode or self.sandbox:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.provider_name,
                provider_ref=f"sandbox_google_adk_{int(time.time())}",
                sandbox=True,
                metadata={"target": "google_adk", "mode": "sovereign_team_simulation"},
            )
        if has_sdk:
            # The SDK may be present, but this adapter still runs the local
            # coordinator rather than an ADK runner. Never label that as live.
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.provider_name,
                provider_ref=f"local_adk_coordinator_{int(time.time())}",
                sandbox=True,
                metadata={
                    "target": "google_adk",
                    "live": False,
                    "mode": "local_coordinator_not_adk_runner",
                },
            )
        else:
            return ProviderResult(
                status=PortStatus.NOT_CONFIGURED,
                provider=self.provider_name,
                error="Google ADK SDK not installed and not in sovereign test mode",
            )

    def execute_agent(
        self,
        spec: AgentSpec,
        input_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> AgentResult:
        t0 = time.time()
        probe_res = self.probe()
        if probe_res.status == PortStatus.NOT_CONFIGURED:
            return AgentResult(
                status=PortStatus.NOT_CONFIGURED,
                provider=self.provider_name,
                run_id=context.run_id,
                state=AgentRuntimeStatus.FAILED,
                error="Google ADK runtime is not configured in this environment",
                latency_ms=(time.time() - t0) * 1000.0,
            )

        if context.run_id in self._cancelled_runs:
            return AgentResult(
                status=probe_res.status,
                provider=self.provider_name,
                run_id=context.run_id,
                state=AgentRuntimeStatus.CANCELLED,
                error="Execution cancelled by user",
                latency_ms=(time.time() - t0) * 1000.0,
            )

        # Coordinate team execution
        team_result = self._coordinator.execute_team(spec=spec, input_data=input_data, context=context)
        self._runs[context.run_id] = team_result

        tool_calls: list[Dict[str, Any]] = []
        for t_name, t_val in team_result.tool_results.items():
            tool_calls.append({"tool": t_name, "result": t_val})

        return AgentResult(
            status=probe_res.status,
            provider=self.provider_name,
            sandbox=probe_res.sandbox,
            run_id=context.run_id,
            state=team_result.status,
            output=team_result.to_dict(),
            error=team_result.error,
            tool_calls=tool_calls,
            idempotency_key=context.idempotency_key,
            step_count=team_result.loop_count,
            latency_ms=(time.time() - t0) * 1000.0,
            metadata={"topology_version": team_result.topology_version},
        )

    def stream_agent(
        self,
        spec: AgentSpec,
        input_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> Iterator[AgentChunk]:
        run_res = self.execute_agent(spec, input_data, context)
        yield AgentChunk(
            chunk_type="log",
            content=f"Google ADK team execution started for run {context.run_id}",
            index=0,
        )
        for i, tc in enumerate(run_res.tool_calls):
            yield AgentChunk(chunk_type="tool_call", content=tc, index=i + 1)
        yield AgentChunk(
            chunk_type="token",
            content=str(run_res.output.get("worker_output", "")),
            index=len(run_res.tool_calls) + 1,
        )

    def cancel_agent(self, run_id: str, reason: str = "User requested cancellation") -> bool:
        self._cancelled_runs.add(run_id)
        if run_id in self._runs:
            self._runs[run_id].status = AgentRuntimeStatus.CANCELLED
            self._runs[run_id].error = reason
        return True

    def get_runtime_status(self, run_id: str) -> Dict[str, Any]:
        if run_id in self._runs:
            res = self._runs[run_id]
            return {
                "run_id": run_id,
                "status": res.status.value,
                "loops_completed": res.loop_count,
                "error": res.error,
            }
        return {"run_id": run_id, "status": "NOT_FOUND"}
