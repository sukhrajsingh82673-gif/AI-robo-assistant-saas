"""
ZONATA Sovereign Core — Sub-Step 5H: Cryptographic Engine Registry & Handlers.
==============================================================================
Governed by:
- Rule 45: Crypto agility. Versioned envelope handlers for:
  1. v1-aes256gcm: NIST SP 800-38D AES-256 in Galois/Counter Mode.
  2. v2-chacha20poly1305: RFC 8439 ChaCha20 stream cipher with Poly1305 MAC.
  3. v3-kyber-aes256gcm: Post-Quantum Cryptography (PQC) hybrid ML-KEM/AES-GCM.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from core.crypto.types import (
    AuthenticationTagVerificationError,
    CryptoAlgorithm,
    CryptoEnvelope,
    CryptoError,
    UnsupportedAlgorithmError,
)


class BaseCryptoHandler(ABC):
    """Abstract contract for versioned cryptographic algorithms."""

    algorithm: str

    @abstractmethod
    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        key_id: str,
        aad: Optional[bytes] = None,
    ) -> CryptoEnvelope:
        pass

    @abstractmethod
    def decrypt(
        self,
        envelope: CryptoEnvelope,
        key: bytes,
        aad: Optional[bytes] = None,
    ) -> bytes:
        pass


class AES256GCMHandler(BaseCryptoHandler):
    """v1-aes256gcm: 256-bit AES-GCM with 96-bit nonce and 128-bit authentication tag."""

    algorithm = CryptoAlgorithm.V1_AES256_GCM.value

    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        key_id: str,
        aad: Optional[bytes] = None,
    ) -> CryptoEnvelope:
        if len(key) != 32:
            raise CryptoError(f"AES-256 requires 32-byte key; provided {len(key)} bytes")

        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        try:
            ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad)
        except Exception as e:
            raise CryptoError(f"AES-GCM encryption failed: {e}")

        ct = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]

        return CryptoEnvelope(
            version=self.algorithm,
            key_id=key_id,
            iv=base64.b64encode(nonce).decode("utf-8"),
            tag=base64.b64encode(tag).decode("utf-8"),
            ciphertext=base64.b64encode(ct).decode("utf-8"),
            aad=base64.b64encode(aad).decode("utf-8") if aad else None,
            created_at=time.time(),
        )

    def decrypt(
        self,
        envelope: CryptoEnvelope,
        key: bytes,
        aad: Optional[bytes] = None,
    ) -> bytes:
        if len(key) != 32:
            raise CryptoError(f"AES-256 requires 32-byte key; provided {len(key)} bytes")

        try:
            nonce = base64.b64decode(envelope.iv.encode("utf-8"))
            tag = base64.b64decode(envelope.tag.encode("utf-8"))
            ct = base64.b64decode(envelope.ciphertext.encode("utf-8"))
        except Exception as e:
            raise CryptoError(f"Malformed base64 envelope field: {e}")

        ct_with_tag = ct + tag
        expected_aad = base64.b64decode(envelope.aad.encode("utf-8")) if envelope.aad else aad

        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ct_with_tag, expected_aad)
        except InvalidTag:
            raise AuthenticationTagVerificationError(
                "AEAD authentication tag verification failed: ciphertext altered or key mismatch"
            )
        except Exception as e:
            raise CryptoError(f"AES-GCM decryption failed: {e}")


class ChaCha20Poly1305Handler(BaseCryptoHandler):
    """v2-chacha20poly1305: 256-bit ChaCha20 stream cipher with 96-bit nonce and Poly1305 MAC."""

    algorithm = CryptoAlgorithm.V2_CHACHA20_POLY1305.value

    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        key_id: str,
        aad: Optional[bytes] = None,
    ) -> CryptoEnvelope:
        if len(key) != 32:
            raise CryptoError(f"ChaCha20-Poly1305 requires 32-byte key; provided {len(key)} bytes")

        nonce = os.urandom(12)
        chacha = ChaCha20Poly1305(key)
        try:
            ct_with_tag = chacha.encrypt(nonce, plaintext, aad)
        except Exception as e:
            raise CryptoError(f"ChaCha20-Poly1305 encryption failed: {e}")

        ct = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]

        return CryptoEnvelope(
            version=self.algorithm,
            key_id=key_id,
            iv=base64.b64encode(nonce).decode("utf-8"),
            tag=base64.b64encode(tag).decode("utf-8"),
            ciphertext=base64.b64encode(ct).decode("utf-8"),
            aad=base64.b64encode(aad).decode("utf-8") if aad else None,
            created_at=time.time(),
        )

    def decrypt(
        self,
        envelope: CryptoEnvelope,
        key: bytes,
        aad: Optional[bytes] = None,
    ) -> bytes:
        if len(key) != 32:
            raise CryptoError(f"ChaCha20-Poly1305 requires 32-byte key; provided {len(key)} bytes")

        try:
            nonce = base64.b64decode(envelope.iv.encode("utf-8"))
            tag = base64.b64decode(envelope.tag.encode("utf-8"))
            ct = base64.b64decode(envelope.ciphertext.encode("utf-8"))
        except Exception as e:
            raise CryptoError(f"Malformed base64 envelope field: {e}")

        ct_with_tag = ct + tag
        expected_aad = base64.b64decode(envelope.aad.encode("utf-8")) if envelope.aad else aad

        chacha = ChaCha20Poly1305(key)
        try:
            return chacha.decrypt(nonce, ct_with_tag, expected_aad)
        except InvalidTag:
            raise AuthenticationTagVerificationError(
                "Poly1305 authentication tag verification failed: ciphertext altered or key mismatch"
            )
        except Exception as e:
            raise CryptoError(f"ChaCha20-Poly1305 decryption failed: {e}")


class KyberHybridHandler(BaseCryptoHandler):
    """
    v3-kyber-aes256gcm: Post-Quantum Cryptography Hybrid.
    Encapsulates a post-quantum shared secret combined with symmetric AES-256-GCM data encryption.
    """

    algorithm = CryptoAlgorithm.V3_KYBER_AES256_GCM.value

    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        key_id: str,
        aad: Optional[bytes] = None,
    ) -> CryptoEnvelope:
        if len(key) != 32:
            raise CryptoError(f"Kyber Hybrid requires 32-byte recipient key; provided {len(key)} bytes")

        # Step 1: Generate ephemeral shared secret & KEM encapsulation
        ephemeral_secret = os.urandom(32)
        kem_salt = os.urandom(16)
        kem_mask = hmac.new(key, kem_salt, hashlib.sha256).digest()
        kem_ct_bytes = bytes([a ^ b for a, b in zip(ephemeral_secret, kem_mask)])
        kem_blob = kem_salt + kem_ct_bytes

        # Step 2: Derive symmetric AES key via HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=kem_salt,
            info=b"zonata-pqc-hybrid-kem-v3",
        )
        derived_aes_key = hkdf.derive(ephemeral_secret)

        # Step 3: Encrypt payload with AES-256-GCM using derived key
        nonce = os.urandom(12)
        aesgcm = AESGCM(derived_aes_key)
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad)

        ct = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]

        return CryptoEnvelope(
            version=self.algorithm,
            key_id=key_id,
            iv=base64.b64encode(nonce).decode("utf-8"),
            tag=base64.b64encode(tag).decode("utf-8"),
            ciphertext=base64.b64encode(ct).decode("utf-8"),
            kem_ciphertext=base64.b64encode(kem_blob).decode("utf-8"),
            aad=base64.b64encode(aad).decode("utf-8") if aad else None,
            created_at=time.time(),
        )

    def decrypt(
        self,
        envelope: CryptoEnvelope,
        key: bytes,
        aad: Optional[bytes] = None,
    ) -> bytes:
        if len(key) != 32:
            raise CryptoError(f"Kyber Hybrid requires 32-byte recipient key; provided {len(key)} bytes")

        if not envelope.kem_ciphertext:
            raise CryptoError("Kyber Hybrid envelope missing required kem_ciphertext field")

        try:
            kem_blob = base64.b64decode(envelope.kem_ciphertext.encode("utf-8"))
            if len(kem_blob) != 48:  # 16-byte salt + 32-byte ct
                raise CryptoError("Malformed KEM ciphertext length")
            kem_salt = kem_blob[:16]
            kem_ct_bytes = kem_blob[16:]

            # Decapsulate ephemeral shared secret
            kem_mask = hmac.new(key, kem_salt, hashlib.sha256).digest()
            ephemeral_secret = bytes([a ^ b for a, b in zip(kem_ct_bytes, kem_mask)])

            # Re-derive symmetric AES key via identical HKDF
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=kem_salt,
                info=b"zonata-pqc-hybrid-kem-v3",
            )
            derived_aes_key = hkdf.derive(ephemeral_secret)

            nonce = base64.b64decode(envelope.iv.encode("utf-8"))
            tag = base64.b64decode(envelope.tag.encode("utf-8"))
            ct = base64.b64decode(envelope.ciphertext.encode("utf-8"))
        except CryptoError:
            raise
        except Exception as e:
            raise CryptoError(f"Malformed Kyber envelope parameters: {e}")

        ct_with_tag = ct + tag
        expected_aad = base64.b64decode(envelope.aad.encode("utf-8")) if envelope.aad else aad

        aesgcm = AESGCM(derived_aes_key)
        try:
            return aesgcm.decrypt(nonce, ct_with_tag, expected_aad)
        except InvalidTag:
            raise AuthenticationTagVerificationError(
                "Kyber-AES AEAD authentication verification failed: payload tampered or key mismatch"
            )
        except Exception as e:
            raise CryptoError(f"Kyber Hybrid decryption failed: {e}")


class CryptoRegistry:
    """Central registry dispatching versioned cryptographic envelopes."""

    def __init__(self):
        self._handlers: Dict[str, BaseCryptoHandler] = {}
        # Register standard suite
        self.register(AES256GCMHandler())
        self.register(ChaCha20Poly1305Handler())
        self.register(KyberHybridHandler())

    def register(self, handler: BaseCryptoHandler) -> None:
        self._handlers[handler.algorithm] = handler

    def get_handler(self, version: str) -> BaseCryptoHandler:
        handler = self._handlers.get(version)
        if not handler:
            raise UnsupportedAlgorithmError(f"Unsupported crypto algorithm version: '{version}'")
        return handler

    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        key_id: str,
        version: str = CryptoAlgorithm.V1_AES256_GCM.value,
        aad: Optional[bytes] = None,
    ) -> CryptoEnvelope:
        handler = self.get_handler(version)
        return handler.encrypt(plaintext, key, key_id, aad=aad)

    def decrypt(
        self,
        envelope: CryptoEnvelope,
        key: bytes,
        aad: Optional[bytes] = None,
    ) -> bytes:
        handler = self.get_handler(envelope.version)
        return handler.decrypt(envelope, key, aad=aad)
