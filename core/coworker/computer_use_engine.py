"""
ZONATA Autonomous Coworker 2.0 — Desktop Computer-Use Engine
Implements the 14 GUI automation primitives with visual perception,
bounding box element grounding, and graceful headless fallback simulation.
"""

from __future__ import annotations
import os
import sys
import time
import uuid
import json
import base64
import re
import subprocess
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any



class GUIActionPrimitive(str, Enum):
    OBSERVE = "OBSERVE"
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    DRAG = "DRAG"
    SCROLL = "SCROLL"
    MOVE = "MOVE"
    TYPE_TEXT = "TYPE_TEXT"
    PRESS_KEY = "PRESS_KEY"
    HOTKEY = "HOTKEY"
    LAUNCH = "LAUNCH"
    CLOSE = "CLOSE"
    SWITCH_WINDOW = "SWITCH_WINDOW"
    SCREENSHOT = "SCREENSHOT"
    VERIFY = "VERIFY"


class DesktopEnvironmentType(str, Enum):
    REAL_DESKTOP_CONNECTED = "REAL_DESKTOP_CONNECTED"
    VIRTUAL_DESKTOP_CONNECTED = "VIRTUAL_DESKTOP_CONNECTED"
    HEADLESS_EXECUTION_ONLY = "HEADLESS_EXECUTION_ONLY"
    SIMULATED_PERCEPTION_ONLY = "SIMULATED_PERCEPTION_ONLY"


@dataclass
class GUIExecutionResult:
    success: bool
    action_id: str
    execution_time_ms: float
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px <= (self.x + self.width) and self.y <= py <= (self.y + self.height)

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class UIElement:
    element_id: str
    label: str
    box: BoundingBox
    confidence: float = 1.0
    element_type: str = "button"  # button, input, text, icon, window, menu
    is_interactive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "label": self.label,
            "box": self.box.to_dict(),
            "confidence": self.confidence,
            "element_type": self.element_type,
            "is_interactive": self.is_interactive,
            "metadata": self.metadata,
        }


@dataclass
class GUIObservation:
    timestamp: float
    screen_width: int
    screen_height: int
    active_window: str
    open_windows: List[str]
    elements: List[UIElement]
    screenshot_base64: Optional[str] = None
    cursor_position: Tuple[int, int] = (0, 0)
    # True when the element tree is seeded rather than scraped from a display.
    # Window titles, when present, may still be real; see windows_verified.
    synthetic: bool = False
    windows_verified: bool = False
    # Real top-level windows scraped from the X server (xwininfo). These are
    # actual X windows with real geometry, unlike the seeded interactive tree.
    window_elements: List[UIElement] = field(default_factory=list)
    window_tree_available: bool = False
    environment_type: DesktopEnvironmentType = DesktopEnvironmentType.HEADLESS_EXECUTION_ONLY
    perception_source: str = "IN_MEMORY_SYNTHETIC"

    @property
    def active_app(self) -> str:
        return self.active_window

    @property
    def window_title(self) -> str:
        return self.active_window

    @property
    def screen_resolution(self) -> Tuple[int, int]:
        return (self.screen_width, self.screen_height)

    @property
    def interactive_elements(self) -> List[UIElement]:
        return self.elements


class PerceptionEngine:
    """
    Visual perception and bounding box element locator.
    Parses accessibility trees, visual geometry, and simulated UI frames.
    """

    def __init__(self):
        self._registered_elements: Dict[str, UIElement] = {}

    def register_element(self, element: UIElement) -> None:
        self._registered_elements[element.element_id] = element

    def clear(self) -> None:
        self._registered_elements.clear()

    def detect_elements(self, image_bytes: Optional[bytes] = None) -> List[UIElement]:
        """
        Extracts UI elements and bounding boxes.
        When running in synthetic or headless mode, returns current simulated element tree.
        """
        return list(self._registered_elements.values())

    def find_by_text(self, text_query: str) -> Optional[UIElement]:
        q = text_query.lower().strip()
        for el in self._registered_elements.values():
            if q in el.label.lower():
                return el
        return None

    def find_by_type(self, element_type: str) -> List[UIElement]:
        return [el for el in self._registered_elements.values() if el.element_type == element_type]

    def observe_screen(self) -> GUIObservation:
        cue = ComputerUseEngine.get_instance()
        return cue.observe()


class ComputerUseEngine:
    """
    The 14 Universal GUI Automation Primitives for ZONATA Coworker 2.0.
    1. observe
    2. click
    3. double_click
    4. right_click
    5. drag
    6. scroll
    7. move
    8. type
    9. key
    10. hotkey
    11. launch
    12. close
    13. switch_window
    14. screenshot
    + verify
    """

    def __init__(self, display_width: int = 1920, display_height: int = 1080):
        self.width = display_width
        self.height = display_height
        self.cursor_x = display_width // 2
        self.cursor_y = display_height // 2
        self.active_window = "Desktop"
        self.open_windows = ["Desktop", "Terminal", "ZONATA Agent Console"]
        self.action_history: List[Dict[str, Any]] = []
        self.perception = PerceptionEngine()
        self.is_headless = not bool(os.environ.get("DISPLAY"))
        self.last_screenshot_synthetic = True
        self._init_default_scene()

    def _init_default_scene(self) -> None:
        """Seeds baseline desktop UI elements."""
        self.perception.clear()
        defaults = [
            UIElement("btn_start", "Start Menu", BoundingBox(10, self.height - 40, 80, 30), element_type="button"),
            UIElement("btn_submit", "Submit", BoundingBox(600, 450, 100, 40), element_type="button"),
            UIElement("inp_search", "Search Bar", BoundingBox(200, 100, 400, 35), element_type="input"),
            UIElement("btn_close", "Close Window", BoundingBox(self.width - 50, 10, 40, 30), element_type="button"),
        ]
        for d in defaults:
            self.perception.register_element(d)

    def _record(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "action": action,
            "params": params,
            "cursor": (self.cursor_x, self.cursor_y),
            "active_window": self.active_window,
            "timestamp": time.time()
        }
        self.action_history.append(entry)
        return entry

    # --- Execution truth helpers -------------------------------------------------

    def _dispatch(self, argv: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Attempt a real input dispatch. Returns (executed, reason_if_not).

        A primitive may only report success when the host actually accepted the
        input event. Headless operation is not simulated: callers get
        ACTION_NOT_IMPLEMENTED instead of a fabricated success.
        """
        if not os.environ.get("DISPLAY"):
            return False, "NO_DISPLAY"
        if not shutil.which(argv[0]):
            return False, "TOOL_MISSING"
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=5)
        except subprocess.TimeoutExpired:
            return False, "DISPATCH_TIMEOUT"
        except Exception:
            return False, "DISPATCH_FAILED"
        if proc.returncode != 0:
            return False, "DISPATCH_FAILED"
        return True, None

    def _mode(self, executed: bool) -> str:
        if executed:
            return "x11"
        return "headless" if not os.environ.get("DISPLAY") else "unavailable"

    def _action(self, name: str, params: Dict[str, Any], executed: bool,
                reason: Optional[str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rec = self._record(name, params)
        rec.update({
            "executed": executed,
            "mode": self._mode(executed),
            "status": "SUCCESS" if executed else "ACTION_NOT_IMPLEMENTED",
            "reason": None if executed else (reason or "NOT_EXECUTED"),
        })
        if extra:
            rec.update(extra)
        return rec

    def _clamp(self, x: int, y: int) -> Tuple[int, int]:
        return (max(0, min(int(x), self.width)), max(0, min(int(y), self.height)))

    @classmethod
    def detect_desktop_environment(cls) -> DesktopEnvironmentType:
        """
        Inspects active host environment to determine display reality:
        - REAL_DESKTOP_CONNECTED: Hardware X11 display (:0) or Wayland socket
        - VIRTUAL_DESKTOP_CONNECTED: Virtual X11 server (Xvfb / Xvnc on :99)
        - HEADLESS_EXECUTION_ONLY: Headless container, POSIX CLI only, no display
        - SIMULATED_PERCEPTION_ONLY: Unit-test sandbox with mocked/seeded perceptions
        """
        wayland = os.environ.get("WAYLAND_DISPLAY")
        if wayland:
            return DesktopEnvironmentType.REAL_DESKTOP_CONNECTED

        display = os.environ.get("DISPLAY")
        if not display:
            return DesktopEnvironmentType.HEADLESS_EXECUTION_ONLY

        if shutil.which("xdpyinfo"):
            try:
                out = subprocess.check_output(["xdpyinfo"], stderr=subprocess.DEVNULL, text=True, timeout=2)
                if "X.Org" in out or "vendor" in out.lower():
                    try:
                        ps = subprocess.check_output(["ps", "aux"], stderr=subprocess.DEVNULL, text=True)
                        if "Xvfb" in ps or display.startswith(":99"):
                            return DesktopEnvironmentType.VIRTUAL_DESKTOP_CONNECTED
                    except Exception:
                        pass
                    if display in (":0", ":0.0"):
                        return DesktopEnvironmentType.REAL_DESKTOP_CONNECTED
                    return DesktopEnvironmentType.VIRTUAL_DESKTOP_CONNECTED
            except Exception:
                return DesktopEnvironmentType.HEADLESS_EXECUTION_ONLY

        return DesktopEnvironmentType.HEADLESS_EXECUTION_ONLY

    @property
    def desktop_environment_type(self) -> DesktopEnvironmentType:
        return self.detect_desktop_environment()

    @property
    def environment_type(self) -> DesktopEnvironmentType:
        return self.detect_desktop_environment()

    # --- Real X11 perception ---------------------------------------------------

    # Matches lines such as:
    #   0x40000c "localhost: ~": ("xterm" "XTerm")  484x316+10+10  +10+10
    #   0x20011f "Openbox": ("" (none))  1x1+-100+-100  +-100+-100
    #   0x200173 (has no name): ()  1x1+0+0  +0+0
    _XWININFO_LINE = re.compile(
        r'^\s*(0x[0-9a-fA-F]+)\s+'
        r'(?:"([^"]*)"|\(has no name\)):\s*'
        r'(?:\(([^)]*)\))?\s*'
        r'(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)\s+'
        r'([+-]-?\d+)([+-]-?\d+)\s*$'
    )

    @staticmethod
    def _coord(tok: str) -> int:
        # Negative offsets print as "+-100"; a leading '+' is only a separator.
        return int(tok[1:] if tok.startswith("+") else tok)

    def x11_window_tree(self) -> List[UIElement]:
        """
        Enumerates named top-level X windows via `xwininfo -root -tree`.

        Only user-meaningful windows are returned: unnamed window-manager
        internals and the WM's own frame windows are excluded. Returns an empty
        list when there is no display, when xwininfo is missing, or when the
        query fails. No window is ever invented.
        """
        if not os.environ.get("DISPLAY") or not shutil.which("xwininfo"):
            return []
        try:
            out = subprocess.check_output(
                ["xwininfo", "-root", "-tree"], text=True, timeout=3,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return []

        windows: List[UIElement] = []
        seen = set()
        for line in out.splitlines():
            m = self._XWININFO_LINE.match(line)
            if not m:
                continue
            win_id, name, class_blob, w, h, rx, ry, ax, ay = m.groups()
            width, height = int(w), int(h)
            if width <= 1 or height <= 1:
                continue

            class_quoted = re.findall(r'"([^"]*)"', class_blob or "")
            klass = class_quoted[1] if len(class_quoted) > 1 else (
                class_quoted[0] if class_quoted else ""
            )
            label = (name or "").strip()
            if not label:
                # Unnamed windows are WM internals; skipping keeps the tree useful.
                continue
            if klass.lower() in ("openbox", "mutter", "metacity", "xfwm4"):
                continue

            # Deduplicate by absolute geometry + label (frame/client pairs).
            key = (label, int(ax) if False else self._coord(ax), self._coord(ay), width, height)
            if key in seen:
                continue
            seen.add(key)

            windows.append(UIElement(
                element_id=f"x11_{win_id}",
                label=label,
                box=BoundingBox(self._coord(ax), self._coord(ay), width, height),
                confidence=1.0,
                element_type="window",
                is_interactive=True,
                metadata={
                    "source": "x11_window_tree",
                    "window_id": win_id,
                    "window_class": klass,
                    "relative_geometry": f"{width}x{height}{rx}{ry}",
                },
            ))
        return windows

    def find_in_window_tree(self, text_query: str) -> Optional[UIElement]:
        """Case-insensitive label match against real X windows."""
        q = text_query.lower().strip()
        if not q:
            return None
        for el in self.x11_window_tree():
            if q in el.label.lower():
                return el
        return None

    # --- 14 GUI Primitives ---

    def observe(self) -> GUIObservation:
        """Primitive 1: Capture state, active window, and visible UI elements."""
        active_win = self.active_window
        open_wins = list(self.open_windows)
        display = os.environ.get("DISPLAY")
        real_windows = False
        if display and shutil.which("xdotool"):
            try:
                w_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True, timeout=2,
                                               stderr=subprocess.DEVNULL).strip()
                if w_id:
                    w_title = subprocess.check_output(["xdotool", "getwindowname", w_id], text=True,
                                                      timeout=2, stderr=subprocess.DEVNULL).strip()
                    if w_title:
                        active_win = w_title
                        real_windows = True
            except Exception:
                pass
        if display and shutil.which("wmctrl"):
            try:
                out = subprocess.check_output(["wmctrl", "-l"], text=True, timeout=2,
                                                stderr=subprocess.DEVNULL)
                parsed = []
                for line in out.strip().splitlines():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        parsed.append(parts[3])
                if parsed:
                    open_wins = parsed
                    real_windows = True
            except Exception:
                pass

        elements = self.perception.detect_elements()
        synthetic_elements = bool(elements)  # the element tree is seeded, never scraped
        for el in elements:
            el.metadata.setdefault("source", "seeded_scene")

        # Real window tree, scraped from the X server when a display exists.
        window_elements = self.x11_window_tree()
        window_tree_available = bool(window_elements)

        env_type = self.detect_desktop_environment()
        if window_tree_available:
            perception_src = "X11_WINDOW_TREE+SEEDED_ELEMENTS"
        elif real_windows:
            perception_src = "X11_WINDOW_METADATA+SEEDED_ELEMENTS"
        else:
            perception_src = "IN_MEMORY_SYNTHETIC"

        obs = GUIObservation(
            timestamp=time.time(),
            screen_width=self.width,
            screen_height=self.height,
            active_window=active_win,
            open_windows=open_wins,
            elements=elements,
            screenshot_base64=None,
            cursor_position=(self.cursor_x, self.cursor_y),
            synthetic=synthetic_elements,
            windows_verified=real_windows,
            window_elements=window_elements,
            window_tree_available=window_tree_available,
            environment_type=env_type,
            perception_source=perception_src,
        )
        self._record("observe", {"element_count": len(obs.elements),
                                 "window_tree_count": len(window_elements),
                                 "windows_from_x11": real_windows,
                                 "elements_seeded": synthetic_elements})
        return obs

    def click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """Primitive 2: Move cursor and send mouse click."""
        self.cursor_x, self.cursor_y = self._clamp(x, y)
        btn = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        ok, why = self._dispatch(["xdotool", "mousemove", str(self.cursor_x), str(self.cursor_y)])
        if ok:
            ok, why = self._dispatch(["xdotool", "click", btn])
        return self._action("click", {"x": self.cursor_x, "y": self.cursor_y, "button": button}, ok, why)

    def double_click(self, x: int, y: int) -> Dict[str, Any]:
        """Primitive 3: Send double click."""
        self.cursor_x, self.cursor_y = self._clamp(x, y)
        ok, why = self._dispatch(["xdotool", "mousemove", str(self.cursor_x), str(self.cursor_y)])
        if ok:
            ok, why = self._dispatch(["xdotool", "click", "--repeat", "2", "--delay", "100", "1"])
        return self._action("double_click", {"x": self.cursor_x, "y": self.cursor_y}, ok, why)

    def right_click(self, x: int, y: int) -> Dict[str, Any]:
        """Primitive 4: Send right click."""
        self.cursor_x, self.cursor_y = self._clamp(x, y)
        ok, why = self._dispatch(["xdotool", "mousemove", str(self.cursor_x), str(self.cursor_y)])
        if ok:
            ok, why = self._dispatch(["xdotool", "click", "3"])
        return self._action("right_click", {"x": self.cursor_x, "y": self.cursor_y}, ok, why)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> Dict[str, Any]:
        """Primitive 5: Drag and drop from start to end coordinates."""
        sx, sy = self._clamp(start_x, start_y)
        ex, ey = self._clamp(end_x, end_y)
        steps = [
            ["xdotool", "mousemove", str(sx), str(sy)],
            ["xdotool", "mousedown", "1"],
            ["xdotool", "mousemove", str(ex), str(ey)],
            ["xdotool", "mouseup", "1"],
        ]
        ok, why = True, None
        for cmd in steps:
            ok, why = self._dispatch(cmd)
            if not ok:
                break
        if ok:
            self.cursor_x, self.cursor_y = ex, ey
        return self._action("drag", {"start": (sx, sy), "end": (ex, ey)}, ok, why)

    def scroll(self, dx: int = 0, dy: int = 0, direction: str = "down") -> Dict[str, Any]:
        """Primitive 6: Scroll viewport in specified direction."""
        wheel = "4" if (direction == "up" or dy < 0) else "5"
        repeats = max(1, min(10, abs(dy) // 100 or abs(dx) // 100 or 1))
        ok, why = self._dispatch(["xdotool", "click", "--repeat", str(repeats), wheel])
        return self._action("scroll", {"dx": dx, "dy": dy, "direction": direction, "wheel": wheel,
                                       "repeats": repeats}, ok, why)

    def move(self, x: int, y: int) -> Dict[str, Any]:
        """Primitive 7: Move mouse cursor to coordinate without clicking."""
        self.cursor_x, self.cursor_y = self._clamp(x, y)
        ok, why = self._dispatch(["xdotool", "mousemove", str(self.cursor_x), str(self.cursor_y)])
        return self._action("move", {"x": self.cursor_x, "y": self.cursor_y}, ok, why)

    def type_text(self, text: str, delay_ms: int = 10) -> Dict[str, Any]:
        """Primitive 8: Type text string into focused input field."""
        if not text:
            return self._action("type", {"text": text}, False, "EMPTY_INPUT")
        ok, why = self._dispatch(["xdotool", "type", "--delay", str(delay_ms), text])
        return self._action("type", {"text": text, "delay_ms": delay_ms}, ok, why)

    def press_key(self, key_name: str) -> Dict[str, Any]:
        """Primitive 9: Press individual keyboard key."""
        ok, why = self._dispatch(["xdotool", "key", key_name])
        return self._action("key", {"key": key_name}, ok, why)

    def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        """Primitive 10: Press combination of hotkeys (e.g. ['ctrl', 'c'])."""
        if not keys:
            return self._action("hotkey", {"keys": keys}, False, "EMPTY_INPUT")
        combo = "+".join(keys)
        ok, why = self._dispatch(["xdotool", "key", combo])
        return self._action("hotkey", {"keys": keys, "combo": combo}, ok, why)

    def launch(self, application: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Primitive 11: Launch target application window.

        Deliberately not implemented here: spawning arbitrary host processes is an
        authority-bearing action and must pass the policy/approval gateway, not a
        GUI helper. The modelled state is only updated when a real launch is added.
        """
        app_name = application.strip()
        rec = self._record("launch", {"app": app_name, "args": args or []})
        rec.update({
            "executed": False,
            "mode": self._mode(False),
            "status": "ACTION_NOT_IMPLEMENTED",
            "reason": "APP_LAUNCH_REQUIRES_POLICY_GATEWAY",
        })
        return rec

    def close(self, application_or_window: str) -> Dict[str, Any]:
        """Primitive 12: Close application or window."""
        target = application_or_window.strip()
        ok, why = self._dispatch(["wmctrl", "-c", target])
        if ok and target in self.open_windows:
            self.open_windows.remove(target)
            if self.active_window == target:
                self.active_window = self.open_windows[0] if self.open_windows else "Desktop"
        return self._action("close", {"target": target}, ok, why)

    def switch_window(self, window_title: str) -> Dict[str, Any]:
        """Primitive 13: Bring specified window to foreground."""
        target = window_title.strip()
        ok, why = self._dispatch(["wmctrl", "-a", target])
        if ok:
            self.active_window = target
        return self._action("switch_window", {"target": target}, ok, why)

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
        """
        Primitive 14: Capture screenshot bytes.

        Returns real PNG bytes when a display is available. In headless mode it
        returns a 1x1 placeholder and records last_screenshot_synthetic=True so no
        caller can mistake it for the host screen.
        """
        self.last_screenshot_synthetic = True
        self._record("screenshot", {"region": region})
        display = os.environ.get("DISPLAY")
        if display and shutil.which("scrot"):
            tmp_f = f"/tmp/cu_shot_{uuid.uuid4().hex[:8]}.png"
            try:
                subprocess.run(["scrot", tmp_f], check=True, timeout=5,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(tmp_f):
                    with open(tmp_f, "rb") as f:
                        data = f.read()
                    os.remove(tmp_f)
                    if data.startswith(b"\x89PNG\r\n\x1a\n"):
                        self.last_screenshot_synthetic = False
                        return data
            except Exception:
                pass
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    def verify(self, assertion_type: str, expected_value: Any) -> bool:
        """
        Verification Primitive: asserts a condition on the *real* desktop state.

        Only conditions confirmed against the X server can pass. The seeded
        element tree is not evidence, so element assertions return False with
        UNVERIFIABLE unless a real accessibility scrape exists.
        """
        display = os.environ.get("DISPLAY")
        passed = False
        reason = None

        if assertion_type == "window_active":
            if display and shutil.which("xdotool"):
                try:
                    w_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True, timeout=2,
                                                   stderr=subprocess.DEVNULL).strip()
                    title = subprocess.check_output(["xdotool", "getwindowname", w_id], text=True,
                                                    timeout=2, stderr=subprocess.DEVNULL).strip()
                    passed = title.lower() == str(expected_value).lower()
                    if not passed:
                        reason = "WINDOW_MISMATCH"
                except Exception:
                    reason = "OBSERVATION_FAILED"
            else:
                reason = "NO_DISPLAY"
        elif assertion_type == "cursor_at":
            if display and shutil.which("xdotool"):
                try:
                    out = subprocess.check_output(["xdotool", "getmouselocation"], text=True, timeout=2,
                                                  stderr=subprocess.DEVNULL)
                    coords = dict(part.split(":") for part in out.split() if ":" in part)
                    ex, ey = expected_value
                    passed = abs(int(coords.get("x", -9999)) - ex) <= 5 and abs(int(coords.get("y", -9999)) - ey) <= 5
                    if not passed:
                        reason = "CURSOR_MISMATCH"
                except Exception:
                    reason = "OBSERVATION_FAILED"
            else:
                reason = "NO_DISPLAY"
        elif assertion_type == "element_present":
            # No real accessibility/OCR scrape is implemented, so the seeded tree
            # cannot prove anything about the host screen.
            reason = "PERCEPTION_NOT_IMPLEMENTED"
        else:
            reason = "UNKNOWN_ASSERTION"

        self._record("verify", {"assertion": assertion_type, "expected": expected_value,
                                "passed": passed, "reason": reason})
        return passed

    _instance: Optional[ComputerUseEngine] = None

    @classmethod
    def get_instance(cls) -> ComputerUseEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute_primitive(self, primitive: Any, **params) -> GUIExecutionResult:
        start_t = time.time()
        action_id = f"gui_act_{uuid.uuid4().hex[:12]}"
        try:
            prim_name = primitive.value if isinstance(primitive, GUIActionPrimitive) else str(primitive).upper()
            if prim_name == "OBSERVE":
                obs = self.observe()
                if obs.synthetic:
                    # Window/element data is not a real scrape: report it as such
                    # rather than letting a caller believe the screen was read.
                    return GUIExecutionResult(
                        success=False,
                        action_id=action_id,
                        execution_time_ms=(time.time() - start_t) * 1000,
                        output_data={
                            "active_app": obs.active_window,
                            "window_title": obs.active_window,
                            "screen_resolution": (obs.screen_width, obs.screen_height),
                            "interactive_elements": [e.to_dict() for e in obs.elements],
                            "synthetic": True,
                            "windows_verified": obs.windows_verified,
                            "status": "PARTIAL",
                            "reason": "PERCEPTION_NOT_IMPLEMENTED",
                        },
                        error="PERCEPTION_NOT_IMPLEMENTED",
                    )
                output = {
                    "active_app": obs.active_window,
                    "window_title": obs.active_window,
                    "screen_resolution": (obs.screen_width, obs.screen_height),
                    "interactive_elements": [e.to_dict() for e in obs.elements],
                    "synthetic": False,
                    "windows_verified": obs.windows_verified,
                }
            elif prim_name == "CLICK":
                rec = self.click(params.get("x", 0), params.get("y", 0), button=params.get("button", "left"))
                output = rec
            elif prim_name == "DOUBLE_CLICK":
                output = self.double_click(params.get("x", 0), params.get("y", 0))
            elif prim_name == "RIGHT_CLICK":
                output = self.right_click(params.get("x", 0), params.get("y", 0))
            elif prim_name == "DRAG":
                output = self.drag(params.get("start_x", 0), params.get("start_y", 0), params.get("end_x", 0), params.get("end_y", 0))
            elif prim_name == "SCROLL":
                output = self.scroll(dx=params.get("dx", 0), dy=params.get("dy", 0), direction=params.get("direction", "down"))
            elif prim_name == "MOVE":
                output = self.move(params.get("x", 0), params.get("y", 0))
            elif prim_name == "TYPE_TEXT":
                output = self.type_text(params.get("text", ""), delay_ms=params.get("delay_ms", 10))
            elif prim_name == "PRESS_KEY":
                output = self.press_key(params.get("key_name", "Return"))
            elif prim_name == "HOTKEY":
                output = self.hotkey(params.get("keys", []))
            elif prim_name == "LAUNCH":
                output = self.launch(params.get("application", ""), args=params.get("args"))
            elif prim_name == "CLOSE":
                output = self.close(params.get("application_or_window", ""))
            elif prim_name == "SWITCH_WINDOW":
                output = self.switch_window(params.get("window_title", ""))
            elif prim_name == "SCREENSHOT":
                b = self.screenshot(region=params.get("region"))
                synthetic = bool(getattr(self, "last_screenshot_synthetic", True))
                if synthetic:
                    return GUIExecutionResult(
                        success=False,
                        action_id=action_id,
                        execution_time_ms=(time.time() - start_t) * 1000,
                        output_data={"image_bytes": b, "size": len(b), "synthetic": True,
                                     "status": "ACTION_NOT_IMPLEMENTED", "reason": "NO_DISPLAY"},
                        error="NO_DISPLAY",
                    )
                output = {"image_bytes": b, "size": len(b), "synthetic": False}
            elif prim_name == "VERIFY":
                passed = self.verify(params.get("assertion_type", ""), params.get("expected_value"))
                output = {"passed": passed,
                          "status": "SUCCESS" if passed else "VERIFICATION_FAILED"}
            else:
                return GUIExecutionResult(
                    success=False,
                    action_id=action_id,
                    execution_time_ms=(time.time() - start_t) * 1000,
                    error=f"Unknown primitive: {prim_name}"
                )

            executed = output.get("executed", True)
            if prim_name == "VERIFY":
                executed = bool(output.get("passed"))
            return GUIExecutionResult(
                success=bool(executed),
                action_id=action_id,
                execution_time_ms=(time.time() - start_t) * 1000,
                output_data=output,
                error=None if executed else output.get("reason") or output.get("status"),
            )
        except Exception as e:
            return GUIExecutionResult(
                success=False,
                action_id=action_id,
                execution_time_ms=(time.time() - start_t) * 1000,
                error=str(e)
            )
