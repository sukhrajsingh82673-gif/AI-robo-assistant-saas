# Phase 7 Completion Report: Automated QA & Certification Engine

**Execution Timestamp:** 2026-11-19
**Host Environment:** Linux ARM64 (Android / Termux)
**Status:** COMPLETED & VERIFIED

---

## 1. Summary of Deliverables

1. **Gate Evaluator (`agent_factory/cert/gates.py`):**
   - Lifts `reference/qa/gate_eval.py` and `gate_policy.yaml` unchanged in core logic.
   - Evaluates deterministic Gates G00 through G13:
     - **G00:** Real model profile verification (mock/fake models forbidden for certification) & evaluator independence (evaluator != builder, held-out fraction $\ge 30\%$).
     - **G01:** Declarative spec validity against `zonata.agent/v1`.
     - **G02:** Static vulnerability scan (0 critical, 0 high, 0 unwaived medium).
     - **G03:** Functional test suites & Wilson lower bound score floor.
     - **G04:** Tool discipline (0 ungranted tool calls, minimum selection rate).
     - **G05:** Security suite (100% mandatory pass rate, minimum injection corpus, 0 zero-tolerance hits).
     - **G06:** Tenant isolation (cross-tenant access attempts denied).
     - **G07:** Permission integrity (privilege escalation attempts blocked).
     - **G08:** Integration tests & Wilson floor.
     - **G09:** Performance SLOs (error rate $\le 1\%$, p95 latency within SLO, median cost within cap).
     - **G10:** Upgrade regression bounds (max performance drop $\le 2.0$ pp, 0 new security failures).
     - **G11:** Provenance verification.
     - **G12:** Human review (dual control enforced for R3 agents).
     - **G13:** Team integration (acyclic, single-supervisor reporting).

2. **Automated QA Runner (`agent_factory/qa/runner.py`):**
   - Coordinates multi-suite test execution and evidence assembly.
   - Implements **dataset calibration** against reference known-good and known-bad agents (AT-21).

3. **Certification Bundle Manager (`agent_factory/cert/bundle.py`):**
   - Packages manifest + gate results + eval summaries into canonical JSON.
   - Generates detached Ed25519 signatures over canonical payload.
   - Seals certification record in `af_certification`, artifact in `af_artifact`, and appends to `EvidenceLedger`.
   - Implements bundle verification and tamper detection (AT-15).

4. **QA & Certification API Routes (`agent_factory/api/routes.py`):**
   - Route 19: `GET /agent-versions/{id}/evaluations`
   - Route 20: `GET /agent-versions/{id}/findings`
   - Route 21: `POST /findings/{id}/waive` (medium/low only; critical/high cannot be waived $\rightarrow$ 409 `AF-FINDING-NOT-WAIVABLE`).
   - Route 22: `GET /agent-versions/{id}/certification`
   - Route 22B: `POST /agent-versions/{id}/certify` (runs QA + gates + seals bundle; rejects failing packages with 422 `AF-GATE-FAILED`).

5. **Acceptance Tests Implemented & Verified:**
   - **AT-09:** Rejection of agents failing mandatory QA criteria.
   - **AT-15:** Packaging, sealing, and verification of signed certification bundles; detection of manifest and signature tampering.
   - **AT-21:** Dataset calibration against known-good and known-bad agents.

---

## 2. Real Test Execution Evidence

```
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
collected 74 items

tests/agent_factory/test_a2a_gateway.py ...                              [  4%]
tests/agent_factory/test_at01_single_agent.py .                          [  5%]
tests/agent_factory/test_at04_at05_multi_agent_team.py .                 [  6%]
tests/agent_factory/test_at06_at07_batch_dag.py ..                       [  9%]
tests/agent_factory/test_at08_recover_failed_build.py .                  [ 10%]
tests/agent_factory/test_at09_qa_certification.py .                      [ 12%]
tests/agent_factory/test_at10_db_self_approval.py .                      [ 13%]
tests/agent_factory/test_at11_prevent_self_granted_perms.py .            [ 14%]
tests/agent_factory/test_at12_tenant_isolation.py ...                    [ 18%]
tests/agent_factory/test_at14_evidence_ledger.py .                       [ 20%]
tests/agent_factory/test_at15_signed_artifacts.py .                      [ 21%]
tests/agent_factory/test_at19_at20_quotas.py .                           [ 22%]
tests/agent_factory/test_at21_gate_calibration.py .                      [ 24%]
tests/agent_factory/test_at22_baseline_diff.py ..                        [ 27%]
tests/agent_factory/test_batch_scheduler.py .                            [ 28%]
tests/agent_factory/test_browser_ssrf_guard.py ....                      [ 33%]
tests/agent_factory/test_compiler.py ..                                  [ 36%]
tests/agent_factory/test_gate_eval.py .                                  [ 37%]
tests/agent_factory/test_governed_call.py ....                           [ 43%]
tests/agent_factory/test_import_quarantine.py ..                         [ 45%]
tests/agent_factory/test_mcp_gateway.py ...                              [ 50%]
tests/agent_factory/test_migration_verification.py ......                [ 58%]
tests/agent_factory/test_permission_calculator.py .....                  [ 64%]
tests/agent_factory/test_phase3_routes.py .                              [ 66%]
tests/agent_factory/test_quotas.py .                                     [ 67%]
tests/agent_factory/test_routes.py ......                                [ 75%]
tests/agent_factory/test_signer.py .                                     [ 77%]
tests/agent_factory/test_spec_validator.py .........                     [ 89%]
tests/agent_factory/test_template_loader.py ...                          [ 93%]
tests/agent_factory/test_transition_helper.py .....                      [100%]

============================== 74 passed in 5.92s ==============================
```

All 74 tests passing. Zero regressions across baseline codebase.
