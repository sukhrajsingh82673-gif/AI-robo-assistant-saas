"""
ZONATA Enterprise Desktop Interaction Dispatcher (Sub-Step 3C)
Implements:
- 11 GUI interaction primitives with window-relative coordinate translation
- Out-of-grant coordinate boundary rejection (Rule 23 & Rule 28)
- Physical-speed throttling (human typing rate limits, click smoothing)
- Instant human physical override / hotkey halt (Rule 23 / 3C acceptance)
- Cryptographic evidence ledger event recording
"""

from __future__ import annotations

import os
import time
import uuid
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Any

from core.evidence_service import evidence_service
from .perception import BoundingRect

logger = logging.getLogger("zonata.host.interaction")


class InteractionPrimitive(str, Enum):
    """The 11 standard OS GUI interaction primitives."""
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    MIDDLE_CLICK = "MIDDLE_CLICK"
    CLICK_AND_DRAG = "CLICK_AND_DRAG"
    TYPE_TEXT = "TYPE_TEXT"
    PRESS_KEY = "PRESS_KEY"
    KEY_COMBO = "KEY_COMBO"
    SCROLL = "SCROLL"
    HOVER = "HOVER"
    WAIT_FOR_NODE = "WAIT_FOR_NODE"


class OutOfGrantCoordinatesError(Exception):
    """Raised when interaction coordinates fall outside the granted window boundary."""
    pass


class HumanPhysicalOverrideError(Exception):
    """Raised when a human physical mouse/keyboard event or kill switch halts execution."""
    pass


@dataclass
class InteractionResult:
    action_id: str
    primitive: InteractionPrimitive
    executed: bool
    relative_coords: Optional[Tuple[int, int]]
    absolute_coords: Optional[Tuple[int, int]]
    duration_ms: float
    throttled_wait_ms: float
    evidence_event_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "primitive": self.primitive.value,
            "executed": self.executed,
            "relative_coords": self.relative_coords,
            "absolute_coords": self.absolute_coords,
            "duration_ms": self.duration_ms,
            "throttled_wait_ms": self.throttled_wait_ms,
            "evidence_event_id": self.evidence_event_id,
            "error": self.error,
        }


class PhysicalSpeedThrottler:
    """
    Enforces physiological human speed constraints on synthetic inputs.
    - Max typing speed: 12 chars/sec (~120 words per minute).
    - Mouse movement & click smoothing: enforces inter-action cadence.
    """

    MAX_TYPING_CPS = 12.0  # Max 12 characters per second
    MIN_INTER_CLICK_INTERVAL_SEC = 0.05  # 50ms between clicks

    def __init__(self, simulated: Optional[bool] = None):
        self.simulated = (
            os.environ.get("ZONATA_TEST_MODE") == "1" if simulated is None else simulated
        )
        self._last_interaction_time: float = 0.0

    def compute_typing_duration(self, text: str) -> float:
        """Returns the human physical duration required to type the text in seconds."""
        if not text:
            return 0.0
        # 12 chars per second -> ~83ms per keystroke
        return len(text) / self.MAX_TYPING_CPS

    def throttle_interaction(self, is_click: bool = False) -> float:
        """
        Enforces pause between physical actions.
        Returns throttled delay in milliseconds.
        """
        now = time.time()
        elapsed = now - self._last_interaction_time
        delay_ms = 0.0

        if is_click and elapsed < self.MIN_INTER_CLICK_INTERVAL_SEC:
            delay_sec = self.MIN_INTER_CLICK_INTERVAL_SEC - elapsed
            delay_ms = delay_sec * 1000.0
            if not self.simulated:
                time.sleep(delay_sec)

        self._last_interaction_time = time.time()
        return delay_ms


class HumanOverrideDetector:
    """
    Monitors host physical peripherals for human override.
    Any physical mouse movement, keystroke, or hotkey triggers instant abort.
    """

    def __init__(self):
        self._override_active: bool = False
        self._override_reason: Optional[str] = None

    @property
    def is_override_active(self) -> bool:
        return self._override_active

    def trigger_physical_override(self, reason: str = "HUMAN_PHYSICAL_INPUT_DETECTED") -> None:
        """Called by OS hook when human touches mouse, keyboard, or hotkey."""
        self._override_active = True
        self._override_reason = reason
        logger.warning("HUMAN PHYSICAL OVERRIDE TRIGGERED: %s", reason)

    def reset(self) -> None:
        self._override_active = False
        self._override_reason = None


class DesktopInteractionDispatcher:
    """
    Translates relative coordinates, enforces boundary grants, physical-speed throttling,
    and human physical override interception.
    """

    def __init__(
        self,
        throttler: Optional[PhysicalSpeedThrottler] = None,
        backend: Optional[Callable[[Dict[str, Any]], bool]] = None,
        simulated: Optional[bool] = None,
    ):
        self.simulated = (
            os.environ.get("ZONATA_TEST_MODE") == "1" if simulated is None else simulated
        )
        self.throttler = throttler or PhysicalSpeedThrottler(simulated=self.simulated)
        self.backend = backend
        self.override_detector = HumanOverrideDetector()

    def dispatch(
        self,
        tenant_id: str,
        company_id: str,
        primitive: InteractionPrimitive,
        window_bounds: BoundingRect,
        relative_coords: Optional[Tuple[int, int]] = None,
        drag_end_relative: Optional[Tuple[int, int]] = None,
        text: Optional[str] = None,
        key_name: Optional[str] = None,
        scroll_delta: Optional[int] = None,
    ) -> InteractionResult:
        start_time = time.time()
        action_id = f"act_{uuid.uuid4().hex[:12]}"

        # 1. Human Physical Override Check (acceptance criterion e)
        if self.override_detector.is_override_active:
            raise HumanPhysicalOverrideError(
                f"Automation halted by human override: {self.override_detector._override_reason}"
            )

        # 2. Coordinate Boundary Validation (acceptance criterion d & Rule 28)
        abs_coords: Optional[Tuple[int, int]] = None
        if relative_coords is not None:
            rx, ry = relative_coords
            if rx < 0 or rx > window_bounds.width or ry < 0 or ry > window_bounds.height:
                raise OutOfGrantCoordinatesError(
                    f"Coordinates ({rx}, {ry}) are outside the granted window bounds "
                    f"[0..{window_bounds.width}, 0..{window_bounds.height}]. Host rejected action."
                )
            abs_coords = (window_bounds.x + rx, window_bounds.y + ry)

        # If drag primitive, validate drag end coordinates too
        if primitive == InteractionPrimitive.CLICK_AND_DRAG and drag_end_relative is not None:
            ex, ey = drag_end_relative
            if ex < 0 or ex > window_bounds.width or ey < 0 or ey > window_bounds.height:
                raise OutOfGrantCoordinatesError(
                    f"Drag end coordinates ({ex}, {ey}) are outside the granted window bounds "
                    f"[0..{window_bounds.width}, 0..{window_bounds.height}]. Host rejected action."
                )

        # 3. Physical-Speed Throttling (acceptance criterion)
        throttled_wait_ms = 0.0
        if primitive in {
            InteractionPrimitive.CLICK,
            InteractionPrimitive.DOUBLE_CLICK,
            InteractionPrimitive.RIGHT_CLICK,
            InteractionPrimitive.MIDDLE_CLICK,
        }:
            throttled_wait_ms = self.throttler.throttle_interaction(is_click=True)
        elif primitive == InteractionPrimitive.TYPE_TEXT and text:
            # Human typing speed limit calculation
            typing_duration_sec = self.throttler.compute_typing_duration(text)
            throttled_wait_ms = typing_duration_sec * 1000.0

        # Check override again right before action
        if self.override_detector.is_override_active:
            raise HumanPhysicalOverrideError("Automation halted by human override during throttling pause.")

        # 4. Dispatch through a real backend. A test may explicitly simulate;
        # production cannot claim execution without one.
        executed = False
        execution_error: Optional[str] = None
        if self.simulated:
            executed = True
        elif self.backend is not None:
            try:
                executed = bool(self.backend({
                    "action_id": action_id,
                    "primitive": primitive.value,
                    "relative_coords": relative_coords,
                    "absolute_coords": abs_coords,
                    "text": text,
                    "key_name": key_name,
                    "scroll_delta": scroll_delta,
                }))
                if not executed:
                    execution_error = "Desktop backend refused the interaction."
            except Exception as exc:
                execution_error = f"Desktop backend failed: {exc}"
        else:
            execution_error = (
                "No desktop interaction backend is configured; refusing to report a phantom execution."
            )

        duration_ms = (time.time() - start_time) * 1000.0

        # 5. Cryptographic Evidence Ledger Recording
        ev_receipt = evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="DESKTOP_INTERACTION_DISPATCHED",
            payload={
                "action_id": action_id,
                "primitive": primitive.value,
                "relative_coords": relative_coords,
                "absolute_coords": abs_coords,
                "text_length": len(text) if text else 0,
                "throttled_wait_ms": throttled_wait_ms,
                "window_bounds": window_bounds.to_dict(),
                "executed": executed,
                "simulated": self.simulated,
                "error": execution_error,
            },
        )

        if execution_error:
            raise HumanPhysicalOverrideError(execution_error)

        return InteractionResult(
            action_id=action_id,
            primitive=primitive,
            executed=executed,
            relative_coords=relative_coords,
            absolute_coords=abs_coords,
            duration_ms=duration_ms,
            throttled_wait_ms=throttled_wait_ms,
            evidence_event_id=ev_receipt.get("event_id"),
        )
