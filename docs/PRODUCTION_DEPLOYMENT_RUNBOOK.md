# URA / ZONATA — Production Deployment & Rollback Runbook
## Staging Verification, Release Packaging & Paid Infrastructure Migration Procedures

**Document ID:** ZONATA-DEPLOY-RUNBOOK-2026  
**Candidate Release Commit:** [`40810d0f77bfeb166164d1f2bce434c4f346b0a7`](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/commit/40810d0f77bfeb166164d1f2bce434c4f346b0a7)  
**Parent Release Anchor:** [`87c3dd97d15c222567b4f627be8de24c7d39232f`](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/commit/87c3dd97d15c222567b4f627be8de24c7d39232f)  
**Target Environments:** Staging (`https://zonata-staging.onrender.com`) | Production (Pending Owner Authorization)  
**Evaluation Date:** October 22, 2026  
**Auditor:** Antigravity Autonomous Release Manager  

---

## 1. Release Architecture & Environment Profiles

| Component | Free-Tier Staging Profile | Paid Production Target Profile | Migration Prerequisite |
| :--- | :--- | :--- | :--- |
| **Web Compute** | Render Free (0.1 vCPU, 512MB RAM, 15m spindown) | Render Standard (1–2 dedicated vCPU, 2–4 GB RAM, zero spindown) | Owner authorization ($7–$25/mo) |
| **Database** | Neon Free (0.25 CU scale-to-zero, shared pooler) | Neon Launch/Scale (2+ CU autoscaling, HA replica, dedicated pooler) | Owner authorization ($19+/mo) |
| **Edge & CDN** | Cloudflare Edge (Standard TLS, dynamic cache) | Cloudflare Pro/Enterprise (WAF rules, DDoS mitigation, custom certs) | Optional upgrade |
| **Blob Storage**| Local cryptographic mirror buffer | AWS S3 Bucket with Object Lock (Compliance Mode) | AWS account credentials |
| **Billing Webhooks**| Synthetic test-mode signatures | Live Stripe / Razorpay merchant account signing secrets | Live merchant activation |

---

## 2. Staging Deployment & Provenance Verification Workflow

Deployments to Render are triggered automatically upon pushing to the synchronized `main` branch:

### Step 1: Git Release Branch Verification & Push

```bash
cd /root/roboassistant

# 1. Verify clean working tree and commit SHA
git status
git rev-parse HEAD
# Expected Candidate SHA: 40810d0f77bfeb166164d1f2bce434c4f346b0a7

# 2. Push to origin main and engineering branch
git push origin engineering/production-readiness-gap-closure
git push origin engineering/production-readiness-gap-closure:main
```

### Step 2: Render Container Build & Rollout Monitoring
- Render automatically detects the new commit on `main`.
- Container builds execute via `Dockerfile` with multi-stage python dependency compilation.
- Container rollout performs blue-green container swap upon passing internal Docker `HEALTHCHECK`.

### Step 3: Live Provenance Probe & Readiness Verification

Execute HTTP probe against live staging:

```bash
curl -s -i "https://zonata-staging.onrender.com/readyz"
```

**Acceptance Criteria for Successful Deployment:**
1. HTTP Response status is `200 OK`.
2. `"status"` field is `"HEALTHY"`.
3. `"commit"` matches the expected deployment candidate SHA (`40810d0` or parent anchor `87c3dd9`).
4. `"database"` reports `"CONNECTED"`.
5. `"merkle_ledger"` reports `"INTEGRITY_VERIFIED"`.
6. `"cryptography_version"` reports `"50.0.2"`.

---

## 3. Rollback Runbook (Zero-Downtime Reversion)

If a production defect is detected post-deployment, follow the immediate rollback sequence:

### Procedure A: Render Dashboard Immediate Rollback
1. Log into Render Console: `https://dashboard.render.com`
2. Select web service: `zonata-staging`
3. Navigate to **Events** tab.
4. Locate the last verified healthy build (Commit `87c3dd9` or `c3032f1`).
5. Click **Rollback to this build**.
6. Rollback activates in < 30 seconds.

### Procedure B: Git Emergency Revert & Fast-Forward Push

```bash
cd /root/roboassistant

# 1. Revert to previous verified release anchor
git checkout -b rollback-emergency
git revert HEAD --no-edit

# 2. Push revert to main
git push origin rollback-emergency:main

# 3. Verify rollout on Render /readyz
curl -s "https://zonata-staging.onrender.com/readyz" | jq .
```

---

## 4. Paid Production Infrastructure Migration Runbook

> [!CAUTION]
> **Owner Authorization Barrier:**
> DO NOT execute the commands in this section until the Project Owner explicitly authorizes paid compute and resource provisioning.

Once explicit authorization is provided:

### Phase 1: Provision Render Standard Web Instance
1. In Render Dashboard, open service settings for `zonata-production`.
2. Change instance type from **Free** to **Standard** (2 vCPU, 4GB RAM).
3. Confirm persistent always-on setting (disable idle spin-down).
4. Inject production environment variables (`RENDER_GIT_COMMIT`, `IS_PRODUCTION=true`).

### Phase 2: Provision Neon Autoscaling Database
1. In Neon Console, upgrade project `ep-broad-sky-b4jnm313` to **Launch / Scale**.
2. Set compute autoscaling range: minimum 1.0 CU, maximum 4.0 CU.
3. Configure dedicated connection pooler with max pool size = 50.
4. Enable automated daily PITR backup snapshots.

### Phase 3: Configure Live Commercial Payment Webhooks
1. In Stripe Dashboard, navigate to Developers -> Webhooks.
2. Add endpoint: `https://zonata-app.com/api/v1/billing/stripe/webhook`
3. Select events: `customer.subscription.*`, `invoice.*`, `checkout.session.completed`.
4. Copy signing secret and configure in Render: `STRIPE_WEBHOOK_SECRET=whsec_...`
5. Repeat for Razorpay if dual-gateway routing is active.

### Phase 4: Production-Scale Validation
1. Execute capacity benchmark with concurrency C=50 and C=100.
2. Confirm p50 latency < 120ms and throughput > 250 requests/second.
3. Execute end-to-end customer subscription checkout and verify webhook signature verification.
4. Transition release verdict to **GO — PUBLIC GA**.
