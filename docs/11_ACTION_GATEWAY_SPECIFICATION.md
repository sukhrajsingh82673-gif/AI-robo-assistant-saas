# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Central Action Gateway Specification (ZonataActionGateway)

---

### 1. Mandatory Canonical Boundary
The `ZonataActionGateway` (`core/action_gateway.py`) is the single non-bypassable execution boundary through which ALL mutations, tool calls, external API integrations, browser interactions, code executions, and workflow activities must pass.

> [!CRITICAL]
> **Constitutional Invariant**:
> No subagent, AI CEO, Temporal activity, OpenHands container, or MCP tool may make an external side effect directly without obtaining an authenticated, policy-cleared, evidence-sealed contract from `ZonataActionGateway`.

---

### 2. The Canonical 20-Step Execution Pipeline

Every execution request must be presented in the universal `ActionEnvelope` and strictly traversed in sequence:

```
[INGRESS] ActionEnvelope Received
   |
   +--> Step 01: Authenticate (Token check, expiration, killswitch query)
   +--> Step 02: Resolve Tenant (Anti-spoofing; reject default tenant)
   +--> Step 03: Resolve Company (Validate corporate operating context)
   +--> Step 04: Resolve Agent (Check lifecycle state: block if quarantined/revoked)
   +--> Step 05: Resolve Mission (Verify mission is active and uncompleted)
   +--> Step 06: Resolve Capability (Lookup in capability registry)
   +--> Step 07: Validate Target (SSRF defense: block 127.0.0.1, 169.254.169.254, file://)
   +--> Step 08: Classify Risk (READ_ONLY, LOW_RISK, MUTATING, FINANCIAL, DESTRUCTIVE)
   +--> Step 09: Calculate Action Hash (Verify SHA-256 parameter digest)
   +--> Step 10: Evaluate Policy (Constitutional rate limits and invariant rules)
   +--> Step 11: Evaluate Authority (Self-modification defense: protect core.* modules)
   +--> Step 12: Evaluate Approval (Require human OWNER approval for FINANCIAL/DESTRUCTIVE)
   +--> Step 13: Obtain Credential (Retrieve opaque handle `cred_...` via CredentialBroker)
   +--> Step 14: Enforce Idempotency (Deduplicate via distributed coordination cache)
   +--> Step 15: Execute (Dispatch to isolated subsystem adapter driver)
   +--> Step 16: Observe (Collect real-world telemetry, response payloads, errors)
   +--> Step 17: Verify (Evaluate expected vs observed state: VERIFIED vs UNKNOWN)
   +--> Step 18: Reconcile If Needed (Trigger reconciliation engine on ambiguous results)
   +--> Step 19: Seal Evidence (Atomic append to distributed Merkle ledger)
   +--> Step 20: Return Outcome (Package final business outcome with cryptographic proof)
   |
[EGRESS] Verified Outcome Delivered
```

---

### 3. Fail-Closed Security Posture
If an action fails any step between Step 1 and Step 14, execution halts immediately with `ActionGatewayRejection(step, rule, message)`. No partial mutation or unrecorded side effect is permitted.
