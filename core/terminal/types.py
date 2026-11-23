"""
ZONATA Sovereign Core — Terminal Types & Contracts (OpenCode Step 3I).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from core.ports.base import ProviderResult


class CommandTier(str, Enum):
    SAFE_READ_ONLY = "SAFE_READ_ONLY"
    MUTATING_SAFE = "MUTATING_SAFE"
    HIGH_IMPACT = "HIGH_IMPACT"
    FORBIDDEN_DENIED = "FORBIDDEN_DENIED"


class DangerousCommandForbiddenError(Exception):
    """Raised when a forbidden command (e.g. sudo, curl | sh, rm -rf /) is attempted."""
    pass


class TerminalDisabledError(Exception):
    """Raised when terminal execution is attempted while TERMINAL_ENABLED=0."""
    pass


class HighImpactApprovalRequiredError(Exception):
    """Raised when high-impact commands (e.g. rm, git push) lack human approval."""
    pass


@dataclass
class TerminalCommandResult(ProviderResult):
    command: str = ""
    tier: CommandTier = CommandTier.SAFE_READ_ONLY
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    delimited_output: str = ""
    killed_by_signal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "tier": self.tier.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "delimited_output": self.delimited_output,
            "killed_by_signal": self.killed_by_signal,
        }
