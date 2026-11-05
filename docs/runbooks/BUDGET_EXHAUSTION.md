# Runbook — Tenant Hard Budget Limit Reached

| Field | Value |
|---|---|
| Alert | `ALT_BUDGET_EXHAUSTED` — Tenant Hard Budget Limit Reached |
| Severity | HIGH |
| Owner | `FINANCE_DIRECTOR` |
| Metric | `zonata_budget_exhaustions_total` |
| Threshold | `>= 1` |
| Source of truth | `core/alerting_engine.py`, `GET /api/v1/economic/budgets` |

## What it means

A tenant or company has hit a hard spend limit. Spending-limited work must stop; the platform is expected to have refused the work rather than overrun. The alert confirms a limit was enforced, so the first question is not "how do we spend more" but "was the refusal correct".

## First 5 minutes

1. Read the budget state: `GET /api/v1/economic/budgets`.
2. Identify the scope that exhausted: tenant, company, department, or agent instance.
3. Identify the workload that was refused, and whether any refused work was silently retried in a loop (retry storms are the common companion failure).
4. Confirm the limit was enforced at the gateway and not merely observed after the spend happened. If spend overran the limit, treat it as a control failure, not a billing event.

## Mitigation

- If the limit is correct: the work stops. Prioritise the owner's queued work, do not raise the limit by default.
- If the limit is wrong: raise it through the governed approval path with an explicit amount, scope, and expiry. Never raise a limit inside the failing workflow.
- Never disable a budget guard to unblock a demo.

## Do not

- Top up from inside an agent loop.
- Treat "budget exhausted" as an infrastructure error and auto-retry.
- Aggregate multiple small top-ups to avoid the approval threshold.

## Verification and evidence

- Budget state reflects the new limit (if changed) and refused work is recorded with a reason.
- No spend occurred between exhaustion and limit change.
- Attach: budget scope, limit, observed spend, refused workload ids, and the approval record for any change.

## Escalation

AI CEO for reallocation decisions; Human Owner for any increase above the approved tenant ceiling.
