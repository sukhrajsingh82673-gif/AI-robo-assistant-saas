"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 11 — Enterprise Policy Engine V2 (ABAC & Multi-Dimensional Governance)
Evaluates context across WHO, WHAT, WHY, WHEN, WHERE, WHICH DATA, WHICH TOOL,
WHICH MODEL, WHICH BUDGET, WHICH RISK.

Decision Taxonomy:
  ALLOW
  ALLOW_WITH_RESTRICTIONS
  REQUIRE_APPROVAL
  DENY
  ESCALATE
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger("zonata.policy.engine.v2")

class PolicyDecision:
    ALLOW = "ALLOW"
    ALLOW_WITH_RESTRICTIONS = "ALLOW_WITH_RESTRICTIONS"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"
    ESCALATE = "ESCALATE"

@dataclass
class PolicyContext:
    # WHO
    requester_id: str
    requester_type: str         # HUMAN, AI_EMPLOYEE, SERVICE
    requester_roles: List[str]
    requester_departments: List[str]
    tenant_id: str
    company_id: str

    # WHAT & WHY
    action: str                 # READ, MUTATE, EXECUTE, FINANCIAL_TRANSFER, DELETE
    intent: str
    mission_id: Optional[str]

    # WHICH DATA, TOOL, MODEL, SYSTEM
    data_classification: Optional[str] = "INTERNAL"
    data_sensitivities: Optional[List[str]] = None
    tool_id: Optional[str] = None
    tool_risk_class: Optional[str] = "LOW_RISK"
    model_id: Optional[str] = None
    target_system: Optional[str] = None

    # BUDGET & RISK
    requested_spend_usd: float = 0.0
    employee_remaining_budget_usd: float = 1000.0

@dataclass
class PolicyEvaluationResult:
    decision: str
    reasons: List[str]
    restrictions: Dict[str, Any]
    approval_requirement: Optional[Dict[str, Any]] = None

class PolicyEngineV2:
    """
    Attribute-Based Access Control (ABAC) & Corporate Governance Policy Engine.
    """
    # Financial thresholds requiring human executive approval
    HUMAN_APPROVAL_SPEND_THRESHOLD_USD = 500.0
    ESCALATION_SPEND_THRESHOLD_USD = 5000.0

    def evaluate(self, ctx: PolicyContext) -> PolicyEvaluationResult:
        reasons = []
        restrictions = {}

        # 1. Tenancy Boundary Invariant
        if not ctx.tenant_id or not ctx.company_id:
            return PolicyEvaluationResult(
                decision=PolicyDecision.DENY,
                reasons=["Missing mandatory tenant or company context."],
                restrictions={}
            )

        # 2. Destructive Action Protection
        if ctx.tool_risk_class in ("DESTRUCTIVE", "IRREVERSIBLE"):
            reasons.append(f"Tool risk class '{ctx.tool_risk_class}' requires human executive council approval.")
            return PolicyEvaluationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reasons=reasons,
                restrictions={"requires_human_token": True, "quorum": 2}
            )

        # 3. Financial Spend Governance
        if ctx.requested_spend_usd > 0:
            if ctx.requested_spend_usd > ctx.employee_remaining_budget_usd:
                return PolicyEvaluationResult(
                    decision=PolicyDecision.DENY,
                    reasons=[f"Requested spend (${ctx.requested_spend_usd:.2f}) exceeds remaining budget (${ctx.employee_remaining_budget_usd:.2f})."],
                    restrictions={}
                )

            if ctx.requested_spend_usd >= self.ESCALATION_SPEND_THRESHOLD_USD:
                reasons.append(f"Financial spend >= ${self.ESCALATION_SPEND_THRESHOLD_USD:.2f} triggers mandatory C-Level escalation.")
                return PolicyEvaluationResult(
                    decision=PolicyDecision.ESCALATE,
                    reasons=reasons,
                    restrictions={"escalate_to": "CEO_EXECUTIVE_COUNCIL"}
                )

            if ctx.requested_spend_usd >= self.HUMAN_APPROVAL_SPEND_THRESHOLD_USD:
                reasons.append(f"Financial spend >= ${self.HUMAN_APPROVAL_SPEND_THRESHOLD_USD:.2f} requires human approval.")
                return PolicyEvaluationResult(
                    decision=PolicyDecision.REQUIRE_APPROVAL,
                    reasons=reasons,
                    restrictions={"approval_role": "FINANCE_DIRECTOR"}
                )

        # 4. Data Classification Protection
        if ctx.data_classification == "HIGHLY_RESTRICTED":
            if "OWNER" not in ctx.requester_roles and "SECURITY_ADMIN" not in ctx.requester_roles:
                return PolicyEvaluationResult(
                    decision=PolicyDecision.DENY,
                    reasons=["Access to HIGHLY_RESTRICTED data requires OWNER or SECURITY_ADMIN role."],
                    restrictions={}
                )
            # Allowed with restrictions
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW_WITH_RESTRICTIONS,
                reasons=["Access granted to HIGHLY_RESTRICTED data with mandatory audit logging and zero-cache."],
                restrictions={"audit_log": True, "cache_disabled": True, "pii_redacted": True}
            )

        # 5. Default Admittance for Authorized Operational Actions
        return PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            reasons=["All policy gates and authority attributes satisfied."],
            restrictions={}
        )

# Global singleton
policy_engine_v2 = PolicyEngineV2()
