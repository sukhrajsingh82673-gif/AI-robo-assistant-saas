# ZONATA / URA — AI DLP Data-Flow & Policy Enforcement Matrix

**Outbound Channel Governance & Data Classification Taxonomy**  
**Document Classification:** RESTRICTED — INTERNAL GOVERNANCE  
**Authority Reference:** `core/ai_dlp_gateway.py` & `core/data_classification_engine.py`  
**Baseline Commit:** `45cf91f`  

---

## 1. Enterprise Data Classification Taxonomy

| Level | Severity Score | Typical Data Types | Sovereign Egress Rule |
|---|:---:|---|---|
| **PUBLIC** | 1 | Marketing copy, public documentation, open knowledge | Unrestricted transmission to all approved destinations. |
| **INTERNAL** | 2 | Routine meeting notes, non-confidential task logs | Permitted to internal services and approved SaaS with TLS. |
| **CONFIDENTIAL** | 3 | Customer records, employee HR data, financial forecasts | Class 2 Transform (Redact/Tokenize) required before cloud egress. Egress to unapproved external endpoints strictly prohibited. |
| **RESTRICTED** | 4 | Legal agreements, PII (SSNs, full credit card numbers), strategic plans | Strict tokenization/masking required. Cloud egress permitted only to explicitly approved destinations. |
| **HIGHLY_RESTRICTED** | 5 | Private encryption keys, root passwords, live API tokens | **ZERO CLOUD EGRESS.** Local sovereign processing only (`LOCAL_SOVEREIGN` / `INTERNAL_SECURE`). |

---

## 2. Destination Trust Levels

1. **`LOCAL_SOVEREIGN`**: In-container execution, sovereign local LLMs (`llama-3.3-70b-local`, `gemma-4-sovereign`), local SQLite databases.
2. **`INTERNAL_SECURE`**: Internal enterprise sidecars (HashiCorp Vault, NATS message bus, internal stdio MCP servers).
3. **`APPROVED_SAAS`**: Contractually approved enterprise partners (Anthropic, OpenAI, ERPNext local connector, Stripe).
4. **`UNAPPROVED_EXTERNAL`**: Third-party public APIs, external agent swarms, unverified partner endpoints.
5. **`PUBLIC_INTERNET`**: Unauthenticated web scraping targets, public websites, external search engines.

---

## 3. Comprehensive Source-to-Destination Policy Matrix

| Source Entity | Outbound Channel | Data Classification | Target Destination | Trust Level | Policy Enforcement Action | Security Class | Fail-Closed Fallback |
|---|---|---|---|---|---|:---:|---|
| AI Employee | `LLM_PROMPT` | `PUBLIC` | Cloud Provider (Anthropic) | `APPROVED_SAAS` | Allow without alteration | **Class 1** | Return error; do not send |
| AI Employee | `LLM_PROMPT` | `CONFIDENTIAL` (PII) | Cloud Provider (OpenAI) | `APPROVED_SAAS` | Anonymize PII; substitute `<REDACTED_...>` | **Class 2** | Fail closed: prompt withheld |
| AI CEO | `LLM_PROMPT` | `HIGHLY_RESTRICTED` (Secret) | Cloud Provider (Google) | `APPROVED_SAAS` | Automatically route to local model (`llama-3.3-70b-local`) | **Class 2** | Fail closed: prompt withheld |
| Rogue Agent | `LLM_PROMPT` | `HIGHLY_RESTRICTED` (Secret) | External API | `UNAPPROVED_EXTERNAL` | Deny transfer; log critical incident; track violations | **Class 3** | Fail closed; isolate agent on 3rd attempt (**Class 4**) |
| Co-worker | `MCP_TOOL` | `INTERNAL` | Corporate SQLite | `INTERNAL_SECURE` | Allow tool execution under least privilege | **Class 1** | Return error; tool unexecuted |
| Co-worker | `MCP_TOOL` | `CONFIDENTIAL` (Token) | Remote Partner MCP | `UNAPPROVED_EXTERNAL` | Block outbound call; deny credential disclosure | **Class 3** | Return `DLP Policy Denied` |
| Untrusted Web | `MCP_TOOL` (Inbound) | Untrusted Output | Co-worker Context | `INTERNAL_SECURE` | Scan for prompt injection; reject if adversarial | **Class 3** | Discard output; record incident |
| Agent Tenant A | `A2A_MESSAGE` | Any | Agent Tenant B | `INTERNAL_SECURE` | Block cross-tenant communication | **Class 3** | Discard message; log `CROSS_TENANT_VIOLATION` |
| Agent Tenant A | `A2A_MESSAGE` | `CONFIDENTIAL` (Customer) | Agent Tenant A | `INTERNAL_SECURE` | Redact sensitive PII; forward sanitized payload | **Class 2** | Deliver sanitized content only |
| Agent Worker | `MEMORY_STORE` | `HIGHLY_RESTRICTED` (Key) | Operational Memory | `LOCAL_SOVEREIGN` | Scrub credentials; persist `<REDACTED_MEMORY_SECRET>` | **Class 2** | Memory stored without secret |
| Non-Sovereign | `MEMORY_STORE` | Any | Business Memory | `LOCAL_SOVEREIGN` | Reject write; require sovereign authority | **Class 3** | Raise `PermissionError` |
| Browser Agent | `BROWSER_EGRESS` | Navigation | `169.254.169.254` | `PUBLIC_INTERNET` | Block metadata service access | **Class 3** | Abort HTTP request immediately |
| Browser Agent | `BROWSER_EGRESS` | Navigation | Public Site $\to$ Localhost Redirect | `PUBLIC_INTERNET` | Re-evaluate IP on redirect; block loopback target | **Class 3** | Abort HTTP request immediately |
| Terminal Agent | `TERMINAL_COMMAND` | File Operation | `../../etc/passwd` | `LOCAL_SOVEREIGN` | Confinement check; reject path traversal | **Class 3** | Return `FAILED_SECURITY_POLICY` |
| Workflow Engine| `CONNECTOR_MUTATION`| Financial > ₹50,000 INR | ERPNext / Bank | `APPROVED_SAAS` | Verify canonical HMAC approval receipt | **Class 5** | Require executive approval token |

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
    "ZONATA_CUSTOMER_ID": { "type": "tokenize" },
    "CONFIDENTIAL_PROJECT_NAME": { "type": "replace", "new_value": "<REDACTED_CONFIDENTIAL_PROJECT_NAME>" },
    "SECURITY_CANARY": { "type": "replace", "new_value": "<REDACTED_CANARY_SECRET>" }
  }
}
```
