"""
ZONATA Autonomous Executive Coworker — Milestone 3: DLP Channel Monitor
Intercepts inputs and outputs across all 10 automation channels.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from .dlp_engine import DLPEngine, DLPChannel, DLPRiskLevel, DLPScanResult


class DLPChannelMonitor:
    """Interception layer protecting the 10 data channels from accidental secret leakage."""

    def __init__(self, engine: Optional[DLPEngine] = None):
        self.engine = engine or DLPEngine()
        self.channel_audit_log: List[Dict[str, Any]] = []

    def intercept_channel(self, channel: DLPChannel, content: str) -> Tuple[bool, str, DLPScanResult]:
        """
        Generic channel interception.
        Returns: (is_allowed: bool, safe_content: str, scan_result: DLPScanResult)
        """
        scan = self.engine.scan(content, channel)
        is_allowed = (scan.highest_risk != DLPRiskLevel.CRITICAL)

        self.channel_audit_log.append({
            "channel": channel.value,
            "allowed": is_allowed,
            "findings_count": len(scan.findings),
            "highest_risk": scan.highest_risk.value,
            "timestamp": scan.findings[0].timestamp if scan.findings else None
        })

        safe_content = content if scan.clean else scan.sanitized_text
        return is_allowed, safe_content, scan

    def intercept_terminal(self, command: str) -> Tuple[bool, str]:
        allowed, safe, _ = self.intercept_channel(DLPChannel.TERMINAL_COMMAND, command)
        return allowed, safe

    def intercept_llm_prompt(self, messages: List[Dict[str, str]]) -> Tuple[bool, List[Dict[str, str]]]:
        all_allowed = True
        sanitized_messages = []
        for m in messages:
            allowed, safe_text, _ = self.intercept_channel(DLPChannel.LLM_PROMPT, m.get("content", ""))
            if not allowed:
                all_allowed = False
            sanitized_messages.append({**m, "content": safe_text})
        return all_allowed, sanitized_messages

    def intercept_file_write(self, file_path: str, content: str) -> Tuple[bool, str]:
        return self.intercept_channel(DLPChannel.FILE_WRITE, content)[:2]
