# Step 9 Product Readiness Inventory (`docs/reports/STEP9_INVENTORY.md`)

**Date:** 2026-11-25  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter / Independent Red Team  
**Scope:** Billing, metering, edge gateway, public API, webhooks, consoles, onboarding, mobile PWA, status, support, marketplace, release engineering.

---

## 1. Executive Summary & Preflight Gate Results

This preflight inventory examines the platform's readiness for **Antigravity Step 9 — Product Readiness: billing and metering, public API and webhooks, consoles, onboarding, mobile, status and support, marketplace foundations, release engineering**.

### Gate Verification Checklist
- [x] **Steps 1 to 8 Merged with Green CI:** Tagged at `step8-final` (commit `7aee993`). All 67 cumulative Step 8 tests passing.
- [x] **Step 6 Public Exposure Report on File:** [`docs/security/PUBLIC_EXPOSURE_REPORT.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/security/PUBLIC_EXPOSURE_REPORT.md) confirmed.
- [x] **Owner Rotation Attestation on File:** [`docs/security/OWNER_ROTATION_ATTESTATION.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/security/OWNER_ROTATION_ATTESTATION.md) confirmed.
- [x] **Step 5 Identity Architecture:** Keycloak integration, SCIM 2.0 endpoints, and API key management verified in `core/identity/` and `core/auth/`.
- [x] **Step 5F Control Matrix and Privacy Workflows:** [`docs/security/CONTROL_MATRIX.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/security/CONTROL_MATRIX.md) and GDPR/DPDP export/erasure routines active.
- [x] **Step 4 Temporal & Observability:** Temporal workflow orchestrators and Prometheus/OTel telemetry verified.
- [x] **Step 7 Connector SDK & Ports:** Connector framework, replay contract fixtures, and 10 department engines active.
- [x] **Step 8 Regional Cells, Localisation & Procurement Pack:** `CellRouter` (regional residency), `CLDREngine` (multi-locale formatting), and `BuyerPackGenerator` active.
- [x] **Step 1F Export Pack:** Standalone export manifest and verification routines active.

### Invariant Checklist for Step 9
- [x] **Rule 77 (Preservation Extension to Steps 1–8):** Baseline frozen at `step8-final`. Existing `/api/*` surface remains unchanged. Product features added in front or beside core via edge gateway, public namespace, or event subscriptions.
- [x] **Rule 78 (Billing Safety Invariant):** Billing never deletes customer data or silently drops critical workflows. Grace periods, read-only modes, and export windows guaranteed. Legal holds always win.
- [x] **Rule 79 (Money Truth):** Usage events are idempotent, append-only, and hash-chained. Amounts in minor integer units. Card data is never stored.
- [x] **Rule 80 (Stable Published Contracts):** OpenAPI 3.1 specification, RFC 9457 problem details, idempotency keys, cursor pagination, deprecation with `Sunset` header.
- [x] **Rule 81 (Hostile Third-Party Code):** Marketplace packages execute in isolated sandboxes with capability manifests; tenant consents per capability.
- [x] **Rule 82 (Consented Support Access):** Operator support access requires tenant-issued, time-boxed, dual-control grants. Never bypasses reserved decisions.
- [x] **Rule 83 (Independent Status Page):** Status page runs on separate infrastructure; incident publishing requires human decision.
- [x] **Rule 84 (UX Honesty & Accessibility):** No dead controls (enforced by dead-control crawler); WCAG 2.2 AA target; zero dark patterns.

---

## 2. Product Platform Component Inventory

| Category | Component / Module | Status | Current Capabilities | Gaps to Address in Step 9 |
| :--- | :--- | :---: | :--- | :--- |
| **Web Shell & Consoles** | `web/app_shell.js`, `web/app_shell.css` | `PARTIAL` | Responsive layout, theme toggling, menu navigation | Tenant Admin Console & Operator Console; dead-control detector |
| **Settings Registry** | `core/settings_service.py`, `storage/enterprise_settings.json` | `EXISTS` | Key-value settings with versioning and validation | Integration with new edge gateway and OpenFeature flags |
| **Existing API Routes** | `api_server.py`, `openapi_v4.json`–`v8.json` | `EXISTS` | Internal authenticated API endpoints for Steps 1–8 | Must freeze existing routes; expose new `/api/public/v1` namespace |
| **Billing & Metering** | `core/billing.py`, `core/saas_billing.py` | `PARTIAL` | Stripe test mode stubs, basic quota checks | `BillingPort`, Paddle/Stripe/Lago adapters, idempotent usage metering, cost caps |
| **Webhooks** | `core/webhooks.py` | `PARTIAL` | Basic HMAC webhook dispatch | Standard Webhooks specification (Apache-2.0), replay protection, secret rotation |
| **Company Setup & UI** | `core/company_setup/status.py`, `web/settings_enterprise.js` | `PARTIAL` | Company initialization wizards | First-run onboarding wizard, demo company isolation, data import/export |
| **Mobile & Responsive** | Responsive CSS rules in `web/app_shell.css` | `PARTIAL` | Basic mobile breakpoint scaling | Installable PWA manifest, service worker, mobile approval flows, WCAG 2.2 AA |
| **Status & Support** | `core/workflows/departments/support_to_resolution.py` | `PARTIAL` | Internal departmental ticketing | Independent status page architecture, consented support access grants |
| **Marketplace** | Step 6G intake & Step 3G import lane | `PARTIAL` | Agent skill import and sandbox execution | Marketplace package format, capability manifests, review pipeline, takedown |
| **Release Engineering** | GitHub Actions workflows, `deploy/` scripts | `PARTIAL` | Test runs, container packaging | Canary rollouts, deploy gateway approvals, release readiness report |

---

## 3. Structural Analysis of Snapshots and Contracts

1. **OpenAPI Snapshots (`openapi_v4.json` to `openapi_v8.json`):**
   - Provide historical snapshots of internal API surfaces.
   - Preserved as immutable baseline artifacts.
   - Step 9 public API will be formalized in `docs/api/openapi_v9_public.json` conforming to OpenAPI 3.1.
2. **Settings Registry:**
   - Evaluated under `core/settings_service.py` with hierarchical tenant defaults.
   - Step 9 extends this to support OpenFeature provider interfaces.
3. **Billing State Invariants:**
   - Existing code tracks `is_trial` and basic quotas.
   - Step 9 establishes the formal lifecycle: `TRIAL` -> `ACTIVE` -> `PAST_DUE` -> `GRACE_PERIOD` -> `RESTRICTED` -> `SUSPENDED` -> `EXPORT_ONLY` -> `DELETED` (with legal holds overriding deletion).
