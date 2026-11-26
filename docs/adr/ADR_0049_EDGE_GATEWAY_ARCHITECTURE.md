# ADR 0049: Edge Gateway Architecture (Rule 77 & Rule 80)

## Status
Accepted

## Context
As the ZONATA platform transitions to product readiness, direct exposure of internal micro-services or monolithic ASGI applications to public ingress introduces security risks: lack of centralized rate limiting, inconsistent TLS/header enforcement, uncoordinated CORS management, and fragmented route entitlement enforcement. Furthermore, preservation contracts (Rule 77) forbid altering existing Step 1–8 service endpoints.

## Decision
1. **Edge Gateway Reverse Proxy Layer (`core/edge/`):**
   - Sit in front of core API and internal service namespaces.
   - Enforce uniform perimeter security: TLS termination headers, CORS validation, security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).
   - Implement rate limiting (sliding window / token bucket per client IP and authenticated tenant API key).
   - Propagate standardized distributed tracing headers (`traceparent`, `X-Request-ID`).
2. **Route Entitlement & Route Matching:**
   - Intercept requests to public APIs (`/api/public/v1/*`), console APIs (`/api/console/*`), and health probes (`/healthz`, `/readyz`).
   - Validate tenant subscription status and feature entitlements via `EntitlementsEngine` before proxying requests to upstream handlers.
   - Return standard RFC 9457 Problem Details (`application/problem+json`) on rate limits, unauthorized routes, or plan downgrades.
3. **Preservation Guarantee:**
   - Existing Step 1–8 internal routes are preserved verbatim; the Edge Gateway proxies or dispatches to them cleanly without mutating underlying route definitions.

## Consequences
- **Positive:** Centralized ingress policy, DDoS mitigation, clean contract enforcement, and strict preservation compliance.
- **Negative:** Adds minimal routing latency (< 2ms) to request path.
