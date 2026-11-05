# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Data Classification & Enterprise Data Governance Model

---

### 1. Data Classification Tiers

| Classification Level | Definition | Examples | Retention Policy | Storage & Encryption |
| :--- | :--- | :--- | :--- | :--- |
| **RESTRICTED** | Credentials, private keys, financial tokens, payment PANs | OAuth refresh tokens, Stripe secret keys | Expire immediately post-use; vaulted | AES-GCM 256 + KMS; never logged |
| **CONFIDENTIAL** | Proprietary customer business records, strategy documents, employee data | Mission specs, Letta agent memory, HR records | Active mission + 7 years | PostgreSQL encrypted at rest |
| **SENSITIVE** | Execution logs, browser DOM captures, tool inputs/outputs | Run artifacts, error dumps, intermediate traces | 90 Days default | S3 tenant-partitioned storage |
| **INTERNAL** | System health vitals, anonymous metrics, component topologies | Pod heartbeats, aggregated latency metrics | 1 Year | Distributed telemetry database |
| **PUBLIC** | Open-source API schemas, public agent cards | `/.well-known/agent-card.json`, OpenAPI specs | Indefinite | Public edge CDN / API |

---

### 2. Tenant Privacy & Legal Compliance Boundaries
* **Cryptographic Data Partitioning**: All records require mandatory `tenant_id` columns with cascading foreign keys.
* **Right to be Forgotten (GDPR / CCPA)**: Hard deletion is supported for user personal records, while legal audit trails in `merkle_evidence_events` anonymize PII through one-way cryptographic SHA-256 digests.
* **Auditability**: Every data mutation and access to restricted tokens generates an attributable event sealed into the distributed Merkle ledger.
