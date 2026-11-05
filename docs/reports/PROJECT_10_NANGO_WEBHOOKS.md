# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Webhooks Gateway & Ingestion Architecture

### 1. Governed Inbound Webhook Pipeline

External events (e.g., Salesforce lead created, Stripe payment succeeded) pass through a 6-stage security and governance pipeline before triggering any internal workflow:

```
External Webhook HTTP POST
  ├── 1. Timestamp Verification (Replay Attack Defense: <300s window)
  ├── 2. Payload Digest & Duplicate Suppression (SHA-256 idempotency cache)
  ├── 3. Cryptographic Signature Verification (HMAC SHA-256 / Provider Secret)
  ├── 4. Tenant & Company Connection Resolution (Validates registered connection)
  ├── 5. Dead-Letter Routing (Unverified or malformed payloads quarantined)
  └── 6. Governed Emission (Dispatched to Event Engine / AI CEO / Temporal)
```

---

### 2. Security Invariants for Webhooks

1. **External Event != Authority**:
   An inbound webhook payload has zero native authority. It is treated strictly as an unverified perception observation until validated against local business contracts.
2. **Replay Attack Defense**:
   Webhooks with timestamps differing from server time by more than 300 seconds are rejected with a logged `WEBHOOK_REPLAY_ATTEMPT` event.
3. **Duplicate Suppression**:
   A SHA-256 digest of the raw payload is stored in `nango_webhooks`. Repeated transmissions of identical payloads within the idempotency window return `DUPLICATE_SUPPRESSED` without re-executing business logic.
4. **Dead-Letter Quarantine**:
   Any webhook failing signature verification or schema parsing is routed to `status = 'DEAD_LETTER'` in the database for operator review.
