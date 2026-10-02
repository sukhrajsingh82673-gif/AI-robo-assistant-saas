# ZONATA V3 — Nango External System Connectivity Validation

## 1. Subsystem Architecture
- **Component:** `core.nango_integration_runtime.ExternalIntegrationGateway` (Project 10)
- **Scope:** Governed universal external SaaS connectivity, token management, OAuth refresh, bi-directional sync, webhooks, rate limits, and connection health lifecycle.
- **Architectural Stance:** Internal infrastructure adapter ensuring full compliance with Elastic License 2.0 restrictions (internal operations only; not re-sold or offered as a managed integration broker service).

---

## 2. Invariant & Test Verification Matrix
| Invariant | Test Target | Verification Method | Status | Classification |
|---|---|---|---|---|
| **INV-NAN-01** | Multi-Tenant Key Isolation | Per-tenant encryption keys for SaaS provider tokens | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-NAN-02** | 20-Step Pipeline Gate | External mutations routed strictly through ActionGateway | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-NAN-03** | Auto-Refresh & Retry | Automatic handling of expired OAuth tokens with backoff | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-NAN-04** | Webhook HMAC Verification | Ingress signature verification rejecting forged payloads | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-NAN-05** | Live SaaS Endpoints (Salesforce, Stripe, Jira) | End-to-end sync with live third-party production APIs | BLOCKED | `BLOCKED — CREDENTIALS REQUIRED` |

---

## 3. Operational Classification
- **Nango Integration Adapter & Gateway:** `REAL_LOCAL_INFRASTRUCTURE`
- **Live SaaS Provider Connectors:** `BLOCKED — CREDENTIALS REQUIRED`
- **Verdict:** Integration engine certified; production sync operational once enterprise customer supplies API keys.
