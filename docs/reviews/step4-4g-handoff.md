# Sub-Step 4G Handoff: Governed MCP Client & Sandboxed Server

## 1. Summary of Changes
- Created DDL migrations:
  - `migrations/common/0033_mcp_governance.sql`
  - `migrations/pg/0033_mcp_governance.sql` (enforces fail-closed PostgreSQL RLS policies).
- Built `core/mcp/client.py`: `GovernedMCPClient` implementing:
  - Server registration and tool schema hash pinning with deterministic SHA-256 (`compute_schema_hash`).
  - Rule 39 enforcement: `SchemaTamperingError` raised on schema deviations; model descriptions overridden with verified sovereign descriptions to neutralize prompt injection.
  - Rule 34 enforcement: MCP tools evaluate `ActionEnvelope` through `ActionGateway` and execute via `ToolRegistry`.
  - Rule 35 enforcement: Deterministic idempotency caching.
- Built `core/mcp/server.py`: `SandboxedMCPServer` handling MCP JSON-RPC 2.0 requests (`tools/list`, `tools/call`) with defensive `wrap_untrusted_tool_output(...)` wrapping.
- Built `core/mcp/__init__.py`.
- Built `tests/test_step4_governed_mcp.py`: 8 comprehensive tests covering server registration, prompt injection neutralization, schema tampering detection, unpinned tool rejection, ActionGateway evaluation, idempotency, JSON-RPC roundtrip, and mutation checks.
- Updated `docs/reports/ADOPTION_STATUS.md`: Marked Governed MCP Client as `ADOPTED`.
- Updated `.github/workflows/ci.yml`: Added `tests/test_step4_governed_mcp.py` to SQLite and PostgreSQL 16 CI test jobs.

## 2. Files Changed
```text
 core/mcp/__init__.py                     |  20 ++++
 core/mcp/client.py                       | 290 ++++++++++++++++++++++++++++++
 core/mcp/server.py                       |  95 ++++++++++
 docs/reports/ADOPTION_STATUS.md          |   2 +-
 docs/reports/STEP4_REPORT.md             |  54 ++++++
 migrations/common/0033_mcp_governance.sql |  36 ++++
 migrations/pg/0033_mcp_governance.sql     |  56 ++++++
 tests/test_step4_governed_mcp.py         | 230 ++++++++++++++++++++++++
 .github/workflows/ci.yml                 |   4 +-
```

## 3. Verification Commands
```bash
python3 -m pytest tests/test_step4_governed_mcp.py -v
python3 -m pytest tests/test_step4_runtime_ports.py -v
python3 -m pytest tests/test_truth_linter.py -v
python3 scripts/anti_bypass_linter.py --scan-path core
```

## 4. Claims Made
1. External MCP schemas are cryptographically pinned; any remote schema deviation is detected and blocked with `SchemaTamperingError` (Rule 39).
2. Hostile prompt injections embedded in remote tool descriptions are neutralized by replacing them with human-reviewed sovereign descriptions before reaching an LLM.
3. 100% of MCP tool executions route through `ActionEnvelope` evaluated by `ActionGateway` (Rule 34).
4. Replayed MCP tool calls with identical idempotency keys return cached execution outputs without side effects (Rule 35).
5. Tool outputs from `SandboxedMCPServer` are safely framed within `<<<UNTRUSTED_CONTENT>>>` wrappers.

## 5. Mutation Checks Done
- Verified that unapproved tools (`is_approved=0`) raise `UnpinnedToolError` (`test_08_mutation_check_unapproved_tool_execution_blocked`).
- Verified that unpinned tools cannot be discovered or executed (`test_04_unpinned_tool_rejected`).
- Verified that tampered schemas raise `SchemaTamperingError` (`test_03_schema_tampering_detection_fails_closed`).
