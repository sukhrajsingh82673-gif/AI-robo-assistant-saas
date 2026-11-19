# GAP_AND_RISK_REGISTER

Scale: Likelihood (L) and Impact (I) = Low / Med / High. "Trigger" = observable sign the risk has materialised. Owner roles: **HO** human owner, **CTO**, **SEC** security approver, **OC** OpenCode (implementation agent).

## A. Gaps (things not known or not yet done)

| ID | Gap | Why it matters | Closed by | Owner |
|---|---|---|---|---|
| G-01 | ZONATA repository **not audited** (private; no access) | Every reuse point and port binding is hypothetical | Phase 1 audit (or give access/zip) | HO / OC |
| G-02 | Existing "agent factory" (owner believes one exists) is unlocated | Risk of a parallel second factory | Phase 1 Q1 + ADR on migration | OC |
| G-03 | Governance components (AuthorityGateway, ApprovalEngine, EvidenceLedger, KillSwitchMatrix, Constitution) may be partial/stub | Factory security depends on them | Phase 1 classification with executed negative tests; stop-the-line if absent | OC |
| G-04 | Backend language/framework, migration tool, API version prefix unknown (the brief's `/api/v9` is a guess) | File plan and DDL syntax adapt | Phase 1 `API_CONVENTIONS.md` | OC |
| G-05 | Tenant isolation boundary (tenant vs company; RLS vs app filter) unknown | RLS design must mirror reality | Phase 1 Q6 | OC |
| G-06 | `[KNOWLEDGE]` licences/versions (gVisor, Firecracker, Kata, cosign, Semgrep, Bandit, gitleaks, pip-audit, OSV, Syft, Trivy, DeepEval, Inspect, Ragas, garak, PyRIT, OPA, OpenFGA, Keycloak, NATS, Langfuse, OTel, pgvector, Qdrant, MCP/A2A SDKs) not re-verified | Licence mistakes are costly | Phase 1 licence gate | OC |
| G-07 | Gate thresholds are **uncalibrated defaults** | Too strict blocks everything; too lax certifies bad agents | Phase 7 calibration; formal policy change path | HO + CTO |
| G-08 | bagalsharad modules **not executed** by me (README claims unverified) | Alpha code may be defective | Phase 3: run its tests before vendoring; keep only what passes review | OC |
| G-09 | Throughput/concurrency/soak/DR **cannot be validated** on free tier | Scale claims would be false | Phase 10 on prod-grade infra; report as not validated otherwise | CTO |
| G-10 | Sandbox T1/T2 unavailable on Render free/Termux | Tool authoring, code execution, Import lane disabled | Provision a Linux/KVM host | HO |
| G-11 | Neon + connection pooling vs per-transaction tenant setting | Session-level `SET` is unsafe with transaction pooling | Use `SET LOCAL`/`set_config(..., true)` inside each transaction; test through the pooler; Neon not tested here | OC |
| G-12 | Privacy/legal review (e.g., India's DPDP Act 2023, GDPR for EU tenants, data residency, retention) not performed | Compliance exposure | Legal review before pilot with real personal data | HO |
| G-13 | UI conventions unknown (design system, router) | UI plan is semantic only | Phase 1 + Phase 8 | OC |
| G-14 | Real-model QA cost not estimated | Budget surprise | Phase 7 measurement; caps | HO |

## B. Risks

| ID | Risk | L | I | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|---|
| R-01 | Governance stubs ⇒ Factory built on sand | Med | High | Stop-the-line; implement minimal *authoritative* adapter in ZONATA core (not Factory) with owner approval | Phase-1 negative tests fail | HO |
| R-02 | Second authority created by accident | Low | High | Ports only; code review rule: no approval/audit tables in `af_*`; CI check | New table named *approval*/*audit* | OC |
| R-03 | Prompt injection residual risk (cannot be eliminated) | High | High | Defence in depth (§7 Security); deterministic authz per call; egress allowlists; approval for impactful actions; canary evals in prod | Blocked ungranted calls rising | SEC |
| R-04 | LLM-judge unreliability / gaming | Med | Med | Programmatic assertions first; judge ≠ agent model; human sampling; dataset rotation | Judge–human disagreement > 10 % | CTO |
| R-05 | Certification theatre (passing weak tests) | Med | High | Calibration with bad references; held-out sets; min cases; Wilson floors; red-team corpus growth | Production incidents on certified agents | SEC |
| R-06 | Alpha dependency quality (vendored code) | Med | Med | Vendor only reviewed files with tests; pin commit; NOTICE; no runtime dependency | Defects in vendored modules | OC |
| R-07 | MinIO archived (no patches) | High | Med | Port + migrate to maintained S3 target | CVE announced | CTO |
| R-08 | Vault BSL / licensing exposure | Med | Med | Legal review; test OpenBao in CI | Legal flag | HO |
| R-09 | promptfoo governance change | Low | Low | Optional/pinned; datasets portable | Licence change | CTO |
| R-10 | Free-tier cold starts break long jobs | High | Med | Durable stage log; resume; keep-alive not relied on; workers resumable | Jobs stuck `LOST` | OC |
| R-11 | Cost runaway (LLM) | Med | High | Estimates, reservation, hard stops, per-agent caps | Spend > 80 % budget | HO |
| R-12 | Approval fatigue ⇒ rubber stamps | Med | High | Concise approval payload with permission diff; R3 dual control; rate caps; audit of approval durations | Median decision < 20 s on R2/R3 | HO |
| R-13 | Tenant leakage via shared infra (vector store, cache, checkpoints, logs) | Low | High | Tenant-keyed namespaces; canary probes in every QA; RLS | Canary hit | SEC |
| R-14 | Template poisoning / propagation | Low | High | Review + signing; no auto-propagation; template test pack | Unreviewed template present | SEC |
| R-15 | Sandbox escape (when enabled) | Low | High | T2 microVM for untrusted code; no secrets; egress proxy; patching; external review | Anomalous host activity | SEC |
| R-16 | Scope creep ("perfect everything" at once) | High | Med | 10 gated phases; MVP = Phases 1–4 + 7 for R0/R1 single agents | Phase slip > 50 % | HO |
| R-17 | Signing-key compromise | Low | High | Key in Vault/OpenBao (transit); rotation; revocation list; verification at load | Unexpected signatures | SEC |
| R-18 | Ledger tamper-evidence weaker than assumed | Med | High | Phase-1 tamper test; export Merkle roots off-DB; restrict DB roles | Tamper test passes undetected | SEC |
| R-19 | Existing workforce regression | Low | High | Additive migrations; baseline suite gate (AT-22); feature flag | Baseline diff | OC |
| R-20 | LLM role output drift when providers update models | Med | Med | Pin profiles; golden tests; recertification on profile change | Gate pass-rate shifts | CTO |
| R-21 | Over-promising capability to employees ("any agent, instantly") | Med | Med | Honest estimates; plain-language limits; tiers visible | Complaints | HO |

## C. External dependencies

LLM provider(s) via ZONATA model gateway · Postgres (Neon) · optional Temporal cluster · S3-compatible store · Vault/OpenBao · Keycloak/OpenFGA · NATS · Langfuse/OTel · a Linux/KVM host for sandboxes (optional) · GitHub access for the audit.

## D. Decisions that need a human (summary of gates)

D1 audit acceptance · D2 governance binding approach if stubs found · Vault vs OpenBao · MinIO replacement · enabling sandboxes/Import lane · gate policy v1.0.0 and later changes · platform-global template publication · quota defaults · external-model use for confidential data · pilot go/no-go (D10).
