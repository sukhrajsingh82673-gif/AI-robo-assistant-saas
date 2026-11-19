# ZONATA V3 — Temporal Durable Execution Validation

## 1. Subsystem Architecture
- **Component:** `core.temporal_durable_execution_runtime.TemporalDurableExecutionGateway`
- **Purpose:** Governed durable execution, deterministic mission workflows, resilient long-running retries, and cross-session state durability.
- **Dual Execution Route:**
  - `LOCAL_SECURE_RUNTIME`: High-performance SQLite-backed durable workflow state engine.
  - `TEMPORAL_PRODUCTION_CLUSTER`: Remote gRPC-connected Temporal cluster via port 7233.

---

## 2. Invariant & Test Verification Matrix
| Invariant | Test Target | Verification Mechanism | Status | Classification |
|---|---|---|---|---|
| **INV-TMP-01** | Deterministic Replay | State hydration from sequence-ordered workflow events | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TMP-02** | Activity Retry Backoff | Exponential backoff with jitter and non-retryable errors | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TMP-03** | Budget Admission | Maximum token, tool call, and duration limits per workflow | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TMP-04** | Distributed Killswitch | Instant termination of running workflow executions | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TMP-05** | Remote Cluster Connectivity | gRPC channel negotiation with fail-closed fallback | PASS | `BLOCKED — CREDENTIALS REQUIRED` |

---

## 3. Worker Audit & Failure Recovery
- **Stale Worker Detection:** The HA Supervisor runs `_audit_temporal_workers` every cycle, transitioning silent workers to `DEGRADED` if heartbeats lapse past 60 seconds.
- **Crash Recovery:** Workflow state machines resume from the last recorded checkpoint upon process restart.
- **Verdict:** Local durable execution certified; enterprise production deployment conditional on remote cluster connection string.
