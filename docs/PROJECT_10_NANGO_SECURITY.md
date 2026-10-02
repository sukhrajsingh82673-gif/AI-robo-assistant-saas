# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Security Architecture & Context Firewall

### 1. Multi-Tenant Connection Isolation

Every external connection strictly belongs to a three-tier hierarchy:
```
Tenant ID (e.g. tnt_primary)
  └── Company ID (e.g. comp_royal_haveli)
       └── Provider ID (e.g. salesforce)
            └── Connection ID (e.g. conn_salesforce_1e54443b)
```

**Security Invariants Enforced:**
* A connection established by Tenant A cannot be discovered, queried, tested, or executed by Tenant B.
* Any cross-tenant execution attempt raises an immediate `SecurityException` and records an audited `CROSS_TENANT_VIOLATION` event in `nango_security_events`.
* SQLite foreign key cascading ensures that deleting a tenant or company immediately purges all associated connections, sync jobs, sync records, and credentials.

---

### 2. Opaque Credential Handles & Secret Isolation

AI agents never receive raw OAuth access tokens, refresh tokens, client secrets, or API keys in prompts, memories, or execution contexts.

* All credentials are encrypted and vaulted inside the Credential Broker.
* When a connection is established, an opaque cryptographic handle is generated:
  `cred_nango_<provider>_<12_hex_chars>`
* Agents only ever reference this handle. JIT token injection occurs exclusively inside the isolated `NangoAdapter` network transport layer immediately prior to external transmission.

---

### 3. Context Firewall & Prompt Injection Defense

All inbound payloads from external APIs and webhooks pass through the `IntegrationSecurityBoundary`:

1. **Adversarial Instruction Neutralization**:
   Regex pattern matchers scan payloads for override directives (e.g., `"ignore previous instructions and..."`, `"system override"`, `"grant all permissions"`). Payloads containing adversarial prompts are blocked immediately or stripped of execution authority.
2. **Automated Secret Scrubbing**:
   All parameters, event histories, and log outputs are scrubbed using regex matchers targeting bearer tokens, API keys (`sk_...`, `ghp_...`, `xoxb-...`, `whsec_...`), replacing them with `[REDACTED_CREDENTIAL]`.

---

### 4. Multi-Scope Integration KillSwitch

The `IntegrationKillSwitch` provides immediate, non-bypassable halt authority across 8 distinct scopes:

1. `GLOBAL` — Halts all external integrations across the entire platform.
2. `TENANT` — Halts all integrations for a specific enterprise tenant.
3. `COMPANY` — Halts all integrations for a specific subsidiary company.
4. `MISSION` — Halts external calls originating from a designated mission.
5. `AGENT` — Revokes external execution authority for an individual AI employee.
6. `CAPABILITY` — Disables a specific action (e.g., blocks `DELETE_LEAD` while keeping `READ_CONTACT` operational).
7. `PROVIDER` — Disables all interactions with a specific vendor (e.g., Salesforce).
8. `CONNECTION` — Suspends a specific connection during audit or reauthorization.

Any blocked execution raises a `SecurityException` and logs a `KILLSWITCH_ENGAGED` event.
