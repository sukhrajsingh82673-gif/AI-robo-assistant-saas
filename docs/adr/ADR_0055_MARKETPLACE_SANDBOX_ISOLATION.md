# ADR 0055: Marketplace Sandbox Isolation (Rule 81)

## Status
Accepted

## Context
Rule 81 establishes that third-party marketplace packages must be treated as hostile code. Unregulated plugins could compromise tenant boundary isolation, exfiltrate confidential business data, or execute unauthorized transactions across departments.

## Decision
1. **Package Manifest Specification (`zonata.marketplace-package/v1`):**
   - Packages must provide a signed `manifest.yaml` declaring identity, publisher verification, version, entrypoints, and granular capability requests (e.g. `read:finance.invoices`, `webhook:listen`, `egress:api.partner.com`).
2. **Sandboxed Execution:**
   - Plugins execute in isolated sandboxes (gVisor microVMs or process-isolated sandboxes with restricted seccomp and network namespaces).
   - Zero access to the host filesystem, host environment variables, or other tenant namespaces.
   - All external network egress is blocked by default; only explicit allowlisted domains declared in the manifest and approved by the tenant admin are permitted.
3. **Emergency Revocation Engine:**
   - Platform operators or tenant admins can revoke a package instantaneously (< 1 second), immediately terminating running instances and invalidating temporary access tokens.
4. **Commercial Truth:**
   - In accordance with the truth rule, paid listing purchase flows report `NOT_IMPLEMENTED` until commercial merchant rails are fully certified.

## Consequences
- **Positive:** Ironclad multi-tenant security; defense in depth against malicious or buggy third-party packages.
- **Negative:** Sandboxing overhead requires pre-warmed runtimes or lightweight container dispatch.
