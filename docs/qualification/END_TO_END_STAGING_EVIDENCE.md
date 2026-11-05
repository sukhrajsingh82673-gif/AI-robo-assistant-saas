# END-TO-END STAGING EVIDENCE & WORKFLOW MATRIX
**ZONATA Enterprise Autonomous SaaS**
**Document ID**: E2E-STG-EVD-2026-10-13  
**Status**: STAGED & FUNCTIONALLY AUDITED  
**Auditor**: End-to-End Workflow Verification Lead  

---

## 1. Executive Workflow Assessment

This document inventories the full 38-route application interface, API endpoints, and database interactions across the ZONATA Enterprise SaaS platform.

| Qualification Dimension | Status | Audit Verdict |
| :--- | :---: | :--- |
| **API End-to-End Workflows** | **PASS** | Customer CRUD, deal pipelines, auth tokens, RBAC & settings verified via integration suites. |
| **Persistence Across Restarts** | **PASS** | Relational data persistence verified in database tables (`crm_customers`, `crm_deals`, `users`, `settings_store`). |
| **Browser Staging Execution** | **BLOCKED** | Live browser-to-ingress execution blocked pending deployed staging domain and TLS endpoint. |
| **Connector Execution Authenticity** | **CLASSIFIED** | All connectors strictly classified across the mandatory 5-tier status taxonomy. |

---

## 2. Critical User Journey Verification Matrix

| Workflow Journey | Path & Endpoint Trace | Backend & Database Mutation | Persistence Verification | Status |
| :--- | :--- | :--- | :--- | :---: |
| **1. Clean Registration & Tenant Provisioning** | `POST /api/auth/register` | Inserts `tenants`, `users`, `auth_credentials` | Database row query on restart | **PASS** |
| **2. Authentication & Scoped Token Issuance** | `POST /api/auth/login` | Dual-axis rate check, PBKDF2 verify (600k iters), issues HMAC-SHA256 Bearer token | Validated via `POST /api/auth/me` | **PASS** |
| **3. Session Revocation / Logout** | `POST /api/auth/revoke` | Inserts `auth_revoked_tokens` table | Subsequent requests fail with HTTP 401 | **PASS** |
| **4. Customer Relational CRUD** | `POST/GET/PUT/DELETE /api/crm/customers/:id` | Parameterized SQL on `crm_customers` with `tenant_id` scoping | Persists across test suites | **PASS** |
| **5. Deal Creation & Customer Association** | `POST /api/crm/deals` | Validates customer ownership; inserts `crm_deals` | Verified in Kanban pipeline | **PASS** |
| **6. Deal Stage Mutation & Partial Updates** | `PUT/PATCH /api/crm/deals/:id` | Validates deal ownership; updates `stage`, `value` in `crm_deals` | Real-time Kanban pipeline update | **PASS** |
| **7. Enterprise Settings Governance** | `PUT /api/settings/key/:key` | Parameterized mutation in `settings_store` with actor audit log | Audited in `settings_audit_events` | **PASS** |
| **8. Financial & Pipeline Empty States** | `GET /api/overview` | Honest empty states: 0 ARR, 0 deals when database is clean | No fabricated metrics displayed | **PASS** |
| **9. Consequential Approvals Gate** | `POST /api/a2a/approvals` | RBAC check: requires `OWNER` or `EXECUTIVE` | Blocks unauthorized operators | **PASS** |

---

## 3. Connector Authenticity & Execution Isolation Taxonomy

To eliminate ambiguity between simulated components and genuine live integrations, all connectors and runtime engines are classified under the mandatory 5-tier taxonomy:

| Component / Subsystem | Functional Scope | Classification | Runtime Proof / Constraint |
| :--- | :--- | :---: | :--- |
| **Enterprise CRM Database** | Customers & Deals persistence | `LIVE_CONFIGURED` | Full relational SQL operations in `crm_customers` and `crm_deals`. |
| **Multi-Tenant IAM & Tokens** | Authentication & RBAC | `LIVE_CONFIGURED` | HMAC-SHA256 sovereign key verification & PBKDF2-HMAC-SHA256 (600k). |
| **Distributed Rate Limiter** | Throttling & Brute-force defense | `LIVE_CONFIGURED` | Backed by `auth_rate_limits` table with scoped write transactions. |
| **PostgreSQL 16 Engine** | External production persistence | `LIVE_NOT_CONFIGURED` | Dialect translation active; blocked pending staging connection. |
| **Nango Integration Runtime** | External SaaS OAuth connectors | `TEST_ONLY` | In-memory integration harnesses; live OAuth credentials unconfigured. |
| **OpenHands Sandbox Engine** | Autonomous task execution | `SIMULATED` | Deterministic simulation fixtures; isolated from host OS. |
| **A2A Multi-Agent Gateway** | Inter-agent delegation | `SIMULATED` | Local mock agents; live distributed NATS transport unconfigured. |
| **Host Shell Connector** | Arbitrary host OS command execution | `NOT_IMPLEMENTED` | **Strictly prohibited & disabled** in production mode (`ZONATA_ALLOW_HOST_SHELL=0`). |
