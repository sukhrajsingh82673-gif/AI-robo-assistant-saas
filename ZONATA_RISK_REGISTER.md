# ZONATA ENTERPRISE RISK REGISTER
## Risk Identification, Mitigation Strategy & Residual Risk Matrix

**Document Version**: 1.0.0  
**Classification**: ENTERPRISE GOVERNANCE & COMPLIANCE  
**Review Cycle**: CONTINUOUS / QUARTERLY  

---

## 1. Enterprise Risk Matrix

| Risk ID | Threat Description | Likelihood | Impact | Severity | Machine Mitigation Engine | Residual Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-001** | **LLM Prompt Injection / Privilege Escalation**<br/>Adversary instructs AI CEO to execute prohibited or destructive actions. | Medium | Critical | **HIGH** | `core/ceo_policy_matrix.py`<br/>Deterministic Python code blocks forbidden actions and financial thresholds. | **LOW** |
| **RSK-002** | **External System Split-Brain / Drop**<br/>Network disconnects after external PMS mutates room rate, leading to blind retry. | High | High | **HIGH** | `core/reconciliation_engine.py`<br/>Inspects remote state via idempotency token before retrying; detects drift. | **LOW** |
| **RSK-003** | **Worker Crash During State Mutation**<br/>Process terminated between domain database write and downstream event publish. | Medium | High | **MEDIUM** | `core/transactional_outbox.py`<br/>Atomic commit in DB transaction; supervisor recovers hung events automatically. | **VERY LOW** |
| **RSK-004** | **Cascading External Provider Outages**<br/>Third-party API returns 5xx errors; repeated calls exhaust connection pools. | Medium | High | **MEDIUM** | `core/hospitality_production_connector.py`<br/>Circuit breaker trips to OPEN on 3 consecutive failures. | **LOW** |
| **RSK-005** | **Provider Rate-Limit Blacklisting**<br/>Autonomous agents send high-frequency bursts exceeding vendor rate limits. | High | Medium | **MEDIUM** | `core/hospitality_production_connector.py`<br/>Token bucket rate limiter forces caller backoff. | **VERY LOW** |
| **RSK-006** | **Database Host Failure / Data Loss**<br/>Storage disk corruption or host crash wipes primary database. | Low | Critical | **HIGH** | `core/disaster_recovery.py`<br/>Hot online backup, streaming SHA-256 manifest, and verified restore drill. | **VERY LOW** |
| **RSK-007** | **Cross-Tenant Data Exposure**<br/>Tenant B queries or manipulates incidents or receipts belonging to Tenant A. | Low | Critical | **HIGH** | `UniversalControlKernel` & `core/db.py`<br/>Strict tenant isolation filters enforced on all database queries. | **VERY LOW** |
| **RSK-008** | **Missing Live Cloud Credentials**<br/>Customer has not yet supplied production OAuth client credentials for Opera Cloud. | High | Low | **LOW** | `core/hospitality_production_connector.py`<br/>Operates in sovereign emulator mode; transparently flags status. | **CONTROLLED** |

---

## 2. Continuous Monitoring & Incident Escalation
Any trigger of the above risks automatically creates an entry in `executive_incidents`.
Critical events immediately engage the platform KillSwitch, halting autonomous mutations until the Human Owner reviews the situation.
