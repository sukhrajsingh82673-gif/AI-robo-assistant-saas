"""
ZONATA Autonomous Coworker 2.0 — Hermes Tool-Calling Adapter
Binds the 14 Computer-Use Engine primitives to Nous Hermes function-calling format.
"""

from __future__ import annotations
import json
import time
from typing import Dict, List, Optional, Any
from ..computer_use_engine import ComputerUseEngine


class HermesComputerUseAdapter:
    """
    Translates Hermes tool calling schemas and invocations into ComputerUseEngine actions.
    """

    TOOL_NAME = "computer_use"

    def __init__(self, engine: Optional[ComputerUseEngine] = None):
        self.engine = engine or ComputerUseEngine()

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

    def execute_hermes_call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses Hermes tool call arguments and invokes the corresponding GUI primitive.
        """
        action = arguments.get("action")
        coord = arguments.get("coordinate") or [self.engine.cursor_x, self.engine.cursor_y]
        x = int(coord[0]) if len(coord) > 0 else 0
        y = int(coord[1]) if len(coord) > 1 else 0

        if action == "observe":
            obs = self.engine.observe()
            return {
                "status": "SUCCESS",
                "active_window": obs.active_window,
                "cursor": obs.cursor_position,
                "elements_detected": len(obs.elements),
                "element_labels": [el.label for el in obs.elements]
            }
        elif action == "click":
            res = self.engine.click(x, y, button=arguments.get("button", "left"))
            return {"status": "SUCCESS", "result": res}
        elif action == "double_click":
            res = self.engine.double_click(x, y)
            return {"status": "SUCCESS", "result": res}
        elif action == "right_click":
            res = self.engine.right_click(x, y)
            return {"status": "SUCCESS", "result": res}
        elif action == "move":
            res = self.engine.move(x, y)
            return {"status": "SUCCESS", "result": res}
        elif action == "drag":
            end_c = arguments.get("end_coordinate") or [x + 50, y + 50]
            res = self.engine.drag(x, y, end_c[0], end_c[1])
            return {"status": "SUCCESS", "result": res}
        elif action == "scroll":
            res = self.engine.scroll(direction=arguments.get("direction", "down"))
            return {"status": "SUCCESS", "result": res}
        elif action == "type":
            text = arguments.get("text", "")
            res = self.engine.type_text(text)
            return {"status": "SUCCESS", "result": res}
        elif action == "key":
            key_name = arguments.get("key", "Return")
            res = self.engine.press_key(key_name)
            return {"status": "SUCCESS", "result": res}
        elif action == "hotkey":
            keys = arguments.get("keys") or [arguments.get("key", "ctrl")]
            res = self.engine.hotkey(keys)
            return {"status": "SUCCESS", "result": res}
        elif action == "launch":
            res = self.engine.launch(arguments.get("target", "Terminal"))
            return {"status": "SUCCESS", "result": res}
        elif action == "close":
            res = self.engine.close(arguments.get("target", ""))
            return {"status": "SUCCESS", "result": res}
        elif action == "switch_window":
            res = self.engine.switch_window(arguments.get("target", ""))
            return {"status": "SUCCESS", "result": res}
        elif action == "screenshot":
            png_bytes = self.engine.screenshot()
            return {"status": "SUCCESS", "size_bytes": len(png_bytes)}
        elif action == "verify":
            passed = self.engine.verify(
                arguments.get("assertion", "window_active"),
                arguments.get("expected", self.engine.active_window)
            )
            return {"status": "SUCCESS", "verified": passed}
        else:
            return {"status": "ERROR", "error": f"Unknown GUI action: '{action}'"}
