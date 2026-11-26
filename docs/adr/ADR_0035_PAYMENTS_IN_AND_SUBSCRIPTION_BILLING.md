# ADR 0035: Inbound Payments and Subscription Billing Orchestration

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 41 (Zero Plaintext Secrets), Rule 59 (Ports Pattern), Rule 62 (Reserved Human Financial Decisions)

---

## 1. Context & Problem Statement
Handling inbound customer payments, invoices, recurring subscriptions, and payment reconciliation across multiple payment gateways (Stripe, Razorpay, Adyen).

## 2. Decision
1. **PaymentsPort Architecture:** Unified abstraction for inbound charges, payment intents, and refund preparation.
2. **Open-Source Orchestration:**
   - **Hyperswitch** (Apache-2.0): Payment orchestration router supporting multi-gateway failover and cost optimization.
   - **Kill Bill** (Apache-2.0): Subscription billing and invoice generation engine.
3. **PCI-DSS Scope Minimization:** ZONATA never stores, processes, or transmits raw credit card numbers. All card handling uses hosted client elements or payment gateway tokens.
4. **Disbursement & Money Out (Rule 62):** Outbound payments, refunds exceeding thresholds, and vendor disbursements strictly require explicit human gateway authorization.

## 3. Consequences
- High-resilience payment routing across multiple providers.
- Absolute isolation of sensitive payment credentials.
