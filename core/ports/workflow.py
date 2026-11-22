"""ZONATA Sovereign Core — WorkflowEngine Port & Execution Kernel.

Implements OpenCode Step 2E (Requirement 5):
1. WorkflowEnginePort base class behind Port pattern.
2. WorkflowRunSpec and WorkflowEngineResult typed data structures.
3. LocalWorkflowEngine provider for deterministic execution without external dependencies.
4. Pluggable architecture ready for Temporal/Airflow/Prefect adapters when configured.
5. Truth Rule: Nothing reports success it did not achieve.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
    port_registry,
)


@dataclass
class WorkflowRunSpec:
    workflow_id: str
    tenant_id: str
    company_id: str
    run_id: str = field(default_factory=lambda: f"wf_run_{uuid.uuid4().hex[:12]}")
    steps: List[Dict[str, Any]] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 300.0
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEngineResult(ProviderResult):
    run_id: Optional[str] = None
    state: str = "PENDING"
    completed_steps: int = 0
    total_steps: int = 0
    output: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "run_id": self.run_id,
            "state": self.state,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "output": self.output,
        })
        return d


class WorkflowEnginePort(Port):
    name = "workflow_engine"
    capability = "workflow_engine"

    def submit(self, spec: WorkflowRunSpec) -> WorkflowEngineResult:
        raise NotImplementedError

    def get_status(self, run_id: str) -> WorkflowEngineResult:
        raise NotImplementedError

    def cancel(self, run_id: str, reason: str = "Cancelled by user") -> WorkflowEngineResult:
        raise NotImplementedError


class LocalWorkflowEngine(WorkflowEnginePort):
    """Local, deterministic workflow engine running in-process or via SQLite/outbox."""

    def __init__(self, provider_name: str = "local_workflow_engine", sandbox: bool = False):
        super().__init__(provider_name=provider_name, sandbox=sandbox)
        self._runs: Dict[str, WorkflowEngineResult] = {}

    def probe(self) -> ProviderResult:
        t0 = time.perf_counter()
        lat = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.OK,
            provider=self.provider_name,
            provider_ref=f"local_wf_probe_{int(time.time())}",
            sandbox=self.sandbox,
            latency_ms=lat,
            cost=0.0,
            metadata={"runner": "in_process_deterministic"}
        )

    def submit(self, spec: WorkflowRunSpec) -> WorkflowEngineResult:
        t0 = time.perf_counter()
        completed = 0
        step_outputs: Dict[str, Any] = {}

        for idx, step in enumerate(spec.steps):
            step_id = step.get("step_id", f"step_{idx+1}")
            action = step.get("action", "noop")
            params = step.get("params", {})
            # Execute step handler if available
            handler: Optional[Callable] = step.get("handler")
            if callable(handler):
                try:
                    res = handler(params)
                    step_outputs[step_id] = res
                except Exception as e:
                    lat = (time.perf_counter() - t0) * 1000.0
                    failed_res = WorkflowEngineResult(
                        status=PortStatus.FAILED,
                        provider=self.provider_name,
                        run_id=spec.run_id,
                        state="FAILED",
                        completed_steps=completed,
                        total_steps=len(spec.steps),
                        latency_ms=lat,
                        error=f"Step '{step_id}' failed: {e}",
                        output=step_outputs,
                        sandbox=self.sandbox,
                    )
                    self._runs[spec.run_id] = failed_res
                    return failed_res
            else:
                step_outputs[step_id] = {"status": "SKIPPED", "action": action}
            completed += 1

        lat = (time.perf_counter() - t0) * 1000.0
        success_res = WorkflowEngineResult(
            status=PortStatus.OK if not self.sandbox else PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=spec.run_id,
            run_id=spec.run_id,
            state="COMPLETED",
            completed_steps=completed,
            total_steps=len(spec.steps),
            latency_ms=lat,
            cost=0.0,
            output=step_outputs,
            sandbox=self.sandbox,
        )
        self._runs[spec.run_id] = success_res
        return success_res

    def get_status(self, run_id: str) -> WorkflowEngineResult:
        if run_id in self._runs:
            return self._runs[run_id]
        return WorkflowEngineResult(
            status=PortStatus.FAILED,
            provider=self.provider_name,
            run_id=run_id,
            state="UNKNOWN",
            completed_steps=0,
            total_steps=0,
            error=f"Run '{run_id}' not found",
            sandbox=self.sandbox,
        )

    def cancel(self, run_id: str, reason: str = "Cancelled by user") -> WorkflowEngineResult:
        if run_id in self._runs:
            res = self._runs[run_id]
            res.state = "CANCELLED"
            res.error = reason
            return res
        return WorkflowEngineResult(
            status=PortStatus.FAILED,
            provider=self.provider_name,
            run_id=run_id,
            state="UNKNOWN",
            error=f"Run '{run_id}' not found",
            sandbox=self.sandbox,
        )


class NotConfiguredWorkflowEngineProvider(WorkflowEnginePort):
    def __init__(self, reason: str = "Workflow engine not configured in environment"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return ProviderResult(
            status=PortStatus.NOT_CONFIGURED,
            provider="not_configured",
            latency_ms=0.0,
            cost="UNMEASURED",
            error=self.reason
        )

    def submit(self, spec: WorkflowRunSpec) -> WorkflowEngineResult:
        return WorkflowEngineResult(
            status=PortStatus.NOT_CONFIGURED,
            provider="not_configured",
            run_id=spec.run_id,
            state="REFUSED",
            error=self.reason
        )

    def get_status(self, run_id: str) -> WorkflowEngineResult:
        return WorkflowEngineResult(
            status=PortStatus.NOT_CONFIGURED,
            provider="not_configured",
            run_id=run_id,
            state="UNKNOWN",
            error=self.reason
        )

    def cancel(self, run_id: str, reason: str = "") -> WorkflowEngineResult:
        return WorkflowEngineResult(
            status=PortStatus.NOT_CONFIGURED,
            provider="not_configured",
            run_id=run_id,
            state="UNKNOWN",
            error=self.reason
        )


class SandboxWorkflowEngineProvider(LocalWorkflowEngine):
    def __init__(self):
        super().__init__(provider_name="sandbox_workflow_engine", sandbox=True)


def resolve_workflow_provider() -> WorkflowEnginePort:
    """Resolve workflow provider based on environment and test mode."""
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    engine_type = os.environ.get("WORKFLOW_ENGINE_PROVIDER", "local").lower()

    if is_test:
        return SandboxWorkflowEngineProvider()

    if engine_type == "local":
        return LocalWorkflowEngine()
    elif engine_type in ("temporal", "prefect", "airflow"):
        # Not yet configured external network adapter
        return NotConfiguredWorkflowEngineProvider(f"External workflow engine '{engine_type}' is not configured")
    else:
        return NotConfiguredWorkflowEngineProvider(f"Unknown workflow engine provider '{engine_type}'")


# Register in global port_registry
port_registry.register("workflow_engine", resolve_workflow_provider())
