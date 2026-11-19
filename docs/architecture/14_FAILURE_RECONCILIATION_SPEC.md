# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Failure & State Reconciliation Specification

---

### 1. The UNKNOWN_OUTCOME Invariant
When an external mutation returns an ambiguous response (e.g. network disconnect, provider HTTP 500, worker timeout, process termination), ZONATA strictly forbids blind automated retries.

> [!CAUTION]
> Blindly retrying a failed HTTP request to a payment, CRM, or booking provider risks double billing, duplicate accounts, and data corruption.
> The action MUST immediately transition to `UNKNOWN_OUTCOME` and mandate active reconciliation.

---

### 2. The 3-Phase Reconciliation Protocol

```
                  AMBIGUOUS RESPONSE / TIMEOUT
                               |
                               v
                     [UNKNOWN_OUTCOME STATE]
                               |
                               v
               +---------------+---------------+
               |                               |
        AUTOMATED PROBING               MANUAL ESCALATION
     (Query External Source)         (Exceeds Retry / High Risk)
               |                               |
       +-------+-------+                       v
       |               |                 HUMAN REVIEW
   MATCH FOUND    NO RECORD FOUND        (OWNER / AUDITOR)
       |               |
       v               v
  [VERIFIED]      [SAFE RETRY OR
                   COMPENSATION]
```

1. **Phase 1: Freeze & Triage**:
   - The in-flight workflow halts and records `UNKNOWN_OUTCOME` in `temporal_reconciliations` and the evidence ledger.
   - The idempotency key is preserved to block concurrent submissions.
2. **Phase 2: External State Probing**:
   - A dedicated read-only probe queries the external provider using unique secondary keys (e.g. customer email, transaction reference, order ID).
   - If the entity exists: marked `VERIFIED_SUCCESS`.
   - If confirmed absent: marked `VERIFIED_FAILURE` and safely requeued.
3. **Phase 3: Escalation**:
   - If probing is inconclusive after 3 attempts, the action is marked `RECONCILIATION_REQUIRED` and escalated to human executive review.
