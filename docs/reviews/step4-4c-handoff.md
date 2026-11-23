# Sub-Step 4C Handoff: LangGraph Runtime Adapter & Encrypted PostgreSQL Checkpointer

## 1. Summary of Changes
- Built `core/langgraph/state.py`: Typed immutable execution state with custom reducers (`add_message`, `record_idempotency_key`) and untrusted content boundaries.
- Built `core/langgraph/checkpointer.py`: `PostgresCheckpointer` implementing checkpoint persistence across SQLite and PostgreSQL 16. Enforces **Rule 36 (Payload Encryption at Rest)** using `KeyManagementPort` envelope encryption (`kms.encrypt(...)`), storing base64 ciphertext in `checkpoint_blob`. Fails closed if KMS encryption is unavailable.
- Built `core/langgraph/adapter.py`: `LangGraphRuntimeAdapter` implementing cyclic execution (Planner -> Tool Executor -> Critic -> Router) bounded to $\le 5$ iterations. Enforces **Rule 34** port routing and **Rule 35** idempotency key caching.
- Created DDL migrations:
  - `migrations/common/0032_langgraph_checkpoints.sql`
  - `migrations/pg/0032_langgraph_checkpoints.sql`
- Added comprehensive unit and contract tests in `tests/test_step4_langgraph_runtime.py`.
- Updated `.github/workflows/ci.yml` to include `tests/test_step4_langgraph_runtime.py` in both SQLite and PostgreSQL 16 CI test jobs.
- Updated `docs/reports/ADOPTION_STATUS.md` recording LangGraph / PostgresCheckpointer as `ADOPTED`.

## 2. Files Changed
```text
 core/langgraph/__init__.py                     |  20 ++++
 core/langgraph/adapter.py                      | 266 +++++++++++++++++++++++++++++++++++++++
 core/langgraph/checkpointer.py                 | 205 ++++++++++++++++++++++++++++++
 core/langgraph/state.py                        |  88 +++++++++++++
 core/ports/agent_runtime.py                    |  20 ++-
 docs/reports/ADOPTION_STATUS.md                |  13 ++
 docs/reports/STEP4_REPORT.md                   |  52 ++++++++
 migrations/common/0032_langgraph_checkpoints.sql |  40 ++++++
 migrations/pg/0032_langgraph_checkpoints.sql     |  42 +++++++
 tests/test_step4_langgraph_runtime.py          | 227 +++++++++++++++++++++++++++++++++
 .github/workflows/ci.yml                       |   4 +-
```

## 3. Verification Commands
```bash
python3 -m pytest tests/test_step4_langgraph_runtime.py -v
python3 -m pytest tests/test_step4_runtime_ports.py -v
python3 -m pytest tests/test_truth_linter.py -v
python3 scripts/anti_bypass_linter.py --scan-path core
```

## 4. Claims Made
1. `PostgresCheckpointer` initializes `langgraph_checkpoints` and `langgraph_checkpoint_writes` with RLS (`tenant_id`, `company_id`).
2. Payloads are encrypted at rest using `KeyManagementPort` envelope encryption; raw prompt and response strings never reach database rows.
3. Checkpoint persistence fails closed with `RuntimeError` if encryption is unconfigured or unavailable.
4. `LangGraphRuntimeAdapter` executes cyclic loops bounded to $\le 5$ iterations, routing 100% of LLM calls through `LLMGateway` and tool executions through `ActionGateway`.
5. Resuming from a checkpoint loads state without re-executing already-completed steps (Rule 35).

## 5. Mutation Checks Done
- Verified that unconfigured KMS (`test_07_mutation_check_unconfigured_kms_fails_closed`) fails closed immediately with `RuntimeError` rather than writing unencrypted state.
- Verified that direct database inspection shows non-empty base64 ciphertext and zero plaintext prompt strings in the database.
