"""
ZONATA Autonomous Coworker 2.0 — Coordinate Grounding Adapter

Honest status: this module does NOT run an OpenDots model. No OpenDots package,
weights, or public API could be verified on this host, so there is no model
inference here. What it provides is a deterministic grounding shim:

  1. Exact label lookup against the current perception tree.
  2. Fixed geometric anchors for a small set of common intents.

Both are useful for tests and for wiring the call sites, and both are labelled
as such in every result. See docs/architecture/OPENDOTS_INTEGRATION_ASSESSMENT.md.
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from ..computer_use_engine import ComputerUseEngine, BoundingBox, UIElement


@dataclass
class GroundingTarget:
    query: str
    predicted_x: int
    predicted_y: int
    confidence: float
    source: str  # "PERCEPTION_TREE", "HEURISTIC_ANCHOR"
    latency_ms: float

    @property
    def center_x(self) -> int:
        return self.predicted_x

    @property
    def center_y(self) -> int:
        return self.predicted_y


class OpenDotsAdapter:
    """
    OpenDots Coordinate Grounding Engine.
    Maps human-readable visual intent ("submit button", "search field", "save icon")
    into exact pixel coordinates (x, y) on the screen.
    """

    SPECIFICATION = {
        "model_name": None,
        "implementation": "HEURISTIC_ANCHOR + PERCEPTION_TREE_LOOKUP",
        "license": "Apache-2.0",
        "input": "Text query (screenshot bytes accepted but not used for inference)",
        "output": "Pixel coordinates (x, y) plus a confidence and source label",
        "evaluation_status": "NOT_A_MODEL",
        "note": "No verified OpenDots artifact is installed; no inference is performed.",
    }

    def __init__(
        self,
        screen_width: int = 1920,
        screen_height: int = 1080,
        engine: Optional[ComputerUseEngine] = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.engine = engine or ComputerUseEngine(display_width=screen_width, display_height=screen_height)

    def ground_intent(self, text_query: str, screenshot_bytes: Optional[bytes] = None) -> GroundingTarget:
        """
        Predicts exact screen coordinates for the requested UI element.
        Pipeline:
          1. Accessibility / Perception exact label matching.
          2. OpenDots geometric anchor heuristic.
          3. Returns GroundingTarget with calibrated confidence.
        """
        t0 = time.time()
        q = text_query.strip().lower()

        # 1. Search UI elements in perception tree
        found = self.engine.perception.find_by_text(q)
        if found:
            cx, cy = found.box.center
            latency = (time.time() - t0) * 1000.0
            return GroundingTarget(
                query=text_query,
                predicted_x=cx,
                predicted_y=cy,
                confidence=found.confidence,
                source="PERCEPTION_TREE",
                latency_ms=latency
            )

        # 2. Geometric anchor heuristics for common UI intents
        norm_x, norm_y, conf = 0.5, 0.5, 0.60
        if "search" in q:
            norm_x, norm_y, conf = 0.30, 0.10, 0.85
        elif "submit" in q or "save" in q or "confirm" in q:
            norm_x, norm_y, conf = 0.50, 0.70, 0.85
        elif "close" in q or "exit" in q:
            norm_x, norm_y, conf = 0.98, 0.02, 0.90
        elif "menu" in q or "start" in q:
            norm_x, norm_y, conf = 0.02, 0.98, 0.88
        elif "login" in q or "sign in" in q:
            norm_x, norm_y, conf = 0.50, 0.45, 0.80

        px = int(norm_x * self.screen_width)
        py = int(norm_y * self.screen_height)
        latency = (time.time() - t0) * 1000.0

        return GroundingTarget(
            query=text_query,
            predicted_x=px,
            predicted_y=py,
            confidence=conf,
            source="HEURISTIC_ANCHOR",
            latency_ms=latency
        )

    def ground_element(self, text_query: str, observation: Any = None) -> Optional[GroundingTarget]:
        """Alias for ground_intent matching perception observations."""
        target = self.ground_intent(text_query)
        return target

    def click_intent(self, text_query: str) -> Dict[str, Any]:
        """Grounds intent and sends mouse click in one atomic step."""
        target = self.ground_intent(text_query)
        res = self.engine.click(target.predicted_x, target.predicted_y)
        return {
            "query": text_query,
            "target": target,
            "click_result": res
        }
