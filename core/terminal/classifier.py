"""
ZONATA Terminal — Command Classifier & Deny-List Guard (Rule 27, Rule 31, Rule 32).

Enforces strict command safety tiers and rejects dangerous execution patterns.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from core.terminal.types import CommandTier, DangerousCommandForbiddenError


# Strictly forbidden commands & patterns (Rule 3)
FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bsu\b\s+", re.IGNORECASE),
    re.compile(r"curl\s+[^|]+\|\s*(sh|bash|zsh)", re.IGNORECASE),
    re.compile(r"wget\s+[^|]+\|\s*(sh|bash|zsh)", re.IGNORECASE),
    re.compile(r"\brm\s+(-rf?|-fr?)\s+(/|/\*|~|\$HOME)", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\|\:&\s*\}\s*;\s*:", re.IGNORECASE),  # fork bomb
    re.compile(r"\b(nc|netcat)\s+.*-e\b", re.IGNORECASE),            # reverse shell
    re.compile(r"/etc/(passwd|shadow|sudoers)", re.IGNORECASE),
]

# High-impact commands requiring human approval (Rule 27 & 31)
HIGH_IMPACT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\brm\b"),
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bchmod\b"),
    re.compile(r"\bchown\b"),
    re.compile(r"\bsystemctl\b"),
    re.compile(r"\bkill\b"),
    re.compile(r"\bpkill\b"),
    re.compile(r"\bkillall\b"),
    re.compile(r"\bdropdb\b"),
    re.compile(r"\bshutdown\b"),
    re.compile(r"\breboot\b"),
]

# Known safe read-only commands
SAFE_READ_ONLY_PREFIXES = (
    "ls", "dir", "pwd", "cat", "head", "tail", "grep", "find",
    "git status", "git log", "git diff", "git show", "echo",
    "uname", "whoami", "date", "uptime", "wc", "env"
)


class CommandClassifier:
    """
    Analyzes terminal commands and classifies them into governance safety tiers.
    """

    @classmethod
    def classify(cls, command: str) -> CommandTier:
        cmd_clean = command.strip()

        # 1. Deny forbidden dangerous commands immediately
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(cmd_clean):
                return CommandTier.FORBIDDEN_DENIED

        # 2. Check high-impact actions
        for pat in HIGH_IMPACT_PATTERNS:
            if pat.search(cmd_clean):
                return CommandTier.HIGH_IMPACT

        # 3. Check safe read-only commands
        cmd_lower = cmd_clean.lower()
        for prefix in SAFE_READ_ONLY_PREFIXES:
            if cmd_lower == prefix or cmd_lower.startswith(prefix + " "):
                # Ensure no pipe to dangerous commands
                if "|" not in cmd_lower and ">" not in cmd_lower:
                    return CommandTier.SAFE_READ_ONLY

        # Default mutating / general command
        return CommandTier.MUTATING_SAFE
