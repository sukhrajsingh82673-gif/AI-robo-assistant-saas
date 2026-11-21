"""ZONATA Agent Factory - Detached Ed25519 Signer & Merkle Sealer.

Lifts reference/qa/signing_ref.py into production architecture.
Provides canonical JSON serialization, Ed25519 detached signatures,
key rotation, revocation check, and Merkle tree verification.
"""

from __future__ import annotations
import base64
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def canonical(obj: Any) -> bytes:
    """Deterministic canonical JSON serialization (RFC 8785 style)."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    """Compute hex SHA-256 digest."""
    return hashlib.sha256(b).hexdigest()


def sign_manifest(priv: Ed25519PrivateKey, manifest: Dict[str, Any], key_id: str) -> Dict[str, str]:
    """Generate detached signature over canonical manifest JSON."""
    body = canonical(manifest)
    sig = priv.sign(body)
    return {
        "manifest_sha256": sha256_hex(body),
        "signature": base64.b64encode(sig).decode("ascii"),
        "signing_key_id": key_id
    }


def verify_manifest(
    pub: Ed25519PublicKey,
    manifest: Dict[str, Any],
    signed: Dict[str, str],
    revoked_key_ids: Optional[Set[str]] = None
) -> Tuple[bool, str]:
    """Verify detached Ed25519 signature over canonical manifest."""
    revoked = revoked_key_ids or set()
    key_id = signed.get("signing_key_id", "")
    if key_id in revoked:
        return False, "key revoked"

    body = canonical(manifest)
    if sha256_hex(body) != signed.get("manifest_sha256"):
        return False, "hash mismatch"

    sig_b64 = signed.get("signature", "")
    try:
        sig_bytes = base64.b64decode(sig_b64)
        pub.verify(sig_bytes, body)
    except (InvalidSignature, KeyError, ValueError, Exception):
        return False, "bad signature"

    return True, "ok"


def chain_append(chain: List[Dict[str, Any]], event: Dict[str, Any]) -> Dict[str, Any]:
    """Append event to hash-chained log."""
    prev = chain[-1]["entry_hash"] if chain else "0" * 64
    entry = {"seq": len(chain) + 1, "prev_hash": prev, "event": event}
    entry["entry_hash"] = sha256_hex(canonical({k: entry[k] for k in ("seq", "prev_hash", "event")}))
    chain.append(entry)
    return entry


def chain_verify(chain: List[Dict[str, Any]]) -> Tuple[bool, Optional[int]]:
    """Verify hash chain integrity. Returns (valid, failing_seq_index)."""
    prev = "0" * 64
    for e in chain:
        h = sha256_hex(canonical({"seq": e["seq"], "prev_hash": e["prev_hash"], "event": e["event"]}))
        if e["prev_hash"] != prev or e["entry_hash"] != h:
            return False, e["seq"]
        prev = e["entry_hash"]
    return True, None


def merkle_root(hashes: List[str]) -> str:
    """Compute binary Merkle tree root from hex hashes."""
    if not hashes:
        return sha256_hex(b"")
    level = [bytes.fromhex(h) for h in hashes]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest()
            for i in range(0, len(level), 2)
        ]
    return level[0].hex()
