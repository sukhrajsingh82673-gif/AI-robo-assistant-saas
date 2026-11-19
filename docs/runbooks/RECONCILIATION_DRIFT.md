# Runbook — External Action Drift Detected

| Field | Value |
|---|---|
| Alert | `ALT_RECONCILIATION_DRIFT` — External Action Drift Detected |
| Severity | CRITICAL |
| Owner | `REVENUE_CONTROLLER` |
| Metric | `zonata_reconciliation_drift_total` |
| Threshold | `>= 1` |
| Source of truth | `core/alerting_engine.py`, reconciliation endpoints listed below |

## What it means

An autonomous agent performed an external mutation (price, invoice, subscription, seat, campaign spend) and the platform's record of that action no longer matches the external system's state. This is a correctness and trust failure, not a performance issue. One drift is enough to fire.

## First 5 minutes

1. Freeze autonomous mutations for the affected tenant/company before investigating. Reverting a wrong action is cheap; a second wrong action is not.
2. Identify the drifted entity: external system, object id, expected value, observed value, and the action envelope / evidence id that produced the expected value.
3. Pull the reconciliation record:
   - `POST /api/v1/billing/settlement/reconcile`
   - `POST /api/nango/reconcile`
   - `POST /api/coworker/recovery/reconcile`
4. Determine who is authoritative for the field. If the platform's evidence ledger is authoritative, correct the external system. If the external system is authoritative (e.g. a human edited it there), record the human override — do not silently "fix" the ledger.

## Mitigation

- Replay-safe correction only: corrections must be idempotent and carry a reference to the original action envelope.
- If the drift came from a retried external call, verify the external system's idempotency key was honoured before retrying again.
- Keep the kill switch engaged for the specific integration until the drift is explained, not merely until the numbers match.

## Do not

- Reset the drift counter, or mark the reconciliation as clean without an external read-back.
- Edit evidence records. Evidence is append-only; corrections are new records that reference the old one.

## Verification and evidence

- External read-back shows the corrected value.
- Drift counter returns to zero and a fresh reconcile run reports zero drift.
- Attach: action envelope id, evidence ids (before and after), reconcile payload, and the human approval for the correction if one was required.

## Escalation

Immediate Human Owner notification. Financial drift additionally requires Finance Director sign-off before the integration is re-enabled.
