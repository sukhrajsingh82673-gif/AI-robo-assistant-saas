"""
ZONATA Sovereign Core — Terminal Package.
"""

from core.terminal.classifier import CommandClassifier
from core.terminal.types import (
    CommandTier,
    DangerousCommandForbiddenError,
    HighImpactApprovalRequiredError,
    TerminalCommandResult,
    TerminalDisabledError,
)

__all__ = [
    "CommandClassifier",
    "CommandTier",
    "DangerousCommandForbiddenError",
    "HighImpactApprovalRequiredError",
    "TerminalCommandResult",
    "TerminalDisabledError",
]
