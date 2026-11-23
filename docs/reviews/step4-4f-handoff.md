# Sub-Step 4F Handoff: Google ADK Hierarchical Teams & Loops

## 1. Summary of Changes
- Built `core/adk/model.py`: `ZonataADKModel` wrapping `LLMGatewayPort` with token usage accounting, ModelTier enforcement, and correlation IDs (Rule 34).
- Built `core/adk/tool_wrapper.py`: `ZonataADKToolWrapper` packaging tools from `ToolRegistry` into immutable `ActionEnvelope` evaluations evaluated by `ActionGateway` with Rule 35 idempotency caching.
- Built `core/adk/session.py`: `ZonataADKSessionService` providing multi-tenant conversation session state encrypted with per-tenant KMS keys (Rule 36).
- Built `core/adk/coordinator.py`: `HierarchicalTeamCoordinator` orchestrating supervisor-worker-critic squads bounded by constitutional tree depth $\le 3$ and loop count $\le 5$.
- Built `core/adk/adapter.py`: `GoogleADKRuntimeAdapter` bridging `AgentRuntimePort` to Google ADK team engine with probe, execution, cancellation, and streaming.
- Built `core/adk/__init__.py`.
- Updated `core/ports/agent_runtime.py`: Delegated `GoogleADKRuntimeAdapter` to `core.adk.adapter.GoogleADKRuntimeAdapter`.
- Built `tests/test_step4_google_adk_runtime.py`: 10 comprehensive unit and contract tests covering probe statuses, squad consensus, tool invocation, tree depth / loop bounds, kill switches, multi-tenant session isolation, streaming, and mutation checks.
- Updated `docs/reports/ADOPTION_STATUS.md`: Marked Google ADK as `ADOPTED`.
- Updated `.github/workflows/ci.yml`: Added `tests/test_step4_google_adk_runtime.py` to SQLite and PostgreSQL 16 CI test jobs.

## 2. Files Changed
```text
 core/adk/__init__.py                     |  24 ++++
 core/adk/adapter.py                      | 145 ++++++++++++++++++++
 core/adk/coordinator.py                  | 175 +++++++++++++++++++++++++
 core/adk/model.py                        |  52 ++++++++
 core/adk/session.py                      | 145 ++++++++++++++++++++
 core/adk/tool_wrapper.py                 |  88 +++++++++++++
 core/ports/agent_runtime.py              |  38 +-----
 docs/reports/ADOPTION_STATUS.md          |   2 +-
 docs/reports/STEP4_REPORT.md             |  64 +++++++++
 tests/test_step4_google_adk_runtime.py   | 205 +++++++++++++++++++++++++++++
 .github/workflows/ci.yml                 |   4 +-
```

## 3. Verification Commands
```bash
python3 -m pytest tests/test_step4_google_adk_runtime.py -v
python3 -m pytest tests/test_step4_runtime_ports.py -v
python3 -m pytest tests/test_truth_linter.py -v
python3 scripts/anti_bypass_linter.py --scan-path core
```

## 4. Claims Made
1. `ZonataADKModel` enforces Rule 34 by routing 100% of LLM calls through `LLMGatewayPort`.
2. `ZonataADKToolWrapper` enforces Rule 34 by evaluating tools through `ActionGateway` and executing via `ToolRegistry`.
3. Rule 35 idempotency caching guarantees that replayed squad actions return cached records without repeating side effects.
4. Constitutional bounds are strictly enforced: tree depth $> 3$ raises `TeamTopologyError` and loop count terminates at $\le 5$.
5. Rule 36 is satisfied: session dialogues are KMS encrypted at rest with multi-tenant isolation.

## 5. Mutation Checks Done
- Verified that requesting execution at tree depth 4 raises `TeamTopologyError` (`test_04_tree_depth_bound_enforced`).
- Verified that unregistered tool execution raises `ADKToolExecutionError` (`test_09_mutation_check_unregistered_tool_rejected`).
- Verified that an unconfigured ADK adapter in non-test mode fails closed (`test_10_mutation_check_unconfigured_runtime_fails_closed`).
