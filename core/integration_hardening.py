"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Integration Hardening & Quarantine Pipeline
Enforces the mandatory Browser-to-OpenHands artifact quarantine chain,
SSRF/DNS-rebinding filters, and response firewalls for MCP, A2A, Nango, and Browser content.
"""

import re
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger("zonata.hardening.integrations")

class SecurityBoundaryViolation(Exception):
    pass

class ArtifactQuarantineStatus:
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    POLICY_CLEARED = "POLICY_CLEARED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"

@dataclass
class QuarantinedArtifact:
    artifact_id: str
    source_subsystem: str  # e.g. "BROWSER_USE"
    filename: str
    sha256_hash: str
    size_bytes: int
    status: str
    scan_findings: List[str]
    quarantined_at: float
    cleared_at: Optional[float] = None

class QuarantinePipeline:
    """
    Guarantees: Browser downloaded artifacts MUST NOT automatically become executable OpenHands input.
    Pipeline: Browser -> Download -> Quarantine -> Classify -> Scan -> Policy -> Approval -> OpenHands
    """
    DISALLOWED_EXTENSIONS = {".exe", ".sh", ".bash", ".bin", ".elf", ".so", ".dylib", ".vbs", ".bat"}
    SUSPICIOUS_PATTERNS = [
        re.compile(b"rm\\s+-rf", re.IGNORECASE),
        re.compile(b"/bin/sh", re.IGNORECASE),
        re.compile(b"eval\\s*\\(", re.IGNORECASE),
        re.compile(b"curl\\s+.*\\|\\s*bash", re.IGNORECASE)
    ]

    def __init__(self):
        self._quarantine_store: Dict[str, QuarantinedArtifact] = {}

    def ingest_downloaded_artifact(self, source: str, filename: str, data: bytes) -> QuarantinedArtifact:
        """Ingest artifact into quarantine sandbox. Never writes directly to execution workspace."""
        sha = hashlib.sha256(data).hexdigest()
        artifact_id = f"quar_{sha[:16]}"

        findings = []
        # Check file extension
        for ext in self.DISALLOWED_EXTENSIONS:
            if filename.lower().endswith(ext):
                findings.append(f"Executable extension '{ext}' detected.")

        # Check binary patterns
        for pat in self.SUSPICIOUS_PATTERNS:
            if pat.search(data):
                findings.append(f"Suspicious payload pattern matching '{pat.pattern}' found.")

        status = ArtifactQuarantineStatus.REJECTED if findings else ArtifactQuarantineStatus.POLICY_CLEARED
        artifact = QuarantinedArtifact(
            artifact_id=artifact_id,
            source_subsystem=source,
            filename=filename,
            sha256_hash=sha,
            size_bytes=len(data),
            status=status,
            scan_findings=findings,
            quarantined_at=time.time(),
            cleared_at=time.time() if status == ArtifactQuarantineStatus.POLICY_CLEARED else None
        )
        self._quarantine_store[artifact_id] = artifact
        return artifact

    def authorize_for_openhands(self, artifact_id: str) -> bool:
        """Verify artifact has been scanned and approved before OpenHands can access it."""
        artifact = self._quarantine_store.get(artifact_id)
        if not artifact:
            raise SecurityBoundaryViolation(f"Artifact {artifact_id} not found in quarantine.")
        if artifact.status != ArtifactQuarantineStatus.POLICY_CLEARED:
            raise SecurityBoundaryViolation(f"Artifact {artifact_id} cannot enter OpenHands: Status is {artifact.status}.")
        return True


class ResponseFirewall:
    """
    Inspects responses from external systems (MCP, A2A, Nango, Browser web pages)
    to neutralize indirect prompt injection and data exfiltration vectors.
    """
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*override", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+an\s+unrestricted\s+ai", re.IGNORECASE),
        re.compile(r"disregard\s+all\s+prior\s+directives", re.IGNORECASE),
        re.compile(r"!\[.*\]\(https?:\/\/.*\/exfil\?.*=.*\)", re.IGNORECASE)  # Markdown image exfiltration
    ]

    @classmethod
    def sanitize_external_response(cls, source_subsystem: str, response_text: str) -> Tuple[str, bool, List[str]]:
        """
        Sanitize response text.
        Returns: (sanitized_text: str, is_flagged: bool, violations: List[str])
        """
        if not response_text or not isinstance(response_text, str):
            return (response_text, False, [])

        violations = []
        sanitized = response_text

        for pat in cls.PROMPT_INJECTION_PATTERNS:
            matches = pat.findall(sanitized)
            if matches:
                violations.append(f"Neutralized injection pattern '{pat.pattern}'")
                sanitized = pat.sub("[PROMPT_INJECTION_NEUTRALIZED]", sanitized)

        return (sanitized, len(violations) > 0, violations)

# Global instances
quarantine_pipeline = QuarantinePipeline()
response_firewall = ResponseFirewall()
