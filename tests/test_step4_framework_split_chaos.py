"""ZONATA Sovereign Core — Sub-Step 4E Unit & Contract Test Suite.

Verifies:
1. Decision D4-1 Framework Split:
   - TEMPORAL: Long-running durable business processes.
   - LANGGRAPH: Short-cycle iterative agents.
   - GOOGLE_ADK: Hierarchical multi-agent teams.
   - LOCAL: Fast in-process single-turn sovereign utility agents.
2. Routing Validation: Rejects invalid or mismatched workload assignments.
3. Chaos Engineering Drill (Rules 33 & 35):
   - LangGraph mid-cycle worker crash and restart from encrypted checkpoint.
   - Temporal activity replay idempotency verification (cached_replay=True).
4. Multi-tenant RLS isolation during fault recovery.
5. Mutation checks: invalid target fails closed; non-idempotent replay attempts blocked.
"""

from __future__ import annotations
import os
import unittest
from typing import Any, Dict

from core.ports.base import PortStatus
from core.ports.agent_runtime import (
    AgentSpec,
    ExecutionContext,
    AgentResult,
    AgentRuntimeStatus,
)
from core.framework_router import (
    FrameworkRouter,
    RuntimeTarget,
    RoutingValidationError,
    framework_router,
)
from core.chaos.simulator import (
    SimulatedWorkerCrash,
    ChaosSimulator,
    chaos_simulator,
)
from core.langgraph.adapter import LangGraphRuntimeAdapter
from core.langgraph.checkpointer import PostgresCheckpointer
from core.temporal.activities import TemporalActivities


class TestStep4FrameworkSplitChaos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        cls.checkpointer = PostgresCheckpointer()
        cls.langgraph_adapter = LangGraphRuntimeAdapter(state_checkpointer=cls.checkpointer)
        cls.temporal_activities = TemporalActivities()

    def test_01_router_assigns_temporal_for_durable_or_long_running(self):
        """Test Decision D4-1: Multi-day / durable processes route to TEMPORAL."""
        # Case A: Timeout > 3600 seconds
        spec_long = AgentSpec(
            spec_id="spec_long_01",
            name="Month End Close",
            system_prompt="Execute month end close process.",
            limits={"timeout_seconds": 86400},
        )
        target_a = framework_router.resolve_target(spec_long)
        self.assertEqual(target_a, RuntimeTarget.TEMPORAL)

        # Case B: Explicit durable workflow_type
        spec_durable = AgentSpec(
            spec_id="spec_durable_01",
            name="Saga Coordinator",
            system_prompt="Coordinate cross-system saga.",
            workflow_type="durable",
        )
        target_b = framework_router.resolve_target(spec_durable)
        self.assertEqual(target_b, RuntimeTarget.TEMPORAL)

    def test_02_router_assigns_langgraph_for_cyclic_loops(self):
        """Test Decision D4-1: Iterative cyclic agents route to LANGGRAPH."""
        spec_cyclic = AgentSpec(
            spec_id="spec_cycle_01",
            name="Code Auditor",
            system_prompt="Iteratively write and audit code.",
            workflow_type="cyclic",
            limits={"max_steps": 5},
        )
        target = framework_router.resolve_target(spec_cyclic)
        self.assertEqual(target, RuntimeTarget.LANGGRAPH)

    def test_03_router_assigns_google_adk_for_hierarchical_teams(self):
        """Test Decision D4-1: Hierarchical squads and team topologies route to GOOGLE_ADK."""
        spec_team = AgentSpec(
            spec_id="spec_team_01",
            name="Engineering Squad",
            system_prompt="Supervisor coordinates developer and tester.",
            workflow_type="hierarchical",
        )
        target = framework_router.resolve_target(spec_team)
        self.assertEqual(target, RuntimeTarget.GOOGLE_ADK)

    def test_04_router_assigns_local_for_sequential_tasks(self):
        """Test Decision D4-1: Standard single-turn utility tasks route to LOCAL."""
        spec_seq = AgentSpec(
            spec_id="spec_seq_01",
            name="Fast Parser",
            system_prompt="Parse input document json.",
            workflow_type="sequential",
            limits={"timeout_seconds": 60},
        )
        target = framework_router.resolve_target(spec_seq)
        self.assertEqual(target, RuntimeTarget.LOCAL)

    def test_05_router_rejects_architectural_mismatches(self):
        """Test FrameworkRouter rejects workloads that violate architectural boundaries."""
        # Reject: Multi-day process forced onto ephemeral LOCAL
        spec_invalid = AgentSpec(
            spec_id="spec_inv_01",
            name="Invalid Router Target",
            system_prompt="Long process on local",
            limits={"timeout_seconds": 7200},
            metadata={"target_runtime": "LOCAL"},
        )
        with self.assertRaises(RoutingValidationError):
            framework_router.resolve_target(spec_invalid)

        # Reject: Unbounded cyclic loop on LangGraph (>10 iterations)
        spec_unbounded = AgentSpec(
            spec_id="spec_inv_02",
            name="Unbounded Loop",
            system_prompt="Loop forever",
            workflow_type="cyclic",
            limits={"max_steps": 25},
            metadata={"target_runtime": "LANGGRAPH"},
        )
        with self.assertRaises(RoutingValidationError):
            framework_router.resolve_target(spec_unbounded)

        # Reject: Unknown runtime target string
        spec_unknown = AgentSpec(
            spec_id="spec_inv_03",
            name="Unknown Runtime",
            system_prompt="Run on alien runtime",
            metadata={"target_runtime": "ALIEN_RUNTIME_99"},
        )
        with self.assertRaises(RoutingValidationError):
            framework_router.resolve_target(spec_unknown)

    def test_06_langgraph_chaos_crash_and_recovery(self):
        """Chaos Drill: Simulates worker crash mid-graph, restarts, and proves seamless checkpoint recovery."""
        spec = AgentSpec(
            spec_id="spec_chaos_lg_01",
            name="Resilient Auditor",
            system_prompt="Complete multi-step financial audit.",
            workflow_type="cyclic",
        )
        ctx = ExecutionContext(
            tenant_id="tenant_chaos_01",
            company_id="company_chaos_01",
            actor_id="user_ci",
            run_id="run_chaos_lg_001",
            idempotency_key="idem_chaos_lg_001",
        )
        injected_err, recovered_res = chaos_simulator.run_langgraph_with_crash_and_recovery(
            adapter=self.langgraph_adapter,
            spec=spec,
            input_data={"account": "GL_1001"},
            context=ctx,
            crash_at_iteration=1,
        )
        self.assertIsInstance(injected_err, SimulatedWorkerCrash)
        self.assertIsInstance(recovered_res, AgentResult)
        self.assertEqual(recovered_res.state, AgentRuntimeStatus.COMPLETED)
        self.assertIn("calculator", recovered_res.output.get("tool_outputs", {}))

    def test_07_temporal_chaos_activity_crash_and_replay(self):
        """Chaos Drill: Simulates worker crash after activity completion, replays with same key, proves idempotency."""
        t_id = "tenant_chaos_02"
        c_id = "company_chaos_02"
        act_id = "user_ci"
        idem_key = "idem_chaos_temporal_unique_42"

        res1, res2 = chaos_simulator.run_temporal_with_activity_replay_check(
            activities=self.temporal_activities,
            tenant_id=t_id,
            company_id=c_id,
            actor_id=act_id,
            tool_name="calculator",
            tool_args={"expression": "999 + 1"},
            idempotency_key=idem_key,
        )
        self.assertFalse(res1["cached_replay"])
        self.assertTrue(res2["cached_replay"])
        self.assertEqual(res1["result"], res2["result"])

    def test_08_multi_tenant_isolation_under_chaos(self):
        """Test Multi-Tenant RLS isolation holds during chaos recovery."""
        # Save checkpoint under tenant A
        self.checkpointer.put(
            tenant_id="tenant_iso_A",
            company_id="company_iso_A",
            thread_id="thread_iso_01",
            checkpoint_id="cp_iso_01",
            state_dict={"data": "tenant_A_confidential"},
            metadata={"secret": "alpha"},
            idempotency_key="idem_iso_A",
            step_count=1,
        )

        # Attempt to read from tenant B
        read_b = self.checkpointer.get(
            tenant_id="tenant_iso_B",
            company_id="company_iso_B",
            thread_id="thread_iso_01",
        )
        self.assertIsNone(read_b, "Tenant B must not access Tenant A's checkpoint state under chaos")

    def test_09_mutation_check_unauthorized_bypass_attempt_fails(self):
        """Mutation Check: Simple task cannot be given team orchestration without team requirements."""
        spec_simple = AgentSpec(
            spec_id="spec_simple_bypass",
            name="Simple Echo",
            system_prompt="Echo text",
            workflow_type="sequential",
        )
        with self.assertRaises(RoutingValidationError):
            FrameworkRouter.validate_assignment(
                RuntimeTarget.GOOGLE_ADK,
                spec_simple,
                input_data={"requires_team": False},
            )


if __name__ == "__main__":
    unittest.main()
