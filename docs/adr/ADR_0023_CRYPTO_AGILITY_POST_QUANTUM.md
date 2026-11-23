# ADR 0023: Crypto Agility, Versioned Envelopes, and Post-Quantum Cryptography Readiness

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 45 (Crypto agility: versioned envelopes, zero hardcoded algorithms)

---

## 1. Context and Problem Statement
Cryptographic algorithms degrade over time as cryptanalysis progresses and quantum computing advances. Embedding hardcoded cryptographic primitives (such as `AES-256-GCM` or `HMAC-SHA256`) directly in application code creates severe security debt when algorithms must be rotated or upgraded to Post-Quantum Cryptography (PQC) standards (such as NIST FIPS 203 ML-KEM / Kyber and FIPS 204 ML-DSA / Dilithium).

## 2. Decision

### 2.1 Central Crypto Registry (`core/crypto/`)
All cryptographic operations across ZONATA must route through a unified, centralized module: `core/crypto`. No raw imports of `hashlib`, `hmac`, `cryptography`, or `nacl` are permitted in business or domain modules. An automated AST lint (`tests/test_crypto_lint.py`) enforces this in CI.

### 2.2 Versioned Ciphertext and Signature Envelopes
All encrypted payloads stored at rest or transmitted over the wire must be encapsulated in structured, self-describing JSON/binary envelopes:
```json
{
  "version": "v1",
  "algorithm": "AES-256-GCM",
  "key_id": "transit:keys/zonata-root:3",
  "iv": "base64...",
  "ciphertext": "base64...",
  "tag": "base64...",
  "created_at": "2026-11-23T12:00:00Z"
}
```
Supported algorithms are cataloged in an authoritative enum:
- `v1-aes256gcm`: Current standard for high-throughput symmetric encryption.
- `v2-chacha20poly1305`: Mobile and CPU-friendly authenticated cipher.
- `v3-hybrid-kyber768-aes256gcm`: Post-quantum hybrid KEM combining NIST ML-KEM-768 with classical X25519 and AES-256-GCM.

### 2.3 Online Rewrap Utility
Data re-encryption must not require application downtime. `core/crypto/rewrap.py` provides an online batch rewrap tool that:
1. Reads records encrypted under key version $N$ or algorithm $A$.
2. Decrypts using the version identified in the envelope.
3. Encrypts under active key version $N+1$ or target post-quantum algorithm $B$.
4. Updates database records atomically using optimistic version locks.

### 2.4 Transport Security & PQC Hybrid TLS
Inter-service and external TLS connections require OpenBao and reverse proxies configured with hybrid post-quantum key exchange (e.g., `X25519Kyber768Draft00` or standardized `mlkem768x25519`), protecting current traffic from "Harvest Now, Decrypt Later" quantum threats.

## 3. Consequences
- **Positive:** Complete cryptographic agility; ability to rotate keys and algorithms without data migration nightmares; immediate quantum-resilience posture.
- **Negative:** Small envelope serialization overhead compared to raw byte arrays.
