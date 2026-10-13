# URA / ZONATA SaaS — Staging Deployment Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Files**: `docker-compose.prod.yml`, `PRODUCTION_DEPLOYMENT_RUNBOOK.md`, `.env.production.template`, `infra/`  
**Formal Verdict**: **CONDITIONAL PASS / BLOCKED**

---

## 1. Executive Summary & Verdict Rationale

This qualification report evaluates the containerization topology, multi-service orchestration, staging deployment runbooks, external integration safety, and runtime isolation controls designed for the staging and production deployment of the URA / ZONATA Enterprise SaaS platform.

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
1. **`nginx`**: Ingress gateway terminating TLS 1.3. Enforces HTTP Strict Transport Security (`HSTS`), Content Security Policy (`CSP`), and IP rate limiting.
2. **`app`**: Serves compiled enterprise web client assets. Executes as unprivileged user (`UID 1001:1001`).
3. **`api`**: Python REST API server with PBKDF2 authentication, token verification, and relational CRM persistence. Probes: `/health`, `/livez`, `/readyz`.
4. **`db` (`postgres:16-alpine`)**: Relational database bound solely to internal `zonata_backend` bridge network. Automated healthcheck: `pg_isready -U zonata_admin -d zonata_prod`. Volume persistence: `postgres_data`.
5. **`redis` (`redis:7-alpine`)**: Fast cache and task queue broker for asynchronous mission dispatch.
6. **`worker` & `scheduler`**: Asynchronous job execution and cron schedules with clean production mode enforced.
7. **`prometheus` & `grafana`**: Telemetry collection and SRE monitoring dashboards.

---

## 3. External Integration & Connector Safety Inventory

All external interfaces and third-party connector adapters are inventoried and explicitly classified across 5 formal tiers:

| Connector / Subsystem | Location | Classification | Operational State & Safety Controls |
|---|---|---|---|
| **A2A Interoperability Gateway** | `core/a2a_interoperability_runtime.py` | `LIVE_CONFIGURED` | In-process agent-to-agent protocol with Merkle audit evidence. Fully functional. |
| **Model Context Protocol (MCP)** | `core/mcp_interoperability_runtime.py` | `LIVE_CONFIGURED` | Governed stdio/SSE MCP tool invocation gateway with killswitch and permission enforcement. |
| **Universal Automation Fabric** | `core/automation_fabric.py` | `LIVE_CONFIGURED` | Background delegation worker and job scheduler. Active. |
| **Hospitality Production Connector** | `core/hospitality_production_connector.py` | `LIVE_NOT_CONFIGURED` | Full REST adapter; fails closed when PMS URL or credentials missing. |
| **Nango Unified SaaS Gateway** | `core/nango_integration_runtime.py` | `LIVE_NOT_CONFIGURED` | Unified sync gateway; reports unconfigured when `NANGO_SECRET_KEY` missing. |
| **OpenHands Container Runtime** | `core/openhands_execution_runtime.py` | `LIVE_NOT_CONFIGURED` | Docker execution sandbox; reports offline when daemon unavailable. |
| **Browser Execution Gateway** | `core/browser_use_execution_runtime.py` | `LIVE_NOT_CONFIGURED` | Playwright browser runner; reports offline when browser process absent. |
| **Keycloak IdP Client** | `core/keycloak_idp.py` | `LIVE_NOT_CONFIGURED` | Enterprise SSO connector; reports unconfigured until realm URL injected. |
| **HashiCorp Vault Client** | `core/vault_client.py` | `LIVE_NOT_CONFIGURED` | Secret manager connector; reports offline when `VAULT_ADDR` unconfigured. |
| **Temporal Workflow Engine** | `core/temporal_durable_runtime.py` | `LIVE_NOT_CONFIGURED` | Durable orchestration; reports disconnected until gRPC endpoint configured. |
| **NATS Event Bus** | `core/nats_event_bus.py` | `LIVE_NOT_CONFIGURED` | Distributed messaging; reports disconnected until cluster configured. |
| **PostgreSQL Database** | `core/db.py` | `LIVE_NOT_CONFIGURED` | Dialect ready; reports disconnected until `DATABASE_URL` configured. |
| **Hospitality PMS Contract Simulator** | `core/connectors.py` | `SIMULATED` | In-memory contract simulation for rate/booking reconciliation in local tests. Output is sealed with `SIMULATED` epistemic state and cannot be counted as verified evidence. |
| **Accounting Balance Simulator** | `core/connectors.py` | `SIMULATED` | In-memory balance matching interface for local tests. |
| **Payment Gateway Simulator** | `core/connectors.py` | `SIMULATED` | In-memory webhook verification for offline simulation. |
| **Stripe Test Mode Adapter** | `tests/` fixtures | `TEST_ONLY` | Used strictly with `tok_visa` test tokens in isolated harnesses. Never triggers real financial transactions. |
| **VM Runtime Adapter** | `core/universal_terminal/` | `NOT_IMPLEMENTED` | Hypervisor bridge reserved for cloud infrastructure expansion. |

### Strict Simulation-to-Execution Invariants:
1. **Simulation Epistemic Boundary**: Simulation output (e.g. from `/api/missions/simulate`) is explicitly labeled as `SIMULATED` and strictly barred from updating verified ledger balances.
2. **Approval Gates & Emergency Stop**: High-risk actions require sovereign approval (`ASK_ME`, `DUAL_KEY`, `NEVER`). The emergency stop killswitch persists in database settings and halts execution instantly when tripped.

---

## 4. Host & Runtime Security Isolation

| Security Control | Configuration | Verification Status |
|---|---|---|
| **Host Shell Prohibition** | `ZONATA_ALLOW_HOST_FALLBACK=0` | **ENFORCED** (Terminal engine refuses raw host execution) |
| **Shell Elevation Block** | `ZONATA_ALLOW_HOST_SHELL=0` | **ENFORCED** (Explicit refusal of host shell in production) |
| **Container User Context** | `USER 1001:1001` in Dockerfile | **ENFORCED** (Prevents root container privilege escalation) |
| **Database Port WAN Lock** | Port 5432 bound internally | **ENFORCED** (PostgreSQL is inaccessible from WAN) |
| **Secret Protection** | Read via Docker secrets or `.env` | **ENFORCED** (Zero default keys allowed in production) |

---

## 5. Concise Infrastructure Prerequisite Checklist for Staging Unblock

To advance Staging Deployment and Operations from `CONDITIONAL PASS / BLOCKED` to `PASS`:

1. **Compute Host / Kubernetes Cluster**:
   - Ubuntu 24.04 LTS VM (minimum 4 vCPU, 16 GB RAM) with Docker Engine 26+ and Docker Compose v2.
2. **DNS & Reverse Proxy Ingress**:
   - Dedicated staging hostname (e.g. `staging.zonata.internal`).
   - Reverse proxy with Let's Encrypt TLS 1.3 certificate, HSTS, and rate limiting.
3. **Dedicated Staging Database**:
   - Managed cloud PostgreSQL 16 (AWS RDS, GCP Cloud SQL, or containerized PostgreSQL service) with network connectivity to application container.
4. **Staging Environment Variables**:
   - `.env.staging` populated with test keys for Stripe (`sk_test_...`) and LLM providers.
5. **Automated Smoke Test Verification**:
   - Execute automated staging smoke tests against all 38 routes with zero failures.

---

## 6. Formal Decision

| Evaluation Area | Verdict | Summary |
|---|---|---|
| **Deployment Readiness** | **CONDITIONAL PASS / BLOCKED** | Production Docker Compose topology, integration safety inventory, network partitioning, and runbooks are validated. Physical staging deployment remains blocked pending target cluster provisioning. |
