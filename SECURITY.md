# Security Policy

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues, pull requests, or discussions.**

Because this repository is public, disclose suspected vulnerabilities privately to the repository owner via GitHub Private Vulnerability Reporting (Security Advisories) or direct maintainer contact. Include:

- Affected module, endpoint, or dependency.
- Step-by-step reproduction instructions with synthetic data only.
- Potential impact on tenant isolation, authority boundaries, secrets, or sandbox containment.

## Response & EU Cyber Resilience Act (CRA) Alignment

Operational vulnerability triage, 24-hour early CSIRT/ENISA warning pathways, and 72-hour full remediation reporting follow [`docs/security/CRA_INCIDENT_RUNBOOK.md`](docs/security/CRA_INCIDENT_RUNBOOK.md).

## Architectural Security Guarantees

- **Tenant & Company Isolation:** Multi-tenant PostgreSQL Row-Level Security (RLS) policies and strict application-level tenant scoping.
- **No Unconsented Support Access (Rule 82):** Platform operators require tenant-issued, time-boxed, HMAC-signed grants and cannot invoke owner-reserved actions.
- **Hostile Third-Party Code Isolation (Rule 81):** Marketplace packages execute inside capability-scoped sandboxes with egress allowlisting and sub-second global revocation.
- **Secret Hygiene:** All repository commits are screened with `gitleaks` and AST security linters; `production.env.example` contains placeholders only.
