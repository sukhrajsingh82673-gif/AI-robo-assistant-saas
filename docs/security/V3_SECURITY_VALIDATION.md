# ZONATA V3 — Security Architecture & Threat Model Validation

## 1. Zero-Trust Security Invariants
- **Authentication:** HMAC SHA-256 session tokens with mandatory claims (`tenant_id`, `user_id`, `role`, `exp`). Token revocation store backed by distributed coordination.
- **Fail-Closed Configuration:** `core.production_config.ProductionConfig` rejects weak dev secrets, unencrypted strings, or missing TLS settings in staging/production environments.
- **Action Ingress:** No mutation may bypass `ZonataActionGateway` (enforcing the canonical 20-step execution pipeline).
- **Execution Boundaries:** Unprivileged user containers (`UID 10001`), root filesystem read-only compatibility, dropped Linux capabilities (`ALL`).

---

## 2. Threat Vector Penetration Test Results
| Threat ID | Threat Vector | Defense Mechanism | Tested Behavior | Result |
|---|---|---|---|---|
| **THR-01** | Missing / Forged Bearer Token | `ProductionAPIHandler` token verification | HTTP 401 UNAUTHORIZED returned | PASS |
| **THR-02** | Tenant Header Spoofing | Cross-claim token vs header verification | HTTP 403 TENANT_SPOOFING_ATTEMPT | PASS |
| **THR-03** | Command Queue Ingestion Bypass | Unvalidated parameters / direct bus write | ActionEnvelope strict schema validation | PASS |
| **THR-04** | AST Injection in Synthesized Tools | AST Visitor blocking `eval`, `os.system` | AST_SECURITY_VIOLATION raised | PASS |
| **THR-05** | Merkle Audit Trail Alteration | SHA-256 previous-hash chain validation | `TAMPER_DETECTED` raised immediately | PASS |
| **THR-06** | Runaway Agent Creation Flood | `AgentResourceGovernor` plan quotas | Rejection at tier ceiling (e.g. 25, 500) | PASS |

---

## 3. Operational Classification
- **Threat Defense & Cryptographic Gates:** `REAL_LOCAL_INFRASTRUCTURE`
- **External Red Team Certification:** `SIMULATED` (Internal adversarial suite)
