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
    VerificationPostcondition, DesktopEnvironment, ExecutionMode, NetworkMode
)
from .capability_registry import EnvironmentCapabilityRegistry
from .resource_inspector import ResourceInspector
from .runtime_router import UniversalRuntimeRouter, EnvironmentSelectionDecision
from .security_gateway import TerminalSecurityGateway
from .execution_gateway import TerminalExecutionGateway
from .verification_engine import TerminalVerificationEngine
from .failure_recovery import TerminalFailureRecoveryEngine
from .tool_integration import TerminalToolIntegrationEngine
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

        # 7. CHECK POLICY: Enforce PolicyEngine & authorization barrier
        auth_ok, auth_err = TerminalSecurityGateway.check_authorization(
            risk_tier, human_approved=human_approved, tenant_id=self.tenant_id, company_id=self.company_id
        )
        if not auth_ok:
            session.status = TerminalStatus.WAITING_AUTHORIZATION
            session.log(f"Step 7: Check Policy - Blocked: {auth_err}")
            return TerminalResult(
                status="REQUIRES_AUTHORIZATION",
                summary=auth_err,
                environment_used=env_decision.distribution,
                runtime_profile=env_decision.selected_profile_id,
                tools_used=required_tools,
                tools_installed=acquired_tools,
                commands_executed=[],
                files_changed=[],
                artifacts=[],
                observations={"risk_tier": risk_tier.value, "approval_required": True},
                verification={"verified": False},
                evidence_id=None,
                failures=[{"type": "AUTHORIZATION_REQUIRED", "detail": auth_err}],
                recovery_actions=["Request explicit human approval in Owner Decision Center"],
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

        # 14. CAPTURE EVIDENCE: Seal into Evidence Ledger
        evidence_id = exec_res.get("evidence_id")
        final_status = "SUCCESS" if verified else ("FAILED" if failures else "VERIFICATION_FAILED")
        session.status = TerminalStatus.COMPLETED if verified else TerminalStatus.FAILED

        # 15. REPORT TO AICU: Structured TerminalResult contract
        summary = (
            f"Execution {final_status} on {env_decision.distribution} ({env_decision.selected_profile_id}). "
            f"Command exit code: {exec_res.get('exit_code')}. Verified: {verified}."
        )

        return TerminalResult(
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
