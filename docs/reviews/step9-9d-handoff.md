# OpenCode Handoff: Sub-Step 9D

## 1. Summary of Changes
- Created `openapi_v9_public.json` defining canonical OpenAPI 3.1.0 specifications for the public API.
- Created `core/webhooks/standard_webhooks.py` implementing Standard Webhooks HMAC-SHA256 signing, timestamp validation (300s replay tolerance), dual-secret rotation, and SSRF address verification.
- Created `core/api/public_v1.py` providing `/api/public/v1/*` endpoints with RFC 9457 errors, `Idempotency-Key` deduplication, and cursor pagination.
- Created `core/api/portal.py` providing developer documentation and multi-language snippets.
- Created typed SDK packages: `sdk/python/` and `sdk/typescript/`.
- Created `tests/test_step9d_public_api.py`.

## 2. Verification Commands
```bash
pytest -v tests/test_step9d_public_api.py
```

## 3. Claims and Invariants
- Rule 80: Public API conforms to OpenAPI 3.1.0 with RFC 9457 Problem Details (`application/problem+json`).
- Outbound webhooks follow Standard Webhooks spec and prevent replay and SSRF against private/loopback/cloud metadata networks.
- Mutating operations honor `Idempotency-Key` headers.
