# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Production Secrets & Credential Architecture

---

### 1. Zero-Secret Persistence Invariant
In ZONATA, plaintext credentials (passwords, private keys, SaaS API tokens, OAuth refresh tokens) are strictly prohibited from appearing in:
* LLM prompt memory & agent context windows
* LangGraph / Temporal workflow checkpoints
* SQLite / PostgreSQL business records
* Log files, error traces, and telemetry
* Screenshots and browser DOM dumps
* Git repositories and SBOM manifests

---

### 2. Ephemeral JIT Token Broker Architecture
All credentials are held in `SecretVaultManager` (`core/secret_manager.py`) behind opaque handles (`cred_...`).

```
  AGENT WORKSPACE                      SECRET VAULT               EXTERNAL SERVICE
         |                                   |                            |
  [ActionEnvelope]                           |                            |
  credential_handle: cred_a8b9               |                            |
         |                                   |                            |
         +-----> ZonataActionGateway --------+                            |
                       |                                                  |
              Acquire JIT Token (TTL: 60s)                                |
                       |                                                  |
                       +------------------------------------------------->|
                                     Execute with Token                   |
                                                                          |
                       <--------------------------------------------------+
                                     Response Returned                    |
                       |                                                  |
              Expire / Revoke Token                                       |
                       |                                                  |
              Automatic Redaction Filter Applied                          |
                       |                                                  |
              Evidence Sealed (Zero Secrets)                              |
```

---

### 3. Automated Secret Redaction Engine
Any unstructured text leaving an execution boundary is processed through automated regex scrubbers targeting:
* Bearer tokens (`Bearer [REDACTED_SECRET]`)
* Stripe / SaaS live keys (`sk_live_...`, `xoxb-...`, `ghp_...`)
* Known registered vault values (`[REDACTED_VAULT_SECRET]`)
