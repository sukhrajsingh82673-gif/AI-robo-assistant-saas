"""
UI Consoles and UX Honesty verification package (Rule 84).
"""

from .dead_control_detector import DeadControlDetector, ControlElement, ControlAuditResult
from .tenant_console import TenantAdminConsole
from .operator_console import PlatformOperatorConsole

__all__ = [
    "DeadControlDetector",
    "ControlElement",
    "ControlAuditResult",
    "TenantAdminConsole",
    "PlatformOperatorConsole",
]
