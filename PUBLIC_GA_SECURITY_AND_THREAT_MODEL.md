# URA / ZONATA — PUBLIC GA SECURITY ARCHITECTURE & THREAT MODEL

**Target System:** URA / ZONATA Universal AI Company Operating System  
**Classification:** Confidential / System Security Architecture & Threat Model  
**Authoritative Version:** 1.0.0-GA Security Hardening Specification  
**Last Updated:** October 25, 2026  

---

## 1. Security Architecture Overview

The ZONATA platform operates as a multi-tenant enterprise operating system running autonomous AI agents, financial ledgers, and executive decision pipelines. Its security architecture is founded on **Zero Trust**, **Cryptographic Auditability**, and **Strict Multi-Tenant Isolation**.

```
+--------------------------------------------------------------------------+
|                     EXTERNAL REQUESTS (HTTPS / TLS 1.3)                  |
+--------------------------------------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------+
| REVERSE PROXY & RATE LIMITING (IP & Account-Level Token Bucket Quotas)   |
+--------------------------------------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------+
| AUTHENTICATION & AUTHORIZATION GATEWAY                                   |
| - PBKDF2-HMAC-SHA256 Password Verification                               |
| - HMAC-SHA256 Signed Bearer Tokens                                       |
| - In-Memory & Distributed Token Revocation Store                         |
| - Multi-Tenant Context Injection (tenant_id, company_id, role)           |
+--------------------------------------------------------------------------+
          |                                               |
          v                                               v
+-------------------------------+               +--------------------------+
| GOVERNED AI AGENT RUNTIME     |               | RELATIONAL DATA PLANE    |
| - Authority Levels (0 to 4)   |               | - Neon PostgreSQL 16     |
| - Pre-Execution Policy Checks |               | - Strict tenant_id RLS   |
| - Spending Limits & Budgets   |               | - Parameterized Queries  |
| - Human Approval Pipeline     |               | - Zero SQLite Fallback   |
+-------------------------------+               +--------------------------+
          |                                               |
          +-----------------------+-----------------------+
                                  |
                                  v
+--------------------------------------------------------------------------+
| IMMUTABLE MERKLE EVIDENCE LEDGER                                         |
| - Continuous SHA-256 Hash Chaining                                       |
| - Epistemic Honesty: Unknowns recorded as PENDING_EVIDENCE                |
| - Crash-Safe Physical Flush & Exclusive File Locking (fcntl.flock)       |
+--------------------------------------------------------------------------+
```

---

## 2. STRIDE Threat Model Analysis

| Threat Category | Potential Attack Vector | Platform Defense Mechanism | Verification Status |
|:---|:---|:---|:---:|
| **Spoofing Identity** | Attacker crafts forged Bearer token or impersonates another tenant user | Tokens signed using secret HMAC-SHA256; token_id validated against `auth_revoked_tokens` table on every request. | **PASS** |
| **Tampering with Data** | Attacker modifies financial ledger or historical evidence | All evidence packages sealed with previous-hash cryptographic chain; financial entries enforced via immutable double-entry journals. | **PASS** |
| **Repudiation** | Rogue agent or executive denies taking destructive action | Every action recorded in Merkle evidence ledger with actor ID, timestamp, deliverable digest, and digital signature. | **PASS** |
| **Information Disclosure** | Cross-tenant data leakage via IDOR or missing tenant filter | Every SQL query strictly binds `tenant_id = ?` parameter. Tested via `test_tenant_spoofing_defense`. | **PASS** |
| **Denial of Service** | Resource exhaustion via API flood or concurrent task spawning | Rate limiting (60/120 RPM per tenant) + strict concurrency leases (4 pilot / 10 GA leases per tenant) with automatic lease reclamation. | **PASS** |
| **Elevation of Privilege** | Agent synthesizes new tools to bypass constitutional boundaries | `GovernedToolFactory` enforces AST code parsing and forbids `eval()`, `exec()`, `raw_secrets`, or filesystem escapes. | **PASS** |

---

## 3. Cryptographic Standards & Secrets Management

1. **Password Storage:**
   * **Algorithm:** PBKDF2 with HMAC-SHA256.
   * **Salt:** Cryptographically random 16-byte salt per user (`uuid.uuid4().hex[:16]`).
   * **Iterations:** 100,000 iterations minimum.
2. **Session Security:**
   * **Token Format:** Signed Bearer tokens (`payload.signature`).
   * **Signature Algorithm:** HMAC-SHA256 using server-side secret key.
   * **Token Expiration:** Default 7 days (`604,800` seconds).
   * **Revocation:** Explicit token revocation via `/api/auth/logout` writing to `auth_revoked_tokens` table.
3. **Database Connection String Sanitization:**
   * Every log entry and diagnostic error string passes through `sanitize_db_url()`.
   * Passwords in `postgres://user:password@host/db` connection strings are replaced with `***`.
4. **Git Repository Sanitization:**
   * `.env`, `.env.local`, and credential files are registered in `.gitignore`.
   * Automated scans confirm 0 exposed production credentials in git history.

---

## 4. Multi-Tenant Isolation Controls

* **Logical Tenant Partitioning:** Every tenant has a unique, cryptographically generated `tenant_id` (`tnt_[a-f0-9]{8}`).
* **Query Binding Rule:** No query in `core/` or `api_server.py` may execute without explicitly filtering by `tenant_id`.
* **Cross-Tenant Mutation Defense:** Any request attempting to modify resources belonging to another `tenant_id` raises `AuthExceptions.PermissionDenied` or returns HTTP 403 Forbidden.
* **Testing:** Validated by `tests/test_adversarial_security_and_chaos.py::test_01_tenant_spoofing_defense` and `tests/test_fresh_user_experience_and_clean_ui.py::test_05_no_cross_tenant_pollution_from_test_tenants`.

---

## 5. Emergency Governance & Kill Switches

1. **Emergency Quarantine (`emergency_quarantine`):**
   * Instantly halts all autonomous agent execution across the entire platform.
   * Forces all pending actions to fail closed.
2. **Autonomous Spawning Kill Switch (`autonomous_spawning`):**
   * Disables dynamic agent instantiation via `DynamicAgentFactory`.
3. **Financial Spending Hard Cap (`ceo_spending_limit` / `cost_spend_cap`):**
   * Restricts maximum allowable spending per mission without explicit human executive sign-off.
