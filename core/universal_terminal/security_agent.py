"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Security & Governance Agent
Layer 3 Independent Supervision Agent.
Enforces the mandatory architectural separation between Technical Completion (Terminal Agent)
and Safe Authorized Completion (Security Agent).

Responsibilities:
- Classify risk into 12 granular tiers
- Inspect requested operations and commands
- Detect dangerous and destructive patterns
- Detect and neutralize prompt-injection content in untrusted output
- Evaluate filesystem scope, path canonicalization, and tenant isolation
- Evaluate network policy and egress controls
- Scrub credentials and protect secret references (Vault)
- Evaluate operation reversibility (REVERSIBLE, PARTIALLY_REVERSIBLE, IRREVERSIBLE, UNKNOWN)
- Produce explicit security decisions (ALLOW, REQUIRE_APPROVAL, DENY, BLOCKED)
- Supervise execution and trigger KillSwitch containment when needed
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import os
import time
import hashlib
import json
import logging
from enum import Enum

from .models import (
    TerminalCommandRisk, IsolationLevel, NetworkMode, TerminalStatus
)
from .security_gateway import TerminalSecurityGateway
from ..killswitch_matrix import KillSwitchMatrix, KillSwitchLevel, KillSwitchEngagedException

logger = logging.getLogger("zonata.terminal.security_agent")

class SecurityDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_MONITORING = "ALLOW_WITH_MONITORING"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_OWNER = "REQUIRE_OWNER"
    DENY = "DENY"
    BLOCKED = "BLOCKED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"

class ReversibilityClassification(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"

class SecurityGovernanceAgent:
    """
    Dedicated Security & Governance Specialist Agent for the Universal Terminal.
    Subordinate to ZONATA Sovereign Authority.
    Ensures that technical execution never bypasses governance, policy, or tenant boundaries.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.killswitch = KillSwitchMatrix(tenant_id=tenant_id)
        self.audit_log: List[Dict[str, Any]] = []

    def evaluate_operation(
        self,
        command: str,
        working_directory: str,
        allowed_workspace: str,
        human_approved: bool = False,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes pre-execution security and governance evaluation.
        Returns detailed security assessment, decision, risk tier, reversibility, and audit tokens.
        """
        start_time = time.time()
        
        # 1. KillSwitch Check
        try:
            self.killswitch.assert_can_execute(
                company_id=self.company_id,
                session_id=session_id,
                agent_id=agent_id
            )
        except KillSwitchEngagedException as e:
            decision = SecurityDecision.BLOCKED
            reason = f"Execution blocked by active KillSwitch: {str(e)}"
            self._record_audit(command, decision, reason, TerminalCommandRisk.SYSTEM_MUTATION, 0)
            return {
                "decision": decision.value,
                "allowed": False,
                "reason": reason,
                "risk_tier": TerminalCommandRisk.SYSTEM_MUTATION.value,
                "reversibility": ReversibilityClassification.UNKNOWN.value,
                "requires_approval": False,
                "killswitch_engaged": True
            }

        # 2. Dangerous Command Patterns
        is_safe, sec_err = TerminalSecurityGateway.check_forbidden(command)
        if not is_safe:
            decision = SecurityDecision.DENY
            self._record_audit(command, decision, sec_err, TerminalCommandRisk.DATA_DELETION, 0)
            return {
                "decision": decision.value,
                "allowed": False,
                "reason": sec_err,
                "risk_tier": TerminalCommandRisk.DATA_DELETION.value,
                "reversibility": ReversibilityClassification.IRREVERSIBLE.value,
                "requires_approval": False,
                "killswitch_engaged": False
            }

        # 3. Path Traversal & Workspace Boundary
        is_boundary_ok, norm_path = TerminalSecurityGateway.verify_workspace_boundary(
            working_directory, allowed_workspace
        )
        if not is_boundary_ok:
            decision = SecurityDecision.DENY
            reason = f"Path traversal violation: '{working_directory}' attempts to escape workspace boundary '{allowed_workspace}'"
            self._record_audit(command, decision, reason, TerminalCommandRisk.SYSTEM_MUTATION, 0)
            return {
                "decision": decision.value,
                "allowed": False,
                "reason": reason,
                "risk_tier": TerminalCommandRisk.SYSTEM_MUTATION.value,
                "reversibility": ReversibilityClassification.UNKNOWN.value,
                "requires_approval": False,
                "killswitch_engaged": False
            }

        # 4. Risk Classification
        risk_tier = TerminalSecurityGateway.classify_risk(command)

        # 5. Reversibility Classification
        reversibility = self.classify_reversibility(command, risk_tier)

        # 6. Authorization Policy Enforcement
        approval_ok, approval_err = TerminalSecurityGateway.check_authorization(
            risk_tier, human_approved=human_approved, tenant_id=self.tenant_id, company_id=self.company_id
        )
        if not approval_ok:
            decision = SecurityDecision.REQUIRE_APPROVAL
            self._record_audit(command, decision, approval_err, risk_tier, 0)
            return {
                "decision": decision.value,
                "allowed": False,
                "reason": approval_err,
                "risk_tier": risk_tier.value,
                "reversibility": reversibility.value,
                "requires_approval": True,
                "killswitch_engaged": False
            }

        # 7. Approved with monitoring
        decision = SecurityDecision.ALLOW if risk_tier == TerminalCommandRisk.READ_ONLY else SecurityDecision.ALLOW_WITH_MONITORING
        self._record_audit(command, decision, "Operation cleared by Security & Governance Agent", risk_tier, (time.time() - start_time) * 1000)

        return {
            "decision": decision.value,
            "allowed": True,
            "reason": "Operation cleared by Security & Governance Agent",
            "risk_tier": risk_tier.value,
            "reversibility": reversibility.value,
            "requires_approval": False,
            "killswitch_engaged": False
        }

    def classify_reversibility(self, command: str, risk_tier: TerminalCommandRisk) -> ReversibilityClassification:
        """
        Classifies operation reversibility:
        REVERSIBLE: Local file edits, git changes, process spawns (with rollback snapshots).
        PARTIALLY_REVERSIBLE: Package installs (packages can be uninstalled, but cache/state remains).
        IRREVERSIBLE: Permanent deletions (shred, raw rm without backup), external financial actions, email sends.
        UNKNOWN: Ambiguous or unparseable shell pipelines.
        """
        cmd_l = command.strip().lower()

        # Irreversible actions
        if (
            risk_tier in [TerminalCommandRisk.DATA_DELETION, TerminalCommandRisk.FINANCIAL_ACTION, TerminalCommandRisk.EXTERNAL_COMMUNICATION]
            or any(w in cmd_l for w in ["shred", "rm -rf", "rm -r", "rm ", "dd if=", "mkfs", "payout", "stripe", "charge", "mail", "sendmail", "curl -x post", "curl -d"])
        ):
            return ReversibilityClassification.IRREVERSIBLE

        # Partially reversible
        if risk_tier in [TerminalCommandRisk.PACKAGE_INSTALL, TerminalCommandRisk.SYSTEM_MUTATION]:
            return ReversibilityClassification.PARTIALLY_REVERSIBLE

        # Reversible under snapshot restore
        if risk_tier in [TerminalCommandRisk.READ_ONLY, TerminalCommandRisk.LOCAL_MUTATION]:
            return ReversibilityClassification.REVERSIBLE

        if any(cmd_l.startswith(prefix) for prefix in ["touch ", "cat ", "echo ", "git ", "python3 ", "python ", "node "]):
            return ReversibilityClassification.REVERSIBLE

        return ReversibilityClassification.UNKNOWN

    def sanitize_and_scrub(self, raw_output: str) -> Tuple[str, bool, bool]:
        """
        Scans output for prompt injection attempts and scrubs credentials.
        Returns: (clean_output, injection_detected, credentials_scrubbed)
        """
        clean_text, injection_detected = TerminalSecurityGateway.sanitize_untrusted_output(raw_output)
        scrubbed_text = TerminalSecurityGateway.scrub_credentials(clean_text)
        credentials_scrubbed = (scrubbed_text != clean_text)
        return scrubbed_text, injection_detected, credentials_scrubbed

    def trigger_containment(self, session_id: str, reason: str) -> str:
        """
        Triggers emergency KillSwitch containment at SESSION scope.
        """
        logger.warning(f"SECURITY AGENT TRIGGERING CONTAINMENT: Session={session_id}, Reason={reason}")
        sw_id = self.killswitch.activate(
            level=KillSwitchLevel.SESSION.value,
            target_id=session_id,
            reason=f"Security Agent Containment: {reason}"
        )
        return sw_id

    def release_containment(self, switch_id: str) -> bool:
        """Deactivates a previously triggered containment switch."""
        return self.killswitch.deactivate(switch_id)

    def _record_audit(
        self,
        command: str,
        decision: SecurityDecision,
        reason: str,
        risk_tier: TerminalCommandRisk,
        duration_ms: float
    ):
        self.audit_log.append({
            "timestamp": time.time(),
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "command": TerminalSecurityGateway.scrub_credentials(command),
            "decision": decision.value,
            "reason": reason,
            "risk_tier": risk_tier.value if hasattr(risk_tier, "value") else str(risk_tier),
            "duration_ms": duration_ms
        })
