# ZONATA / URA — AI DLP Data-Flow & Policy Enforcement Matrix

**Outbound Channel Governance & Data Classification Taxonomy**  
**Document Classification:** RESTRICTED — INTERNAL GOVERNANCE  
**Authority Reference:** `core/ai_dlp_gateway.py` & `core/data_classification_engine.py`  
**Baseline Commit:** `520e68d` (Lineage verified from `353238f`, `53bd2ef`, and `45cf91f`)  
**Status:** PRODUCTION QUALIFIED — VERIFIED SCOPE  

---

## 1. Enterprise Data Classification Taxonomy

| Level | Severity Score | Typical Data Types | Sovereign Egress Rule |
|---|:---:|---|---|
| **PUBLIC** | 1 | Marketing copy, public documentation, open knowledge | Unrestricted transmission to all approved destinations. |
| **INTERNAL** | 2 | Routine meeting notes, non-confidential task logs | Permitted to internal services and approved SaaS with TLS. |
| **CONFIDENTIAL** | 3 | Customer records, employee HR data, financial forecasts, Indian tax identifiers (PAN, Aadhaar, GSTIN, IFSC) | Class 2 Transform (Redact/Tokenize) required before cloud egress. Egress to unapproved external endpoints strictly prohibited. |
| **RESTRICTED** | 4 | Legal agreements, PII (SSNs, full credit card numbers), strategic plans | Strict tokenization/masking required. Cloud egress permitted only to explicitly approved destinations. |
| **HIGHLY_RESTRICTED** | 5 | Private encryption keys, root passwords, live API tokens, synthetic canary secrets | **ZERO CLOUD EGRESS.** Local sovereign processing only (`LOCAL_SOVEREIGN` / `INTERNAL_SECURE`). |

---

## 2. Destination Trust Levels

1. **`LOCAL_SOVEREIGN`**: In-container execution, sovereign local LLMs (`llama-3.3-70b-local`, `gemma-4-sovereign`), local SQLite databases.
2. **`INTERNAL_SECURE`**: Internal enterprise sidecars (HashiCorp Vault, NATS message bus, internal stdio MCP servers).
3. **`APPROVED_SAAS`**: Contractually approved enterprise partners (Anthropic, OpenAI, ERPNext local connector, Stripe).
4. **`UNAPPROVED_EXTERNAL`**: Third-party public APIs, external agent swarms, unverified partner endpoints.
5. **`PUBLIC_INTERNET`**: Unauthenticated web scraping targets, public websites, external search engines.

---

## 3. Comprehensive Source-to-Destination Policy Matrix across 10 Routes

| # | Outbound Route | Source Entity | Target Destination | Trust Level | Data Classification | Policy Enforcement Action | Security Class | Fail-Closed Fallback |
|:---:|---|---|---|---|---|---|:---:|---|
| **1** | Central LLM Provider | AI Employee | Cloud Provider (Anthropic) | `APPROVED_SAAS` | `PUBLIC` | Allow without alteration | **Class 1** | Return error; prompt withheld |
| **1** | Central LLM Provider | AI Employee | Cloud Provider (OpenAI) | `APPROVED_SAAS` | `CONFIDENTIAL` (PII / PAN) | Anonymize PII / PAN (`<REDACTED_...>`) | **Class 2** | Fail closed: prompt withheld |
| **1** | Central LLM Provider | AI CEO | Cloud Provider (Google) | `APPROVED_SAAS` | `HIGHLY_RESTRICTED` (Secret) | Route to local sovereign model (`llama-3.3-70b-local`) | **Class 2** | Fail closed: prompt withheld |
| **1** | Central LLM Provider | Rogue Agent | External API | `UNAPPROVED_EXTERNAL` | `HIGHLY_RESTRICTED` (Secret) | Strike 1 immediate deny; Strike 3 isolate worker | **Class 3 / 4** | Fail closed; isolate agent |
| **2** | Direct SDK / HTTP Client | Autonomous Agent | OpenAI / LiteLLM Gateway | `APPROVED_SAAS` | `HIGHLY_RESTRICTED` (Secret) | Gateway blocks prompt pre-synthesis; returns `[DLP_BLOCKED]` | **Class 3** | Abort call; fail closed |
| **3** | Governed MCP Tool | Co-worker Agent | Corporate SQLite MCP | `INTERNAL_SECURE` | `INTERNAL` | Allow tool execution under least privilege | **Class 1** | Return error; tool unexecuted |
| **3** | Governed MCP Tool | Co-worker Agent | Remote Partner MCP | `UNAPPROVED_EXTERNAL` | `CONFIDENTIAL` (Token) | Block outbound call; deny credential disclosure | **Class 3** | Return `DLP Policy Denied` |
| **3** | Governed MCP Tool (Inbound) | Untrusted Tool | Co-worker Context | `INTERNAL_SECURE` | Untrusted Output | Scan for prompt injection; reject if adversarial | **Class 3** | Discard output; record incident |
| **4** | Agent-to-Agent (A2A) | Agent Tenant A | Agent Tenant B | `INTERNAL_SECURE` | Any | Block cross-tenant communication | **Class 3** | Discard message; log `CROSS_TENANT` |
| **4** | Agent-to-Agent (A2A) | Agent Tenant A | Agent Tenant A | `INTERNAL_SECURE` | `CONFIDENTIAL` (Customer) | Redact sensitive PII; forward sanitized payload | **Class 2** | Deliver sanitized content only |
| **5** | Persistent Memory | Agent Worker | Operational Memory | `LOCAL_SOVEREIGN` | `HIGHLY_RESTRICTED` (Key) | Scrub credentials; persist `<REDACTED_MEMORY_SECRET>` | **Class 2** | Memory stored without secret |
| **5** | Persistent Memory | Non-Sovereign | Business Memory | `LOCAL_SOVEREIGN` | Any | Reject write; require sovereign authority | **Class 3** | Raise `PermissionError` |
| **6** | Browser & Egress | Browser Agent | `169.254.169.254` or Decimal IP | `PUBLIC_INTERNET` | Navigation | Connection-time socket check (`SSRFSafeHTTPConnection` / `SSRFSafeHTTPSConnection`), direct socket binding, strict TLS SNI & `CERT_REQUIRED`, proxy neutralization: block metadata | **Class 3** | Abort connection immediately |
| **6** | Browser & Egress | Browser Agent | Public Site $\to$ Localhost Redirect | `PUBLIC_INTERNET` | Navigation | Re-evaluate IP on redirect and socket connect; block loopback | **Class 3** | Abort HTTP request immediately |
| **6** | Browser & Egress (Typing) | Browser Agent | Web Form Input | `PUBLIC_INTERNET` | `HIGHLY_RESTRICTED` (Canary) | Intercept type action; redact credentials | **Class 2** | Keystrokes sanitized |
| **7** | Terminal Sandbox | Terminal Agent | `../../etc/passwd` or `/root/.ssh` | `LOCAL_SOVEREIGN` | File Operation | Confinement check + `realpath`; reject traversal | **Class 3** | Return `FAILED_SECURITY_POLICY` |
| **7** | Terminal Sandbox (Command) | Terminal Agent | Shell command with canary / key | `UNAPPROVED_EXTERNAL` | `HIGHLY_RESTRICTED` (Canary) | Pre-execution command DLP: Strike 1 denial before subprocess spawn | **Class 3** | Return `POLICY_DENIED`, exit 126 |
| **8** | Enterprise Connectors | Workflow Engine | External Webhook / API | `UNAPPROVED_EXTERNAL` | `HIGHLY_RESTRICTED` (Canary) | Screen params; deny credential exfiltration | **Class 3** | Raise `ConnectorSecurityError` |
| **8** | Enterprise Connectors | Workflow Engine | ERPNext / Financial Bank | `APPROVED_SAAS` | Mutation > ₹50,000 INR | Verify canonical HMAC approval receipt | **Class 5** | Require executive approval token |
| **9** | Telemetry & Audit Logs | Telemetry Exporter | Observability Backend | `INTERNAL_SECURE` | Traces & Exceptions | Scrub raw credentials; output SHA-256 trace IDs | **Class 2** | Raw secrets omitted from logs |
| **10**| CI/CD & Build Pipeline | CI Pipeline Runner | GitHub Action Runner | `APPROVED_SAAS` | Codebase & Commits | Scan secrets; mask matches in build logs | **Class 3** | Exit code 1; commit rejected |

---

## 4. Presidio Operator Configuration

```json
{
  "operators": {
    "US_SSN": { "type": "replace", "new_value": "<REDACTED_US_SSN>" },
    "CREDIT_CARD": { "type": "mask", "chars_to_preserve": 4, "masking_char": "*" },
    "EMAIL_ADDRESS": { "type": "replace", "new_value": "<REDACTED_EMAIL_ADDRESS>" },
    "PHONE_NUMBER": { "type": "replace", "new_value": "<REDACTED_PHONE_NUMBER>" },
    "IP_ADDRESS": { "type": "replace", "new_value": "<REDACTED_IP_ADDRESS>" },
    "CRYPTO_PRIVATE_KEY": { "type": "redact" },
    "API_KEY_OR_SECRET": { "type": "replace", "new_value": "<REDACTED_SECRET>" },
    "ZONATA_EMPLOYEE_ID": { "type": "replace", "new_value": "<REDACTED_ZONATA_EMPLOYEE_ID>" },
    "ZONATA_CUSTOMER_ID": { "type": "tokenize", "session_salted": true, "csprng_256bit": true, "mission_rotatable": true, "keyed_hmac": true },
    "CONFIDENTIAL_PROJECT_NAME": { "type": "replace", "new_value": "<REDACTED_CONFIDENTIAL_PROJECT_NAME>" },
    "SECURITY_CANARY": { "type": "replace", "new_value": "<REDACTED_CANARY_SECRET>" },
    "INDIA_PAN": { "type": "replace", "new_value": "<REDACTED_INDIA_PAN>" },
    "INDIA_AADHAAR": { "type": "replace", "new_value": "<REDACTED_INDIA_AADHAAR>" },
    "INDIA_GSTIN": { "type": "replace", "new_value": "<REDACTED_INDIA_GSTIN>" },
    "INDIA_IFSC": { "type": "replace", "new_value": "<REDACTED_INDIA_IFSC>" }
  }
}
```

---

## 5. Final Policy Matrix Verdict

```
================================================================================
FINAL POLICY MATRIX VERDICT: PRODUCTION QUALIFIED — VERIFIED SCOPE
================================================================================
```
