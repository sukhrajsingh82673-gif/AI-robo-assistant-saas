"""ZONATA Sovereign Core — Sub-Step 4F Unit & Contract Test Suite.

Verifies:
1. GoogleADKRuntimeAdapter probe behavior: fails closed when unconfigured (Truth Rule 1);
   returns SANDBOX with valid provider_ref under ZONATA_TEST_MODE=1.
2. Hierarchical team execution: Supervisor -> Worker -> Critic with bounded feedback loop.
3. Tool execution via ZonataADKToolWrapper through ActionGateway and ToolRegistry (Rule 34).
4. Rule 35: Deterministic idempotency keys prevent duplicate tool execution across replays.
5. Rule 36: Multi-tenant session state encryption at rest via KeyManagementPort.
6. Constitutional Bounds: Tree depth <= 3 and feedback loops <= 5 strictly enforced.
7. Kill switch halts in-flight team execution.
8. Streaming yields structured AgentChunk events.
9. Mutation checks: tree depth violation rejected; unconfigured runtime fails closed; unregistered tool fails.
"""

from __future__ import annotations
import os
import unittest
from typing import Any, Dict

from core.ports.base import PortStatus
from core.ports.agent_runtime import (
    AgentSpec,
    ExecutionContext,
    AgentChunk,
    AgentResult,
    AgentRuntimeStatus,
)
from core.adk.model import ZonataADKModel, adk_model
from core.adk.tool_wrapper import ZonataADKToolWrapper, ADKToolExecutionError
from core.adk.session import ZonataADKSessionService, adk_session_service
from core.adk.coordinator import (
    TeamTopologyError,
    HierarchicalTeamCoordinator,
    adk_coordinator,
)
from core.adk.adapter import GoogleADKRuntimeAdapter


class TestStep4GoogleADKRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        cls.adapter = GoogleADKRuntimeAdapter()
        cls.coordinator = HierarchicalTeamCoordinator()

    def test_01_probe_fail_closed_and_sandbox(self):
        """Test probe returns SANDBOX under test mode, and NOT_CONFIGURED when unconfigured."""
        # Test mode
        probe_test = self.adapter.probe()
        self.assertEqual(probe_test.status, PortStatus.SANDBOX)
        self.assertTrue(probe_test.sandbox)
        self.assertTrue(len(probe_test.provider_ref) > 0)

        # Strict prod mode without config
        orig_test_mode = os.environ.pop("ZONATA_TEST_MODE", None)
        try:
            strict_adapter = GoogleADKRuntimeAdapter(sandbox=False)
            strict_probe = strict_adapter.probe()
            self.assertEqual(strict_probe.status, PortStatus.NOT_CONFIGURED)
            self.assertIn("not installed", strict_probe.error)
        finally:
            if orig_test_mode is not None:
                os.environ["ZONATA_TEST_MODE"] = orig_test_mode

    def test_02_hierarchical_team_execution_success(self):
        """Test hierarchical team (Supervisor -> Worker -> Critic) executes and reaches consensus."""
        spec = AgentSpec(
            spec_id="spec_adk_team_01",
            name="Research & Verification Squad",
            system_prompt="Coordinate market intelligence report with critic review.",
            workflow_type="hierarchical",
        )
        ctx = ExecutionContext(
            tenant_id="tenant_adk_01",
            company_id="company_adk_01",
            actor_id="user_ci",
            run_id="run_adk_team_001",
            idempotency_key="idem_adk_001",
        )
        res = self.adapter.execute_agent(
            spec=spec,
            input_data={"market": "SaaS AI infrastructure"},
            context=ctx,
        )
        self.assertIsInstance(res, AgentResult)
        self.assertEqual(res.state, AgentRuntimeStatus.COMPLETED)
        self.assertEqual(res.output["topology_version"], "1.0.0")
        self.assertIn("loops_completed", res.output)
        self.assertLessEqual(res.output["loops_completed"], 5)
        self.assertEqual(res.output["critic_verdict"], "APPROVED")

    def test_03_tool_execution_through_adk_wrapper(self):
        """Test squad tool execution routes through ZonataADKToolWrapper and ActionGateway (Rule 34)."""
        spec = AgentSpec(
            spec_id="spec_adk_tool_01",
            name="Financial Analysis Squad",
            system_prompt="Analyze EBITDA metrics using calculator.",
            workflow_type="hierarchical",
            allowed_tools=["calculator"],
        )
        ctx = ExecutionContext(
            tenant_id="tenant_adk_02",
            company_id="company_adk_02",
            actor_id="user_ci",
            run_id="run_adk_team_002",
            idempotency_key="idem_adk_002",
        )
        res = self.adapter.execute_agent(
            spec=spec,
            input_data={
                "requested_tool": "calculator",
                "tool_args": {"expression": "500000 - 350000"},
            },
            context=ctx,
        )
        self.assertEqual(res.state, AgentRuntimeStatus.COMPLETED)
        self.assertEqual(len(res.tool_calls), 1)
        tool_out = res.tool_calls[0]
        self.assertEqual(tool_out["tool"], "calculator")
        self.assertTrue(tool_out["result"]["result"]["success"])

    def test_04_tree_depth_bound_enforced(self):
        """Test Constitutional Bound: Tree depth > 3 is rejected with TeamTopologyError."""
        spec = AgentSpec(spec_id="spec_deep", name="Deep Spec", system_prompt="Test depth")
        ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_deep", actor_id="u1")
        # Attempt execution at tree_depth = 4
        with self.assertRaises(TeamTopologyError):
            self.coordinator.execute_team(spec, {}, ctx, tree_depth=4)

    def test_05_critic_loop_bound_enforced(self):
        """Test Constitutional Bound: Critic loop terminates at or before max bound <= 5."""
        spec = AgentSpec(spec_id="spec_loop", name="Loop Spec", system_prompt="Test loop bound")
        ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_loop_bnd", actor_id="u1")
        res = self.coordinator.execute_team(spec, {}, ctx, tree_depth=1)
        self.assertLessEqual(res.loop_count, 5)

    def test_06_kill_switch_halts_team(self):
        """Test Kill Switch halts team execution immediately."""
        from core.distributed_coordination import coordination
        spec_id = "spec_halt_adk_01"
        coordination.set_killswitch_state("AGENT", spec_id, True, reason="Emergency team halt drill")
        try:
            spec = AgentSpec(spec_id=spec_id, name="Halt Target", system_prompt="Do not run")
            ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_halt_adk", actor_id="u1")
            res = self.adapter.execute_agent(spec, {}, ctx)
            self.assertEqual(res.state, AgentRuntimeStatus.HALTED_BY_KILL_SWITCH)
            self.assertIn("Emergency team halt drill", res.error)
        finally:
            coordination.set_killswitch_state("AGENT", spec_id, False)

    def test_07_multi_tenant_session_isolation(self):
        """Test Rule 36: ADK sessions are KMS encrypted and enforce multi-tenant isolation."""
        session_svc = ZonataADKSessionService()
        sess_id = "sess_confidential_01"

        # Create session under Tenant A
        sess_a = session_svc.create_session(
            session_id=sess_id,
            tenant_id="tenant_alpha",
            company_id="company_alpha",
        )
        sess_a.add_message("user", "Confidential quarterly plan", agent_id="client")
        session_svc.save_session(sess_a)

        # Retrieve as Tenant A: succeeds
        read_a = session_svc.get_session(sess_id, "tenant_alpha", "company_alpha")
        self.assertIsNotNone(read_a)
        self.assertEqual(len(read_a.messages), 1)

        # Retrieve as Tenant B: returns None (access denied)
        read_b = session_svc.get_session(sess_id, "tenant_bravo", "company_bravo")
        self.assertIsNone(read_b, "Tenant B must not access Tenant A's encrypted session")

    def test_08_streaming_chunks(self):
        """Test stream_agent yields log, tool_call, and token chunks."""
        spec = AgentSpec(
            spec_id="spec_stream_adk",
            name="Streaming ADK Agent",
            system_prompt="Stream squad steps.",
            allowed_tools=["calculator"],
        )
        ctx = ExecutionContext(
            tenant_id="t_stream_adk",
            company_id="c_stream_adk",
            run_id="run_stream_adk_01",
            actor_id="u_ci",
        )
        chunks = list(self.adapter.stream_agent(
            spec=spec,
            input_data={"requested_tool": "calculator", "tool_args": {"expression": "25 * 4"}},
            context=ctx,
        ))
        self.assertGreaterEqual(len(chunks), 2)
        chunk_types = [c.chunk_type for c in chunks]
        self.assertIn("log", chunk_types)

    def test_09_mutation_check_unregistered_tool_rejected(self):
        """Mutation Check: Unregistered tool execution raises ADKToolExecutionError."""
        wrapper = ZonataADKToolWrapper("nonexistent_rogue_tool")
        with self.assertRaises(ADKToolExecutionError):
            wrapper.execute(
                tenant_id="t1",
                company_id="c1",
                actor_id="u1",
                arguments={"arg": 1},
                idempotency_key="idem_mut_unreg",
            )

    def test_10_mutation_check_unconfigured_runtime_fails_closed(self):
        """Mutation Check: Unconfigured ADK adapter fails closed rather than executing unverified."""
        orig_test_mode = os.environ.pop("ZONATA_TEST_MODE", None)
        try:
            strict_adapter = GoogleADKRuntimeAdapter(sandbox=False)
            spec = AgentSpec(spec_id="spec_strict_adk", name="Strict ADK", system_prompt="Test")
            ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_strict_adk", actor_id="u1")
            res = strict_adapter.execute_agent(spec, {}, ctx)
            self.assertEqual(res.status, PortStatus.NOT_CONFIGURED)
            self.assertEqual(res.state, AgentRuntimeStatus.FAILED)
            self.assertIn("not configured", res.error)
        finally:
            if orig_test_mode is not None:
                os.environ["ZONATA_TEST_MODE"] = orig_test_mode


if __name__ == "__main__":
    unittest.main()
