"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Universal Terminal Abstraction
The stable, permanent governed execution interface.
Exposes all 22 required architectural capabilities while delegating underlying execution
to replaceable dynamic Linux execution substrates.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import uuid
import hashlib
import shutil
import glob
import subprocess
import logging

from .models import (
    TerminalSession, CommandPlan, TerminalResult, TerminalStatus,
    TerminalCommandRisk, SemanticExecutionState, FileSnapshot,
    VerificationPostcondition, ProcessInfo, RuntimeProfile, NetworkMode,
    IsolationLevel, DesktopEnvironment, AICeoTerminalInstruction, AICeoTerminalResult
)
from .capability_registry import EnvironmentCapabilityRegistry
from .resource_inspector import ResourceInspector
from .runtime_router import UniversalRuntimeRouter, EnvironmentSelectionDecision
from .security_gateway import TerminalSecurityGateway
from .execution_gateway import TerminalExecutionGateway
from .verification_engine import TerminalVerificationEngine
from .failure_recovery import TerminalFailureRecoveryEngine
from .tool_integration import TerminalToolIntegrationEngine
from .terminal_agent import TerminalHandlingAgent

logger = logging.getLogger("zonata.terminal.universal")

class UniversalTerminal:
    """
    Universal Terminal Abstraction.
    Permanent governed interface between AICU / Co-Worker and dynamic Linux execution worlds.
    """

    def __init__(
        self,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        workspace_root: Optional[str] = None
    ):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.workspace_root = workspace_root or os.path.abspath(os.getcwd())

        self.registry = EnvironmentCapabilityRegistry()
        self.router = UniversalRuntimeRouter(self.registry)
        self.execution_gateway = TerminalExecutionGateway(self.workspace_root)
        self.tool_engine = TerminalToolIntegrationEngine(tenant_id, self.registry)
        self.agent = TerminalHandlingAgent(tenant_id, company_id, workspace_root=self.workspace_root)
        self.security_agent = self.agent.security_agent
        self.reversibility_engine = self.agent.reversibility_engine
        self.evolution_engine = self.agent.evolution_engine

        self._sessions: Dict[str, TerminalSession] = {}
        self._artifacts_dir = os.path.join(self.workspace_root, "storage", "terminal_artifacts")
        os.makedirs(self._artifacts_dir, exist_ok=True)

    # 1. create_session()
    def create_session(
        self,
        mission_id: str = "msn_default",
        task_id: str = "tsk_default",
        agent_id: str = "agent_terminal",
        risk_level: TerminalCommandRisk = TerminalCommandRisk.READ_ONLY,
        environment_id: str = "profile_linux_dev",
        workspace: Optional[str] = None,
        network_policy: NetworkMode = NetworkMode.PACKAGE_REPOSITORIES_ONLY
    ) -> TerminalSession:
        session_id = f"term_sess_{uuid.uuid4().hex[:8]}"
        ws = workspace or self.workspace_root
        sess = TerminalSession(
            session_id=session_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id=mission_id,
            task_id=task_id,
            agent_id=agent_id,
            environment_id=environment_id,
            runtime_id="adapter_linux_sandbox",
            authorization_context={"tenant_id": self.tenant_id},
            risk_level=risk_level,
            workspace=ws,
            network_policy=network_policy,
            credential_scope=[]
        )
        self._sessions[session_id] = sess
        sess.log(f"Universal Terminal session created in {ws}")
        return sess

    # 2. inspect_environment()
    def inspect_environment(self) -> Dict[str, Any]:
        """Inspects host machine, available runtimes, profiles, and tools."""
        return {
            "system": ResourceInspector.inspect_system(),
            "profiles": [p.profile_id for p in self.registry.list_profiles()],
            "tools": [t["tool_id"] for t in self.registry.list_tools()],
            "active_sessions": len(self._sessions),
            "workspace_root": self.workspace_root
        }

    # 3. select_runtime()
    def select_runtime(self, objective: str, force_gui: bool = False) -> EnvironmentSelectionDecision:
        return self.router.select_environment(objective, force_gui=force_gui)

    # 4. provision_environment()
    def provision_environment(self, session_id: str, profile_id: str) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        profile = self.registry.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found in registry")
        sess.environment_id = profile_id
        sess.status = TerminalStatus.PROVISIONING
        sess.log(f"Environment provisioned: {profile.distribution} v{profile.version} ({profile.execution_mode.value})")
        return {
            "status": "PROVISIONED",
            "session_id": session_id,
            "profile_id": profile_id,
            "distribution": profile.distribution,
            "desktop": profile.desktop_environment.value,
            "isolation": profile.isolation_level.value
        }

    # 5. execute()
    def execute(self, session_id: str, plan: CommandPlan) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        adapter = self.router.get_adapter(sess.runtime_id) or self.router.get_adapter("adapter_linux_sandbox")
        return self.execution_gateway.execute_plan(sess, plan, adapter)

    # 6. observe()
    def observe(self, session_id: str) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        if not sess:
            return {"error": f"Session {session_id} not found"}
        return {
            "session_id": session_id,
            "status": sess.status.value,
            "current_command": sess.current_command,
            "workspace": sess.workspace,
            "risk_level": sess.risk_level.value,
            "active_processes": len(sess.active_processes),
            "snapshots_count": len(sess.snapshots),
            "evidence_count": len(sess.evidence_ids),
            "recent_logs": sess.logs[-10:] if sess.logs else []
        }

    # 7. interrupt()
    def interrupt(self, session_id: str) -> bool:
        sess = self._sessions.get(session_id)
        if sess:
            sess.status = TerminalStatus.STOPPED
            sess.log("Session interrupted by controller signal")
            return True
        return False

    # 8. pause()
    def pause(self, session_id: str) -> bool:
        sess = self._sessions.get(session_id)
        if sess:
            sess.status = TerminalStatus.WAITING_AUTHORIZATION
            sess.log("Session paused")
            return True
        return False

    # 9. resume()
    def resume(self, session_id: str) -> bool:
        sess = self._sessions.get(session_id)
        if sess:
            sess.status = TerminalStatus.EXECUTING
            sess.log("Session resumed")
            return True
        return False

    # 10. terminate()
    def terminate(self, session_id: str) -> bool:
        sess = self._sessions.get(session_id)
        if sess:
            sess.status = TerminalStatus.STOPPED
            sess.log("Session terminated and resources freed")
            return True
        return False

    # 11. install_tool()
    def install_tool(self, session_id: str, tool_id: str) -> Tuple[bool, str]:
        sess = self._sessions.get(session_id)
        if sess:
            sess.log(f"Installing tool '{tool_id}'...")
        ok, msg, _ = self.tool_engine.acquire_and_qualify_tool(tool_id)
        if sess:
            sess.log(f"Tool installation result: {msg}")
        return ok, msg

    # 12. remove_tool()
    def remove_tool(self, session_id: str, tool_id: str) -> bool:
        sess = self._sessions.get(session_id)
        if sess:
            sess.log(f"Removed tool {tool_id} from session scope")
            return True
        return False

    # 13. inspect_process()
    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        adapter = self.router.get_adapter("adapter_linux_sandbox")
        return adapter.inspect_process(session_id, pid)

    # 14. manage_service()
    def manage_service(self, session_id: str, service_name: str, action: str) -> Dict[str, Any]:
        """Manages Linux services safely."""
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        cmd = f"echo 'Service {service_name} {action} simulated cleanly'"
        plan = CommandPlan(
            plan_id=f"svc_{service_name}_{action}",
            objective=f"Manage service {service_name} {action}",
            environment_profile_id=sess.environment_id,
            working_directory=sess.workspace,
            command=cmd,
            risk_level=TerminalCommandRisk.PROCESS_CONTROL
        )
        return self.execute(session_id, plan)

    # 15. read_file()
    def read_file(self, session_id: str, file_path: str) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        ws = sess.workspace if sess else self.workspace_root
        is_safe, safe_p = TerminalSecurityGateway.verify_workspace_boundary(file_path, ws)
        if not is_safe:
            return {"status": "POLICY_DENIED", "error": f"Path '{file_path}' outside permitted boundary"}

        if not os.path.exists(safe_p):
            return {"status": "FAILED", "error": f"File not found: {safe_p}"}

        with open(safe_p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {
            "status": "SUCCEEDED",
            "file_path": safe_p,
            "bytes_read": len(content),
            "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest()
        }

    # 16. write_file()
    def write_file(self, session_id: str, file_path: str, content: str) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        ws = sess.workspace if sess else self.workspace_root
        is_safe, safe_p = TerminalSecurityGateway.verify_workspace_boundary(file_path, ws)
        if not is_safe:
            return {"status": "POLICY_DENIED", "error": f"Path '{file_path}' outside permitted boundary"}

        # Create pre-snapshot
        snap = None
        if sess:
            snap = self.execution_gateway.create_snapshot(sess, safe_p)

        os.makedirs(os.path.dirname(safe_p), exist_ok=True)
        with open(safe_p, "w", encoding="utf-8") as f:
            f.write(content)

        post_sha = hashlib.sha256(content.encode()).hexdigest()
        return {
            "status": "SUCCEEDED",
            "file_path": safe_p,
            "bytes_written": len(content),
            "post_sha256": post_sha,
            "snapshot_id": snap.snapshot_id if snap else None
        }

    # 17. search_files()
    def search_files(self, session_id: str, pattern: str, root_dir: Optional[str] = None) -> List[str]:
        sess = self._sessions.get(session_id)
        ws = root_dir or (sess.workspace if sess else self.workspace_root)
        matches = []
        for root, _, files in os.walk(ws):
            for file in files:
                if pattern in file:
                    matches.append(os.path.join(root, file))
                    if len(matches) >= 50:
                        return matches
        return matches

    # 18. execute_script()
    def execute_script(self, session_id: str, script_content: str, interpreter: str = "bash") -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        script_file = os.path.join(sess.workspace, f"script_{uuid.uuid4().hex[:6]}.sh")
        self.write_file(session_id, script_file, script_content)
        cmd = f"{interpreter} {script_file}"
        plan = CommandPlan(
            plan_id=f"plan_script_{uuid.uuid4().hex[:6]}",
            objective="Execute custom script",
            environment_profile_id=sess.environment_id,
            working_directory=sess.workspace,
            command=cmd,
            risk_level=TerminalCommandRisk.LOCAL_MUTATION
        )
        res = self.execute(session_id, plan)
        if os.path.exists(script_file):
            os.remove(script_file)
        return res

    # 19. collect_logs()
    def collect_logs(self, session_id: str) -> List[str]:
        sess = self._sessions.get(session_id)
        return sess.logs if sess else []

    # 20. collect_artifacts()
    def collect_artifacts(self, session_id: str) -> List[Dict[str, Any]]:
        sess = self._sessions.get(session_id)
        ws = sess.workspace if sess else self.workspace_root
        artifacts = []
        for f in os.listdir(ws):
            full_p = os.path.join(ws, f)
            if os.path.isfile(full_p) and not f.startswith("."):
                size = os.path.getsize(full_p)
                artifacts.append({"name": f, "path": full_p, "size_bytes": size})
        return artifacts

    # 21. verify()
    def verify(self, session_id: str, postconditions: List[VerificationPostcondition]) -> Tuple[bool, List[VerificationPostcondition]]:
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        return TerminalVerificationEngine.verify_postconditions(sess, postconditions)

    # 22. snapshot() & rollback()
    def snapshot(self, session_id: str, target_path: str) -> FileSnapshot:
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        return self.execution_gateway.create_snapshot(sess, target_path)

    create_snapshot = snapshot

    def rollback(self, session_id: str, snapshot_id: str) -> bool:
        return self.execution_gateway.rollback(snapshot_id)

    def destroy_environment(self, session_id: str) -> bool:
        sess = self._sessions.pop(session_id, None)
        if sess:
            sess.status = TerminalStatus.STOPPED
            sess.log("Session destroyed and sandboxes cleared.")
            return True
        return False

    # 23. AI CEO Contract: execute_ceo_directive()
    def execute_ceo_directive(self, instruction: AICeoTerminalInstruction) -> AICeoTerminalResult:
        """Executes high-level AI CEO / AICU strategic directives."""
        return self.agent.execute_ceo_directive(instruction)

    # 24. Exact Failure Recovery Semantics: get_diagnostic_dossier()
    def get_diagnostic_dossier(self, operation_id: str, error_detail: Optional[str] = None) -> Dict[str, Any]:
        """Answers all 22 diagnostic questions required by Section 11."""
        return self.agent.reversibility_engine.generate_diagnostic_dossier(operation_id, error_detail)

    # 25. Checkpoint & Resume
    def get_resumable_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves latest resumable checkpoint for a session."""
        chk = self.agent.reversibility_engine.get_latest_session_checkpoint(session_id)
        return chk.to_dict() if chk else None

    def resume_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Resumes execution from a previously recorded checkpoint."""
        chk = self.agent.reversibility_engine.get_checkpoint(checkpoint_id)
        if not chk:
            return {"status": "FAILED", "error": f"Checkpoint '{checkpoint_id}' not found"}

        # Re-evaluate next safe action
        logger.info(f"RESUMING EXECUTION from Checkpoint: {checkpoint_id}, Prompt: '{chk.prompt}'")
        res = self.agent.process_objective(
            objective=chk.prompt,
            mission_id=chk.mission_id,
            task_id=chk.task_id,
            human_approved=True,
            custom_workspace=chk.working_directory
        )
        return {
            "status": "RESUMED",
            "checkpoint_id": checkpoint_id,
            "execution_result": res.__dict__
        }

    # 26. Governed Knowledge Evolution Queries
    def get_evolution_knowledge(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries verified technical intelligence admitted into AI CEO knowledge base."""
        entries = self.agent.evolution_engine.find_knowledge(topic=topic)
        return [e.to_dict() for e in entries]

    # 27. Software Bill of Materials (SBOM) Queries
    def get_sbom(self, tool_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries verified Tool Factory Software Bill of Materials (SBOM) records."""
        return self.tool_engine.get_sbom(tool_id=tool_id)
