# Step 5C Handoff Dossier: Identity & Access Platform (Keycloak / OIDC / Workload Identity)

## 1. Summary of Changes
- **Identity & Access Port Contract (`core/ports/identity.py`):**
  - Defined `IdentityPort` abstract port inheriting from sovereign `Port`.
  - Implemented `KeycloakOIDCProvider` connecting to Keycloak realms with OIDC discovery, JWT claims validation, audience enforcement, and SCIM 2.0 provisioning.
  - Implemented `SandboxIdentityProvider` for `ZONATA_TEST_MODE=1` verifying OIDC token issuance, signature checks, refresh token rotation with reuse detection, and MFA enforcement.
- **Role Tiering & Invariant Types (`core/identity/types.py`, `core/identity/__init__.py`):**
  - Authoritative role tiers: `OWNER`, `EXECUTIVE`, `MANAGER`, `OPERATOR`, `AUDITOR`, `OBSERVER`, `SYSTEM_AGENT`.
  - Defined `SCIM_PERMITTED_ROLES` explicitly excluding `OWNER` and `BOARD` (Rule 44).
  - Concrete security exceptions: `UnauthorizedOwnerPromotionError`, `StepUpRequiredError`, `MFAEnforcementError`, `AudienceMismatchError`, `OwnershipTransferCoolingOffError`, `DualControlApprovalRequiredError`, `RecoveryForbiddenByEmailAloneError`, `TokenReuseDetectedError`, `MachineInteractiveLoginForbiddenError`.
- **Rule 44 Governance & Multi-Channel Recovery (`core/identity/ownership.py`):**
  - `OwnershipGovernance` requiring dual independent authorization, cooling-off timer enforcement (default 24h), and immutable audit sealing in `EvidenceLedger`.
  - Multi-channel account recovery verifying strong cryptographic/hardware authenticators; email alone is strictly forbidden under Rule 44.
- **Customer Integration API Keys (`core/identity/api_keys.py`):**
  - Generates scoped tokens (`zonata_live_sk_...` / `zonata_test_sk_...`).
  - Prefix-based lookup with salted SHA-256 storage; raw secret is never stored or logged (Rule 41).
  - Scope verification, expiration, revocation, and last-used timestamp tracking.
- **Workload Identities & Scoped CI Tokens (`core/identity/workload.py`):**
  - Parsed and validated SPIFFE IDs (`spiffe://zonata.internal/ns/{tenant}/sa/{service}`).
  - Service-to-service ACL boundary validation.
  - Prohibition of interactive sessions for machine workload identities (Rule 42).
  - GitHub App scoped installation token issuance and verification.
- **Capability Reality Probe (`core/capability_probe.py`):**
  - Added `probe_identity()` verifying active identity provider health.
- **CI Test Suite (`tests/test_step5_identity_access.py` & `.github/workflows/ci.yml`):**
  - 12 comprehensive test cases validating all 5C security invariants. Added to both SQLite and PostgreSQL 16 CI test matrices.

---

## 2. Changed Files (`git diff --stat`)
```text
 .github/workflows/ci.yml            |   4 +-
 core/capability_probe.py            |   6 +
 core/identity/__init__.py           |  38 +++++
 core/identity/api_keys.py           | 135 +++++++++++++++++
 core/identity/ownership.py          | 167 +++++++++++++++++++++
 core/identity/types.py              | 113 ++++++++++++++
 core/identity/workload.py           | 122 +++++++++++++++
 core/ports/identity.py              | 397 +++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_step5_identity_access.py | 373 +++++++++++++++++++++++++++++++++++++++++++++
 9 files changed, 1353 insertions(+), 2 deletions(-)
```

---

## 3. Commands to Re-run
```bash
# Bytecode compilation check
python3 -m compileall -q .

# Run Step 5C Identity Access Test Suite
python3 -m pytest tests/test_step5_identity_access.py -v

# Run Full Step 5 Preflight, Secrets, Identity & AST Truth Linter
python3 -m pytest tests/test_step5_preflight.py tests/test_step5_secrets_platform.py tests/test_step5_identity_access.py tests/test_truth_linter.py -v
```

---

## 4. Claims & Evidence
| Claim | Rule | Evidence |
|---|---|---|
| No SCIM or external API can mint or elevate to OWNER | Rule 44 | `tests/test_step5_identity_access.py::test_06_scim_owner_promotion_forbidden_rule44` (Raises `UnauthorizedOwnerPromotionError`) |
| Ownership transfer requires dual control & cooling-off period | Rule 44 | `tests/test_step5_identity_access.py::test_07_dual_control_ownership_transfer_and_cooling_off` (Enforces 2 distinct approvals + cooling-off timer) |
| Account recovery rejects email alone | Rule 44 | `tests/test_step5_identity_access.py::test_08_multi_channel_recovery_rejects_email_alone_rule44` (Raises `RecoveryForbiddenByEmailAloneError`) |
| Machine workloads forbidden from acquiring interactive sessions | Rule 42 | `tests/test_step5_identity_access.py::test_10_workload_identity_and_machine_interactive_forbidden` (Raises `MachineInteractiveLoginForbiddenError`) |
| Replaying rotated refresh token revokes token family | Security Invariant | `tests/test_step5_identity_access.py::test_03_refresh_token_rotation_and_reuse_detection` (Raises `TokenReuseDetectedError`) |
| No plaintext secret tokens in API key store | Rule 41 | `tests/test_step5_identity_access.py::test_09_customer_api_key_lifecycle_and_scopes` (Salted SHA-256 only) |
| AST Truth Linter zero violations | Standing Rule 8 | `tests/test_truth_linter.py` (6/6 passing) |

---

## 5. Mutation Checks Done
1. **SCIM Owner Elevation:** Attempting to submit `role: OWNER` or `role: BOARD` to SCIM provisioning raises `UnauthorizedOwnerPromotionError`.
2. **Transfer Premature Execution:** Attempting to execute ownership transfer before `cooling_off_seconds` elapses raises `OwnershipTransferCoolingOffError`.
3. **Single-Approval Transfer:** Attempting to execute ownership transfer with only 1 approval raises `DualControlApprovalRequiredError`.
4. **Email-Only Recovery:** Requesting recovery with `channels: ["email"]` raises `RecoveryForbiddenByEmailAloneError`.
5. **Machine Interactive Session:** Calling `assert_not_machine_interactive(ident)` raises `MachineInteractiveLoginForbiddenError`.
6. **Token Tampering:** Altering any segment of the signed JWT raises `PermissionError`.
7. **Refresh Token Reuse:** Presenting an already-consumed refresh token raises `TokenReuseDetectedError` and invalidates downstream tokens.

---

## 6. Known Gaps / Follow-ups
- Sub-Step 5D will apply database-level transaction scoping (`set_config(..., true)`) and verify that connection poolers execute strictly under non-superuser `zonata_app` roles with RLS enabled across all tenant tables.
