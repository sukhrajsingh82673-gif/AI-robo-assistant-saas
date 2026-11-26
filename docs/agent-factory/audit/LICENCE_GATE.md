# LICENCE_GATE — ZONATA Agent Factory Phase 1 Audit

Date: 2026-11-19 · Scope: Open Source Dependency & Supply Chain Verification

---

## 1. Critical Flags & Licensing Warnings

1. **MinIO Storage Engine:**
   - **Status:** **FLAGGED / ARCHIVED UPSTREAM**.
   - **Reason:** Upstream repository was archived on 2026-04-25. No further community security patches or maintenance.
   - **Action:** Transition artifact storage to an active S3-compatible cloud object store (AWS S3, Cloudflare R2, Neon storage) or local disk.

2. **HashiCorp Vault vs OpenBao:**
   - **Status:** **BSL 1.1 LICENCE RESTRICTION**.
   - **Reason:** HashiCorp Vault is governed by the Business Source License (BSL 1.1), prohibiting competitive commercial hosting.
   - **Action:** Use OpenBao (MPL-2.0, Linux Foundation) for external secrets/transit or retain the existing AES-GCM encrypted local secret store.

3. **Promptfoo:**
   - **Status:** Commercial acquisition notice. Pinned as optional adapter; do not make a hard gate dependency.

---

## 2. Permitted & Adopted Dependencies

| Package / Tool | License | Target Version / Pin | Upstream Status | Role in Agent Factory |
|---|---|---|---|---|
| **`pydantic`** | MIT | `^2.7.0` | Active | Declarative spec validation & JSON Schema compilation |
| **`cryptography`** | Apache-2.0 / BSD | `50.0.2` | Active (already installed) | Ed25519 detached signatures, SHA-256 digests |
| **`langgraph`** | MIT | `^0.0.40+` (library only) | Active | Directed cyclic execution graph compiler |
| **`bagalsharad/agent_factory`** | Apache-2.0 | Vendored & reviewed | Active (Alpha) | Adapted spec models, starter templates, gate logic |
| **`opentelemetry-api`** | Apache-2.0 | `^1.24.0` | Active | Distributed tracing and spans |
| **`jsonschema`** | MIT | `^4.21.0` | Active | Strict schema validation against `zonata.agent.v1` |

---

## 3. Rejected Dependencies (Strict Invariant Enforcement)

| Rejected Tool | Reason for Rejection |
|---|---|
| **Mozilla `agent-factory`** | Dormant since Oct 2025; generates unvalidated executable host code; no governance. |
| **CrewAI / Agno / ADK** | Telemetry defaults, duplicates LangGraph graph execution, conflicts with ZONATA authority hierarchy. |
| **LangGraph Server / LangSmith** | Proprietary commercial service; violates data sovereignty requirement. |
| **OPA (Open Policy Agent) / Cedar** | Redundant; ZONATA PolicyEngine and ActionGateway are already authoritative. |

---

## 4. Free-Tier / Local Host Tooling Evaluation

| Tool | License | Local Availability (Termux ARM64) | Pilot Status |
|---|---|---|---|
| **Bandit** | Apache-2.0 | Available via pip | Enabled for static analysis |
| **pip-audit** | Apache-2.0 | Available via pip | Enabled for vulnerability screening |
| **gitleaks** | MIT | Available via Go binary / standalone script | Enabled for secret screening |
| **gVisor / Firecracker / Kata** | Apache-2.0 | **UNAVAILABLE** (no KVM / root virtualization) | **Disabled (T0 mode only)** |
| **Temporal Server** | MIT | **UNAVAILABLE** (no daemon / Docker) | **Disabled (use DbQueueOrchestrator)** |
| **OpenFGA / Keycloak / NATS** | Apache-2.0 | Standalone daemons unavailable | **Fallback to embedded SQLite/in-process models** |
