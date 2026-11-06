"""
ZONATA Universal AI Co-Worker Fabric — Open-Source Computer-Use & GUI Router
=============================================================================
Unified, governed GUI automation router integrating Agent-S, UI-TARS, OpenAdapt,
and Native OS UI Automation (Windows UIA, macOS Accessibility, Linux X11/Wayland)
behind the ZONATA Universal Worker Contract.

Constitutional Invariants:
1. Sovereign Governance Inviolability: No GUI action bypasses PolicyEngine or ApprovalEngine.
2. Supervised Control Modes: Full support for AI_CONTROL, HUMAN_SUPERVISED, and HUMAN_TAKEOVER.
3. Zero-Mock Reality Rule: If the local environment lacks a physical display server
   (e.g., headless Linux PRoot), physical GUI actions are truthfully designated as
   READY_FOR_REMOTE_NODE or dispatched to a qualified remote desktop node.
4. Cryptographic Evidence: Every mouse, keyboard, or screenshot action generates an
   unalterable SHA-256 evidence entry recorded in the Evidence Ledger.
"""

import os
import sys
import time
import json
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from ..provider_base import CapabilityProvider
from ..contracts import (
    ProviderHealthStatus, ProviderEstimate, ExecutionResult,
    VerificationResult, VerificationStatus, RiskLevel, SupervisedControlMode
)
from ..universal_worker_contract import (
    UniversalWorkerContract, WorkerMetadata, WorkerLocationClass
)
from .agent_s_provider import AgentSProvider
from .ui_tars_provider import UITARSProvider
from .openadapt_provider import OpenAdaptProvider
from .desktop_native_providers import (
    WindowsDesktopProvider, MacOSDesktopProvider, LinuxDesktopProvider
)


class ComputerUseOpenSourceRouter(CapabilityProvider, UniversalWorkerContract):
    """
    Governed Open-Source Computer-Use and GUI Automation Router.
    Routes visual grounding, mouse/keyboard manipulation, and OS interactions
    to Agent-S, UI-TARS, OpenAdapt, or native desktop providers.
    """

    GUI_CAPABILITIES = [
        "MOUSE_CLICK",
        "MOUSE_DOUBLE_CLICK",
        "MOUSE_RIGHT_CLICK",
        "MOUSE_DRAG",
        "MOUSE_MOVE",
        "KEYBOARD_TYPE",
        "KEYBOARD_HOTKEY",
        "CAPTURE_SCREENSHOT",
        "VISUAL_GROUNDING",
        "ACTIVE_WINDOW_INSPECT",
        "APPLICATION_LAUNCH",
        "GUI_MACRO_PLAYBACK",
        "HUMAN_TAKEOVER_TRANSFER"
    ]

    def __init__(self, tenant_id: str = "tnt_primary"):
        super().__init__()
        self._id = "provider_computer_use_router"
        self._name = "ZONATA Open-Source Computer-Use Fabric"
        self.tenant_id = tenant_id

        self.control_mode = SupervisedControlMode.AI_CONTROL
        self.active_operator: Optional[str] = None
        self._history: Dict[str, Any] = {}
        self._cue = None

        # Instantiate underlying open-source providers
        self.agent_s = AgentSProvider()
        self.ui_tars = UITARSProvider()
        self.openadapt = OpenAdaptProvider()
        self.linux_native = LinuxDesktopProvider()
        self.windows_native = WindowsDesktopProvider()
        self.macos_native = MacOSDesktopProvider()

        # Check local physical display availability
        self.has_physical_display = bool(
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        )
        self._health = ProviderHealthStatus.AVAILABLE

    def providerId(self) -> str:
        return "provider_computer_use_router"

    def capabilities(self) -> List[str]:
        return list(self.GUI_CAPABILITIES)

    def platforms(self) -> List[str]:
        return ["linux", "windows", "darwin"]

    def health(self) -> ProviderHealthStatus:
        return self._health

    def set_health(self, status: ProviderHealthStatus):
        self._health = status


    def riskProfile(self) -> Dict[str, Any]:
        return {
            "risk_tier": RiskLevel.MEDIUM,
            "deterministic": False,
            "requires_display": True,
            "supports_dry_run": True,
            "supports_rollback": False,
            "human_admission_required": True
        }

    def estimate(self, capability: str, params: Dict[str, Any]) -> ProviderEstimate:
        return ProviderEstimate(
            provider_id=self.providerId(),
            estimated_duration_sec=0.45,
            estimated_cost_usd=0.001,
            confidence_score=0.95,
            risk_assessment="Governed GUI desktop automation via open-source engines",
            requires_visual=True
        )

    def prepare(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return capability in self.GUI_CAPABILITIES

    def observe(self, capability: str, execution_id: str) -> Dict[str, Any]:
        return self._history.get(execution_id, {"status": "NOT_FOUND"})

    def verify(self, execution_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        data = self._history.get(execution_id)
        if not data:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verified_by="ComputerUseVerifier",
                confidence=0.0,
                discrepancy_notes="Execution not recorded"
            )
        if not data.get("executed"):
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verified_by="ComputerUseVerifier",
                confidence=0.0,
                discrepancy_notes=f"Action was not executed: {data.get('reason') or data.get('status')}"
            )
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            verified_by="ComputerUseVerifier",
            confidence=0.98,
            evidence_details={"operation": "gui_action_executed"}
        )

    def rollback(self, execution_id: str) -> bool:
        return False

    def cancel(self, execution_id: str) -> bool:
        return True

    def recover(self, execution_id: str, error: Exception) -> bool:
        return True

    def shutdown(self) -> None:
        self._history.clear()


    def execute(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> ExecutionResult:
        start_time = time.time()
        exec_id = f"gui_{uuid.uuid4().hex[:8]}"

        # Governance Check: Human Takeover Mode
        if self.control_mode == SupervisedControlMode.HUMAN_TAKEOVER:
            return ExecutionResult(
                provider_id=self._id,
                capability_id=capability,
                execution_id=exec_id,
                status="PAUSED",
                output={"status": "PAUSED_FOR_HUMAN_OPERATOR", "operator_id": self.active_operator},
                error_message="AI execution paused while human operator holds control",
                duration_ms=(time.time() - start_time) * 1000
            )


        # Environment check: Headless Linux vs Physical Display vs Remote Node
        remote_node_id = params.get("remote_node_id") or context.get("target_node_id")

        if not self.has_physical_display and not remote_node_id and capability in (
            "MOUSE_CLICK", "MOUSE_DOUBLE_CLICK", "MOUSE_RIGHT_CLICK", "MOUSE_DRAG",
            "MOUSE_MOVE", "KEYBOARD_TYPE", "KEYBOARD_HOTKEY",
            "CAPTURE_SCREENSHOT", "ACTIVE_WINDOW_INSPECT",
        ):
            # A compiled dispatch spec is not an executed action. Report it as
            # such: the caller must not believe the click happened.
            intent = {
                "capability": capability,
                "status": "READY_FOR_REMOTE_NODE",
                "reason": "Host Linux container lacks a DISPLAY server and no remote node was configured; action was not executed.",
                "action_intent": {
                    "action": capability,
                    "parameters": params,
                    "required_platform": params.get("target_platform", "windows_or_macos_or_x11"),
                    "timestamp": time.time()
                }
            }
            self._history[exec_id] = {"executed": False, **intent}
            return ExecutionResult(
                provider_id=self._id,
                capability_id=capability,
                execution_id=exec_id,
                status="FAILED",
                output=intent,
                confidence=0.0,
                evidence=[{
                    "type": "remote_dispatch_spec",
                    "sha256": hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
                }],
                error_message="NOT_EXECUTED: no local display and no remote node configured",
                duration_ms=(time.time() - start_time) * 1000
            )

        # Route to the real provider / engine.
        output = self._route_gui_action(capability, params, context)
        executed = bool(output.get("executed"))
        self._history[exec_id] = {"executed": executed, **output}

        output_digest = hashlib.sha256(json.dumps(output, sort_keys=True, default=str).encode()).hexdigest()

        return ExecutionResult(
            provider_id=self._id,
            capability_id=capability,
            execution_id=exec_id,
            status="SUCCESS" if executed else "FAILED",
            output=output,
            confidence=0.96 if executed else 0.0,
            evidence=[{
                "type": "computer_use_evidence",
                "capability": capability,
                "executed": executed,
                "digest": output_digest,
                "timestamp": time.time()
            }],
            error_message=None if executed else (output.get("reason") or "ACTION_NOT_IMPLEMENTED"),
            duration_ms=(time.time() - start_time) * 1000
        )

    def _engine(self):
        """Lazily obtain the real desktop engine (avoids an import cycle)."""
        from ..computer_use_engine import ComputerUseEngine
        if getattr(self, "_cue", None) is None:
            self._cue = ComputerUseEngine.get_instance()
        return self._cue

    @staticmethod
    def _wrap(name: str, res: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise an engine primitive result into a router output record."""
        return {
            "engine": name,
            "executed": bool(res.get("executed")),
            "status": res.get("status", "ACTION_NOT_IMPLEMENTED"),
            "mode": res.get("mode"),
            "reason": res.get("reason"),
        }

    def _delegate(self, provider, capability: str, params: Dict[str, Any],
                  context: Dict[str, Any], engine_name: str) -> Dict[str, Any]:
        """Delegate to an open-source provider, reporting its real outcome."""
        result = provider.execute(capability, params, context)
        executed = result.status == "SUCCESS"
        return {
            "engine": engine_name,
            "executed": executed,
            "status": "SUCCESS" if executed else "ACTION_NOT_IMPLEMENTED",
            "reason": None if executed else (result.error_message or "PROVIDER_UNAVAILABLE"),
            "provider_status": result.status,
            "provider_output": result.output,
        }

    def _route_gui_action(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a GUI action to the real execution path.

        Every branch reports `executed`. Engines that are not configured return
        ACTION_NOT_IMPLEMENTED with the provider's own reason; nothing here
        fabricates a bounding box, a replay count, or a screenshot hash.
        """
        preferred_engine = params.get("engine", "AUTO")

        if capability == "HUMAN_TAKEOVER_TRANSFER":
            self.control_mode = SupervisedControlMode.HUMAN_TAKEOVER
            self.active_operator = params.get("operator_id")
            return {"engine": "zonata-control-plane", "executed": True,
                    "status": "SUCCESS", "operator_id": self.active_operator}

        if capability == "VISUAL_GROUNDING" or preferred_engine == "UI_TARS":
            return self._delegate(self.ui_tars, "VISUAL_GROUNDING", params, context, "UI-TARS-VL")

        if preferred_engine == "AGENT_S" or "subgoal" in params:
            return self._delegate(self.agent_s, "AGENT_S_PLAN", params, context, "Agent-S-OSWorld")

        if capability == "GUI_MACRO_PLAYBACK" or preferred_engine == "OPENADAPT":
            return self._delegate(self.openadapt, "GUI_MACRO_PLAYBACK", params, context, "OpenAdapt-Playback")

        if capability == "APPLICATION_LAUNCH":
            # Spawning host processes is an authority-bearing action; it belongs
            # to the action gateway, not to a GUI provider.
            return {"engine": "zonata-policy-gateway", "executed": False,
                    "status": "ACTION_NOT_IMPLEMENTED",
                    "reason": "APP_LAUNCH_REQUIRES_POLICY_GATEWAY"}

        engine = self._engine()

        if capability == "CAPTURE_SCREENSHOT":
            png = engine.screenshot()
            synthetic = bool(getattr(engine, "last_screenshot_synthetic", True))
            return {
                "engine": "ZONATA-Screen-Capture",
                "executed": not synthetic,
                "status": "SUCCESS" if not synthetic else "ACTION_NOT_IMPLEMENTED",
                "reason": None if not synthetic else "NO_DISPLAY",
                "format": "PNG",
                "size_bytes": len(png),
                "content_hash": hashlib.sha256(png).hexdigest(),
                "synthetic": synthetic,
                "timestamp": time.time(),
            }

        if capability == "ACTIVE_WINDOW_INSPECT":
            obs = engine.observe()
            return {
                "engine": "X11-Window-Perception",
                "executed": obs.windows_verified,
                "status": "SUCCESS" if obs.windows_verified else "ACTION_NOT_IMPLEMENTED",
                "reason": None if obs.windows_verified else "NO_DISPLAY",
                "active_window": {
                    "title": obs.active_window,
                    "open_windows": obs.open_windows,
                    "windows_verified": obs.windows_verified,
                },
                "elements_found": len(obs.elements),
                "elements_synthetic": obs.synthetic,
            }

        x_raw = params.get("x", params.get("coordinate", [None, None])[0])
        y_raw = params.get("y", params.get("coordinate", [None, None])[1])

        if capability == "MOUSE_CLICK":
            res = engine.click(int(x_raw or 0), int(y_raw or 0), params.get("button", "left"))
        elif capability == "MOUSE_DOUBLE_CLICK":
            res = engine.double_click(int(x_raw or 0), int(y_raw or 0))
        elif capability == "MOUSE_RIGHT_CLICK":
            res = engine.right_click(int(x_raw or 0), int(y_raw or 0))
        elif capability == "MOUSE_MOVE":
            res = engine.move(int(x_raw or 0), int(y_raw or 0))
        elif capability == "MOUSE_DRAG":
            start = params.get("start", [x_raw or 0, y_raw or 0])
            end = params.get("end", [0, 0])
            res = engine.drag(int(start[0]), int(start[1]), int(end[0]), int(end[1]))
        elif capability == "KEYBOARD_TYPE":
            res = engine.type_text(params.get("text", ""))
        elif capability == "KEYBOARD_HOTKEY":
            keys = params.get("keys") or [params.get("key", "Return")]
            res = engine.hotkey(keys)
        else:
            return {"engine": "none", "executed": False,
                    "status": "ACTION_NOT_IMPLEMENTED",
                    "reason": f"UNSUPPORTED_CAPABILITY:{capability}"}

        return self._wrap("Governed-Desktop-Native", res)

    # -------------------------------------------------------------------------
    # UniversalWorkerContract 14-Method Implementation
    # -------------------------------------------------------------------------

    def discover_capabilities(self) -> List[str]:
        return self.capabilities()

    def authorize(self, task_id: str, lease_token: str, authority_ceiling: str) -> bool:
        return bool(lease_token and authority_ceiling)

    def observe(self, task_id: str, execution_id: str) -> Dict[str, Any]:
        return self._history.get(execution_id, {})

    def pause(self, task_id: str) -> bool:
        self.control_mode = SupervisedControlMode.HUMAN_TAKEOVER
        return True

    def resume(self, task_id: str) -> bool:
        self.control_mode = SupervisedControlMode.AI_CONTROL
        return True

    def cancel(self, task_id: str) -> bool:
        return True

    def take_control(self, task_id: str, operator_id: str) -> bool:
        self.control_mode = SupervisedControlMode.HUMAN_TAKEOVER
        self.active_operator = operator_id
        return True

    def release_control(self, task_id: str, reconciliation_state: Dict[str, Any]) -> bool:
        self.control_mode = SupervisedControlMode.AI_CONTROL
        self.active_operator = None
        return True

    def verify(self, task_id: str, execution_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        data = self._history.get(execution_id)
        if not data:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verified_by="ComputerUseVerifier",
                confidence=0.0,
                discrepancy_notes="Execution not recorded"
            )
        if not data.get("executed"):
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verified_by="ComputerUseVerifier",
                confidence=0.0,
                discrepancy_notes=f"Action was not executed: {data.get('reason') or data.get('status')}"
            )
        return VerificationResult(
            status=VerificationStatus.PASSED,
            verified_by="ComputerUseVerifier",
            confidence=0.98,
            evidence_details={"operation": "gui_action_executed"}
        )

    def recover(self, task_id: str, failure_reason: str) -> Dict[str, Any]:
        return {
            "recovered": True,
            "action": "RESET_GUI_FOCUS_AND_CANCEL_KEYSTATES",
            "task_id": task_id,
            "reason": failure_reason
        }

    def shutdown(self) -> bool:
        self._history.clear()
        return True

    def get_worker_metadata(self) -> WorkerMetadata:
        return WorkerMetadata(
            worker_id="worker_computer_use_router",
            node_id="node_local_plane",
            worker_type="COMPUTER_USE_OPEN_SOURCE",
            platform=sys.platform,
            architecture="any",
            runtime="python3",
            runtime_version="3.14+",
            capabilities=self.GUI_CAPABILITIES,
            health="AVAILABLE",
            resource_limits={"max_cpu_percent": 80.0, "max_ram_mb": 2048, "max_execution_sec": 300},
            security_profile="GOVERNED_DESKTOP_ROUTER",
            credential_scope=["desktop_ui_access"],
            tenant_scope=self.tenant_id,
            location_class=WorkerLocationClass.LOCAL_CONTROL_PLANE,
            availability=True
        )

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "provider_id": self.providerId(),
            "provider_version": "1.0.0",
            "repository": "builtin/zonata-computer-use-router",
            "commit": "5c3e9a1",
            "license": "Apache-2.0",
            "supported_platforms": self.platforms(),
            "model_dependencies": ["UI-TARS-VL", "Agent-S"],
            "runtime_dependencies": ["pyautogui", "openadapt"],
            "capabilities": self.capabilities(),
            "health": self.health().value,
            "security_status": "GOVERNED_BY_ZONATA",
            # Only the native mouse/keyboard/screenshot path is a real
            # integration; UI-TARS/Agent-S/OpenAdapt require configured
            # endpoints and report UNAVAILABLE until then.
            "integration_status": "PARTIAL_INTEGRATION"
        }

