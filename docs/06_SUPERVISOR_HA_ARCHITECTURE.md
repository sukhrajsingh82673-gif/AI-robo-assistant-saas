# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## High-Availability Distributed Supervisor Architecture (V2)

---

### 1. Architectural Role & Non-Negotiable Requirements
In enterprise production deployments, the ZONATA Company Supervisor must operate continuously across multiple nodes without single points of failure (SPOF) and without risking split-brain or duplicate job executions.

The `CompanySupervisorHA` (`core/supervisor_ha.py`) implements:
* **Active-Passive Leader Election**: Exactly one supervisor instance holds the `LEADER` lease across the tenant cluster.
* **Distributed Lease & Renewal**: Leases are acquired via distributed coordination (`coordination.acquire_lock`) and renewed automatically during each tick.
* **Rapid Heartbeat & Failover Takeover**: If the active leader crashes or experiences network partition, the standby node acquires the lease within 1.5–15 seconds and resumes supervision seamlessly.
* **Idempotent Schedule Dispatch**: Schedules are dispatched with jitter and atomic deduplication keys (`coordination.set_idempotency_key`), preventing double-execution during leadership transitions.
* **Stuck-Job & Orphan Recovery**: Background commands stuck in `ASSIGNED` state beyond 300s are automatically recovered and requeued.

```
                           DISTRIBUTED CLUSTER NODES
                 +---------------------+---------------------+
                 |                                           |
           SUPERVISOR POD 1                            SUPERVISOR POD 2
           (Node ID: sup_pod_01)                       (Node ID: sup_pod_02)
                 |                                           |
                 +---------------------+---------------------+
                                       |
                       DISTRIBUTED COORDINATION LEASE
               (Key: zonata:prod:supervisor:leader:{tenant_id})
                                       |
                     +-----------------+-----------------+
                     |                                   |
              [LEADER LEASE HELD]               [STANDBY WATCHER]
           - Heartbeat Lease Renewal           - Passive Vitals Monitoring
           - Schedule Execution                - Lease Expiry Polling
           - Orphan Job Recovery               - Zero Mutation Interference
           - Worker Heartbeat Audit
```

---

### 2. Failure Recovery & Split-Brain Prevention

1. **Graceful Step-Down**:
   When a node receives `SIGTERM` or `SIGINT`, it immediately releases its distributed lease (`_active_lock.release()`), allowing the standby candidate to assume leadership without waiting for TTL expiration.
2. **Crash/Partition Handling**:
   If a leader process is hard-killed (`SIGKILL`) or severed by network partition, its heartbeat stops. Once `lease_seconds` (default 15s) elapses, the distributed lock expires automatically. The standby node detects this condition and transitions from `STANDBY -> LEADER`.
3. **Double Execution Defense**:
   Before dispatching any schedule from `universal_schedules`, the supervisor checks `coordination.set_idempotency_key(f"sched_dispatch:{sched_id}")`. Even if two candidates briefly overlap during network reconciliation, only one can claim and trigger the task.
