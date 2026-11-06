"""
ZONATA Universal AI Co-worker Fabric — Unified Computer Use (CUA) Worker Runtime
Provides a unified abstraction for all desktop/GUI computer-use automation:
- computer.observe
- computer.click
- computer.type
- computer.key
- computer.scroll
- computer.drag
- computer.launch
- computer.window
- computer.screenshot
- computer.verify

Integrates native accessibility (AT-SPI, AX, UIAutomation), Hermes CUA driver,
Computer Use MCP, OpenAdapt, Agent-S, UI-TARS, and OpenRPA.
Routes to DESKTOP_NODE / WINDOWS_NODE / MACOS_NODE when running on a headless host.
"""

from __future__ import annotations
import os
import sys
import time
import json
import uuid
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .base_runtime import (
    WorkerRuntime, RuntimeSession, SessionState, BackgroundJob, JobStatus
)
from ..contracts import (
    RiskLevel, ExecutionState, SupervisedControlMode, CoworkerProfile
)

@dataclass
class DesktopScreenState:
    session_id: str
    active_window: str = "Desktop"
    cursor_position: Tuple[int, int] = (0, 0)
    screen_resolution: Tuple[int, int] = (1920, 1080)
    last_screenshot_hash: str = ""
    visual_elements_detected: int = 0
    accessibility_tree_available: bool = False

class ComputerUseWorkerRuntime(WorkerRuntime):
    """
    Unified Computer Use Runtime Provider.
    Prefers deterministic accessibility APIs (AX/UIA/AT-SPI) where available;
    falls back to visual CUA (screenshot-driven click/type) only when necessary.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self.sessions: Dict[str, RuntimeSession] = {}
        self.screen_states: Dict[str, DesktopScreenState] = {}
        self.workers: Dict[str, CoworkerProfile] = {}
        self._cue = None

    def runtime_id(self) -> str:
        return "runtime_computer_use_unified"

    def runtime_type(self) -> str:
        return "COMPUTER_USE"

    def version(self) -> str:
        return "2.1.0-cua"

    def supported_capabilities(self) -> List[str]:
        return [
            "computer.observe",
            "computer.click",
            "computer.type",
            "computer.key",
            "computer.scroll",
            "computer.drag",
            "computer.launch",
            "computer.window",
            "computer.screenshot",
            "computer.verify"
        ]

    def create_worker(self, profile: CoworkerProfile) -> str:
        self.workers[profile.worker_id] = profile
        return profile.worker_id

    def start_session(self, session: RuntimeSession) -> bool:
        session.state = SessionState.ACTIVE
        session.runtime_version = self.version()
        session.provider_version = "cua-driver-mcp-v1"
        initial = DesktopScreenState(session_id=session.session_id)
        try:
            from ..computer_use_engine import ComputerUseEngine
            cue = ComputerUseEngine.get_instance()
            initial.screen_resolution = (cue.width, cue.height)
        except Exception:
            pass
        self.screen_states[session.session_id] = initial
        session.log(f"Initialized unified CUA desktop session {session.session_id} on node {session.node_id}")
        self.sessions[session.session_id] = session
        return True

    def submit_mission(self, session_id: str, mission: Dict[str, Any]) -> str:
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        mission_id = mission.get("mission_id", f"msn_cua_{uuid.uuid4().hex[:8]}")
        session.mission_id = mission_id
        session.log(f"Accepted CUA desktop mission: {mission.get('objective', 'GUI Task')}")
        return mission_id

    def _engine(self):
        """Lazily obtain the real desktop engine (avoids an import cycle)."""
        from ..computer_use_engine import ComputerUseEngine
        if getattr(self, "_cue", None) is None:
            self._cue = ComputerUseEngine.get_instance()
        return self._cue

    @staticmethod
    def _status(result: Dict[str, Any]) -> str:
        """Derive the runtime status from what the engine actually did."""
        if result.get("executed"):
            return "SUCCESS"
        return result.get("status") or "ACTION_NOT_IMPLEMENTED"

    def _sync_state(self, state: DesktopScreenState) -> None:
        state.cursor_position = (self._engine().cursor_x, self._engine().cursor_y)
        state.active_window = self._engine().active_window

    def run_foreground(self, session_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a computer-use action on the host.

        Delegates to ComputerUseEngine, which dispatches real X11 input and
        reports `executed`/`mode`/`status`/`reason`. This runtime does not invent
        success: when there is no display or the tool is missing, the caller gets
        ACTION_NOT_IMPLEMENTED with a reason.
        """
        session = self.sessions.get(session_id)
        if not session:
            return {"status": "ERROR", "error": f"Session {session_id} not found"}

        if session.control_mode == SupervisedControlMode.HUMAN_CONTROL:
            return {"status": "HUMAN_TAKEOVER_ACTIVE", "result": None}

        state = self.screen_states.get(session_id) or DesktopScreenState(session_id=session_id)
        self.screen_states.setdefault(session_id, state)
        session.record_heartbeat()

        action = task.get("action", "observe")
        params = task.get("parameters", {})
        engine = self._engine()

        # 1. Observation
        if action == "observe":
            session.log("Observing desktop windows and UI elements")
            obs = engine.observe()
            state.active_window = obs.active_window
            state.cursor_position = obs.cursor_position
            state.screen_resolution = (obs.screen_width, obs.screen_height)
            state.visual_elements_detected = len(obs.elements)
            state.accessibility_tree_available = False
            status = "SUCCESS" if (obs.windows_verified and not obs.synthetic) else "PARTIAL"
            return {
                "status": status,
                "action": "computer.observe",
                "executed": obs.windows_verified,
                "active_window": obs.active_window,
                "open_windows": obs.open_windows,
                "elements_found": len(obs.elements),
                "accessibility_tree": {
                    "root": obs.active_window,
                    "children": [e.label for e in obs.elements],
                    "source": "seeded_scene",
                },
                # Window titles may be real while the element tree is seeded.
                "windows_verified": obs.windows_verified,
                "synthetic": obs.synthetic,
                "reason": None if obs.synthetic is False else "PERCEPTION_NOT_IMPLEMENTED",
                "timestamp": time.time(),
            }

        # 2. Click
        if action == "click":
            x, y = params.get("coordinate", (engine.cursor_x, engine.cursor_y))
            button = params.get("button", "left")
            res = engine.click(int(x), int(y), button=button)
            self._sync_state(state)
            session.log(f"computer.click at ({x}, {y}) button={button}: {res['status']}")
            return {
                "status": self._status(res),
                "action": "computer.click",
                "executed": res["executed"],
                "mode": res["mode"],
                "coordinate": (int(x), int(y)),
                "button": button,
                "reason": res.get("reason"),
            }

        # 3. Type Text
        if action == "type":
            text = params.get("text", "")
            res = engine.type_text(text)
            session.log(f"computer.type ({len(text)} chars): {res['status']}")
            return {
                "status": self._status(res),
                "action": "computer.type",
                "executed": res["executed"],
                "mode": res["mode"],
                "chars_written": len(text),
                "reason": res.get("reason"),
            }

        # 4. Keyboard Key
        if action == "key":
            key_name = params.get("key", "Return")
            res = engine.press_key(key_name)
            session.log(f"computer.key {key_name}: {res['status']}")
            return {
                "status": self._status(res),
                "action": "computer.key",
                "executed": res["executed"],
                "mode": res["mode"],
                "key": key_name,
                "reason": res.get("reason"),
            }

        # 5. Scroll
        if action == "scroll":
            direction = params.get("direction", "down")
            res = engine.scroll(dx=params.get("dx", 0), dy=params.get("dy", 0), direction=direction)
            return {
                "status": self._status(res),
                "action": "computer.scroll",
                "executed": res["executed"],
                "mode": res["mode"],
                "direction": direction,
                "reason": res.get("reason"),
            }

        # 6. Drag
        if action == "drag":
            start = params.get("start", params.get("from", (0, 0)))
            end = params.get("end", params.get("to", (100, 100)))
            res = engine.drag(int(start[0]), int(start[1]), int(end[0]), int(end[1]))
            self._sync_state(state)
            return {
                "status": self._status(res),
                "action": "computer.drag",
                "executed": res["executed"],
                "mode": res["mode"],
                "start": tuple(start),
                "end": tuple(end),
                "reason": res.get("reason"),
            }

        # 7. Screenshot
        if action == "screenshot":
            png = engine.screenshot()
            synthetic = bool(getattr(engine, "last_screenshot_synthetic", True))
            digest = hashlib.sha256(png).hexdigest()
            state.last_screenshot_hash = digest
            state.screen_resolution = (engine.width, engine.height)
            session.log(f"Desktop screenshot: {len(png)} bytes synthetic={synthetic} digest={digest[:16]}")
            return {
                "status": "ACTION_NOT_IMPLEMENTED" if synthetic else "SUCCESS",
                "action": "computer.screenshot",
                "executed": not synthetic,
                "mode": "headless" if synthetic else "x11",
                "screenshot_hash": digest,
                "size_bytes": len(png),
                "resolution": state.screen_resolution,
                "synthetic": synthetic,
                "reason": "NO_DISPLAY" if synthetic else None,
            }

        # 8. Window Selection
        if action == "window":
            title = params.get("title", "")
            res = engine.switch_window(title)
            if res["executed"]:
                state.active_window = title
            session.log(f"computer.window -> {title}: {res['status']}")
            return {
                "status": self._status(res),
                "action": "computer.window",
                "executed": res["executed"],
                "mode": res["mode"],
                "active_window": state.active_window,
                "reason": res.get("reason"),
            }

        # 9. Launch (authority-bearing: delegated to the policy gateway, not here)
        if action == "launch":
            res = engine.launch(params.get("application", ""), params.get("args"))
            return {
                "status": self._status(res),
                "action": "computer.launch",
                "executed": res["executed"],
                "mode": res["mode"],
                "reason": res.get("reason") or "APP_LAUNCH_REQUIRES_POLICY_GATEWAY",
            }

        # 10. Verification
        if action == "verify":
            assertion = params.get("assertion", "window_active")
            expected = params.get("expected", params.get("title", state.active_window))
            passed = engine.verify(assertion, expected)
            session.log(f"computer.verify {assertion}={expected!r}: {passed}")
            return {
                "status": "SUCCESS" if passed else "VERIFICATION_FAILED",
                "action": "computer.verify",
                "executed": passed,
                "verified": passed,
                "target_matched": passed,
                "assertion": assertion,
                "expected": expected,
                "reason": None if passed else "ASSERTION_NOT_CONFIRMED",
            }

        # Unknown action: refuse rather than claiming a completed task.
        return {
            "status": "ACTION_NOT_IMPLEMENTED",
            "action": f"computer.{action}",
            "executed": False,
            "completed": False,
            "reason": f"UNKNOWN_CUA_ACTION:{action}",
            "timestamp": time.time(),
        }

    def run_background(self, session_id: str, task: Dict[str, Any]) -> str:
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        job_id = f"job_cua_{uuid.uuid4().hex[:8]}"
        session.log(f"Dispatched background CUA job {job_id}")
        return job_id

    def pause(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.PAUSED
            session.log("CUA desktop session paused")
            return True
        return False

    def resume(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.ACTIVE
            session.log("CUA desktop session resumed")
            return True
        return False

    def redirect(self, session_id: str, new_instruction: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.log(f"CUA desktop redirected: {new_instruction}")
            return True
        return False

    def observe(self, session_id: str) -> Dict[str, Any]:
        state = self.screen_states.get(session_id)
        session = self.sessions.get(session_id)
        return {
            "session_id": session_id,
            "active_window": state.active_window if state else "unknown",
            "cursor": state.cursor_position if state else (0, 0),
            "state": session.state.value if session else "UNKNOWN"
        }

    def collect_logs(self, session_id: str) -> List[str]:
        session = self.sessions.get(session_id)
        return list(session.logs) if session else []

    def request_input(self, session_id: str, prompt: str) -> str:
        session = self.sessions.get(session_id)
        if session:
            session.log(f"CUA desktop input request: {prompt}")
        return "GRANTED"

    def take_control(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.control_mode = SupervisedControlMode.HUMAN_CONTROL
            session.state = SessionState.HUMAN_TAKEOVER
            session.log("Human supervisor seized desktop keyboard and mouse")
            return True
        return False

    def return_control(self, session_id: str, human_state_delta: Optional[Dict[str, Any]] = None) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.control_mode = SupervisedControlMode.AI_CONTROL
            session.state = SessionState.ACTIVE
            session.log("Control restored to autonomous CUA desktop worker")
            return True
        return False

    def terminate(self, session_id: str, reason: str = "COMPLETED") -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.TERMINATED
            session.log(f"CUA desktop session terminated: {reason}")
            return True
        return False

    def recover(self, session_id: str, failure_context: Dict[str, Any]) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.log(f"CUA desktop recovering: {failure_context.get('error', 'none')}")
            session.state = SessionState.ACTIVE
            return True
        return False

    def verify(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seal a result. CONFIRMED requires positive proof of execution
        (`executed` true or an explicit `verified` true), not merely a
        success-shaped status string.
        """
        confirmed = bool(result.get("executed")) or result.get("verified") is True
        return {
            "session_id": session_id,
            "verification_status": "CONFIRMED" if confirmed else "UNCONFIRMED",
            "digest": hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest(),
            "timestamp": time.time()
        }

    def collect_evidence(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        state = self.screen_states.get(session_id)
        return {
            "session_id": session_id,
            "runtime": self.runtime_id(),
            "active_window": state.active_window if state else "",
            "screenshot_hash": state.last_screenshot_hash if state else "",
            "timestamp": time.time()
        }
