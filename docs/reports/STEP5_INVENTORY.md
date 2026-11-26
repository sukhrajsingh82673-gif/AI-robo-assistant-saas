# STEP 5 SECURITY & TRUST INVENTORY

**Document Version:** 1.0.0  
**Generated Date:** 2026-11-23  
**Status:** COMPLETE AUDIT  
**Auditor Persona:** Antigravity (Systems Architect & Builder)  
**Verification Scope:** Step 5 Trust Layer Readiness (Rules 41–48)

---

## 1. Executive Summary & Inventory Matrix

| Subsystem / Component | Path / Location | Current Real Implementation | Status | Test Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **Authentication & Tokens** | `api_server.py`, `core/auth.py` | Bearer HMAC-SHA256 tokens, tenant header/claim validation, token revocation list | `EXISTS` | `tests/test_auth.py`, `tests/test_api_auth.py` |
| **Session Lifetime & 2FA** | `api_server.py`, `core/two_step_auth.py` | 8h session expiry, TOTP/SMS two-step challenges, brute-force rate limiters | `EXISTS` | `tests/test_two_step_auth.py` |
| **Role Tiers (RBAC)** | `core/auth.py` (`UserRole`) | `OWNER`, `EXECUTIVE`, `MANAGER`, `OPERATOR`, `AUDITOR`, `OBSERVER`, `SYSTEM_AGENT` | `EXISTS` | `tests/test_auth.py`, `tests/test_organization_model.py` |
| **Secret Vault** | `core/vault/vault.py`, `core/secret_vault.py` | `OriginBoundSecretVault` with tenant key derivation and strict destination origin checks | `EXISTS` | `tests/test_step3_credential_vault.py` |
| **Automation Signing Keys** | `core/automation_fabric/fabric.py` | HMAC signing keys for cross-node automated webhooks and task leases | `EXISTS` | `tests/test_universal_automation_fabric_qualification.py` |
| **Environment Secret Ingestion** | Environment variables across modules | 54 distinct environment variables read directly across core services | `PARTIAL` | Tested via env mocks, needs migration to `SecretsPort` |
| **Evidence & Audit Log** | `core/evidence_ledger.py`, `core/evidence_service.py` | Merkle hash-chained ledger, SHA-256 event hashing, tamper verification | `EXISTS` | `tests/test_at14_evidence_ledger.py`, `tests/test_stage2_foundations.py` |
| **Row-Level Security (RLS)** | `migrations/pg/*.sql` | 46 PostgreSQL tables with RLS ENABLED, 44 with RLS FORCED | `PARTIAL` | Tested in CI PostgreSQL jobs, 228 tables lack RLS |
| **Database Connection & Roles** | `core/db.py`, `docker/init-db-roles.sql` | `zonata_app` (DML), `zonata_worker`, `zonata_migrator` (DDL), `zonata_backup` defined | `PARTIAL` | Roles defined in SQL, app defaults to connection URL user |
| **Connection Pooling & RLS Scope**| `core/db.py` (`PostgresConnectionPool`) | Connection pooler with `set_config('zonata.tenant_id', %s, false)` (Session-scoped) | `PARTIAL` | **CRITICAL:** Needs refactor to `true` (Transaction-scoped) |
| **API Route Authorization** | `api_server.py` | 558 API routes audited: granular token validation, settings guards, approval barriers | `EXISTS` | Verified across test suite |

---

## 2. Authentication & Session Security Audit

### 2.1 Code Path & Mechanism
- **Core Implementation:** [core/auth.py](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/auth.py) and [api_server.py](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/api_server.py#L635-L668).
- **Mechanism:** Requests submit `Authorization: Bearer <token>` and optional `X-Tenant-ID`. `api_server.py._get_auth_context()` calls `UserManager.verify_token(token)`.
- **Tenant Isolation Check:** If `requested_tenant` differs from `token_tenant`, an immediate `AuthExceptions.TenantIsolationViolation` is thrown.
- **Fail-Closed:** Missing, expired, or malformed tokens raise `AuthExceptions.AuthenticationError` (HTTP 401/403). Anonymous access to protected endpoints is rejected.

### 2.2 Role Tiers
The system defines 8 role tiers in `core.auth.UserRole`:
1. `OWNER`: Sovereign administrator; approval authority, budget governance, company setup.
2. `EXECUTIVE`: High-level management; approval authority for medium-to-high risk actions.
3. `MANAGER`: Operational team lead; delegation and resource allocation.
4. `OPERATOR`: Executes workflows and standard operating tasks.
5. `AUDITOR`: Read-only access across compliance, audit logs, and ledger integrity.
6. `OBSERVER`: Read-only view for stakeholders.
7. `SYSTEM_AGENT`: Machine service account for automated background execution.
8. `GLOBAL_ADMIN`: Super-admin for cross-tenant maintenance (strictly isolated from tenant data).

### 2.3 Two-Step Sign-in & Session Lengths
- **Two-Step Sign-in:** Handled in `/api/auth/two-step/` using TOTP (RFC 6238) and SMS verification codes stored in `user_two_step_secrets`.
- **Session Lifetimes:** Default session token expiry is configured for 8 hours (28,800 seconds). High-privilege tokens can be configured for short windows (15 minutes).
- **Revocation:** `TokenRevocationStore` maintains an in-memory and database blacklist of invalidated JTI identifiers with expiry-based garbage collection.

---

## 3. Secret Vault & Key Material Audit

### 3.1 `enterprise_secret_vault`
- **Location:** Table `enterprise_secret_vault` defined in `migrations/pg/0030_origin_bound_credential_vault.sql` and manipulated by `core/vault/vault.py`.
- **Schema:**
  ```sql
  CREATE TABLE enterprise_secret_vault (
      secret_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      secret_name TEXT NOT NULL,
      secret_type TEXT NOT NULL,
      encrypted_payload TEXT NOT NULL,
      allowed_origins JSONB NOT NULL,
      privilege_level TEXT NOT NULL,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      expires_at TIMESTAMP WITH TIME ZONE,
      revoked BOOLEAN DEFAULT FALSE
  );
  ```
- **Guarantees:** Cryptographically encrypted payloads; origin-binding enforced by `OriginValidator` before injection; high-privilege credentials require human ActionGateway approval; plaintext export forbidden.

### 3.2 `automation_signing_keys.secret_key`
- **Location:** `automation_signing_keys` table used by `core/automation_fabric/fabric.py`.
- **Audit Result:** Contains cryptographic signing keys for distributed node handshakes and webhook verifications. Must be transitioned to OpenBao Transit engine in Sub-Step 5B to ensure zero plaintext keys at rest in the relational database.

### 3.3 Environment Variable Secret Reads
A comprehensive scan identified **54 environment variables** reading secrets, tokens, or private keys across the repository:
1. `ANTHROPIC_API_KEY`: Anthropic LLM provider key
2. `BRAVE_API_KEY`, `BRAVE_SEARCH_API_KEY`: Brave Search engine key
3. `GEMINI_API_KEY`, `GOOGLE_API_KEY`: Google Gemini provider keys
4. `GOOGLE_CLIENT_SECRET`: Google OAuth2 client secret
5. `GROQ_API_KEY`: Groq LPU inference key
6. `HERMES_API_KEY`: Hermes API key
7. `JWT_SECRET`, `SESSION_SECRET`, `ZONATA_AUTH_SECRET`: Web session & token HMAC keys
8. `KEYCLOAK_URL`: Keycloak identity provider endpoint
9. `KMS_MASTER_KEY`: Master envelope key for `KeyManagementPort`
10. `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`: Langfuse observability credentials
11. `LOCAL_ENVELOPE_KEY`: Interim local encryption key (to be purged in 5B)
12. `METRICS_AUTH_TOKEN`: Prometheus /metrics bearer token
13. `NEON_AI_GATEWAY_TOKEN`, `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`: Neon cloud integration tokens
14. `OPENAI_API_KEY`: OpenAI model access token
15. `OPENCLOUD_AUTH_TOKEN`: OpenCloud storage token
16. `OPENROUTER_API_KEY`: OpenRouter gateway key
17. `PMS_APP_KEY`, `PMS_CLIENT_SECRET`: Property Management System API credentials
18. `POSTGRES_PASSWORD`: PostgreSQL database root/user password
19. `POSTHOG_API_KEY`: PostHog analytics key
20. `QUICKBOOKS_CLIENT_SECRET`: QuickBooks accounting OAuth secret
21. `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`: Payment gateway credentials
22. `SECRET_VAULT_KEY`: Legacy vault master key
23. `SMS_PROVIDER_API_KEY`: Twilio / SMS provider auth key
24. `SSL_KEYFILE`, `TLS_KEY_PATH`: HTTPS / TLS private key paths
25. `STRIPE_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`: Stripe payment processing credentials
26. `TAVILY_API_KEY`: Tavily search engine API key
27. `URA_LEASE_SECRET`: Universal Resource Adapter lease HMAC key
28. `VAULT_TOKEN`: OpenBao / Vault root or service token
29. `ZONATA_APPROVAL_SECRET`: Cryptographic action approval HMAC secret
30. `ZONATA_BOOTSTRAP_SECRET`: First-boot company provisioning key
31. `ZONATA_EMERGENCY_RETIRE_PREVIOUS_KEY`: Key retirement trigger
32. `ZONATA_GOOGLE_CALENDAR_ACCESS_TOKEN`: Google Calendar OAuth token
33. `ZONATA_LLM_API_KEY`: Unified LLM Gateway bearer secret
34. `ZONATA_PREVIOUS_AUTH_SECRET`, `ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT`: Grace-period rotation secrets
35. `ZONATA_REQUIRE_EXPLICIT_SECRET`, `ZONATA_STRICT_AUTH`: Production security gate flags
36. `ZONATA_REVOKED_AUTH_SECRETS`, `ZONATA_REVOKED_KEY_FINGERPRINTS`: Key revocation list
37. `ZONATA_SETTINGS_MASTER_KEY`: System settings envelope encryption key
38. `ZONATA_SMTP_PASSWORD`: Outbound email delivery credential

---

## 4. Database Isolation, Roles & Connection Pooling Audit

### 4.1 Database Role Architecture
[docker/init-db-roles.sql](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docker/init-db-roles.sql) establishes four distinct roles:
1. `zonata_app`: DML only (`SELECT`, `INSERT`, `UPDATE`, `DELETE`). Connects at API runtime.
2. `zonata_worker`: DML on job queues, task states, and evidence ledger. Connects for background workers.
3. `zonata_migrator`: Holds DDL privileges (`CREATE TABLE`, `ALTER TABLE`). Executed exclusively by migration CI/CD.
4. `zonata_backup`: Read-only access with `REPLICATION` grant for physical backup and WAL streaming.

### 4.2 Row-Level Security (RLS) Coverage
- **Total Tables in PostgreSQL Schema:** 274 tables.
- **Tables with RLS Enabled:** 46 tables (including `agent_runs`, `action_approvals`, `company_spend_budgets`, `evidence_ledger`).
- **Tables with RLS Forced:** 44 tables (`ALTER TABLE ... FORCE ROW LEVEL SECURITY`).
- **Unprotected Tables:** 228 tables currently lack explicit RLS. These include global reference tables, legacy caches, and Agent Factory catalog tables. Sub-Step 5D will enforce tenant-partitioned RLS on all tenant data tables.

### 4.3 Connection Pooling & The Neon/PgBouncer Transaction Trap
- **Current Behavior in `core/db.py`:**
  ```python
  # core/db.py line 4026
  cursor.execute(
      "SELECT set_config('zonata.tenant_id', %s, false), "
      "set_config('zonata.company_id', %s, false)",
      (tenant_id, company_id)
  )
  ```
- **Vulnerability Identified:** The third argument is `false` (session-scoped).
  In transaction pooling mode (such as PgBouncer in transaction mode or Neon serverless pooling), consecutive transactions from different tenants may be dispatched to the same physical PostgreSQL backend connection. A session-scoped variable persists across transactions, causing potential tenant context bleed!
- **Mandated Remediation (Standing Rule 43):**
  Must be changed to `set_config('zonata.tenant_id', %s, true)` where `true` creates a transaction-scoped setting (equivalent to `SET LOCAL`) that is automatically wiped when the transaction commits or aborts.

---

## 5. API Authorization Surface Audit

Out of 558 API routes audited in `api_server.py`:
- **Public Endpoints (Unauthenticated):**
  - `/readyz`, `/metrics` (metrics requires token if `METRICS_AUTH_TOKEN` is set)
  - `/api/auth/oauth/google/config`, `/login`, `/callback`
  - `/api/auth/register`, `/api/auth/two-step/`
- **Authenticated Tenant Endpoints:**
  - Protected via `self._get_auth_context()`. Enforces cryptographic HMAC token verification, expiration check, and anti-spoofing tenant identity binding.
- **High-Privilege / Approval Endpoints:**
  - Protected via `self._approver_denied()`. Restricts access strictly to `OWNER`, `EXECUTIVE`, or `GLOBAL_ADMIN`.
- **System Settings Endpoints:**
  - Protected via `self._require_settings_permission()`. Rejects requests lacking explicit Executive or Owner clearance.

---

## 6. Audit & Evidence Log System

- **Architecture:** [core/evidence_ledger.py](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/evidence_ledger.py) and [core/evidence_service.py](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/evidence_service.py).
- **Integrity Mechanism:** Cryptographic Merkle tree structure where each event block stores:
  `block_hash = SHA256(previous_block_hash + event_payload + timestamp + nonce)`.
- **Verification:** `EvidenceLedger.verify_ledger_integrity()` walks the hash chain verifying that no records have been altered, injected, or removed.
- **Status:** Production-ready and verified in Steps 1 and 2. Sub-Step 5F will extend this into OpenTelemetry Log streaming and CEF export for SIEM integration.
