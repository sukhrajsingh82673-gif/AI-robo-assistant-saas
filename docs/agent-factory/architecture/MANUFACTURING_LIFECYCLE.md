# MANUFACTURING_LIFECYCLE — employee request → production agent

**Pipeline:** Request → Requirement analysis → Architecture → Template discovery → Construction → Integration → Builder testing → Independent QA → Certification → ZONATA release approval → Provisioning → Production monitoring → Upgrade/lifecycle.

## 0. Conventions

- **Evidence event** = one append to the existing EvidenceLedger via `GovernancePort.record_evidence`; its id is stored in `af_lifecycle_event.evidence_ledger_id` (NOT NULL). Event names below are the stable contract.
- **Every stage entry** first runs: `kill_switch_active(factory|tenant|batch|agent)` → `authorize(factory.<action>)` → budget check. Any failure ends the stage (`FAILED` or `KILLED`), never "continue anyway".
- **Retry default:** 2 automatic retries for infrastructure failures (worker lost, timeout, 5xx), exponential back-off 5 s/30 s; **0 automatic retries** for policy denials, gate failures, validation failures of deterministic checks. LLM output validation: 2 re-prompts then fail.
- **Idempotency:** each stage is keyed by `(request_id, item_key, stage, attempt)`; re-running a completed stage returns the stored result.
- **Risk tier** is *computed* by the Architect + calculator from requested capabilities (highest capability tier wins), never self-declared; the template provides a floor.

## 1. Stage reference

### Stage 1 — Employee request
| | |
|---|---|
| Purpose | Capture intent for 1..N agents, a team, an upgrade, or an import |
| Responsible | Factory API (service) |
| Inputs | NL text (10–20 000 chars), `mode`, optional template ref, budget cap, release policy; authenticated principal; `Idempotency-Key` |
| Processing | Validate; authorise `factory.request.create`; quota pre-check; create `af_request`; return 202 |
| Outputs | `af_request(status=REQUESTED)`; job id |
| Validation | Schema; mode-specific fields (e.g. `target_agent_id` for upgrade); company ∈ tenant; requester role may request this mode |
| Failure conditions | 401/403/404/409/422/429; quota exceeded (`AF-QUOTA-EXCEEDED`) |
| Retry | Client-side with same idempotency key |
| Audit evidence | `factory.request.created` (principal, company, mode, text sha256 — **text itself stored in DB only, not in ledger**) |
| Security controls | Tenant from principal; body size cap; rate limit; NL treated as untrusted data |

### Stage 2 — Requirement analysis
| | |
|---|---|
| Purpose | Turn NL into a formal **Agent Requirement Specification (ARS)** and surface only essential gaps |
| Responsible | Requirement Analyst (LLM) + schema validator |
| Inputs | Request, org chart (`WorkforcePort`), employee SOP/KRA/KPI refs, tenant policy summary |
| Processing | Draft ARS: role, mission, responsibilities, expected outcomes, knowledge/tool/memory needs, performance expectations (latency, success), requested permissions, reporting relationships, cost limits, out-of-scope. Compute `open_questions`; classify each as *blocking* or *assumable*; ask only blocking ones (max 5) |
| Outputs | `af_requirement_spec` vN (+ question set) → status `CLARIFYING` or `DESIGNING` |
| Validation | ARS JSON-Schema; each responsibility has a measurable success criterion; no credentials/PII in text; requested permissions subset of requester's own authority (cannot request more than the requester may delegate) |
| Failure conditions | Unparseable request; requester lacks authority for requested capability → `REJECTED` with explanation; contradictory requirements → clarification |
| Retry | LLM: 2 re-prompts; clarification loop ≤ 3 rounds then escalate to requester's manager/AI CEO |
| Audit evidence | `factory.ars.created`(version, sha256, role prompt hash, model profile) |
| Security controls | Role has no tools; input delimited as data; output schema-bound; requester-authority intersection |

### Stage 3 — Architecture design
| | |
|---|---|
| Purpose | Decide single/supervisor/sequential/parallel/hierarchical/dynamic delegation and the agent set |
| Responsible | Agent Architect (LLM) + planner (`batch_scheduler.plan`) + permission calculator |
| Inputs | ARS vN, template catalogue summary, quotas |
| Processing | Produce architecture spec: agents, roles, workflow type each, communication contracts, dependency graph (`build_requires`, `runtime_delegates_to`, `reports_to`), shared knowledge plan, risk tier per agent, estimate (tokens, cost, wall time, sandbox seconds) |
| Outputs | Architecture spec + `af_batch` (manifest, `PLANNED`) + `af_batch_item`s |
| Validation | DAG acyclic; delegation acyclic; single supervisor per agent; depth ≤ policy; agents ≤ 500; estimate ≤ budget; risk tier computed |
| Failure conditions | `AF-DAG-INVALID`; over budget/quota; over-privileged split |
| Retry | LLM 2 re-prompts with validator errors |
| Audit evidence | `factory.architecture.proposed`, `factory.batch.planned`(manifest_sha256) |
| Security controls | Design cannot add capabilities not in the ARS; R2/R3 requires `factory.design.approve` by someone other than the requester |

### Stage 4 — Template discovery
| | |
|---|---|
| Purpose | Reuse before building |
| Responsible | Template Engineer (service matching + LLM explanation) |
| Inputs | Architecture items |
| Processing | Search APPROVED template versions and **certified** agents (same tenant/global) by category, capability set, risk ceiling, compat; rank; deterministic compat check (`spec_api`, `capability_api`, `runtime`, `gate_policy`); output chosen template or `from_scratch` with reasons |
| Outputs | Per-item template resolution (`name@semver` or none) |
| Validation | Template risk ceiling ≥ item risk; `forbidden_capabilities` ∩ requested = ∅; template not DEPRECATED/WITHDRAWN |
| Failure conditions | No compatible template → from-scratch path (not a failure); only incompatible → from-scratch |
| Retry | none (deterministic) |
| Audit evidence | `factory.template.resolved` |
| Security controls | Read-only; tenant-local templates cannot leak across tenants (RLS) |

### Stage 5 — Agent construction
| | |
|---|---|
| Purpose | Produce the complete operational package as data |
| Responsible | Agent Developer (LLM) + spec validator + **permission calculator** (deterministic) |
| Inputs | ARS, architecture item, template |
| Processing | Mint identity candidate (slug, **agent principal minted only at integration**); render spec: system instructions, responsibilities, model requirements, workflow, memory policy, knowledge config, I/O contracts, limits, error handling, observability config, builder test cases; compute `permission_profile` = request ∩ template ceiling ∩ requester authority ∩ tenant policy ∩ AI CEO policy ∩ constitution |
| Outputs | `af_agent_version(status=BUILDING)` with `spec`, `capability_profile`, `permission_profile`, `risk_tier` |
| Validation | **G01**: JSON-Schema + semantic: no credential-like strings (entropy + patterns + secret-scan), no `may_use_employees=true`, `limits` present, every tool in permissions exists in registry, instruction length caps, no URLs with tokens |
| Failure conditions | Validation errors; permission calculator reduces request (recorded as *reduction notes*; if reduction breaks a mandatory responsibility → `CLARIFYING` with requester) |
| Retry | LLM 2 re-prompts |
| Audit evidence | `factory.version.built`(spec_sha256, template version, prompt hashes, reduction notes) |
| Security controls | LLM cannot write `permission_profile` (column guarded by service role + frozen after BUILDING); secrets referenced by name only |

### Stage 6 — Integration
| | |
|---|---|
| Purpose | Bind approved tools/services; create runtime resources in *staging* |
| Responsible | Integration Engineer (service + LLM proposals) |
| Inputs | Spec, registry |
| Processing | Resolve each tool/MCP/A2A/knowledge/memory/database-view ref to registered objects; **pin MCP tool descriptions by hash** (defence against tool poisoning); create `af_tool_binding` with scopes + constraints; request approvals for grants above auto-grant (`REQUIRE_APPROVAL`); mint agent principal (`IdentityPort`), write FGA tuples (agent → tool scopes only); create memory store; set up knowledge ACLs; package; **scan** (gitleaks, Bandit/Ruff for code-bearing parts, pip-audit, Syft); store package artifact, compute sha256 |
| Outputs | Bindings, staging runtime, package artifact, SBOM (if code), scan reports → `BUILT` |
| Validation | Every binding ⊆ permission_profile; no direct production DB (only governed views); network allowlist hosts valid; scan: 0 critical/high |
| Failure conditions | Unregistered tool; denied grant; scan finding ≥ high; sandbox required but unavailable (`AF-SANDBOX-UNAVAILABLE`) |
| Retry | Infra retries; scan failures are **not** retried—fix in a new attempt of Stage 5 |
| Audit evidence | `factory.binding.created`, `factory.principal.minted`, `factory.package.built`(sha256), `factory.scan.completed` |
| Security controls | Secrets resolved at runtime via `SecretsPort`; worker has no prod credentials; staging isolation; artifact tenant-prefixed |

### Stage 7 — Builder testing
| | |
|---|---|
| Purpose | Fast feedback for the builder; **never counts toward certification** |
| Responsible | Agent Developer's own cases (`tests.author_cases`) + platform smoke tests |
| Inputs | Staged agent |
| Processing | Run in staging with mock data; mock model allowed here (labelled `phase=builder_unit`); tool-call plumbing, permission denial checks, schema conformance, failure injection |
| Outputs | `af_eval_run(phase=builder_unit)` + results |
| Validation | Mandatory builder cases pass; else back to Stage 5 (≤3 loops) |
| Failure conditions | Plumbing errors; spec bug |
| Retry | ≤3 build–test loops |
| Audit evidence | `factory.test.builder_completed` |
| Security controls | Mock data only; staging tenant namespace; egress blocked |

### Stage 8 — Independent QA
| | |
|---|---|
| Purpose | Test the *complete agent against its original requirements* by parties who did not build it |
| Responsible | QA Director (service); Functional Test Engineer, Security Engineer, Performance Engineer |
| Inputs | Staged agent version, ARS, independent datasets (≥30 % held-out the builder role can never read), real model profile |
| Processing | Suites: functional, security (injection, leakage, tool abuse, privilege escalation, delegation bypass, secrets), tenant-isolation (canary records across memory/knowledge/tools/A2A/artifacts), integration (MCP, DB view, knowledge, memory isolation, A2A, supervisor delegation), performance (latency, throughput, reliability, tokens, cost), regression vs previous certified version (upgrades). Repeats per tier (3 or 5); per-case majority vote; Wilson lower bound computed |
| Outputs | `af_eval_run(phase=independent_qa)` ×suites, `af_eval_result`, `af_finding`s |
| Validation | DB-enforced evaluator ≠ builder; dataset sha recorded; model profile not mock |
| Failure conditions | Suite error (infra) vs suite fail (agent) are distinct; infra error ⇒ rerun suite, not pass |
| Retry | Infra retry ×2; agent failures → back to Stage 5 as a **new attempt/version**; max 3 QA cycles then escalate |
| Audit evidence | `factory.qa.completed`(per suite: dataset sha, n, pass count, evaluator) |
| Security controls | Attack runs only in staging sandbox with canary data; red-team corpus versioned; evaluator write access to datasets only |

### Stage 9 — Certification
| | |
|---|---|
| Purpose | Decide mechanically whether release criteria are met and freeze the evidence |
| Responsible | Certification Manager (deterministic) |
| Inputs | Evidence from Stages 6–8; `gate_policy.yaml` (version pinned) |
| Processing | `evaluate(tier, evidence)`; assemble **certification bundle** (spec, package hash, SBOM, scan reports, eval reports, gate results, prompt hashes, model profiles, dataset hashes); canonicalise; Ed25519-sign; store; insert `af_certification` (immutable) with ledger reference |
| Outputs | Certification (pass/fail with per-gate results) |
| Validation | G00–G13 per policy; **mock evidence cannot satisfy gates**; critical/high open finding blocks |
| Failure conditions | Any mandatory gate fails → version `FAILED_QA`; no release path |
| Retry | None — re-evaluation only on new evidence (new version/attempt) |
| Audit evidence | `factory.certification.issued`(gate_results hash, bundle sha, policy version, Merkle root) |
| Security controls | Policy file is read-only to the Factory; signing key from `SecretsPort`; verdict reproducible from the bundle offline |

### Stage 10 — ZONATA release approval
| | |
|---|---|
| Purpose | Sovereign authorisation of production use |
| Responsible | Release Manager (submit) → **ApprovalEngine / AI CEO / human owner / security approver** (decide) |
| Inputs | Certification, risk tier, autonomy setting |
| Processing | Create `af_release(PENDING)` and an ApprovalEngine request with the certification summary; approvers per `approval_matrix` (R0 policy-auto, R1 AI CEO, R2 AI CEO + human, R3 AI CEO + human + security, dual control); autonomy mode may only tighten; wait via signal/interrupt |
| Outputs | Decision `APPROVED/REJECTED/EXPIRED` with `approval_id`, `decided_by` |
| Validation | Approver ∉ {requester, builder, Factory Director}; certification not expired and policy version current; DB trigger re-checks |
| Failure conditions | Rejected; expired (default 7 days); policy changed → re-certify |
| Retry | Resubmit after changes (new version) |
| Audit evidence | `factory.release.submitted`, `factory.release.decided` (approver, approval_id) |
| Security controls | Approval is bound to the certification **hash**; a different package cannot ride on an old approval |

### Stage 11 — Provisioning
| | |
|---|---|
| Purpose | Register, deploy and assign the approved agent |
| Responsible | Release Manager + Provisioner |
| Inputs | Approved release |
| Processing | Verify signature + hashes; set version `PUBLISHED`; (team: **atomic** transaction over all members, see Multi-Agent doc); deploy to runtime channel (`staging`→`canary`→`production` per tier; R2/R3 default canary 10 % when replacing a version); activate FGA tuples and tokens; create memory/knowledge scopes; assign to employee/department/team/assistant via `WorkforcePort`; notify requester |
| Outputs | `af_agent.lifecycle=ACTIVE`, `af_runtime_instance`, `af_assignment` |
| Validation | Signature valid; approval valid; assignment target in same tenant/company; assignee authorised to *use* (employees use agents; agents never use employees) |
| Failure conditions | Deploy failure → automatic rollback of the publish transaction; partial team publish impossible |
| Retry | ×2 infra; then the publish transaction is rolled back, the version stays `APPROVED`, and an alert is raised |
| Audit evidence | `factory.agent.published`, `factory.agent.assigned` |
| Security controls | Runtime refuses unsigned/modified packages; least-privilege tokens with TTL; kill switch wired |

### Stage 12 — Production monitoring
| | |
|---|---|
| Purpose | Detect degradation, abuse, cost drift; capture feedback |
| Responsible | Monitoring Engineer (collectors service + analyst LLM for proposals) |
| Inputs | OTel traces/metrics, Langfuse scores, tool-failure logs, feedback, escalations, security events |
| Processing | SLO engine: success rate, eval score drift (periodic canary evals on held-out set), tool failures, latency p50/p95, runtime errors, tokens, model cost, resource use, escalations, incidents, version changes. Incident rules (see Security doc) |
| Outputs | `af_agent.monitoring_status`, alerts, improvement proposals |
| Validation | Metrics tenant-scoped; no raw content in telemetry unless `capture_content` allows |
| Failure conditions | Collector outage → `UNMONITORED` status shown (never "healthy by default") |
| Retry | continuous |
| Audit evidence | `factory.monitoring.incident`, `factory.agent.suspended` (if triggered) |
| Security controls | Zero-tolerance events auto-suspend; analyst proposals cannot mutate anything |

### Stage 13 — Upgrade and lifecycle management
| | |
|---|---|
| Purpose | Controlled change after release |
| Responsible | Factory Director (workflow) with the same roles |
| Inputs | Upgrade/config/tool/template/model change request, or monitoring proposal |
| Processing | **Always a new version** (parent link). Re-run Stages 5–11 as needed: material change (new capability, widened permission, new tool, template major, model profile change, instruction change) ⇒ full QA + certification; non-material (copy edit in docs) ⇒ policy-defined light path (still signed, still evidenced). Version comparison view (spec diff + metric delta). **Rollback:** pointer switch to previous certified version; **Suspend/Resume**; **Retire** (revoke principal, tokens, tool bindings; memory purge/retention per policy) |
| Outputs | New `af_agent_version` or lifecycle transition |
| Validation | G10 regression: ≤3 pp drop, 0 new security failures; rollback only to certified non-withdrawn versions |
| Failure conditions | Regression; certification expired; template withdrawn → agents flagged for upgrade |
| Retry | as above |
| Audit evidence | `factory.version.created`, `factory.agent.rolled_back`, `factory.agent.suspended`, `factory.agent.retired` |
| Security controls | **Production agents never rewrite themselves**; template changes never propagate automatically — each dependent agent needs its own new version and certification |

## 2. Lanes

| Lane | Trigger | Differences |
|---|---|---|
| **Standard** | `single/multi/team/hierarchy/from_template/from_scratch` | Stages 1–13 as above |
| **Upgrade** | `mode=upgrade` | Starts from previous version; Stage 2 diff-only ARS; Stage 8 includes regression (G10) |
| **Import (quarantined)** | `mode=import`, `source_url` (owner's "download an open-source agent from GitHub" flow) | Stage 0 **Quarantine**: fetch in an isolated environment (T2) with no secrets/egress except the allowlisted source; license check (permissive only unless approved); static scan; SBOM; *never executed on the host*; **convert to `zonata.agent/v1`** (tool code becomes a reviewed *tool package* run only in T1/T2 sandbox, human-approved). If the conversion cannot be expressed as spec + sandboxed tool package → rejected. Then Stages 5–13. Disabled when T2 is unavailable. |

## 3. Failure-mode summary

`LOST worker` → resume from last durable stage · `Validation fail` → fail-stage, loop or escalate · `Gate fail` → no release; new version required · `Kill` → cancel everywhere + evidence · `Budget hit` → hard stop · `Partial team failure` → see Multi-Agent doc · `Approver unavailable` → expire after 7 days, never auto-approve.
