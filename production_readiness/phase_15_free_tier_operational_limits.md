# Phase 15 Free-Tier Operational Limits & Capacity Guidelines

**Evaluation Date:** October 19, 2026  
**Infrastructure Architecture:** Zero-Cost Cloud Staging  
**PaaS Compute Target:** Render Web Service (Free Tier)  
**Database Compute Target:** Neon Serverless PostgreSQL 16 (Free Tier)  
**Operational Invariant:** ZERO PAID UPGRADES REQUIRED. The platform is architected to operate sustainably within existing free quotas.  

---

## 1. Render Free Tier Architecture & Operational Constraints

| Dimension | Render Free Tier Specification | Operational Impact on ZONATA | Mitigation / Architectural Defense |
|:---|:---:|:---|:---|
| **Memory (RAM)** | **512 MB** | Risk of OOM kill if heavy in-memory data frames or ML models are loaded in-process. | Streamed cursor pagination; compact data structures; heavy LLM inference delegated to external APIs. |
| **CPU Allocation** | **Shared vCPU** (throttled) | Multi-process forks and high-concurrency requests experience CPU throttling. | Connection concurrency capped; worker pools bounded to 8 concurrent threads; non-blocking async I/O. |
| **Inactivity Spin-Down** | **15 minutes** | Web container transitions to suspended state after 15 minutes of zero HTTP traffic. | Healthcheck probe `/readyz` configured; cold-start initialization completes in <3.5 seconds. |
| **Cold Start Latency** | **30 to 50 seconds** (on first inbound TCP handshake after spin-down) | First request after idle period may experience HTTP latency while container pulls and starts. | Client-side progressive loading skeleton UI with informative "Waking Staging Engine" toast. |
| **Monthly Compute Quota** | **750 Instance Hours / Month** | Sufficient to run 1 free web service continuously 24/7 for a 31-day month (744 hours). | Single staging container deployed; auto-deploy handles rolling replacement without duplicate quota consumption. |
| **Bandwidth (Egress)** | **100 GB / month** | Risk of bandwidth exhaustion if uncompressed large assets or raw database dumps are served. | Gzip/Brotli compression enabled; static web assets bundled and minified; zero raw binary DB streaming. |
| **Persistent Disk** | **0 GB (Ephemeral Disk)** | Local files written to container filesystem are wiped on container restart or redeploy. | Database state persisted in Neon PostgreSQL; Merkle audit ledger mirrored to database. |

---

## 2. Neon Serverless PostgreSQL Free Tier Constraints

| Dimension | Neon Free Tier Specification | Operational Impact on ZONATA | Mitigation / Architectural Defense |
|:---|:---:|:---|:---|
| **Storage Capacity** | **0.5 GiB (512 MB)** | High-frequency telemetry or audit logging could exceed 512 MB over extended evaluation. | Automatic audit compaction; historical telemetry older than 90 days pruned; relational index efficiency. |
| **Active Branches** | **1 Root + 1 Child Branch** | Unlimited branching unavailable on free tier. | Staging tests execute against primary branch with transaction isolation and synthetic tenant cleanup. |
| **Compute Scale-to-Zero** | **5 minutes of inactivity** | Postgres compute endpoint shuts down after 5m idle, causing ~1.5s latency on next query. | Neon Connection Pooler (`-pooler` domain suffix) keeps client connection open; pgbouncer amortizes wakeup. |
| **Connection Pooling** | **Up to 10,000 pooled connections via PgBouncer** | Exceeding direct connection limit (typically 20 on free tier) causes `too many clients` errors. | `DATABASE_URL` uses Neon pooler; `DATABASE_MIN_POOL_SIZE=1`, `DATABASE_MAX_POOL_SIZE=8` in `render.yaml`. |
| **Compute Unit (CU)** | **0.25 CU minimum** (autoscaling up to 2 CU on free tier) | Query bursts may experience slight latency while compute scales from 0.25 to 1 CU. | Optimized SQL queries with composite B-Tree indexes on `(tenant_id, created_at)` and `(company_id)`. |

---

## 3. Free-Tier Operational Runbook & Safe Testing Protocol

To ensure continuous staging operation without incurring unexpected cloud charges or exhausting quotas:

1. **Synthetic Data Hygiene**:
   - Synthetic enterprise simulation test cases create tenants with prefix `tnt_synth_*` or `tnt_test_*`.
   - Automated cleanup scripts purge test fixtures post-execution to conserve the 0.5 GiB storage limit.
2. **Cold-Start Anticipation**:
   - Automated synthetic smoke runners send an initial wake-up probe to `GET /healthz` with a 45-second socket timeout before initiating test batteries.
3. **Connection Pooling Mandatory**:
   - Always connect using the pooled connection string (`ep-broad-sky-b4jnm313-pooler.c-6.us-east-2.aws.neon.tech`).
   - Never use direct unpooled connections for web request handlers to prevent connection exhaustion.
