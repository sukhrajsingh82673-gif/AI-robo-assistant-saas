# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Distributed Security Threat Model & Attack Surface Analysis

---

### 1. Security Architecture & Threat Vectors
The ZONATA Universal AI Company Operating System controls real-world enterprise infrastructure, financial tools, SaaS accounts, browser sessions, and autonomous code execution environments. This document outlines the STRIDE threat analysis, trust boundaries, and constitutional defense mitigations across the distributed control and execution planes.

```
+-----------------------------------------------------------------------------------+
| TRUST BOUNDARY 0: External Clients / Public Internet                             |
| (WAF, Rate Limiting, DDoS Protection, TLS 1.3 Termination)                        |
+-----------------------------------------------------------------------------------+
                                         |
+-----------------------------------------------------------------------------------+
| TRUST BOUNDARY 1: API Control Plane                                               |
| (HMAC-SHA256 Token Validation, Tenant Cryptographic Binding, No Header Trust)    |
+-----------------------------------------------------------------------------------+
       |                                     |                              |
+--------------------+             +--------------------+         +-----------------+
| TRUST BOUNDARY 2:  |             | TRUST BOUNDARY 3:  |         | TRUST BOUNDARY 4|
| Database / Redis   |             | Central Action GW  |         | Evidence Ledger |
| (Encrypted at rest,|             | (20-Step Pipeline, |         | (PostgreSQL WAL,|
|  Scoped Tenant IDs)|             |  Risk Classifier)  |         |  Merkle Proofs) |
+--------------------+             +--------------------+         +-----------------+
                                             |
+-----------------------------------------------------------------------------------+
| TRUST BOUNDARY 5: Execution Plane / Workers (Least Privilege, Sandboxed)          |
| [OpenHands Sandbox]   [Browser Container]   [MCP Gateway]   [Nango Vault Broker]  |
+-----------------------------------------------------------------------------------+
                                             |
+-----------------------------------------------------------------------------------+
| TRUST BOUNDARY 6: External World (Unverified APIs, Untrusted Web Data)            |
+-----------------------------------------------------------------------------------+
```

---

### 2. STRIDE Threat Matrix & Mitigations

| Category | Threat Scenario | Impact | Primary Invariant / Defense | Technical Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **Spoofing** | Attacker injects `X-Tenant-ID: victim_corp` in HTTP headers to access victim tenant data. | Cross-tenant data breach, account takeover. | `UNAUTHENTICATED REQUEST != TENANT AUTHORITY` | Token signature cryptographically encodes `tenant_id`. API server rejects header mismatches with `403 Forbidden (TENANT_SPOOFING_ATTEMPT)`. |
| **Spoofing** | Compromised agent impersonates a parent agent or AI CEO to approve high-risk actions. | Unauthorized financial transfer, policy bypass. | `AGENT != AUTHORITY` | Approvals require cryptographic signatures from an authorized human role (`OWNER`), verified against DB authority records with parameter-bound leases. |
| **Tampering** | Rogue agent attempts to mutate `core/policy.py` or governance engine files to disable killswitch. | Total control plane compromise. | `SELF_MODIFICATION_DEFENSE` | Static and runtime self-modification blocks on immutable governance modules; rootless container sandboxes with read-only root filesystems. |
| **Tampering** | Concurrent database writers or network partition splits Merkle evidence history into divergent chains. | Tampered audit logs, non-verifiable causality. | `CHECKPOINT != EVIDENCE` | Transactional PostgreSQL evidence append with strict sequential ordering (`event_index`), previous-hash binding, and distributed locks. |
| **Repudiation**| External API provider claims webhook was not received or agent denies executing mutating action. | Audit failure, unresolvable business disputes. | `ACTION != EVIDENCE (WITHOUT PROOF)` | Canonical `ActionEnvelope` logged with SHA-256 parameter hashes, timestamps, digital signatures, and Merkle ledger inclusion proofs. |
| **Information Disclosure** | LLM prompt injection extracts vaulted OAuth tokens or API keys from memory/prompts. | Credential theft, unauthorized API access. | `ZERO_SECRET_PERSISTENCE` | All credentials vaulted; agents only handle opaque handles (`cred_...`). Ephemeral JIT token leasing with automatic redaction filter on all logs, prompts, and traces. |
| **Information Disclosure** | Cross-tenant database queries leaking competitor data via un-scoped SQL filters. | Severe confidentiality violation. | `TENANT_ISOLATION_MANDATORY` | All repository queries parameterized with mandatory `tenant_id` clauses; automated negative test suites verifying cross-tenant access denial. |
| **Denial of Service** | Rogue agent spawns recursive tree of child agents exhausting CPU, RAM, and DB pools. | Host crash, system-wide outage. | `ANTI_EXPLOSION_CONTROLS` | Hard server-side quotas: max 100 agents/tenant, max 5 child agents/parent, max delegation depth 4, and admission control in database connection pools. |
| **Denial of Service** | Host disk full (`ENOSPC`) due to unchecked browser screenshot dumps or sandbox artifacts. | Database corruption, service disruption. | `STORAGE_GOVERNOR_ACTIVE` | Real-time disk capacity monitoring with automated tier alerts (70% WARN, 80% CRITICAL, 90% EMERGENCY) and automatic pruning of expired sandbox data. |
| **Elevation of Privilege** | Agent creates dynamic tool containing `os.system('curl ... | bash')` to gain root shell. | Host escape, arbitrary code execution. | `TOOL != PERMISSION` | Two-phase tool validation: 1) AST static scanning rejecting dangerous imports (`os`, `subprocess`, `socket`); 2) Execution inside rootless, non-privileged containers with no network egress. |
| **Elevation of Privilege** | Workflow replay or Temporal retry blindly repeats payment or destructive API mutation. | Duplicate financial charges, double booking. | `RETRY != SAFE REPLAY` | Idempotency key tracking (`tenant_id + idempotency_key + action_hash`); mutations yielding ambiguous responses transition to `UNKNOWN_OUTCOME` for reconciliation. |

---

### 3. Trust Boundary Transitions

1. **Boundary 0 → 1 (Ingress)**:
   - WAF sanitization: payload size capped at 10MB; standard security headers injected (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
   - Authentication gateway verifies HMAC-SHA256 signature and checks token revocation status in `auth_revoked_tokens`.
2. **Boundary 1 → 3 (Action Gateway)**:
   - Every mutation is translated into an `ActionEnvelope`.
   - The central `ZonataActionGateway` executes the non-bypassable 20-step verification pipeline: Tenant Resolution → Risk Classification → Policy Clearance → Authority Check → Idempotency Verification → Execution → Reality Observation → Evidence Sealing.
3. **Boundary 3 → 5 (Worker Sandboxes)**:
   - OpenHands, Browser Use, and Tool Factory run inside isolated container sandboxes.
   - Filesystem: read-only root, ephemeral `/tmp` with memory limits.
   - Network: egress allowlisting only; localhost, private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and cloud metadata endpoints (`169.254.169.254`) are strictly blocked.
4. **Boundary 5 → 6 (External Egress)**:
   - Nango connections use short-lived OAuth tokens retrieved via the Credential Broker.
   - Ambiguous external responses (e.g. HTTP 500, network timeout, 429) transition to `UNKNOWN_OUTCOME` and mandate active reconciliation before any further action is permitted.
