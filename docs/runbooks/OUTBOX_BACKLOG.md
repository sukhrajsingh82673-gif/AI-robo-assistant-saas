# Runbook — Outbox Dispatch Backlog

| Field | Value |
|---|---|
| Alert | `ALT_OUTBOX_BACKLOG` — Outbox Dispatch Backlog |
| Severity | HIGH |
| Owner | `SRE_ONCALL` |
| Metric | `zonata_outbox_queue_depth` |
| Threshold | `>= 50` pending messages |
| Source of truth | `core/alerting_engine.py`, `core/observability_stack.py` |

## What it means

The transactional outbox holds side effects that must be delivered exactly once (external writes, notifications, ledger appends). A depth at or above 50 means delivery is falling behind the enqueue rate. Messages are not lost — they are queued — but anything depending on them is stale.

## First 5 minutes

1. Confirm the alert is real, not scrape lag:
   - `GET /api/health` returns `status: ok`
   - the metric is still above threshold on two consecutive reads
2. Determine direction of travel: is depth growing, flat, or draining? Flat or draining is degraded-but-stable; growing is an incident.
3. Check whether a downstream dependency is failing (connector errors, provider timeouts). The outbox is a symptom; the connector is usually the cause.
4. Check whether a dispatcher process is alive and how many workers are running.

## Mitigation

- **Downstream failing:** fix or disable the failing connector through the governed integration surface. Do not delete outbox rows to clear the metric.
- **Dispatcher starved:** scale out dispatcher workers. Consumers must remain idempotent; the outbox guarantees at-least-once, not exactly-once, at the transport layer.
- **Poison message:** quarantine the single failing message via the governed path and record the reason. Never bulk-skip.

## Do not

- Delete or truncate outbox rows to make the metric green.
- Increase the alert threshold as a fix. Thresholds are part of the evidence surface.

## Verification and evidence

- Depth returns below threshold and stays there for one full dispatch cycle.
- Capture: before/after depth, the incident window, the root cause, and the action taken. Attach to the evidence ledger for the affected tenant.

## Escalation

Platform Lead if not draining within 30 minutes, or immediately if any message has been pending longer than its contractual delivery window.
