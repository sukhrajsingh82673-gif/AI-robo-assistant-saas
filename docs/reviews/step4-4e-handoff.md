# Sub-Step 4E Handoff: Framework Split Qualification & Chaos Test

## 1. Summary of Changes
- Built `core/framework_router.py`: `FrameworkRouter` enforcing Decision D4-1 matrix across `TEMPORAL`, `LANGGRAPH`, `GOOGLE_ADK`, and `LOCAL`. Validates timeouts, cyclic steps, and team topology requirements; fails closed on mismatches (`RoutingValidationError`).
- Built `core/chaos/simulator.py`: `ChaosSimulator` simulating mid-execution worker death (`SimulatedWorkerCrash`) for LangGraph and Temporal, verifying resumption without duplicate tool calls (Rule 35).
- Created `core/chaos/__init__.py`.
- Built `tests/test_step4_framework_split_chaos.py`: 9 comprehensive tests covering Decision D4-1 classification, invalid assignment rejection, LangGraph crash recovery, Temporal idempotency replay, multi-tenant isolation under chaos, and mutation checks.
- Updated `.github/workflows/ci.yml`: Added `tests/test_step4_framework_split_chaos.py` to SQLite and PostgreSQL 16 CI test jobs.

## 2. Files Changed
```text
 core/chaos/__init__.py                     |  12 +++
 core/chaos/simulator.py                    |  95 ++++++++++++++++++++++
 core/framework_router.py                   |  88 ++++++++++++++++++++
 docs/reports/STEP4_REPORT.md               |  51 ++++++++++++
 tests/test_step4_framework_split_chaos.py  | 195 +++++++++++++++++++++++++++
 .github/workflows/ci.yml                   |   4 +-
```

## 3. Verification Commands
```bash
python3 -m pytest tests/test_step4_framework_split_chaos.py -v
python3 -m pytest tests/test_step4_temporal_runtime.py -v
python3 -m pytest tests/test_step4_langgraph_runtime.py -v
python3 scripts/anti_bypass_linter.py --scan-path core
```

## 4. Claims Made
1. `FrameworkRouter` correctly enforces Decision D4-1 runtime assignment (Temporal for durable/long-running, LangGraph for cyclic loops, Google ADK for hierarchical teams, Local for sequential utility).
2. Routing validation fails closed when a task violates architectural bounds (e.g., >3600s timeout routed to ephemeral Local/LangGraph).
3. LangGraph recovers seamlessly from worker crashes using encrypted checkpoints without duplicate step/tool execution (Rule 35).
4. Temporal activity replay returns cached results when invoked with identical idempotency keys (Rule 35).
5. Multi-tenant RLS boundaries are strictly preserved during fault injection and recovery.

## 5. Mutation Checks Done
- Verified that requesting `GOOGLE_ADK` for a simple sequential task without team requirements raises `RoutingValidationError` (`test_09_mutation_check_unauthorized_bypass_attempt_fails`).
- Verified that unbounded cyclic loops (>10 iterations) and unknown targets raise `RoutingValidationError`.
