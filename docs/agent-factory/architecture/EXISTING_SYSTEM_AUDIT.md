# EXISTING_SYSTEM_AUDIT — ZONATA / URA

**Status: NOT AUDITED — repository access unavailable.** This document is deliberately honest rather than complete-looking. It states exactly what could not be inspected, records what is *claimed* (never as fact), and supplies the audit protocol and tooling that turn every row from UNKNOWN into evidence in Phase 1.

## 1. What could and could not be inspected

| Item | Result |
|---|---|
| GitHub repo `sukhrajsingh82673-gif/AI-robo-assistant-saas` | **Not inspectable.** Anonymous `git ls-remote` prompts for credentials (private or non-existent), and this session has no linked GitHub account (`add_repo`/`list_repos` both refused). |
| Local path `/root/roboassistant` | **Does not exist** in this session's sandbox. |
| Branches / commits / tests / migrations / schemas / API routes | **Not inspected.** |
| Live staging `https://zonata-staging.onrender.com` | Fetch refused (`robots_disallowed`); nothing was retrieved and no API surface was observed. Not evidence. |
| Project knowledge available | Only user statements (project notes) and the GPT brief's *"indicative inventory, not proof"*. |

**Consequence:** no row below is classified `IMPLEMENTED AND VERIFIED`. Per the brief: *"do not fabricate audit findings."*

## 2. Inventory required by Brief Part 4 (all UNKNOWN until Phase 1)

"Claimed by" is the only source available today. "Phase-1 evidence required" is what OpenCode must produce (file path, class/function, DB table, test coverage, evidence, gap).

| # | Capability (Part 4) | Classification today | Claimed by | Phase-1 evidence required to classify |
|---|---|---|---|---|
| 1 | Agent creation mechanism | UNKNOWN / INSUFFICIENT EVIDENCE | Owner believes an "agent factory" already exists; owner's design says an AI employee builds agents from the app's templates, else downloads OSS agents via the terminal | Locate code that creates an agent record/runtime. Run it. Is it LLM-prompt-only, config-only, or code-generating? Is it called by a route or by the AI CEO flow? |
| 2 | Agent registry | UNKNOWN | Brief lists it as needed | Table(s) + CRUD + identity binding + tenant column? Version history? |
| 3 | Agent templates | UNKNOWN | Owner: "app's templates" | Template store (files/DB), schema, count, versioning, review process |
| 4 | Agent execution engine | UNKNOWN | LangGraph, Agency Swarm, Letta, HAL AI listed | Which engine actually executes a task end-to-end today (run one) |
| 5 | Workforce assignment | UNKNOWN | Owner: AI employees use agents; agents never use employees; CHRO manages employees and agents | Employee/department tables, assignment relation, enforcement of "agents never use employees" |
| 6 | Employee identity & permissions | UNKNOWN | Keycloak, OpenFGA, RBAC listed | Realm/clients, FGA model, role tables, how an AI employee authenticates |
| 7 | MCP infrastructure | UNKNOWN | Listed; owner says agents also create MCPs/integrations per department | Client/server code, registry, tool allowlisting, auth, gateway |
| 8 | A2A implementation | UNKNOWN | Listed | Protocol version, Agent Card endpoint, message handling, auth |
| 9 | Memory infrastructure | UNKNOWN | Letta listed | Scoping (agent/team/company), tenant isolation, retention |
| 10 | Tool registry | UNKNOWN | Listed implicitly | Registry, per-tool permission, MCP binding |
| 11 | Agent evaluation | UNKNOWN | Not listed | Any eval harness/datasets/scores |
| 12 | Test infrastructure | UNKNOWN | — | Frameworks, count, pass/fail baseline **executed** |
| 13 | Deployment mechanisms | Partial context | Render staging (`zonata-staging`) + Neon Postgres; builds via Termux | Dockerfile/render.yaml, env handling, what services actually run (Temporal? NATS? Vault?) |
| 14 | Workflow orchestration | UNKNOWN | Temporal, LangGraph, "Universal Automation Fabric" listed | Which are running vs. only imported |
| 15 | Monitoring | UNKNOWN | OpenTelemetry, Langfuse, PostHog listed | Exporters configured? Dashboards? |
| 16 | Tenant isolation | UNKNOWN | "Multi-tenant isolation" listed; owner has multiple companies per account | **Isolation boundary: tenant, company, or both?** RLS? App-level filters only? |
| 17 | Governance integrations | UNKNOWN | Constitution, PolicyEngine, AuthorityGateway, ApprovalEngine, EvidenceLedger (SHA-256+Merkle), KillSwitchMatrix listed | For each: real implementation vs. class/interface/doc only; are protected actions actually routed through it; verify ledger hash-chain with a tamper test |

## 3. Claimed components that must each be classified

Company Kernel · Sovereign Constitution · PolicyEngine · AuthorityGateway · Consent/ApprovalEngine · EvidenceLedger (SHA-256 + Merkle) · KillSwitchMatrix · RBAC/org authority · AI CEO/AICU · Agency Swarm · LangGraph · Letta · HAL AI · MCP · A2A · OpenHands · Browser Use · Universal Linux Terminal · Universal Automation Fabric · Temporal · Vault · Keycloak · OpenFGA · NATS JetStream · MinIO/S3 · OpenTelemetry · Langfuse · PostHog · model gateway/inference.

Allowed classifications: `IMPLEMENTED AND VERIFIED` · `IMPLEMENTED BUT INCOMPLETE` · `PARTIALLY IMPLEMENTED` · `NOT IMPLEMENTED` · `IMPLEMENTED BUT REQUIRES REFACTORING` · `UNKNOWN / INSUFFICIENT EVIDENCE`.

### Evidence rubric (what earns "IMPLEMENTED AND VERIFIED")
All of: (1) code on the real execution path (not dead code); (2) reachable from a route/job/CLI; (3) **no** stub/mock/canned response on the production path; (4) backing storage exists with migrations; (5) at least one test that exercises it and **was executed by the auditor** with captured output; (6) for governance components, a negative test (denied/blocked case) was executed. Missing any → at best `IMPLEMENTED BUT INCOMPLETE`. A class, interface, README, or ADR alone → `NOT IMPLEMENTED` or `PARTIALLY IMPLEMENTED`, never "verified".

## 4. Audit protocol for Phase 1 (read-only; no repo modification)

1. `git status`, `git branch -a`, `git log --oneline -n 50`, note the commit SHA audited. Create `docs/agent-factory/audit/` only (documentation) on a new branch `agent-factory/audit`.
2. Run `python3 -I architecture/tools/audit_scan.py <repo> --out audit/audit_scan.json --md audit/audit_scan.md` (stdlib only; tested on a 20k-line FastAPI/LangGraph codebase). It yields: languages, frameworks, API version prefixes in use, routes, tables, tests, migration files, per-component mention counts and **stub/mock density per file**.
3. Establish the **test baseline**: install dependencies using the repo's own method, run the full existing suites, save raw output to `audit/baseline_tests.txt`. This baseline is the oracle for acceptance test AT-22 (existing workforce functionality unaffected).
4. For each claimed component, produce one entry in `audit/INVENTORY.md` with: classification · file paths · classes/functions/routes · DB tables · tests (executed output) · evidence · gap.
5. Answer the **eight reuse questions** (below) explicitly.
6. Produce `audit/PORT_MAP.md` mapping each Factory port (`GovernancePort`, `IdentityPort`, `SecretsPort`, `ModelGatewayPort`, `ToolRegistryPort`, `McpGatewayPort`, `MemoryPort`, `WorkforcePort`, `RuntimePort`, `ArtifactStorePort`, `OrchestratorPort`, `TelemetryPort`) to the **real** class/function it will wrap, or to "MISSING → minimal adapter needed".
7. STOP and hand the audit to the human owner for approval before any code is written (decision gate D1).

### The eight reuse questions (answers drive the design)
| Q | Question | If yes | If no |
|---|---|---|---|
| Q1 | Does an **agent factory / agent builder** already exist? | Classify it. Keep it running. Put it behind `AgentBuildPort`, route new capability through the Factory pipeline, migrate via strangler pattern (never delete). | Build the Factory fresh on the ports. |
| Q2 | Is there an agent **registry** table with identities? | Extend via `af_agent` *mapping* (add `legacy_agent_id`) instead of a second source of truth; decide in ADR. | Create `af_agent`. |
| Q3 | Does AuthorityGateway expose a callable `authorize(...)` that real routes use? | Wrap it in `GovernancePort`. | **Stop-the-line**: governance integration is the Factory's #1 dependency; implement a minimal authoritative adapter and flag as risk. |
| Q4 | Is the EvidenceLedger append-only with verifiable hash chain **in tests**? | Use as-is. | Fix/complete before Factory release gates can rely on it. |
| Q5 | Is Temporal actually **deployed and reachable** where the app runs? | `TemporalOrchestrator`. | `DbQueueOrchestrator` (Postgres) behind same port. |
| Q6 | What is the tenant boundary and how is it enforced (RLS vs app filter)? | Mirror it exactly in `af_*` policies. | Adopt RLS as specified in `001_agent_factory_core.sql`. |
| Q7 | Is there a sandbox/terminal that can run untrusted code with isolation? | Candidate for T1; verify controls. | Tool-authoring and OSS-import lanes stay **disabled**; declarative agents only (T0). |
| Q8 | What backend language/framework and migration tool are used? | Match conventions; translate the reference DDL. | — |

## 5. Hypotheses to confirm or kill (not findings)

H1 The "existing agent factory" is mostly prompt-template based. · H2 Several listed components are interface-only or mocked (the owner's own front-end notes list scripted assistant replies, scripted terminal, sample companies and numbers as placeholders in the **design prototype** — the repo may or may not share them). · H3 Free-tier hosting cannot run Temporal, NATS, Keycloak and Vault together. · H4 Tenant isolation is application-level. · H5 Existing "agents" are not separately identified principals.

## 6. Existing facts about the *owner's intended design* (from project notes — design intent, not code)

- AI employees run under SOPs and KRA/KPI; **AI employees can use AI agents, but agents can never use employees**.
- If no agent fits, an AI employee builds one from the app's templates; if templates are insufficient, it finds open-source agents (e.g. GitHub) and installs them via the app terminal → this becomes the Factory's quarantined **Import lane**.
- The AI CEO watches everything; the co-worker assistant observes and can use factory agents; personal scope is free, company scope needs AI CEO permission.
- Autonomy modes exist in Settings ("Ask me first", "Balanced", "Mostly autonomous") and drive the Approvals queue → mapped onto the release approval matrix in `gate_policy.yaml`.
- The CHRO department owns AI employees and agents; CTO owns technology.

## 7. How to convert this document into a real audit quickly

Give me (a) GitHub access or a zip of the repo (excluding `node_modules`, `.git`, secrets), or (b) have OpenCode run the protocol above and paste `audit/INVENTORY.md` + `audit/PORT_MAP.md` back. I will then update `TARGET_ARCHITECTURE.md`, the roadmap and the OpenCode prompt with verified reuse points.
