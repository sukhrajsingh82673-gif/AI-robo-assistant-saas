# ADR 0037: Connector SDK and Model Context Protocol (MCP) Framework

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 41 (Zero Plaintext Secrets), Rule 42 (Credential Lease Lifecycle), Rule 59 (Systems of Record are Ports)

---

## 1. Context & Problem Statement
ZONATA departments interact with external software (ERPNext, CRM, carrier logistics, bank feeds, payment gateways, e-invoicing portals). Connecting these services requires secure credential isolation, deterministic offline replay testing, and standardized agent tool exposure.

## 2. Decision
1. **Connector Architecture:**
   - All department integrations are implemented as subclasses of `DepartmentBasePort` adhering to the standard Port & Adapter pattern.
   - Every external system interaction is routed through the Connector SDK, which enforces rate limiting, retry with exponential backoff, circuit breaking, and structured logging.
2. **Secret Management & Zero Plaintext Credential Invariant (Rule 41, 42):**
   - Connectors never accept or store plaintext credentials in configuration, database, or workflow payloads.
   - Credentials (API tokens, mutual TLS certs, OAuth tokens) are dynamically leased from OpenBao (Vault-compatible, MPL-2.0) at invocation time via `OpenBaoSecretAdapter`.
   - Dynamic leases carry strict TTLs and are revoked immediately upon workflow task completion or agent failure.
3. **Deterministic Replay Contract Fixtures:**
   - For all external integrations, the Connector SDK includes a `FixtureReplayEngine`.
   - Golden test runs record sanitized network responses into versioned JSON replay fixtures (`tests/fixtures/connectors/<system>/<scenario>.json`).
   - In CI or offline test runs, connectors run in `REPLAY` mode, guaranteeing deterministic unit and regression tests without requiring live external SaaS endpoints.
4. **Model Context Protocol (MCP) Tool Integration:**
   - For each connector, an MCP server wrapper is generated exposing typed, validated JSON-schema tools.
   - High-impact operations (e.g. initiating bank transfers, signing agreements, firing staff, altering tax records) are flagged with `gateway_required: true` and cannot execute without a verified cryptographic human approval signature (Rule 62).

## 3. Consequences
- Completely uniform integration pattern across all 10 departments.
- 100% CI reproducibility using recorded replay fixtures.
- Strict prevention of credential leakage to agent context windows or logs.
