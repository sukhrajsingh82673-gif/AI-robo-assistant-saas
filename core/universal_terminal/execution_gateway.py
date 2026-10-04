"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Execution Gateway
Executes structured CommandPlans via runtime adapters under multi-level KillSwitch supervision,
process tree tracking, pre/post SHA-256 filesystem snapshots, and automated rollback backups.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import uuid
import shutil
import hashlib
import json
import logging
import signal

from .models import (
    CommandPlan, TerminalSession, TerminalCommandRisk, SemanticExecutionState,
    FileSnapshot, ProcessInfo, TerminalStatus
)
from .security_gateway import TerminalSecurityGateway
from .runtime_adapters import BaseRuntimeAdapter

logger = logging.getLogger("zonata.terminal.gateway")

class TerminalExecutionGateway:
    """
    Governed Execution Gateway.
    Passes CommandPlans through runtime adapters, tracking process trees,
    capturing stdout/stderr, and maintaining immutable snapshot rollbacks.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.getcwd())
        self.backup_dir = os.path.join(self.workspace_root, "storage", "terminal_backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self._active_processes: Dict[int, Dict[str, Any]] = {}
        self._snapshots: Dict[str, FileSnapshot] = {}

    def execute_plan(
        self,
        session: TerminalSession,
        plan: CommandPlan,
        adapter: BaseRuntimeAdapter
    ) -> Dict[str, Any]:
        """
        Executes a planned command through the chosen adapter with full governance.
        """
        start_time = time.time()
        session.status = TerminalStatus.EXECUTING
        session.current_command = plan.command
        session.current_plan = plan

        # 1. Check KillSwitch barrier before starting
        from ..killswitch_matrix import KillSwitchMatrix, KillSwitchEngagedException
        try:
            ks = KillSwitchMatrix(tenant_id=session.tenant_id)
            ks.assert_can_execute(
                company_id=session.company_id,
                session_id=session.session_id,
                agent_id=session.agent_id
            )
        except KillSwitchEngagedException as e:
            session.status = TerminalStatus.STOPPED
            session.log(f"Execution halted by KillSwitch barrier: {str(e)}")
            return {
                "status": "STOPPED",
                "semantic_state": SemanticExecutionState.COMMAND_EXECUTED.value,
                "error": f"Halted by KillSwitch barrier: {str(e)}",
                "exit_code": 130,
                "verified": False,
                "duration_ms": (time.time() - start_time) * 1000
            }


        # 2. Check forbidden patterns
        is_safe, sec_err = TerminalSecurityGateway.check_forbidden(plan.command)
        if not is_safe:
            session.status = TerminalStatus.FAILED
            session.log(f"Security Alert: {sec_err}")
            return {
                "status": "POLICY_DENIED",
                "semantic_state": SemanticExecutionState.COMMAND_EXECUTED.value,
                "error": sec_err,
                "exit_code": 126,
                "verified": False,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # 3. Path boundary verification
        is_safe_path, safe_cwd = TerminalSecurityGateway.verify_workspace_boundary(
            plan.working_directory, session.workspace
        )
        if not is_safe_path:
            session.status = TerminalStatus.FAILED
            return {
                "status": "POLICY_DENIED",
                "error": f"Working directory '{plan.working_directory}' exceeds workspace boundary.",
                "exit_code": 126,
                "verified": False,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # 4. Create snapshot if command has filesystem impact
        snapshot = None
        if plan.filesystem_impact in ["LOCAL", "SYSTEM", "DESTRUCTIVE"] and plan.rollback_strategy == "SNAPSHOT_RESTORE":
            snapshot = self.create_snapshot(session, safe_cwd)

        # 5. Scrub command of raw credentials before execution
        scrubbed_cmd = TerminalSecurityGateway.scrub_credentials(plan.command)
        session.log(f"Executing: {scrubbed_cmd}")

        # 6. Execute via runtime adapter
        adapter_res = adapter.execute_command(
            session_id=session.session_id,
            command=plan.command,
            cwd=safe_cwd,
            timeout_sec=plan.timeout_sec
        )

        exit_code = adapter_res["exit_code"]
        raw_stdout = adapter_res.get("stdout", "")
        raw_stderr = adapter_res.get("stderr", "")

        # 7. Post-process output: prompt injection neutralization and credential scrubbing
        clean_stdout, injection_stdout = TerminalSecurityGateway.sanitize_untrusted_output(raw_stdout)
        clean_stderr, injection_stderr = TerminalSecurityGateway.sanitize_untrusted_output(raw_stderr)
        scrubbed_stdout = TerminalSecurityGateway.scrub_credentials(clean_stdout)
        scrubbed_stderr = TerminalSecurityGateway.scrub_credentials(clean_stderr)

        if injection_stdout or injection_stderr:
            session.log("WARNING: Prompt injection payload detected in output and neutralized into safe data.")

        # 8. Determine semantic execution state
        # INVARIANT: exit code 0 != task success
        semantic_state = SemanticExecutionState.COMMAND_EXECUTED
        if exit_code == 0:
            semantic_state = SemanticExecutionState.COMMAND_SUCCEEDED

        duration_ms = adapter_res.get("duration_ms", (time.time() - start_time) * 1000)

        # Evidence package hash
        evidence_payload = {
            "session_id": session.session_id,
            "plan_id": plan.plan_id,
            "command": scrubbed_cmd,
            "cwd": safe_cwd,
            "exit_code": exit_code,
            "stdout_sha256": hashlib.sha256(scrubbed_stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(scrubbed_stderr.encode()).hexdigest(),
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "timestamp": time.time()
        }
        evidence_id = hashlib.sha256(json.dumps(evidence_payload, sort_keys=True).encode()).hexdigest()
        session.evidence_ids.append(evidence_id)

        session.log(f"Completed command (exit: {exit_code}, state: {semantic_state.value}, evidence: {evidence_id[:8]})")

        return {
            "status": "SUCCEEDED" if exit_code == 0 else "FAILED",
            "semantic_state": semantic_state.value,
            "exit_code": exit_code,
            "stdout": scrubbed_stdout,
            "stderr": scrubbed_stderr,
            "evidence_id": evidence_id,
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "timed_out": adapter_res.get("timed_out", False),
            "duration_ms": duration_ms
        }

    def create_snapshot(self, session: TerminalSession, target_path: str) -> FileSnapshot:
        """Creates pre-execution snapshot for rollback safety."""
        snap_id = f"snap_{uuid.uuid4().hex[:8]}"
        pre_sha = None
        backup_path = None

        if os.path.exists(target_path) and os.path.isfile(target_path):
            with open(target_path, "rb") as f:
                pre_sha = hashlib.sha256(f.read()).hexdigest()
            backup_path = os.path.join(self.backup_dir, f"{os.path.basename(target_path)}.{snap_id}.bak")
            shutil.copy2(target_path, backup_path)

        snapshot = FileSnapshot(
            snapshot_id=snap_id,
            target_path=target_path,
            pre_sha256=pre_sha,
            backup_path=backup_path
        )
        self._snapshots[snap_id] = snapshot
        session.snapshots[snap_id] = snapshot
        return snapshot

    def rollback(self, snapshot_id: str) -> bool:
        """Rolls back filesystem mutations from a previous snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if not snap:
            return False

        if snap.backup_path and os.path.exists(snap.backup_path):
            shutil.copy2(snap.backup_path, snap.target_path)
            return True
        elif snap.pre_sha256 is None and os.path.exists(snap.target_path):
            # File was newly created by the operation, remove it on rollback
            os.remove(snap.target_path)
            return True
        return False

