# ZONATA Co-Worker — Third-Party Open-Source Supply Chain & Licensing Governance

## 1. Executive Summary & Sovereignty Invariant

The ZONATA Universal AI Co-Worker Fabric integrates open-source execution engines, RPA toolkits, browser automations, and desktop vision-language frameworks behind strict corporate contracts. 

> [!IMPORTANT]
> **Sovereign Authority Invariant**:
> External open-source components are **execution providers only**. Under no circumstances does an open-source library, runtime, agent framework, or external protocol obtain sovereign authority over ZONATA. All executions remain subordinate to the **Company Kernel**, **PolicyEngine**, **ApprovalEngine**, **AuthorityGateway**, **CredentialAuthority**, and **EvidenceLedger**.

Every external dependency is audited, quarantined in sandboxes, cryptographically bounded by execution leases, and restricted from unauthorized credential access.

---

## 2. Integrated Open-Source Runtime Dependencies (Actually Installed)

The following libraries are physically installed and verified against package metadata:

| Project | Installed Version | License (SPDX) | Role in ZONATA | Status |
| :--- | :--- | :--- | :--- | :--- |
| **pg8000** | `1.31.6` | BSD-3-Clause | Pure-Python PostgreSQL Wire Protocol Driver | INTEGRATED & ACTIVE |
| **psycopg2-binary** | `2.9.9` | LGPL-3.0 with exception | PostgreSQL Driver (Linux Container Profile) | INTEGRATED & ACTIVE |
| **PyYAML** | `6.0.3` | MIT | Process Pack & Declarative Schema Parser | INTEGRATED & ACTIVE |
| **numpy** | `2.5.5` | BSD-3-Clause | Numeric Computations & Mathematical Kernels | INTEGRATED & ACTIVE |
| **pandas** | `3.1.1` | BSD-3-Clause | Tabular Financial Dataframe Modeling | INTEGRATED & ACTIVE |
| **cryptography** | `50.0.2` | Apache-2.0 OR BSD-3-Clause | AES-256-GCM Sovereign Envelopes & Signatures | INTEGRATED & ACTIVE |
| **python-dateutil** | `4.0.0` | BSD-3-Clause | ISO-8601 UTC Timestamp & Recurrence Arithmetic | INTEGRATED & ACTIVE |

---

## 3. Network Service Boundaries (Independent Service Containers)

| Service | Pinned Image | License (SPDX) | Protocol Boundary | Confinement |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL 16** | `postgres:16.4-alpine` | PostgreSQL (MIT-style) | TCP Port 5432 network wire | RLS enforced; zero shared memory |
| **SeaweedFS** | `chrislusf/seaweedfs:3.79` | Apache-2.0 | TCP Port 8333 S3 HTTP API | Pre-signed URLs, read-back SHA-256 |
| **Mailpit** | `axllent/mailpit:v1.21.8` | Apache-2.0 | TCP Port 1025 SMTP / 8025 API | Sandboxed test sink; zero disclosure |
| **Apache Tika** | `apache/tika:2.9.2.1` | Apache-2.0 | TCP Port 9998 HTTP REST | Document text/metadata extraction |
| **ClamAV** | `clamav/clamav:1.4.1` | GPL-2.0-only | TCP Port 3310 socket | Quarantined network boundary |

---

## 4. Planned Future Integrations (Architecture Roadmap)

The following components were referenced in earlier pilot specifications but are **not currently imported** into runtime execution. Per OpenCode Step 1 honesty invariants, they are designated as `PLANNED` for subsequent architectural stages:

| Component | Upstream Project | License (SPDX) | Planned Stage | Integration Architecture |
| :--- | :--- | :--- | :--- | :--- |
| **Temporal** | `temporalio/sdk-python` | MIT | Step 4 | Durable Workflow Engine behind `WorkflowPort` |
| **NATS JetStream** | `nats-py` | Apache-2.0 | Step 4 | High-throughput distributed event broker |
| **MCP Python SDK** | `modelcontextprotocol` | MIT | Step 4 | Standardized tool exposition protocol |
| **OpenTelemetry** | `opentelemetry-api` | Apache-2.0 | Step 4 | Distributed tracing and span propagation |
| **Langfuse / LiteLLM** | `langfuse`, `litellm` | MIT / Apache-2.0 | Step 2 | Model gateway tracing and token routing |
| **boto3** | `boto3` | Apache-2.0 | Step 1D | Production AWS S3 client behind `StoragePort` |
| **pydantic** | `pydantic` | MIT | Step 1H | Typed schema validation for industry packs |
| **httpx** | `httpx` | BSD-3-Clause | Step 1D | Async HTTP client for outbound webhook delivery |
| **OpenHands** | `All-Hands-AI/OpenHands` | MIT | Step 3 | Sandboxed software engineer coworker runtime |
| **Playwright** | `playwright` | Apache-2.0 | Step 3 | Headless browser execution with human hand-off |
| **OpenAdapt** | `OpenAdaptAI/OpenAdapt` | MIT | Step 3 | Desktop visual perception & macro recording |
| **LangGraph Core** | `langgraph` | MIT | Step 4 | Multi-agent state graph coordinator |

---

## 5. Security Audit & Supply Chain Policy

1. **SPDX Allowlist**: Only OSI-approved, non-viral licenses (MIT, Apache-2.0, BSD-2/3-Clause, MPL-2.0, PSFL, 0BSD, ISC) may be imported directly into Python runtime space.
2. **Copyleft & Source-Available Boundaries**: Any tool with GPL, AGPL, SSPL, BSL, or Elastic licensing is strictly confined to independent network services communicating via network sockets or REST APIs.
3. **Automated Audit Gates**: Every CI push evaluates `gitleaks`, `pip-audit`, CycloneDX SBOM, and an AST license validator.
