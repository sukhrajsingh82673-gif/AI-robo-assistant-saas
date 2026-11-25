# ADR 0056: Privacy-Preserving Product Analytics (Rule 78 & Rule 84)

## Status
Accepted

## Context
To continuously improve product onboarding, reduce UI friction, and understand feature utilization, the product team requires product usage analytics. However, enterprise SaaS tenants handle strictly confidential business data, PII, and financial records. Traditional third-party analytics trackers frequently leak sensitive DOM content, URL query parameters, and form inputs.

## Decision
1. **Zero-Tenant-Content Guarantee:**
   - Product analytics tracking is strictly decoupled from tenant business data.
   - Event payloads record only synthetic event IDs (e.g., `button_click: export_data`, `filter_applied: date_range`), page route templates (`/admin/billing`, not containing tenant UUIDs or customer names), and pseudonymous session identifiers.
   - Keystroke logging, input field values, prompt texts, and response payloads are strictly excluded at the client SDK level.
2. **Self-Hosted / Private Aggregation:**
   - Ingest events into a self-hosted privacy-focused analytics sink (e.g. self-hosted PostHog or ClickHouse buffer).
   - No tracking beacons or third-party cookies sent to advertising networks or external data brokers.
3. **Tenant Consent & Opt-Out:**
   - Tenant administrators can disable product telemetry entirely via a single toggle in the Tenant Admin Console.

## Consequences
- **Positive:** Complete respect for enterprise confidentiality; zero GDPR/CCPA telemetry violation risks; clean data pipeline.
- **Negative:** Cannot perform ad-hoc debugging of user-specific input errors via session replays.
