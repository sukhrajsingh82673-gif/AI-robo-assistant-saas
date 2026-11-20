# ZONATA Dependency Licensing & Commercial Compliance Audit

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-19  
**Policy:** Permissive Open-Source Licensing (MIT, Apache 2.0, BSD-2/3-Clause). Copyleft/AGPL quarantined outside proprietary core boundaries.

---

## 1. Runtime Python Dependencies (`requirements.txt`)

| Package | Version | License (SPDX) | Commercial SaaS Permissible? | Usage & Confinement |
|---|---|---|---|---|
| `psycopg2-binary` | `2.9.9` | LGPL-3.0 with OpenSSL exception | **YES (Permissible)** | C-binding client for PostgreSQL. Dynamically linked; no modifications made. |
| `pg8000` | `>=1.31.5` | BSD-3-Clause | **YES (Permissible)** | Pure-Python PostgreSQL driver for ARM64/Termux fallback without C compiler. |
| `PyYAML` | `6.0.1` | MIT | **YES (Permissible)** | Parser for templates, Process Packs, and gate policies. |
| `numpy` | `>=1.26.4` | BSD-3-Clause | **YES (Permissible)** | Vector arithmetic, Wilson score calculations, statistical analysis. |
| `pandas` | `>=2.2.2` | BSD-3-Clause | **YES (Permissible)** | Tabular corporate analytics and ledger aggregation. |
| `python-dateutil` | `2.9.0.post0` | Apache-2.0 / BSD-3-Clause | **YES (Permissible)** | ISO-8601 parsing and calendar scheduling. |
| `cryptography` | `50.0.2` | Apache-2.0 / BSD-3-Clause | **YES (Permissible)** | Ed25519 signing, HMAC-SHA256, Merkle tree sealing. |

---

## 2. Node.js & Web Client Dependencies (`package.json`)

| Package | Version | License (SPDX) | Commercial SaaS Permissible? | Usage & Confinement |
|---|---|---|---|---|
| `@neon/config` | `^1.9.2` | Apache-2.0 | **YES (Permissible)** | Serverless database configuration. |
| `@neon/env` | `^1.6.3` | Apache-2.0 | **YES (Permissible)** | Cloud environment variable loader. |
| `jsdom` (devDependencies) | `^31.0.0` | MIT | **YES (Permissible)** | Test runner for assistant and company setup headless DOM assertions. |

---

## 3. Quarantined & External Node Components

| Component | License | Confinement Strategy |
|---|---|---|
| **LangGraph Core (`v0.2.14`)** | MIT | Native SQLite StateGraph checkpointing in `core/durable_workflow_runtime.py`. |
| **Model Context Protocol (MCP)** | MIT | Stdio / SSE transport gateway in `agent_factory/capabilities/mcp_gateway.py` with tool description SHA-256 hash pinning. |
| **OpenRPA** | AGPL-3.0 | Strictly out-of-process network boundary (A2A JSON-RPC / REST). Zero proprietary code linkage. |

---

## 4. Compliance Conclusion
All direct dependencies in `requirements.txt` and `package.json` comply with commercial enterprise SaaS constraints. No restrictive copyleft code touches the core proprietary domain logic.
