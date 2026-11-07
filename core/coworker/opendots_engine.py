"""
ZONATA Autonomous Coworker 3.0 — OpenDots Virtual Desktop & Grounding Engine
Provides honest, open-source computer-use automation:
  - Transparent labeling: never claims proprietary OpenAI Dots equivalence.
  - Real X11 virtual desktop observation via scrot, xdotool, and wmctrl.
  - Perceptual screenshot SHA-256 hashing to verify UI state transitions.
  - Window tree identification and interactive element coordinate targeting.
  - Always-on scheduled GUI automation tasks.
"""

from __future__ import annotations
import os
import time
import json
import uuid
import hashlib
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .contracts_v3 import VisualObservation, ScheduledTaskEntry
from .adapters.opendots_adapter import OpenDotsAdapter, GroundingTarget


class OpenDotsEngine:
    """
    Open-source visual perception and desktop automation engine.
    Controls X11 display environments, captures real framebuffers, and tracks window states.
    """

    def __init__(
        self,
        display: str = ":99",
        width: int = 1920,
        height: int = 1080
    ):
        self.display = display
        self.width = width
        self.height = height
        self.adapter = OpenDotsAdapter(screen_width=width, screen_height=height)
        self.scheduled_tasks: Dict[str, ScheduledTaskEntry] = {}
        self._ensure_display_env()

    def _ensure_display_env(self):
        """Sets DISPLAY environment variable if not present."""
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = self.display

    def check_x11_available(self) -> bool:
        """Verifies if the X11 display server is reachable."""
        try:
            res = subprocess.run(["xdpyinfo"], capture_output=True, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    def capture_screen_observation(self) -> VisualObservation:
        """
        Captures real visual observation from the display framebuffer.
        Computes SHA-256 screenshot hash to detect UI state mutations.
        """
        tmp_screenshot = f"/tmp/opendots_screen_{uuid.uuid4().hex[:6]}.png"
        screenshot_bytes = b""
        sha256_hash = ""
        perception_mode = "REAL_VIRTUAL_X11"

        try:
            # Capture using scrot
            res = subprocess.run(["scrot", "-z", tmp_screenshot], capture_output=True, timeout=5)
            if res.returncode == 0 and os.path.exists(tmp_screenshot):
                with open(tmp_screenshot, "rb") as f:
                    screenshot_bytes = f.read()
                sha256_hash = hashlib.sha256(screenshot_bytes).hexdigest()
                os.remove(tmp_screenshot)
            else:
                # Scrot unavailable or failed: generate fallback frame buffer
                perception_mode = "HEADLESS_SIMULATED"
                screenshot_bytes = b"FALLBACK_SCREEN_FRAMEBUFFER"
                sha256_hash = hashlib.sha256(screenshot_bytes).hexdigest()
        except Exception:
            perception_mode = "HEADLESS_SIMULATED"
            screenshot_bytes = b"FALLBACK_SCREEN_FRAMEBUFFER"
            sha256_hash = hashlib.sha256(screenshot_bytes).hexdigest()

        # Identify active window title
        active_title = self.get_active_window_title()

        return VisualObservation(
            display=self.display,
            width=self.width,
            height=self.height,
            screenshot_bytes=screenshot_bytes,
            screenshot_sha256=sha256_hash,
            active_window_title=active_title,
            detected_elements_count=len(self.adapter.engine.perception.detect_elements()),
            perception_mode=perception_mode,
            timestamp=time.time()
        )

    def get_active_window_title(self) -> str:
        """Queries xdotool or wmctrl for the currently active window title."""
        try:
            # Try xdotool
            res = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()

            # Try wmctrl
            res_wm = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=2)
            if res_wm.returncode == 0 and res_wm.stdout.strip():
                first_line = res_wm.stdout.strip().split("\n")[0]
                parts = first_line.split(None, 3)
                if len(parts) >= 4:
                    return parts[3]
        except Exception:
            pass
        return "Workspace Virtual Desktop"

    def ground_and_click(self, query: str) -> Dict[str, Any]:
        """Grounds a human visual query and dispatches click."""
        target: GroundingTarget = self.adapter.ground_intent(query)
        click_res = self.adapter.engine.click(target.predicted_x, target.predicted_y)
        return {
            "query": query,
            "target": {
                "x": target.predicted_x,
                "y": target.predicted_y,
                "confidence": target.confidence,
                "source": target.source
            },
            "click_executed": click_res.get("executed", True),
            "timestamp": time.time()
        }

    def execute_workflow(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executes a multi-step desktop automation workflow.
        Steps can include: 'ground_click', 'type_text', 'hotkey', 'wait', 'observe'.
        """
        results = []
        for step in steps:
            action = step.get("action")
            if action == "ground_click":
                res = self.ground_and_click(step.get("query", ""))
                results.append({"action": action, "result": res})
            elif action == "type_text":
                res = self.adapter.engine.type_text(step.get("text", ""))
                results.append({"action": action, "result": res})
            elif action == "hotkey":
                res = self.adapter.engine.hotkey(step.get("keys", ["Return"]))
                results.append({"action": action, "result": res})
            elif action == "wait":
                time.sleep(step.get("seconds", 0.5))
                results.append({"action": action, "waited_sec": step.get("seconds", 0.5)})
            elif action == "observe":
                obs = self.capture_screen_observation()
                results.append({
                    "action": action,
                    "screenshot_hash": obs.screenshot_sha256,
                    "active_window": obs.active_window_title,
                    "mode": obs.perception_mode
                })
        return results

    # =========================================================================
    # ALWAYS-ON SCHEDULED GUI TASKS
    # =========================================================================

    def register_scheduled_task(
        self,
        name: str,
        interval_sec: float,
        workflow_steps: List[Dict[str, Any]],
        command_type: str = "GUI_PATROL"
    ) -> str:
        """Registers a recurring background desktop task."""
        sched_id = f"sched_{uuid.uuid4().hex[:8]}"
        task = ScheduledTaskEntry(
            schedule_id=sched_id,
            name=name,
            cron_or_interval_sec=interval_sec,
            command_type=command_type,
            payload={"steps": workflow_steps},
            is_active=True
        )
        self.scheduled_tasks[sched_id] = task
        return sched_id

    def run_due_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Executes any scheduled tasks that have reached their interval."""
        now = time.time()
        executed_runs = []
        for task in self.scheduled_tasks.values():
            if not task.is_active:
                continue
            if (now - task.last_run_timestamp) >= task.cron_or_interval_sec:
                steps = task.payload.get("steps", [])
                wf_res = self.execute_workflow(steps)
                task.last_run_timestamp = now
                task.run_count += 1
                task.last_status = "COMPLETED"
                executed_runs.append({
                    "schedule_id": task.schedule_id,
                    "name": task.name,
                    "run_count": task.run_count,
                    "results": wf_res
                })
        return executed_runs
