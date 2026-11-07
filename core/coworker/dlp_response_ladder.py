"""
ZONATA Autonomous Executive Coworker — Milestone 3: DLP 4-Tier Response Ladder
Tier 1 (LOW): Allow & Audit
Tier 2 (MEDIUM): Redact & Warn & Continue
Tier 3 (HIGH): Sanitize & Block Sensitive Transfer & Continue Safe Portion
Tier 4 (CRITICAL): Quarantine & Halt & Alert CEO
"""

from __future__ import annotations
import time
from typing import Dict, List, Optional, Any
from .dlp_engine import DLPRiskLevel, DLPScanResult


class DLPResponseLadder:
    """Applies governed remediation response based on DLP risk level."""

    def __init__(self, ceo_alert_callback: Optional[Any] = None):
        self.ceo_alert_callback = ceo_alert_callback
        self.incident_history: List[Dict[str, Any]] = []

    def evaluate_response(self, scan_result: DLPScanResult, context_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        risk = scan_result.highest_risk

        if risk == DLPRiskLevel.LOW:
            return {
                "decision": "ALLOW",
                "risk_tier": "LOW",
                "action": "AUDIT_ONLY",
                "payload": scan_result.sanitized_text,
                "quarantined": False
            }

        elif risk == DLPRiskLevel.MEDIUM:
            return {
                "decision": "REDACT_AND_CONTINUE",
                "risk_tier": "MEDIUM",
                "action": "MASK_AND_WARN",
                "payload": scan_result.sanitized_text,
                "warnings": [f"DLP finding detected ({len(scan_result.findings)} items) - sanitized automatically."],
                "quarantined": False
            }

        elif risk == DLPRiskLevel.HIGH:
            return {
                "decision": "SANITIZE_AND_RESTRICT",
                "risk_tier": "HIGH",
                "action": "BLOCK_TRANSFER_ALLOW_SAFE_PORTION",
                "payload": scan_result.sanitized_text,
                "warnings": ["High-risk secret or token blocked from transmission."],
                "quarantined": False
            }

        else: # CRITICAL
            incident = {
                "decision": "QUARANTINE_AND_HALT",
                "risk_tier": "CRITICAL",
                "action": "HALT_EXECUTION_ALERT_CEO",
                "findings": [f.snippet_masked for f in scan_result.findings],
                "quarantined": True,
                "timestamp": time.time(),
                "context": context_meta or {}
            }
            self.incident_history.append(incident)
            if self.ceo_alert_callback:
                try:
                    self.ceo_alert_callback(incident)
                except Exception:
                    pass
            return incident
