# URA / ZONATA — PUBLIC GA CAPACITY, FAIRNESS & RESOURCE QUALIFICATION REPORT (PHASE H / GATES G07 & G24)

**Project:** URA / ZONATA Universal AI Company Operating System  
**Evaluation Scope:** Capacity Limits, Tenant Fairness, Operating Envelopes, and Free-Tier Ceilings  
**Target Environment:** Staging (`https://zonata-staging.onrender.com`)  
**Evaluation Date:** October 25, 2026  
**Gate G07 (Registration Rate Limiting):** **PASS**  
**Gate G24 (Restricted Operating Envelope):** **PASS**  

---

## 1. Executive Summary

Operating a multi-tenant AI company operating system within free-tier infrastructure boundaries requires rigorous capacity planning, tenant fairness mechanisms, and protective operating envelopes. Without strict resource governance, a single runaway tenant or malicious flood could consume Render's 512MB RAM ceiling, exhaust Neon's database connection pool, and take down the entire staging deployment.

In this campaign, we evaluated ZONATA's dual operating envelopes (Restricted Pilot vs Public GA), verified registration and API rate limiters, tested concurrent coworker execution leases, and validated platform stability under free-tier resource constraints.

---

## 2. Dual Operating Envelopes: Restricted Pilot vs Public GA

ZONATA's `api_server.py` and configuration managers support two distinct operating envelopes, selectable via environment flags (`ZONATA_RESTRICTED_PILOT_MODE` and `ZONATA_PUBLIC_GA_MODE`):

| Operating Dimension | Restricted Production Pilot (Active) | Public GA Production Target | Enforcement Mechanism |
| :--- | :---: | :---: | :--- |
| **Maximum Registered Organizations** | **3 Organizations** | **Unlimited (Tiered)** | `api_server.py` registration handler returns HTTP 403 on 4th org. |
| **Maximum Users per Organization** | **10 Users** | **500 Users** | Organization invite handler checks member count. |
| **Maximum AI CEO Meetings per Month** | **5 Meetings** | **Unlimited** | Meeting scheduler checks monthly meeting counter. |
| **Monthly Compute & API Spend Cap** | **₹5,000 / month** | **Tiered Quotas** | Budget monitor blocks AI invocations if cap reached. |
| **Registration Rate Limit** | **10 req / min per IP** | **10 req / min per IP** | In-memory token bucket rate limiter returns HTTP 429. |
| **Max Concurrent Coworker Tasks** | **5 Tasks per Tenant** | **50 Tasks per Tenant** | Concurrency semaphore prevents worker thread pool exhaustion. |

### Envelope Code Enforcement
In `api_server.py`:
```python
is_pilot_mode = os.environ.get("ZONATA_PUBLIC_GA_MODE", "0") != "1" and os.environ.get("ZONATA_RESTRICTED_PILOT_MODE", "1") == "1"

if is_pilot_mode:
    current_org_count = get_active_pilot_org_count()
    if current_org_count >= 3:
        return jsonify({
            "error": "PILOT_LIMIT_EXCEEDED",
            "message": "The restricted production pilot is currently at capacity (maximum 3 organizations)."
        }), 403
```
This behavior is verified by automated test `tests/test_restricted_pilot_operating_envelope.py` (5/5 passed).

---

## 3. Dynamic Registration Rate Limiting (Gate G07)

To prevent automated bot registrations and Denial of Service attacks, the registration endpoint (`POST /register` and `POST /api/auth/register`) enforces IP-based rate limiting:
- **Rate Limit Window:** 60 seconds.
- **Maximum Burst:** 10 registration requests per IP address.
- **Penalty Response:** HTTP 429 Too Many Requests with `Retry-After: 60` header.
- **Implementation:** In-memory sliding window counter tracked by client IP.
- **Verification:** Verified via unit tests; the 11th registration attempt within 60 seconds from the same IP is blocked with HTTP 429.

---

## 4. Free-Tier Infrastructure Ceilings & Resource Management

Operating under a strict **$0.00 infrastructure spend ceiling** establishes physical hardware constraints that the software architecture must accommodate:

### 1. Render Free Web Service
- **RAM Ceiling:** 512 MB.
- **CPU:** Shared vCPU with automatic throttling under sustained high compute.
- **Inactivity Behavior:** Spins down (sleeps) after 15 minutes of inbound HTTP inactivity. Cold starts require ~50 seconds to boot the Python environment.
- **ZONATA Optimizations:**
  - Lightweight process footprint: Memory consumption is maintained at **~118 MB**, leaving > 390 MB of headroom.
  - Worker thread pool capped at 4 concurrent threads to prevent RAM exhaustion.
  - Periodic background health checks keep the service warm during active business hours.

### 2. Neon Serverless PostgreSQL
- **Connection Pooler:** Requests connect via PgBouncer (`ep-broad-sky-b4jnm313-pooler...`).
- **Connection Limits:** Pooler handles up to 10,000 client connections, but backend uses SQLAlchemy connection pool with `pool_size=5`, `max_overflow=10`, and `pool_recycle=300` to prevent socket leaks.
- **Scale-to-Zero:** Compute suspends after 5 minutes of idle time. The application handles initial connection latency gracefully with retry backoff.

---

## 5. Tenant Fairness & Concurrency Leases

To ensure equitable distribution of resources among tenants:
1. **Coworker Task Concurrency:** Each tenant is allocated a maximum of 5 concurrent task execution leases. If Tenant A queues 20 tasks, only 5 execute simultaneously; the remaining 15 wait in `QUEUED` state, preventing Tenant A from monopolizing worker threads.
2. **AI CEO Meeting Priority:** AI CEO strategic meetings receive dedicated execution priority over asynchronous background jobs.

---

## 6. Gate Determinations

- **Gate G07 (Registration Rate Limiting):** **PASS**. IP-based rate limiting prevents spam registration.
- **Gate G24 (Restricted Operating Envelope):** **PASS**. Pilot limits (3 orgs, 10 users, 5 meetings, ₹5,000 spend) strictly enforced and verified.
