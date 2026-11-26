# ZONATA — Autonomous AI Company Operating System

[![CI Pipeline](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/workflows/ci.yml/badge.svg)](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Node](https://img.shields.io/badge/node-20%2B-green)
![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1.0-brightgreen)
![Release Status](https://img.shields.io/badge/status-Step%209%20Product%20Readiness%20Certified-success)

**A governed AI workforce, enterprise operations, and developer platform.** Define a company; ZONATA provisions an executive hierarchy (AI CEO, C-suite roles, departments, and outcome-owning AI employees), orchestrates work across 10 functional departments and 88 UN ISIC Rev. 4 industry divisions, filters every side effect through policy/authority/budget gates, and seals outcomes into a cryptographic evidence ledger.

> **Verification & Honesty Contract:** This README describes strictly what is implemented and verified in the repository. Unconfigured live third-party credentials (such as commercial billing gateways or customer ERPs) explicitly report `NOT_CONFIGURED` or `NOT_IMPLEMENTED`, and live PostgreSQL 16 / container contracts require CI or Docker environments rather than lightweight local SQLite runs. Authoritative evidence lives in [`docs/reports/`](docs/reports/).

---

## Platform Architecture

```
                         ┌─────────────────────────────────────┐
                         │             HUMAN OWNER             │
                         │  Approvals · Kill Switches · Grants │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                         │        EDGE GATEWAY & AUTH          │
                         │  Rate Limits · Entitlements · Flags │
                         └──────────────────┬──────────────────┘
                                            │
       ┌────────────────────────────────────▼────────────────────────────────────┐
       │                   AI CEO & MULTI-DEPARTMENT ENGINE                      │
       │  Strategy · Decision Arena · 10 Departments · 88 ISIC Divisions · 30 Geo│
       └────────────────────────────────────┬────────────────────────────────────┘
                                            │
       ┌────────────────────────────────────▼────────────────────────────────────┐
       │         ACTION GATEWAY & DURABLE EXECUTION RUNTIMES                     │
       │  Policy · Authority · Budgets · LangGraph · Temporal · ADK · MCP        │
       └────────────────────────────────────┬────────────────────────────────────┘
                                            │
       ┌────────────────────────────────────▼────────────────────────────────────┐
       │    SOVEREIGN BACKBONE, BILLING, PUBLIC API & MARKETPLACE SANDBOX        │
       │  Double-Entry Ledger · Merkle Evidence · SHA-256 Metering · Webhooks    │
       └─────────────────────────────────────────────────────────────────────────┘
```

---

## Capability Overview (Steps 1–9)

| Milestone | Scope & Implemented Capabilities | Report & Spec |
| :--- | :--- | :--- |
| **Step 1 — Backbone** | Sovereign SQLite/PostgreSQL 16 storage, multi-tenant RLS, double-entry minor-unit ledger, Merkle folio export packs, capability truth probe | [`STEP1_REPORT.md`](docs/reports/STEP1_REPORT.md) |
| **Step 2 — Intelligence** | AI CEO brain, Action Gateway, authority/delegation, org hierarchy, work kernel, SOP executor, 5-layer verification pyramid, KPI/Kaizen loop | [`STEP2_REPORT.md`](docs/reports/STEP2_REPORT.md) |
| **Step 3 — Hands** | Host pairing & permissions, desktop control, origin-bound credential vault, browser engine, anti-evasion AST linters, remote takeover, terminal & sandboxed skill import | [`STEP3_REPORT.md`](docs/reports/STEP3_REPORT.md) |
| **Step 4 — Runtimes** | Runtime ports, LangGraph adapter & encrypted checkpointer, Temporal durable workflows, Google ADK local coordinator, governed MCP runtime | [`STEP4_REPORT.md`](docs/reports/STEP4_REPORT.md) |
| **Step 5 — Trust & Security** | Secrets management, RBAC & dual-control ownership transfer, DB RLS audit, CycloneDX SBOM supply-chain checks, SIEM audit stream, DR drills, crypto-agility | [`STEP5_REPORT.md`](docs/reports/STEP5_REPORT.md) |
| **Step 6 — Evolution** | Failure intelligence taxonomy, owner help escalation, playbook store, canary optimizer, open-source agent intake sandbox, clean-room replication, human-merge GitHub guard | [`STEP6_REPORT.md`](docs/reports/STEP6_REPORT.md) |
| **Step 7 — Department Depth** | 10 functional domains (Finance, Sales/CRM, Support, Marketing, HR fairness/payroll, Operations, Supply Chain/Sanctions, R&D, Legal/Security, BI Semantic Layer) + 7 Temporal workflows | [`STEP7_REPORT.md`](docs/reports/STEP7_REPORT.md) |
| **Step 8 — Global Industry Factory** | Declarative `zonata.industry-pack/v1` factory, 88 ISIC Rev. 4 T1 divisions, 16 T2 overlays, 30 jurisdiction packs, EN 16931 e-invoicing, multi-entity consolidation, blinded benchmark engine | [`STEP8_REPORT.md`](docs/reports/STEP8_REPORT.md) |
| **Step 9 — Product Readiness** | Edge Gateway, OpenFeature flags, Entitlements, BillingPort & SHA-256 metering with hard cost caps & legal hold protection, OpenAPI 3.1.0 Public API v1, Standard Webhooks + SSRF defense, Python & TS SDKs, Consoles + Dead-Control Detector, Onboarding & EU Data Act switching, Mobile PWA + WCAG 2.2 AA gates, Out-of-band Status & Dual-Control Support Grants, Marketplace Sandboxing, Canary Rollback & SLOs | [`STEP9_REPORT.md`](docs/reports/STEP9_REPORT.md) |

---

## Verification & Environment Boundaries

| Surface | Local Dev (SQLite) | GitHub Actions CI | Notes |
| :--- | :--- | :--- | :--- |
| **Core Unit, Security & Qualification Suites** | **Verified** (~2,843 tests across 250 files) | **Verified** | Run with `ZONATA_DB_DIALECT=sqlite ZONATA_TEST_MODE=1` |
| **AST Security & License Linters** | **Verified** | **Verified** | `anti_evasion_linter.py`, `anti_bypass_linter.py`, `gitleaks` |
| **PostgreSQL 16 + Live Service Containers** | Requires local Postgres/Docker | **Verified in CI** | Tests live Postgres 16 RLS, SeaweedFS S3, Mailpit, ClamAV, Tika |
| **Billing / SaaS / Live LLM Providers** | `NOT_CONFIGURED` / `Sandbox` | `Sandbox` fixtures | Real external credentials supplied only by deployment owner |
| **Marketplace Paid Listings** | `NOT_IMPLEMENTED` | `NOT_IMPLEMENTED` | Capability-sandboxed free extensions operational; paid rails gated honestly |

---

## Quick Start

### 1. Local Development Setup

Requirements: Python 3.11+ (tested on 3.11 and 3.14), `pip`, and Node.js 20+ (optional, for frontend syntax checks and TypeScript SDK).

```bash
git clone https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git
cd AI-robo-assistant-saas

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed development database and start local API + web workspace on :8080
./run_local.sh
```

Run an isolated API instance against a disposable SQLite file:

```bash
ZONATA_DB_PATH=/tmp/zonata-dev.db APP_ENV=development python3 api_server.py 8101
curl -s http://127.0.0.1:8101/health
```

### 2. Running Verification Tests & Linters

```bash
# Run full pytest suite (SQLite isolated test mode)
env -u DATABASE_URL -u DATABASE_URL_UNPOOLED ZONATA_DB_DIALECT=sqlite ZONATA_TEST_MODE=1 python3 -m pytest -q

# Run security AST linters & bytecode check
python3 -m compileall -q .
python3 scripts/anti_evasion_linter.py
python3 scripts/anti_bypass_linter.py

# Run Step 9 Release Readiness & End-to-End Qualification Scenario
python3 scripts/release_readiness.py
python3 scripts/step9_scenario.py
```

### 3. Production Container Stack

Copy `production.env.example` to `.env`, configure strong secrets and `DATABASE_URL`, and validate the compose stack:

```bash
cp production.env.example .env
docker compose -f docker-compose.prod.yml config --quiet
```

---

## Repository Layout

| Path | Description |
| :--- | :--- |
| `api_server.py`, `cli.py` | HTTP API server and management CLI |
| `core/` | Domain engine: governance, billing, edge gateway, entitlements, flags, webhooks, public API, consoles, onboarding, EU Data Act compliance, marketplace sandbox, release/SLO engineering, industry/jurisdiction engines, security & execution ports |
| `agent_factory/` | Agent capability compiler, signer, isolated runtime pipeline |
| `sdk/python/`, `sdk/typescript/` | Official client SDKs (`zonata-sdk`, `@zonata/sdk`) and Standard Webhooks verifiers |
| `web/`, `web/pwa/` | Web shell, consoles, Progressive Web App manifest & service worker |
| `migrations/pg/`, `migrations/rollback/` | PostgreSQL 16 schemas, RLS policies, and additive migration rollbacks |
| `packs/`, `evals/` | Declarative UN ISIC Rev. 4 industry packs and golden benchmark evaluations |
| `scripts/` | Scenario runners, linters, release readiness checks, DB seeding, and DR drills |
| `security/` | Protected paths policies (`protected_paths*.yaml`) and security manifests |
| `docs/` | Architecture specs, ADRs (`ADR_0001`–`ADR_0057`), baselines, compliance reports, WCAG 2.2 AA VPAT, CRA runbook — start at [`docs/README.md`](docs/README.md) |
| `openapi_v4.json` – `openapi_v9_public.json` | Versioned OpenAPI specifications (including OpenAPI 3.1.0 Public API v1) |
| `tests/` | Comprehensive unit, contract, preservation, security, chaos, and scenario test suite (250 test files) |

---

## Core Governance Invariants

1. **Preservation Contract (Rules 49, 58, 67, 77):** Protected baselines and schema invariants are verified cryptographically via `docs/baselines/`.
2. **Truth Rule & Honest Capability Reporting (Rule 24):** Missing credentials or unbuilt paths return `NOT_CONFIGURED` / `NOT_IMPLEMENTED`; test simulations require `ZONATA_TEST_MODE=1`.
3. **Money Truth & Billing Safety (Rules 78 & 79):** All monetary arithmetic uses minor integer units (cents) with SHA-256 hash-chained ledgers. Delinquency enforces grace periods, read-only export windows, and strict legal-hold protection against deletion.
4. **No Self-Granted Authority & Dual Control (Rules 15, 57, 82):** Agents cannot elevate permissions or self-approve merges; support staff cannot act without tenant-signed time-boxed grants and cannot invoke owner-reserved actions.
5. **Hostile Extension Sandboxing (Rule 81):** Marketplace packages run inside capability-scoped sandboxes with egress allowlisting and sub-second global revocation.
6. **UX Honesty & Regulatory Readiness (Rule 84 & ADR 0057):** Automated Dead-Control Detector checks, WCAG 2.2 AA quality gates (`DRAFT_ACR_VPAT.md`), EU Data Act zero-fee export, and CRA 24h/72h incident runbooks.

---

## Documentation, Contributing & Security

- **Documentation Index:** [`docs/README.md`](docs/README.md)
- **Contributing Guidelines:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Security Policy & Vulnerability Reporting:** [`SECURITY.md`](SECURITY.md)
- **Third-Party Licences:** [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)

## Licence

No project-wide open-source licence file is currently included in this repository; default copyright applies. Third-party dependency licences are catalogued in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
