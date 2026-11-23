"""
ZONATA Browser Engine Types & Contracts (OpenCode Step 3E)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class ChallengeType(str, Enum):
    NONE = "NONE"
    CLOUDFLARE_TURNSTILE = "CLOUDFLARE_TURNSTILE"
    RECAPTCHA = "RECAPTCHA"
    HCAPTCHA = "HCAPTCHA"
    ARKOSE_LABS = "ARKOSE_LABS"
    BOTGUARD = "BOTGUARD"
    QUEUE_IT = "QUEUE_IT"


@dataclass
class ChallengeDetectionResult:
    has_challenge: bool
    challenge_type: ChallengeType
    signatures_detected: List[str]
    detected_at: float = field(default_factory=time.time)
    hand_off_required: bool = True
    masked_widget_bounds: Optional[Dict[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_challenge": self.has_challenge,
            "challenge_type": self.challenge_type.value,
            "signatures_detected": self.signatures_detected,
            "detected_at": self.detected_at,
            "hand_off_required": self.hand_off_required,
            "masked_widget_bounds": self.masked_widget_bounds,
        }


@dataclass
class BrowserDownloadResult:
    download_id: str
    filename: str
    extension: str
    byte_size: int
    sha256: str
    clamav_scanned: bool
    is_infected: bool
    is_executable: bool
    execution_permitted: bool
    retention_status: str
    rejection_reason: Optional[str] = None
    quarantine_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "download_id": self.download_id,
            "filename": self.filename,
            "extension": self.extension,
            "byte_size": self.byte_size,
            "sha256": self.sha256,
            "clamav_scanned": self.clamav_scanned,
            "is_infected": self.is_infected,
            "is_executable": self.is_executable,
            "execution_permitted": self.execution_permitted,
            "retention_status": self.retention_status,
            "rejection_reason": self.rejection_reason,
            "quarantine_id": self.quarantine_id,
        }
