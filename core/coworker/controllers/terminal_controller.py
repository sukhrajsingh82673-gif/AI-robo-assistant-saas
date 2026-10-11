"""
ZONATA Universal AI Co-Worker Fabric — Terminal Controller
Governed execution controller operating over the Governed Terminal Runtime.
Provides 12-tier risk classification, path confinement, pre/post SHA-256 rollback,
credential scrubbing, and tool self-extension.
"""

from typing import Dict, List, Optional, Any
import os
import uuid
import time

from ..runtimes.terminal_runtime import (
    TerminalWorkerRuntime,
    TerminalCommandRisk,
    TerminalSecurityAnalyzer
)

class GovernedTerminalController:
    """
    High-level terminal controller for the Universal Co-Worker.
    Delegates all low-level bash, script, compile, and filesystem commands
    through the governed terminal runtime.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary", workspace_root: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.runtime = TerminalWorkerRuntime(tenant_id=tenant_id, company_id=company_id, workspace_root=workspace_root)
        from ...universal_terminal import UniversalTerminal, TerminalHandlingAgent
        self.universal_terminal = UniversalTerminal(tenant_id=tenant_id, company_id=company_id, workspace_root=workspace_root)
        self.agent = TerminalHandlingAgent(tenant_id=tenant_id, company_id=company_id, workspace_root=workspace_root)

    def process_objective(
        self,
        objective: str,
        mission_id: Optional[str] = None,
        human_approved: bool = False,
        force_gui: bool = False,
        explicit_command: Optional[str] = None,
        postconditions: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Processes high-level objective via the 16-step Terminal Handling Agent lifecycle."""
        res = self.agent.process_objective(
            objective=objective,
            mission_id=mission_id,
            human_approved=human_approved,
            force_gui=force_gui,
            explicit_command=explicit_command,
            postconditions=postconditions
        )
        return {
            "status": res.status,
            "summary": res.summary,
            "environment_used": res.environment_used,
            "runtime_profile": res.runtime_profile,
            "tools_used": res.tools_used,
            "tools_installed": res.tools_installed,
            "commands_executed": res.commands_executed,
            "observations": res.observations,
            "verification": res.verification,
            "evidence_id": res.evidence_id,
            "failures": res.failures,
            "recovery_actions": res.recovery_actions,
            "duration_ms": res.duration_ms
        }

    def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        human_approved: bool = False,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        """Runs a command through the governed 12-tier security sandbox."""
        session_id = f"term_ctl_{uuid.uuid4().hex[:6]}"
        return self.runtime.run_foreground(session_id, {
            "capability": "terminal.shell_command",
            "command": command,
            "parameters": {"command": command, "cwd": cwd or os.getcwd()},
            "human_approved": human_approved,
            "timeout_sec": timeout_sec
        })

    def file_operation(
        self,
        action: str,
        file_path: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Safely performs read/write/append with pre/post SHA-256 hashing and path confinement."""
        clean_path = os.path.normpath(file_path)
        real_path = os.path.realpath(file_path) if os.path.exists(file_path) else clean_path
        restricted_prefixes = ("/etc", "/root/.vault", "/proc", "/sys", "/root/.ssh", "/root/.gnupg", "/dev")
        if (
            ".." in clean_path.split(os.sep) or
            any(clean_path.startswith(p) for p in restricted_prefixes) or
            any(real_path.startswith(p) for p in restricted_prefixes)
        ):
            return {
                "success": False,
                "error": f"Security Violation: Path traversal or restricted system path '{file_path}' blocked.",
                "status": "FAILED_SECURITY_POLICY"
            }
        session_id = f"file_ctl_{uuid.uuid4().hex[:6]}"
        return self.runtime.run_foreground(session_id, {
            "capability": "terminal.file_operation",
            "action": action,
            "file_path": file_path,
            "content": content,
            "parameters": {"action": action, "file_path": file_path, "content": content}
        })

    def rollback_mutation(self, file_path: str) -> bool:
        """Restores a previous backup snapshot for the specified path."""
        return self.runtime.rollback_file(file_path)

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns terminal sandbox diagnostics, sandbox directory, and snapshot count."""
        return self.runtime.get_diagnostics()

