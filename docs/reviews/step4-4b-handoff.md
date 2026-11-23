# Sub-Step 4B Handoff: Runtime Ports, Spec Compilers & Anti-Bypass Guards

**Sub-Step:** 4B  
**Branch:** `step4-durable-frameworks`  
**Commit:** Pending 4B commit  
**Author:** Antigravity (Builder)  
**Reviewer:** OpenCode (Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed
```text
.github/workflows/ci.yml           |   6 +++-
core/agent_spec/__init__.py        |  15 ++++++++
core/agent_spec/compiler.py        | 344 ++++++++++++++++++++++++++++++++++++++++++++++++++
core/ports/__init__.py             |  25 ++++
core/ports/agent_runtime.py        | 452 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
core/security/anti_bypass.py       | 167 +++++++++++++++++++++++++
scripts/anti_bypass_linter.py      |  48 ++++++++
docs/reports/STEP4_REPORT.md       |  51 ++++++++
tests/test_step4_runtime_ports.py  | 321 +++++++++++++++++++++++++++++++++++++++++++++++
9 files changed, 1427 insertions(+), 2 deletions(-)
```

---

## 2. Commands to Re-run
```bash
# Run the Step 4B unit and contract test suite
python3 -m pytest tests/test_step4_runtime_ports.py -v

# Run the Rule 34 Anti-Bypass AST security linter
python3 scripts/anti_bypass_linter.py
```

---

## 3. Claims Made
1. **AgentRuntimePort Interface Built:** Standard `AgentRuntimePort` created in `core/ports/agent_runtime.py` with typed execution, streaming, status, and cancellation contracts.
2. **Framework Adapters Implemented:**
   - `LocalAgentRuntimeAdapter`: sovereign in-process execution via `LLMGateway` and `ActionGateway`.
   - `LangGraphRuntimeAdapter`, `TemporalRuntimeAdapter`, and `GoogleADKRuntimeAdapter`: fail-closed adapters conforming to Truth Rule 1 (`NOT_CONFIGURED` when unconfigured, `SANDBOX` under test mode).
3. **Spec Compiler Multi-Targeting:** `core/agent_spec/compiler.py` validates `zonata.agent/v1` specs and compiles to `LOCAL`, `LANGGRAPH`, `TEMPORAL`, and `GOOGLE_ADK` execution descriptors with deterministic digests.
4. **Anti-Bypass AST Linter:** `scripts/anti_bypass_linter.py` and `core/security/anti_bypass.py` enforce Standing Rule 34, disallowing direct model SDK imports, unwrapped subprocesses, and raw network calls in agent runtimes.
5. **Acceptance Testing:** All 15 tests in `tests/test_step4_runtime_ports.py` pass 100% locally. Mutation checks confirm detection of simulated direct model imports and direct network calls.

---

## 4. Mutation Checks Done
- Verified that direct `import openai` in agent code raises `RULE_34_DIRECT_MODEL_IMPORT` violation (Test 14).
- Verified that direct `requests.get` in framework runtime code raises `RULE_34_DIRECT_NETWORK_EGRESS` violation (Test 15).
- Verified that specs with high-entropy credential patterns are rejected with `ValueError` (Test 12).

---

## 5. Known Gaps
- Concrete LangGraph cyclic graphs, Temporal durable workflows, and Google ADK team topologies are full implementations reserved for Sub-Steps 4C, 4D, and 4F respectively.
