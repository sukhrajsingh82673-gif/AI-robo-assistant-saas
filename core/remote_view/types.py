"""
ZONATA Sovereign Core — Remote View & Human Takeover Contracts (OpenCode Step 3G).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RemoteTargetType(str, Enum):
    BROWSER_TAB = "BROWSER_TAB"
    HOST_DESKTOP = "HOST_DESKTOP"


class TakeoverState(str, Enum):
    AGENT_ACTIVE = "AGENT_ACTIVE"
    HUMAN_TAKEOVER_ACTIVE = "HUMAN_TAKEOVER_ACTIVE"
    HANDBACK_PENDING = "HANDBACK_PENDING"
    SESSION_CLOSED = "SESSION_CLOSED"


class TakeoverEventType(str, Enum):
    TAKEOVER_INITIATED = "TAKEOVER_INITIATED"
    HUMAN_INTERACTION = "HUMAN_INTERACTION"
    CONTROL_RELEASED = "CONTROL_RELEASED"
    ABORTED = "ABORTED"


class AgentExecutionSuppressedError(Exception):
    """Raised when agent attempts interaction while human has taken over controls."""
    pass


@dataclass(frozen=True)
class ViewportBounds:
    x: int
    y: int
    width: int
    height: int

    def contains(self, px: int, py: int) -> bool:
        return (
            self.x <= px <= (self.x + self.width)
            and self.y <= py <= (self.y + self.height)
        )

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True)
class MaskRegion:
    x: int
    y: int
    width: int
    height: int
    reason: str  # "SECRET_INPUT", "CHALLENGE_WIDGET", "OUT_OF_GRANT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FramePacket:
    session_id: str
    frame_index: int
    timestamp: float
    viewport: Dict[str, int]
    image_base64: str
    masked_regions: List[Dict[str, Any]]
    is_redacted: bool = True


@dataclass
class TakeoverHandbackAssertion:
    session_id: str
    human_principal_id: str
    status_asserted: str  # e.g. "CHALLENGE_SOLVED", "LOGIN_AUTHENTICATED", "CONFIRMATION_GRANTED"
    notes: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "human_principal_id": self.human_principal_id,
            "status_asserted": self.status_asserted,
            "notes": self.notes,
            "created_at": self.created_at,
        }
