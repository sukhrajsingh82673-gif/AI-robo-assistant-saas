"""
ZONATA Autonomous Coworker 2.0 — Hermes Tool-Calling Adapter
Binds the 14 Computer-Use Engine primitives to Nous Hermes function-calling format.
"""

from __future__ import annotations
import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from ..computer_use_engine import ComputerUseEngine


class HermesComputerUseAdapter:
    """
    Translates Hermes tool calling schemas and invocations into ComputerUseEngine actions.
    Supports live model inference against Nous Hermes / OpenAI-compatible endpoints.
    """

    TOOL_NAME = "computer_use"

    def __init__(
        self,
        engine: Optional[ComputerUseEngine] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.engine = engine or ComputerUseEngine()
        self.endpoint = (endpoint or os.environ.get("HERMES_API_ENDPOINT") or os.environ.get("HERMES_ENDPOINT") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("HERMES_API_KEY") or ""

    def check_connection(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Verifies if the configured Hermes inference endpoint is live and reachable."""
        if not self.endpoint:
            return {
                "connected": False,
                "status": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                "endpoint": None,
                "reason": "HERMES_API_ENDPOINT is not configured in environment"
            }
        try:
            url = f"{self.endpoint}/v1/models"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                return {"connected": True, "status": "ONLINE", "endpoint": self.endpoint, "models": data.get("data", [])}
        except Exception as e:
            return {
                "connected": False,
                "status": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                "endpoint": self.endpoint,
                "reason": f"Connection failed: {str(e)}"
            }

    def call_hermes_inference(
        self,
        messages: List[Dict[str, Any]],
        model: str = "hermes-3-llama-3.1-8b",
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Invokes Hermes chat completions endpoint with optional computer_use function definition.
        Returns the parsed message or honest dependency block if endpoint is offline.
        """
        conn = self.check_connection(timeout=min(timeout, 3.0))
        if not conn["connected"]:
            return {
                "status": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                "connected": False,
                "endpoint": self.endpoint or "UNSET",
                "reason": conn["reason"],
                "content": None,
                "tool_calls": []
            }

        url = f"{self.endpoint}/v1/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2
        }
        if tools is not None:
            payload["tools"] = tools
        elif True:
            payload["tools"] = [self.get_tool_schema()]

        try:
            req_data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode())
                choice = resp_data.get("choices", [{}])[0].get("message", {})
                return {
                    "status": "SUCCESS",
                    "connected": True,
                    "content": choice.get("content"),
                    "tool_calls": choice.get("tool_calls", []),
                    "raw": resp_data
                }
        except Exception as e:
            return {
                "status": "ERROR",
                "connected": True,
                "reason": f"Inference call error: {str(e)}",
                "tool_calls": []
            }

    def get_tool_schema(self) -> Dict[str, Any]:
        """Returns JSON schema formatted for Hermes model prompt context."""
        return {
            "type": "function",
            "function": {
                "name": self.TOOL_NAME,
                "description": "Desktop computer-use automation primitives for mouse, keyboard, window, and observation tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "observe", "click", "double_click", "right_click",
                                "drag", "scroll", "move", "type", "key", "hotkey",
                                "launch", "close", "switch_window", "screenshot", "verify"
                            ],
                            "description": "The specific GUI primitive to invoke."
                        },
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "[x, y] screen coordinates for click, move, drag."
                        },
                        "text": {"type": "string", "description": "Text to type into input fields."},
                        "key": {"type": "string", "description": "Key or hotkey string."},
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of modifier keys for hotkey combos."
                        },
                        "target": {"type": "string", "description": "Application or window title."},
                        "direction": {"type": "string", "enum": ["up", "down", "left", "right"]}
                    },
                    "required": ["action"]
                }
            }
        }

    @staticmethod
    def _wrap(res: Dict[str, Any]) -> Dict[str, Any]:
        """Map a primitive result to a tool-call status without inventing success."""
        executed = bool(res.get("executed", False))
        out = {
            "status": "SUCCESS" if executed else "ACTION_NOT_IMPLEMENTED",
            "executed": executed,
            "result": res,
        }
        if not executed:
            out["reason"] = res.get("reason") or "NOT_EXECUTED"
        return out

    def execute_hermes_call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses Hermes tool call arguments and invokes the corresponding GUI primitive.

        Status reflects what actually happened on the host: a primitive that could
        not be dispatched reports ACTION_NOT_IMPLEMENTED, never SUCCESS.
        """
        action = arguments.get("action")
        coord = arguments.get("coordinate") or [self.engine.cursor_x, self.engine.cursor_y]
        x = int(coord[0]) if len(coord) > 0 else 0
        y = int(coord[1]) if len(coord) > 1 else 0

        if action == "observe":
            obs = self.engine.observe()
            # Window data can be real while the element tree is still seeded.
            executed = obs.windows_verified and not obs.synthetic
            out = {
                "status": "SUCCESS" if executed else "PARTIAL",
                "executed": executed,
                "synthetic": obs.synthetic,
                "windows_verified": obs.windows_verified,
                "active_window": obs.active_window,
                "cursor": obs.cursor_position,
                "elements_detected": len(obs.elements),
                "element_labels": [el.label for el in obs.elements],
            }
            if not executed:
                out["reason"] = "PERCEPTION_NOT_IMPLEMENTED"
            return out
        elif action == "click":
            return self._wrap(self.engine.click(x, y, button=arguments.get("button", "left")))
        elif action == "double_click":
            return self._wrap(self.engine.double_click(x, y))
        elif action == "right_click":
            return self._wrap(self.engine.right_click(x, y))
        elif action == "move":
            return self._wrap(self.engine.move(x, y))
        elif action == "drag":
            end_c = arguments.get("end_coordinate") or [x + 50, y + 50]
            return self._wrap(self.engine.drag(x, y, end_c[0], end_c[1]))
        elif action == "scroll":
            return self._wrap(self.engine.scroll(direction=arguments.get("direction", "down")))
        elif action == "type":
            return self._wrap(self.engine.type_text(arguments.get("text", "")))
        elif action == "key":
            return self._wrap(self.engine.press_key(arguments.get("key", "Return")))
        elif action == "hotkey":
            keys = arguments.get("keys") or [arguments.get("key", "ctrl")]
            return self._wrap(self.engine.hotkey(keys))
        elif action == "launch":
            return self._wrap(self.engine.launch(arguments.get("target", "Terminal")))
        elif action == "close":
            return self._wrap(self.engine.close(arguments.get("target", "")))
        elif action == "switch_window":
            return self._wrap(self.engine.switch_window(arguments.get("target", "")))
        elif action == "screenshot":
            png_bytes = self.engine.screenshot()
            synthetic = bool(getattr(self.engine, "last_screenshot_synthetic", True))
            out = {
                "status": "ACTION_NOT_IMPLEMENTED" if synthetic else "SUCCESS",
                "executed": not synthetic,
                "synthetic": synthetic,
                "size_bytes": len(png_bytes),
            }
            if synthetic:
                out["reason"] = "NO_DISPLAY"
            return out
        elif action == "verify":
            passed = self.engine.verify(
                arguments.get("assertion", "window_active"),
                arguments.get("expected", self.engine.active_window)
            )
            return {
                "status": "SUCCESS" if passed else "VERIFICATION_FAILED",
                "executed": passed,
                "verified": passed,
            }
        else:
            return {"status": "ERROR", "error": f"Unknown GUI action: '{action}'"}
