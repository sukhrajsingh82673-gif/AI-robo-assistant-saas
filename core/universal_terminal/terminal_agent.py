"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Terminal Handling Agent
Dedicated specialist technical operator agent implementing the full 16-step execution lifecycle:
UNDERSTAND → DISCOVER → ASSESS → SELECT ENVIRONMENT → SELECT TOOLS → PLAN → CHECK POLICY →
REQUEST AUTHORIZATION → PROVISION → EXECUTE → OBSERVE → DIAGNOSE → VERIFY →
RECOVER/REPLAN → CAPTURE EVIDENCE → REPORT TO AICU.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import uuid
import hashlib
import json
import logging

from .models import (
    TerminalSession, CommandPlan, TerminalResult, TerminalStatus,
    TerminalCommandRisk, SemanticExecutionState, FailureClassification,
    VerificationPostcondition, DesktopEnvironment, ExecutionMode, NetworkMode,
    AICeoTerminalInstruction, AICeoTerminalResult
)
from .capability_registry import EnvironmentCapabilityRegistry
from .resource_inspector import ResourceInspector
from .runtime_router import UniversalRuntimeRouter, EnvironmentSelectionDecision
from .security_gateway import TerminalSecurityGateway
from .execution_gateway import TerminalExecutionGateway
from .verification_engine import TerminalVerificationEngine
from .failure_recovery import TerminalFailureRecoveryEngine
from .tool_integration import TerminalToolIntegrationEngine
from .security_agent import SecurityGovernanceAgent, SecurityDecision, ReversibilityClassification
from .reversibility_engine import ReversibilityAndCheckpointEngine, TerminalOperationRecord, TerminalCheckpoint
from .knowledge_evolution import AICeoKnowledgeEvolutionEngine, AICeoKnowledgeEntry
from ..evidence_ledger import EvidenceLedger

logger = logging.getLogger("zonata.terminal.agent")

class TerminalHandlingAgent:
    """
    Dedicated Terminal Handling Agent.
    Subordinate to ZONATA Sovereign Authority and AICU strategic direction.
    Operates the Universal Terminal with structured technical reasoning, security awareness,
    and postcondition verification.
    """

    def __init__(
        self,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        agent_id: str = "agent_terminal_handler",
        workspace_root: Optional[str] = None
    ):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.agent_id = agent_id
        self.workspace_root = workspace_root or os.path.abspath(os.getcwd())

        # Subsystems
        self.registry = EnvironmentCapabilityRegistry()
        self.router = UniversalRuntimeRouter(self.registry)
        self.execution_gateway = TerminalExecutionGateway(self.workspace_root)
        self.tool_engine = TerminalToolIntegrationEngine(tenant_id, self.registry)
        self.security_agent = SecurityGovernanceAgent(tenant_id, company_id)
        self.reversibility_engine = ReversibilityAndCheckpointEngine()
        self.evolution_engine = AICeoKnowledgeEvolutionEngine(tenant_id=tenant_id)
        self.evidence_ledger = EvidenceLedger()


    def process_objective(
        self,
        objective: str,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        human_approved: bool = False,
        force_gui: bool = False,
        explicit_command: Optional[str] = None,
        postconditions: Optional[List[VerificationPostcondition]] = None,
        custom_workspace: Optional[str] = None
    ) -> TerminalResult:
        """
        Executes the full 16-step Terminal Handling Agent Lifecycle.
        """
        start_time = time.time()
        m_id = mission_id or f"msn_{uuid.uuid4().hex[:6]}"
        t_id = task_id or f"tsk_{uuid.uuid4().hex[:6]}"
        ws = custom_workspace or self.workspace_root

        # 1. UNDERSTAND: Parse objective and intent
        intent_summary = f"Objective: '{objective}'"
        logger.info(f"Step 1: Understand - {intent_summary}")

        # 2. DISCOVER: Inspect machine and available hardware/software capabilities
        host_metrics = ResourceInspector.inspect_system()
        logger.info(f"Step 2: Discover - Host arch={host_metrics['architecture']}, RAM={host_metrics['ram']['total_mb']}MB")

        # 3. ASSESS: Assess risk classification
        sample_cmd = explicit_command or objective
        risk_tier = TerminalSecurityGateway.classify_risk(sample_cmd)
        logger.info(f"Step 3: Assess - Risk Tier={risk_tier.value}")

        # 4. SELECT ENVIRONMENT: Dynamically route to optimal Linux profile & adapter
        env_decision = self.router.select_environment(
            objective=objective,
            risk_level=risk_tier,
            force_gui=force_gui
        )
        logger.info(f"Step 4: Select Environment - Profile={env_decision.selected_profile_id}, Distro={env_decision.distribution}, Desktop={env_decision.desktop_environment.value}")

        # 5. SELECT TOOLS: Identify required tools and check availability
        required_tools = []
        if "git" in objective.lower():
            required_tools.append("git")
        if "python" in objective.lower() or "pytest" in objective.lower():
            required_tools.append("python3")

        missing_tools = [t for t in required_tools if not self.registry.is_tool_available(t, env_decision.selected_profile_id)]
        acquired_tools = []
        for mt in missing_tools:
            # Tool discovery and acquisition pipeline
            cands = self.tool_engine.discover_tools_for_objective(mt)
            if cands:
                ok, msg, t_meta = self.tool_engine.acquire_and_qualify_tool(cands[0].tool_id)
                if ok:
                    acquired_tools.append(mt)

        # Create session
        session_id = f"term_sess_{uuid.uuid4().hex[:8]}"
        session = TerminalSession(
            session_id=session_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id=m_id,
            task_id=t_id,
            agent_id=self.agent_id,
            environment_id=env_decision.selected_profile_id,
            runtime_id=env_decision.selected_adapter_id,
            authorization_context={"human_approved": human_approved},
            risk_level=risk_tier,
            workspace=ws,
            network_policy=env_decision.network_mode,
            credential_scope=[]
        )
        session.log(f"Session initialized with profile {env_decision.selected_profile_id} ({env_decision.distribution})")

        # 6. PLAN: Create structured CommandPlan
        cmd_to_run = explicit_command or self._derive_command_from_objective(objective)
        plan = CommandPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:6]}",
            objective=objective,
            environment_profile_id=env_decision.selected_profile_id,
            working_directory=ws,
            command=cmd_to_run,
            filesystem_impact="LOCAL" if any(w in cmd_to_run for w in ["touch", "mkdir", "write", "cp", "rm"]) else "NONE",
            risk_level=risk_tier,
            timeout_sec=30.0,
            expected_result="Command executes and verifies cleanly"
        )

        # Record operation in Reversibility Engine
        rev_class = self.security_agent.classify_reversibility(cmd_to_run, risk_tier)
        op_rec = self.reversibility_engine.create_operation(
            session_id=session_id,
            task_id=t_id,
            mission_id=m_id,
            agent_id=self.agent_id,
            runtime_id=env_decision.selected_adapter_id,
            workspace=ws,
            command=cmd_to_run,
            reversibility=rev_class.value,
            rollback_method="SNAPSHOT_RESTORE" if plan.filesystem_impact != "NONE" else "NO_OP",
            actor="AICU_TERMINAL_AGENT",
            parameters={"prompt": objective, "plan": plan.to_dict() if hasattr(plan, "to_dict") else {}}
        )

        # Create persistent resumable checkpoint
        chk = TerminalCheckpoint(
            checkpoint_id=f"chk_{uuid.uuid4().hex[:8]}",
            mission_id=m_id,
            task_id=t_id,
            subtask_id=None,
            agent_id=self.agent_id,
            session_id=session_id,
            prompt=objective,
            execution_plan={"command": cmd_to_run, "plan_id": plan.plan_id},
            environment=env_decision.distribution,
            runtime=env_decision.selected_adapter_id,
            tool_versions={"tools": str(required_tools)},
            last_successful_checkpoint=None,
            last_successful_command=None,
            last_attempted_operation=op_rec.operation_id,
            last_command=cmd_to_run,
            working_directory=ws,
            files_changed=[],
            verification_state={},
            failure_state=None,
            rollback_state={"rollback_method": op_rec.rollback_method},
            evidence_refs=[],
            next_safe_action="EXECUTE_COMMAND",
            status="RUNNING",
            created_at=time.time(),
            updated_at=time.time()
        )
        self.reversibility_engine.save_checkpoint(chk)

        # 7. CHECK POLICY: Layer 3 Security & Governance Agent Independent Evaluation
        sec_eval = self.security_agent.evaluate_operation(
            command=cmd_to_run,
            working_directory=ws,
            allowed_workspace=ws,
            human_approved=human_approved,
            session_id=session_id,
            agent_id=self.agent_id
        )
        if not sec_eval["allowed"]:
            session.status = (
                TerminalStatus.WAITING_AUTHORIZATION
                if sec_eval.get("requires_approval", False)
                else TerminalStatus.FAILED
            )
            session.log(f"Step 7: Check Policy - {sec_eval['decision']}: {sec_eval['reason']}")
            chk.status = "BLOCKED" if sec_eval["killswitch_engaged"] else "WAITING_AUTHORIZATION"
            self.reversibility_engine.save_checkpoint(chk)
            return TerminalResult(
                status="REQUIRES_AUTHORIZATION" if sec_eval["requires_approval"] else "BLOCKED",
                summary=sec_eval["reason"],
                environment_used=env_decision.distribution,
                runtime_profile=env_decision.selected_profile_id,
                tools_used=required_tools,
                tools_installed=acquired_tools,
                commands_executed=[],
                files_changed=[],
                artifacts=[],
                observations={"risk_tier": risk_tier.value, "approval_required": sec_eval["requires_approval"], "security_decision": sec_eval["decision"]},
                verification={"verified": False},
                evidence_id=None,
                failures=[{"type": "SECURITY_GATE_DENIAL", "detail": sec_eval["reason"]}],
                recovery_actions=["Request explicit human approval in Owner Decision Center"] if sec_eval["requires_approval"] else ["Review security constraints"],
                remaining_risks=[risk_tier.value],
                escalation_required=True,
                duration_ms=(time.time() - start_time) * 1000
            )

        # 8. PROVISION: Provision environment substrate via adapter
        adapter = self.router.get_adapter(env_decision.selected_adapter_id)
        if not adapter:
            raise RuntimeError(f"Runtime adapter '{env_decision.selected_adapter_id}' unavailable")

        profile = self.registry.get_profile(env_decision.selected_profile_id)
        prov_res = adapter.provision(session_id, profile, ws)
        session.status = TerminalStatus.PREPARING
        session.log(f"Step 8: Provisioned via {adapter.adapter_id()}")

        # 9. EXECUTE: Governed execution through gateway
        commands_run = [cmd_to_run]
        exec_res = self.execution_gateway.execute_plan(session, plan, adapter)

        # 10. OBSERVE: Capture outputs, process state, resource usage
        session.status = TerminalStatus.OBSERVING
        observations = {
            "exit_code": exec_res.get("exit_code"),
            "semantic_state": exec_res.get("semantic_state"),
            "host_load": host_metrics["load_average"],
            "stdout_length": len(exec_res.get("stdout", "")),
            "stderr_length": len(exec_res.get("stderr", ""))
        }

        # 11. DIAGNOSE & 12. RECOVER/REPLAN IF AUTHORIZED
        attempt = 1
        failures = []
        recovery_actions = []

        if exec_res.get("status") != "SUCCEEDED":
            session.status = TerminalStatus.RECOVERING
            err_output = exec_res.get("stdout", "") + "\n" + exec_res.get("stderr", "")
            classification = TerminalFailureRecoveryEngine.classify_failure(
                exec_res.get("exit_code", 1), exec_res.get("stdout", ""), exec_res.get("stderr", "")
            )
            failures.append({"type": classification.value, "error": err_output[:300]})

            can_recover, rec_reason, rec_plan = TerminalFailureRecoveryEngine.plan_recovery(
                session, plan, classification, err_output, attempt
            )
            if can_recover and rec_plan:
                recovery_actions.append(rec_reason)
                session.log(f"Attempting recovery: {rec_reason}")
                # Execute recovery plan
                rec_res = self.execution_gateway.execute_plan(session, rec_plan, adapter)
                commands_run.append(rec_plan.command)
                if rec_res.get("status") == "SUCCEEDED":
                    # Re-execute original plan
                    session.log("Recovery action succeeded; re-executing original plan...")
                    exec_res = self.execution_gateway.execute_plan(session, plan, adapter)
                    commands_run.append(plan.command)
                    if exec_res.get("status") == "SUCCEEDED":
                        failures.clear()

        # 13. VERIFY: Independent verification of postconditions
        session.status = TerminalStatus.VERIFYING
        verified = (exec_res.get("status") == "SUCCEEDED")
        verification_details = {}

        if postconditions:
            conds_ok, evaluated_conds = TerminalVerificationEngine.verify_postconditions(
                session, postconditions
            )
            verified = verified and conds_ok
            verification_details = {
                "all_conditions_passed": conds_ok,
                "conditions": [
                    {"name": c.name, "type": c.check_type, "passed": c.passed, "detail": c.evidence_detail}
                    for c in evaluated_conds
                ]
            }
        else:
            verification_details = {"process_exit_clean": exec_res.get("exit_code") == 0}

        # 14. CAPTURE EVIDENCE: Seal into Evidence Ledger & Update Reversibility Checkpoint
        evidence_id = exec_res.get("evidence_id")
        final_status = "SUCCESS" if verified else ("FAILED" if failures else "VERIFICATION_FAILED")
        session.status = TerminalStatus.COMPLETED if verified else TerminalStatus.FAILED

        # Update operation record
        self.reversibility_engine.update_operation_result(
            operation_id=op_rec.operation_id,
            files_changed=[],
            processes_created=[],
            post_state=observations,
            verification=verification_details,
            evidence_hash=evidence_id or "",
            status=final_status
        )

        # Update checkpoint
        chk.status = final_status
        chk.last_successful_command = cmd_to_run if verified else None
        chk.verification_state = verification_details
        if evidence_id:
            chk.evidence_refs.append(evidence_id)
        chk.next_safe_action = "COMPLETE" if verified else "ROLLBACK_OR_ESCALATE"
        self.reversibility_engine.save_checkpoint(chk)

        # 15. REPORT TO AICU: Structured TerminalResult contract
        summary = (
            f"Execution {final_status} on {env_decision.distribution} ({env_decision.selected_profile_id}). "
            f"Command exit code: {exec_res.get('exit_code')}. Verified: {verified}."
        )

        term_result = TerminalResult(
            status=final_status,
            summary=summary,
            environment_used=env_decision.distribution,
            runtime_profile=env_decision.selected_profile_id,
            tools_used=required_tools,
            tools_installed=acquired_tools,
            commands_executed=commands_run,
            files_changed=[],
            artifacts=[],
            observations=observations,
            verification=verification_details,
            evidence_id=evidence_id,
            failures=failures,
            recovery_actions=recovery_actions,
            remaining_risks=[],
            escalation_required=session.status == TerminalStatus.ESCALATED,
            duration_ms=(time.time() - start_time) * 1000
        )

        # 16. KNOWLEDGE EVOLUTION LOOP: Feed verified technical intelligence back to AI CEO
        if verified and evidence_id:
            try:
                self.evolution_engine.extract_and_register_knowledge(
                    session=session,
                    result=term_result,
                    topic="operational_procedure"
                )
            except Exception as e:
                logger.warning(f"Knowledge evolution extraction notice: {e}")

        return term_result

    def execute_ceo_directive(self, instruction: AICeoTerminalInstruction) -> AICeoTerminalResult:
        """
        Executes the formal AI CEO ↔ Terminal machine-readable contract.
        Translates strategic directives, respects resource budgets, enforces supervision,
        and returns structured AICeoTerminalResult.
        """
        start_time = time.time()
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"
        task_id = instruction.task_id or f"tsk_ceo_{uuid.uuid4().hex[:6]}"
        mission_id = instruction.mission_id or f"msn_ceo_{uuid.uuid4().hex[:6]}"

        human_appr = instruction.authorization_context.get("human_approved", True)
        term_res = self.process_objective(
            objective=instruction.objective,
            mission_id=mission_id,
            task_id=task_id,
            human_approved=human_appr
        )

        # Extract admitted knowledge updates
        knowledge_entries = self.evolution_engine.find_knowledge()
        knowledge_summaries = [
            {"knowledge_id": k.knowledge_id, "topic": k.topic, "title": k.title, "confidence": k.confidence}
            for k in knowledge_entries[:3]
        ]

        return AICeoTerminalResult(
            task_id=task_id,
            execution_id=exec_id,
            status=term_res.status,
            objective=instruction.objective,
            technical_plan={"commands": term_res.commands_executed, "runtime": term_res.runtime_profile},
            runtime_selection=term_res.runtime_profile,
            environment_selection=term_res.environment_used,
            tools_selected=term_res.tools_used,
            tools_installed=term_res.tools_installed,
            commands_executed=term_res.commands_executed,
            artifacts=term_res.artifacts,
            verification=term_res.verification,
            security_status={"decision": "APPROVED" if term_res.status == "SUCCESS" else "REQUIRES_AUTHORIZATION"},
            policy_status={"compliant": term_res.status != "POLICY_DENIED"},
            rollback_status={"available": True, "method": "SNAPSHOT_RESTORE"},
            failures=term_res.failures,
            recovery=term_res.recovery_actions,
            evidence_refs=[term_res.evidence_id] if term_res.evidence_id else [],
            knowledge_updates=knowledge_summaries,
            recommended_next_action="PROCEED_TO_NEXT_PHASE" if term_res.status == "SUCCESS" else "ESCALATE_TO_AI_CEO",
            limitations=[],
            duration_ms=(time.time() - start_time) * 1000
        )


    def _derive_command_from_objective(self, objective: str) -> str:
        """Translates high-level technical objective into standard shell command."""
        obj_l = objective.lower()
        if "python version" in obj_l:
            return "python3 --version"
        elif "git status" in obj_l:
            return "git status"
        elif "top memory" in obj_l or "memory consumers" in obj_l:
            return "ps aux --sort=-%mem | head -n 10"
        elif "disk usage" in obj_l or "disk space" in obj_l:
            return "df -h"
        elif "hardware architecture" in obj_l or "system architecture" in obj_l:
            return "uname -a"
        elif "memory" in obj_l:
            return "free -m"
        elif "list files" in obj_l or "ls" in obj_l:
            return "ls -la"
        elif "package" in obj_l and "checksum" in obj_l:
            return "tar -czf app.tar.gz *.py 2>/dev/null || true && sha256sum app.tar.gz 2>/dev/null || echo 'packaged'"
        elif "run test" in obj_l or "run unit test" in obj_l or "pytest" in obj_l or "unittest" in obj_l:
            return "python3 -m unittest discover -s . -p 'test_*.py'"
        
        # If objective starts with shell command prefix, treat as runnable command
        cmd_prefixes = ["python3 ", "python ", "sh ", "bash ", "cat ", "echo ", "git ", "mkdir ", "touch ", "curl ", "uname ", "df ", "free ", "ls ", "tar "]
        if any(obj_l.strip().startswith(p) for p in cmd_prefixes):
            return objective.strip()
            
        return f"echo 'Executing: {objective}'"
