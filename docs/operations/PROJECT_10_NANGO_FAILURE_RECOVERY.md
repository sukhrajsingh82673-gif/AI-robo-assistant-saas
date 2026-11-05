# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Failure Recovery & Unknown Outcome Protocol

### 1. First-Class UNKNOWN_OUTCOME Protocol

In distributed systems, mutations that experience network drops, TCP resets, or HTTP 504 Gateway Timeouts create an ambiguous state where the external system may or may not have committed the transaction.

**ZONATA Protocol:**
1. Blind automated replay is **STRICTLY PROHIBITED**.
2. The execution status is immediately marked as `UNKNOWN_OUTCOME`.
3. A reconciliation record is created in `nango_reconciliations` with status `PENDING`.
4. The system enters the `RECONCILING` state.
5. An observation query using the preserved `idempotency_key` inspects the external system.
6. Once external truth is determined, the execution transitions to `RECONCILED_SUCCESS` or `RECONCILED_FAILURE`.

```
Mutation Dispatched ──> [Network Drop / Timeout] ──> [UNKNOWN_OUTCOME] (Blind Replay Blocked)
                                                             │
                                                             ▼
                                                    [State Reconciliation]
                                                             │
                              ┌──────────────────────────────┴──────────────────────────────┐
                              ▼                                                             ▼
                    [External Record Found]                                       [External Record Not Found]
                              │                                                             │
                              ▼                                                             ▼
                   [RECONCILED_SUCCESS]                                          [RECONCILED_FAILURE]
```

---

### 2. Rate Limit Governance & Fairness

* **Sliding Window Monitoring**: Tracks requests per minute per endpoint.
* **Multi-Tenant Fairness**: Prevents noisy tenants from consuming global provider quotas.
* **Exponential Backoff**: When HTTP 429 or rate limits are triggered, the governor computes dynamic backoff using `Retry-After` headers and pauses dispatches.

---

### 3. Temporal Durable Process Integration

When long-running workflows involve external API calls:
* Temporal activities manage transient retries for safe, idempotent operations (`READ_ONLY`).
* Multi-step distributed operations use the `SagaCompensationCoordinator` to execute LIFO reverse compensations if downstream mutations fail.
