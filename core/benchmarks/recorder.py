"""
Human Baseline Telemetry Recorder with Consent Verification & PII Scrubbing (Rule 69 & ADR 0045)
Records Config A participant performance with irreversible pseudonymization and ethical consent safeguards.
"""

from typing import Dict, Any, List, Optional
import hashlib
import hmac
import json
import re
import time
import datetime


class ParticipantConsentMissingError(PermissionError):
    """Raised when telemetry recording is attempted without verified human participant consent."""
    pass


# Scrubbing regex patterns
PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD]"),
    (re.compile(r"\b(?:password|secret|token)\s*[:= ]\s*\S+", re.IGNORECASE), "[REDACTED_CREDENTIAL]"),
    (re.compile(r"\bbearer\s+[A-Za-z0-9_\-\.]+\b", re.IGNORECASE), "[REDACTED_CREDENTIAL]"),
    (re.compile(r"\b(?:password|secret)\b", re.IGNORECASE), "[REDACTED_CREDENTIAL]"),
]


class HumanBaselineRecorder:
    """Manages telemetry collection for Config A human baseline trials."""

    def __init__(self, salt: bytes = b"zonata-pseudonymization-salt-2026"):
        self.salt = salt
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def pseudonymize_participant(self, real_participant_id: str) -> str:
        """Deterministically derives an irreversible pseudonym from participant identifier."""
        return "PSEUDO-" + hmac.new(self.salt, real_participant_id.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    @classmethod
    def scrub_pii(cls, text: str) -> str:
        """Removes PII, contact info, and credentials from captured telemetry traces."""
        scrubbed = text
        for pattern, replacement in PII_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    def start_session(
        self,
        session_id: str,
        real_participant_id: str,
        task_id: str,
        domain_code: str,
        consent_given: bool = False,
    ) -> Dict[str, Any]:
        """Initiates a baseline measurement session. Enforces informed consent."""
        if not consent_given:
            raise ParticipantConsentMissingError(
                f"PARTICIPANT_CONSENT_MISSING: Recording telemetry for participant '{real_participant_id}' "
                f"requires explicit informed consent under Rule 69 and ADR 0045."
            )

        pseudo_id = self.pseudonymize_participant(real_participant_id)
        session = {
            "session_id": session_id,
            "pseudo_participant_id": pseudo_id,
            "task_id": task_id,
            "domain_code": domain_code,
            "start_monotonic": time.monotonic(),
            "start_wallclock": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "actions_count": 0,
            "action_log": [],
            "status": "IN_PROGRESS",
        }
        self._sessions[session_id] = session
        return {"session_id": session_id, "pseudo_participant_id": pseudo_id, "status": "RECORDING"}

    def log_action(self, session_id: str, action_type: str, raw_payload: str):
        """Logs an action with scrubbed payload text."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found")

        session = self._sessions[session_id]
        clean_payload = self.scrub_pii(raw_payload)
        session["actions_count"] += 1
        session["action_log"].append({
            "action_num": session["actions_count"],
            "action_type": action_type,
            "payload_scrubbed": clean_payload,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

    def complete_session(
        self,
        session_id: str,
        is_success: bool,
        error_count: int = 0
    ) -> Dict[str, Any]:
        """Finalizes baseline trial and calculates total wall-clock duration."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found")

        session = self._sessions[session_id]
        elapsed_sec = time.monotonic() - session["start_monotonic"]

        session["status"] = "COMPLETED" if is_success else "FAILED"
        session["duration_seconds"] = round(elapsed_sec, 3)
        session["error_count"] = error_count
        session["end_wallclock"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Generate tamper seal over session
        summary = {
            "session_id": session_id,
            "pseudo_id": session["pseudo_participant_id"],
            "task_id": session["task_id"],
            "duration_seconds": session["duration_seconds"],
            "actions_count": session["actions_count"],
            "is_success": is_success,
            "error_count": error_count,
        }
        session["session_seal_sha256"] = hashlib.sha256(
            json.dumps(summary, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return session
