# Sub-Step 5B Handoff Dossier — OpenBao Secrets Platform

**Date:** 2026-11-23  
**Sub-Step:** 5B (Secrets Platform behind SecretsPort)  
**Builder Persona:** Antigravity  
**Reviewer Persona:** OpenCode (Reviewer & Red Team)  
**Target Branch:** `step5-trust-security`

---

## 1. Files Changed (`git diff --stat`)
```text
 .github/workflows/ci.yml               |   4 +-
 core/capability_probe.py               |  51 ++++--
 core/ports/kms.py                      | 187 ++++++++++++++++++++-
 core/ports/secrets.py                  | 448 ++++++++++++++++++++++++++++++++++++++++++++++++
 docs/reports/STEP5_REPORT.md           |  26 +++
 tests/test_step5_secrets_platform.py   | 218 +++++++++++++++++++++++
 6 files changed, 915 insertions(+), 19 deletions(-)
```

---

## 2. Commands to Re-run
```bash
cd /data/data/com.termux/files/home/AI-robo-assistant-saas
python3 -m unittest tests/test_step5_secrets_platform.py
python3 -m unittest tests/test_step5_preflight.py tests/test_step5_secrets_platform.py
```

---

## 3. Claims & Evidence
1. **Rule 41 Enforced:** `LocalEnvelopeKeyProvider` is removed from the production code path; attempting to instantiate or resolve it when `APP_ENV=production` raises a fatal `RuntimeError`.
2. **Authoritative `SecretsPort`:** `core/ports/secrets.py` implements the full contract, including OpenBao REST API client and sandbox test simulator.
3. **Multi-Tenant KV v2 Isolation:** Tenant A token cannot access Tenant B secrets. Verified by `test_01_multi_tenant_namespace_isolation`.
4. **Key Rotation & Rewrap:** Encrypted data under version $N$ successfully decrypts after rotation to $N+1$; new data writes use version $N+1$; rewrap updates ciphertext without exposing plaintext. Verified by `test_02_transit_key_rotation_and_rewrap`.
5. **Token Revocation:** Token revocation denies immediate subsequent calls. Verified by `test_03_token_revocation_denies_next_call`.
6. **Fail-Closed on Seal:** Sealed vault immediately causes dependent secret retrieval and transit encryption to fail closed. Verified by `test_04_vault_sealed_fails_closed`.
7. **Crypto-Shredding:** `destroy_tenant_keys()` permanently eliminates tenant Transit keys, rendering historical ciphertexts undecryptable. Verified by `test_05_crypto_shredding_renders_ciphertext_undecryptable`.
8. **Dynamic Database Credentials:** Temporary role credentials generated with lease IDs and TTLs. Verified by `test_06_dynamic_database_credentials`.
9. **Canary Zero-Leak Hunt:** Storing a canary secret yields zero plaintext hits across simulated dumps and logs. Verified by `test_07_canary_zero_plaintext_leak_hunt`.

---

## 4. Mutation Checks Done
- In production profile (`APP_ENV=production`), requesting a local envelope provider fails immediately with `RuntimeError`.
- Tenant boundary tampering (cross-tenant token request) rejected.
- Decryption of shredded tenant data fails closed with explicit crypto-shredded error.

---

## 5. Known Gaps
- Sub-Step 5C will implement Keycloak OIDC authentication and workload identities.
- Sub-Step 5D will refactor transaction-scoped database connections behind transaction-mode poolers.
