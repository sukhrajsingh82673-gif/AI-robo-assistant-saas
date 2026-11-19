# ZONATA / RoboAssistant

**A governed AI workforce operating system.** You define a company; the platform provisions an
organisation with an AI CEO, C-suite executives, departments and employees; those employees do
work through controlled tools, and every consequential action is filtered by policy, approvals
and budgets, then sealed into an evidence ledger.

> **Release status: restricted production pilot.** This is not a public GA product. Several
> capabilities are implemented but unproven, and a few are explicitly not implemented. The
> per-capability matrix in [`docs/reports/STAGE1_NORTHSTAR_GAP_REPORT.md`](docs/reports/STAGE1_NORTHSTAR_GAP_REPORT.md)
> is the authoritative statement of what works. Where this README and that report disagree, the
> report wins.

---

## Status at a glance

| Dimension | State |
|---|---|
| Release stage | Restricted production pilot (single-tenant evaluations, synthetic data) |
| Test suite | See [§5 Verification](#5-verification) — run it yourself, results are environment-dependent |
| Persistence | SQLite by default; PostgreSQL supported through `DATABASE_URL` |
| Live PostgreSQL qualification | **Blocked** in this environment (no server available) |
| Container / Kubernetes suites | **Blocked** here (no Docker daemon) |
| Browser interaction | **Partial** — `navigate` performs a real HTTP fetch; click/type/submit return `ACTION_NOT_IMPLEMENTED` |
| Tenant, company and employee isolation | **Verified** by negative tests (cross-tenant, cross-company, cross-employee refusals) |

Nothing below is a marketing claim about market readiness. It describes the system that exists in
this repository.

---

## What the system actually does

**Organisation provisioning.** A company is created from one of 15 industry blueprints
(SaaS, e-commerce, professional services, manufacturing, healthcare, financial services, education,
logistics, media, real estate, insurance, energy/utilities, hospitality, telecommunications,
agriculture). Each blueprint provisions 13 C-suite roles plus industry-specific departments.
Hierarchy is data, not code: departments, positions and reporting lines are configurable, and
circular reporting is rejected.

**Employees, not agents.** An AI employee owns an outcome. An agent is a shared capability that an
employee invokes through an isolated instance. Employees have SOPs (immutably versioned), KRAs with
KPIs, and performance reviews that must cite evidence. The co-worker assistant stays outside the
employee hierarchy — it is a tool the owner uses, not a member of staff.

**Governed execution.** Every action that leaves the system passes an action gateway: policy
evaluation, authority tier check, approval requirement, budget check, and a kill switch per surface
(`automation`, `browser`, `mcp`, `nango`, `openhands`, `temporal`, `a2a`). Agents cannot widen their
own authority; HR-style expansion requests cannot approve themselves.

**Evidence, not assertions.** Outcomes are sealed into an append-only ledger with Merkle chaining.
A performance or business claim without a measurement is refused rather than estimated — the
evaluation endpoint returns `409 INSUFFICIENT_MEASUREMENTS` instead of inventing a score.

**Decision arena.** Corporate decisions are scored by four independent deterministic lenses
(FINANCE, RISK, OPERATIONS, COMPLIANCE), producing `CONSENSUS`, `MAJORITY`, `CONTESTED` or
`INSUFFICIENT_EVIDENCE`. Disagreement is reported, never averaged away.

---

## Architecture

```
                    ┌──────────────────────────────┐
                    │          HUMAN OWNER         │
                    │  approvals · kill switch     │
                    └───────────────┬──────────────┘
                                    │
                    ┌───────────────▼──────────────┐
                    │            AI CEO            │
                    │  strategy · missions · arena │
                    └───────────────┬──────────────┘
                                    │
        ┌───────────────────────────▼───────────────────────────┐
        │         EXECUTIVES & DEPARTMENTS (data-driven)        │
        │  CFO · CTO · COO · CRO · CHRO · CISO · …  (13 roles)  │
        └───────────────────────────┬───────────────────────────┘
                                    │
        ┌───────────────────────────▼───────────────────────────┐
        │              EMPLOYEES (own outcomes)                 │
        │   SOP versions · KRAs/KPIs · reviews · collaboration  │
        └───────────────────────────┬───────────────────────────┘
                                    │ invoke (isolated instance + quota)
        ┌───────────────────────────▼───────────────────────────┐
        │        AGENT CAPABILITY FACTORY (shared, sandboxed)   │
        └───────────────────────────┬───────────────────────────┘
                                    │
   ┌────────────────────────────────▼────────────────────────────────┐
   │  ACTION GATEWAY → PolicyEngine → Authority → Approvals → Budget │
   │  → Kill switch check → Execution → Evidence ledger (Merkle)     │
   └─────────────────────────────────────────────────────────────────┘
```

Layer notes and contracts: [`docs/architecture/`](docs/architecture/).

---

## 1. Quick start

Requirements: Python 3.12, `pip`. No paid service is required to run locally.

```bash
git clone https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git
cd AI-robo-assistant-saas

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

./run_local.sh                 # http://localhost:8080
```

`run_local.sh` copies `storage/roboassistant.db` to `storage/runtime.db` and starts the API and the
web shell. To run against a scratch database on a specific port:

```bash
ZONATA_DB_PATH=/tmp/zonata-dev.db APP_ENV=development python3 api_server.py 8101
```

Health probes:

```bash
curl -s localhost:8101/health
curl -s localhost:8101/api/v1/health
```

## 2. Configuration

| Variable | Purpose |
|---|---|
| `ZONATA_DB_PATH` | SQLite file to use (local development default) |
| `DATABASE_URL` / `DATABASE_URL_UNPOOLED` | PostgreSQL connection; takes precedence over SQLite |
| `ZONATA_DB_DIALECT` | Force `sqlite` or `postgres` |
| `APP_ENV` | `development`, `staging`, `production` |
| `ZONATA_TEST_MODE` | Enables test-only fixtures; never set this in production |

Secrets belong in environment variables or a secret manager, never in the repository. `.env*`
files are git-ignored; only `.env.production.example` / `production.env.example` templates are
tracked, and they contain placeholder values.

## 3. Repository layout

| Path | Contents |
|---|---|
| `api_server.py` | HTTP API and static web shell (standard-library server, no framework) |
| `core/` | Domain logic: governance, workforce, agents, evidence, connectors, finance (~370 modules) |
| `web/` | Vanilla-JS workspace shell and per-workspace views |
| `tests/` | Test suite (~120 files) |
| `migrations/pg/` | PostgreSQL schema migrations |
| `docs/` | All long-form documentation — start at [`docs/README.md`](docs/README.md) |
| `k8s/`, `docker/`, `Dockerfile`, `docker-compose.*.yml` | Deployment assets |
| `scripts/`, `run_local.sh` | Operational scripts |
| `production_readiness/`, `organization_qualification_evidence/` | Readiness artefacts and retained evidence |

## 4. Governance invariants

These are enforced in code and covered by negative tests. They are not configuration options.

1. **No self-granted authority.** An agent cannot raise its own authority tier; expansion requires
   an approval from a tier that already holds it.
2. **Tenant and company isolation.** Every read and write is scoped; cross-tenant and
   cross-company access is refused, including through shared resources.
3. **Kill switch is authoritative.** While engaged, every execution surface returns `403`,
   including terminal, browser, missions, MCP, workflows, A2A, finance and workforce.
4. **Budgets are hard limits.** Exhaustion stops work; it does not degrade into a warning.
5. **Evidence or it did not happen.** Business outcomes require a verified record; claims without
   measurement are refused, not estimated.
6. **Employee ≠ agent ≠ co-worker.** Employees own outcomes, agents are shared capabilities with
   isolated sessions, the co-worker sits outside the employee hierarchy.

## 5. Verification

Run the suite locally:

```bash
env -u DATABASE_URL -u DATABASE_URL_UNPOOLED ZONATA_DB_DIALECT=sqlite ZONATA_TEST_MODE=1 \
  python3 -m pytest -q
```

Tests are treated as necessary but not sufficient: end-to-end claims in the reports come from
executed HTTP calls with retained responses, not from unit tests. Every capability row in
[`docs/reports/STAGE1_NORTHSTAR_GAP_REPORT.md`](docs/reports/STAGE1_NORTHSTAR_GAP_REPORT.md) names
the evidence file that backs it.

Known environment limits at the time of writing:

- No Playwright/Chromium, so browser interaction E2E cannot run (`BLOCKED`).
- No Docker daemon, so container suites cannot run (`BLOCKED`).
- No PostgreSQL server, so live-PG qualification and migration `0005` remain unexecuted (`BLOCKED`).
- No local language model (no Ollama daemon, no `HERMES_API_ENDPOINT`). The bundled engine is a
  deterministic rule router, not a model; it reports `RULE_ENGINE_ONLY`, `is_language_model: false`.
- No OCR/AT-SPI tooling, so desktop perception is limited to real X11 windows plus a frame digest;
  interactive elements inside a window are seeded (`PARTIAL`).
- The co-worker autonomy scheduler is verified on one host; its duplicate-run lock is host-local
  `flock`, not a distributed lease (`PARTIAL` for multi-host deployments).

## 6. Documentation

[`docs/README.md`](docs/README.md) is the index. The short version:

| You need | Go to |
|---|---|
| Honest capability and gap matrix | [`docs/reports/STAGE1_NORTHSTAR_GAP_REPORT.md`](docs/reports/STAGE1_NORTHSTAR_GAP_REPORT.md) |
| Coworker §1–§16 spec status | [`docs/reports/SPEC_VS_IMPLEMENTATION_GAP_REPORT.md`](docs/reports/SPEC_VS_IMPLEMENTATION_GAP_REPORT.md) |
| Coworker autonomy runtime | [`docs/architecture/COWORKER_AUTONOMY_RUNTIME.md`](docs/architecture/COWORKER_AUTONOMY_RUNTIME.md), [`docs/runbooks/AUTONOMY_SUPERVISOR.md`](docs/runbooks/AUTONOMY_SUPERVISOR.md) |
| Corrections to earlier coworker reports | [`docs/reports/ZONATA_COWORKER_REPORT_CORRECTIONS.md`](docs/reports/ZONATA_COWORKER_REPORT_CORRECTIONS.md) |
| Release gate status | [`docs/qualification/PUBLIC_GA_FINAL_GATE_MATRIX.md`](docs/qualification/PUBLIC_GA_FINAL_GATE_MATRIX.md) |
| Architecture and contracts | [`docs/architecture/`](docs/architecture/) (the `01_`–`30_` series is in order) |
| Security model and audits | [`docs/architecture/SECURITY_MODEL.md`](docs/architecture/SECURITY_MODEL.md), [`docs/security/`](docs/security/) |
| Runbooks and incident response | [`docs/operations/`](docs/operations/), [`docs/runbooks/`](docs/runbooks/) |
| Installation and deployment | [`docs/deployment/LOCAL_AND_PRODUCTION_INSTALLATION.md`](docs/deployment/LOCAL_AND_PRODUCTION_INSTALLATION.md) |

## 7. Security

- Report vulnerabilities privately to the repository owner; do not open a public issue.
- Do not commit credentials. If a token or password is ever committed, treat it as compromised,
  revoke it, and rotate anything it could reach.
- Third-party licence inventory: [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

## 8. Licence

No project licence file is currently included, so default copyright applies. Third-party
components are listed in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
