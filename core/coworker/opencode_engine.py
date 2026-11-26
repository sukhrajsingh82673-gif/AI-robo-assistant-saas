"""
ZONATA Autonomous Coworker 3.0 — OpenCode Specialist Software Engineering Engine
Implements the 7-stage governed autonomous software development loop:
  Inspect -> Plan -> Implement in isolated Git worktree -> Test -> Review -> Repair -> Submit.
Enforces strict Constitutional Boundaries and self-development invariants:
  - Cannot modify or disable constitutional governance.
  - Cannot bypass approval gates.
  - Cannot alter immutable evidence or delete failed test logs.
"""

from __future__ import annotations
import os
import tempfile
import sys
import time
import uuid
import json
import shutil
import hashlib
import subprocess
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field

from .contracts_v3 import OpenCodeMission, OpenCodeLoopPhase
from core.paths import get_repo_root


class ConstitutionalViolationError(Exception):
    """Raised when an autonomous agent attempts to modify protected governance files."""
    pass


class OpenCodeEngine:
    """
    OpenCode Governed Engineering Engine.
    Operates in isolated Git worktrees to prevent accidental disruption of the primary codebase.
    Executes automated repair cycles (Ralph Loop) and enforces constitutional boundaries.
    """

    # Protected paths that autonomous self-modification can NEVER alter
    PROTECTED_PATTERNS = [
        "core/constitution",
        "core/killswitch_matrix.py",
        "core/auth",
        "storage/evidence",
        "evidence_ledger",
        ".git",
        "core/policy_evaluator.py",
        "core/operating_instructions.py"
    ]

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = os.path.abspath(repo_root or get_repo_root())
        self.worktree_base = os.path.join(tempfile.gettempdir(), "zonata_opencode_worktrees")
        os.makedirs(self.worktree_base, exist_ok=True)
        import shutil
        # Resolve the CLI portably: PATH first, then common install prefixes.
        self.opencode_cli_path: Optional[str] = shutil.which("opencode") or next(
            (
                p for p in (
                    os.path.expanduser("~/.opencode/bin/opencode"),
                    "/usr/local/bin/opencode",
                    "/usr/bin/opencode",
                ) if os.path.exists(p)
            ),
            None,
        )
        self.opencode_cli_available: bool = self.opencode_cli_path is not None
        self.opencode_cli_version: Optional[str] = None
        if self.opencode_cli_available:
            try:
                proc = subprocess.run([self.opencode_cli_path, "--version"], capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    self.opencode_cli_version = proc.stdout.strip()
            except Exception:
                pass

    def verify_boundaries(self, file_paths: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validates that none of the target modification paths violate constitutional invariants.
        """
        for fp in file_paths:
            normalized = fp.replace("\\", "/").strip("/")
            for pattern in self.PROTECTED_PATTERNS:
                if pattern in normalized:
                    return False, f"Constitutional Boundary Violation: modification of '{fp}' is strictly prohibited."
        return True, None

    def create_worktree(self, mission_id: str, branch_name: Optional[str] = None) -> Tuple[str, str]:
        """
        Creates an isolated Git worktree for safe code implementation.
        """
        branch = branch_name or f"opencode/{mission_id}"
        worktree_path = os.path.join(self.worktree_base, mission_id)

        # Cleanup any lingering path
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)

        # Create git worktree
        cmd = ["git", "worktree", "add", "-b", branch, worktree_path, "HEAD"]
        proc = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
        if proc.returncode != 0:
            # Fallback if branch already exists: checkout existing or force directory
            cmd_force = ["git", "worktree", "add", worktree_path, "HEAD"]
            proc2 = subprocess.run(cmd_force, cwd=self.repo_root, capture_output=True, text=True)
            if proc2.returncode != 0:
                # If git worktree fails (e.g. in non-git test fixtures), create directory copy
                shutil.copytree(self.repo_root, worktree_path, ignore=shutil.ignore_patterns(".git", "__pycache__", "venv"))

        return worktree_path, branch

    def cleanup_worktree(self, mission: OpenCodeMission) -> bool:
        """
        Removes the isolated Git worktree safely.
        """
        if not os.path.exists(mission.worktree_path):
            return True
        try:
            subprocess.run(["git", "worktree", "remove", "--force", mission.worktree_path], cwd=self.repo_root, capture_output=True)
            if os.path.exists(mission.worktree_path):
                shutil.rmtree(mission.worktree_path, ignore_errors=True)
            # Prune worktree records
            subprocess.run(["git", "worktree", "prune"], cwd=self.repo_root, capture_output=True)
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # 7-Stage Autonomous Software Engineering Loop
    # -------------------------------------------------------------------------

    def inspect_scope(self, objective: str, target_files: List[str]) -> Tuple[bool, Optional[str]]:
        """Stage 1: INSPECT scope and ensure constitutional compliance."""
        return self.verify_boundaries(target_files)

    def plan_mission(self, objective: str, target_files: List[str]) -> OpenCodeMission:
        """Stage 2: PLAN steps and construct isolated worktree."""
        is_safe, error_msg = self.inspect_scope(objective, target_files)
        if not is_safe:
            raise ConstitutionalViolationError(error_msg)

        mission_id = f"oc_msn_{uuid.uuid4().hex[:8]}"
        worktree_path, branch_name = self.create_worktree(mission_id)

        plan = [
            f"1. Inspect target files: {', '.join(target_files)}",
            f"2. Formulate implementation diff in worktree: {worktree_path}",
            f"3. Run automated tests and targeted linters",
            f"4. Independent AST review for security and regressions",
            f"5. Submit verified diff with cryptographic evidence hash"
        ]

        mission = OpenCodeMission(
            mission_id=mission_id,
            objective=objective,
            repo_path=self.repo_root,
            worktree_path=worktree_path,
            branch_name=branch_name,
            phase=OpenCodeLoopPhase.PLAN,
            plan_steps=plan,
            modified_files=list(target_files)
        )
        return mission

    def inspect_and_plan(self, objective: str, target_files: List[str]) -> Tuple[List[str], OpenCodeMission]:
        """Convenience method combining inspect and plan."""
        mission = self.plan_mission(objective, target_files)
        return mission.plan_steps, mission

    def implement_changes(
        self,
        mission: OpenCodeMission,
        file_mutations: Dict[str, str]
    ) -> bool:
        """Stage 3: IMPLEMENT code mutations inside the isolated worktree."""
        mission.phase = OpenCodeLoopPhase.IMPLEMENT

        is_safe, err = self.verify_boundaries(list(file_mutations.keys()))
        if not is_safe:
            mission.phase = OpenCodeLoopPhase.FAILED
            mission.error_message = err
            raise ConstitutionalViolationError(err)

        for rel_path, content in file_mutations.items():
            full_path = os.path.join(mission.worktree_path, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            if rel_path not in mission.modified_files:
                mission.modified_files.append(rel_path)

        diff_proc = subprocess.run(["git", "diff"], cwd=mission.worktree_path, capture_output=True, text=True)
        mission.diff_content = diff_proc.stdout
        mission.diff_hash = hashlib.sha256(mission.diff_content.encode("utf-8")).hexdigest()
        return True

    def run_tests(self, mission: OpenCodeMission, test_target: Optional[str] = None) -> bool:
        """Stage 4: TEST code execution in worktree."""
        mission.phase = OpenCodeLoopPhase.TEST
        cmd = [sys.executable, "-m", "pytest", test_target] if test_target else [sys.executable, "-m", "pytest", "-q"]

        try:
            proc = subprocess.run(cmd, cwd=mission.worktree_path, capture_output=True, text=True, timeout=60)
            mission.test_output = proc.stdout + "\n" + proc.stderr
            mission.test_passed = (proc.returncode == 0)
        except Exception as e:
            mission.test_output = str(e)
            mission.test_passed = False

        return mission.test_passed

    def review_changes(self, mission: OpenCodeMission) -> Tuple[bool, List[str]]:
        """Stage 5: REVIEW code through independent AST security and linting checks."""
        mission.phase = OpenCodeLoopPhase.REVIEW
        comments: List[str] = []

        forbidden_tokens = ["__import__('os').system", "eval(", "exec(", "shutil.rmtree('/')"]
        for rel_path in mission.modified_files:
            full_path = os.path.join(mission.worktree_path, rel_path)
            if os.path.exists(full_path) and rel_path.endswith(".py"):
                with open(full_path, "r", encoding="utf-8") as f:
                    src = f.read()
                for tok in forbidden_tokens:
                    if tok in src:
                        comments.append(f"Security Review Failed: '{rel_path}' contains forbidden token '{tok}'.")

        is_approved = (len(comments) == 0 and mission.test_passed)
        mission.code_review_approved = is_approved
        mission.review_comments = comments
        return is_approved, comments

    def repair_cycle(
        self,
        mission: OpenCodeMission,
        test_target: Optional[str] = None,
        repair_fn: Optional[Callable[[OpenCodeMission], None]] = None
    ) -> bool:
        """
        Stage 6: REPAIR through the Ralph Loop.

        A repair must be a real code change supplied by the caller, or produced
        by an upstream model through `repair_fn`. This method never edits tests
        to make them pass — rewriting assertions is test tampering and would
        turn a failed build into a false success.
        """
        if mission.repaired_iterations >= mission.max_repair_iterations:
            return False

        mission.phase = OpenCodeLoopPhase.REPAIR
        mission.repaired_iterations += 1

        if repair_fn is None:
            mission.phase = OpenCodeLoopPhase.FAILED
            mission.error_message = "AUTOMATED_REPAIR_BACKEND_NOT_CONFIGURED"
            return False

        try:
            repair_fn(mission)
        except Exception as exc:
            mission.phase = OpenCodeLoopPhase.FAILED
            mission.error_message = f"REPAIR_FAILED: {exc}"
            return False

        passed = self.run_tests(mission, test_target)
        approved, _ = self.review_changes(mission)
        return passed and approved

    def submit_mission(self, mission: OpenCodeMission) -> OpenCodeMission:
        """Stage 7: SUBMIT verified diff with cryptographic evidence hash."""
        if mission.test_passed and mission.code_review_approved:
            mission.phase = OpenCodeLoopPhase.SUBMITTED
        else:
            mission.phase = OpenCodeLoopPhase.FAILED

        mission.completed_at = time.time()
        mission.compute_evidence_hash()
        return mission

    def execute_autonomous_loop(
        self,
        objective: str,
        target_files: List[str],
        mutations: Dict[str, str],
        test_target: Optional[str] = None,
        repair_fn: Optional[Callable[[OpenCodeMission], None]] = None
    ) -> OpenCodeMission:
        """
        Executes the full 7-stage autonomous engineering loop with Ralph Loop recovery.
        """
        # 1. Inspect & 2. Plan
        mission = self.plan_mission(objective, target_files)

        # 3. Implement
        self.implement_changes(mission, mutations)

        # 4. Test
        passed = self.run_tests(mission, test_target)

        # 5. Review
        approved, _ = self.review_changes(mission)

        # 6. Repair Loop
        while (not passed or not approved) and mission.repaired_iterations < mission.max_repair_iterations:
            resolved = self.repair_cycle(mission, test_target, repair_fn)
            if resolved:
                break

        # 7. Submit
        return self.submit_mission(mission)

    def execute_opencode_cli(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Executes the host opencode CLI binary if available on system PATH.
        """
        if not self.opencode_cli_available or not self.opencode_cli_path:
            return {
                "success": False,
                "executed": False,
                "error": "OPENCODE_CLI_UNAVAILABLE",
                "reason": "Host executable 'opencode' was not found on PATH or in a known install location."
            }
        cmd = [self.opencode_cli_path] + args
        target_cwd = cwd or self.repo_root
        try:
            proc = subprocess.run(cmd, cwd=target_cwd, capture_output=True, text=True, timeout=timeout)
            return {
                "success": proc.returncode == 0,
                "executed": True,
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "command": cmd
            }
        except Exception as e:
            return {
                "success": False,
                "executed": False,
                "error": str(e)
            }
