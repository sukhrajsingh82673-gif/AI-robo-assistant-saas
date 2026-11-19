# Project Memory: ZONATA Agent Factory

## Environment
- **Platform:** Android / Termux (Linux ARM64, Sovereign T0 Mode)
- **Active Workspace:** `/data/data/com.termux/files/home/AI-robo-assistant-saas`
- **Git Branch:** `agent-factory/implementation`
- **Remote:** `origin` (`https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git`)
- **API Version:** `/api/v8/agent-factory/` (highest active API version)

## Architectural Decisions & Principles
- **Declarative T0 Compilation:** 100% pure-Python AST parsing and compilation without external Docker/microVM dependencies.
- **Honest Sandbox Negotiation:** MicroVM / Docker sandboxes (T1–T3) unavailable on ARM64 Termux host are honestly rejected with `AF-SANDBOX-UNAVAILABLE`.
- **Evidence-Before-Effect Invariant:** All 24 `af_*` database state transitions, builds, and releases require prior recording in the immutable Merkle `EvidenceLedger` before side effects take place.
- **Dual Anti-Self-Approval Enforcement:** Enforced by both API router and database triggers on `af_release` (AT-10).
- **Two-Phase Atomic Team Publishing:** Rollback on partial failure ensures zero half-deployed teams (AT-16).
- **Pointer-Switch Rollback:** Active versions can be cleanly rolled back to certified ancestors; uncertified/withdrawn versions are rejected (AT-17).
- **Rapid Suspension:** Immediate halt within $\le 5$s with token revocation via `AuthorityPort` (AT-18).
- **Autonomous Worker Recovery:** Heartbeat leases with automatic stale job reaping (`LOST` status) and checkpoint resumption (AT-08, AT-19).

## Completed Milestones (All 10 Phases Complete & Verified)

1. **Phase 1: Read-Only Repository Audit**
   - 4 live governance probes passed.
   - Comprehensive documentation under `docs/agent-factory/audit/`.
2. **Phase 2: Foundation & Governance**
   - Applied idempotent 24-table migrations `migrations/{sqlite,pg}/0013_agent_factory_core.sql`.
   - Ports, adapters (`agent_factory/adapters/zonata/`, `agent_factory/adapters/fakes/`), and `transition()` helper.
3. **Phase 3: Templates & Requirement Engine**
   - Spec validator, deterministic permission calculator, 6 starter templates, requirement analyst.
4. **Phase 4: Single-Agent Manufacturing**
   - `SpecCompiler` with wrapping invariants, `GovernedCall`, detached Ed25519 `ArtifactSigner`, `ManufacturingPipeline`.
5. **Phase 5: Multi-Agent & Batch**
   - Kahn's cycle-detected DAG planner, wave-based build orchestrator, atomic quotas (`af_quota_usage`), team manifest compilation.
6. **Phase 6: Capabilities & Sandboxing**
   - MCP Gateway with tool description hash pinning, A2A narrowing delegation `min(delegator, delegatee)`, Browser SSRF guard, quarantined OSS importer.
7. **Phase 7: Automated QA & Certification Engine**
   - Gates G00–G13 with Wilson score lower bounds, multi-suite QA runner, signed certification bundle sealing.
8. **Phase 8: Registry, Release, Provisioning & Marketplace**
   - ReleaseManager with anti-self-approval and atomic team publishing, WorkforceProvisioner, web UI integration.
9. **Phase 9: Monitoring, Upgrades, Lifecycle & Worker Daemon**
   - MonitoringService, LifecycleManager (G10 upgrade regression check, $\le 5$s suspension, resume, retirement), FactoryWorker daemon.
10. **Phase 10: Enterprise Acceptance & Pilot Readiness**
    - Full acceptance suite (AT-01 through AT-22) executed and passing (84/84 tests).
    - Existing test suites verified with zero regressions:
      - `npm run test:ui`: 1 passed.
      - `npm run test:assistant`: 41 contract + 29 jsdom + 12 e2e + 79 python passed.
      - `npm run test:company`: 124 python + 8 subtests + 50 UI checks passed.
    - Authoritative runbook created: `docs/runbooks/AGENT_FACTORY_OPERATIONS.md`.
    - Final Pilot Readiness Report: `docs/agent-factory/evidence/phase-10/FINAL_READINESS_REPORT.md`.

## System Status
- **Agent Factory Core:** Fully operational in Sovereign T0 Mode.
- **Verification Score:** 420+ automated tests passing across the entire repository.
- **Pilot Readiness:** GO.
