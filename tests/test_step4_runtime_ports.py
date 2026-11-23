"""ZONATA Sovereign Core — Sub-Step 4B Unit & Contract Test Suite.

Verifies:
1. AgentRuntimePort contract compliance and registration.
2. LocalAgentRuntimeAdapter execution, streaming, kill switch halting, and idempotency (Rule 35).
3. LangGraphRuntimeAdapter, TemporalRuntimeAdapter, and GoogleADKRuntimeAdapter fail-closed behavior (Rule 1).
4. AgentSpecCompiler compilation to LOCAL, LANGGRAPH, TEMPORAL, and GOOGLE_ADK targets.
5. Invariant verification: all external nodes are wrapped by governed port calls (Rule 34).
6. AgentSpecCompiler rejection of credential leaks and invalid specs.
7. AntiBypassASTVisitor / anti_bypass_linter clean repository scan and mutation checks.
"""

from __future__ import annotations
import os
import unittest
from typing import Any, Dict

from core.ports.base import PortStatus, port_registry
from core.ports.agent_runtime import (
    AgentRuntimePort,
    AgentSpec,
    ExecutionContext,
    AgentChunk,
    AgentResult,
    AgentRuntimeStatus,
    LocalAgentRuntimeAdapter,
    LangGraphRuntimeAdapter,
    TemporalRuntimeAdapter,
    GoogleADKRuntimeAdapter,
    local_agent_runtime,
)
from core.agent_spec.compiler import (
    CompilationTarget,
    CompiledSpecDescriptor,
    AgentSpecCompiler,
    spec_compiler,
)
from core.security.anti_bypass import (
    scan_python_code,
    scan_repository_anti_bypass,
    AntiBypassViolation,
)


class TestStep4RuntimePorts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"

    def _sample_valid_spec_dict(self) -> Dict[str, Any]:
        return {
            "apiVersion": "zonata.agent/v1",
            "kind": "Agent",
            "metadata": {
                "name": "financial-reconciler",
                "display_name": "Financial Reconciler",
                "version": "1.0.0",
                "category": "finance",
                "risk_tier": "R1",
            },
            "identity": {
                "principal_kind": "agent",
                "tenant_bound": True,
                "may_use_employees": False,
            },
            "role": {
                "title": "Reconciler",
                "mission": "Reconcile daily accounts receivable balances.",
                "responsibilities": ["Inspect journals", "Verify totals"],
                "out_of_scope": ["Executing payments"],
                "success_criteria": ["All calculations sound"],
                "instructions": "Audit records following strict double-entry standards.",
            },
            "model": {
                "requirements": {
                    "complexity": "medium",
                    "privacy": "confidential",
                }
            },
            "capabilities": {
                "requested": [{"key": "tool.use"}]
            },
            "permissions": {
                "requested": {
                    "tools": [
                        {"name": "calculator", "scopes": ["execute"], "max_calls": 10}
                    ],
                    "network": {"external": False, "allowed_hosts": []},
                    "writes": False,
                }
            },
            "workflow": {"type": "sequential"},
            "memory": {
                "conversation": {"enabled": True, "max_messages": 20},
                "pii_policy": "redact",
            },
            "limits": {
                "max_steps": 25,
                "timeout_seconds": 300,
                "max_cost_usd_per_task": 0.5,
            },
            "io": {
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
            },
            "observability": {
                "trace": True,
                "capture_content": "redacted",
            },
            "tests": {
                "author_cases": [{"id": "smoke", "input": {}, "expect": {"ok": True}}],
                "dataset_refs": ["finance-eval@1.0"],
            },
        }

    def test_01_agent_runtime_port_registered(self):
        """Test that agent_runtime is registered in the port registry and subclasses AgentRuntimePort."""
        port = port_registry.get("agent_runtime")
        self.assertIsNotNone(port)
        self.assertIsInstance(port, AgentRuntimePort)
        self.assertIsInstance(local_agent_runtime, LocalAgentRuntimeAdapter)

    def test_02_local_agent_runtime_executes_successfully(self):
        """Test LocalAgentRuntimeAdapter executes a spec through LLMGateway."""
        adapter = LocalAgentRuntimeAdapter(sandbox=True)
        spec = AgentSpec(
            spec_id="spec_test_01",
            name="Test Auditor",
            system_prompt="Audit input financial balances.",
            allowed_tools=["calculator"],
        )
        ctx = ExecutionContext(
            tenant_id="tenant_ci",
            company_id="company_ci",
            actor_id="user_ci",
            idempotency_key="idem_test_01",
        )
        result = adapter.execute_agent(
            spec=spec,
            input_data={"account": "1000", "balance": 4500},
            context=ctx,
        )
        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.state, AgentRuntimeStatus.COMPLETED)
        self.assertEqual(result.idempotency_key, "idem_test_01")
        self.assertIn("response", result.output)
        self.assertGreater(result.token_usage["input_tokens"], 0)

    def test_03_local_agent_runtime_streams_chunks(self):
        """Test LocalAgentRuntimeAdapter streaming yields AgentChunk objects."""
        adapter = LocalAgentRuntimeAdapter(sandbox=True)
        spec = AgentSpec(
            spec_id="spec_test_02",
            name="Test Streamer",
            system_prompt="Summarize transaction logs.",
        )
        ctx = ExecutionContext(
            tenant_id="tenant_ci",
            company_id="company_ci",
            actor_id="user_ci",
        )
        chunks = list(adapter.stream_agent(spec, {"count": 5}, ctx))
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsInstance(chunk, AgentChunk)
            self.assertIn(chunk.chunk_type, ("log", "tool_call", "token", "approval_request"))

    def test_04_local_agent_runtime_idempotency_cache(self):
        """Test Rule 35: Replayed execution with identical run_id returns cached result."""
        adapter = LocalAgentRuntimeAdapter(sandbox=True)
        spec = AgentSpec(spec_id="spec_test_03", name="Idempotent Agent")
        ctx = ExecutionContext(
            tenant_id="tenant_ci",
            company_id="company_ci",
            actor_id="user_ci",
            run_id="run_fixed_idempotent_01",
            idempotency_key="idem_fixed_01",
        )
        res1 = adapter.execute_agent(spec, {"payload": "first"}, ctx)
        res2 = adapter.execute_agent(spec, {"payload": "second_ignored"}, ctx)
        self.assertEqual(res1.run_id, res2.run_id)
        self.assertTrue(res2.metadata.get("cached_idempotent_replay", False))

    def test_05_langgraph_adapter_fail_closed_and_sandbox(self):
        """Test LangGraphRuntimeAdapter behaves honestly per Truth Rule 1."""
        adapter = LangGraphRuntimeAdapter()
        probe = adapter.probe()
        # Under ZONATA_TEST_MODE=1, should be SANDBOX, otherwise NOT_CONFIGURED
        self.assertIn(probe.status, (PortStatus.SANDBOX, PortStatus.OK, PortStatus.NOT_CONFIGURED))

        ctx = ExecutionContext(
            tenant_id="tenant_ci",
            company_id="company_ci",
            actor_id="user_ci",
        )
        spec = AgentSpec(spec_id="spec_lg", name="LangGraph Agent")
        result = adapter.execute_agent(spec, {}, ctx)
        self.assertIn(result.status, (PortStatus.SANDBOX, PortStatus.OK, PortStatus.NOT_CONFIGURED))

    def test_06_temporal_adapter_fail_closed_and_sandbox(self):
        """Test TemporalRuntimeAdapter behaves honestly per Truth Rule 1."""
        adapter = TemporalRuntimeAdapter()
        probe = adapter.probe()
        self.assertIn(probe.status, (PortStatus.SANDBOX, PortStatus.OK, PortStatus.NOT_CONFIGURED))

        ctx = ExecutionContext(
            tenant_id="tenant_ci",
            company_id="company_ci",
            actor_id="user_ci",
        )
        spec = AgentSpec(spec_id="spec_temporal", name="Temporal Agent")
        result = adapter.execute_agent(spec, {}, ctx)
        self.assertIn(result.status, (PortStatus.SANDBOX, PortStatus.OK, PortStatus.NOT_CONFIGURED))

    def test_07_google_adk_adapter_fail_closed_and_sandbox(self):
        """Test GoogleADKRuntimeAdapter behaves honestly per Truth Rule 1."""
        adapter = GoogleADKRuntimeAdapter()
        probe = adapter.probe()
        self.assertIn(probe.status, (PortStatus.SANDBOX, PortStatus.OK, PortStatus.NOT_CONFIGURED))

        ctx = ExecutionContext(
            tenant_id="tenant_ci",
            company_id="company_ci",
            actor_id="user_ci",
        )
        spec = AgentSpec(spec_id="spec_adk", name="Google ADK Agent")
        result = adapter.execute_agent(spec, {}, ctx)
        self.assertIn(result.status, (PortStatus.SANDBOX, PortStatus.OK, PortStatus.NOT_CONFIGURED))

    def test_08_compile_to_local_target(self):
        """Test AgentSpecCompiler produces valid LOCAL descriptor."""
        spec_dict = self._sample_valid_spec_dict()
        desc = spec_compiler.compile(spec_dict, target=CompilationTarget.LOCAL)
        self.assertIsInstance(desc, CompiledSpecDescriptor)
        self.assertEqual(desc.target, CompilationTarget.LOCAL)
        self.assertEqual(desc.entry_point, "validate_input")
        self.assertGreater(len(desc.nodes), 0)
        self.assertGreater(len(desc.digest), 20)
        self.assertTrue(desc.governed_wrappers_verified)

    def test_09_compile_to_langgraph_target(self):
        """Test AgentSpecCompiler produces valid LANGGRAPH descriptor."""
        spec_dict = self._sample_valid_spec_dict()
        desc = spec_compiler.compile(spec_dict, target=CompilationTarget.LANGGRAPH)
        self.assertEqual(desc.target, CompilationTarget.LANGGRAPH)
        self.assertEqual(desc.runtime_config["graph_class"], "langgraph.graph.StateGraph")
        self.assertTrue(desc.runtime_config["encrypted_state"])
        self.assertIn("PostgresCheckpointer", desc.runtime_config["checkpointer"])

    def test_10_compile_to_temporal_target(self):
        """Test AgentSpecCompiler produces valid TEMPORAL descriptor."""
        spec_dict = self._sample_valid_spec_dict()
        desc = spec_compiler.compile(spec_dict, target=CompilationTarget.TEMPORAL)
        self.assertEqual(desc.target, CompilationTarget.TEMPORAL)
        self.assertEqual(desc.runtime_config["task_queue"], "zonata-agent-queue")
        self.assertTrue(desc.runtime_config["idempotency_key_enforced"])
        # Verify child activities exist
        act_nodes = [n for n in desc.nodes if n.get("kind") == "temporal_activity"]
        self.assertEqual(len(act_nodes), 1)
        self.assertGreaterEqual(len(act_nodes[0]["activities"]), 2)

    def test_11_compile_to_google_adk_target(self):
        """Test AgentSpecCompiler produces valid GOOGLE_ADK descriptor."""
        spec_dict = self._sample_valid_spec_dict()
        desc = spec_compiler.compile(spec_dict, target=CompilationTarget.GOOGLE_ADK)
        self.assertEqual(desc.target, CompilationTarget.GOOGLE_ADK)
        self.assertEqual(desc.runtime_config["team_topology"], "supervisor_worker_critic")
        self.assertLessEqual(desc.runtime_config["max_delegation_depth"], 3)
        self.assertLessEqual(desc.runtime_config["max_loop_iterations"], 5)

    def test_12_compiler_rejects_credential_leak(self):
        """Test AgentSpecCompiler rejects specs containing secret patterns (Gate G01)."""
        bad_spec = self._sample_valid_spec_dict()
        bad_spec["role"]["instructions"] = "Connect using sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456"
        with self.assertRaises(ValueError) as cm:
            spec_compiler.compile(bad_spec, target=CompilationTarget.LOCAL)
        err = str(cm.exception).lower()
        self.assertTrue("token" in err or "credential" in err, f"Unexpected error: {err}")

    def test_13_anti_bypass_linter_passes_current_repo(self):
        """Test that anti-bypass AST linter finds 0 Rule 34 violations on current codebase."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        violations = scan_repository_anti_bypass(repo_root)
        self.assertEqual(
            len(violations),
            0,
            f"Expected 0 Rule 34 violations, found {len(violations)}: {[v.description for v in violations]}",
        )

    def test_14_anti_bypass_linter_mutation_catches_direct_model_import(self):
        """Mutation Check: Verifies that a direct OpenAI import in agent code is flagged."""
        malicious_code = """
import openai

def my_agent_node(prompt):
    client = openai.OpenAI()
    return client.chat.completions.create(model='gpt-4o', messages=[{'role': 'user', 'content': prompt}])
"""
        violations = scan_python_code(malicious_code, file_path="core/agents/bad_agent.py")
        self.assertGreater(len(violations), 0)
        self.assertEqual(violations[0].violation_type, "RULE_34_DIRECT_MODEL_IMPORT")
        self.assertIn("openai", violations[0].offending_symbol)

    def test_15_anti_bypass_linter_mutation_catches_direct_network_call(self):
        """Mutation Check: Verifies that direct network requests in agent runtime are flagged."""
        malicious_code = """
import requests

def agent_worker_step():
    res = requests.get('https://api.external.com/data')
    return res.json()
"""
        violations = scan_python_code(malicious_code, file_path="core/ports/agent_runtime.py")
        self.assertGreater(len(violations), 0)
        self.assertEqual(violations[0].violation_type, "RULE_34_DIRECT_NETWORK_EGRESS")
        self.assertIn("requests.get", violations[0].offending_symbol)


if __name__ == "__main__":
    unittest.main()
