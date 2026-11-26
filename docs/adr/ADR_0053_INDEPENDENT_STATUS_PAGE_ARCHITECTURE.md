# ADR 0053: Independent Status Page Architecture (Rule 83)

## Status
Accepted

## Context
Rule 83 dictates that the status page must be architecturally decoupled from the primary application infrastructure. If the core database, Kubernetes cluster, or application hosting region experiences an outage, a co-hosted status page would fail alongside the service, leaving users uninformed and breaching trust.

## Decision
1. **Out-of-Band Hosting & Execution:**
   - Host the public status page on independent infrastructure (e.g. Cloudflare Pages or distinct secondary cloud provider), separate from the application core.
   - Utilize a lightweight status probe engine (conforming to Gatus / Uptime Kuma standards).
2. **Synthetic Health Probing:**
   - Public health probes query unauthenticated, lightweight `/healthz` and `/readyz` endpoints exposed through the Edge Gateway.
   - Internal probes verify core dependencies (PostgreSQL connectivity, Temporal worker heartbeats, edge response latencies).
3. **Incident Management Workflow:**
   - Incidents can be published manually by authorized operators or triggered automatically by sustained synthetic probe degradation.
   - Status updates are cryptographically signed and archived.

## Consequences
- **Positive:** Status page remains 100% operational during catastrophic core outages, strictly fulfilling Rule 83.
- **Negative:** Requires managing separate deployment credentials and out-of-band domain routing (`status.zonata.ai`).
