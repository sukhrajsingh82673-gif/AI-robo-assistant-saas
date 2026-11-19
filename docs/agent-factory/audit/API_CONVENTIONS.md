# API_CONVENTIONS — ZONATA Agent Factory Phase 1 Audit

## 1. Versioning & Route Prefixes
- **Prefixes Found in Codebase:**
  - `/api/v8/`: **269 occurrences** — **Highest in active use**. Governs enterprise core endpoints, workforce, company setup, and AI CEO.
  - `/api/v1/`: 222 occurrences — Foundational legacy routes.
  - `/api/v2/`: 46 occurrences — Settings V2 and assistant streaming.
- **Factory API Namespace:**
  - The Agent Factory API endpoints will be mounted under `/api/v8/agent-factory/` to match the highest active API version.

---

## 2. Authentication & Authorization Dependency
- **Authentication:**
  - Token Header: `Authorization: Bearer <token>`
  - Resolves to: `Principal(principal_id, tenant_id, company_id, roles)` via `core/auth.py` and `core/identity_gateway.py`.
- **Tenant Context Extraction:**
  - Derived strictly from the verified bearer token. The client query param `tenant_id` is never trusted alone.
  - `X-Company-ID` header must match an active membership in the authenticated tenant; otherwise returns `404 Not Found` (never `403` to prevent tenant cross-probing).

---

## 3. Error Response Shape (RFC 9457 & ZONATA Standards)
- **Standard Error Payload:**
```json
{
  "error": "Human-readable description of error",
  "code": "AF-INVALID-SPEC",
  "status": 400,
  "request_id": "req_a1b2c3d4e5",
  "details": {
    "field": "instructions",
    "reason": "Exceeds maximum allowable size (20KB)"
  }
}
```
- **HTTP Status Code Mapping:**
  - `400 Bad Request`: Schema validation failure (`AF-VALIDATION-ERROR`).
  - `401 Unauthorized`: Missing or invalid bearer token (`AF-UNAUTHORIZED`).
  - `403 Forbidden`: PolicyEngine / AuthorityGateway denial (`AF-FORBIDDEN`).
  - `404 Not Found`: Entity not found, or cross-tenant access attempt (`AF-NOT-FOUND`).
  - `409 Conflict`: Idempotency payload mismatch or version conflict (`AF-IDEMPOTENCY-MISMATCH`).
  - `422 Unprocessable Entity`: Semantic spec violation (`AF-INVALID-SPEC`).
  - `429 Too Many Requests`: Rate limit or quota exceeded (`AF-QUOTA-EXCEEDED`).
  - `503 Service Unavailable`: Feature disabled / Sandbox tier unavailable (`AF-SANDBOX-UNAVAILABLE`).

---

## 4. Router Registration Pattern
- **Host Server:** Native `http.server.BaseHTTPRequestHandler` in [`api_server.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/api_server.py) (`RoboAssistantServer`).
- **Handler Delegation:**
  - Request dispatchers inspect `self.path` and route to specialized modular handlers (e.g. `core.v8_api_handler.handle_v8_request`).
  - Agent Factory routes will be modularized in `<backend>/agent_factory/api/routes.py` and mounted cleanly into the central request dispatcher.

---

## 5. Idempotency & Replay Protection
- **Header:** `Idempotency-Key: <unique-string>`
- **Behavior:**
  - Keys are recorded with request payload hash in `coordination.set_idempotency_key` or `af_request(tenant_id, idempotency_key)`.
  - Replay with identical payload returns the cached result.
  - Replay with different payload returns `409 AF-IDEMPOTENCY-MISMATCH`.

---

## 6. Rate Limiting & Quotas
- **Headers Returned:**
  - `X-RateLimit-Limit`: Maximum requests per window.
  - `X-RateLimit-Remaining`: Remaining budget.
  - `X-RateLimit-Reset`: Unix timestamp of window reset.
- **Enforcement:** Enforced at kernel level via `core/distributed_coordination.py` sliding window counters.

---

## 7. Audit & Observability Headers
Every request returns:
- `X-Request-ID`: Correlation identifier (`req_<uuid>`).
- `X-Evidence-ID`: Merkle ledger receipt ID when the call produces a sealed audit state transition.
