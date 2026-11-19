# ZONATA V5 — COMPLIANCE EVIDENCE MATRIX & MATURITY TAXONOMY
**Granular Audit Mapping for SOC 2, ISO 27001, GDPR, & HIPAA: Controls vs Evidence vs Certification**

---

## 1. Executive Summary & Legal Forensic Mandate

In strict compliance with Section 49 of the V5 mandate (*"A mapping document is NOT certification. Separate: CONTROL IMPLEMENTED, CONTROL TESTED, CONTROL EVIDENCED, INDEPENDENTLY AUDITED, CERTIFIED. Never use 'compliant' as a blanket claim unless legally/technically justified"*):

**Authoritative Compliance Ruling**:
- ZONATA does **not** claim blanket "SOC 2 Certified", "HIPAA Compliant", or "ISO Certified". A software platform cannot legally self-certify compliance; certification requires formal audit periods and third-party attestation by accredited accounting/auditing bodies.
- ZONATA provides **audited technical mechanisms, automated tests, and Merkle cryptographic evidence trails** that satisfy technical control prerequisites.

---

## 2. Five-Stage Compliance Maturity Taxonomy

Every regulatory control in ZONATA is classified into one of five mutually exclusive maturity tiers:

```
[1. CONTROL IMPLEMENTED]    -> Code and architecture exist in repository.
[2. CONTROL TESTED]         -> Automated tests verify positive and negative behavior.
[3. CONTROL EVIDENCED]      -> Immutable Merkle events emitted to audit ledger.
[4. INDEPENDENTLY AUDITED]  -> Formal third-party evaluation by accredited firm.
[5. CERTIFIED]              -> Official attestation certificate issued (e.g. SOC 2 Type II report).
```

---

## 3. Granular Regulatory Control Evaluation Matrix

| Framework & Control ID | Regulatory Requirement | Architectural Subsystem | Maturity Status | Technical Evidence & Verification | Gaps / Third-Party Action Required |
|:-----------------------|:-----------------------|:------------------------|:---------------:|:----------------------------------|:------------------------------------|
| **SOC 2 CC6.1** | Logical Access Controls & Identity Authentication | `core/identity_gateway.py` | **CONTROL EVIDENCED** | SCIM 2.0 lifecycle, OIDC tokens, sub-10ms revocation (`test_scim_lifecycle`) | Independent CPA audit of production operating procedures (Type II window) |
| **SOC 2 CC6.3** | Role-Based & Least Privilege Authorization | `core/policy_engine_v2.py` | **CONTROL EVIDENCED** | 8-dimensional ABAC evaluation; fail-closed default | Customer-defined organizational RBAC role matrix approval |
| **SOC 2 CC6.6** | Boundary Protection & Network Segmentation | `k8s/network-policies.yaml` | **CONTROL TESTED** | Default-deny network policies, container capabilities dropped | Cloud VPC peering and firewall configuration review |
| **SOC 2 CC7.2** | Anomaly Detection & Threat Monitoring | `core/security_center.py` | **CONTROL EVIDENCED** | Automated killswitches, threat alarms in evidence ledger | 24/7 Security Operations Center (SOC) operational runbooks |
| **ISO 27001 A.8.2** | Information Classification | `core/data_classification_engine.py` | **CONTROL EVIDENCED** | 5-level sensitivity classification, admin policy floor invariant | Enterprise information security policy document alignment |
| **ISO 27001 A.8.10** | Information Deletion & Purging | `core/data_lifecycle_manager.py` | **CONTROL EVIDENCED** | Multi-layer verified deletion proof (`docs/V5_DATA_DELETION_PROOF.md`) | Physical media destruction certifications from cloud provider |
| **ISO 27001 A.8.24** | Use of Cryptography & Key Management | `core/secret_manager.py` | **CONTROL EVIDENCED** | AES-256-GCM, HMAC-SHA256, TLS 1.3 only, ephemeral memory keys | Hardware Security Module (HSM) FIPS 140-2 Level 3 validation |
| **GDPR Art. 17** | Right to Erasure ("Right to be Forgotten") | `core/deletion_verifier.py` | **CONTROL EVIDENCED** | Multi-layer purge across DB, vector chunks, cache, and scratch | Customer Data Processing Addendum (DPA) execution |
| **GDPR Art. 25** | Data Protection by Design & Default | `core/knowledge_gateway.py` | **CONTROL EVIDENCED** | Pre-retrieval authorization; 0 unauthorized records in RAM | Legal counsel DPIA (Data Protection Impact Assessment) sign-off |
| **GDPR Art. 30** | Records of Processing Activities | `core/data_lineage_graph.py` | **CONTROL EVIDENCED** | Directed acyclic graph linking triggers, agents, models, and tools | Customer corporate DPO (Data Protection Officer) record audit |
| **HIPAA 164.312(a)** | Access Control & Unique User Identification | `core/enterprise_idp_client.py` | **CONTROL EVIDENCED** | Unique SCIM IDs, M2M service tokens, anti-laundering approval | Business Associate Agreement (BAA) with model & cloud vendors |
| **HIPAA 164.312(b)** | Audit Controls & Non-Repudiation | `core/evidence_ledger.py` | **CONTROL EVIDENCED** | Merkle append-only ledger with cryptographic hash chains | Periodic formal audit log review procedures |
| **HIPAA 164.312(e)** | Transmission Security (Data in Transit) | `core/model_data_firewall.py` | **CONTROL EVIDENCED** | Sovereign barrier stopping PHI from untrusted external models | End-to-end mTLS certificate verification on cloud egress |

---

## 4. Specific Action Items to Attain Formal Certification

```
[ ] Engage accredited AICPA accounting firm for SOC 2 Type I readiness assessment
[ ] Complete 6-month continuous operational observation window for SOC 2 Type II attestation
[ ] Execute formal Business Associate Agreements (BAAs) with OpenAI, Anthropic, or AWS/GCP
[ ] Perform external third-party penetration test and red-team engagement (CREST certified)
[ ] Appoint external Data Protection Officer (DPO) and finalize GDPR Article 28 DPA templates
```
