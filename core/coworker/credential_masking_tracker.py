"""
ZONATA Autonomous Executive Coworker — Milestone 3: Credential Masking Tracker
Implements salted HMAC-SHA256 cryptographic origin tracing without storing plaintext secrets.
"""

from __future__ import annotations
import hmac
import hashlib
import time
import os
from typing import Dict, List, Optional, Any, Tuple


class CredentialMaskingTracker:
    """
    Zero-Knowledge Origin Tracker for credentials and secrets.
    Computes deterministic HMAC fingerprints with a system salt to track leakage origin.
    """

    def __init__(self, salt: Optional[bytes] = None):
        self.salt = salt or os.environ.get("DLP_HMAC_SALT", "zonata-dlp-salt-default-sec").encode("utf-8")
        self._fingerprint_registry: Dict[str, Dict[str, Any]] = {}

    def mask_and_register_secret(
        self,
        raw_secret: str,
        channel: str,
        origin_actor: str,
        category: str = "CREDENTIAL"
    ) -> str:
        """
        Generates a non-reversible cryptographic fingerprint and registers origin lineage.
        Returns the safe replacement token: [REDACTED:FP:<fingerprint>]
        """
        if not raw_secret:
            return ""

        fp = hmac.new(self.salt, raw_secret.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        mask_token = f"[REDACTED:FP:{fp}]"

        self._fingerprint_registry[fp] = {
            "fingerprint": fp,
            "channel": channel,
            "origin_actor": origin_actor,
            "category": category,
            "secret_length": len(raw_secret),
            "first_seen": time.time()
        }
        return mask_token

    def trace_origin(self, text_containing_mask: str) -> List[Dict[str, Any]]:
        """
        Parses text for mask tokens and returns registered origin audit metadata.
        """
        traces = []
        for fp, meta in self._fingerprint_registry.items():
            if f"[REDACTED:FP:{fp}]" in text_containing_mask:
                traces.append(meta)
        return traces

    def get_fingerprint_count(self) -> int:
        return len(self._fingerprint_registry)
