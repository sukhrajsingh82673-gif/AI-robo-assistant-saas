# ZONATA V4 — ENTERPRISE COMPLIANCE EVIDENCE MAPPING
**SOC 2 Type II, ISO 27001, GDPR, CCPA, & HIPAA Technical Controls**

## 1. Compliance Control Mapping

| Standard | Control Reference | ZONATA V4 Implementation & Evidence |
|----------|-------------------|--------------------------------------|
| **SOC 2 Type II** | CC6.1 (Logical Access) | SCIM 2.0 provisioning, short-lived tokens, distributed revocation |
| **SOC 2 Type II** | CC6.6 (Boundary Protection) | Model DLP Firewall, Pre-Retrieval RAG SQL ACLs |
| **SOC 2 Type II** | CC7.2 (Incident Monitoring) | SecurityCenter with real-time killswitches and anomaly alarms |
| **ISO 27001:2022** | A.8.10 (Information Deletion) | Cryptographic purge certificates with zero-remnant index verification |
| **ISO 27001:2022** | A.8.12 (Data Leakage Prevention) | Outbound LLM DLP Firewall with regex sanitization |
| **GDPR** | Article 17 (Right to Erasure) | `DataLifecycleManager.execute_verified_purge` with evidence event |
| **GDPR** | Article 25 (Data Protection by Design) | Pre-Retrieval authorization; unauthorized data never enters LLM RAM |
| **HIPAA** | 164.312(b) (Audit Controls) | Merkle Evidence Ledger + Causal Data Lineage DAG |
