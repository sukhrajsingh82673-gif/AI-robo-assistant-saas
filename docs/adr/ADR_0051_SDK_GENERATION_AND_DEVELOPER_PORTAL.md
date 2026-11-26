# ADR 0051: SDK Generation and Developer Portal (Rule 80)

## Status
Accepted

## Context
Developers integrating with the ZONATA platform need reliable, typed client libraries in modern programming languages (TypeScript and Python) along with interactive documentation to explore and test API operations without writing manual HTTP client wrappers.

## Decision
1. **Automated SDK Generation:**
   - Synthesize strongly-typed SDKs for TypeScript (`sdk/typescript/`) and Python (`sdk/python/`) from the canonical `docs/api/openapi_v9_public.json` OpenAPI 3.1 spec.
   - Embed cryptographic provenance and source git commit hash in SDK metadata.
   - Provide high-level ergonomics: automatic idempotency key generation, automatic exponential backoff retry for transient 429/503 errors, and automatic Standard Webhooks verification utilities.
2. **Developer Portal:**
   - Serve an interactive Developer Portal at `/docs/portal` or via static generation.
   - Provide an interactive "Try it out" sandbox console running against deterministic synthetic test fixtures without requiring real credentials.
   - Include copy-paste code snippets in cURL, TypeScript, and Python for all endpoints.

## Consequences
- **Positive:** Accelerates customer integration time; guarantees client SDKs remain 100% synchronized with OpenAPI contracts.
- **Negative:** SDK generator pipelines must be maintained in CI.
