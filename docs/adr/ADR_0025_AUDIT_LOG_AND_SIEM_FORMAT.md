# ADR 0025: Audit Logging Architecture, SIEM Formats, and Hash-Chained Tamper Resistance

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 46 (No false compliance claims), Rule 48 (Break-glass is loud and sealed in evidence)

---

## 1. Context and Problem Statement
Enterprise compliance frameworks (SOC 2, ISO 27001, HIPAA, GDPR/DPDP) mandate immutable, verifiable audit logging of all administrative actions, approval events, security modifications, and break-glass occurrences. Concurrently, enterprise security teams require real-time log ingestion into SIEM platforms (Splunk, Datadog, Elastic, Wazuh, Google Chronicle).

## 2. Alternatives Considered

| Ingestion / Format Format | Standards & Licensing | Evaluation | Decision |
| :--- | :--- | :--- | :--- |
| **OpenTelemetry Logs (OTel OTLP/JSON)** | CNCF Standard (Apache-2.0) | Cloud-native standard, structured key-value attributes, seamless correlation with traces (4H). | **ADOPTED AS PRIMARY LOGGING TRANSPORT:** Built on the Step 4H OpenTelemetry foundation. |
| **Common Event Format (CEF) / Syslog (RFC 5424)** | ArcSight / IETF Standard | Traditional enterprise SIEM format. Universal compatibility with on-prem SIEM appliances. | **ADOPTED AS EXPORT ADAPTER:** Export transformer parses OTel audit events into CEF format on demand. |
| **CloudWatch / Stackdriver Proprietary** | Vendor specific | High vendor lock-in. | **REJECTED:** Violates sovereign portability rules. |

## 3. Decision
1. **Dual Audit Architecture:**
   - **Internal Cryptographic Ledger (`core/evidence_ledger.py`):** Authoritative, local, Merkle hash-chained ledger storing immutable proof blocks. Each block cryptographically seals previous block hashes, ensuring that any tampering, deletion, or backdating is mathematically detectable.
   - **External SIEM Streaming:** Structured OpenTelemetry Log streams emitted over OTLP gRPC/HTTP to the tenant's chosen collector.
2. **Standard Attribute Allow-List (Sanitization):**
   Logs strictly sanitize payload contents via `core/telemetry/sanitizer.py`. Prompt texts, credentials, personal access tokens, and decrypted secrets are replaced with `[REDACTED_CREDENTIAL]`.
3. **Mandatory High-Severity Audit Triggers:**
   The following events immediately generate an immutable evidence block AND a high-priority SIEM alert:
   - Break-glass credential access or emergency override.
   - Owner principal delegation or transfer attempt.
   - ActionGateway high-impact approvals, vetoes, or policy breaches.
   - Key rotation, unseal, or cryptographic parameter alteration.
   - Failed authentication brute-force spikes.

## 4. Consequences
- **Positive:** Complete alignment between internal mathematical proof (evidence ledger) and enterprise observability (SIEM); zero sensitive secret leaks into logging backends.
- **Negative:** Dual record generation requires background asynchronous dispatch to prevent latency spikes on API endpoints.
