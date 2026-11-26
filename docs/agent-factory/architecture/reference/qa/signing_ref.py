"""Reference: canonical JSON + Ed25519 detached signatures + hash-chain/Merkle evidence check.

Lift into agent_factory/cert/{signer,verifier}.py. Keys must come from SecretsPort (Vault/OpenBao transit);
the in-memory key below is for tests only.  Run tests:  python3 -I signing_ref.py --selftest
Requires: cryptography (Ed25519).  Canonicalisation: sorted keys, no whitespace, UTF-8, no NaN/Infinity,
integers only for numbers that must be exact (floats allowed but must round-trip) — RFC 8785-style, not a full JCS impl.
"""
from __future__ import annotations
import base64, hashlib, json, sys
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sign_manifest(priv: Ed25519PrivateKey, manifest: dict, key_id: str) -> dict:
    body = canonical(manifest)
    sig = priv.sign(body)
    return {"manifest_sha256": sha256_hex(body), "signature": base64.b64encode(sig).decode(), "signing_key_id": key_id}


def verify_manifest(pub: Ed25519PublicKey, manifest: dict, signed: dict, revoked_key_ids: set[str] = frozenset()) -> tuple[bool, str]:
    if signed.get("signing_key_id") in revoked_key_ids:
        return False, "key revoked"
    body = canonical(manifest)
    if sha256_hex(body) != signed.get("manifest_sha256"):
        return False, "hash mismatch"
    try:
        pub.verify(base64.b64decode(signed["signature"]), body)
    except (InvalidSignature, KeyError, ValueError):
        return False, "bad signature"
    return True, "ok"


# --- minimal evidence chain + Merkle (illustrates AT-14; the real EvidenceLedger is ZONATA's) ---
def chain_append(chain: list[dict], event: dict) -> dict:
    prev = chain[-1]["entry_hash"] if chain else "0" * 64
    entry = {"seq": len(chain) + 1, "prev_hash": prev, "event": event}
    entry["entry_hash"] = sha256_hex(canonical({k: entry[k] for k in ("seq", "prev_hash", "event")}))
    chain.append(entry)
    return entry


def chain_verify(chain: list[dict]) -> tuple[bool, int | None]:
    prev = "0" * 64
    for e in chain:
        h = sha256_hex(canonical({"seq": e["seq"], "prev_hash": e["prev_hash"], "event": e["event"]}))
        if e["prev_hash"] != prev or e["entry_hash"] != h:
            return False, e["seq"]
        prev = e["entry_hash"]
    return True, None


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return sha256_hex(b"")
    level = [bytes.fromhex(h) for h in hashes]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def _selftest():
    res, t = [], lambda n, ok: res.append((n, bool(ok)))
    priv = Ed25519PrivateKey.generate(); pub = priv.public_key()
    m = {"agent": "competitor-analysis", "version": "1.0.0", "package_sha256": "ab" * 32, "gate_policy": "1.0.0", "n": 3}
    s = sign_manifest(priv, m, "k1")
    t("valid signature verifies", verify_manifest(pub, m, s)[0])
    t("key order does not matter (canonical)", verify_manifest(pub, dict(reversed(list(m.items()))), s)[0])
    t("1-field change fails (hash mismatch)", verify_manifest(pub, {**m, "version": "1.0.1"}, s) == (False, "hash mismatch"))
    s2 = dict(s, signature=base64.b64encode(bytes(64)).decode())
    t("forged signature fails", verify_manifest(pub, m, s2) == (False, "bad signature"))
    other = Ed25519PrivateKey.generate().public_key()
    t("signature by an unknown key fails", verify_manifest(other, m, s)[0] is False)
    t("revoked key id fails", verify_manifest(pub, m, s, {"k1"}) == (False, "key revoked"))
    t("swapped manifest with valid old signature fails", verify_manifest(pub, {**m, "package_sha256": "cd" * 32}, s)[0] is False)
    chain: list[dict] = []
    for i in range(5):
        chain_append(chain, {"event": "factory.version.built", "i": i})
    t("clean chain verifies", chain_verify(chain) == (True, None))
    root = merkle_root([e["entry_hash"] for e in chain])
    chain[2]["event"]["i"] = 99
    ok, at = chain_verify(chain)
    t("tampered entry detected at the exact seq", (ok, at) == (False, 3))
    t("merkle root changes after tamper-and-rehash", merkle_root([sha256_hex(canonical({k: e[k] for k in ('seq','prev_hash','event')})) for e in chain]) != root)
    t("public key export works", len(pub.public_bytes(Encoding.Raw, PublicFormat.Raw)) == 32)
    bad = 0
    for n, ok in res:
        print(("PASS " if ok else "FAIL ") + n); bad += (not ok)
    print(f"{len(res) - bad}/{len(res)} passed"); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    print(__doc__)
