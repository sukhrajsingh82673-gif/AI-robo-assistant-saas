# Production Reliability & Disaster Recovery (DR) Report

**Evaluation Date:** October 19, 2026  
**Infrastructure Target:** Render Cloud Staging / Production + Neon Serverless PostgreSQL 16  
**RTO Objective:** < 15 Minutes  
**RPO Objective:** < 5 Minutes  
**DR Status:** QUALIFIED  

---

## 1. Reliability & High Availability Architecture

ZONATA combines a stateless application tier running on Render container instances with a serverless, horizontally autoscaling, multi-AZ database tier on Neon PostgreSQL 16.

```
       [ Public Users / Webhooks ]
                   |
                   v (Cloudflare TLS 1.3 / DDOS Protection)
          [ Render Web Service ]
       (Stateless App / SimpleHTTP)
          /        |         \
         v         v          v
   [ Neon Auth ] [ Neon Functions ] [ Neon PG 16 Pooler ]
                                         |
                                         v
                              [ Neon Storage Engine ]
                           (Multi-AZ WAL / Instant Point-in-Time)
```

---

## 2. Disaster Recovery Targets & Capabilities

| Disaster Recovery Metric | Target Objective | Implementation Mechanism | Demonstrated Capability |
|:---|:---:|:---|:---:|
| **Recovery Point Objective (RPO)** | **< 5 Minutes** | Neon Serverless Continuous WAL streaming & point-in-time recovery | Instant branch recovery to any second in the preceding 7 days |
| **Recovery Time Objective (RTO)** | **< 15 Minutes** | Containerized blue/green redeploy on Render + automated schema migration | Cold container startup in ~45s; schema migration replay in < 30s |
| **Data Integrity Verification** | **100% Invariant** | Merkle evidence audit ledger (`ca8181...`) & Relational foreign keys | Exact digest verification verified on `/readyz` probe |

---

## 3. Database Migration Sequence

Database schema evolution is strictly versioned and idempotent (`CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, `ADD COLUMN IF NOT EXISTS`):

1. **`migrations/pg/0001_postgresql_full_schema.sql`:**
   - 172 relational tables establishing core tenant isolation, user management, agent configurations, CRM entities, vector memory catalogs, and audit logs.
2. **`migrations/pg/0002_phase_11_governance_schema.sql`:**
   - Governance extensions: `enterprise_budgets` token columns, `enterprise_budget_reservations`, and `action_approval_nonces` tables with index optimization.
3. **`migrations/pg/0003_phase_12_billing_schema.sql`:**
   - Commercial lifecycle tables: `tenant_subscriptions`, `billing_webhook_events`, and `tenant_invoices` with JSONB payloads and cascade foreign key constraints.

---

## 4. Worker Lifecycle & Failure Modes

### 1. Stateless Worker Recycling
- Autonomous agent executions are decoupled from long-lived server processes.
- All agent context, working memory, and vector clocks are persisted to `governed_memory_records` and `stateful_agent_identities`.
- If an agent worker container is killed mid-task, the next worker container reconstitutes state from the database without state loss or memory corruption (`test_stateful_agent_memory.py` - zero-loss restart recovery).

### 2. Fail-Closed Network Partition Behavior
- In the event of a database partition, the application immediately drops health status (`/readyz` returns HTTP 503 `DATABASE_UNAVAILABLE`).
- Unsettled budget reservations expire cleanly via TTL (`ReservationExpiredException`), preventing orphaned budget locks.
- Webhook callbacks from Stripe and Razorpay fail gracefully with HTTP 500, instructing payment gateways to back off and retry according to their standard exponential retry policies.

---

## 5. Secret Separation & Environmental Hygiene

1. **Zero Secret Leaks in Codebase:**
   - Codebase audit confirmed that no production API keys, database credentials, or private certificates exist in git history.
   - All connection strings and exception outputs pass through `sanitize_db_url()`.
2. **Environmental Partitioning:**
   - Development, Staging, and Production maintain disjoint credentials:
     * `ZONATA_BOOTSTRAP_SECRET`: Isolated per environment.
     * `STRIPE_WEBHOOK_SECRET` & `RAZORPAY_WEBHOOK_SECRET`: Isolated webhook endpoints.
     * `DATABASE_URL`: Staging connects to Neon `ep-broad-sky-b4jnm313`; Production connects to dedicated high-capacity compute endpoint.
