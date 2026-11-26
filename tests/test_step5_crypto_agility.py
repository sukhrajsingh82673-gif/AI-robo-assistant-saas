"""
Unit and Contract Tests for Step 5H: Crypto Agility & Future-Proofing.
======================================================================
Tests:
- v1-aes256gcm AEAD authenticated encryption/decryption.
- v2-chacha20poly1305 AEAD authenticated encryption/decryption.
- v3-kyber-aes256gcm Post-Quantum Cryptography hybrid KEM.
- Fail-closed tamper detection (AuthenticationTagVerificationError).
- CryptoEnvelope serialization and deserialization.
- OnlineRewrapper zero-downtime key and cipher migration.
- Rule 45: Unsupported algorithms rejected fail closed.
"""

import base64
import os
import pytest

from core.crypto.registry import CryptoRegistry
from core.crypto.rewrap import OnlineRewrapper
from core.crypto.types import (
    AuthenticationTagVerificationError,
    CryptoAlgorithm,
    CryptoEnvelope,
    CryptoError,
    UnsupportedAlgorithmError,
)


@pytest.fixture
def crypto_reg():
    return CryptoRegistry()


@pytest.fixture
def rewrapper(crypto_reg):
    return OnlineRewrapper(registry=crypto_reg)


class TestCryptoAgility:
    """Verifies cryptographic agility, versioned envelope handling, and online rewrap."""

    def test_01_v1_aes256gcm_encryption_and_decryption(self, crypto_reg):
        """v1-aes256gcm: standard AEAD encryption and decryption cycle."""
        key = os.urandom(32)
        plaintext = b"top_secret_tenant_ledger_balance_9999"
        aad = b"tenant_id:tenant_alpha|company_id:co_1"

        envelope = crypto_reg.encrypt(
            plaintext=plaintext,
            key=key,
            key_id="k_alpha_v1",
            version=CryptoAlgorithm.V1_AES256_GCM.value,
            aad=aad,
        )

        assert envelope.version == CryptoAlgorithm.V1_AES256_GCM.value
        assert envelope.key_id == "k_alpha_v1"
        assert len(base64.b64decode(envelope.iv)) == 12
        assert len(base64.b64decode(envelope.tag)) == 16

        decrypted = crypto_reg.decrypt(envelope, key, aad=aad)
        assert decrypted == plaintext

    def test_02_v2_chacha20poly1305_encryption_and_decryption(self, crypto_reg):
        """v2-chacha20poly1305: high-speed stream cipher with Poly1305 MAC."""
        key = os.urandom(32)
        plaintext = b"confidential_executive_payroll_stream"

        envelope = crypto_reg.encrypt(
            plaintext=plaintext,
            key=key,
            key_id="k_payroll_v2",
            version=CryptoAlgorithm.V2_CHACHA20_POLY1305.value,
        )

        assert envelope.version == CryptoAlgorithm.V2_CHACHA20_POLY1305.value
        assert envelope.key_id == "k_payroll_v2"
        assert len(base64.b64decode(envelope.iv)) == 12
        assert len(base64.b64decode(envelope.tag)) == 16

        decrypted = crypto_reg.decrypt(envelope, key)
        assert decrypted == plaintext

    def test_03_v3_kyber_aes256gcm_post_quantum_hybrid(self, crypto_reg):
        """v3-kyber-aes256gcm: post-quantum hybrid KEM encapsulation and decryption."""
        key = os.urandom(32)
        plaintext = b"post_quantum_secure_mission_critical_state"

        envelope = crypto_reg.encrypt(
            plaintext=plaintext,
            key=key,
            key_id="k_quantum_v3",
            version=CryptoAlgorithm.V3_KYBER_AES256_GCM.value,
        )

        assert envelope.version == CryptoAlgorithm.V3_KYBER_AES256_GCM.value
        assert envelope.kem_ciphertext is not None
        assert len(base64.b64decode(envelope.kem_ciphertext)) == 48

        decrypted = crypto_reg.decrypt(envelope, key)
        assert decrypted == plaintext

    def test_04_tampered_ciphertext_fails_closed_rule45(self, crypto_reg):
        """AEAD integrity: tampering with 1 byte of ciphertext fails closed for all ciphers."""
        key = os.urandom(32)
        plaintext = b"unaltered_financial_wire_order"

        for algo in [
            CryptoAlgorithm.V1_AES256_GCM.value,
            CryptoAlgorithm.V2_CHACHA20_POLY1305.value,
            CryptoAlgorithm.V3_KYBER_AES256_GCM.value,
        ]:
            envelope = crypto_reg.encrypt(plaintext, key, "k_test", version=algo)

            # Flip last byte of ciphertext
            raw_ct = bytearray(base64.b64decode(envelope.ciphertext))
            raw_ct[-1] ^= 0xFF
            tampered_env = CryptoEnvelope(
                version=envelope.version,
                key_id=envelope.key_id,
                iv=envelope.iv,
                tag=envelope.tag,
                ciphertext=base64.b64encode(raw_ct).decode("utf-8"),
                kem_ciphertext=envelope.kem_ciphertext,
                aad=envelope.aad,
            )

            with pytest.raises(AuthenticationTagVerificationError):
                crypto_reg.decrypt(tampered_env, key)

    def test_05_tampered_tag_fails_closed(self, crypto_reg):
        """AEAD integrity: tampering with the authentication tag fails closed."""
        key = os.urandom(32)
        envelope = crypto_reg.encrypt(b"secret", key, "k1", version=CryptoAlgorithm.V1_AES256_GCM.value)

        # Alter tag
        raw_tag = bytearray(base64.b64decode(envelope.tag))
        raw_tag[0] ^= 0x01
        bad_env = CryptoEnvelope(
            version=envelope.version,
            key_id=envelope.key_id,
            iv=envelope.iv,
            tag=base64.b64encode(raw_tag).decode("utf-8"),
            ciphertext=envelope.ciphertext,
        )

        with pytest.raises(AuthenticationTagVerificationError):
            crypto_reg.decrypt(bad_env, key)

    def test_06_envelope_serialization_and_deserialization(self, crypto_reg):
        """CryptoEnvelope canonical JSON serialization preserves all versioned fields."""
        key = os.urandom(32)
        env = crypto_reg.encrypt(
            b"serializable_content",
            key,
            "k_json",
            version=CryptoAlgorithm.V3_KYBER_AES256_GCM.value,
        )

        serialized = env.serialize()
        assert '"v": "v3-kyber-aes256gcm"' in serialized
        assert '"kem_ct"' in serialized

        restored = CryptoEnvelope.deserialize(serialized)
        assert restored.version == env.version
        assert restored.ciphertext == env.ciphertext
        assert restored.kem_ciphertext == env.kem_ciphertext

        # Verify restored envelope decrypts cleanly
        assert crypto_reg.decrypt(restored, key) == b"serializable_content"

    def test_07_online_rewrapping_migration_zero_downtime(self, crypto_reg, rewrapper):
        """OnlineRewrapper seamlessly migrates legacy envelopes without downtime."""
        old_key = os.urandom(32)
        new_key = os.urandom(32)
        quantum_key = os.urandom(32)
        plaintext = b"immutable_contract_clauses_for_migration"

        # 1. Start with v1 AES-256-GCM
        env_v1 = crypto_reg.encrypt(
            plaintext=plaintext,
            key=old_key,
            key_id="k_legacy_v1",
            version=CryptoAlgorithm.V1_AES256_GCM.value,
        )
        assert env_v1.version == "v1-aes256gcm"

        # 2. Rewrap to v2 ChaCha20-Poly1305 with new key
        env_v2 = rewrapper.rewrap(
            envelope=env_v1,
            old_key=old_key,
            new_key=new_key,
            new_version=CryptoAlgorithm.V2_CHACHA20_POLY1305.value,
            new_key_id="k_active_v2",
        )
        assert env_v2.version == "v2-chacha20poly1305"
        assert env_v2.key_id == "k_active_v2"
        assert crypto_reg.decrypt(env_v2, new_key) == plaintext

        # 3. Rewrap to v3 Post-Quantum Kyber Hybrid with quantum key
        env_v3 = rewrapper.rewrap(
            envelope=env_v2,
            old_key=new_key,
            new_key=quantum_key,
            new_version=CryptoAlgorithm.V3_KYBER_AES256_GCM.value,
            new_key_id="k_future_v3",
        )
        assert env_v3.version == "v3-kyber-aes256gcm"
        assert env_v3.key_id == "k_future_v3"
        assert env_v3.kem_ciphertext is not None
        assert crypto_reg.decrypt(env_v3, quantum_key) == plaintext

    def test_08_mutation_check_unsupported_algorithm_fails(self, crypto_reg):
        """Rule 45: Specifying an unknown or unapproved crypto algorithm fails closed."""
        key = os.urandom(32)
        with pytest.raises(UnsupportedAlgorithmError, match="Unsupported crypto algorithm"):
            crypto_reg.encrypt(b"data", key, "k_bad", version="v99-unapproved-des")
