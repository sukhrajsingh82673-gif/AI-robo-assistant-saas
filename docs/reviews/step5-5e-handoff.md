# Step 5E Handoff Dossier: Application & Supply-Chain Security

## 1. Summary of Changes
- **API Hardening & Perimeter Defense (`core/security/api_hardening.py`):**
  - Host Header Validation: Blocks Host header poisoning and unapproved domain requests.
  - CORS Security (ASVS V14.4): Strict allow-list validation per tenant; wildcard `*` with credentials rejected.
  - OWASP Security Headers: Injects CSP, HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
  - Brute-Force Rate Limiting: Progressive exponential backoff lockout on authentication failures.
  - WAF Payload Inspection: Blocks SQLi, XSS, Path Traversal, Command Injection, and oversized payloads (>10MB).
- **Supply-Chain Integrity (`core/security/supply_chain.py`):**
  - CycloneDX SBOM Validation: Validates component structure and audits licenses against Rule 5 allow-list.
  - Cosign Container / Artifact Signing: Signs and verifies release artifacts using OpenBao Transit KMS (`cosign://...`), failing closed on tampering.
- **CI Test Suite (`tests/test_step5_app_supply_chain_security.py` & `.github/workflows/ci.yml`):**
  - 9 comprehensive test cases integrated into both SQLite and PostgreSQL 16 CI pipelines.

---

## 2. Changed Files (`git diff --stat`)
```text
 .github/workflows/ci.yml                       |   4 +-
 core/security/__init__.py                      |  33 ++++
 core/security/api_hardening.py                 | 205 ++++++++++++++++++++++
 core/security/supply_chain.py                  | 197 +++++++++++++++++++++
 docs/reports/STEP5_REPORT.md                   |  37 ++++
 tests/test_step5_app_supply_chain_security.py  | 242 ++++++++++++++++++++++++++
 6 files changed, 716 insertions(+), 2 deletions(-)
```

---

## 3. Commands to Re-run
```bash
# Verify Python bytecode compilation across repository
python3 -m compileall -q .

# Run Step 5E Application & Supply-Chain Security Suite
python3 -m pytest tests/test_step5_app_supply_chain_security.py -v

# Run Full Step 5 Cumulative Test Suites & AST Truth Linter
python3 -m pytest tests/test_step5_preflight.py tests/test_step5_secrets_platform.py tests/test_step5_identity_access.py tests/test_step5_database_isolation.py tests/test_step5_app_supply_chain_security.py tests/test_truth_linter.py -v
```

---

## 4. Claims & Evidence
| Claim | Rule | Evidence |
|---|---|---|
| Host header injection rejected | OWASP ASVS | `tests/test_step5_app_supply_chain_security.py::test_01_host_header_validation_and_poisoning_rejection` |
| CORS wildcard with credentials rejected | ASVS V14.4 | `tests/test_step5_app_supply_chain_security.py::test_02_cors_origin_allowlist_and_credential_wildcard_rejection` |
| Progressive exponential lockout enforced on auth failures | Security Invariant | `tests/test_step5_app_supply_chain_security.py::test_04_brute_force_exponential_lockout` |
| WAF inspects and flags injection attacks | OWASP Top 10 | `tests/test_step5_app_supply_chain_security.py::test_05_waf_payload_inspection_and_attacks` |
| CycloneDX SBOM audited against Rule 5 license deny-list | Rule 5 | `tests/test_step5_app_supply_chain_security.py::test_06_cyclonedx_sbom_validation` |
| Disallowed license in SBOM triggers immediate rejection | Mutation / Rule 5 | `tests/test_step5_app_supply_chain_security.py::test_07_mutation_check_disallowed_license_in_sbom` |
| Cosign artifact signing & verification via OpenBao Transit | SLSA Level 3 | `tests/test_step5_app_supply_chain_security.py::test_08_cosign_artifact_signing_and_verification` |
| Tampered artifact or signature fails verification | Fail Closed | `tests/test_step5_app_supply_chain_security.py::test_09_tampered_artifact_fails_cosign_verification` |
| AST Truth Linter passes with zero violations | Rule 8 | `tests/test_truth_linter.py` (6/6 passing) |

---

## 5. Mutation Checks Done
1. **SBOM AGPL/SSPL Injection:** Injecting an AGPL-3.0 or SSPL component into CycloneDX SBOM raises `SupplyChainLicenseViolation`.
2. **Cosign Payload Tampering:** Modifying binary artifact bytes after signing causes `verify_artifact` to raise `SupplyChainSignatureTamperedError`.
3. **Cosign Signature Tampering:** Mutating signature characters causes signature verification to fail closed.
4. **CORS Wildcard with Credentials:** Attempting to set `Access-Control-Allow-Origin: *` with credentials raises `CORSSecurityViolation`.
