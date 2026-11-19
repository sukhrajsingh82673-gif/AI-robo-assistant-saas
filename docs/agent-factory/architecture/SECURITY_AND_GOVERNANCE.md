# SECURITY_AND_GOVERNANCE — ZONATA authority integration and threat model

> Existing control names (AuthorityGateway, PolicyEngine, …) are the owner's; their real behaviour is **unverified** until Phase 1. Where the Factory depends on a control that proves absent, the control becomes a **blocking prerequisite** (see Gap register G-01..G-04), not something the Factory quietly re-implements as a second authority.

## 1. Governance path: every action, every time

```
request ─► KillSwitchMatrix ─► AuthorityGateway.authorize ─► PolicyEngine (Constitution rules) ─► OpenFGA relation check
        ─► [REQUIRE_APPROVAL → ApprovalEngine → decision]  ─► DLP / data-class check ─► Vault (secret by reference) ─► EXECUTE
        ─► EvidenceLedger.append (before success is returned) ─► telemetry
```

| Action class | Action name | Controls on the path | Approval |
|---|---|---|---|
| Submit request | `factory.request.create` | kill switch, authorize, quota, DLP on NL (reject secrets), ledger | none |
| Analyse / design | `factory.request.analyze`, `factory.design.approve` | authorize; design approve: approver ≠ requester | R2/R3 |
| Start build | `factory.build.start` | kill switch (batch/tenant/factory), budget reservation, authorize | none (budget by policy) |
| Bind tool / MCP / data | `factory.tool.bind` | authorize; registry check; permission calculator; hash-pinned tool descriptions | If grant tier > auto-grant tier |
| Mint agent identity | `factory.principal.mint` | authorize; identity layer creates `agent` principal; FGA tuples | none (service) |
| Run sandboxed code | `factory.sandbox.run` | authorize; sandbox broker enforces profile; no secrets | R3 for new tool packages |
| Certify | `factory.cert.issue` | deterministic evaluator; **no** authorize bypass; ledger | none |
| Release | `factory.release.submit/decide/publish` | authorize; ApprovalEngine; approver disjointness; cert hash binding | per matrix |
| Assign | `factory.agent.assign` | authorize; same tenant/company; use-right on employee only | by tier |
| Suspend / kill | `factory.agent.suspend`, `factory.kill` | allowed to AI CEO, owner, Security, Monitoring (zero-tolerance rules) | none (fast path) |
| Retire / rollback / upgrade | `factory.agent.retire/rollback/upgrade` | authorize; ledger; upgrades = new version | rollback: none if certified; retire: owner |
| **Production tool call by an agent** | `agent.tool.call` | kill switch, **per-call** authorize with agent principal, DLP in/out, rate/budget, ledger | `REQUIRE_APPROVAL` → LangGraph `interrupt` |
| **Production delegation (A2A)** | `agent.delegate` | per-call authorize; effective = min(delegator, delegatee); depth/cycle check | by tier |

## 2. The thirteen mandatory requirements → mechanism → proof

| # | Requirement | Mechanism | Proof (test) |
|---|---|---|---|
| 1 | Unique identity per agent | `IdentityPort.mint_agent_principal`; `af_agent.agent_principal_id UNIQUE` | AT-01, AT-08 (no double mint) |
| 2 | Tenant-bound ownership | `tenant_id` on every row + RLS + per-job token; principal carries tenant | AT-12; `001_verify.sql` (RLS checks: 3 PASS) |
| 3 | Least privilege | Permission calculator intersection; default deny | G07, AT-11 |
| 4 | No self-granted permissions | `permission_profile` frozen after BUILDING (trigger, verified); no agent write relation on `af_*`; delegation narrows | AT-11; `001_verify.sql` "self-grant" PASS |
| 5 | No unrestricted tool access | Tools only via bindings; MCP via gateway allowlist; network allowlist | AT-13, G04 |
| 6 | No direct production DB access | Only governed read-only views as `database_views`; DB credentials never given to agents or workers | AT-13 variant; G08 |
| 7 | Secrets never in prompts/code | Spec validator rejects credential-like strings; gitleaks; secrets by `secret_refs` resolved at call time; DLP on model I/O | G01, G02, G05 `secret_exfiltration` zero-tolerance |
| 8 | Protected operations via AuthorityGateway | `GovernedCall` wrapper around every outward node; runtime refuses nodes without it | AT-11/13; code-level check that the compiler has no un-wrapped external node |
| 9 | Sensitive operations follow ApprovalEngine rules | `approval_matrix`; `REQUIRE_APPROVAL` → interrupt | AT-10, AT-09 |
| 10 | Lifecycle evidence | `af_lifecycle_event.evidence_ledger_id NOT NULL`; ledger append precedes success | AT-14 |
| 11 | No policy bypass via delegation | effective = min(…); policy evaluated for delegatee as actor *and* originating principal | AT-11c, AT-21, G07 |
| 12 | Kill switches | Scopes `agent`, `team`, `batch`, `tenant`, `factory`; checked at API, per workflow step, per runtime call | AT-18, AT-19 variant, kill test in Phase 9 |
| 13 | Cross-tenant prevention tested | RLS + OpenFGA + per-tenant object prefixes + canary probes in QA gate G06 | AT-12 |

## 3. Identity and relation model (proposal — adapt to the existing OpenFGA model)

```
type tenant
  relations  define member: [user, employee]   define admin: [user]
type company
  relations  define tenant: [tenant]  define owner: [user]  define ceo: [ai_ceo]
type employee                         # AI employee (existing)
  relations  define company: [company]  define can_use_agent: [agent]       # employees may use agents
type agent                            # NEW principal type (agents are never users/employees)
  relations  define company: [company]  define owner: [employee, user]
             define may_call_tool: [tool_scope]                              # granted ONLY by factory.integration service on a certified version
             # deliberately NO relation allowing agent -> employee use
type factory_object                   # request, batch, version, release, certification
  relations  define requester: [employee, user, assistant]
             define observer: [assistant, user, employee]                    # read-only (co-worker assistant)
             define can_decide_release: (approver from matrix) but not requester     # `but not` = set difference
             define can_certify: [service:factory.certification_manager]
             define can_waive_finding: [security_approver]
```

Principle: *requester ∩ approver = ∅* is expressed in the model **and** in service code **and** in the DB (defence in depth, per brief rule 7).

## 4. Evidence design

| Aspect | Design |
|---|---|
| Source of truth | The **existing EvidenceLedger** (append-only, SHA-256 hash chain + Merkle). `af_lifecycle_event` is a projection and must reference a ledger id. |
| Event envelope | `{event, tenant, company, subject_kind, subject_id, actor, from_state, to_state, decision?, hashes{spec,package,bundle,dataset,prompt,policy}, model_profile, correlation_id, ts}` — **hashes, not content**; no PII/secrets |
| Canonicalisation | RFC 8785-style canonical JSON (sorted keys, no insignificant whitespace, UTF-8) before hashing/signing |
| Signing | Ed25519 detached signature over canonical manifest (package, team manifest, certification bundle); `signing_key_id` stored; keys from `SecretsPort`; rotation: new key id, old keys retained for verification; revoked keys listed |
| Verification points | Registry on publish; **runtime on load** (refuse unsigned/modified); auditors via `GET /evidence/...` (Merkle proof + chain) |
| Honest limit | Signatures prove integrity and origin *within ZONATA's key custody*. They do not prove the model behaves well; that is QA's job. Tamper-evidence of the ledger is only as strong as its storage and key protection (see Gap register). |

## 5. Threat model

Scope: attackers = malicious/compromised employee or tenant user, injected content (web, documents, MCP tool output, imported OSS code), compromised dependency, malicious template/agent, curious neighbour tenant, over-eager insider, and **the LLM roles themselves** (treated as untrusted proposers). Trust boundaries are the edges in `TARGET_ARCHITECTURE.md` §2. References: STRIDE; OWASP Top 10 for LLM Applications and for agentic applications `[KNOWLEDGE]`; MITRE ATLAS `[KNOWLEDGE]`.

| ID | Threat | Vector | Impact | Mitigations | Verified by |
|---|---|---|---|---|---|
| T01 | **Prompt injection (direct)** via request text steering design roles | NL request | Over-privileged design, instruction leakage | Roles have no tools; schema-bound outputs; permission calculator is deterministic; intersection with requester authority | AT-01 variants, G05 |
| T02 | **Indirect injection** via web page/doc/tool output | Agent browses/reads | Agent calls ungranted tools, exfiltrates | Untrusted-data framing; per-call AuthorityGateway; egress allowlist; DLP out; tool-output length/format limits; no tool chaining outside spec workflow | G05 (corpus ≥100 for R2/R3), AT-09 |
| T03 | **Tool poisoning / rug pull** (MCP description changes) | MCP server | Hidden instructions | Description hash pinned at binding; change ⇒ binding suspended + re-approval | AT-13 |
| T04 | **Confused deputy** (agent uses employee/supervisor rights) | Delegation | Privilege escalation | Delegation = min(); actor+origin policy evaluation; agents have no employee relations | AT-11c, G07 |
| T05 | **Self-granting permissions** | Agent/Developer role writes profile | Escalation | Calculator sole writer; frozen after BUILDING; FGA tuples written only by integration service on certified versions | `001_verify` PASS, AT-11 |
| T06 | **Self-approval / collusion of roles** | Same principal plays two roles | Bypass QA | Distinct service principals; DB triggers; FGA set difference | AT-10; `001_verify` PASS |
| T07 | **Cross-tenant data access** | IDs guessing, shared caches, prompts, vector store, A2A | Data breach | RLS (FORCE) + per-job tenant token; object prefixes; 404-not-403; tenant-keyed cache/checkpoints; canary probes | AT-12, G06 |
| T08 | **Secret exposure** in prompts/specs/logs/artifacts | Developer role, tool output | Credential theft | Validator + gitleaks; refs-only; DLP; log redaction; workers hold no prod secrets | G01/G02/G05 |
| T09 | **Malicious generated/imported code** | Tool packages, OSS import | RCE, exfil, lateral movement | T0 default (no code); code only in T1/T2 sandbox; egress allowlist; no secrets; read-only FS; non-root; scanning; human approval (R3) | SB-01..SB-06 sandbox suite (Phase 6) |
| T10 | **Supply chain** (deps, images, templates) | Compromised package | Backdoor | Pinned versions + hashes; pip-audit/OSV; SBOM; signed templates; scanner pinned by digest; licence gate | Phase 1 gate; G02 |
| T11 | **Resource exhaustion / cost runaway** | Loops, huge fan-out | DoS, spend | Limits per spec; quotas; budgets; sandbox cgroups; max agents/batch; queue fairness | AT-20 |
| T12 | **Artifact tampering / substitution** | Storage compromise | Run altered agent | Content addressing + signatures verified at runtime; approval bound to cert hash | AT-15 |
| T13 | **Ledger tampering/deletion** | Insider with DB access | Repudiation | Append-only + hash chain/Merkle; periodic root export (outside primary DB); DB role without UPDATE/DELETE on ledger | AT-14 |
| T14 | **Kill-switch evasion** | Long-running tasks | Continued harm | Checks at API, each workflow step, each runtime call; tokens short-lived | AT-18 |
| T15 | **QA gaming / test leakage** | Builder reads datasets, overfits | False assurance | Held-out ≥30 %; dataset ownership by evaluators (FGA deny to builder); different model family for judge where available; periodic dataset rotation | G00 independence; calibration (QA doc) |
| T16 | **Judge manipulation** (LLM-as-judge) | Agent output instructs judge | Inflated scores | Prefer programmatic assertions; judge sees structured fields; judge prompt isolates output; spot-check by humans (G12) | QA doc §5 |
| T17 | **Template poisoning** | Malicious template published | Many agents compromised | Review + approval + signature; no auto-propagation; template test pack | Template lifecycle |
| T18 | **Import-lane attack** (hostile repo) | `source_url` | Sandbox escape, malware | Quarantine T2; no execution on host; licence + malware scan; convert-to-spec only; disabled if T2 absent | AT negative additions, SB-05 |
| T19 | **Memory poisoning** | Writes to long-term memory/knowledge | Persistent injection | Scoped stores; write approval for shared knowledge; provenance tags; retrieval sanitisation | Integration tests |
| T20 | **Exfiltration through allowed channel** (e.g., report email) | `report.send` | Data leak | Recipients internal-only unless approved; DLP; classification ceiling `data_classification_max` | G05 |
| T21 | **SSRF via browser/fetch** | URL redirect, internal IPs | Internal access | Egress proxy deny private ranges/metadata, redirect re-validation | browser-ssrf-core |
| T22 | **Privilege creep through upgrades** | New version adds tools | Escalation | Upgrade = new version; permission diff shown; widening ⇒ re-approval; regression gate | AT-03, G10 |
| T23 | **Insider approval fatigue** | Many approvals | Rubber-stamping | Approval payload shows permission diff, gate results, risk; rate-limited queues; R3 dual control | UI doc |
| T24 | **Model provider data exposure** | External LLM | Data leak | Privacy class → profile hard filter; restricted data only to approved/self-hosted profiles | G09/model policy |
| T25 | **Stale certification** | Policy/template/model changed | Unsafe run | Certification expiry + policy version; model-profile change ⇒ re-certify | Lifecycle stage 13 |

## 6. Sandbox and isolation decision

| Option | Isolation | Cost/complexity | Fit |
|---|---|---|---|
| **T0 — no code execution** (declarative agents + governed tools) | Strongest: nothing untrusted executes | None | **Default for all agents.** Works on free tier. |
| T1 — rootless Docker/Podman + seccomp + AppArmor + read-only FS + cgroups (+ gVisor `runsc` where available) | Process/container; shared kernel (gVisor reduces exposure) | Needs a container host | Reviewed first-party tool packages, data-analysis compute |
| T2 — microVM (Firecracker/Kata) on KVM host | Hardware virtualisation boundary | Highest; needs KVM-capable host | **Required** for model-written code, OpenHands Tool Smith, imported OSS agents |
| Managed sandbox services | Varies | External dependency | Only if self-hostable/approved; not default |

**Mandatory controls for T1/T2:** no secrets or credentials in the sandbox; network **default deny** with an allowlisting egress proxy (blocks RFC1918, link-local/metadata, DNS rebinding); non-root user, dropped capabilities, `no-new-privileges`; read-only root FS with a size-limited tmpfs workdir; CPU/memory/pids/time cgroup limits; no host mounts; ephemeral (destroyed after job); output size caps; artifact scanning before anything leaves; logs shipped out-of-band. **Honest statement:** on the current free-tier/Termux environment **T1/T2 are unavailable**, so tool authoring, code-execution capabilities and the Import lane stay disabled and `/ready` reports `sandbox_tiers_available: []`.

## 7. Prompt-injection architecture (defence in depth; no single control is relied on)

1. **Privilege separation:** design roles have no tools; runtime agents have only granted tools.
2. **Data/instruction separation:** untrusted text is wrapped and labelled; instructions never come from tool output.
3. **Deterministic authorisation** on every call, independent of model output.
4. **Egress and DLP** on both directions.
5. **Output validation** against schemas; high-risk actions require approval (`interrupt`).
6. **Continuous testing:** versioned corpora + periodic canary evals in production on held-out sets (a degradation raises an incident).

## 8. Incident rules and auto-suspension

| Event | Severity | Automatic action |
|---|---|---|
| Ungranted tool call attempted (blocked) | high | Alert; 3 in 10 min ⇒ suspend agent |
| Ungranted tool call **succeeded** (should be impossible) | critical | Immediate suspend + kill token + security incident |
| Cross-tenant canary observed | critical | Suspend all agents of the version; freeze template; page |
| Secret/DLP hit in output | critical | Suspend; quarantine logs |
| SLO breach 2 windows | medium | Mark `DEGRADED`; notify owner; propose rollback |
| Eval drift > 3 pp on canary set | medium | Propose rollback/upgrade |
| Cost > 3× cap rolling | high | Throttle then suspend |

Incident handling: Monitoring Engineer opens the incident → Security Engineer triages → AI CEO/owner decide resume/rollback/retire; every step in the ledger.

## 9. Decisions requiring human approval (non-exhaustive)

(1) Approve this architecture and the Phase-1 audit. (2) Gate policy thresholds and any change to them. (3) Vault vs OpenBao; MinIO replacement. (4) Enabling T1/T2 sandboxes and the Import lane. (5) Template publication (platform-global). (6) R2/R3 releases per matrix. (7) Waiving medium findings. (8) Raising quotas/budgets. (9) Allowing external model providers for `confidential` data. (10) Retention periods.
