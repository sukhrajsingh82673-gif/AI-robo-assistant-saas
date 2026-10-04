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

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self.runtime = TerminalWorkerRuntime(tenant_id=tenant_id)

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
        """Safely performs read/write/append with pre/post SHA-256 hashing."""
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
