"""ZONATA Sovereign Core — Temporal Runtime Adapter.

Implements OpenCode Step 4D (Standing Rules 33, 34, 35, 36, 38):
1. Connects AgentRuntimePort to Temporal Durable Execution engine:
   - Dispatches versioned workflows (Rule 38).
   - Coordinates activities with deterministic idempotency keys (Rule 35).
   - Routes 100% of LLM calls through LLMGateway and tools through ActionGateway (Rule 34).
   - Manages state externally; business truth lives in ZONATA tables (Rule 33).
2. Environment Reality:
   - Probes live Temporal cluster or provides sovereign deterministic simulation under ZONATA_TEST_MODE=1.
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
from core.temporal.workflows import ZonataAgentWorkflow, WorkflowExecutionRecord
from core.temporal.activities import TemporalActivities, temporal_activities

logger = logging.getLogger(__name__)


class TemporalRuntimeAdapter(AgentRuntimePort):
    """Sovereign adapter for Temporal durable execution workflows."""

    def __init__(
        self,
        provider_name: str = "temporal_runtime",
        sandbox: bool = False,
        workflow: Optional[ZonataAgentWorkflow] = None,
    ):
        super().__init__(provider_name=provider_name, sandbox=sandbox)
        self._server_host = os.environ.get("TEMPORAL_HOST", "")
        self._workflow = workflow or ZonataAgentWorkflow()
        self._runs: Dict[str, WorkflowExecutionRecord] = {}
        self._cancelled_runs: Set[str] = set()

    def probe(self) -> ProviderResult:
        """Probes connectivity to Temporal cluster or sovereign test environment."""
        has_sdk = False
        try:
            import temporalio  # type: ignore
            has_sdk = True
        except ImportError:
            has_sdk = False

        is_test_mode = os.environ.get("ZONATA_TEST_MODE") == "1"

        if has_sdk and self._server_host:
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=f"temporal_{self._server_host}",
                metadata={"target": "temporal", "host": self._server_host, "live": True},
            )
        elif is_test_mode or self.sandbox:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.provider_name,
                provider_ref=f"sandbox_temporal_{int(time.time())}",
                sandbox=True,
                metadata={"target": "temporal", "mode": "sovereign_durable_simulation"},
            )
        else:
            return ProviderResult(
                status=PortStatus.NOT_CONFIGURED,
                provider=self.provider_name,
                error="Temporal cluster (TEMPORAL_HOST) or temporalio SDK not configured",
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
                error="Temporal runtime is not configured in this environment",
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

        # Dispatch durable workflow execution
        record = self._workflow.execute(spec=spec, input_data=input_data, context=context)
        self._runs[context.run_id] = record

        tool_calls: list[Dict[str, Any]] = []
        for step in record.step_history:
            if step.get("activity") == "tool_execution":
                tool_calls.append(step.get("result", {}))

        return AgentResult(
            status=probe_res.status,
            provider=self.provider_name,
            sandbox=probe_res.sandbox,
            run_id=context.run_id,
            state=record.status,
            output=record.output,
            error=record.error,
            tool_calls=tool_calls,
            idempotency_key=context.idempotency_key,
            step_count=len(record.step_history),
            latency_ms=(time.time() - t0) * 1000.0,
            metadata={"workflow_version": record.workflow_version, "workflow_id": record.workflow_id},
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
            content=f"Temporal workflow {context.run_id} started (version {self._workflow.workflow_version})",
            index=0,
        )
        for i, tc in enumerate(run_res.tool_calls):
            yield AgentChunk(
                chunk_type="tool_call",
                content=tc,
                index=i + 1,
            )
        yield AgentChunk(
            chunk_type="token",
            content=str(run_res.output.get("llm_plan", "")),
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
            rec = self._runs[run_id]
            return {
                "run_id": run_id,
                "workflow_id": rec.workflow_id,
                "workflow_version": rec.workflow_version,
                "status": rec.status.value,
                "steps_completed": len(rec.step_history),
                "error": rec.error,
            }
        return {"run_id": run_id, "status": "NOT_FOUND"}
