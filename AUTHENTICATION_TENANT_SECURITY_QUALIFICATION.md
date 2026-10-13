# URA / ZONATA SaaS — Authentication & Tenant Security Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Subsystems**: `api_server.py`, `core/auth.py`, `core/enterprise_crm.py`, `core/db.py`  
**Automated Security Suites**:
- `tests/test_production_auth_security.py` (8 tests)
- `tests/test_audit_remediation_security.py` (29 tests)
- `tests/test_direct_object_access_and_tenant_security.py` (6 tests)  
**Execution Status**: **ALL 43 SECURITY TESTS PASSED (43/43)**  
**Formal Verdict**: **PASS** (Application Security Hardening & Tenant Boundaries Certified)

---

## 1. Executive Summary & Verdict Rationale

This qualification report provides comprehensive, test-backed verification of the authentication infrastructure, token lifecycle, password hashing parameters, rate limiting across instances, zero-downtime key rotation, and multi-tenant authorization boundaries (including Direct Object Access / IDOR protections) in the URA / ZONATA Enterprise SaaS platform.

### Verdict: PASS
All security qualification criteria have been verified through code audits and passing automated regression suites:
1. **Salted PBKDF2 Password Hashing**: 100,000 iterations, 16-byte cryptographically secure salt, upgrade-ready prefix formatting (`pbkdf2_sha256$100000$...`), and transparent upgrade on authentication.
2. **Input Validation**: RFC-compliant email validation, minimum 8-character password enforcement, and duplicate registration conflict handling.
3. **Multi-Instance Distributed Rate Limiting**: Shared database-backed sliding window via `auth_rate_limits` table with thread-safe in-memory fallback.
4. **Cryptographic HMAC-SHA256 Tokens**: High-entropy secret signing, constant-time `hmac.compare_digest` validation, tamper rejection, and explicit expiration.
5. **Secret Entropy vs. Length Distinction**: Formal evaluation via `evaluate_secret_entropy` assessing Shannon entropy (>= 3.0 bits/char) and distinct characters (>= 10) in addition to 32+ character length.
6. **Zero-Downtime Key Rotation**: Dual-key verification via `ZONATA_PREVIOUS_AUTH_SECRET` preserving active user sessions during secret rotation.
7. **Server-Side Token Revocation Store**: Relational blacklist in `auth_revoked_tokens` table rejecting revoked tokens across all protected endpoints.
8. **Server-Derived Tenant Identity**: Authenticated principal authoritative; client headers cannot elevate or switch tenant scope.
9. **Anti-Spoofing Tenant Header Guard**: Mismatched `X-Tenant-ID` headers are immediately rejected with HTTP 403 `TENANT_SPOOFING_ATTEMPT`.
10. **Direct Object Access (IDOR) & Relational Isolation**: Every customer and deal query enforces `WHERE tenant_id = ?`. Cross-tenant customer linking in deals is rejected with `Direct Object Access Violation`. Cross-tenant updates and deletes return HTTP 404.
11. **Fail-Closed Architecture**: Missing, malformed, expired, tampered, or revoked tokens fail closed with HTTP 401.

---

## 2. Security Subsystems & Code Verification

### 2.1 Password Storage, Parameters & Upgrade Mechanics
Passwords are never stored in plaintext or with weak fast hashes (MD5/SHA1):
- **Algorithm**: `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)`.
- **Salting**: 16 cryptographically random bytes generated via `secrets.token_hex(16)` per credential record.
- **Iteration Count**: Default 100,000 rounds.
- **Prefix Metadata**: Hash strings are formatted as `pbkdf2_sha256$<iterations>$<salt>$<hash>`.
- **Transparent Upgrade**: During `UserManager.authenticate_user()`, `verify_password_with_upgrade()` checks iteration count and format. Any legacy unformatted or lower-iteration hashes are transparently upgraded and re-saved on successful authentication without user disruption.
- **Roadmap**: Parameter upgrade path supports future transition to 600,000 iterations or Argon2id without database schema migration.

### 2.2 Multi-Instance Distributed Rate Limiting
To prevent account harvesting and registration abuse across a multi-container cluster:
- **Relational Storage**: `auth_rate_limits` table records `(rate_key, attempt_timestamp)` in the shared database.
- **Sliding-Window Logic**: Expired entries older than `window_seconds` are pruned, and active attempts within the window are counted.
- **Cluster Synchronization**: Multiple API instances behind a load balancer share the same rate-limiting state.
- **Threshold**: Maximum 10 registration requests per 60-second window per remote IP. Excess requests immediately fail with HTTP 429 `TOO_MANY_REGISTRATION_REQUESTS`.
- **Resilience**: Thread-safe in-memory fallback engages if database is temporarily unreachable.

### 2.3 Secret Entropy, Key Rotation & Session Preservation
1. **Entropy vs. Length Evaluation**:
   - Length alone (e.g. 32 repeating `'a'`s) has 0.0 bits of Shannon entropy.
   - `evaluate_secret_entropy(secret)` evaluates Shannon entropy, total entropy bits, and unique character count.
   - In production, keys must have at least 32 characters, Shannon entropy >= 3.0 bits/char, and at least 10 unique characters.
2. **Zero-Downtime Key Rotation**:
   - `get_verification_keys()` returns both the primary `ZONATA_AUTH_SECRET` and the previous rotated secret `ZONATA_PREVIOUS_AUTH_SECRET`.
   - When keys are rotated, existing user sessions signed under the previous secret remain valid until their expiration.
   - Newly issued tokens are signed exclusively with the new primary secret.

### 2.4 Token Lifecycle & Revocation
- **Token Structure**: `base64url(payload).hexdigest(signature)`.
- **Expiration**: Explicit `exp` timestamp checked in constant-time.
- **Revocation Store**: `auth_revoked_tokens` table in the relational database.
- **Endpoint**: `POST /api/auth/revoke` invalidates active tokens.
- **Interceptor**: Every incoming request to protected routes queries the revocation store, rejecting blacklisted tokens with HTTP 401 `TOKEN_REVOKED`.

### 2.5 Direct Object Access (IDOR) & Tenant Boundaries
Every CRM endpoint enforces strict tenant ownership:
1. **Customer Ownership**:
   - `GET /api/crm/customers/:id`: Scoped with `WHERE customer_id = ? AND tenant_id = ?`. Returns 404 if belonging to another tenant.
   - `PATCH /api/crm/customers/:id`: Updates only if matching `tenant_id`. Returns 404 if belonging to another tenant.
   - `DELETE /api/crm/customers/:id`: Deletes customer and cascades only within `tenant_id`. Returns 404 if belonging to another tenant.
2. **Deal Ownership & Kanban Stage Changes**:
   - `GET /api/crm/deals/:id`: Scoped with `WHERE deal_id = ? AND tenant_id = ?`. Returns 404 if belonging to another tenant.
   - `PATCH /api/crm/deals/:id`: `update_deal_stage` verifies `rowcount > 0` matching `(deal_id, tenant_id)`. Returns 404 if belonging to another tenant.
   - `DELETE /api/crm/deals/:id`: Deletes only if matching `tenant_id`. Returns 404 if belonging to another tenant.
3. **Cross-Tenant Object Linking Rejection**:
   - `create_deal` verifies that the referenced `customer_id` exists in the caller's `tenant_id`.
   - Attempting to associate a deal in Tenant B with a customer in Tenant A raises `ValueError: Direct Object Access Violation` and returns HTTP 400.

---

## 3. Automated Test Evidence

The security implementation was verified across 43 automated test cases:

| Test Suite | Tests Run | Passed | Failed | Focus Area |
|---|---|---|---|---|
| `tests/test_direct_object_access_and_tenant_security.py` | 6 | 6 | 0 | IDOR rejection, foreign key injection prevention, secret entropy, key rotation, hash upgrades |
| `tests/test_production_auth_security.py` | 8 | 8 | 0 | PBKDF2 hashing, HMAC tamper resistance, rate limiting, token revocation, entropy guard |
| `tests/test_audit_remediation_security.py` | 29 | 29 | 0 | Anti-spoofing header rejection, webhook validation, cross-tenant isolation, baseline invariants |
| **TOTAL** | **43** | **43** | **0** | **100% Security Pass Rate** |

---

## 4. Formal Decision

| Evaluation Area | Verdict | Summary |
|---|---|---|
| **Authentication and Tenant Security** | **PASS** | PBKDF2 hashing, upgrade mechanics, HMAC tokens, distributed rate limiting, token revocation, anti-spoofing rejection, and IDOR direct object protections fully qualified. |
