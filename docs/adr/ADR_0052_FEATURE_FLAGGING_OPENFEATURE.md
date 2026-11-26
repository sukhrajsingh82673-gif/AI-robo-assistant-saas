# ADR 0052: Feature Flagging with OpenFeature (Rule 80 & Rule 84)

## Status
Accepted

## Context
Product readiness requires releasing features gradually, executing dark launches, toggling beta capabilities per tenant, and instantly triggering emergency kill-switches (for example, disabling a degraded external model provider or revoked marketplace extension) without deploying code.

## Decision
1. **OpenFeature Standard Implementation:**
   - Adopt the OpenFeature specification (`core/flags/openfeature_provider.py`).
   - Implement an in-process provider supporting boolean, string, and numeric evaluation contexts (targeting by tenant ID, plan tier, environment).
2. **Safe Defaults & Kill-Switches:**
   - Default rule: all newly introduced features default to `OFF` unless explicitly entitled or enabled.
   - Emergency kill-switches can be engaged immediately via Tenant Admin or Platform Operator consoles.
3. **Audit Trail & Immutability:**
   - Every flag toggle, override, and evaluation change is logged to the immutable audit ledger with the operator ID and justification timestamp.

## Consequences
- **Positive:** Zero-downtime feature control, safe rollout stages, fast incident mitigation.
- **Negative:** Codebase must be periodically cleaned of obsolete flag branches.
