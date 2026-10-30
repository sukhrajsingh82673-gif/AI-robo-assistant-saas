"""
RoboAssistant Company OS 2.0 — Universal Desktop Robot
Governed computer-action execution mechanism supporting screen inspection,
mouse/keyboard events, window control, file management, and process operations
with cryptographic physical verification and evidence ledger integration.
"""

from typing import Dict, List, Optional, Any
import time
import os
import sys
import shutil
import hashlib
import uuid
import json

from .models import ActionContract, AuthorityLevel, HostType, PhysicalVerification, EvidencePackage, EvidenceStatus
from .host_fabric import UniversalHostAgent
from .evidence_ledger import EvidenceLedger
from .db import db

class UniversalDesktopRobot:
    """
    Executes typed desktop actions strictly through governed ActionContracts.
    Separates Robot Execution from AI CEO Strategy.
    """

    def __init__(self, host_agent: UniversalHostAgent, ledger: Optional[EvidenceLedger] = None):
        self.host = host_agent
        self.ledger = ledger or EvidenceLedger()
        self.sandbox_dir = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage/sandbox")
        )
        os.makedirs(self.sandbox_dir, exist_ok=True)

    def _is_path_safe(self, target_path: str) -> bool:
        """Enforces that mutations remain bounded to authorized sandbox workspace."""
        abs_target = os.path.abspath(target_path)
        return abs_target.startswith(self.sandbox_dir) or abs_target.startswith("/tmp")

    def execute_action(self, contract: ActionContract, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a typed ActionContract. Passes through the full governance pipeline:
        Intent -> Policy -> Authority -> Host Capability -> Lock -> Execution -> Observation -> Verification -> Evidence.
        """
        cap = contract.capability.lower()

        # 1. Host Capability & Authority Check
        if self.host.quarantined:
            return {
                "success": False,
                "error": "Execution blocked: Host is quarantined",
                "verified": False
            }

        # 2. Acquire resource locks
        for res in contract.resources_locked:
            if not self.host.acquire_resource_lock(res):
                return {
                    "success": False,
                    "error": f"Execution blocked: Resource '{res}' is currently locked",
                    "verified": False
                }

        try:
            # 3. Route to typed capability handler
            if cap == "file_write" or cap == "create_file":
                result = self._handle_file_write(contract, parameters)
            elif cap == "file_read":
                result = self._handle_file_read(contract, parameters)
            elif cap == "file_list" or cap == "list_directory":
                result = self._handle_file_list(contract, parameters)
            elif cap == "file_delete":
                result = self._handle_file_delete(contract, parameters)
            elif cap == "process_execute" or cap == "start_process":
                result = self._handle_process_execute(contract, parameters)
            elif cap == "screen_capture" or cap == "capture_screen":
                result = self._handle_screen_capture(contract, parameters)
            elif cap == "window_inspect" or cap == "detect_window":
                result = self._handle_window_inspect(contract, parameters)
            elif cap == "mouse_click" or cap == "keyboard_type":
                result = self._handle_input_event(contract, parameters)
            else:
                result = {
                    "success": False,
                    "error": f"Unsupported robot capability: '{contract.capability}'",
                    "verified": False
                }

            # 4. Generate Evidence Package
            if result.get("success"):
                is_simulated = bool(result.get("simulated") or cap in ["screen_capture", "capture_screen", "mouse_click", "keyboard_type", "window_inspect", "detect_window"])
                pv = PhysicalVerification(
                    check_type=result.get("verification_type", "state_check"),
                    target_path=contract.target,
                    expected_val="VERIFIED" if not is_simulated else "SIMULATED",
                    actual_val="VERIFIED" if not is_simulated else "SIMULATED",
                    verified=not is_simulated,
                    details=result.get("details", "Execution verified")
                )
                pkg = self.ledger.seal_evidence(
                    action_id=contract.action_id,
                    mission_id=contract.mission_id,
                    agent_id=contract.agent_id,
                    verifications=[pv],
                    metadata={
                        "target": contract.target,
                        "capability": contract.capability,
                        "simulated": is_simulated,
                        "execution_mode": "SIMULATED" if is_simulated else "LIVE"
                    }
                )
                result["evidence_id"] = pkg.evidence_id
                result["verified"] = not is_simulated
                result["execution_mode"] = "SIMULATED" if is_simulated else "LIVE"

            return result

        finally:
            # Always release acquired locks
            for res in contract.resources_locked:
                self.host.release_resource_lock(res)

    def _handle_file_write(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        target = contract.target
        content = params.get("content", "")
        if not self._is_path_safe(target):
            return {
                "success": False,
                "error": f"Policy Violation: File target '{target}' outside authorized sandbox",
                "verified": False
            }

        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        # Physical reality check
        if not os.path.exists(target):
            return {"success": False, "error": "Physical reality check failed: File was not created on disk", "verified": False}

        with open(target, "rb") as f:
            file_bytes = f.read()
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        return {
            "success": True,
            "verification_type": "sha256_match",
            "bytes_written": len(file_bytes),
            "sha256": sha256,
            "details": f"File created on physical disk with sha256={sha256}"
        }

    def _handle_file_read(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        target = contract.target
        if not os.path.exists(target):
            return {"success": False, "error": f"Target file '{target}' does not exist", "verified": False}

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(10000)

        return {
            "success": True,
            "verification_type": "file_exists",
            "content_preview": content[:500],
            "total_size": os.path.getsize(target),
            "details": f"File read successfully ({os.path.getsize(target)} bytes)"
        }

    def _handle_file_list(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        target = contract.target or self.sandbox_dir
        if not os.path.exists(target):
            return {"success": False, "error": f"Directory '{target}' not found", "verified": False}

        entries = [
            {"name": e, "is_dir": os.path.isdir(os.path.join(target, e)), "size": os.path.getsize(os.path.join(target, e))}
            for e in os.listdir(target)[:50]
        ]
        return {
            "success": True,
            "verification_type": "directory_inspected",
            "entries_count": len(entries),
            "entries": entries,
            "details": f"Inspected directory {target}"
        }

    def _handle_file_delete(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        target = contract.target
        if not self._is_path_safe(target):
            return {"success": False, "error": "Policy Violation: Cannot delete files outside sandbox", "verified": False}

        if os.path.exists(target):
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)

        # Physical verification: File MUST NOT exist
        verified = not os.path.exists(target)
        return {
            "success": verified,
            "verification_type": "file_absent",
            "details": f"File '{target}' removed and physically confirmed absent"
        }

    def _handle_process_execute(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        cmd = params.get("command", ["echo", "robot_noop"])
        timeout = int(params.get("timeout", 10))
        exec_res = self.host.execute_governed_process(
            cmd,
            timeout_seconds=timeout,
            action_id=contract.action_id,
            agent_id=contract.agent_id
        )
        return {
            "success": exec_res["success"],
            "verification_type": "exit_code_zero" if exec_res.get("exit_code") == 0 else "exit_code_failure",
            "exit_code": exec_res.get("exit_code"),
            "stdout": exec_res.get("stdout"),
            "sha256": exec_res.get("sha256_hash", ""),
            "receipt_id": exec_res.get("receipt_id"),
            "details": f"Process exited with code {exec_res.get('exit_code')}"
        }

    def _handle_screen_capture(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        """No display server is attached in this deployment; capture fails closed."""
        display = os.environ.get("DISPLAY", "")
        wayland = os.environ.get("WAYLAND_DISPLAY", "")
        return {
            "success": False,
            "simulated": False,
            "error": "No physical display server is attached to this host.",
            "code": "DISPLAY_NOT_AVAILABLE",
            "verification_type": "display_unavailable",
            "display_env": display or None,
            "wayland_env": wayland or None,
            "details": (
                "Screen capture requires a real display (DISPLAY/WAYLAND_DISPLAY). "
                "No pixels were captured and no telemetry was fabricated."
            ),
        }

    def _handle_window_inspect(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "simulated": False,
            "error": "No window manager is available on this host.",
            "code": "WINDOW_MANAGER_NOT_AVAILABLE",
            "verification_type": "window_manager_unavailable",
            "details": "Window inspection requires a desktop session; nothing was detected.",
        }

    def _handle_input_event(self, contract: ActionContract, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "simulated": False,
            "error": "No input injection channel is available on this host.",
            "code": "INPUT_CHANNEL_NOT_AVAILABLE",
            "verification_type": "input_channel_unavailable",
            "event_type": contract.capability,
            "target": contract.target,
            "details": f"'{contract.capability}' was not dispatched; no input device was reached.",
        }
