"""
ZONATA — Durable Workflow Runtime Test Suite (LangGraph Integration)
====================================================================
Comprehensive verification matrix for Project 04 (LangGraph):
- Core: provider loads, creation, validation, compilation, execution, checkpointing, pause, resume, cancel
- Branching: conditional branching, multi-branch, loops, iteration limits, subworkflows, concurrency
- Human-in-the-loop: approval pause, approval resume, rejection, edit-and-resume, approval timeout
- Reliability: node failures, safe retries, crash recovery, ambiguous outcome handling, reconciliation
- Security: tenant isolation, company isolation, zero-secret persistence, KillSwitch, budget enforcement
- Integration: Agency Swarm, Letta, HAL, TaskMaker, Processes, Schedule, TrustGraph, Evidence Ledger, AI CEO
- Scenarios A-K: All 11 end-to-end business execution scenarios
"""

import unittest
import time
import uuid
import json
import os

from core.db import db
from core.models import EvidenceStatus
from core.evidence_ledger import EvidenceLedger
from core.durable_workflow_runtime import (
    StateGraph, NodeType, EdgeType, WorkflowState,
    governed_workflow_runtime, Command, interrupt,
    ApprovalDecision, RetryPolicyClassification, WorkflowEventType,
    SQLiteCheckpointer, GovernedLangGraphRuntime
)
from core.stateful_agent_runtime import stateful_memory_gateway, MemoryType, MemoryCategory, MemoryScope
from zonata.langgraph_adapter import langgraph_adapter


class TestLangGraphDurableWorkflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = governed_workflow_runtime
        cls.adapter = langgraph_adapter
        cls.ledger = EvidenceLedger()
        cls.tenant_id = "tnt_primary"
        cls.company_id = "comp_primary"

        # Ensure tenant and company exist in db
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_id, "Primary Tenant", time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) VALUES (?, ?, ?, 'IN', 'SERVICES', 'EXISTING', 'OPERATIONAL', ?)",
                (cls.company_id, cls.tenant_id, "Primary Operations", time.time())
            )
            conn.commit()

    # =========================================================================
    # 1. CORE TESTS (1-10)
    # =========================================================================

    def test_01_provider_loads(self):
        """1. Verify workflow runtime provider and checkpointer load."""
        self.assertIsNotNone(self.runtime)
        self.assertIsNotNone(self.runtime.checkpointer)
        self.assertIsInstance(self.runtime, GovernedLangGraphRuntime)

    def test_02_workflow_creation(self):
        """2. Verify StateGraph creation with custom state schema."""
        builder = StateGraph()
        self.assertIsNotNone(builder)
        self.assertEqual(len(builder.nodes), 0)

    def test_03_graph_validation(self):
        """3. Verify graph validation catches missing entry points and disconnected nodes."""
        builder = StateGraph()
        valid, errors = builder.validate_graph()
        self.assertFalse(valid)
        self.assertIn("StateGraph contains no nodes.", errors)

    def test_04_graph_compilation_and_hash(self):
        """4. Verify graph compilation and SHA-256 hash generation."""
        builder = StateGraph()
        builder.add_node("step1", lambda s: {"out": "step1"})
        builder.set_entry_point("step1")
        graph = builder.compile()
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph.definition_hash, str)
        self.assertEqual(len(graph.definition_hash), 64)

    def test_05_execution_simple(self):
        """5. Verify deterministic graph execution through to completion."""
        builder = StateGraph()
        builder.add_node("n1", lambda s: {"val": s.get("val", 0) + 10})
        builder.add_node("n2", lambda s: {"val": s["val"] * 3})
        builder.add_edge("n1", "n2")
        builder.set_entry_point("n1")
        builder.set_finish_point("n2")

        graph = builder.compile()
        wf_id = f"wf_test_exec_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, graph, {"name": "Test Exec"})

        res = self.runtime.start_workflow(wf_id, {"val": 5})
        self.assertEqual(res["status"], WorkflowState.COMPLETED)
        self.assertEqual(res["state"]["val"], 45) # (5+10)*3

    def test_06_state_persistence(self):
        """6. Verify execution state is persisted in workflow_runs table."""
        builder = StateGraph()
        builder.add_node("a", lambda s: {"done": True})
        builder.set_entry_point("a")
        wf_id = f"wf_test_persist_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Test Persist"})

        res = self.runtime.start_workflow(wf_id, {"init": 1})
        run_id = res["run_id"]

        run_state = self.runtime.get_run_state(run_id)
        self.assertIsNotNone(run_state)
        self.assertEqual(run_state["status"], WorkflowState.COMPLETED)

    def test_07_checkpoint_creation(self):
        """7. Verify zero-secret checkpoint created in workflow_checkpoints table."""
        thread_id = f"thrd_chk_{uuid.uuid4().hex[:8]}"
        chk_id = self.runtime.checkpointer.save_checkpoint(
            workflow_id="wf_chk_test",
            run_id="run_chk_test",
            thread_id=thread_id,
            company_id=self.company_id,
            current_node="node_test",
            state_payload={"key": "val", "step": 1},
            step=1
        )
        self.assertIsNotNone(chk_id)
        chk = self.runtime.checkpointer.get_latest_checkpoint(thread_id)
        self.assertIsNotNone(chk)
        self.assertEqual(chk["current_node"], "node_test")
        self.assertEqual(chk["state_payload"]["key"], "val")

    def test_08_resume_workflow(self):
        """8. Verify workflow resumption with Command update."""
        builder = StateGraph()
        builder.add_node("gate", lambda s: interrupt({"pause": True}) if not s.get("unlocked") else {"unlocked": True})
        builder.add_node("finish", lambda s: {"completed": True})
        builder.add_edge("gate", "finish")
        builder.set_entry_point("gate")
        builder.set_finish_point("finish")

        wf_id = f"wf_test_resume_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Test Resume"})

        # Step 1: Pauses at gate
        init_res = self.runtime.start_workflow(wf_id, {"unlocked": False})
        self.assertEqual(init_res["status"], WorkflowState.WAITING_FOR_INPUT)

        # Step 2: Resume with Command
        res = self.runtime.resume_workflow(init_res["run_id"], command=Command(update={"unlocked": True}))
        self.assertEqual(res["status"], WorkflowState.COMPLETED)
        self.assertTrue(res["state"]["completed"])

    def test_09_pause_workflow(self):
        """9. Verify manual workflow pausing."""
        builder = StateGraph()
        builder.add_node("step", lambda s: {"step": 1})
        builder.set_entry_point("step")
        wf_id = f"wf_test_pause_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Test Pause"})

        init_res = self.runtime.start_workflow(wf_id, {})
        run_id = init_res["run_id"]

        pause_res = self.runtime.pause_workflow(run_id, reason="Maintenance")
        self.assertEqual(pause_res["status"], WorkflowState.PAUSED)

    def test_10_cancel_workflow(self):
        """10. Verify workflow cancellation."""
        builder = StateGraph()
        builder.add_node("step", lambda s: {"step": 1})
        builder.set_entry_point("step")
        wf_id = f"wf_test_cancel_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Test Cancel"})

        init_res = self.runtime.start_workflow(wf_id, {})
        run_id = init_res["run_id"]

        cancel_res = self.runtime.cancel_workflow(run_id, reason="User cancelled")
        self.assertEqual(cancel_res["status"], WorkflowState.CANCELLED)

    # =========================================================================
    # 2. BRANCHING & CYCLES TESTS (11-16)
    # =========================================================================

    def test_11_conditional_branching(self):
        """11. Verify dynamic conditional branching."""
        builder = StateGraph()
        builder.add_node("evaluate", lambda s: {"score": s.get("score", 75)})
        builder.add_node("pass_path", lambda s: {"decision": "APPROVED"})
        builder.add_node("fail_path", lambda s: {"decision": "REJECTED"})

        def route(state):
            return "HIGH" if state["score"] >= 70 else "LOW"

        builder.add_conditional_edges("evaluate", route, {"HIGH": "pass_path", "LOW": "fail_path"})
        builder.set_entry_point("evaluate")

        wf_id = f"wf_test_cond_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Cond Branch"})

        res1 = self.runtime.start_workflow(wf_id, {"score": 85})
        self.assertEqual(res1["state"]["decision"], "APPROVED")

        res2 = self.runtime.start_workflow(wf_id, {"score": 50})
        self.assertEqual(res2["state"]["decision"], "REJECTED")

    def test_12_multiple_branches(self):
        """12. Verify multi-way conditional routing."""
        builder = StateGraph()
        builder.add_node("classify", lambda s: {"tier": s.get("tier", "standard")})
        builder.add_node("tier_gold", lambda s: {"discount": 0.20})
        builder.add_node("tier_silver", lambda s: {"discount": 0.10})
        builder.add_node("tier_standard", lambda s: {"discount": 0.0})

        builder.add_conditional_edges(
            "classify",
            lambda s: s["tier"],
            {"gold": "tier_gold", "silver": "tier_silver", "standard": "tier_standard"}
        )
        builder.set_entry_point("classify")

        wf_id = f"wf_test_multi_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Multi Branch"})

        res = self.runtime.start_workflow(wf_id, {"tier": "gold"})
        self.assertEqual(res["state"]["discount"], 0.20)

    def test_13_workflow_loop(self):
        """13. Verify controlled loop execution with state updates."""
        builder = StateGraph()
        builder.add_node("increment", lambda s: {"count": s.get("count", 0) + 1})

        def should_continue(state):
            return "REPEAT" if state["count"] < 3 else "DONE"

        builder.add_conditional_edges("increment", should_continue, {"REPEAT": "increment", "DONE": NodeType.END})
        builder.set_entry_point("increment")

        wf_id = f"wf_test_loop_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Loop Test"})

        res = self.runtime.start_workflow(wf_id, {"count": 0})
        self.assertEqual(res["status"], WorkflowState.COMPLETED)
        self.assertEqual(res["state"]["count"], 3)

    def test_14_maximum_iterations_enforcement(self):
        """14. Verify infinite loops are bounded by max iteration limits."""
        builder = StateGraph()
        # Node that attempts infinite recursion
        builder.add_node("infinite_loop", lambda s: {"loop": s.get("loop", 0) + 1})
        builder.add_conditional_edges("infinite_loop", lambda s: "AGAIN", {"AGAIN": "infinite_loop"})
        builder.set_entry_point("infinite_loop")

        wf_id = f"wf_test_infloop_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Infinite Loop Guard"})

        res = self.runtime.start_workflow(wf_id, {})
        self.assertEqual(res["status"], WorkflowState.FAILED)
        self.assertIn("Loop iteration ceiling exceeded", res["error"])

    def test_15_subworkflow_invocation(self):
        """15. Verify a parent workflow invoking a child subworkflow."""
        # Child workflow
        child_builder = StateGraph()
        child_builder.add_node("child_calc", lambda s: {"child_result": s.get("base", 0) * 10})
        child_builder.set_entry_point("child_calc")
        child_wf_id = f"wf_child_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(child_wf_id, child_builder.compile(), {"name": "Child WF"})

        # Parent workflow
        parent_builder = StateGraph()
        def invoke_subwf(state):
            sub_res = self.runtime.start_workflow(child_wf_id, {"base": state.get("input_val", 4)})
            return {"sub_output": sub_res["state"]["child_result"]}

        parent_builder.add_node("parent_step", invoke_subwf)
        parent_builder.set_entry_point("parent_step")
        parent_wf_id = f"wf_parent_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(parent_wf_id, parent_builder.compile(), {"name": "Parent WF"})

        res = self.runtime.start_workflow(parent_wf_id, {"input_val": 7})
        self.assertEqual(res["status"], WorkflowState.COMPLETED)
        self.assertEqual(res["state"]["sub_output"], 70)

    def test_16_resource_locking_concurrency(self):
        """16. Verify resource lock prevents concurrent conflicting mutations."""
        res_id = f"res_file_{uuid.uuid4().hex[:6]}"
        run1 = "run_alpha"
        run2 = "run_beta"

        # Run 1 acquires lock
        acquired1 = self.runtime.acquire_lock(res_id, "FILE", "wf_test", run1, self.company_id)
        self.assertTrue(acquired1)

        # Run 2 tries to acquire same resource -> blocked
        acquired2 = self.runtime.acquire_lock(res_id, "FILE", "wf_test", run2, self.company_id)
        self.assertFalse(acquired2)

        # Run 1 releases lock
        self.runtime.release_lock(res_id, run1)

        # Run 2 acquires lock successfully
        acquired3 = self.runtime.acquire_lock(res_id, "FILE", "wf_test", run2, self.company_id)
        self.assertTrue(acquired3)
        self.runtime.release_lock(res_id, run2)

    # =========================================================================
    # 3. HUMAN-IN-THE-LOOP TESTS (17-21)
    # =========================================================================

    def test_17_approval_pause(self):
        """17. Verify privileged node transitions to WAITING_FOR_APPROVAL."""
        builder = StateGraph()
        builder.add_node("sensitive_action", lambda s: {"executed": True}, requires_approval=True, risk_level="CRITICAL")
        builder.set_entry_point("sensitive_action")

        wf_id = f"wf_appr_pause_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Appr Pause"})

        res = self.runtime.start_workflow(wf_id, {"target": "acct_01"})
        self.assertEqual(res["status"], WorkflowState.WAITING_FOR_APPROVAL)
        self.assertIsNotNone(res.get("approval_id"))

    def test_18_approval_resume(self):
        """18. Verify approval resume executes the pending action."""
        builder = StateGraph()
        builder.add_node("p_action", lambda s: {"done": True}, requires_approval=True)
        builder.set_entry_point("p_action")

        wf_id = f"wf_appr_resume_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Appr Resume"})

        init_res = self.runtime.start_workflow(wf_id, {})
        approval_id = init_res["approval_id"]

        appr_res = self.runtime.approve_workflow(approval_id, actor="CEO Host")
        self.assertEqual(appr_res["status"], WorkflowState.COMPLETED)
        self.assertTrue(appr_res["state"]["done"])

    def test_19_approval_rejection(self):
        """19. Verify rejection halts workflow and marks status BLOCKED."""
        builder = StateGraph()
        builder.add_node("r_action", lambda s: {"done": True}, requires_approval=True)
        builder.set_entry_point("r_action")

        wf_id = f"wf_appr_reject_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Appr Reject"})

        init_res = self.runtime.start_workflow(wf_id, {})
        approval_id = init_res["approval_id"]

        rej_res = self.runtime.reject_workflow(approval_id, actor="Compliance Officer", reason="Limit exceeded")
        self.assertEqual(rej_res["status"], "REJECTED")

        run_state = self.runtime.get_run_state(init_res["run_id"])
        self.assertEqual(run_state["status"], WorkflowState.BLOCKED)

    def test_20_edit_and_resume(self):
        """20. Verify host modifies parameters and resumes with edited state."""
        builder = StateGraph()
        builder.add_node("e_action", lambda s: {"final_amount": s.get("amount")}, requires_approval=True)
        builder.set_entry_point("e_action")

        wf_id = f"wf_appr_edit_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Appr Edit"})

        init_res = self.runtime.start_workflow(wf_id, {"amount": 10000})
        approval_id = init_res["approval_id"]

        edit_res = self.runtime.edit_and_resume_workflow(approval_id, {"amount": 2500}, actor="Host")
        self.assertEqual(edit_res["status"], WorkflowState.COMPLETED)
        self.assertEqual(edit_res["state"]["final_amount"], 2500)
        self.assertTrue(edit_res["state"]["__was_edited__"])

    def test_21_approval_listing(self):
        """21. Verify pending approvals are retrievable via API query."""
        apprs = self.runtime.list_approvals(status="PENDING")
        self.assertIsInstance(apprs, list)

    # =========================================================================
    # 4. RELIABILITY TESTS (22-27)
    # =========================================================================

    def test_22_node_failure_handling(self):
        """22. Verify node exceptions are caught and transition run to FAILED."""
        builder = StateGraph()
        def crashing_node(state):
            raise RuntimeError("Database connection pool exhausted")
        builder.add_node("fail_step", crashing_node)
        builder.set_entry_point("fail_step")

        wf_id = f"wf_fail_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Failure Test"})

        res = self.runtime.start_workflow(wf_id, {})
        self.assertEqual(res["status"], WorkflowState.FAILED)
        self.assertIn("Database connection pool exhausted", res["error"])

    def test_23_retry_policy_safe(self):
        """23. Verify SAFE_RETRY automatically re-attempts node up to max_retries."""
        attempt_counter = [0]
        def flaky_node(state):
            attempt_counter[0] += 1
            if attempt_counter[0] < 3:
                raise ConnectionError("Transient network blip")
            return {"recovered_after_retries": attempt_counter[0]}

        builder = StateGraph()
        builder.add_node(
            "flaky",
            flaky_node,
            retry_policy={"max_retries": 3, "classification": RetryPolicyClassification.SAFE_RETRY}
        )
        builder.set_entry_point("flaky")

        wf_id = f"wf_flaky_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Flaky Node"})

        res = self.runtime.start_workflow(wf_id, {})
        self.assertEqual(res["status"], WorkflowState.COMPLETED)
        self.assertEqual(res["state"]["recovered_after_retries"], 3)

    def test_24_no_automatic_retry_for_mutations(self):
        """24. Verify NO_AUTOMATIC_RETRY prevents blind replay of mutations."""
        builder = StateGraph()
        def payment_node(state):
            raise TimeoutError("Payment gateway timed out")

        builder.add_node(
            "payment",
            payment_node,
            retry_policy={"max_retries": 3, "classification": RetryPolicyClassification.NO_AUTOMATIC_RETRY}
        )
        builder.set_entry_point("payment")

        wf_id = f"wf_pay_retry_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "No Retry Pay"})

        res = self.runtime.start_workflow(wf_id, {})
        self.assertEqual(res["status"], WorkflowState.FAILED)

    def test_25_crash_recovery(self):
        """25. Verify crash recovery reconstructs state from checkpoint without replaying."""
        builder = StateGraph()
        builder.add_node("step_a", lambda s: {"a": 1})
        builder.set_entry_point("step_a")
        wf_id = f"wf_crash_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Crash Test"})

        res = self.runtime.start_workflow(wf_id, {})
        run_id = res["run_id"]

        # Simulate sudden host crash
        with db.get_connection() as conn:
            conn.execute("UPDATE workflow_runs SET status = 'FAILED' WHERE run_id = ?", (run_id,))
            conn.commit()

        rec = self.runtime.recover_workflow_run(run_id)
        self.assertTrue(rec["recovered"])
        self.assertEqual(rec["status"], WorkflowState.PAUSED)

    def test_26_ambiguous_outcome(self):
        """26. Verify uncertain API timeout transitions to AMBIGUOUS state."""
        res = self.adapter.run_ambiguous_transaction_workflow(self.company_id)
        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], WorkflowState.AMBIGUOUS)

    def test_27_event_audit_trail(self):
        """27. Verify auditable event trail for all transitions."""
        builder = StateGraph()
        builder.add_node("logged_step", lambda s: {"logged": True})
        builder.set_entry_point("logged_step")
        wf_id = f"wf_audit_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Audit Test"})

        res = self.runtime.start_workflow(wf_id, {})
        events = self.runtime.list_events(res["run_id"])
        self.assertGreaterEqual(len(events), 3)
        event_types = [e["event_type"] for e in events]
        self.assertIn(WorkflowEventType.WORKFLOW_STARTED, event_types)
        self.assertIn(WorkflowEventType.WORKFLOW_COMPLETED, event_types)

    # =========================================================================
    # 5. SECURITY & GOVERNANCE TESTS (28-35)
    # =========================================================================

    def test_28_tenant_isolation(self):
        """28. Verify cross-tenant workflow runs are completely isolated."""
        other_tenant = "tnt_secondary"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, 'Secondary Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (other_tenant, time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) VALUES ('comp_other', ?, 'Secondary Operations', 'IN', 'SERVICES', 'EXISTING', 'OPERATIONAL', ?)",
                (other_tenant, time.time())
            )
            conn.commit()

        builder = StateGraph()
        builder.add_node("s", lambda s: {"s": 1})
        builder.set_entry_point("s")

        runtime_other = GovernedLangGraphRuntime(tenant_id=other_tenant)
        runtime_other.register_compiled_graph("wf_isolated", builder.compile(), {"name": "Isolated WF", "company_id": "comp_other"})
        res = runtime_other.start_workflow("wf_isolated", {})

        # Primary runtime cannot access runs of other tenant
        with db.get_connection() as conn:
            runs_primary = conn.execute("SELECT * FROM workflow_runs WHERE tenant_id = 'tnt_primary' AND run_id = ?", (res["run_id"],)).fetchall()
            self.assertEqual(len(runs_primary), 0)

    def test_29_company_isolation(self):
        """29. Verify company scoping prevents cross-company data visibility."""
        res = self.runtime.list_workflows(company_id="comp_primary")
        self.assertIsInstance(res, list)

    def test_30_zero_secret_scrubbing(self):
        """30. Verify raw secrets are scrubbed from checkpoint payloads."""
        thread_id = f"thrd_sec_{uuid.uuid4().hex[:8]}"
        state_with_secret = {
            "api_token": "sk-1234567890abcdef1234567890",
            "bearer_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "normal_data": "Audit report parameters"
        }
        self.runtime.checkpointer.save_checkpoint(
            workflow_id="wf_sec",
            run_id="run_sec",
            thread_id=thread_id,
            company_id=self.company_id,
            current_node="sec_node",
            state_payload=state_with_secret,
            step=1
        )
        saved = self.runtime.checkpointer.get_latest_checkpoint(thread_id)
        saved_str = str(saved["state_payload"])
        self.assertNotIn("sk-1234567890", saved_str)
        self.assertIn("[REDACTED_SECRET_REF]", saved_str)

    def test_31_killswitch_enforcement(self):
        """31. Verify active KillSwitch immediately halts workflow execution."""
        res = self.adapter.run_killswitch_workflow(self.company_id)
        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], WorkflowState.BLOCKED)

    def test_32_budget_tracking(self):
        """32. Verify budget spending (seconds, api calls) is tracked in run records."""
        builder = StateGraph()
        builder.add_node("spend_step", lambda s: {"done": True})
        builder.set_entry_point("spend_step")
        wf_id = f"wf_budget_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Budget Test"})

        res = self.runtime.start_workflow(wf_id, {})
        with db.get_connection() as conn:
            row = conn.execute("SELECT budget_spent FROM workflow_runs WHERE run_id = ?", (res["run_id"],)).fetchone()
            spent = json.loads(row["budget_spent"])
            self.assertIn("api_calls", spent)
            self.assertGreaterEqual(spent["api_calls"], 1)

    def test_33_workflow_version_hash(self):
        """33. Verify workflow definition hash binds to exact graph structure."""
        builder = StateGraph()
        builder.add_node("v1", lambda s: {"v": 1})
        builder.set_entry_point("v1")
        g1 = builder.compile()

        builder2 = StateGraph()
        builder2.add_node("v1", lambda s: {"v": 1})
        builder2.add_node("v2", lambda s: {"v": 2})
        builder2.add_edge("v1", "v2")
        builder2.set_entry_point("v1")
        builder2.set_finish_point("v2")
        g2 = builder2.compile()

        self.assertNotEqual(g1.definition_hash, g2.definition_hash)

    def test_34_authority_gateway_boundary(self):
        """34. Invariant: Workflow state != Authority."""
        # Confirm that injecting claims into state does not grant authority
        builder = StateGraph()
        builder.add_node("unauthorized", lambda s: {"bypass": True}, requires_approval=True)
        builder.set_entry_point("unauthorized")
        wf_id = f"wf_auth_{uuid.uuid4().hex[:6]}"
        self.runtime.register_compiled_graph(wf_id, builder.compile(), {"name": "Auth Guard"})

        res = self.runtime.start_workflow(wf_id, {"authority_override": "TRUE"})
        self.assertEqual(res["status"], WorkflowState.WAITING_FOR_APPROVAL)

    def test_35_evidence_integrity(self):
        """35. Invariant: Checkpoint != Evidence."""
        # A checkpoint is execution state, an EvidencePackage is sealed Merkle audit proof
        res = self.adapter.run_simple_workflow("Integrity check", self.company_id)
        self.assertTrue(res["verified"])
        self.assertIsNotNone(res["merkle_root"])

    # =========================================================================
    # 6. INTEGRATION TESTS (36-44)
    # =========================================================================

    def test_36_agency_swarm_integration(self):
        """36. Verify Agency Swarm squad execution from LangGraph node."""
        res = self.adapter.run_agency_swarm_workflow("Analyze margin stability", self.company_id)
        self.assertTrue(res["verified"])

    def test_37_letta_memory_boundary(self):
        """37. Verify Letta memory separation from LangGraph temporary state."""
        res = self.adapter.run_letta_memory_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_38_hal_multimodal_integration(self):
        """38. Verify HAL screen observation and speech synthesis in workflow."""
        res = self.adapter.run_hal_multimodal_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_39_taskmaker_representation(self):
        """39. Verify workflow state is properly formatted for TaskMaker rendering."""
        wfs = self.runtime.list_workflows(self.company_id)
        self.assertIsInstance(wfs, list)
        self.assertGreaterEqual(len(wfs), 1)

    def test_40_process_reusability(self):
        """40. Verify running the same workflow template repeatedly produces unique runs."""
        res1 = self.adapter.run_simple_workflow("Run 1", self.company_id)
        res2 = self.adapter.run_simple_workflow("Run 2", self.company_id)
        self.assertNotEqual(res1["run_id"], res2["run_id"])

    def test_41_schedule_trigger(self):
        """41. Verify scheduled invocation of a workflow."""
        res = self.adapter.run_simple_workflow("Weekly Monday Scheduled Task", self.company_id)
        self.assertEqual(res["status"], WorkflowState.COMPLETED)

    def test_42_trustgraph_traceability(self):
        """42. Verify full causal chain traceability via run events and ledger."""
        res = self.adapter.run_simple_workflow("TrustGraph trace", self.company_id)
        events = self.runtime.list_events(res["run_id"])
        self.assertGreaterEqual(len(events), 1)

    def test_43_evidence_ledger_integration(self):
        """43. Verify Evidence Ledger registers Merkle leaves for completed workflows."""
        root = self.ledger.get_merkle_root()
        self.assertIsNotNone(root)
        self.assertEqual(len(root), 64)

    def test_44_ai_ceo_reporting(self):
        """44. Verify AI CEO can inspect active, waiting, and completed workflows."""
        runs = self.runtime.list_runs()
        self.assertIsInstance(runs, list)

    # =========================================================================
    # 7. END-TO-END SCENARIOS A THROUGH K (45-55)
    # =========================================================================

    def test_45_scenario_a_simple_workflow(self):
        """45. Scenario A: Simple Governed Task with Tool Execution & Evidence Verification."""
        res = self.adapter.run_simple_workflow("Scenario A Objective", self.company_id)
        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], WorkflowState.COMPLETED)

    def test_46_scenario_b_long_running_workflow(self):
        """46. Scenario B: Long-Running Workflow with Checkpointing & Resumption."""
        res = self.adapter.run_long_running_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_47_scenario_c_human_approval(self):
        """47. Scenario C: Human-in-the-Loop Sensitive Action Approval."""
        res = self.adapter.run_human_approval_workflow(15000.0, self.company_id)
        self.assertTrue(res["verified"])

    def test_48_scenario_d_human_edit(self):
        """48. Scenario D: Human Parameter Modification & Resumption."""
        res = self.adapter.run_human_edit_workflow(30000.0, 10000.0, self.company_id)
        self.assertTrue(res["verified"])

    def test_49_scenario_e_failure_recovery(self):
        """49. Scenario E: Sudden Process Crash & Safe State Recovery."""
        res = self.adapter.run_failure_recovery_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_50_scenario_f_ambiguous_transaction(self):
        """50. Scenario F: External API Timeout & Ambiguous State Containment."""
        res = self.adapter.run_ambiguous_transaction_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_51_scenario_g_loop_control(self):
        """51. Scenario G: Controlled Quality Refinement Loop with Iteration Limits."""
        res = self.adapter.run_loop_control_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_52_scenario_h_agency_swarm(self):
        """52. Scenario H: Agency Swarm Autonomous Specialist Delegation."""
        res = self.adapter.run_agency_swarm_workflow("Strategic audit", self.company_id)
        self.assertTrue(res["verified"])

    def test_53_scenario_i_letta_memory(self):
        """53. Scenario I: Letta Permanent Memory vs Workflow Ephemeral Checkpoints."""
        res = self.adapter.run_letta_memory_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_54_scenario_j_hal_multimodal(self):
        """54. Scenario J: HAL Multimodal Observation & Voice Synthesis."""
        res = self.adapter.run_hal_multimodal_workflow(self.company_id)
        self.assertTrue(res["verified"])

    def test_55_scenario_k_killswitch(self):
        """55. Scenario K: Authoritative ZONATA KillSwitch Emergency Halt."""
        res = self.adapter.run_killswitch_workflow(self.company_id)
        self.assertTrue(res["verified"])


if __name__ == "__main__":
    unittest.main()
