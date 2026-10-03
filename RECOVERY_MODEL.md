# ZONATA UNIVERSAL AI CO-WORKER FABRIC — RECOVERY MODEL
## Self-Healing Architecture, Crash Resilience & Bounded Retry Policies

**Version**: 1.0.0  
**Classification**: SRE & RELIABILITY SPECIFICATION  

---

## 1. Controlled Self-Healing Philosophy

The Co-worker Fabric is built for continuous 24×7 resilience:
1. **Bounded Recovery**: Every recovery loop is capped (default: max 3 attempts) to prevent runaway execution or cost exhaustion.
2. **Idempotency-Checked Retries**: Before retrying any side-effecting task, the `FallbackManager` queries the target system to determine if the prior attempt actually executed.
3. **Session Rehydration**: Application crashes rehydrate saved session state and re-verify environmental prerequisites before resuming execution.

---

## 2. Failure Recovery Matrix

| Failure Event | Diagnostic Trigger | Recovery Action | Escalation Boundary |
| :--- | :--- | :--- | :--- |
| **Browser Crash / OOM** | Playwright process disconnect or non-zero exit code | Relaunch browser daemon, restore target URL and session cookies, re-verify DOM readiness. | If 3 relaunch attempts fail, route to `VisualCUAProvider` or escalate. |
| **Desktop App Freeze** | Window unresponsive or RPC timeout | Soft kill stuck process, relaunch desktop application binary, restore window focus via `desktop.focus_window`. | If app fails to launch twice, escalate to Human Takeover. |
| **Transient Network Drop**| HTTP 502/503/504 or socket timeout | Exponential backoff (1s, 2s, 4s) with jitter. Query idempotency key before retry. | If 3 network attempts fail, mark `UNCERTAIN` and alert SRE. |
| **Hung Worker Lease** | Worker heartbeat silent for >60s | `Watchdog` revokes lease, returns task to `RecoveryQueue`, and spawns replacement worker. | If 2 replacement workers stall, quarantine task in `DeadLetterQueue`. |
| **Approval Payload Tampering**| HMAC signature mismatch | Immediately revoke approval envelope, engage `SESSION` KillSwitch, log security incident. | Immediate Human Incident Commander alert. |
