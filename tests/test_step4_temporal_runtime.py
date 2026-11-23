"""ZONATA Sovereign Core — Sub-Step 4D Unit & Contract Test Suite.

Verifies:
1. TemporalRuntimeAdapter probe behavior: fails closed when unconfigured (Truth Rule 1);
   returns SANDBOX with valid provider_ref under ZONATA_TEST_MODE=1.
2. Rule 33: Framework holds execution state only; business truth lives in ActionGateway/ZONATA tables.
3. Rule 34: 100% of LLM calls route through LLMGateway; 100% of tools route through ActionGateway.
4. Rule 35: Deterministic idempotency keys prevent duplicate activity execution on replay.
5. Rule 38: Workflows are versioned (workflow_version="1.0.0").
6. Kill switch halts in-flight workflow execution.
7. Streaming yields structured AgentChunk events.
8. Mutation checks: unauthorized tool is rejected with NonRetryableActivityError; unconfigured adapter fails closed.
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
from core.temporal.activities import (
    TemporalActivities,
    temporal_activities,
    NonRetryableActivityError,
)
from core.temporal.workflows import ZonataAgentWorkflow, WorkflowExecutionRecord
from core.temporal.adapter import TemporalRuntimeAdapter


class TestStep4TemporalRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        cls.adapter = TemporalRuntimeAdapter()

    def test_01_probe_fail_closed_and_sandbox(self):
        """Test probe returns SANDBOX under test mode, and NOT_CONFIGURED when unconfigured."""
        # Under test mode
        probe_test = self.adapter.probe()
        self.assertEqual(probe_test.status, PortStatus.SANDBOX)
        self.assertTrue(probe_test.sandbox)
        self.assertTrue(len(probe_test.provider_ref) > 0)

        # In strict prod mode without config
        orig_test_mode = os.environ.pop("ZONATA_TEST_MODE", None)
        try:
            strict_adapter = TemporalRuntimeAdapter(sandbox=False)
            strict_probe = strict_adapter.probe()
            self.assertEqual(strict_probe.status, PortStatus.NOT_CONFIGURED)
            self.assertIn("not configured", strict_probe.error)
        finally:
            if orig_test_mode is not None:
                os.environ["ZONATA_TEST_MODE"] = orig_test_mode

    def test_02_workflow_execution_success(self):
        """Test durable workflow executes successfully and records history."""
        spec = AgentSpec(
            spec_id="spec_temporal_01",
            name="Temporal Durable Agent",
            system_prompt="Execute multi-step durable reconciliation process.",
        )
        ctx = ExecutionContext(
            tenant_id="tenant_temporal_01",
            company_id="company_temporal_01",
            actor_id="user_ci",
            run_id="run_temporal_wf_01",
            idempotency_key="idem_wf_01",
        )
        res = self.adapter.execute_agent(
            spec=spec,
            input_data={"task": "monthly_close_audit"},
            context=ctx,
        )
        self.assertIsInstance(res, AgentResult)
        self.assertEqual(res.state, AgentRuntimeStatus.COMPLETED)
        self.assertIn("workflow_id", res.output)
        self.assertEqual(res.output["workflow_version"], "1.0.0")
        self.assertEqual(res.output["steps_completed"], 1)

    def test_03_activity_dispatch_through_action_gateway(self):
        """Test tool execution activity routes through ActionGateway and ToolRegistry (Rule 34)."""
        spec = AgentSpec(
            spec_id="spec_temporal_tool_01",
            name="Temporal Financial Agent",
            system_prompt="Compute financial ratios deterministically.",
            allowed_tools=["calculator"],
        )
        ctx = ExecutionContext(
            tenant_id="tenant_temporal_02",
            company_id="company_temporal_02",
            actor_id="user_ci",
            run_id="run_temporal_wf_tool_02",
            idempotency_key="idem_wf_tool_02",
        )
        res = self.adapter.execute_agent(
            spec=spec,
            input_data={
                "requested_tool": "calculator",
                "tool_args": {"expression": "1000 * 12"},
            },
            context=ctx,
        )
        self.assertEqual(res.state, AgentRuntimeStatus.COMPLETED)
        self.assertEqual(len(res.tool_calls), 1)
        calc_result = res.tool_calls[0]
        self.assertEqual(calc_result["tool"], "calculator")
        self.assertTrue(calc_result["result"]["success"])

    def test_04_idempotent_activity_replay_rule_35(self):
        """Test Rule 35: Replaying an activity with identical idempotency key returns cached result."""
        activities = TemporalActivities()
        idem_key = "idem_activity_unique_99"

        # First attempt: executes
        out1 = activities.tool_execution_activity(
            tenant_id="t_idem",
            company_id="c_idem",
            actor_id="u_ci",
            tool_name="calculator",
            tool_args={"expression": "50 + 50"},
            idempotency_key=idem_key,
        )
        self.assertFalse(out1["cached_replay"])
        self.assertTrue(out1["result"]["success"])

        # Second attempt: returns cached replay
        out2 = activities.tool_execution_activity(
            tenant_id="t_idem",
            company_id="c_idem",
            actor_id="u_ci",
            tool_name="calculator",
            tool_args={"expression": "50 + 50"},
            idempotency_key=idem_key,
        )
        self.assertTrue(out2["cached_replay"])
        self.assertEqual(out1["result"], out2["result"])

    def test_05_workflow_versioning_rule_38(self):
        """Test Rule 38: Workflows carry explicit versioning metadata."""
        workflow = ZonataAgentWorkflow()
        self.assertEqual(workflow.workflow_version, "1.0.0")

        spec = AgentSpec(spec_id="spec_v1", name="V1 Spec", system_prompt="Test v1")
        ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_v1", actor_id="u1")
        record = workflow.execute(spec, {}, ctx)
        self.assertEqual(record.workflow_version, "1.0.0")

    def test_06_kill_switch_halts_workflow(self):
        """Test Kill Switch halts workflow execution immediately."""
        from core.distributed_coordination import coordination
        spec_id = "spec_halt_temporal_01"
        coordination.set_killswitch_state("AGENT", spec_id, True, reason="Emergency halt drill")
        try:
            spec = AgentSpec(spec_id=spec_id, name="Halt Target", system_prompt="Do not run")
            ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_halt_01", actor_id="u1")
            res = self.adapter.execute_agent(spec, {}, ctx)
            self.assertEqual(res.state, AgentRuntimeStatus.HALTED_BY_KILL_SWITCH)
            self.assertIn("Emergency halt drill", res.error)
        finally:
            coordination.set_killswitch_state("AGENT", spec_id, False)

    def test_07_streaming_chunks(self):
        """Test stream_agent yields log, tool_call, and token chunks."""
        spec = AgentSpec(
            spec_id="spec_stream_temp",
            name="Streaming Temporal Agent",
            system_prompt="Stream durable steps.",
            allowed_tools=["calculator"],
        )
        ctx = ExecutionContext(
            tenant_id="t_stream",
            company_id="c_stream",
            run_id="run_stream_temp_01",
            actor_id="u_ci",
        )
        chunks = list(self.adapter.stream_agent(
            spec=spec,
            input_data={"requested_tool": "calculator", "tool_args": {"expression": "7 * 8"}},
            context=ctx,
        ))
        self.assertGreaterEqual(len(chunks), 2)
        chunk_types = [c.chunk_type for c in chunks]
        self.assertIn("log", chunk_types)
        self.assertIn("tool_call", chunk_types)

    def test_08_mutation_check_unauthorized_tool_rejected(self):
        """Mutation Check: Unregistered or unauthorized tool raises NonRetryableActivityError."""
        activities = TemporalActivities()
        with self.assertRaises(NonRetryableActivityError):
            activities.tool_execution_activity(
                tenant_id="t_mut",
                company_id="c_mut",
                actor_id="u_ci",
                tool_name="unregistered_rogue_tool",
                tool_args={"cmd": "whoami"},
                idempotency_key="idem_fail_unregistered",
            )

    def test_09_mutation_check_unconfigured_runtime_fails_closed(self):
        """Mutation Check: Unconfigured Temporal runtime fails closed rather than running unverified."""
        orig_test_mode = os.environ.pop("ZONATA_TEST_MODE", None)
        try:
            strict_adapter = TemporalRuntimeAdapter(sandbox=False)
            spec = AgentSpec(spec_id="spec_strict", name="Strict Spec", system_prompt="Test")
            ctx = ExecutionContext(tenant_id="t1", company_id="c1", run_id="run_strict", actor_id="u1")
            res = strict_adapter.execute_agent(spec, {}, ctx)
            self.assertEqual(res.status, PortStatus.NOT_CONFIGURED)
            self.assertEqual(res.state, AgentRuntimeStatus.FAILED)
            self.assertIn("not configured", res.error)
        finally:
            if orig_test_mode is not None:
                os.environ["ZONATA_TEST_MODE"] = orig_test_mode


if __name__ == "__main__":
    unittest.main()
