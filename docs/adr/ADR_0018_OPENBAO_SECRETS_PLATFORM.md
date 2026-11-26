# ADR 0018: Adoption of OpenBao as Authoritative Enterprise Secrets Platform

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 41 (No plaintext secrets or keys in code, database, logs, or reports)

---

## 1. Context and Problem Statement
ZONATA previously relied on interim secret and key providers (`LocalEnvelopeKeyProvider`, `OriginBoundSecretVault` with local HMAC, and raw environment variables). As dictated by Rule 41, all interim local encryption providers must be removed from the production code path, and `ZONATA_ALLOW_DEGRADED` can no longer cover key management or secret storage. The platform requires a dedicated, sovereign secrets manager supporting:
- Tenant-isolated secret namespaces.
- Cryptographic Transit engine (encryption-as-a-service without exposing keys to clients).
- Dynamic, short-lived database credentials.
- Auto-unseal and dual-control operational workflows.

## 2. Alternatives Considered

| Platform | License | Compatibility & Features | Disqualification / Adoption Rationale |
| :--- | :--- | :--- | :--- |
| **OpenBao (Linux Foundation)** | **MPL-2.0** | Full Vault API compatibility, Transit engine, KV v2, namespaces, PKI engine, auto-unseal plugins, quantum-ready TLS. | **ADOPTED (Lead):** Truly open-source fork of Vault under Linux Foundation governance. Zero commercial licensing traps. Native support for cryptographic transit and dynamic credentials. |
| **HashiCorp Vault** | **BSL 1.1** | Industry standard, complete feature set. | **REJECTED:** Business Source License (BSL 1.1) violates standing rules against restrictive non-open-source licenses in sovereign deployments. |
| **Cloud KMS + Secrets (AWS/GCP)** | Proprietary API | Managed service, automated durability. | **REJECTED as Primary:** Violates sovereign portability requirement. Can serve only as an optional underlying auto-unseal KMS plugin. |
| **Infisical** | AGPL-3.0 / Commercial | Developer secrets manager. | **REJECTED:** AGPL-3.0 license imposes severe boundary risks for backend software integration. |

## 3. Decision
1. **Adopt OpenBao (MPL-2.0)** as the authoritative backend behind ZONATA's `SecretsPort` (`core/ports/secrets.py`).
2. **Transit Engine:** All high-security encryption operations (data at rest, settings envelopes, token HMACs) will delegate to the OpenBao Transit engine (`transit/`). Application workers never hold master key material in memory.
3. **Tenant Namespaces:** Multi-tenancy is enforced through dedicated paths/namespaces: `secret/data/tenants/{tenant_id}/`.
4. **Unseal Strategy:**
   - **Production:** Cloud KMS auto-unseal (AWS KMS, GCP Cloud KMS, or Azure Key Vault) via OpenBao unseal plugins.
   - **Sovereign Standalone / Air-gapped:** Shamir's Secret Sharing (3-of-5 threshold). Recovery key shards held by designated human custodians (Company Owner + 4 Board/Executive trustees).
5. **Fail-Closed Policy:** If OpenBao is sealed or unreachable, all cryptographic and credential operations fail closed immediately.

## 4. Consequences
- **Positive:** Complete elimination of plaintext secrets and local encryption keys from application code and relational databases; full audit trail of secret access within OpenBao access logs.
- **Negative:** Requires running OpenBao container/service in staging and production topologies; unseal orchestration must be automated in CI/CD environments.
