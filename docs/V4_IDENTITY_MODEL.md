# ZONATA V4 — ENTERPRISE IDENTITY & DIRECTORY SYNCHRONIZATION MODEL
**Enterprise Identity Federation, SCIM 2.0, Short-Lived Tokens, & Session Revocation**

## 1. Identity Architecture Overview
ZONATA V4 treats identity as an immutable cryptographic claim, not an assertion of authority. Every actor interacting with ZONATA—whether human executive, AI Employee, API service, or autonomous agent—must possess an active, verified enterprise identity registered within the Enterprise Identity Gateway (`core/identity_gateway.py`).

### Identity Types
- `HUMAN`: Corporate employees, managers, administrators, and auditors.
- `AI_EMPLOYEE`: Autonomous agents instantiated through the AI Employee OS.
- `SERVICE`: Microservices, webhooks, and backend processes.
- `TOOL`: Bound execution tool instances.
- `INTEGRATION`: Third-party SaaS connectors (Nango, Salesforce, Jira, etc.).

---

## 2. Directory Synchronization & SCIM 2.0
The Identity Gateway exposes SCIM 2.0 endpoints for automated synchronization with corporate Identity Providers (Okta, Azure AD / Microsoft Entra, Google Workspace):
- `POST /scim/v2/Users`: Provision user or employee.
- `PATCH /scim/v2/Users/{id}`: Update department, group, role, or active status.
- `DELETE /scim/v2/Users/{id}`: Deprovision and offboard identity immediately.

When SCIM deprovisions a user:
1. The user's status in `enterprise_identities` is set to `OFFBOARDED`.
2. A distributed revocation key (`revoked_identity:{id}`) is published to Redis/Coordination with a 7-day TTL.
3. A killswitch event is triggered immediately across all distributed cluster nodes.
4. Any active agent sessions, missions, or queued actions associated with this identity are canceled.

---

## 3. Token Semantics & Verification
- **Token Format**: Cryptographically signed HMAC-SHA256 tokens with key ID (`kid`) rotation.
- **Short Lifetime**: Default token lifetime is 3600 seconds (1 hour). High-risk operations require JIT elevation tokens with a 300-second (5-minute) lifetime.
- **Pre-Execution Invariant Verification**: Every token verification checks:
  1. Cryptographic signature against active rotating key.
  2. Expiration timestamp (`exp > now`).
  3. Distributed session revocation cache (`coordination.get_idempotency_key(revoked_identity:{id}) != 'REVOKED'`).
  4. Real-time database status (`status == 'ACTIVE'`).

---

## 4. Constitutional Invariants
- `IDENTITY != AUTHORITY`: Holding a valid token confirms *who* the actor is, not what they may do. Every request is independently evaluated by Policy Engine V2.
- `OFFBOARDED_IDENTITY != ACTIVE_AUTHORITY`: An offboarded user or agent cannot issue new tokens, renew expired tokens, or execute actions even if holding cached credentials.
