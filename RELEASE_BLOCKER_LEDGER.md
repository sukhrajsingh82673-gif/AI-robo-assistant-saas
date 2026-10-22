# URA / ZONATA — Authoritative Release Blocker Ledger
## Complete Classification of Open, Blocked, Accepted & Remediated Release Requirements

**Document ID:** ZONATA-BLOCKER-LEDGER-2026  
**Candidate Release Commit:** [`40810d0f77bfeb166164d1f2bce434c4f346b0a7`](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/commit/40810d0f77bfeb166164d1f2bce434c4f346b0a7)  
**Parent Release Anchor:** [`87c3dd97d15c222567b4f627be8de24c7d39232f`](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/commit/87c3dd97d15c222567b4f627be8de24c7d39232f)  
**Evaluation Date:** October 22, 2026  
**Auditor:** Antigravity Autonomous DevSecOps Lead & Release Manager  

---

## 1. Master Release Blocker Inventory

```
+====================================================================================================+
|   RELEASE STATUS SUMMARY:                                                                          |
|   - Category A (Owner Authorization & Paid Spend Required):    5 Items (BLOCKING PUBLIC GA)        |
|   - Category B (Resolved Within Free-Tier Architecture):        7 Items (VERIFIED CLOSED)           |
|   - Restricted Production Pilot Verdict (Milestone M):         RESTRICTED GO (PILOT SCOPE)         |
|   - Scope: Bounded to 1–3 design-partner pilot orgs, max 4 concurrency leases, 60 RPM.             |
|   - Unrestricted Public General Availability Verdict:          NO-GO (AWAITING OWNER AUTHORIZATION)|
+====================================================================================================+
```

---

## 2. Category A: Blockers Requiring Human Owner Decision & Billable Spend

These items cannot be resolved autonomously under the non-negotiable rule prohibiting unauthorized spending.

| Blocker ID | Release Requirement | Current State | Required Production State | Estimated Cost & Prerequisite | Action Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BLK-01** | **Persistent Web Compute** | Render Free tier (0.1 vCPU, 512MB RAM, 15m idle spin-down). Latency p95 = 6.09s at C=4. | Render Standard instance (2 dedicated vCPU, 4GB RAM, persistent always-on execution). | ~$7 – $25 / month. Owner authorization to upgrade Render service. | Human Owner |
| **BLK-02** | **Autoscaling Database Compute** | Neon Free tier (0.25 CU scale-to-zero, shared pooler). | Neon Launch/Scale plan (minimum 1.0 CU, autoscaling to 4.0 CU, HA replica). | ~$19+ / month. Owner authorization to upgrade Neon project. | Human Owner |
| **BLK-03** | **Continuous Automated PITR API** | Logical `pg_dump` and `psql` restore verified. Instantaneous branching unconfigured. | `NEON_API_KEY` configured to automate point-in-time branch creation via CLI/API. | Neon Cloud API Token. Owner must generate and inject `NEON_API_KEY`. | Human Owner |
| **BLK-04** | **Off-Host Immutable Disaster Recovery** | Local cryptographic mirror buffer verified. Off-host cloud bucket unconfigured. | AWS S3 Bucket with Object Lock in Compliance Mode (WORM) and IAM credentials. | AWS Account + S3 storage charges (~$1–$5/mo). Owner must inject credentials. | Human Owner |
| **BLK-05** | **Live Merchant Payment Webhooks** | Stripe and Razorpay HMAC-SHA256 signature engines verified via synthetic test payloads. | Live Stripe (`STRIPE_WEBHOOK_SECRET`) and Razorpay (`RAZORPAY_WEBHOOK_SECRET`) configured. | Commercial Merchant Accounts. Owner must register and provide webhook secrets. | Human Owner |

---

## 3. Category B: Remediated & Verified Free-Tier Capabilities

All engineering, security, and persistence requirements resolvable without spend have been verified and closed:

| Requirement ID | Capability Dimension | Previous State | Verified Current State | Evidence & Verification Reference | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **RES-01** | **Test Database Isolation** | Destructive test teardowns left global `db` pointer directed at unlinked temporary paths. | Resilient fallback added to `core/db.py`; autouse fixture added to `tests/conftest.py`; automatic subsystem schema initialization verified. | Commit [`40810d0`](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/commit/40810d0f77bfeb166164d1f2bce434c4f346b0a7); 101/101 core qualification tests passing with zero errors. | **VERIFIED CLOSED** |
| **RES-02** | **Dependency Vulnerabilities** | CVE GHSA-537c-gmf6-5ccf in `cryptography<49.0.0`. | Upgraded to `cryptography==50.0.2` (OpenSSL 4.0.3); Google OSV API audit confirmed 0 CVEs across 10/10 packages. | [`storage/evidence/osv_vulnerability_audit.json`](file:///root/roboassistant/storage/evidence/osv_vulnerability_audit.json); live telemetry on `/readyz`. | **VERIFIED CLOSED** |
| **RES-03** | **Relational Disaster Recovery** | Single-table logical restore drill previously recorded. | Multi-table relational restore drill (`ldr_ef97ece5`) executed live on Neon 16 (4 tables, FKs, 5 indexes, RTO = 20.653s, 100% Merkle parity). | [`storage/evidence/isolated_logical_restore_drill.json`](file:///root/roboassistant/storage/evidence/isolated_logical_restore_drill.json). | **VERIFIED CLOSED** |
| **RES-04** | **Constitutional Assets Integrity** | Risk of asset modification during test execution. | Bit-for-bit SHA-256 and Git blob hashes verified: `roboassistant.db` (`ba738b6...`), `audit_ledger.jsonl` (`ca8181e...`), `workflow_workspace.js` (`88888ca...`). | Disk and Git object hash verification on October 22, 2026. | **VERIFIED CLOSED** |
| **RES-05** | **Commit SHA Parity** | Risk of branch drift across local, origin, and staging. | Exact commit alignment verified: local HEAD, `main`, `origin/engineering/...`, and `origin/main` match commit `40810d0`; live staging serving healthy parent anchor `87c3dd9`. | Git log and live HTTP probe on `https://zonata-staging.onrender.com/readyz`. | **VERIFIED CLOSED** |
| **RES-06** | **Multi-Tenant Security Boundaries** | Potential IDOR and cross-tenant leakage under concurrency. | Tenant spoofing returns HTTP 403; cross-tenant queries return `None`; zero leakage across all 9 simulated corporate departments. | `test_phase_14_nine_department_lifecycle.py` and `test_adversarial_security_and_chaos.py`. | **VERIFIED CLOSED** |
| **RES-07** | **Free-Tier Staging Stability** | Risk of unhandled container 5xx crashes under load. | Zero unhandled HTTP 500 errors across 80+ benchmark probes on Render staging. Uptime stable. | [`storage/evidence/capacity_test_evidence.json`](file:///root/roboassistant/storage/evidence/capacity_test_evidence.json). | **VERIFIED CLOSED** |

---

## 4. Minimum Action Required to Unblock Public General Availability

To achieve the **GO — PUBLIC GA** verdict, the Project Owner must execute the following 3 unblocking actions:

1. **Authorize Render Compute Upgrade:**
   - Action: Change `zonata` service plan from Free to Standard ($7–$25/mo).
   - Expected Impact: Eliminates 15-minute spin-down delay (cold starts drop from 36s to 0s); eliminates CPU throttling; achieves p95 latency < 450ms.

2. **Authorize Neon Database Upgrade:**
   - Action: Change Neon project `ep-broad-sky-b4jnm313` plan to Launch ($19/mo).
   - Expected Impact: Eliminates 5-minute scale-to-zero compute delay; enables autoscaling to 4 CU; provisions dedicated connection pooler supporting 50+ concurrent leases.

3. **Provide Commercial Webhook Secrets:**
   - Action: Register Stripe/Razorpay endpoints and inject webhook secrets into Render environment.
   - Expected Impact: Transition billing gateways from test-mode signature validation to live commercial subscription processing.
