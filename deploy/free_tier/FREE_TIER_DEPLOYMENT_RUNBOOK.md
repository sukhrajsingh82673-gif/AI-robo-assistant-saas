# ZONATA Universal AI Company OS — Free-Tier Staging Deployment Runbook

**Target Architecture:** Render Free Web Service + Neon Serverless PostgreSQL 16 + Embedded In-Process Worker  
**Estimated Recurring Cost:** **$0.00 / month ($0.00 / year)**  
**Payment Information Required:** **None** (neither Render nor Neon requires a credit card to activate free tier)  
**Target Repository:** [`sukhrajsingh82673-gif/AI-robo-assistant-saas`](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas)  
**Target Branch:** `engineering/production-readiness-gap-closure`  

---

## 1. Architectural Overview & Design Rationale

To satisfy the mandate of **rapid, zero-cost public staging deployment** without compromising core security, tenant isolation, or data safety:

1. **Persistent Database (Neon Serverless PostgreSQL 16):**
   - Staging data cannot be stored on an ephemeral container disk (Render free instances discard local SQLite files on sleep/restart).
   - Neon provides genuine PostgreSQL 16 with 1.0 GB persistent NVMe storage for free (expanded from 0.5 GB in Oct 2026).
   - Unlike Render's free PostgreSQL (which is deleted after 30 days), Neon's free tier does not expire.
   - ZONATA's connection pool, SSL enforcement (`sslmode=require`), and schema migrations work out of the box.

2. **Public Edge Web Service (Render Free Web Service):**
   - Connects directly to the GitHub repository and builds from the root `Dockerfile`.
   - Terminates TLS 1.3 automatically and issues a Let's Encrypt wildcard certificate (`https://<service-name>.onrender.com`).
   - Handles public HTTP-to-HTTPS redirection.

3. **In-Process Embedded Worker (`ZONATA_EMBEDDED_WORKER=1`) & Crash Recovery:**
   - Runs `UniversalAutomationFabric` and `AsynchronousCommandBus` within the same container.
   - Eliminates the need for a separate $7/month paid background worker on Render.
   - **Durability across Sleep/Restarts:** Render free web services spin down after 15 minutes of inactivity. When restarted, `command_bus.recover_interrupted_jobs(timeout_seconds=0.0)` automatically detects actions left in `ASSIGNED` status from interrupted workers and restores them to `QUEUED`.
   - **Retry Governance:** If a failing task causes repeated container interruptions (>3 attempts), it is safely transitioned to `FAILED` with failure audit evidence to prevent infinite loops.
   - **Graceful Termination:** SIGTERM/SIGINT signals trigger graceful worker stop via threading events, allowing current tasks to complete cleanly.

4. **In-Process Event Bus & Durable Execution Architecture:**
   - **JetStream Engine (`core/nats_jetstream.py`):** Operates as an in-process thread-safe event bus with PostgreSQL audit ledger persistence, providing stream delivery without needing a standalone external NATS daemon.
   - **Temporal Gateway (`core/temporal_durable_execution_runtime.py`):** Implements durable workflow execution, state machines, and compensation sagas backed by relational tables (`automation_executions`, `saga_compensations`) in PostgreSQL, fitting comfortably within Render's 512 MB RAM footprint.
   - *Enterprise Note:* The full AWS Compose/Terraform package (`deploy/compose/`) provisions standalone external NATS and Temporal cluster containers when deployed on enterprise infrastructure.

5. **Edge Security & Metric Protection (`ZONATA_PROTECT_METRICS=1`):**
   - Enforces BLK-02 by returning `403 Forbidden` for unauthenticated requests to `/metrics`, blocking public metric scraping without an authorization token.

---

## 2. Platform Signup & Account Preparation

| Service | Purpose | Platform Signup URL | Free Tier Quota | Credit Card Required? |
| :--- | :--- | :--- | :--- | :---: |
| **Neon** | Serverless PostgreSQL 16 Persistence | [https://console.neon.tech/register](https://console.neon.tech/register) | 1.0 GB NVMe storage, serverless autoscaling, active branching | **NO** |
| **Render** | Container Web Ingress & Runtime | [https://dashboard.render.com/register](https://dashboard.render.com/register) | 512MB RAM, 0.1 vCPU, 750 free instance hrs/mo, 100 GB egress | **NO** |
| **GitHub** | Code Repository & CI/CD | [https://github.com/join](https://github.com/join) | Unlimited public repo CI/CD runners | **NO** |

---

## 3. Step-by-Step Staging Deployment

### Step 1: Provision Persistent Neon PostgreSQL 16 (Time: ~1 minute)
1. Sign in to [Neon Console](https://console.neon.tech/).
2. Click **Create Project**:
   - **Project Name:** `zonata-staging`
   - **Postgres Version:** `16`
   - **Region:** `US East (Ohio)` or `US East (N. Virginia)` (closest to Render's Oregon/Ohio regions).
3. Once created, navigate to **Dashboard** -> **Connection Details**.
4. Set the dropdown to **Pooled connection** and ensure **Connection string** is selected.
5. Copy your connection URL (format):
   ```
   postgresql://zonata_app:YOUR_PASSWORD@ep-sample-pooler.us-east-2.aws.neon.tech/zonata_staging?sslmode=require
   ```

### Step 2: Apply Database Schema Migrations (Time: ~30 seconds)
From your terminal or local environment, apply the additive schema migrations to your Neon database:
```bash
# Run the migration initializer pointing to your Neon connection URL
python3 deploy/free_tier/apply_neon_migrations.py \
  --database-url "postgresql://zonata_app:YOUR_PASSWORD@ep-sample-pooler.us-east-2.aws.neon.tech/zonata_staging?sslmode=require"
```
The script will establish SSL connectivity, initialize the baseline schema, execute all controlled migrations, and verify that operational tables (`tenants`, `users`, `missions`, `async_command_queue`, `evidence_ledger`) are active.

### Step 3: Deploy to Render via Blueprint or Web Service (Time: ~3 minutes)

#### Option A: Using Render Blueprint (`render.yaml` — Recommended)
1. Sign in to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your repository: `sukhrajsingh82673-gif/AI-robo-assistant-saas`.
4. Select branch: `engineering/production-readiness-gap-closure`.
5. Render detects `render.yaml`. When prompted for `DATABASE_URL`, paste your Neon connection string.
6. Click **Apply**. Render will automatically build the container and deploy the web service.

#### Option B: Manual Web Service Setup
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Select **Build and deploy from a Git repository**.
3. Choose repository `sukhrajsingh82673-gif/AI-robo-assistant-saas`, branch `engineering/production-readiness-gap-closure`.
4. Configure service parameters:
   - **Name:** `zonata-staging`
   - **Language:** `Docker`
   - **Dockerfile Path:** `./Dockerfile`
   - **Instance Type:** `Free`
5. Add Environment Variables:
   - `APP_ENV`: `staging`
   - `ENVIRONMENT`: `staging`
   - `ZONATA_STRICT_AUTH`: `1`
   - `ZONATA_DISABLE_DEMO_SEED`: `1`
   - `ZONATA_CLEAN_STARTUP`: `1`
   - `ZONATA_ALLOW_HOST_SHELL`: `0`
   - `ZONATA_EMBEDDED_WORKER`: `1`
   - `ZONATA_PROTECT_METRICS`: `1`
   - `DATABASE_URL`: `postgresql://zonata_app:YOUR_PASSWORD@ep-sample-pooler.us-east-2.aws.neon.tech/zonata_staging?sslmode=require`
   - `JWT_SECRET`: Generate a random 64-char string (e.g. `openssl rand -hex 32`)
   - `SESSION_SECRET`: Generate a random 64-char string
   - `METRICS_AUTH_TOKEN`: Generate a random token for scraper authorization
6. Click **Create Web Service**.

---

## 4. Post-Deployment Verification & Smoke Testing

Once Render shows **Deploy live**, copy your staging URL (e.g. `https://zonata-staging.onrender.com`).

Run the automated smoke test suite:
```bash
./deploy/free_tier/smoke_test_render.sh "https://zonata-staging.onrender.com" "YOUR_METRICS_AUTH_TOKEN"
```

Expected output:
```
==============================================================================
ZONATA Free-Tier Staging Smoke Test
Target Endpoint: https://zonata-staging.onrender.com
==============================================================================
Gate: 1. GET /health returns 200 OK ... PASS
Gate: 2. GET /readyz confirms PostgreSQL database readiness ... PASS
Gate: 3. Unauthenticated GET /metrics is blocked (403 Forbidden) ... PASS
Gate: 4. Authenticated GET /metrics returns Prometheus format ... PASS
Gate: 5. Unauthenticated request to /api/v1/overview returns 401 ... PASS
Gate: 6. GET /api/auth/csrf returns valid token ... PASS
Gate: 7. Scheme is HTTPS ... PASS
==============================================================================
Smoke Test Summary: 7 PASSED, 0 FAILED
==============================================================================
ALL FREE-TIER STAGING GATES PASSED (100%)
```

---

## 5. Limitations, Quotas & Cost Safeguards

| Feature / Behavior | Free-Tier Reality | Mitigation / Guidance |
| :--- | :--- | :--- |
| **Idle Sleep & Worker Restarts** | Render spins down free web services after 15 minutes of inactivity. | The first request after sleep takes ~50 seconds to wake. Persistent data is unharmed because it resides in Neon PostgreSQL. Any in-flight commands left in `ASSIGNED` state are automatically reclaimed back to `QUEUED` upon worker wake-up (`recover_interrupted_jobs`). |
| **Storage Persistence** | Render local disk is ephemeral; files written to `/app/storage` are wiped on sleep. | Critical business data is stored exclusively in Neon PostgreSQL. Encrypted backup envelopes can be sent to Cloudflare R2 (10 GB free). |
| **Compute Quota** | 750 free instance hours per month on Render. | Sufficient for 1 continuous web service for the entire 31-day month (744 hours max). |
| **Bandwidth Quota** | 100 GB outbound egress per month on Render. | Ample for staging and demonstration traffic. |
| **Database Quota** | 1.0 GB NVMe storage on Neon. | Ample for tens of thousands of tenants, users, and audit records (expanded from 0.5 GB in Oct 2026). |
| **Cost Safeguard** | Render and Neon will pause services rather than billing if quotas are exceeded. | **Guaranteed $0.00 bill.** No surprise cloud charges. |
