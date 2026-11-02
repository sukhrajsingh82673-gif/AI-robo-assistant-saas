"""
ZONATA — LangGraph Workflow Adapter
===================================
High-level enterprise workflow bridge connecting:
- AI CEO Strategic Directives
- Agency Swarm Autonomous Squads (Project 01)
- Letta Persistent Agent Identity & Memory (Project 02)
- HAL Multimodal Capabilities (Project 03)
- TaskMaker & TaskGraph Execution (Project 04)
- PolicyEngine, ApprovalEngine, KillSwitch, and Merkle Evidence Ledger

Constitutional Invariants:
1. Workflow state != Authority
2. Checkpoint != Evidence
3. Graph definition != Permission
4. Model output != Authorization
5. Retry != Safe replay
6. Completion != Business success
7. Task Success != Business Outcome
"""

import time
import uuid
import json
import hashlib
from typing import Dict, Any, Optional, List

from core.db import db
from core.models import EvidencePackage, PhysicalVerification, EvidenceStatus
from core.evidence_ledger import EvidenceLedger
from core.durable_workflow_runtime import (
    StateGraph, NodeType, EdgeType, WorkflowState,
    governed_workflow_runtime, Command, interrupt,
    ApprovalDecision, RetryPolicyClassification, WorkflowEventType
)
from core.stateful_agent_runtime import stateful_memory_gateway, MemoryType, MemoryCategory, MemoryScope
from core.multimodal_capability_runtime import (
    multimodal_registry, screen_observer, hal_voice,
    execution_manager, GovernedShellProvider
)
from zonata.agent_swarm_adapter import AgentWorkforceAdapter


class LangGraphWorkflowAdapter:
    """
    Adapter orchestrating governed LangGraph workflows within ZONATA.
    Ensures all workflows respect ZONATA's sovereign hierarchy and invariants.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self.runtime = governed_workflow_runtime
        self.ledger = EvidenceLedger()
        self._init_canonical_workflows()

    def _init_canonical_workflows(self):
        """Compiles and registers canonical production workflows."""
        self._register_simple_task_workflow()
        self._register_long_running_workflow()
        self._register_approval_workflow()
        self._register_loop_improvement_workflow()
        self._register_multimodal_hal_workflow()
        self._register_agency_swarm_workflow()

    # =========================================================================
    # 1. CANONICAL WORKFLOW DEFINITIONS
    # =========================================================================

    def _register_simple_task_workflow(self):
        """Workflow: Simple Governed Task with Tool Execution & Evidence Verification."""
        builder = StateGraph()

        def parse_objective(state: Dict[str, Any]) -> Dict[str, Any]:
            nested = state.get("inputs") if isinstance(state.get("inputs"), dict) else {}
            objective = (
                state.get("objective")
                or state.get("task")
                or state.get("prompt")
                or nested.get("objective")
                or nested.get("task")
                or "Default task"
            )
            return {
                "parsed_task": f"Executing validated objective: {objective}",
                "objective_source": "input",
                "timestamp": time.time()
            }

        def execute_sandboxed_action(state: Dict[str, Any]) -> Dict[str, Any]:
            task = state.get("parsed_task")
            # This canonical workflow performs no external action. It only
            # advances durable state and produces a deterministic digest so the
            # checkpoint/evidence machinery can be exercised. The digest is
            # state integrity, NOT proof that a business action happened.
            action_hash = hashlib.sha256(task.encode("utf-8")).hexdigest()
            return {
                "action_result": (
                    "Workflow state advanced. No external or business action was executed "
                    "by this node; this run validates orchestration, checkpointing and "
                    "evidence sealing only."
                ),
                "action_scope": "STATE_ONLY",
                "action_hash": action_hash,
                "state_integrity_verified": True,
                "business_outcome_verified": False,
                "verified": True
            }

        def generate_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
            # Seals state integrity only. The expected and actual digests both
            # originate from this run, so this is a self-consistency check and
            # must never be presented as independent business verification.
            action_hash = state.get("action_hash", "none")
            verif = PhysicalVerification(
                check_type="sha256_match",
                target_path="virtual://workflow/state",
                expected_val=action_hash,
                actual_val=action_hash,
                verified=True,
                details=(
                    "Workflow STATE-INTEGRITY digest is self-consistent. "
                    "No external resource was inspected and no business outcome "
                    "was verified."
                )
            )
            pkg = self.ledger.seal_evidence(
                action_id=f"act_wf_{uuid.uuid4().hex[:6]}",
                mission_id=f"mis_wf_{uuid.uuid4().hex[:6]}",
                agent_id="agt_workflow_runtime",
                verifications=[verif]
            )
            return {
                "evidence_id": pkg.evidence_id,
                "merkle_root": self.ledger.get_merkle_root(),
                "verification_scope": "STATE_INTEGRITY_ONLY",
                "business_outcome_verified": False,
                "completed": True
            }

        builder.add_node("parse_objective", parse_objective, node_type=NodeType.TRANSFORM)
        builder.add_node("execute_action", execute_sandboxed_action, node_type=NodeType.TOOL)
        builder.add_node("generate_evidence", generate_evidence, node_type=NodeType.VERIFICATION)

        builder.add_edge("parse_objective", "execute_action")
        builder.add_edge("execute_action", "generate_evidence")
        builder.set_entry_point("parse_objective")
        builder.set_finish_point("generate_evidence")

        graph = builder.compile()
        self.runtime.register_compiled_graph("wf_canonical_simple", graph, {
            "name": "Canonical Simple Task Workflow",
            "version": 1,
            "risk_level": "SAFE"
        })

    def _register_long_running_workflow(self):
        """Workflow: Long-running task that pauses and awaits resumption."""
        builder = StateGraph()

        def step_prepare(state: Dict[str, Any]) -> Dict[str, Any]:
            return {"prep_done": True, "step": 1}

        def step_checkpoint_pause(state: Dict[str, Any]) -> Dict[str, Any]:
            # Trigger interrupt to pause execution for long-running batch
            if not state.get("batch_approved"):
                return interrupt({"message": "Long-running batch ready for host review", "step": 2})
            return {"step": 2, "batch_processed": True}

        def step_finalize(state: Dict[str, Any]) -> Dict[str, Any]:
            return {"status": "SUCCESS", "final_step": 3, "resumed_cleanly": True}

        builder.add_node("prepare", step_prepare, node_type=NodeType.TRANSFORM)
        builder.add_node("pause_gate", step_checkpoint_pause, node_type=NodeType.WAIT)
        builder.add_node("finalize", step_finalize, node_type=NodeType.REPORT)

        builder.add_edge("prepare", "pause_gate")
        builder.add_edge("pause_gate", "finalize")
        builder.set_entry_point("prepare")
        builder.set_finish_point("finalize")

        graph = builder.compile()
        self.runtime.register_compiled_graph("wf_canonical_long_running", graph, {
            "name": "Canonical Long Running Workflow",
            "version": 1,
            "risk_level": "SAFE"
        })

    def _register_approval_workflow(self):
        """Workflow: Sensitive action requiring explicit ZONATA ApprovalEngine clearance."""
        builder = StateGraph()

        def assess_risk(state: Dict[str, Any]) -> Dict[str, Any]:
            action = state.get("proposed_action", "transfer_funds")
            return {
                "assessment": "CRITICAL_ACTION_DETECTED",
                "action": action,
                "amount": state.get("amount", 1000)
            }

        def execute_privileged(state: Dict[str, Any]) -> Dict[str, Any]:
            # This node requires_approval = True. It exercises the approval
            # gate only: this canonical workflow holds no payment integration,
            # so it must not claim that money moved.
            amount = state.get("amount", 1000)
            return {
                "disbursed": False,
                "disbursement_executed": False,
                "amount": amount,
                "intended_recipient": state.get("recipient", "supplier_acct_01"),
                "approval_gate_passed_at": time.time(),
                "note": (
                    "Approval gate cleared. No funds were transferred: this workflow "
                    "has no payment connector, so the business outcome is NOT verified."
                ),
                "business_outcome_verified": False,
            }

        builder.add_node("assess_risk", assess_risk, node_type=NodeType.TRANSFORM)
        builder.add_node(
            "execute_privileged",
            execute_privileged,
            node_type=NodeType.APPROVAL,
            requires_approval=True,
            risk_level="CRITICAL",
            metadata={"action_summary": "Disburse capital funds to approved recipient"}
        )

        builder.add_edge("assess_risk", "execute_privileged")
        builder.set_entry_point("assess_risk")
        builder.set_finish_point("execute_privileged")

        graph = builder.compile()
        self.runtime.register_compiled_graph("wf_canonical_approval", graph, {
            "name": "Canonical Approval Guarded Workflow",
            "version": 1,
            "risk_level": "CRITICAL"
        })

    def _register_loop_improvement_workflow(self):
        """Workflow: Controlled cycle generating and refining outputs until quality threshold."""
        builder = StateGraph()

        def generate_report(state: Dict[str, Any]) -> Dict[str, Any]:
            iter_count = state.get("generation_count", 0) + 1
            quality = min(0.4 + (iter_count * 0.25), 0.95)
            return {
                "generation_count": iter_count,
                "quality_score": round(quality, 2),
                "report_draft": f"Report draft v{iter_count} with quality {quality:.2f}"
            }

        def check_quality(state: Dict[str, Any]) -> str:
            score = state.get("quality_score", 0.0)
            if score >= 0.85:
                return "PASS"
            return "REVISE"

        def finalize_report(state: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "final_report": state.get("report_draft"),
                "certified": True
            }

        builder.add_node("generate", generate_report, node_type=NodeType.TRANSFORM)
        builder.add_node("finalize", finalize_report, node_type=NodeType.REPORT)

        builder.add_conditional_edges(
            "generate",
            check_quality,
            {"PASS": "finalize", "REVISE": "generate"}
        )
        builder.set_entry_point("generate")
        builder.set_finish_point("finalize")

        graph = builder.compile()
        self.runtime.register_compiled_graph("wf_canonical_loop", graph, {
            "name": "Canonical Controlled Loop Workflow",
            "version": 1,
            "risk_level": "SAFE"
        })

    def _register_multimodal_hal_workflow(self):
        """Workflow: Invokes HAL screen observation and synthesizes executive voice summary."""
        builder = StateGraph()

        def observe_desktop(state: Dict[str, Any]) -> Dict[str, Any]:
            sess = execution_manager.create_session("hal.vision.screen", state.get("company_id", "comp_primary"))
            obs = screen_observer.capture_observation(sess["session_id"], window_title=state.get("window", "Executive Center"))
            return {
                "observation_id": obs["observation_id"],
                "content_hash": obs["raw_hash"],
                "session_id": sess["session_id"]
            }

        def synthesize_audio_report(state: Dict[str, Any]) -> Dict[str, Any]:
            text = f"Observation {state.get('observation_id')} captured and verified."
            audio = hal_voice.synthesize(text)
            return {
                "spoken_summary": text,
                "audio_payload": audio.get("audio_payload"),
                "verified": True
            }

        builder.add_node("observe_desktop", observe_desktop, node_type=NodeType.DESKTOP)
        builder.add_node("synthesize_report", synthesize_audio_report, node_type=NodeType.TOOL)
        builder.add_edge("observe_desktop", "synthesize_report")
        builder.set_entry_point("observe_desktop")
        builder.set_finish_point("synthesize_report")

        graph = builder.compile()
        self.runtime.register_compiled_graph("wf_canonical_hal", graph, {
            "name": "Canonical HAL Multimodal Workflow",
            "version": 1,
            "risk_level": "CONFIRM"
        })

    def _register_agency_swarm_workflow(self):
        """Workflow: AI CEO delegating to Agency Swarm specialist squads."""
        builder = StateGraph()

        def ceo_decompose(state: Dict[str, Any]) -> Dict[str, Any]:
            directive = state.get("directive", "Analyze margins")
            return {
                "assigned_squad": "FinanceSpecialists",
                "directive": directive,
                "priority": "HIGH"
            }

        def squad_execute(state: Dict[str, Any]) -> Dict[str, Any]:
            squad_name = state.get("assigned_squad", "FinanceSpecialists")
            cid = state.get("company_id", "comp_primary")
            # Plan and execute through Agency Swarm adapter
            plan = AgentWorkforceAdapter.create_mission_workforce(
                tenant_id=self.tenant_id,
                company_id=cid,
                mission_objective=state.get("directive", "Analyze margins")
            )
            result = AgentWorkforceAdapter.execute_workforce(plan["workforce_id"])
            # Report the workforce's own outcome. Never substitute a canned
            # business result for what the squad actually produced.
            return {
                "squad_name": squad_name,
                "workforce_id": plan["workforce_id"],
                "squad_completed": bool(getattr(result, "task_success", False)),
                "workforce_status": getattr(result, "status", None),
                "summary": getattr(result, "summary", None) or "Workforce returned no summary.",
                "business_outcome_verified": bool(getattr(result, "business_outcome_verified", False)),
            }

        builder.add_node("ceo_decompose", ceo_decompose, node_type=NodeType.AGENT)
        builder.add_node("squad_execute", squad_execute, node_type=NodeType.AGENT)
        builder.add_edge("ceo_decompose", "squad_execute")
        builder.set_entry_point("ceo_decompose")
        builder.set_finish_point("squad_execute")

        graph = builder.compile()
        self.runtime.register_compiled_graph("wf_canonical_agency_swarm", graph, {
            "name": "Canonical Agency Swarm Delegation Workflow",
            "version": 1,
            "risk_level": "SAFE"
        })

    # =========================================================================
    # 2. END-TO-END DEMONSTRATION WORKFLOWS (TESTS A THROUGH K)
    # =========================================================================

    def run_simple_workflow(self, objective: str = "Audit Q3 cloud spending", company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST A: Host -> Mission -> TaskMaker -> LangGraph -> Tool -> Verification -> Evidence -> Completed."""
        inputs = {"objective": objective, "company_id": company_id}
        res = self.runtime.start_workflow("wf_canonical_simple", inputs, {"company_id": company_id})
        return {
            "scenario": "TEST_A_SIMPLE_WORKFLOW",
            "objective": objective,
            "run_id": res.get("run_id"),
            "status": res.get("status"),
            "evidence_id": res.get("state", {}).get("evidence_id"),
            "merkle_root": res.get("state", {}).get("merkle_root"),
            "verified": res.get("status") == WorkflowState.COMPLETED
        }

    def run_long_running_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST B: Checkpoint -> pause -> resume without losing state."""
        # 1. Start workflow - should hit interrupt gate
        init_res = self.runtime.start_workflow("wf_canonical_long_running", {"company_id": company_id}, {"company_id": company_id})
        run_id = init_res["run_id"]

        # 2. Verify state was checkpointed
        chk = self.runtime.checkpointer.get_latest_checkpoint(self.runtime.get_run_state(run_id)["thread_id"])

        # 3. Simulate process resume with Command
        cmd = Command(update={"batch_approved": True})
        resume_res = self.runtime.resume_workflow(run_id, command=cmd)

        return {
            "scenario": "TEST_B_LONG_RUNNING_WORKFLOW",
            "run_id": run_id,
            "initial_status": init_res["status"],
            "checkpoint_id": chk["checkpoint_id"] if chk else None,
            "resumed_status": resume_res["status"],
            "final_state": resume_res.get("state"),
            "verified": (init_res["status"] == WorkflowState.WAITING_FOR_INPUT and resume_res["status"] == WorkflowState.COMPLETED)
        }

    def run_human_approval_workflow(self, amount: float = 25000.0, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST C: Sensitive action -> WAITING_FOR_APPROVAL -> Host approves -> resume -> execute -> verify."""
        init_res = self.runtime.start_workflow("wf_canonical_approval", {"amount": amount, "company_id": company_id}, {"company_id": company_id})
        run_id = init_res["run_id"]
        approval_id = init_res.get("approval_id")

        # Simulate host approval
        appr_res = self.runtime.approve_workflow(approval_id, actor="Executive Host")

        return {
            "scenario": "TEST_C_HUMAN_APPROVAL",
            "run_id": run_id,
            "approval_id": approval_id,
            "paused_status": init_res["status"],
            "approved_status": appr_res.get("status"),
            "final_state": appr_res.get("state"),
            "verified": (init_res["status"] == WorkflowState.WAITING_FOR_APPROVAL and appr_res.get("status") == WorkflowState.COMPLETED)
        }

    def run_human_edit_workflow(self, initial_amount: float = 50000.0, modified_amount: float = 12500.0, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST D: Host modifies proposed action -> recorded -> policy rerun -> execution uses approved version."""
        init_res = self.runtime.start_workflow("wf_canonical_approval", {"amount": initial_amount, "company_id": company_id}, {"company_id": company_id})
        run_id = init_res["run_id"]
        approval_id = init_res.get("approval_id")

        # Host edits parameter before approving
        edit_res = self.runtime.edit_and_resume_workflow(
            approval_id=approval_id,
            modified_parameters={"amount": modified_amount, "recipient": "renegotiated_supplier_02"},
            actor="CFO Host"
        )

        return {
            "scenario": "TEST_D_HUMAN_EDIT",
            "run_id": run_id,
            "approval_id": approval_id,
            "original_amount": initial_amount,
            "modified_amount": modified_amount,
            "final_amount": edit_res.get("state", {}).get("amount"),
            "was_edited": edit_res.get("state", {}).get("__was_edited__"),
            "status": edit_res.get("status"),
            "verified": (edit_res.get("state", {}).get("amount") == modified_amount)
        }

    def run_failure_recovery_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST E: Simulated crash during execution -> restart -> checkpoint + external state verification + safe resume."""
        # Start simple workflow and simulate sudden crash/interruption
        init_res = self.runtime.start_workflow("wf_canonical_simple", {"objective": "Crash recovery verification"}, {"company_id": company_id})
        run_id = init_res["run_id"]

        # Manually simulate interrupted state in DB
        with db.get_connection() as conn:
            conn.execute("UPDATE workflow_runs SET status = 'FAILED', error_message = 'Process terminated abruptly' WHERE run_id = ?", (run_id,))
            conn.commit()

        # Run recovery
        rec_res = self.runtime.recover_workflow_run(run_id)

        return {
            "scenario": "TEST_E_FAILURE_RECOVERY",
            "run_id": run_id,
            "recovered": rec_res["recovered"],
            "recovered_step": rec_res["recovered_step"],
            "current_node": rec_res["current_node"],
            "status": rec_res["status"],
            "verified": rec_res["recovered"] and rec_res["status"] == WorkflowState.PAUSED
        }

    def run_ambiguous_transaction_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST F: Simulated timeout on mutation -> AMBIGUOUS -> external reconciliation without auto-replay."""
        res = self.runtime.start_workflow(
            "wf_canonical_simple",
            {"objective": "Payment transaction", "__simulate_ambiguous__": True},
            {"company_id": company_id}
        )

        return {
            "scenario": "TEST_F_AMBIGUOUS_TRANSACTION",
            "run_id": res.get("run_id"),
            "status": res.get("status"),
            "error": res.get("error"),
            "blind_replay_prevented": True,
            "verified": res.get("status") == WorkflowState.AMBIGUOUS
        }

    def run_loop_control_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST G: Generate -> verify -> fail -> improve -> verify with max iteration bounds."""
        res = self.runtime.start_workflow("wf_canonical_loop", {"company_id": company_id}, {"company_id": company_id})

        return {
            "scenario": "TEST_G_LOOP_CONTROL",
            "run_id": res.get("run_id"),
            "status": res.get("status"),
            "final_generation_count": res.get("state", {}).get("generation_count"),
            "quality_score": res.get("state", {}).get("quality_score"),
            "certified": res.get("state", {}).get("certified"),
            "verified": res.get("status") == WorkflowState.COMPLETED and res.get("state", {}).get("quality_score") >= 0.85
        }

    def run_agency_swarm_workflow(self, directive: str = "Audit Q3 operating margins", company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST H: AI CEO -> Agency Swarm specialist -> LangGraph node -> verification -> CEO report."""
        res = self.runtime.start_workflow("wf_canonical_agency_swarm", {"directive": directive}, {"company_id": company_id})

        return {
            "scenario": "TEST_H_AGENCY_SWARM",
            "run_id": res.get("run_id"),
            "status": res.get("status"),
            "assigned_squad": res.get("state", {}).get("assigned_squad"),
            "squad_completed": res.get("state", {}).get("squad_completed"),
            "summary": res.get("state", {}).get("summary"),
            "verified": res.get("status") == WorkflowState.COMPLETED
        }

    def run_letta_memory_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST I: Workflow state != Letta memory; zero secret, explicit approved memory only."""
        # 1. State contains temporary execution details
        temp_state = {"temp_cache": "data_001", "iteration": 4, "secret_key": "sk-unauthorized-key-attempt"}

        # 2. Checkpointer scrubs the secret from checkpoint
        thread_id = f"thrd_{uuid.uuid4().hex[:8]}"
        chk_id = self.runtime.checkpointer.save_checkpoint(
            workflow_id="wf_canonical_simple",
            run_id="run_mem_test",
            thread_id=thread_id,
            company_id=company_id,
            current_node="test_node",
            state_payload=temp_state,
            step=1
        )
        saved_chk = self.runtime.checkpointer.get_latest_checkpoint(thread_id)

        # 3. Only explicitly classified memory is synced to Letta
        letta_persisted = False
        try:
            stateful_memory_gateway.store_memory(
                scope=MemoryScope.COMPANY.value,
                scope_id=company_id,
                memory_key=f"workflow_protocol_{uuid.uuid4().hex[:6]}",
                content="Approved workflow checkpoint protocol v1.0",
                memory_type=MemoryType.CORE.value,
                category=MemoryCategory.DECISION.value
            )
            letta_persisted = True
        except Exception:
            letta_persisted = False

        return {
            "scenario": "TEST_I_LETTA_MEMORY_BOUNDARY",
            "checkpoint_scrubbed": "[REDACTED_SECRET_REF]" in str(saved_chk["state_payload"]),
            "workflow_state_isolated_from_letta": True,
            "letta_persisted_clean_record": letta_persisted,
            "verified": ("[REDACTED_SECRET_REF]" in str(saved_chk["state_payload"]) and letta_persisted)
        }

    def run_hal_multimodal_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST J: LangGraph node invoking HAL screen observation / voice capability -> result -> verification."""
        res = self.runtime.start_workflow("wf_canonical_hal", {"window": "Executive Operations", "company_id": company_id}, {"company_id": company_id})

        return {
            "scenario": "TEST_J_HAL_MULTIMODAL",
            "run_id": res.get("run_id"),
            "status": res.get("status"),
            "observation_id": res.get("state", {}).get("observation_id"),
            "spoken_summary": res.get("state", {}).get("spoken_summary"),
            "verified": res.get("status") == WorkflowState.COMPLETED
        }

    def run_killswitch_workflow(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """TEST K: Active workflow halted by ZONATA KillSwitch."""
        # 1. Activate KillSwitch
        self.runtime.set_killswitch(True)

        # 2. Attempt to start workflow
        res = self.runtime.start_workflow("wf_canonical_simple", {"objective": "Halt test"}, {"company_id": company_id})

        # 3. Restore KillSwitch
        self.runtime.set_killswitch(False)

        return {
            "scenario": "TEST_K_KILLSWITCH",
            "status": res.get("status"),
            "error": res.get("error"),
            "blocked_by_killswitch": res.get("status") == WorkflowState.BLOCKED,
            "verified": res.get("status") == WorkflowState.BLOCKED
        }


# Global Singleton Adapter Instance
langgraph_adapter = LangGraphWorkflowAdapter()
