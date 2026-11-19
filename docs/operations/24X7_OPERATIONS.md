# ZONATA UNIVERSAL AI CO-WORKER FABRIC — 24×7×365 OPERATIONS
## Continuous Workforce Operation, Leases, Watchdogs & SRE Procedures

**Version**: 1.0.0  
**Classification**: OPERATIONAL SPECIFICATION  

---

## 1. 24×7 Operational Architecture

Autonomous AI Co-workers operate continuously without manual babysitting, governed by the `WorkerSupervisor`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        WORKER SUPERVISOR                               │
│                                                                        │
│   ┌────────────────────┐   ┌───────────────────┐   ┌───────────────┐   │
│   │ ExecutionLeaseMgr  │   │ MissionScheduler  │   │ SRE Watchdog  │   │
│   └────────────────────┘   └───────────────────┘   └───────────────┘   │
│                                                                        │
│   QUEUES:                                                              │
│   - RetryQueue             (Transient backoff retries)                 │
│   - RecoveryQueue          (Recovering crashed worker leases)          │
│   - HumanEscalationQueue   (Tasks requiring human review / takeover)   │
│   - DeadLetterQueue        (Exhausted / permanently failed tasks)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Lease Timers & Heartbeat Parameters

| Parameter | Default Value | Purpose |
| :--- | :--- | :--- |
| **Task Lease TTL** | `900.0s` (15 mins) | Maximum time a worker may hold an active task before automatic lease revocation. |
| **Worker Heartbeat Timeout** | `60.0s` | If a worker fails to send a heartbeat within 60s, it is marked hung and reclaimed. |
| **Watchdog Audit Frequency**| `30.0s` | Continuous background audit checking lease expirations and queue depths. |
| **Max Recovery Retries** | `3` | Maximum self-healing attempts before moving task to `DeadLetterQueue`. |

---

## 3. Mission Scheduling & Cron Syntax

The `MissionScheduler` supports standard cron syntax (e.g. `"0 8 * * *"` for 8 AM daily revenue monitoring).
Missions scheduled via natural language prompts are compiled into scheduled task graphs with deterministic safety rules.
