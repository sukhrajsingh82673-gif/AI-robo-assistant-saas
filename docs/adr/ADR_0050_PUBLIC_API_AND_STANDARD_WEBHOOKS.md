# ADR 0050: Public API and Standard Webhooks (Rule 80)

## Status
Accepted

## Context
External integrations, enterprise customers, and marketplace developers require a stable, versioned public API and reliable event delivery. Ad-hoc API designs and non-standard webhook signatures lead to integration friction, security vulnerabilities (such as SSRF or replay attacks), and breaking changes.

## Decision
1. **Public API Standards (`/api/public/v1`):**
   - Standardize on OpenAPI 3.1 specification (`docs/api/openapi_v9_public.json`).
   - Use RFC 9457 Problem Details for HTTP APIs (`application/problem+json`) for all error payloads (400, 401, 403, 404, 409, 429, 500).
   - Enforce `Idempotency-Key` header on all state-mutating requests (`POST`, `PUT`, `DELETE`) with a 24-hour deduplication cache.
   - Standardize on cursor-based pagination (`?limit=N&cursor=opaque_token`) for all collection endpoints.
2. **Standard Webhooks Delivery:**
   - Adopt the Standard Webhooks specification for outbound event delivery.
   - Sign payloads using HMAC SHA-256 (`webhook-signature` header: `t=timestamp,v1=signature`).
   - Implement replay attack prevention (rejection of deliveries older than 300 seconds).
   - Implement strict Server-Side Request Forgery (SSRF) protections: prohibit loopback (`127.0.0.0/8`, `::1`), private networks (RFC 1918 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and link-local addresses (`169.254.0.0/16`).
   - Provide webhook secret rotation with dual-signature overlap periods.

## Consequences
- **Positive:** Industry-standard developer experience, cryptographic event authenticity, robust protection against replay and SSRF attacks.
- **Negative:** Requires webhook receivers to implement HMAC verification logic.
