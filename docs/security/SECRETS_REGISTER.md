# AUTHORITATIVE PLATFORM SECRETS REGISTER

**Document Version:** 1.0.0  
**Effective Date:** 2026-11-23  
**Classification:** STRICT CONFIDENTIAL — ZERO PLAINTEXT MATERIAL  
**Governing Rule:** Rule 41 (No plaintext secret or key material in code, DB, logs, traces, or reports)

---

## 1. Secrets Management Policy
- **Zero Raw Secrets:** This register catalogs metadata, purpose, storage backend, authorized consumers, and rotation SLAs. Plaintext values are strictly forbidden from being documented or committed.
- **Access Principle:** All programmatic access routes through `core/ports/secrets.py` (`SecretsPort`).
- **Rotation Enforcement:** Automated or runbook-guided rotation schedules enforced by CI/CD and OpenBao lease TTLs.

---

## 2. Secrets Inventory Catalog

| Secret Identifier / Name | Cryptographic Purpose | Target Storage Backend | Authorized Readers (Least Privilege) | Rotation SLA | Rotation Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ANTHROPIC_API_KEY` | Model inference via Anthropic Claude API | OpenBao KV v2 (`secret/data/providers/anthropic`) | `LLMGateway` worker identity | 90 days | Automated API key regeneration & Vault lease update |
| `BRAVE_SEARCH_API_KEY` | Web research & SERP retrieval | OpenBao KV v2 (`secret/data/providers/brave`) | `ResearchEngine`, `SearchPort` | 90 days | Console rotation & Vault update |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google Gemini API inference | OpenBao KV v2 (`secret/data/providers/google`) | `LLMGateway`, Google ADK adapter | 90 days | Google Cloud Console service account / key rotation |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 SSO authentication | OpenBao KV v2 (`secret/data/auth/google_oauth`) | `UserManager`, `KeycloakIdP` | 180 days | Google Cloud Credentials rotation |
| `GROQ_API_KEY` | Fast LPU inference | OpenBao KV v2 (`secret/data/providers/groq`) | `LLMGateway` (Fast tier) | 90 days | Groq dashboard rotation |
| `HERMES_API_KEY` | Specialized autonomous tool execution | OpenBao KV v2 (`secret/data/providers/hermes`) | `ToolRegistry` executor | 90 days | Key generation & Vault secret update |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak administrative bootstrap | OpenBao KV v2 (`secret/data/auth/keycloak_admin`) | Deployment automation only | 30 days | Keycloak kcadm CLI rotation |
| `KMS_MASTER_KEY` | Master envelope encryption key | OpenBao Transit Engine (`transit/keys/zonata-root`) | `KeyManagementPort` (HSM/Transit only) | 365 days | Transit engine `rotate` command (zero-downtime rewrap) |
| `LANGFUSE_SECRET_KEY` | Distributed observability telemetry | OpenBao KV v2 (`secret/data/telemetry/langfuse`) | `TelemetryInterceptor` | 90 days | Langfuse project API settings |
| `METRICS_AUTH_TOKEN` | Prometheus /metrics endpoint guard | OpenBao KV v2 (`secret/data/ops/prometheus`) | Prometheus scraper service account | 60 days | Vault dynamic secret / token renewal |
| `NEON_AI_GATEWAY_TOKEN` | Serverless AI Gateway proxy | OpenBao KV v2 (`secret/data/infra/neon_ai`) | Neon gateway bridge | 90 days | Neon Console API token issuance |
| `OPENAI_API_KEY` | OpenAI GPT-4o / embeddings access | OpenBao KV v2 (`secret/data/providers/openai`) | `LLMGateway` | 90 days | OpenAI dashboard token regeneration |
| `OPENCLOUD_AUTH_TOKEN` | Multi-cloud storage auth | OpenBao KV v2 (`secret/data/storage/opencloud`) | `StoragePort` | 60 days | Cloud IAM token issuance |
| `OPENROUTER_API_KEY` | Fallback model gateway access | OpenBao KV v2 (`secret/data/providers/openrouter`) | `LLMGateway` fallback provider | 90 days | OpenRouter dashboard rotation |
| `PMS_CLIENT_SECRET` | Hospitality property management API | OpenBao KV v2 (`secret/data/connectors/pms`) | Industry Pack connectors | 90 days | OAuth client secret regeneration |
| `POSTGRES_PASSWORD` | PostgreSQL root administrative password | OpenBao Database Engine (`database/creds/zonata_admin`)| Database migration pipeline only | 30 days | Dynamic credential rotation via OpenBao |
| `POSTHOG_API_KEY` | Product analytics and telemetry | OpenBao KV v2 (`secret/data/telemetry/posthog`) | Analytics reporting worker | 90 days | PostHog project settings |
| `QUICKBOOKS_CLIENT_SECRET`| Accounting connector OAuth secret | OpenBao KV v2 (`secret/data/connectors/quickbooks`) | Accounting sync worker | 90 days | Intuit Developer Portal rotation |
| `RAZORPAY_KEY_SECRET` | Payment checkout verification | OpenBao KV v2 (`secret/data/billing/razorpay`) | `SaaSBillingEngine` | 90 days | Razorpay dashboard API key rotation |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook signature verification | OpenBao KV v2 (`secret/data/billing/razorpay_webhook`)| Webhook ingress controller | 90 days | Razorpay webhook settings |
| `SMS_PROVIDER_API_KEY` | 2FA SMS OTP delivery | OpenBao KV v2 (`secret/data/notifications/sms`) | `TwoStepAuthService` | 90 days | Twilio / Telco provider dashboard |
| `STRIPE_SECRET_KEY` | Stripe billing integration | OpenBao KV v2 (`secret/data/billing/stripe`) | `SaaSBillingEngine` | 90 days | Stripe Dashboard API key rotation |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook HMAC validation | OpenBao KV v2 (`secret/data/billing/stripe_webhook`) | Webhook ingress controller | 90 days | Stripe webhook dashboard |
| `TAVILY_API_KEY` | Deep web search engine access | OpenBao KV v2 (`secret/data/providers/tavily`) | `SearchPort` | 90 days | Tavily API console |
| `TLS_PRIVATE_KEY` | Server TLS termination certificate | OpenBao PKI Engine (`pki/issue/server-cert`) | Reverse proxy / HTTPS listener | 30 days | Automatic PKI certificate renewal (ACME / OpenBao) |
| `URA_LEASE_SECRET` | Universal Resource Adapter leases | OpenBao Transit Engine (`transit/keys/ura-leases`) | `URAManager` | 30 days | Automated HMAC key rotation |
| `VAULT_ROOT_TOKEN` | Initial OpenBao root token | Destroyed immediately after bootstrap | N/A (Revoked upon deployment) | Instant | Zero-retention: unseal keys distributed to custodians |
| `ZONATA_APPROVAL_SECRET` | ActionGateway cryptographic seals | OpenBao Transit Engine (`transit/keys/action-approvals`)| `ZonataActionGateway` | 60 days | Transit key rotation |
| `ZONATA_AUTH_SECRET` | Session token HMAC signing secret | OpenBao Transit Engine (`transit/keys/session-hmac`) | `UserManager`, `AuthorizationEnforcer`| 30 days | Dual-key rotation with 24h grace window |
| `ZONATA_BOOTSTRAP_SECRET` | First-tenant provisioning secret | OpenBao KV v2 (`secret/data/bootstrap`) | Initial setup CLI only | Single-use | Invalidated immediately following tenant 0 initialization |
| `ZONATA_SETTINGS_MASTER_KEY`| Settings envelope encryption key | OpenBao Transit Engine (`transit/keys/settings-vault`)| `SettingsV2Service` | 180 days | Envelope rewrap procedure |
| `ZONATA_SMTP_PASSWORD` | Outbound transactional email | OpenBao KV v2 (`secret/data/notifications/smtp`) | `EmailPort` | 90 days | SMTP server credential rotation |

---

## 3. Emergency Secret Revocation & Break-Glass Protocol
- **Trigger:** Immediate suspicion of secret compromise, unauthorized egress, or inadvertent logging.
- **Action:** OpenBao lease revocation API called: `bao lease revoke -prefix secret/data/` or `transit/keys/<key>/rotate`.
- **Break-Glass Audit:** All emergency unseal, token generation, or secret access triggers high-priority alerts to the platform Owner and logs a cryptographically sealed block to `core/evidence_ledger.py`.
