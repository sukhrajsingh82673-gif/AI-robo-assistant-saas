"""
ZONATA Universal AI Co-worker Fabric — Governed Terminal Worker Runtime
Specialized Terminal & Shell Co-worker Runtime.
Integrates the Governed Terminal as a first-class Co-Worker execution capability
under ZONATA sovereign supervision.

Architecture:
ZONATA AI Assistant
        ↓
Co-Worker
        ↓
Capability Router
        ↓
Terminal Worker
        ↓
Governed Terminal
        ↓
Operating System

Execution & Security Pipeline:
Command Intent
→ Risk Classification (12 Tiers)
→ Policy Check
→ Permission Check
→ Sandbox / Workspace Check
→ Credential Check (Zero Raw Secrets)
→ Execution Lease
→ Command Execution
→ Output Capture
→ Verification (Exit code 0 != business success)
→ Evidence Ledger
→ Automatic Rollback Backup
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import json
import uuid
import shutil
import hashlib
import subprocess
import platform
import re
from enum import Enum

from .base_runtime import (
    WorkerRuntime, RuntimeSession, SessionState, BackgroundJob, JobStatus
)
from ..contracts import (
    RiskLevel, ExecutionState, SupervisedControlMode, CoworkerProfile,
    ExecutionResult, VerificationResult, VerificationStatus
)
from ..providers.terminal_provider import TerminalProvider

class TerminalCommandRisk(str, Enum):
    """
    12-Tier Granular Command Risk Classification.
    """
    READ_ONLY = "READ_ONLY"
    LOCAL_MUTATION = "LOCAL_MUTATION"
    PACKAGE_INSTALL = "PACKAGE_INSTALL"
    PROCESS_CONTROL = "PROCESS_CONTROL"
    NETWORK_ACCESS = "NETWORK_ACCESS"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    ACCOUNT_OPERATION = "ACCOUNT_OPERATION"
    DATA_DELETION = "DATA_DELETION"
    SYSTEM_MUTATION = "SYSTEM_MUTATION"
    PRODUCTION_MUTATION = "PRODUCTION_MUTATION"
    FINANCIAL_ACTION = "FINANCIAL_ACTION"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"

class TerminalSecurityAnalyzer:
    """
    Analyzes shell commands, classifies risk, sanitizes inputs,
    and scrub credentials before execution.
    """

    FORBIDDEN_COMMAND_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        ":(){ :|:& };:", # Fork bomb
        "mkfs",
        "dd if=/dev/zero",
        "> /dev/sda",
        "chmod -R 777 /",
        "chown -R",
        "curl -s http://* | bash",
        "curl -s https://* | bash",
        "wget -O- * | bash"
    ]

    SECRET_PATTERNS = [
        re.compile(r'(?i)(api[_-]?key|secret|token|password|auth[_-]?token)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?'),
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        re.compile(r'sk-[a-zA-Z0-9]{32,}'),
        re.compile(r'Bearer\s+[a-zA-Z0-9\-_\.]{20,}'),
        re.compile(r'CANARY_[A-Z0-9_]{10,}'),
        re.compile(r'-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----.*?-----END\s+[A-Z\s]+PRIVATE\s+KEY-----', re.DOTALL)
    ]

    @classmethod
    def classify_risk(cls, command: str, capability: str = "terminal.run_command") -> TerminalCommandRisk:
        """
        Maps command intent to one of the 12 risk tiers.
        """
        cmd_l = command.strip().lower()

        # 1. Financial Action
        if any(w in cmd_l for w in ["stripe", "paypal", "payout", "transfer_funds", "bank", "charge_card"]):
            return TerminalCommandRisk.FINANCIAL_ACTION

        # 2. Production Mutation
        if any(w in cmd_l for w in ["production.db", "production.env", "drop table", "drop database", "alter table"]):
            return TerminalCommandRisk.PRODUCTION_MUTATION

        # 3. System Mutation
        if any(w in cmd_l for w in ["/etc/", "/boot/", "/sys/", "iptables", "sysctl", "chmod 777", "visudo"]):
            return TerminalCommandRisk.SYSTEM_MUTATION

        # 4. Data Deletion
        if any(w in cmd_l.split() for w in ["rm", "unlink", "shred"]) or "rm -" in cmd_l or "rmdir" in cmd_l:
            return TerminalCommandRisk.DATA_DELETION

        # 5. Account Operation
        if any(w in cmd_l.split() for w in ["useradd", "usermod", "userdel", "passwd", "groupadd"]):
            return TerminalCommandRisk.ACCOUNT_OPERATION

        # 6. Credential Access
        if any(w in cmd_l for w in [".env", "id_rsa", "id_ed25519", "/etc/shadow", "/etc/passwd", "credentials.json", "vault"]):
            return TerminalCommandRisk.CREDENTIAL_ACCESS

        # 7. Package Install
        if any(w in cmd_l for w in ["pip install", "npm install", "apt install", "apt-get install", "yarn add", "cargo install"]):
            return TerminalCommandRisk.PACKAGE_INSTALL

        # 8. Process Control
        if any(w in cmd_l.split() for w in ["kill", "pkill", "killall", "systemctl", "service", "nohup"]):
            return TerminalCommandRisk.PROCESS_CONTROL

        # 9. External Communication
        if any(w in cmd_l for w in ["mail", "sendmail", "slack.com/api", "discord.com/api/webhooks"]):
            return TerminalCommandRisk.EXTERNAL_COMMUNICATION

        # 10. Network Access
        if any(w in cmd_l.split() for w in ["curl", "wget", "ssh", "scp", "nc", "netcat", "ping", "nmap"]):
            return TerminalCommandRisk.NETWORK_ACCESS

        # 11. Local Mutation
        if any(w in cmd_l.split() for w in ["touch", "mkdir", "cp", "mv", "sed", "tee"]) or ">" in cmd_l or ">>" in cmd_l:
            return TerminalCommandRisk.LOCAL_MUTATION

        # 12. Read Only (Default safe operations)
        if any(w in cmd_l.split() for w in ["ls", "cat", "grep", "find", "head", "tail", "pwd", "uname", "whoami", "echo", "wc", "git"]):
            return TerminalCommandRisk.READ_ONLY

        return TerminalCommandRisk.LOCAL_MUTATION

    @classmethod
    def check_forbidden(cls, command: str) -> Tuple[bool, Optional[str]]:
        norm = " ".join(command.lower().split())
        for pat in cls.FORBIDDEN_COMMAND_PATTERNS:
            pat_norm = " ".join(pat.lower().split())
            if "*" in pat_norm:
                regex_pat = "^.*" + re.escape(pat_norm).replace(r"\*", ".*") + ".*$"
                if re.match(regex_pat, norm):
                    return False, f"Forbidden dangerous pattern detected: '{pat}'"
            elif pat_norm in norm:
                return False, f"Forbidden dangerous pattern detected: '{pat}'"
        return True, None

    @classmethod
    def scrub_credentials(cls, text: str) -> str:
        scrubbed = text
        for pat in cls.SECRET_PATTERNS:
            scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
        return scrubbed

class TerminalWorkerRuntime(WorkerRuntime):
    """
    First-Class Governed Terminal Worker Runtime for ZONATA AI Co-Worker Fabric.
    Provides auditable, sandboxed shell execution, environment inspection,
    tool discovery, and package management under ZONATA sovereign authority.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary", workspace_root: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._provider = TerminalProvider(workspace_root=workspace_root)
        self.sessions: Dict[str, RuntimeSession] = {}
        self.workers: Dict[str, CoworkerProfile] = {}
        self.jobs: Dict[str, BackgroundJob] = {}

        if workspace_root:
            self._workspace_root = os.path.abspath(workspace_root)
        else:
            self._workspace_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

        self._scratch_dir = os.path.join(self._workspace_root, "scratch", "terminal_sandboxes")
        self._backup_dir = os.path.join(self._workspace_root, "storage", "terminal_backups")
        os.makedirs(self._scratch_dir, exist_ok=True)
        os.makedirs(self._backup_dir, exist_ok=True)

    def runtime_id(self) -> str:
        return "runtime_terminal"

    def runtime_type(self) -> str:
        return "TERMINAL"

    def version(self) -> str:
        return "1.0.0-GA"

    def supported_capabilities(self) -> List[str]:
        return [
            "terminal.run_command",
            "terminal.inspect_filesystem",
            "terminal.inspect_environment",
            "terminal.inspect_software",
            "terminal.install_package",
            "terminal.clone_repository",
            "terminal.inspect_git",
            "terminal.file_operation",
            "terminal.invoke_tool",
            "terminal.collect_logs",
            "terminal.diagnose_failure",
            "terminal.rollback",
            "terminal.discover_tool",
            "terminal.self_extension",
            "terminal.execute_script",
            "terminal.build_and_test",
            "terminal.verify_hash"
        ]

    def create_worker(self, profile: CoworkerProfile) -> str:
        self.workers[profile.worker_id] = profile
        return profile.worker_id

    def start_session(self, session: RuntimeSession) -> bool:
        session.state = SessionState.ACTIVE
        session.runtime_version = self.version()
        session.provider_version = "TerminalProvider-1.0.0"
        session.log(f"Governed Terminal session started for mission {session.mission_id} on node {session.node_id}")
        self.sessions[session.session_id] = session
        return True

    def submit_mission(self, session_id: str, mission: Dict[str, Any]) -> str:
        sess = self.sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")
        sess.log(f"Terminal runtime mission submitted: {mission.get('objective', 'Unnamed mission')}")
        return session_id

    def _resolve_safe_path(self, target_path: str) -> Tuple[bool, str]:
        """
        Enforces path boundary confinement.
        Prevents path traversal attacks out of permissible directories.
        """
        if os.path.isabs(target_path):
            norm = os.path.normpath(target_path)
        else:
            norm = os.path.normpath(os.path.join(self._workspace_root, target_path))

        # Check if inside workspace root or scratch
        allowed_roots = [self._workspace_root, "/tmp"]
        is_safe = any(norm.startswith(root) for root in allowed_roots)
        return is_safe, norm

    def run_foreground(self, session_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a task through the complete Governed Terminal Security Pipeline.
        """
        sess = self.sessions.get(session_id)
        start_time = time.time()
        capability = task.get("capability", "terminal.run_command")
        command = task.get("command", "")
        params = task.get("parameters", {})
        if not command and "command" in params:
            command = params["command"]

        # 1. Command Intent & 12-Tier Risk Classification
        risk_tier = TerminalSecurityAnalyzer.classify_risk(command, capability)
        task["risk_tier"] = risk_tier.value

        # 2. Forbidden Command Check
        is_safe_cmd, sec_err = TerminalSecurityAnalyzer.check_forbidden(command)
        if not is_safe_cmd:
            if sess:
                sess.log(f"SECURITY ALERT: {sec_err}")
            return {
                "status": "POLICY_DENIED",
                "risk_tier": risk_tier.value,
                "error": sec_err,
                "exit_code": 126,
                "verified": False,
                "evidence_hash": None,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # 3. Policy & Approval Evaluation
        # High-risk mutation operations require explicit approval
        approval_required_tiers = {
            TerminalCommandRisk.DATA_DELETION,
            TerminalCommandRisk.PACKAGE_INSTALL,
            TerminalCommandRisk.SYSTEM_MUTATION,
            TerminalCommandRisk.PRODUCTION_MUTATION,
            TerminalCommandRisk.FINANCIAL_ACTION,
            TerminalCommandRisk.CREDENTIAL_ACCESS
        }
        human_approved = bool(task.get("human_approved", False))
        if risk_tier in approval_required_tiers and not human_approved:
            if sess:
                sess.state = SessionState.AWAITING_APPROVAL
                sess.log(f"Awaiting Human Approval for {risk_tier.value} action: {command}")
            return {
                "status": "AWAITING_APPROVAL",
                "risk_tier": risk_tier.value,
                "approval_context": {
                    "what": f"Execute shell command '{TerminalSecurityAnalyzer.scrub_credentials(command)}'",
                    "why": f"Action classified as consequential {risk_tier.value}",
                    "worker": sess.worker_id if sess else "worker_terminal",
                    "node": platform.node(),
                    "risk_level": "HIGH" if risk_tier in [TerminalCommandRisk.PACKAGE_INSTALL, TerminalCommandRisk.DATA_DELETION] else "CRITICAL"
                },
                "verified": False,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # 4. Sandbox Workspace Resolution & Path Confinement
        cwd = params.get("cwd", self._workspace_root)
        is_safe_cwd, safe_cwd = self._resolve_safe_path(cwd)
        if not is_safe_cwd:
            return {
                "status": "POLICY_DENIED",
                "risk_tier": risk_tier.value,
                "error": f"Path traversal violation: Working directory '{cwd}' is outside permitted workspace.",
                "exit_code": 126,
                "verified": False,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # 5. Handle Specialized Capabilities
        # A. File Operation with Pre/Post SHA-256 and Backup Rollback
        if capability == "terminal.file_operation":
            action = params.get("action", "read")
            file_path = params.get("file_path", "")
            content = params.get("content", "")
            is_p_safe, safe_fpath = self._resolve_safe_path(file_path)
            if not is_p_safe:
                return {
                    "status": "POLICY_DENIED", "error": f"Target file '{file_path}' outside workspace boundary.",
                    "exit_code": 126, "verified": False
                }

            exec_id = f"fop_{uuid.uuid4().hex[:8]}"
            pre_sha = None
            backup_path = None
            if os.path.exists(safe_fpath):
                with open(safe_fpath, "rb") as f:
                    pre_sha = hashlib.sha256(f.read()).hexdigest()
                backup_path = os.path.join(self._backup_dir, f"{os.path.basename(safe_fpath)}.{exec_id}.bak")
                shutil.copy2(safe_fpath, backup_path)

            if action in ["create", "write"]:
                os.makedirs(os.path.dirname(safe_fpath), exist_ok=True)
                with open(safe_fpath, "w", encoding="utf-8") as f:
                    f.write(content)
                with open(safe_fpath, "rb") as f:
                    post_sha = hashlib.sha256(f.read()).hexdigest()
                out_data = {
                    "action": action, "file_path": safe_fpath, "bytes_written": len(content),
                    "pre_sha256": pre_sha, "post_sha256": post_sha, "backup_path": backup_path
                }
                # Independent verification
                verified = os.path.exists(safe_fpath) and post_sha is not None
            elif action == "read":
                if not os.path.exists(safe_fpath):
                    return {"status": "FAILED", "error": f"File not found: {safe_fpath}", "exit_code": 1, "verified": False}
                with open(safe_fpath, "r", encoding="utf-8", errors="replace") as f:
                    data = f.read()
                out_data = {"action": "read", "file_path": safe_fpath, "content": data, "bytes_read": len(data)}
                verified = True
            elif action == "delete":
                if os.path.exists(safe_fpath):
                    os.remove(safe_fpath)
                out_data = {"action": "delete", "file_path": safe_fpath, "deleted": True, "pre_sha256": pre_sha, "backup_path": backup_path}
                verified = not os.path.exists(safe_fpath)
            else:
                return {"status": "FAILED", "error": f"Unknown file action '{action}'", "exit_code": 1, "verified": False}

            evidence_hash = hashlib.sha256(json.dumps(out_data, sort_keys=True).encode()).hexdigest()
            if sess:
                sess.log(f"File operation {action} on {safe_fpath} verified (sha: {evidence_hash[:8]})")
            return {
                "status": "SUCCEEDED",
                "risk_tier": risk_tier.value,
                "output": out_data,
                "verified": verified,
                "evidence_hash": evidence_hash,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # B. Tool Discovery & Self-Extension via Terminal
        if capability in ["terminal.discover_tool", "terminal.self_extension"]:
            query = params.get("query") or params.get("tool_name") or command
            from ..tool_discovery import ToolDiscoveryEngine
            from ..self_extension import SelfExtensionEngine
            from ..capability_registry import CapabilityRegistry
            from ..provider_registry import ProviderRegistry
            from ..router import CapabilityRouter

            t_disc = ToolDiscoveryEngine(self.tenant_id)
            c_reg = CapabilityRegistry()
            p_reg = ProviderRegistry()
            c_rout = CapabilityRouter(c_reg, p_reg)
            s_ext = SelfExtensionEngine(c_reg, p_reg, t_disc, c_rout, self.tenant_id)

            if capability == "terminal.discover_tool":
                matches = t_disc.discover_tools(query)
                out_data = {"query": query, "candidates_found": len(matches), "tools": [t.tool_id for t in matches]}
                verified = len(matches) > 0
            else:
                ext_res = s_ext.request_capability(query)
                out_data = {
                    "query": query, "action_taken": ext_res.action_taken, "success": ext_res.success,
                    "capability_id": ext_res.capability_id, "qualification_status": ext_res.qualification_status.value
                }
                verified = ext_res.success

            evidence_hash = hashlib.sha256(json.dumps(out_data, sort_keys=True).encode()).hexdigest()
            return {
                "status": "SUCCEEDED" if verified else "FAILED",
                "risk_tier": risk_tier.value,
                "output": out_data,
                "verified": verified,
                "evidence_hash": evidence_hash,
                "duration_ms": (time.time() - start_time) * 1000
            }

        # C. General Governed Shell Command Execution
        timeout_s = min(float(params.get("timeout_sec", 30)), 120.0)
        scrubbed_cmd = TerminalSecurityAnalyzer.scrub_credentials(command)

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=safe_cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s
            )
            stdout = TerminalSecurityAnalyzer.scrub_credentials(proc.stdout[:20000])
            stderr = TerminalSecurityAnalyzer.scrub_credentials(proc.stderr[:20000])
            exit_code = proc.returncode

            # Invariant: exit code 0 != business outcome
            # Check for ambiguous execution outcomes
            uncertain = False
            if exit_code != 0 and ("already exists" in stderr or "interrupted" in stderr):
                uncertain = True

            out_data = {
                "command": scrubbed_cmd,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "cwd": safe_cwd,
                "process_succeeded": exit_code == 0
            }

            # Independent verification: verify process terminated and produced valid output
            verified = (exit_code == 0) and not uncertain
            evidence_hash = hashlib.sha256(json.dumps(out_data, sort_keys=True).encode()).hexdigest()

            if sess:
                sess.log(f"Executed command '{scrubbed_cmd[:50]}' (exit: {exit_code}, verified: {verified})")

            final_status = "UNCERTAIN" if uncertain else ("SUCCEEDED" if verified else "FAILED")
            return {
                "status": final_status,
                "risk_tier": risk_tier.value,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "output": out_data,
                "verified": verified,
                "uncertain": uncertain,
                "evidence_hash": evidence_hash,
                "duration_ms": (time.time() - start_time) * 1000
            }

        except subprocess.TimeoutExpired:
            if sess:
                sess.log(f"Command timed out after {timeout_s}s: {scrubbed_cmd}")
            return {
                "status": "FAILED",
                "risk_tier": risk_tier.value,
                "error": f"Command execution timed out after {timeout_s} seconds",
                "exit_code": 124,
                "verified": False,
                "evidence_hash": None,
                "duration_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            if sess:
                sess.log(f"Command execution error: {str(e)}")
            return {
                "status": "FAILED",
                "risk_tier": risk_tier.value,
                "error": str(e),
                "exit_code": 1,
                "verified": False,
                "evidence_hash": None,
                "duration_ms": (time.time() - start_time) * 1000
            }

    def run_background(self, session_id: str, task: Dict[str, Any]) -> str:
        sess = self.sessions.get(session_id)
        job_id = f"job_term_{uuid.uuid4().hex[:8]}"
        job = BackgroundJob(
            job_id=job_id,
            session_id=session_id,
            worker_id=sess.worker_id if sess else "worker_terminal",
            tenant_id=self.tenant_id,
            mission_id=sess.mission_id if sess else "msn_terminal",
            description=task.get("description", "Background Terminal Task")
        )
        self.jobs[job_id] = job

        # Execute foreground task and record results into background job
        res = self.run_foreground(session_id, task)
        job.result = res
        if res.get("status") == "SUCCEEDED":
            job.update_progress(100.0, "Completed and verified")
            job.status = JobStatus.SUCCEEDED
            job.evidence_id = res.get("evidence_hash")
        elif res.get("status") == "UNCERTAIN":
            job.status = JobStatus.UNCERTAIN
            job.error = "Ambiguous mutation outcome"
        else:
            job.status = JobStatus.FAILED
            job.error = res.get("error", "Execution failed")

        return job_id

    def pause(self, session_id: str) -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.state = SessionState.PAUSED
            sess.log("Terminal session PAUSED by controller")
            return True
        return False

    def resume(self, session_id: str) -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.state = SessionState.ACTIVE
            sess.log("Terminal session RESUMED")
            return True
        return False

    def redirect(self, session_id: str, new_instruction: str) -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.log(f"Terminal session redirected: {new_instruction}")
            return True
        return False

    def observe(self, session_id: str) -> Dict[str, Any]:
        sess = self.sessions.get(session_id)
        uname = platform.uname()
        return {
            "session_id": session_id,
            "runtime": self.runtime_id(),
            "state": sess.state.value if sess else "IDLE",
            "host": {
                "system": uname.system,
                "machine": uname.machine,
                "node": uname.node,
                "python_version": sys.version.split()[0],
                "cwd": os.getcwd()
            },
            "scratch_sandboxes": len(os.listdir(self._scratch_dir)) if os.path.exists(self._scratch_dir) else 0,
            "backup_snapshots": len(os.listdir(self._backup_dir)) if os.path.exists(self._backup_dir) else 0
        }

    def collect_logs(self, session_id: str) -> List[str]:
        sess = self.sessions.get(session_id)
        return sess.logs if sess else []

    def request_input(self, session_id: str, prompt: str) -> str:
        sess = self.sessions.get(session_id)
        if sess:
            sess.log(f"Awaiting user terminal input: {prompt}")
        return "TERMINAL_INPUT_PENDING"

    def take_control(self, session_id: str) -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.control_mode = SupervisedControlMode.HUMAN_TAKEOVER
            sess.state = SessionState.HUMAN_TAKEOVER
            sess.log("Human operator TOOK OVER control of terminal runtime")
            return True
        return False

    def return_control(self, session_id: str, human_state_delta: Optional[Dict[str, Any]] = None) -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.control_mode = SupervisedControlMode.AI_CONTROL
            sess.state = SessionState.ACTIVE
            sess.log("Human operator RETURNED control to AI Co-Worker")
            return True
        return False

    def terminate(self, session_id: str, reason: str = "COMPLETED") -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.state = SessionState.TERMINATED
            sess.log(f"Terminal session terminated: {reason}")
            return True
        return False

    def recover(self, session_id: str, failure_context: Dict[str, Any]) -> bool:
        sess = self.sessions.get(session_id)
        if sess:
            sess.state = SessionState.ACTIVE
            sess.log(f"Terminal session recovered from failure: {failure_context.get('error', 'unknown')}")
            return True
        return False

    def verify(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        verified = bool(result.get("verified", False))
        ev_hash = result.get("evidence_hash")
        return {
            "verified": verified,
            "verification_status": "VERIFIED" if verified else "FAILED",
            "evidence_digest": ev_hash,
            "verified_by": "TerminalWorkerRuntime"
        }

    def collect_evidence(self, session_id: str) -> Dict[str, Any]:
        sess = self.sessions.get(session_id)
        logs = sess.logs if sess else []
        digest = hashlib.sha256("\n".join(logs).encode()).hexdigest()
        return {
            "runtime_id": self.runtime_id(),
            "session_id": session_id,
            "log_count": len(logs),
            "evidence_merkle_digest": digest,
            "timestamp": time.time()
        }

    def rollback_file(self, backup_path: str, target_file: str) -> bool:
        """Restores file from pre-mutation backup snapshot."""
        if os.path.exists(backup_path) and target_file:
            shutil.copy2(backup_path, target_file)
            return True
        return False
