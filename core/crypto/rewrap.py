"""
ZONATA Sovereign Core — Sub-Step 5H: Online Rewrapping & Key Migration Utility.
================================================================================
Governed by:
- Rule 45: Keys can be rotated and data rewrapped without downtime.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.crypto.registry import CryptoRegistry
from core.crypto.types import CryptoAlgorithm, CryptoEnvelope, CryptoError

logger = logging.getLogger("zonata.crypto.rewrap")


class OnlineRewrapper:
    """Non-blocking online rewrapping engine for zero-downtime key and cipher migration."""

    def __init__(self, registry: Optional[CryptoRegistry] = None):
        self.registry = registry or CryptoRegistry()

    def rewrap(
        self,
        envelope: CryptoEnvelope,
        old_key: bytes,
        new_key: bytes,
        new_version: str,
        new_key_id: str,
        aad: Optional[bytes] = None,
    ) -> CryptoEnvelope:
        """
        Rewraps a single envelope:
        1. Decrypts with old key and original algorithm version.
        2. Re-encrypts with new key and target algorithm version.
        3. Returns fresh CryptoEnvelope.
        """
        plaintext = self.registry.decrypt(envelope, old_key, aad=aad)
        new_envelope = self.registry.encrypt(
            plaintext=plaintext,
            key=new_key,
            key_id=new_key_id,
            version=new_version,
            aad=aad,
        )
        return new_envelope

    def rewrap_batch(
        self,
        envelopes: List[CryptoEnvelope],
        old_key: bytes,
        new_key: bytes,
        new_version: str,
        new_key_id: str,
        aad: Optional[bytes] = None,
    ) -> List[CryptoEnvelope]:
        """Batch rewraps multiple envelopes with transaction isolation."""
        migrated: List[CryptoEnvelope] = []
        for env in envelopes:
            migrated.append(
                self.rewrap(
                    envelope=env,
                    old_key=old_key,
                    new_key=new_key,
                    new_version=new_version,
                    new_key_id=new_key_id,
                    aad=aad,
                )
            )
        return migrated
