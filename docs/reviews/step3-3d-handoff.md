# Sub-Step 3D Handoff: Origin-Bound Credential Vault

**Sub-Step:** 3D  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml                             |   2 +-
 core/vault/__init__.py                               |  35 ++++
 core/vault/cookies.py                                |  97 ++++++++++
 core/vault/injector.py                               |  72 ++++++++
 core/vault/origin.py                                 |  67 +++++++
 core/vault/types.py                                  |  83 +++++++++
 core/vault/vault.py                                  | 377 +++++++++++++++++++++++++++++++++++++++++++
 docs/reports/STEP3_REPORT.md                         |  25 +++
 migrations/common/0030_origin_bound_credential_vault.sql |  31 ++++
 migrations/pg/0030_origin_bound_credential_vault.sql     |  63 ++++++++
 tests/test_step3_credential_vault.py                 | 240 +++++++++++++++++++++++++++
 11 files changed, 1091 insertions(+), 1 deletion(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run unit tests for Sub-Step 3D
python -m unittest tests/test_step3_credential_vault.py

# 2. Run all Step 3 test suites together
pytest tests/test_step3_preflight.py tests/test_step3_host_agent.py tests/test_step3_desktop_control.py tests/test_step3_credential_vault.py -v
```

---

## 3. Claims Made & Verified

1. **Origin Mismatch Refusal:** Injecting into mismatched domains, ports, or http downgrades raises `OriginMismatchError` and logs denial to evidence ledger. Verified in `test_01`.
2. **Late-Binding Placeholder Substitution:** Models see `{{CREDENTIAL:...}}`; plaintext substitution occurs at the last moment inside execution engine. Verified in `test_02`.
3. **Zero Plaintext Leakage (Rule 24):** Post-injection perception, trees, and DOM dumps mask the secret with `[MASKED_INPUT]`. Verified in `test_03`.
4. **Database & Audit Secrecy:** Database contains encrypted payloads only; Merkle evidence events store hashes and masked references, never plaintext. Verified in `test_04`.
5. **High-Privilege ActionGateway Gate (Rule 27):** High-privilege credentials require human approval before injection. Verified in `test_05`.
6. **Zero Secret Export Invariant:** Secret export fails closed with `SecretExportForbiddenError`. Verified in `test_06`.
7. **Ephemeral Cookie Purge:** Session cookies bound to origin and wiped immediately on logout. Verified in `test_07`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3D delivers origin-bound credential management.
- Sub-Step 3E will deliver the browser automation engine (`Playwright` lead).
