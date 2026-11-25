# ADR 0048: Billing and Tax Architecture (Rule 78 & Rule 79)

## Status
Accepted

## Context
Step 9 requires customer subscription management, metered usage billing, and statutory tax calculation. Choosing a billing model directly impacts regulatory obligations, VAT/GST filing liabilities, chargeback liabilities, and corporate licensing.
Three distinct billing architectures are evaluated:
1. **Merchant of Record (MoR) — e.g., Paddle:**
   - Paddle acts as the legal reseller and merchant of record.
   - Paddle assumes global sales tax, VAT, GST calculation, collection, filing, and chargeback liabilities.
   - Ideal for cross-border SaaS without requiring tax registrations in 50+ jurisdictions.
   - License/SDK: Paddle Python SDK (MIT).
2. **Payment Gateway with Integrated Tax — e.g., Stripe Billing + Stripe Tax:**
   - ZONATA remains the legal seller; Stripe acts as processor and tax calculation service.
   - ZONATA must register for VAT/GST where economic nexus is met and file taxes directly.
   - License/SDK: Stripe Python SDK (MIT).
3. **Self-Hosted Billing Engine — e.g., Kill Bill or Lago:**
   - Kill Bill (Apache-2.0): Java-based enterprise billing platform.
   - Lago (AGPL-3.0 as evaluated in README; boundary network service): Open-source metering and billing engine. Under Rule 4, Lago must run as an isolated network service marked `BOUNDARY — legal review`.

## Decision
1. **Implement `BillingPort` Abstraction:**
   - Decouple application core from specific billing providers.
   - Define canonical billing operations: `create_customer`, `subscribe_plan`, `report_usage`, `fetch_invoices`, `handle_webhook`.
2. **Provider Adapters:**
   - Provide `PaddleBillingAdapter`, `StripeBillingAdapter`, `LagoBillingAdapter`, `SandboxBillingAdapter`, and `NotConfiguredBillingAdapter`.
   - Adapters remain `NOT_CONFIGURED` until live provider credentials are provided by the business owner.
   - Test suites execute against `SandboxBillingAdapter` and deterministic replay contract fixtures.
3. **Owner Business Action:**
   - The final choice of MoR vs Stripe vs Lago is reserved for the owner and legal accountant.

## Consequences
- **Positive:** Zero vendor lock-in; flexible tax liability allocation; strict compliance with Rule 24 (`NOT_CONFIGURED`) and Rule 78 (billing never deletes data).
- **Negative:** Maintaining provider abstraction requires periodic synchronization with external API changes.
