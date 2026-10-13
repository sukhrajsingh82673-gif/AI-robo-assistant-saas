"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Reversibility & Checkpoint Engine
Implements operation record tracking, reversibility classification, persistent resumable checkpoints,
exact failure-recovery semantics (22 diagnostic questions), and rollback orchestration.

Survives process crashes, timeouts, KillSwitch, and system restarts.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import uuid
import json
import sqlite3
import hashlib
import shutil
import logging
from dataclasses import dataclass, field, asdict

from .models import (
    SemanticExecutionState, TerminalCommandRisk, TerminalStatus,
    VerificationPostcondition, FileSnapshot
)
from .security_agent import ReversibilityClassification

logger = logging.getLogger("zonata.terminal.reversibility")

@dataclass
class TerminalOperationRecord:
    operation_id: str
    parent_operation_id: Optional[str]
    task_id: str
    mission_id: str
    agent_id: str
    session_id: str
    runtime_id: str
    workspace: str
    pre_state: Dict[str, Any]
    command: str
    parameters: Dict[str, Any]
    files_changed: List[str]
    packages_changed: List[str]
    processes_created: List[int]
    network_actions: List[str]
    post_state: Dict[str, Any]
    verification: Dict[str, Any]
    rollback_method: str  # SNAPSHOT_RESTORE, PROCESS_KILL, GIT_RESET, FILE_DELETE, IRREVERSIBLE
    evidence_hash: str
    timestamp: float
    actor: str  # AI_CEO, COWORKER, HUMAN, TERMINAL_AGENT
    authorization: Dict[str, Any]
    reversibility: str  # REVERSIBLE, PARTIALLY_REVERSIBLE, IRREVERSIBLE, UNKNOWN
    status: str = "COMPLETED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TerminalCheckpoint:
    checkpoint_id: str
    mission_id: str
    task_id: str
    subtask_id: Optional[str]
    agent_id: str
    session_id: str
    prompt: str
    execution_plan: Dict[str, Any]
    environment: str
    runtime: str
    tool_versions: Dict[str, str]
    last_successful_checkpoint: Optional[str]
    last_successful_command: Optional[str]
    last_attempted_operation: Optional[str]
    last_command: Optional[str]
    working_directory: str
    files_changed: List[str]
    verification_state: Dict[str, Any]
    failure_state: Optional[Dict[str, Any]]
    rollback_state: Dict[str, Any]
    evidence_refs: List[str]
    next_safe_action: str
    status: str  # RUNNING, INTERRUPTED, RECOVERABLE, ROLLING_BACK, ROLLED_BACK, RESUMING, FAILED, ESCALATED, COMPLETED
    created_at: float
    updated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ReversibilityAndCheckpointEngine:
    """
    Persistent Reversibility & Checkpoint State Engine for the Universal Terminal.
    Stores operations and checkpoints in SQLite database to survive crashes and interruptions.
    """

    def __init__(self, tenant_id: str = "tnt_primary", db_path: Optional[str] = None):
        self.tenant_id = tenant_id
        if db_path is None:
            from core.db import get_default_db_path
            self.db_path = get_default_db_path()
        else:
            self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.backup_dir = os.path.join(os.path.dirname(self.db_path), "terminal_backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS terminal_operations (
                    operation_id TEXT PRIMARY KEY,
                    parent_operation_id TEXT,
                    task_id TEXT,
                    mission_id TEXT,
                    agent_id TEXT,
                    session_id TEXT,
                    runtime_id TEXT,
                    workspace TEXT,
                    command TEXT,
                    reversibility TEXT,
                    rollback_method TEXT,
                    evidence_hash TEXT,
                    timestamp REAL,
                    actor TEXT,
                    status TEXT,
                    payload_json TEXT,
                    tenant_id TEXT DEFAULT 'tnt_primary'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS terminal_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    task_id TEXT,
                    mission_id TEXT,
                    agent_id TEXT,
                    status TEXT,
                    created_at REAL,
                    updated_at REAL,
                    checkpoint_json TEXT,
                    tenant_id TEXT DEFAULT 'tnt_primary'
                )
            """)
            try:
                conn.execute("ALTER TABLE terminal_operations ADD COLUMN tenant_id TEXT DEFAULT 'tnt_primary'")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE terminal_checkpoints ADD COLUMN tenant_id TEXT DEFAULT 'tnt_primary'")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def create_operation(
        self,
        session_id: str,
        task_id: str,
        mission_id: str,
        agent_id: str,
        runtime_id: str,
        workspace: str,
        command: str,
        reversibility: str,
        rollback_method: str = "SNAPSHOT_RESTORE",
        actor: str = "TERMINAL_AGENT",
        parent_operation_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        pre_state: Optional[Dict[str, Any]] = None
    ) -> TerminalOperationRecord:
        """Initializes and records a governed operation before execution."""
        op_id = f"op_{uuid.uuid4().hex[:10]}"
        op = TerminalOperationRecord(
            operation_id=op_id,
            parent_operation_id=parent_operation_id,
            task_id=task_id,
            mission_id=mission_id,
            agent_id=agent_id,
            session_id=session_id,
            runtime_id=runtime_id,
            workspace=workspace,
            pre_state=pre_state or {},
            command=command,
            parameters=parameters or {},
            files_changed=[],
            packages_changed=[],
            processes_created=[],
            network_actions=[],
            post_state={},
            verification={},
            rollback_method=rollback_method,
            evidence_hash="",
            timestamp=time.time(),
            actor=actor,
            authorization={"status": "AUTHORIZED"},
            reversibility=reversibility,
            status="RUNNING"
        )
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO terminal_operations (
                    operation_id, parent_operation_id, task_id, mission_id, agent_id,
                    session_id, runtime_id, workspace, command, reversibility,
                    rollback_method, evidence_hash, timestamp, actor, status, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    op.operation_id, op.parent_operation_id, op.task_id, op.mission_id, op.agent_id,
                    op.session_id, op.runtime_id, op.workspace, op.command, op.reversibility,
                    op.rollback_method, op.evidence_hash, op.timestamp, op.actor, op.status,
                    json.dumps(op.to_dict())
                )
            )
            conn.commit()
        return op

    def update_operation_result(
        self,
        operation_id: str,
        files_changed: List[str],
        processes_created: List[int],
        post_state: Dict[str, Any],
        verification: Dict[str, Any],
        evidence_hash: str,
        status: str = "COMPLETED"
    ) -> Optional[TerminalOperationRecord]:
        """Finalizes operation state and hashes after execution."""
        op = self.get_operation(operation_id)
        if not op:
            return None
        op.files_changed = files_changed
        op.processes_created = processes_created
        op.post_state = post_state
        op.verification = verification
        op.evidence_hash = evidence_hash
        op.status = status

        with self._get_connection() as conn:
            conn.execute(
                """UPDATE terminal_operations SET
                    evidence_hash = ?, status = ?, payload_json = ?
                    WHERE operation_id = ?""",
                (evidence_hash, status, json.dumps(op.to_dict()), operation_id)
            )
            conn.commit()
        return op

    def get_operation(self, operation_id: str) -> Optional[TerminalOperationRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT payload_json FROM terminal_operations WHERE operation_id = ?", (operation_id,)).fetchone()
            if row:
                return TerminalOperationRecord(**json.loads(row["payload_json"]))
        return None

    def save_checkpoint(self, checkpoint: TerminalCheckpoint, tenant_id: Optional[str] = None) -> str:
        """Persists a resumable execution checkpoint."""
        checkpoint.updated_at = time.time()
        t_id = tenant_id or self.tenant_id
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO terminal_checkpoints (
                    checkpoint_id, session_id, task_id, mission_id, agent_id,
                    status, created_at, updated_at, checkpoint_json, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    checkpoint.checkpoint_id, checkpoint.session_id, checkpoint.task_id,
                    checkpoint.mission_id, checkpoint.agent_id, checkpoint.status,
                    checkpoint.created_at, checkpoint.updated_at, json.dumps(checkpoint.to_dict()),
                    t_id
                )
            )
            conn.commit()
        return checkpoint.checkpoint_id

    def get_checkpoint(self, checkpoint_id: str) -> Optional[TerminalCheckpoint]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT checkpoint_json FROM terminal_checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)).fetchone()
            if row:
                return TerminalCheckpoint(**json.loads(row["checkpoint_json"]))
        return None

    def get_latest_session_checkpoint(self, session_id: str, tenant_id: Optional[str] = None) -> Optional[TerminalCheckpoint]:
        t_id = tenant_id or self.tenant_id
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT checkpoint_json FROM terminal_checkpoints WHERE session_id = ? AND tenant_id = ? ORDER BY updated_at DESC LIMIT 1",
                (session_id, t_id)
            ).fetchone()
            if row:
                return TerminalCheckpoint(**json.loads(row["checkpoint_json"]))
        return None

    def create_snapshot(self, target_path: str) -> FileSnapshot:
        """Creates pre-execution snapshot for rollback safety."""
        snap_id = f"snap_{uuid.uuid4().hex[:8]}"
        pre_sha = None
        backup_path = None

        if os.path.exists(target_path) and os.path.isfile(target_path):
            with open(target_path, "rb") as f:
                pre_sha = hashlib.sha256(f.read()).hexdigest()
            backup_path = os.path.join(self.backup_dir, f"{os.path.basename(target_path)}.{snap_id}.bak")
            shutil.copy2(target_path, backup_path)

        return FileSnapshot(
            snapshot_id=snap_id,
            target_path=target_path,
            pre_sha256=pre_sha,
            backup_path=backup_path
        )

    def rollback_snapshot(self, snapshot: FileSnapshot) -> bool:
        """Rolls back filesystem mutations from a snapshot."""
        if snapshot.backup_path and os.path.exists(snapshot.backup_path):
            shutil.copy2(snapshot.backup_path, snapshot.target_path)
            return True
        elif snapshot.pre_sha256 is None and os.path.exists(snapshot.target_path):
            os.remove(snapshot.target_path)
            return True
        return False

    def generate_diagnostic_dossier(self, operation_id: str, error_detail: Optional[str] = None) -> Dict[str, Any]:
        """
        Answers all 22 exact failure-recovery questions required by Section 11 of the specification.
        """
        op = self.get_operation(operation_id)
        if not op:
            return {"error": f"Operation '{operation_id}' not found"}

        return {
            "1_task_executed": op.task_id,
            "2_initiator": op.actor,
            "3_agent_initiated": op.agent_id,
            "4_ceo_instruction": op.mission_id,
            "5_active_prompt": op.parameters.get("prompt", op.command),
            "6_execution_plan": op.parameters.get("plan", op.command),
            "7_runtime_selected": op.runtime_id,
            "8_environment_selected": op.parameters.get("environment_profile_id", "profile_linux_dev"),
            "9_tool_versions_used": op.parameters.get("tool_versions", {"python3": "3.12"}),
            "10_last_successful_command": op.parameters.get("last_successful_command", "none"),
            "11_failed_command": op.command,
            "12_exit_code": op.post_state.get("exit_code", 1),
            "13_output_or_error": error_detail or op.post_state.get("stderr", "Unknown error"),
            "14_files_changed": op.files_changed,
            "15_processes_created": op.processes_created,
            "16_network_activity": op.network_actions,
            "17_verified_conditions": [k for k, v in op.verification.items() if v is True],
            "18_unverified_conditions": [k for k, v in op.verification.items() if v is False],
            "19_rollback_performed": op.rollback_method,
            "20_resume_checkpoint": op.parameters.get("checkpoint_id", "chk_init"),
            "21_next_safe_action": "Rollback filesystem mutations and escalate to AI CEO or retry with doubled timeout" if op.reversibility == "REVERSIBLE" else "Escalate to Human Owner (Irreversible mutation)",
            "22_authorization_required": op.reversibility != "REVERSIBLE"
        }
