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
        """Sets DISPLAY environment variable only if X11 is reachable or already configured."""
        if "DISPLAY" in os.environ:
            return
        disp_num = self.display.lstrip(":")
        sock_path = f"/tmp/.X11-unix/X{disp_num}"
        if os.path.exists(sock_path):
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

    def benchmark_grounding_accuracy(
        self,
        ground_truth_targets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Benchmarks coordinate grounding and visual perception accuracy:
          - Target visual grounding
          - Euclidean click distance error in pixels: sqrt((px - ex)^2 + (py - ey)^2)
          - Text-entry character accuracy
          - Overall task completion rate
        """
        import math
        total = len(ground_truth_targets)
        if total == 0:
            return {
                "total_benchmarks": 0,
                "completed_count": 0,
                "completion_rate": 0.0,
                "mean_euclidean_distance_error_px": 0.0,
                "max_euclidean_distance_error_px": 0.0,
                "character_accuracy": 1.0,
                "target_results": []
            }

        completed_count = 0
        distance_errors = []
        char_accuracies = []
        target_results = []

        for target_spec in ground_truth_targets:
            query = target_spec.get("query", "")
            expected_x = target_spec.get("expected_x", 0)
            expected_y = target_spec.get("expected_y", 0)
            expected_text = target_spec.get("expected_text")
            typed_text = target_spec.get("typed_text")
            tolerance_px = target_spec.get("tolerance_px", 50.0)

            target: GroundingTarget = self.adapter.ground_intent(query)
            px = target.predicted_x
            py = target.predicted_y

            dist_err = math.sqrt((px - expected_x) ** 2 + (py - expected_y) ** 2)
            distance_errors.append(dist_err)

            char_acc = 1.0
            if expected_text is not None and typed_text is not None:
                if not expected_text and not typed_text:
                    char_acc = 1.0
                elif not expected_text or not typed_text:
                    char_acc = 0.0
                else:
                    matches = sum(1 for c1, c2 in zip(expected_text, typed_text) if c1 == c2)
                    char_acc = matches / max(len(expected_text), len(typed_text))
                char_accuracies.append(char_acc)

            is_completed = (dist_err <= tolerance_px) and (char_acc >= 0.8)
            if is_completed:
                completed_count += 1

            target_results.append({
                "query": query,
                "expected": (expected_x, expected_y),
                "predicted": (px, py),
                "distance_error_px": round(dist_err, 2),
                "within_tolerance": dist_err <= tolerance_px,
                "confidence": target.confidence,
                "source": target.source,
                "character_accuracy": round(char_acc, 2),
                "task_completed": is_completed
            })

        mean_dist = sum(distance_errors) / len(distance_errors) if distance_errors else 0.0
        max_dist = max(distance_errors) if distance_errors else 0.0
        mean_char_acc = sum(char_accuracies) / len(char_accuracies) if char_accuracies else 1.0
        completion_rate = completed_count / total

        return {
            "total_benchmarks": total,
            "completed_count": completed_count,
            "completion_rate": round(completion_rate, 4),
            "mean_euclidean_distance_error_px": round(mean_dist, 2),
            "max_euclidean_distance_error_px": round(max_dist, 2),
            "character_accuracy": round(mean_char_acc, 4),
            "target_results": target_results,
            "benchmark_timestamp": time.time()
        }
