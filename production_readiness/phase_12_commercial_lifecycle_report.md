# Phase 12 Commercial SaaS Lifecycle, Entitlements & Billing Architecture Report

**Version:** 1.0.0-GA  
**Branch:** `engineering/production-readiness-gap-closure`  
**Execution Date:** October 19, 2026  
**Status:** IMPLEMENTED & QUALIFIED  

---

## 1. Executive Summary

Phase 12 delivers the commercial foundation for ZONATA, establishing an authoritative SaaS subscription lifecycle, server-side entitlement enforcement engine, cryptographic multi-gateway payment adapters (Stripe and Razorpay), and automated reconciliation with the Phase 11 AI CEO economic governor.

### Core Principle
> **Constitutional Invariant:** ZONATA IS THE SOLE ENTITLEMENT AUTHORITY.  
> The workflow is strictly: `Plan -> Entitlement -> Quota -> Usage -> Authorization`.  
> Payment gateways (Stripe/Razorpay) process transactions; they **never** decide business authorization.

---

## 2. Subscription Lifecycle State Machine

The subscription lifecycle is governed by an authoritative finite state machine (`SubscriptionStatus`) with deterministic transition guards and non-destructive suspension semantics:

```
                      +------------+
                      |  TRIALING  |
                      +------------+
                        /    |    \
                       /     |     \
                      v      v      v
              +--------+  +-------+  +-----------+
              | ACTIVE |  |EXPIRED|  | CANCELLED |
              +--------+  +-------+  +-----------+
               /   |   \      |            |
              /    |    \     | (Renewal)  | (Reactivation)
             v     |     v    v            v
      +--------+   |   +-----------+  +--------+
      |PAST_DUE|   |   |   ACTIVE  |  | ACTIVE |
      +--------+   |   +-----------+  +--------+
        /    \     |
       /      \    |
      v        v   v
  +------+   +-----------+
  |UNPAID|   | SUSPENDED |
  +------+   +-----------+
      \            /
       \          /
        v        v
      +-----------+
      | CANCELLED |
      +-----------+
```

### Transition Matrix
- `TRIALING` -> `ACTIVE` (payment method added), `EXPIRED` (trial ended), `CANCELLED` (user opted out).
- `ACTIVE` -> `PAST_DUE` (payment failed), `SUSPENDED` (administrative hold / dunning), `CANCELLED` (user request).
- `PAST_DUE` -> `ACTIVE` (payment recovered), `UNPAID` (grace period elapsed), `SUSPENDED`, `CANCELLED`.
- `UNPAID` -> `ACTIVE` (balance settled), `SUSPENDED`, `CANCELLED`.
- `SUSPENDED` -> `ACTIVE` (reinstated), `CANCELLED`, `EXPIRED`.
- `CANCELLED` -> `ACTIVE` (new subscription cycle).
- `EXPIRED` -> `ACTIVE` (subscription renewed).

### Grace Period Mechanics
When an account enters `PAST_DUE`, a configurable `grace_period_end` timestamp (default: 3 days / 259,200 seconds) is applied:
- During active grace period: Basic non-token read operations are permitted; high-risk operations and token expansions exceeding 100,000 tokens are restricted.
- After grace period expiry: All entitlement checks fail closed (`Account past due: Grace period expired. Payment required.`).
- Non-destructive suspension: Transitioning to `SUSPENDED` blocks all execution immediately without altering historical token usage, member lists, or vector memory. Reinstatement to `ACTIVE` restores access seamlessly.

---

## 3. Central Server-Side Entitlement Enforcer

Entitlement enforcement is strictly evaluated on the server side prior to any capability dispatch or resource allocation:

### Canonical Tier Matrix

| Entitlement Metric | FREE | STARTER | PRO | ENTERPRISE |
|:---|:---:|:---:|:---:|:---:|
| **Monthly Price (USD)** | $0.00 | $49.00 | $199.00 | $999.00 |
| **Tokens / Month** | 1,000,000 | 10,000,000 | 50,000,000 | 500,000,000 |
| **Browser Minutes / Month** | 60 | 600 | 3,000 | 50,000 |
| **Terminal Seconds / Month** | 600 | 6,000 | 30,000 | 500,000 |
| **Storage Capacity** | 500 MB | 5 GB | 50 GB | 1 TB |
| **Active Agents Ceiling** | 2 | 10 | 50 | 500 |
| **Member Seats Ceiling** | 1 | 5 | 25 | 100 |
| **Workflow Concurrency** | 1 | 3 | 10 | 50 |
| **Feature Catalog** | Core Agents, Basic Terminal, SQLite | Core Agents, Browser-Use, Universal Terminal, Scraping | Tool Factory, Temporal Workflows, S3/MinIO, A2A Mesh | Dedicated Nodes, Custom LLMs, Air-Gap, Economic Governance |

---

## 4. Cryptographic Multi-Gateway Webhook Engines

Inbound gateway callbacks are protected against forgery, timing attacks, and replay vulnerabilities:

### 1. Stripe Webhook Verification (`StripeBillingAdapter`)
- Scheme: HMAC-SHA256 signature verification over `{timestamp}.{payload}` using `STRIPE_WEBHOOK_SECRET`.
- Anti-Replay: Verifies that header timestamp drift is within 300 seconds (`|current_time - timestamp| <= 300`).
- Comparison: Constant-time comparison via `hmac.compare_digest`.
- Event Routing:
  * `customer.subscription.created` / `updated` -> Synchronizes subscription status.
  * `customer.subscription.deleted` -> Transitions subscription to `CANCELLED`.
  * `invoice.payment_succeeded` -> Transitions subscription to `ACTIVE`.
  * `invoice.payment_failed` -> Transitions subscription to `PAST_DUE` with grace period.

### 2. Razorpay Webhook Verification (`RazorpayBillingAdapter`)
- Scheme: HMAC-SHA256 signature verification over raw request payload using `RAZORPAY_WEBHOOK_SECRET`.
- Header: `X-Razorpay-Signature`.
- Comparison: Constant-time comparison via `hmac.compare_digest`.
- Event Routing:
  * `subscription.activated` / `charged` / `payment.captured` -> Transitions subscription to `ACTIVE`.
  * `subscription.halted` / `payment.failed` -> Transitions subscription to `PAST_DUE`.
  * `subscription.cancelled` -> Transitions subscription to `CANCELLED`.

### 3. Atomic Webhook Idempotency Engine
Every processed webhook event is recorded in the `billing_webhook_events` table (`event_id`, `provider`, `event_type`, `processed_at`, `status`). Duplicate deliveries are intercepted and return `DUPLICATE_IGNORED` without re-executing state mutations.

---

## 5. Economic Governor Reconciliation

Autonomous agent execution governed by Phase 11 (`EconomicGovernanceEngine`) is wired directly into the billing usage ledger:
1. **Two-Phase Reservation:** Tasks reserve budgetary ceilings before execution begins.
2. **Settlement Execution:** Upon task completion, actual tokens and actual USD expenditures are settled via `settle_budget()`.
3. **Billing Reconciliation:** `reconcile_economic_settlement()` ingests settled reservations into the tenant usage snapshot and `usage_records` table under idempotency protection (`reconciled_reservations`), ensuring customer invoices accurately capture agent swarm consumption without double billing.

---

## 6. Database Migration Specification

PostgreSQL migration script: `migrations/pg/0003_phase_12_billing_schema.sql`

```sql
-- Phase 12: Commercial SaaS Lifecycle, Entitlements & Multi-Gateway Billing Schema Migration
CREATE TABLE IF NOT EXISTS tenant_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'STARTER',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    current_period_start REAL NOT NULL,
    current_period_end REAL NOT NULL,
    grace_period_end REAL,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    payment_provider TEXT NOT NULL DEFAULT 'internal',
    provider_customer_id TEXT,
    provider_subscription_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata JSONB,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS billing_webhook_events (
    event_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB,
    processed_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROCESSED',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS tenant_invoices (
    invoice_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subscription_id TEXT,
    amount_due_usd REAL NOT NULL,
    amount_paid_usd REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'PAID',
    period_start REAL NOT NULL,
    period_end REAL NOT NULL,
    line_items JSONB,
    created_at REAL NOT NULL,
    paid_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
```
