"""
ZONATA Host Permission & Agent Framework (OpenCode Step 3B / 3C)
"""

from core.host.types import (
    GrantMode,
    GrantScope,
    DeviceStatus,
    HostSessionStatus,
    GrantEventType,
    DeviceRecord,
    HostGrantRecord,
    GrantEventRecord,
    HostSessionRecord,
    DENIED_BY_DEFAULT_APPS,
    HostSecurityViolation,
    OutOfGrantError,
    DeniedByDefaultError,
    ReplayDetectedError,
    StepUpAuthenticationRequiredError,
)
from core.host.pairing import PairingManager
from core.host.grants import HostGrantManager
from core.host.session import HostSessionManager
from core.host.perception import (
    BoundingRect,
    AccessibilityNode,
    AccessibilityTree,
    PerceptionLayer,
    PerceptionSnapshot,
    DesktopPerceptionEngine,
)
from core.host.interaction import (
    InteractionPrimitive,
    InteractionResult,
    OutOfGrantCoordinatesError,
    HumanPhysicalOverrideError,
    PhysicalSpeedThrottler,
    HumanOverrideDetector,
    DesktopInteractionDispatcher,
)
from core.host.agent import ZonataHostAgent

__all__ = [
    "GrantMode",
    "GrantScope",
    "DeviceStatus",
    "HostSessionStatus",
    "GrantEventType",
    "DeviceRecord",
    "HostGrantRecord",
    "GrantEventRecord",
    "HostSessionRecord",
    "DENIED_BY_DEFAULT_APPS",
    "HostSecurityViolation",
    "OutOfGrantError",
    "DeniedByDefaultError",
    "ReplayDetectedError",
    "StepUpAuthenticationRequiredError",
    "PairingManager",
    "HostGrantManager",
    "HostSessionManager",
    "BoundingRect",
    "AccessibilityNode",
    "AccessibilityTree",
    "PerceptionLayer",
    "PerceptionSnapshot",
    "DesktopPerceptionEngine",
    "InteractionPrimitive",
    "InteractionResult",
    "OutOfGrantCoordinatesError",
    "HumanPhysicalOverrideError",
    "PhysicalSpeedThrottler",
    "HumanOverrideDetector",
    "DesktopInteractionDispatcher",
    "ZonataHostAgent",
]
