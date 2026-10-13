# URA / ZONATA SaaS — Authentication & Tenant Security Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Subsystems**: `api_server.py`, `core/auth.py`, `core/enterprise_crm.py`, `core/db.py`  
**Automated Security Suites**:
- `tests/test_direct_object_access_and_tenant_security.py` (11 tests)
- `tests/test_production_auth_security.py` (8 tests)
- `tests/test_audit_remediation_security.py` (29 tests)  
**Execution Status**: **ALL 48 SECURITY TESTS PASSED (48/48, 100% PASS RATE)**  
**Formal Verdict**: **PASS** (Application Security Hardening & Tenant Boundaries Certified)

---

## 1. Executive Summary & Verdict Rationale

This qualification report provides comprehensive, test-backed verification of the authentication infrastructure, token lifecycle, password hashing parameters, rate limiting across instances, zero-downtime key rotation, and multi-tenant authorization boundaries (including Direct Object Access / IDOR protections) in the URA / ZONATA Enterprise SaaS platform.

### Verdict: PASS
All security qualification criteria have been verified through code audits and passing automated regression suites across 48 dedicated security-negative tests:
1. **Salted PBKDF2 Password Hashing**: Configurable iterations (default 100,000, production up to 600,000 via `ZONATA_PBKDF2_ITERATIONS`), 16-byte cryptographically secure salt, upgrade-ready prefix formatting (`pbkdf2_sha256$<iter>$<salt>$<hash>`), and transparent upgrade on successful authentication.
2. **Safe Hash Verification & Optimistic Concurrency**: Malformed hash strings (invalid formats, non-numeric iteration counts, corrupted salts) fail closed safely without throwing unhandled exceptions. Upgrading password hashes uses optimistic concurrency (`WHERE user_id = ? AND password_hash = ?`) so concurrent logins cannot overwrite newer credential state. Failed logins never alter stored credential hashes or salts.
3. **Input Validation**: RFC-compliant email validation, minimum 8-character password enforcement, and duplicate registration conflict handling.
4. **Concurrency-Safe Distributed Rate Limiting**: Shared database-backed sliding window via `auth_rate_limits` table with transaction write-lock serialization (`BEGIN IMMEDIATE`), opportunistic garbage collection of expired timestamps, and dual-axis enforcement by both remote IP address and account identifier (`rate_limit_ip_and_account`). Verified under 15-thread simultaneous race conditions.
5. **Cryptographic HMAC-SHA256 Tokens**: High-entropy secret signing, constant-time `hmac.compare_digest` validation, tamper rejection, and explicit expiration.
6. **CSPRNG Secret Generation & True Cryptographic Entropy**: `generate_secure_auth_secret(32)` yields 256 bits of true cryptographic entropy from system CSPRNG (`secrets.token_hex(32)`). Shannon character-distribution metrics are evaluated via `evaluate_secret_entropy` as a supplementary safeguard.
7. **Zero-Downtime Key Rotation & Grace Periods**: Dual-key verification via `ZONATA_PREVIOUS_AUTH_SECRET` preserving active user sessions during documented rotation windows, with explicit window expiry enforcement via `ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT`.
8. **Emergency Key Retirement Procedure**: In the event of a compromised signing key, `emergency_retire_previous_secret()` and `ZONATA_REVOKED_AUTH_SECRETS` immediately revoke acceptance of the compromised key across all instances, bypassing rotation fallback and failing invalid sessions closed immediately.
9. **Server-Side Token Revocation Store**: Relational blacklist in `auth_revoked_tokens` table rejecting revoked tokens across all protected endpoints.
10. **Server-Derived Tenant Identity**: Authenticated principal is authoritative; client headers cannot elevate or switch tenant scope.
11. **Anti-Spoofing Tenant Header Guard**: Mismatched `X-Tenant-ID` headers are immediately rejected with HTTP 403 `TENANT_SPOOFING_ATTEMPT`.
12. **Direct Object Access (IDOR) & Relational Isolation**: Every customer and deal query enforces `WHERE tenant_id = ?`. In `create_deal` and `update_deal`, referencing a customer owned by another tenant is strictly prohibited and returns a non-leaking error (`Customer '...' not found in current organization`). Unauthorized cross-tenant updates and deletes return HTTP 404 without disclosing resource existence.
13. **Fail-Closed Architecture**: Missing, malformed, expired, tampered, or revoked tokens fail closed with HTTP 401.

---

## 2. Security Subsystems & Code Verification

### 2.1 Password Storage, Parameters & Upgrade Mechanics
Passwords are never stored in plaintext or with weak fast hashes (MD5/SHA1):
- **Algorithm**: `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)`.
- **Salting**: 16 cryptographically random bytes generated via `secrets.token_hex(16)` per credential record.
- **Iteration Count**: Default 100,000 rounds, configurable up to 600,000 via `ZONATA_PBKDF2_ITERATIONS` compliant with current OWASP guidance.
- **Prefix Metadata**: Hash strings are formatted as `pbkdf2_sha256$<iterations>$<salt>$<hash>`.
- **Transparent Upgrade**: During `UserManager.authenticate_user()`, `verify_password_with_upgrade()` checks iteration count and format. Any legacy unformatted or lower-iteration hashes are transparently upgraded and re-saved on successful authentication using optimistic locking `WHERE user_id = ? AND password_hash = ?`.
- **Failed Login Invariant**: On authentication failure, only `failed_attempts` and `locked_until` are updated; credential hash and salt are never modified.
- **Malformed Encodings**: Safely returns `(False, False)` on any corrupted string, non-integer iteration count, or truncated hash.

### 2.2 Concurrency-Safe Distributed Rate Limiting
To prevent account harvesting and registration abuse across a multi-container cluster:
- **Relational Storage**: `auth_rate_limits` table records `(rate_key, attempt_timestamp)` in the shared database.
- **Concurrency Serialization**: Acquires database write locks (`conn.execute("BEGIN IMMEDIATE")`) before reading sliding-window counts, preventing concurrent worker race conditions.
- **Garbage Collection**: Expired entries older than `window_seconds` across all keys are pruned opportunistically on each check.
- **Dual-Axis Throttling**: `RateLimiter.rate_limit_ip_and_account(ip, account)` throttles both source IP (max 20 req/min) and target account identifier (max 5 req/min), preventing distributed credential stuffing against a single account.
- **Verified Concurrency**: Tested with 15 simultaneous threads competing for 5 allowed slots; exactly 5 were accepted and 10 were blocked (0 leaks under race conditions).

### 2.3 Secret Entropy, Key Rotation & Emergency Retirement
1. **CSPRNG Secret Generation**:
   - `generate_secure_auth_secret(num_bytes=32)` uses `secrets.token_hex(32)` providing 256 bits of true cryptographic entropy.
   - Runtime Shannon entropy evaluation (`evaluate_secret_entropy`) validates character diversity and length (>= 32 chars, Shannon entropy >= 3.0 bits/char, >= 10 unique chars).
2. **Zero-Downtime Key Rotation**:
   - New tokens are signed only with the active primary key (`ZONATA_AUTH_SECRET`).
   - Old tokens are accepted during the rotation grace period via `ZONATA_PREVIOUS_AUTH_SECRET`.
   - Rotation grace period window is enforced via `ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT`.
3. **Emergency Secret Retirement**:
   - In case of key compromise, `emergency_retire_previous_secret(compromised_key)` immediately revokes the key and appends it to `ZONATA_REVOKED_AUTH_SECRETS`.
   - All tokens signed with the compromised key fail verification immediately (tested in `test_09`).

### 2.4 Direct Object Access (IDOR) & Relational Isolation
- **CRM Customers**: `get_customer`, `update_customer`, and `delete_customer` strictly require `tenant_id = ?`.
- **CRM Deals**: `get_deal`, `create_deal`, `update_deal`, `update_deal_stage`, and `delete_deal` enforce tenant scoping directly in the SQL statement.
- **Cross-Tenant Association**: `create_deal` and `update_deal` verify that `customer_id` belongs to the authenticated tenant. If not found, a non-leaking `ValueError: Direct Object Access Violation: Customer '...' not found in current organization` is raised.
- **Non-Disclosure**: Cross-tenant `GET`, `PATCH`, and `DELETE` requests return HTTP 404 without disclosing whether the object exists in another tenant's partition.

---

## 3. Automated Test Evidence Summary

| Test Suite | Unique Tests | Passed | Failures | Errors | Focus Area |
|---|---|---|---|---|---|
| `tests/test_direct_object_access_and_tenant_security.py` | 11 | 11 | 0 | 0 | IDOR CRM checks, concurrent rate limits, emergency key retirement, CSPRNG secret generation, malformed hash safety |
| `tests/test_production_auth_security.py` | 8 | 8 | 0 | 0 | PBKDF2 hashing, email validation, token tamper rejection, revocation blacklist, password length |
| `tests/test_audit_remediation_security.py` | 29 | 29 | 0 | 0 | FIND-01 through FIND-08, anti-spoofing rejection, unauthenticated token issuance prevention, fail-closed sandboxes |
| **Total Security Tests** | **48** | **48** | **0** | **0** | **100.00% Pass Rate** |

Evidence artifact persisted at: `storage/evidence/test_accounting_summary.json`.
