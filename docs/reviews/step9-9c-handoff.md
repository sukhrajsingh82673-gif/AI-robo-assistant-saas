# OpenCode Handoff: Sub-Step 9C

## 1. Summary of Changes
- Created `core/billing/port.py` providing `BillingPort` and provider adapters (`SandboxBillingAdapter`, `PaddleBillingAdapter`, `StripeBillingAdapter`, `LagoBillingAdapter`).
- Created `core/billing/plans.py` declaring versioned subscription plans as data with integer cent overage math.
- Created `core/billing/metering.py` implementing append-only usage event logging with SHA-256 chaining from genesis hash and tamper detection.
- Created `core/billing/cost_caps.py` providing soft cap (80%) alerts and hard cap (100%) auto-halts.
- Created `core/billing/lifecycle.py` enforcing delinquency transitions (grace period -> restricted read-only -> export window) and guaranteeing legal holds always block data deletion.
- Created `tests/test_step9c_billing.py`.

## 2. Verification Commands
```bash
pytest -v tests/test_step9c_billing.py
```

## 3. Claims and Invariants
- Rule 78: Billing delinquency never deletes customer data; 14-day grace period and 30-day read-only mode verified; legal holds strictly prevent data purging.
- Rule 79: All financial calculations are in minor integer units (USD/EUR cents); subtotal + tax = total verified to the exact cent; zero credit card numbers or CVVs stored.
- Rule 24: Unconfigured external adapters report `NOT_CONFIGURED`.
