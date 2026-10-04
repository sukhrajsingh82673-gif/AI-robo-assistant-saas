"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Failure Recovery Engine
Diagnoses failures, classifies error types, and plans recovery actions.
Crucial Invariant: The Terminal Agent can bypass TECHNICAL LIMITATIONS (missing dependencies,
runtime mismatch, resource exhaustion, transient errors), but CAN NEVER bypass
ZONATA security/authorization controls, tenant boundaries, or KillSwitch barriers.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import time
import logging
from .models import (
    FailureClassification, CommandPlan, TerminalSession, TerminalStatus
)

logger = logging.getLogger("zonata.terminal.recovery")

class TerminalFailureRecoveryEngine:
    """
    Intelligent failure classification and recovery planner.
    Differentiates between resolvable technical limitations vs inviolable security boundaries.
    """

    MAX_RETRIES_PER_TASK = 3

    @classmethod
    def classify_failure(cls, exit_code: int, stdout: str, stderr: str) -> FailureClassification:
        combined = (stdout + " " + stderr).lower()

        # 1. Security / Policy Denial (CANNOT BE BYPASSED)
        if "policy_denied" in combined or "forbidden dangerous pattern" in combined or "killswitch" in combined or "security alert" in combined:
            return FailureClassification.SECURITY_DENIAL

        # 2. Timeout
        if exit_code == 124 or "timed out" in combined:
            return FailureClassification.TIMEOUT

        # 3. Missing Dependencies (Technical Limitation - RESOLVABLE)
        dep_patterns = [
            "no module named", "command not found", "cannot find package",
            "not installed", "pkg-config: not found", "unable to locate package",
            "import error", "module not found"
        ]
        if any(pat in combined for pat in dep_patterns):
            return FailureClassification.DEPENDENCY_FAILURE

        # 4. Resource Exhaustion (Technical Limitation - RESOLVABLE BY RESIZING)
        res_patterns = ["out of memory", "cannot allocate memory", "no space left on device", "resource temporarily unavailable"]
        if any(pat in combined for pat in res_patterns):
            return FailureClassification.RESOURCE_EXHAUSTION

        # 5. Network Failure (Technical Limitation - RESOLVABLE)
        net_patterns = ["could not resolve host", "connection refused", "network is unreachable", "connection timed out"]
        if any(pat in combined for pat in net_patterns):
            return FailureClassification.NETWORK_FAILURE

        # 6. Build Failure
        if "syntax error" in combined or "compilation failed" in combined or "error: " in combined:
            return FailureClassification.BUILD_FAILURE

        # 7. Permission Failure (OS level)
        if "permission denied" in combined or "operation not permitted" in combined:
            return FailureClassification.PERMISSION_FAILURE

        return FailureClassification.UNKNOWN_FAILURE

    @classmethod
    def plan_recovery(
        cls,
        session: TerminalSession,
        failed_plan: CommandPlan,
        classification: FailureClassification,
        error_output: str,
        attempt_count: int
    ) -> Tuple[bool, Optional[str], Optional[CommandPlan]]:
        """
        Determines if and how a failure can be safely recovered.
        Returns: (can_recover, explanation, recovery_plan)
        """
        if attempt_count >= cls.MAX_RETRIES_PER_TASK:
            session.log(f"Recovery aborted: exceeded max retry limit ({cls.MAX_RETRIES_PER_TASK}). Escalating to AICU.")
            session.status = TerminalStatus.ESCALATED
            return False, "Exceeded retry limit; technical recovery exhausted. Requires AICU or human intervention.", None

        # INVIOLABLE BARRIER: Security denials cannot be bypassed
        if classification == FailureClassification.SECURITY_DENIAL:
            session.log("SECURITY ALERT: Operation was denied by policy or barrier. Recovery refused.")
            session.status = TerminalStatus.ESCALATED
            return False, "Operation denied by ZONATA security/policy boundary. Cannot be bypassed autonomously.", None

        # Technical Limitation: Missing Dependency
        if classification == FailureClassification.DEPENDENCY_FAILURE:
            # Detect missing tool or python module
            missing_mod = None
            m = re.search(r"no module named ['\"]([^'\"]+)['\"]", error_output, re.IGNORECASE)
            if m:
                missing_mod = m.group(1)
            elif "pytest: command not found" in error_output.lower():
                missing_mod = "pytest"

            if missing_mod:
                session.log(f"Resolving technical limitation: Missing dependency '{missing_mod}' detected. Creating install plan.")
                recovery_cmd = f"pip install --quiet {missing_mod}"
                rec_plan = CommandPlan(
                    plan_id=f"rec_dep_{missing_mod}",
                    objective=f"Install missing dependency '{missing_mod}' to unblock technical execution",
                    environment_profile_id=failed_plan.environment_profile_id,
                    working_directory=failed_plan.working_directory,
                    command=recovery_cmd,
                    filesystem_impact="LOCAL",
                    risk_level=failed_plan.risk_level,
                    timeout_sec=60.0
                )
                return True, f"Installing required dependency '{missing_mod}' to resolve technical limitation.", rec_plan

        # Technical Limitation: Resource Exhaustion
        if classification == FailureClassification.RESOURCE_EXHAUSTION:
            session.log("Resolving technical limitation: Resource exhaustion. Suggesting runtime profile shift to larger node/lightweight mode.")
            return True, "Resource bottleneck detected. Shift execution substrate to high-memory profile.", None

        # Technical Limitation: Timeout
        if classification == FailureClassification.TIMEOUT:
            new_timeout = failed_plan.timeout_sec * 2.0
            session.log(f"Resolving technical limitation: Increasing timeout from {failed_plan.timeout_sec}s to {new_timeout}s.")
            rec_plan = CommandPlan(
                plan_id=f"rec_timeout_{failed_plan.plan_id}",
                objective=failed_plan.objective,
                environment_profile_id=failed_plan.environment_profile_id,
                working_directory=failed_plan.working_directory,
                command=failed_plan.command,
                filesystem_impact=failed_plan.filesystem_impact,
                risk_level=failed_plan.risk_level,
                timeout_sec=new_timeout
            )
            return True, f"Retrying with doubled execution timeout ({new_timeout}s).", rec_plan

        return False, f"Automated recovery unavailable for {classification.value}. Escalating to AICU.", None
