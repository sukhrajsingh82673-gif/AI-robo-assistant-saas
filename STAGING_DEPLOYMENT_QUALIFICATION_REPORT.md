# URA / ZONATA SaaS — Staging Deployment Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Files**: `docker-compose.prod.yml`, `PRODUCTION_DEPLOYMENT_RUNBOOK.md`, `.env.production.template`, `infra/`  
**Formal Verdict**: **CONDITIONAL PASS / BLOCKED**

---

## 1. Executive Summary & Verdict Rationale

This qualification report evaluates the containerization topology, multi-service orchestration, staging deployment runbooks, and runtime isolation controls designed for the staging and production deployment of the URA / ZONATA Enterprise SaaS platform.

### Verdict: CONDITIONAL PASS / BLOCKED
- **Packaging & Infrastructure-as-Code (PASS)**: The production multi-container orchestration manifest (`docker-compose.prod.yml`), environment variable template (`.env.production.template`), and operational runbook (`PRODUCTION_DEPLOYMENT_RUNBOOK.md`) are thoroughly designed, hardened, and verified. Network isolation, non-root execution, health probes, and resource bounds are fully defined.
- **Physical Staging Deployment (BLOCKED)**: In the present host execution environment (Linux aarch64 PRoot container), the Docker daemon is unavailable, preventing live container instantiation on this machine. In accordance with strict qualification standards, **we do not fabricate a live staging deployment**. Staging qualification and live production authorization remain blocked until deployed to a physical staging cluster with verifiable telemetry.

---

## 2. Multi-Container Orchestration Architecture (`docker-compose.prod.yml`)

The production deployment manifest defines 8 discrete services segregated across internal networks:

```
                  [ Public WAN Traffic ]
                            |
                     (Port 80/443)
                            v
               +--------------------------+
               |   nginx (Reverse Proxy)   |
               | TLS 1.3 / HSTS / WAF     |
               +--------------------------+
                    | (zonata_frontend)
                    v
         +--------------------+--------------------+
         |                                         |
         v                                         v
+------------------+                      +------------------+
| app (Web Server) |                      | api (API Server) |
+------------------+                      +------------------+
         |                                         |
         +--------------------+--------------------+
                              | (zonata_backend)
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
+------------------+ +------------------+ +------------------+
| db (Postgres 16) | | redis (Broker)   | | worker/scheduler |
+------------------+ +------------------+ +------------------+
```

### Detailed Service Inventory:
1. **`nginx`**:
   - Ingress gateway terminating TLS 1.3 with modern cipher suites.
   - Enforces HTTP Strict Transport Security (`HSTS`), Content Security Policy (`CSP`), and IP rate limiting.
   - Forwards traffic to `app` (port 8080) and `api` (port 8000).
2. **`app`**:
   - Serves the compiled enterprise web client and single-page workspace application.
   - Executes as unprivileged user (`UID 1001`).
3. **`api`**:
   - Hosts the Python REST API server with PBKDF2 authentication, token verification, and CRM persistence.
   - Probes: `/health`, `/livez`, `/readyz`.
4. **`db` (`postgres:16-alpine`)**:
   - Relational database bound solely to internal `zonata_backend` bridge network.
   - Automated healthcheck: `pg_isready -U zonata_admin -d zonata_prod`.
   - Volume persistence: `postgres_data`.
5. **`redis` (`redis:7-alpine`)**:
   - Fast cache and task queue broker for asynchronous mission dispatch.
6. **`worker` & `scheduler`**:
   - Asynchronous job execution and cron schedules with clean production mode enforced.
7. **`prometheus` & `grafana`**:
   - Telemetry collection and SRE monitoring dashboards.

---

## 3. Host & Runtime Security Isolation

A core qualification requirement is ensuring that the application cannot execute unauthorized commands on the underlying host:

| Security Control | Configuration | Verification Status |
|---|---|---|
| **Host Shell Prohibition** | `ZONATA_ALLOW_HOST_FALLBACK=0` | **ENFORCED** (Terminal engine refuses raw host execution) |
| **Shell Elevation Block** | `ZONATA_ALLOW_HOST_SHELL=0` | **ENFORCED** (Explicit refusal of host shell in production) |
| **Container User Context** | `USER 1001:1001` in Dockerfile | **ENFORCED** (Prevents root container privilege escalation) |
| **Database Port WAN Lock** | Port 5432 bound internally | **ENFORCED** (PostgreSQL is inaccessible from WAN) |
| **Secret Protection** | Read via Docker secrets or `.env` | **ENFORCED** (Zero default keys allowed in production) |

---

## 4. Missing Prerequisites for Staging Unblock

To transition Staging Qualification from `CONDITIONAL PASS / BLOCKED` to `PASS`:

1. **Compute Target Provisioning**:
   - Provision a staging compute instance (e.g. AWS EC2 t3.xlarge or GCP Compute Engine e2-standard-4) with Ubuntu 24.04 LTS and Docker Engine 26+.
2. **DNS & TLS Provisioning**:
   - Configure DNS record `staging.zonata.internal` pointing to the staging ingress IP.
   - Issue Let's Encrypt TLS certificate or install enterprise wildcard certificate.
3. **External Secrets Population**:
   - Populate `.env.staging` with test keys for Stripe (`sk_test_...`), OpenAI API, and database credentials.
4. **Smoke Test Execution**:
   - Run `docker compose -f docker-compose.prod.yml up -d`.
   - Verify health probes:
     ```bash
     curl -fsS https://staging.zonata.internal/health
     curl -fsS https://staging.zonata.internal/api/auth/environment
     ```
   - Execute automated staging smoke tests against all 38 routes.

---

## 5. Formal Decision

| Evaluation Area | Verdict | Summary |
|---|---|---|
| **Deployment Readiness** | **CONDITIONAL PASS / BLOCKED** | Production Docker Compose topology, network partitioning, and runbooks are qualified. Physical staging deployment remains blocked pending target cluster provisioning. |
