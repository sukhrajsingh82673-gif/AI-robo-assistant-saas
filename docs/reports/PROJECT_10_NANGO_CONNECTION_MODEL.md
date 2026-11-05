# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Connection Model & Lifecycle Architecture

### 1. Connection Lifecycle State Machine

Every external connection transitions through an explicit 10-stage lifecycle. No connection displays an "ACTIVE" badge without physical verification:

```
[DISCOVER] ──> [INSTALL] ──> [AUTHORIZE] ──> [CONNECT] ──> [VALIDATE] ──> [ACTIVE]
                                                                             │
                              ┌──────────────────────────────────────────────┴──────────┐
                              ▼                                                         ▼
                         [DEGRADED]                                            [REAUTH_REQUIRED]
                              │                                                         │
                              └──────────────────┐                   ┌──────────────────┘
                                                 ▼                   ▼
                                           [DISCONNECTED] ──> [REVOKED]
```

1. **`DISCOVER`**: Provider discovered in the Integration Catalog; schemas and supported scopes inspected.
2. **`INSTALL`**: Provider registered for a specific tenant and operating company.
3. **`AUTHORIZE`**: User redirects to provider OAuth consent screen; permissions approved.
4. **`CONNECT`**: OAuth callback received by Nango; token vaulted and opaque reference generated.
5. **`VALIDATE`**: Pre-flight health check executed to verify endpoint reachability and token validity.
6. **`ACTIVE`**: Connection is operational and ready for governed agent execution.
7. **`DEGRADED`**: Intermittent provider errors or elevated latencies detected.
8. **`REAUTH_REQUIRED`**: OAuth token expired and automated refresh failed; awaits human re-authorization.
9. **`DISCONNECTED`**: Connection paused by operator; scheduled syncs and new actions halted.
10. **`REVOKED`**: Connection permanently terminated; tokens destroyed and credentials purged.

---

### 2. Scope & Permission Governance

* **Pre-Declared Scopes**: Connections only request scopes pre-approved in the provider catalog definition.
* **Scope Down-scoping**: Agents only receive access to the minimum set of capabilities required for their assigned role (e.g., Sales agents never receive accounting scopes).
* **Audit Trail**: Every change in connection state or scope grant is sealed in the Merkle Evidence Ledger.
