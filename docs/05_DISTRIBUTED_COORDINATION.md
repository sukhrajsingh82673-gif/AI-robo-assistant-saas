# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Distributed Coordination & State Synchronization Architecture

---

### 1. Architectural Scope & Responsibilities
ZONATA V2 employs a dedicated distributed coordination layer (`core/distributed_coordination.py`) to manage transient state, leader leases, mutual exclusion, rate limiting, and backpressure across all stateless API and worker nodes.

> [!IMPORTANT]
> **Redis / Coordination Invariant**: Redis is NEVER the authoritative source of permanent business records, evidence, or financial state. It is strictly used for ephemeral synchronization, high-frequency locks, rate limits, and live heartbeats.

---

### 2. Distributed Lock & Lease Specification

Every distributed lock in ZONATA conforms to the following rules:
1. **Explicit Owner Identification**: Every lock acquisition binds a unique cryptographic identifier (`worker_<hostname>_<uuid>`).
2. **Lease Expiration**: Locks always specify a finite TTL (`lease_seconds`, default 10s). Infinite locks are constitutionally prohibited.
3. **Heartbeat Renewal**: Long-running critical tasks must actively renew their lease via `lock.renew()` or `lock.start_auto_renewal()`. If the worker process crashes or partitions, the lease automatically expires.
4. **Safe Atomic Release**: A worker cannot release a lock if its lease has already expired and been acquired by another node.

---

### 3. Key Namespacing & Tenant Isolation

Keys are isolated using strict hierarchical namespaces:
```
zonata:{environment}:{tenant_id}:{subsystem}:{key_type}:{identifier}
```
* **Locks**: `zonata:prod:tenant_01:supervisor:lock:leader`
* **Idempotency Keys**: `zonata:prod:tenant_01:actions:idemp:action_req_9921`
* **Rate Limits**: `zonata:prod:tenant_01:api:ratelimit:minute_bucket`
* **Heartbeats**: `zonata:prod:system:heartbeat:supervisor:node_pod_3`
* **Killswitch State**: `zonata:prod:governance:killswitch:AGENT:agt_sales_01`

---

### 4. Distributed KillSwitch Architecture

The `DistributedKillSwitch` synchronizes emergency stop signals across all pods in <100ms:
* **Scopes**: `GLOBAL`, `TENANT`, `COMPANY`, `MISSION`, `WORKFLOW`, `AGENT`, `CAPABILITY`, `PROVIDER`.
* **Worker Duty**: Before executing any high-risk, mutating, or financial action, workers re-check `coordination.is_killed(scope, target_id)`.
* **Fail-Closed**: If the coordination layer is partitioned and a killswitch check cannot be verified for a high-risk mutation, the action is blocked.

---

### 5. Multi-Tenant Rate Limiting & Backpressure

* **Sliding Window Token Bucket**: `check_rate_limit(key, max_requests, window_seconds)` tracks exact millisecond timestamps, preventing burst starvation.
* **Admission Control**: Backpressure counters (`increment_backpressure` / `decrement_backpressure`) track active in-flight missions and database transactions, rejecting new work with `HTTP 429 Retry-After` when saturation thresholds are reached.
