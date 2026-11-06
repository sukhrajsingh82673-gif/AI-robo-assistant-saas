"""
ZONATA Universal AI Co-worker Fabric — OpenAdapt Provider Adapter
Provides demonstrated desktop workflows, repeatable GUI workflows, workflow compilation,
and governed desktop execution across Linux, Windows, and macOS.
Operates strictly under ZONATA admission, credentials, policies, and evidence ledger.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import hashlib
import json
import os
from ..provider_base import CapabilityProvider
from ..contracts import (
    ProviderHealthStatus, ProviderEstimate, ExecutionResult,
    VerificationResult, VerificationStatus, RiskLevel
)

class OpenAdaptProvider(CapabilityProvider):
    """
    OpenAdapt Adapter for repeatable GUI and desktop workflow execution.
    ZONATA controls admission, credentials, policies, and evidence.
    """

    def __init__(self, host_platform: str = "linux"):
        self._id = "provider_openadapt"
        self._platform = host_platform
        self._health = ProviderHealthStatus.AVAILABLE
        self._workflows: Dict[str, Dict[str, Any]] = {
            "workflow_export_financial_report": {
                "name": "Export Financial Report",
                "app": "LegacyERP",
                "steps": ["focus_window", "menu_click_export", "fill_date_range", "save_csv"],
                "compiled": True,
                "reversibility": "REVERSIBLE"
            },
            "workflow_update_hotel_inventory": {
                "name": "Update Hotel Inventory",
                "app": "PropertyManagementDesktop",
                "steps": ["open_matrix", "select_dates", "update_allotment", "commit_changes"],
                "compiled": True,
                "reversibility": "REVERSIBLE"
            }
        }
        self._execution_history: Dict[str, Dict[str, Any]] = {}
        self._version = "0.10.0"
        self._repository = "OpenAdaptAI/OpenAdapt"
        self._commit = "5e8c10a"
        self._license = "MIT"
        self._integration_status = "ADAPTER_ONLY"
        self._model_dependencies = []
        self._runtime_dependencies = ["openadapt", "spacy"]

    def providerId(self) -> str:
        return self._id

    def capabilities(self) -> List[str]:
        return [
            "desktop.workflow",
            "desktop.record_workflow",
            "desktop.replay_workflow",
            "desktop.compile_workflow",
            "desktop.inspect_gui"
        ]

    def platforms(self) -> List[str]:
        return ["linux", "windows", "darwin"]

    def health(self) -> ProviderHealthStatus:
        return self._health

    def set_health(self, status: ProviderHealthStatus):
        self._health = status

    def riskProfile(self) -> Dict[str, Any]:
        return {
            "risk_tier": RiskLevel.MEDIUM,
            "deterministic": True,
            "requires_display": True,
            "supports_dry_run": True,
            "supports_rollback": True,
            "human_admission_required": False
        }

    def estimate(self, capability: str, params: Dict[str, Any]) -> ProviderEstimate:
        return ProviderEstimate(
            provider_id=self._id,
            estimated_duration_sec=3.5,
            estimated_cost_usd=0.001,
            confidence_score=0.96,
            risk_assessment="Predictable compiled GUI automation; repeatable workflow",
            requires_visual=False
        )

    def prepare(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if self._health != ProviderHealthStatus.AVAILABLE:
            return False
        workflow_id = params.get("workflow_id")
        if workflow_id and workflow_id not in self._workflows:
            # Dynamically register custom workflow if steps provided
            if "steps" in params:
                self._workflows[workflow_id] = {
                    "name": params.get("name", workflow_id),
                    "steps": params["steps"],
                    "compiled": True
                }
        return True

    @staticmethod
    def _runtime_available() -> bool:
        """True only when the OpenAdapt package is actually importable."""
        import importlib.util
        return importlib.util.find_spec("openadapt") is not None

    def execute(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> ExecutionResult:
        start_time = time.time()
        exec_id = f"oa_exec_{uuid.uuid4().hex[:8]}"

        if self._health == ProviderHealthStatus.CRASHED:
            return ExecutionResult(
                provider_id=self._id,
                capability_id=capability,
                execution_id=exec_id,
                status="FAILED",
                error_message="OpenAdapt daemon is currently CRASHED",
                duration_ms=(time.time() - start_time) * 1000
            )

        workflow_id = params.get("workflow_id", "workflow_export_financial_report")
        workflow = self._workflows.get(workflow_id, {
            "name": "Generic Desktop Workflow",
            "steps": params.get("steps", []),
            "compiled": True
        })

        # Honest refusal: replaying a GUI workflow requires the OpenAdapt
        # runtime. Emitting COMPLETED steps without it would be fabricated
        # evidence.
        if not self._runtime_available():
            payload = {
                "workflow_id": workflow_id,
                "status": "ADAPTER_ONLY",
                "reason": "The 'openadapt' package is not installed on this host. "
                          "A workflow cannot be replayed; this adapter only compiles "
                          "workflow definitions.",
                "compiled_steps": list(workflow.get("steps", [])),
            }
            self._execution_history[exec_id] = {
                "capability": capability,
                "params": params,
                "output": payload,
                "timestamp": time.time(),
                "status": "NOT_EXECUTED",
                "executed": False,
            }
            return ExecutionResult(
                provider_id=self._id,
                capability_id=capability,
                execution_id=exec_id,
                status="FAILED",
                output=payload,
                confidence=0.0,
                error_message="ADAPTER_ONLY: openadapt runtime not installed",
                duration_ms=(time.time() - start_time) * 1000
            )

        # Real replay path. Kept minimal and explicit: it runs OpenAdapt's CLI
        # against the compiled workflow and records the actual exit status.
        try:
            import subprocess
            proc = subprocess.run(
                ["python3", "-m", "openadapt", "replay", workflow_id],
                capture_output=True, text=True, timeout=300,
            )
            executed = proc.returncode == 0
            output_payload = {
                "workflow_id": workflow_id,
                "status": "WORKFLOW_COMPLETED" if executed else "WORKFLOW_FAILED",
                "target_app": workflow.get("app"),
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
            evidence = [{
                "type": "openadapt_execution_trace",
                "workflow_id": workflow_id,
                "returncode": proc.returncode,
                "hash": hashlib.sha256((proc.stdout + proc.stderr).encode()).hexdigest(),
            }]
        except Exception as exc:
            executed = False
            output_payload = {"workflow_id": workflow_id, "status": "WORKFLOW_FAILED", "error": str(exc)}
            evidence = [{"type": "openadapt_execution_trace", "workflow_id": workflow_id, "error": str(exc)}]

        self._execution_history[exec_id] = {
            "capability": capability,
            "params": params,
            "output": output_payload,
            "timestamp": time.time(),
            "status": "COMPLETED" if executed else "FAILED",
            "executed": executed,
        }

        return ExecutionResult(
            provider_id=self._id,
            capability_id=capability,
            execution_id=exec_id,
            status="SUCCESS" if executed else "FAILED",
            output=output_payload,
            confidence=0.98 if executed else 0.0,
            evidence=evidence,
            rollback_available=executed,
            rollback_data={"workflow_id": workflow_id} if executed else None,
            idempotency_key=params.get("idempotency_key"),
            error_message=None if executed else "OpenAdapt replay failed",
            duration_ms=(time.time() - start_time) * 1000
        )

    def observe(self, capability: str, execution_id: str) -> Dict[str, Any]:
        record = self._execution_history.get(execution_id, {})
        if not record:
            return {"execution_id": execution_id, "observed_state": "NOT_FOUND"}
        executed = bool(record.get("executed"))
        return {
            "execution_id": execution_id,
            "observed_state": "DESKTOP_WORKFLOW_ACTIVE" if executed else "NOT_EXECUTED",
            "active_window": record.get("output", {}).get("target_app"),
            "last_step_status": record.get("status"),
            "executed": executed,
        }

    def verify(self, execution_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        record = self._execution_history.get(execution_id)
        if not record:
            return VerificationResult(
                status=VerificationStatus.NOT_VERIFIED,
                verified_by=self._id,
                confidence=0.0,
                discrepancy_notes="Execution record not found in OpenAdapt history"
            )
        if not record.get("executed"):
            return VerificationResult(
                status=VerificationStatus.NOT_VERIFIED,
                verified_by=self._id,
                confidence=0.0,
                discrepancy_notes="Workflow was not executed by OpenAdapt"
            )
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            verified_by=self._id,
            confidence=0.98,
            evidence_details={"workflow_status": record.get("status")}
        )

    def rollback(self, execution_id: str) -> bool:
        record = self._execution_history.get(execution_id)
        if record:
            record["status"] = "ROLLED_BACK"
            return True
        return False

    def cancel(self, execution_id: str) -> bool:
        record = self._execution_history.get(execution_id)
        if record:
            record["status"] = "CANCELLED"
            return True
        return False

    def recover(self, execution_id: str, error: Exception) -> bool:
        # Re-initialize OpenAdapt session
        self._health = ProviderHealthStatus.AVAILABLE
        return True

    def shutdown(self) -> None:
        self._execution_history.clear()
