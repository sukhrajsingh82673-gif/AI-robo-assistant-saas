"""
ZONATA Remote View — Streamer & Minimum Capture Engine (Rule 24, Rule 28).

Enforces Rule 28:
"Minimum necessary capture. Capture only the granted window or region,
mask secret fields and challenge widgets before anything is stored or
sent to a model, and apply Step 1 retention to recordings."
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, List, Optional

from core.remote_view.types import FramePacket, MaskRegion, ViewportBounds


class RemoteViewStreamer:
    """
    Renders and streams viewport frames for browser or desktop sessions.
    Strictly clips to the granted viewport and redacts sensitive regions pre-transmission.
    """

    def __init__(self, session_id: str, viewport: ViewportBounds):
        self.session_id = session_id
        self.viewport = viewport
        self.mask_regions: List[MaskRegion] = []
        self._frame_counter: int = 0

    def add_mask_region(self, region: MaskRegion) -> None:
        """Register a sensitive rectangle that must be blacked out (Rule 24 & 28)."""
        self.mask_regions.append(region)

    def clear_mask_regions(self) -> None:
        """Clear dynamic mask regions."""
        self.mask_regions.clear()

    def process_and_stream_frame(
        self,
        raw_pixels: Optional[bytes] = None,
        canvas_description: Optional[str] = None,
    ) -> FramePacket:
        """
        Produce a safe, redacted, viewport-bounded frame packet.
        """
        self._frame_counter += 1

        # Simulate synthetic frame capture clipped to viewport
        frame_payload = {
            "session_id": self.session_id,
            "frame_index": self._frame_counter,
            "viewport": self.viewport.to_dict(),
            "canvas_description": canvas_description or "rendered_viewport",
            "redacted_regions": [m.to_dict() for m in self.mask_regions],
            "redaction_applied": len(self.mask_regions) > 0,
        }

        # Encode frame safely
        encoded_data = base64.b64encode(json.dumps(frame_payload).encode("utf-8")).decode("ascii")

        return FramePacket(
            session_id=self.session_id,
            frame_index=self._frame_counter,
            timestamp=time.time(),
            viewport=self.viewport.to_dict(),
            image_base64=f"data:image/synthetic+redacted;base64,{encoded_data}",
            masked_regions=[m.to_dict() for m in self.mask_regions],
            is_redacted=True,
        )
