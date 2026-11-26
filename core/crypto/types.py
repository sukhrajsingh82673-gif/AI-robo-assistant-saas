"""
ZONATA Sovereign Core — Sub-Step 5H: Cryptographic Agility Types & Envelopes.
============================================================================
Governed by:
- Rule 45: Crypto agility. No hardcoded algorithm or key size outside the single
  crypto module; ciphertexts and signatures carry a version; keys can be rotated
  and data rewrapped without downtime.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class CryptoAlgorithm(str, Enum):
    V1_AES256_GCM = "v1-aes256gcm"
    V2_CHACHA20_POLY1305 = "v2-chacha20poly1305"
    V3_KYBER_AES256_GCM = "v3-kyber-aes256gcm"


class CryptoError(Exception):
    """Base exception for all cryptographic failures."""
    pass


class AuthenticationTagVerificationError(CryptoError):
    """Raised when an AEAD authentication tag check fails (data tampering detected)."""
    pass


class UnsupportedAlgorithmError(CryptoError):
    """Raised when an envelope requests an unknown or unapproved algorithm version."""
    pass


@dataclass
class CryptoEnvelope:
    """
    Sovereign versioned ciphertext envelope under Rule 45.
    Explicitly carries version, key reference, IV/nonce, authentication tag,
    ciphertext payload, and optional PQC hybrid KEM ciphertext.
    """
    version: str
    key_id: str
    iv: str  # Base64 encoded IV / Nonce
    tag: str  # Base64 encoded AEAD tag
    ciphertext: str  # Base64 encoded ciphertext
    kem_ciphertext: Optional[str] = None  # Base64 encoded KEM shared secret ciphertext
    aad: Optional[str] = None  # Base64 encoded authenticated data
    created_at: float = field(default_factory=time.time)

    def serialize(self) -> str:
        """Serializes envelope to canonical JSON string format."""
        payload = {
            "v": self.version,
            "kid": self.key_id,
            "iv": self.iv,
            "tag": self.tag,
            "ct": self.ciphertext,
            "created_at": self.created_at,
        }
        if self.kem_ciphertext:
            payload["kem_ct"] = self.kem_ciphertext
        if self.aad:
            payload["aad"] = self.aad
        return json.dumps(payload, sort_keys=True)

    @classmethod
    def deserialize(cls, raw: str) -> CryptoEnvelope:
        """Parses envelope from canonical JSON or versioned token string."""
        raw = raw.strip()
        if raw.startswith("{") and raw.endswith("}"):
            try:
                data = json.loads(raw)
                return cls(
                    version=data["v"],
                    key_id=data["kid"],
                    iv=data["iv"],
                    tag=data["tag"],
                    ciphertext=data["ct"],
                    kem_ciphertext=data.get("kem_ct"),
                    aad=data.get("aad"),
                    created_at=data.get("created_at", time.time()),
                )
            except Exception as e:
                raise CryptoError(f"Malformed JSON crypto envelope: {e}")

        # String format: enc:{version}:{key_id}:{iv}:{tag}:{ciphertext}
        parts = raw.split(":")
        if len(parts) == 6 and parts[0] == "enc":
            return cls(
                version=parts[1],
                key_id=parts[2],
                iv=parts[3],
                tag=parts[4],
                ciphertext=parts[5],
            )
        raise CryptoError(f"Unrecognized crypto envelope format: {raw[:30]}...")
