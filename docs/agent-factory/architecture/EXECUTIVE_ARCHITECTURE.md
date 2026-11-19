# EXECUTIVE_ARCHITECTURE — ZONATA Agent Factory

**Prepared:** 2026-11-15 · **For:** the owner of ZONATA / URA · **Audience:** owner, AI CEO configuration, and the coding agent (OpenCode) that will implement it.

## 1. What this is

The Agent Factory is the part of ZONATA that **manufactures AI agents on request**. An employee (or the owner, or the co-worker assistant on the owner's behalf) describes what they need in plain language; the Factory returns **one agent, several agents, or a whole supervised team** that is designed, built, **independently tested, security-checked, certified, approved by ZONATA's own authority, and then handed to the requesting employee or department**. Then it keeps watching them.

> The Agent Factory manufactures. ZONATA governance authorises. The existing workforce system manages. The authorised runtime executes. ZONATA remains the ultimate authority.

## 2. The five decisions that shape everything

1. **Agents are data, not generated code.** Every agent is a validated specification (`zonata.agent/v1`) that ZONATA's existing LangGraph runtime compiles. Nothing a model writes ever runs inside the backend. Code appears only as reviewed *tool packages* in a sandbox, and only where a sandbox exists.
2. **No AI holds a gate.** The roles that approve, certify, release or schedule are deterministic services. AI roles only *propose* (requirements, design, drafts, test cases). A threshold cannot be talked out of its answer.
3. **Four hands must differ:** requester ≠ builder ≠ independent tester ≠ approver — enforced in code, in the permission model, and in the database.
4. **Capability is not permission.** An agent may be *able* to browse the web or call a database view; it can *do* so only if the permission calculator, the AI CEO's policy, the constitution and a per-call AuthorityGateway check all agree — every time.
5. **Reuse ZONATA; don't rebuild it.** The Factory talks to your Company Kernel, PolicyEngine, AuthorityGateway, ApprovalEngine, EvidenceLedger, KillSwitchMatrix, workforce and runtime only through thin *ports*. It owns just 24 new tables (prefixed `af_`) and creates no employee, tenant, identity, approval or audit tables.

## 3. How it works in one page

```
Employee request ─► Requirement analysis ─► Architecture (single / supervisor / parallel / hierarchy)
 ─► Template discovery ─► Construction ─► Integration (tools, MCP, knowledge, memory; secrets by reference)
 ─► Builder tests ─► INDEPENDENT QA (different principal, held-out data, real model)
 ─► Certification (deterministic gates, signed bundle) ─► ZONATA approval (AI CEO / owner / security by risk)
 ─► Atomic publish & provisioning to employee/department ─► Monitoring ─► Upgrade / rollback / suspend / retire
```

- **Batches and teams:** one request can yield up to 500 agents; a dependency graph decides what builds in parallel; a failed agent blocks only its dependants and can never be silently certified; teams publish **atomically** (never half-live).
- **Risk tiers R0–R3** (reads only → high impact) are computed from what an agent can do and decide who must approve. Your existing autonomy modes ("Ask me first", "Balanced", "Mostly autonomous") can only make this stricter.
- **Control and observation:** the AI CEO and owner sit at the top of approvals, quotas, policy and the kill switch; the co-worker assistant is a **read-only observer** of the Factory and can *use* certified agents and submit requests on a user's behalf (company scope needs AI CEO permission).
- **Open-source agents** (your "download from GitHub" idea) enter through a **quarantined Import lane** that never runs foreign code on the host and converts it into a certified spec — available only once a proper sandbox host exists.

## 4. Technology decisions (evidence in `OPEN_SOURCE_EVALUATION.md`)

| Decision | Verdict | Key reason |
|---|---|---|
| Mozilla `agent-factory` | **Reject** as a dependency | Dormant since 2025-10-20; generates executable code; no governance |
| `bagalsharad/agent_factory` | **Adapt** (reference + reviewed vendored modules) | Closest philosophy (declarative specs, policy outside the model, gates) but **alpha**: 17 commits in 4 days, single author, AI-built, tests not run by us |
| LangGraph | **Adopt (existing, library only)** | MIT; platform/Server is proprietary — avoid |
| Temporal | **Adopt via a port**, with a Postgres queue fallback | Perfect fit for long jobs; cannot run on free tiers |
| CrewAI, Agno | **Not as runtimes** | Duplicate LangGraph; telemetry defaults |
| OpenHands | **Optional, flag-gated Tool Smith** in a microVM only | Powerful but executes code |
| Sandboxes (gVisor/Firecracker/Kata) | **Required for untrusted code**; unavailable on free tier | Honest isolation |
| QA tooling | Own thin harness + Langfuse; promptfoo/garak/DeepEval optional | Control of independence; avoid vendor drift |
| Signing | Ed25519 detached signatures, key in secret store | Simple and verifiable |

**Three licence/supply flags you must decide on:** MinIO's open-source repo was **archived on 2026-04-25** (no more patches) → move artifacts to a maintained S3 target; **HashiCorp Vault is BSL 1.1** → consider OpenBao (MPL-2.0) and get legal advice; **promptfoo** is being acquired by OpenAI → keep it optional.

## 5. What has actually been verified — and what has not

| Verified by execution in this session | Result |
|---|---|
| Core database schema (24 tables) on PostgreSQL 16.15 | Applies cleanly; **17/17 behavioural checks pass**: cross-tenant isolation (read, write, fail-closed), frozen agent versions, no self-granted permissions, immutable artifacts/certifications/releases, **self-approval blocked at DB level**, approval needs an ApprovalEngine id, builder cannot be the independent evaluator, global templates read-only, idempotency |
| Certification gate evaluator | **14/14 self-tests** (mock evidence never certifies; one critical finding, one cross-tenant hit, one ungranted tool call, too few cases, duplicate approver, cyclic team each block) |
| Batch planner | **15/15 self-tests** (7-agent team → 3 waves; failure blocks dependants only; cycles, two supervisors, unknown nodes rejected; 300-agent fleet plans) |
| Agent spec schema | Example agent validates; "agents may use employees", bad risk tier and unknown keys are rejected |
| Repo audit scanner | Runs on a real 20k-line FastAPI/LangGraph codebase (245 routes, 40 tables found) |
| Open-source facts | Licences, versions, commit dates, structure read from cloned sources; web facts fetched 2026-11-15 |
| Ed25519 signing, hash-chain tamper detection, Merkle root (reference implementation) | **11/11 self-tests** (forged/swapped/revoked-key signatures rejected; tampered ledger entry detected at the exact sequence) |
| 5 Mermaid diagrams | Render without errors |

| **NOT verified** | Why |
|---|---|
| **Your ZONATA repository** — every "existing component" | Repo is private/unlinked. The audit document is honest: all UNKNOWN. Phase 1 fixes this |
| Whether an "agent factory" already exists in URA | Same |
| Neon/pooler behaviour of the RLS design, Temporal, sandboxes, scale, cost | Not available here; listed in the risk register |
| The alpha OSS code I propose to adapt | Read, not executed |
| Gate thresholds | Engineering defaults; calibrate in Phase 7 |

## 6. Roadmap in one view

Phase 1 audit (≈1 wk) → 2 foundation & governance (2) → 3 templates & requirement engine (2) → 4 single-agent manufacturing (2) → 5 batch/teams (2) → 6 tools/capabilities (2) → 7 QA & certification (3) → 8 registry, approval, marketplace UI (1.5) → 9 monitoring, upgrades, Command Centre (2) → 10 enterprise acceptance & pilot readiness (2). **≈19–21 weeks** (rough estimate). A useful **first milestone** is Phases 1–4 + the QA core of Phase 7 for single R0/R1 agents on the free tier — real, governed, tested agent manufacturing without sandboxes.

## 7. What I need from you

1. **Give me repo access** (link GitHub or send a zip without secrets/`node_modules`) → I convert the audit into verified findings and tighten the plan; **or** run Phase 1 with OpenCode and paste back `INVENTORY.md` + `PORT_MAP.md`.
2. Approve (or change) the decisions marked *Proposed* in the ADR, especially ADR-002, 004, 007, 017, 018.
3. Tell me your **hosting reality** for the pilot (can you get one Linux VM with Docker, ideally KVM?). That decides whether tool-authoring and the Import lane are in the pilot.
4. Hand `OPENCODE_MASTER_IMPLEMENTATION_PROMPT.md` + the `architecture/` folder to OpenCode, **Phase 1 only first**.

## 8. Document map

01 this file · 02 `EXISTING_SYSTEM_AUDIT` · 03 `OPEN_SOURCE_EVALUATION` · 04 `TARGET_ARCHITECTURE` · 05 `FACTORY_ORGANISATION` · 06 `MANUFACTURING_LIFECYCLE` · 07 `MULTI_AGENT_MANUFACTURING` · 08 `TEMPLATE_AND_CAPABILITY_SYSTEM` · 09 `SECURITY_AND_GOVERNANCE` · 10 `DATABASE_AND_API_SPECIFICATION` · 11 `QA_AND_CERTIFICATION` · 12 `UI_UX_SPECIFICATION` · 13 `INFRASTRUCTURE_AND_DEPLOYMENT` · 14 `IMPLEMENTATION_ROADMAP` · 15 `OPENCODE_MASTER_IMPLEMENTATION_PROMPT` · 16 `GAP_AND_RISK_REGISTER` · 17 `FINAL_ARCHITECTURE_DECISION_RECORD`; plus `reference/` (tested SQL, schemas, gate policy, planner) and `tools/` (audit scanner, diagram checker, build script).
