# Runbook — Kill Switch Barrier Active

| Field | Value |
|---|---|
| Alert | `ALT_KILLSWITCH_ENGAGED` — Platform Kill Switch Barrier Active |
| Severity | CRITICAL |
| Owner | `SECURITY_OFFICER` |
| Metric | `zonata_killswitch_activations_total` |
| Threshold | `>= 1` |
| Source of truth | `core/alerting_engine.py`, per-surface kill switch endpoints |

## What it means

A kill switch is engaged. Autonomous execution on the affected surface is blocked by design. This alert is never "noise": either an automated guard tripped it after a policy violation, or a human engaged it during an incident.

## First 5 minutes

1. Identify **which** surface is blocked and **why** it engaged. Kill switches are independent per surface:
   - `POST /api/automation/killswitch`
   - `POST /api/browser/killswitch`
   - `POST /api/mcp/killswitch`
   - `POST /api/nango/killswitch`
   - `POST /api/openhands/killswitch`
   - `POST /api/temporal/killswitch`
   - `POST /api/a2a/killswitch`
2. Read the triggering evidence record: policy id, tenant, agent instance, and the attempted action.
3. Confirm blast radius: which tenants/companies had work in flight on that surface.

## Re-enabling

Re-enabling requires **dual-key** authority: the Security Officer proposes, the Human Owner approves. Never re-enable to "see if it happens again".

Before approval, require:

- root cause identified and written down;
- the offending policy/agent quota corrected through the governed path;
- a replay of the blocked action in simulation showing it would now be denied or handled correctly.

## Do not

- Disengage a kill switch programmatically inside the same request that detected the violation.
- Treat a kill switch as a substitute for fixing the underlying authority model.
- Disable the alert to stop notifications.

## Verification and evidence

- Post-re-enable: the surface accepts only policy-compliant work; a deliberately non-compliant action is still denied (negative test).
- Attach: engagement timestamp, trigger evidence id, approver identity, re-enable timestamp, and the negative test result.

## Escalation

Immediate Human Owner notification. Any engagement that was not human-initiated must be treated as a potential safety incident until proven otherwise.
