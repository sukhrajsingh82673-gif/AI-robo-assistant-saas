"""Tests for Ed25519 Detached Signer and Merkle Sealer (Phase 4)."""

import base64
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agent_factory.build.signer import (
    canonical, sha256_hex, sign_manifest, verify_manifest,
    chain_append, chain_verify, merkle_root
)


def test_signing_selftest_suite():
    """Verify all 11 core signing properties."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    m = {
        "agent": "competitor-analysis",
        "version": "1.0.0",
        "package_sha256": "ab" * 32,
        "gate_policy": "1.0.0",
        "n": 3
    }
    s = sign_manifest(priv, m, "k1")

    # 1. Valid signature verifies
    ok, reason = verify_manifest(pub, m, s)
    assert ok is True
    assert reason == "ok"

    # 2. Key order does not matter (canonical JSON)
    reversed_m = dict(reversed(list(m.items())))
    ok, _ = verify_manifest(pub, reversed_m, s)
    assert ok is True

    # 3. 1-field modification fails (hash mismatch)
    m_tampered = dict(m, version="1.0.1")
    ok, reason = verify_manifest(pub, m_tampered, s)
    assert ok is False
    assert reason == "hash mismatch"

    # 4. Forged signature fails
    s_forged = dict(s, signature=base64.b64encode(bytes(64)).decode())
    ok, reason = verify_manifest(pub, m, s_forged)
    assert ok is False
    assert reason == "bad signature"

    # 5. Signature by unknown key fails
    other_pub = Ed25519PrivateKey.generate().public_key()
    ok, _ = verify_manifest(other_pub, m, s)
    assert ok is False

    # 6. Revoked key ID fails
    ok, reason = verify_manifest(pub, m, s, revoked_key_ids={"k1"})
    assert ok is False
    assert reason == "key revoked"

    # 7. Swapped manifest fails
    ok, _ = verify_manifest(pub, dict(m, package_sha256="cd" * 32), s)
    assert ok is False

    # 8. Hash chain append and verify
    chain = []
    for i in range(5):
        chain_append(chain, {"event": "factory.version.built", "i": i})
    ok, fail_seq = chain_verify(chain)
    assert ok is True
    assert fail_seq is None

    # 9. Tampered entry detected at exact sequence index
    root = merkle_root([e["entry_hash"] for e in chain])
    chain[2]["event"]["i"] = 99
    ok, fail_seq = chain_verify(chain)
    assert ok is False
    assert fail_seq == 3

    # 10. Merkle root changes after tamper
    new_root = merkle_root([
        sha256_hex(canonical({"seq": e["seq"], "prev_hash": e["prev_hash"], "event": e["event"]}))
        for e in chain
    ])
    assert new_root != root
