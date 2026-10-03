"""
RoboAssistant Enterprise — Machine-Enforced CEO Policy & Boundary Matrix
Provides deterministic, code-enforced boundaries over AI CEO and workforce actions.
Prohibits privilege escalation, restricts financial thresholds, and strictly gates
irreversible enterprise operations.
"""

import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from .db import db

logger = logging.getLogger("ZonataPolicyMatrix")

class GovernanceViolationException(Exception):
    """Raised when an actor attempts an action violating policy boundaries."""
    pass

class ActorRole:
    AI_CEO = "AI_CEO"
    DEPT_HEAD = "DEPT_HEAD"
    SPECIALIST = "SPECIALIST"
    HUMAN_OWNER = "HUMAN_OWNER"

class ActionCategory:
    READ = "READ"
    OPERATIONAL_MUTATION = "OPERATIONAL_MUTATION"
    FINANCIAL_MUTATION = "FINANCIAL_MUTATION"
    IRREVERSIBLE_ACTION = "IRREVERSIBLE_ACTION"

class ExecutivePolicyMatrixEnforcer:
    """
    Evaluates and enforces authority boundaries before any executive or autonomous action.
    """

    # Baseline limits
    AI_CEO_MAX_SPEND_INR = 50000.0         # Above ₹50,000 requires Human Owner approval
    DEPT_HEAD_MAX_SPEND_INR = 10000.0      # Above ₹10,000 requires AI CEO approval
    SPECIALIST_MAX_SPEND_INR = 2000.0      # Above ₹2,000 requires Dept Head approval

    FORBIDDEN_AI_ACTIONS = {
        "DROP_TABLE",
        "PURGE_AUDIT_LOGS",
        "EXTERNAL_CAPITAL_TRANSFER",
        "SIGN_LEGAL_CONTRACT",
        "OVERRIDE_KILLSWITCH",
        "MASS_CUSTOMER_TERMINATION",
        "ROTATE_SOVEREIGN_ROOT_KEY"
    }

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._ensure_baseline_rules()

    def _ensure_baseline_rules(self):
        """Seeds standard enterprise rules if not present in DB."""
        with db.get_connection() as conn:
            cnt = conn.execute(
                "SELECT count(*) FROM executive_policy_rules WHERE tenant_id = ?",
                (self.tenant_id,)
            ).fetchone()[0]
            if cnt == 0:
                now = time.time()
                rules = [
                    (f"rul_{uuid.uuid4().hex[:8]}", self.tenant_id, ActorRole.AI_CEO, ActionCategory.READ, 0.0, 0, 0, 0, "CEO read-only telemetry", now),
                    (f"rul_{uuid.uuid4().hex[:8]}", self.tenant_id, ActorRole.AI_CEO, ActionCategory.OPERATIONAL_MUTATION, 50000.0, 0, 0, 0, "Autonomous operational workflows up to ₹50k", now),
                    (f"rul_{uuid.uuid4().hex[:8]}", self.tenant_id, ActorRole.AI_CEO, ActionCategory.FINANCIAL_MUTATION, 50000.0, 1, 0, 0, "Financial mutations above ₹50k require Owner approval", now),
                    (f"rul_{uuid.uuid4().hex[:8]}", self.tenant_id, ActorRole.AI_CEO, ActionCategory.IRREVERSIBLE_ACTION, 0.0, 1, 1, 1, "Irreversible actions forbidden to AI CEO", now),
                    (f"rul_{uuid.uuid4().hex[:8]}", self.tenant_id, ActorRole.HUMAN_OWNER, ActionCategory.IRREVERSIBLE_ACTION, 10000000.0, 0, 1, 0, "Owner dual-key authorized for irreversible actions", now),
                ]
                conn.executemany(
                    """
                    INSERT INTO executive_policy_rules (
                        rule_id, tenant_id, role, action_category,
                        max_amount_inr, requires_human_approval,
                        dual_key_required, is_forbidden, description, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rules
                )
                conn.commit()

    def validate_action(
        self,
        actor_role: str,
        action_name: str,
        action_category: str,
        amount_inr: float = 0.0,
        owner_signature: Optional[str] = None,
        dual_key_signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates whether the requested action is permitted under enterprise policy boundaries.
        Raises GovernanceViolationException if boundary is breached.
        """
        norm_action = action_name.upper().strip()

        # 1. Check absolute AI prohibitions
        if actor_role != ActorRole.HUMAN_OWNER and norm_action in self.FORBIDDEN_AI_ACTIONS:
            raise GovernanceViolationException(
                f"Action '{norm_action}' is strictly forbidden for AI agent role '{actor_role}'."
            )

        # 2. Check Irreversible Actions
        if action_category == ActionCategory.IRREVERSIBLE_ACTION:
            if actor_role != ActorRole.HUMAN_OWNER:
                raise GovernanceViolationException(
                    f"Irreversible actions require Human Owner authorization. Role '{actor_role}' denied."
                )
            if not owner_signature or not dual_key_signature:
                raise GovernanceViolationException(
                    "Irreversible enterprise actions require dual-key human owner cryptographic signatures."
                )

        # 3. Check Financial Mutation Thresholds
        if action_category == ActionCategory.FINANCIAL_MUTATION:
            if actor_role == ActorRole.SPECIALIST and amount_inr > self.SPECIALIST_MAX_SPEND_INR:
                raise GovernanceViolationException(
                    f"Specialist spend limit of ₹{self.SPECIALIST_MAX_SPEND_INR:,.2f} exceeded (requested: ₹{amount_inr:,.2f})."
                )
            if actor_role == ActorRole.DEPT_HEAD and amount_inr > self.DEPT_HEAD_MAX_SPEND_INR:
                raise GovernanceViolationException(
                    f"Department Head spend limit of ₹{self.DEPT_HEAD_MAX_SPEND_INR:,.2f} exceeded (requested: ₹{amount_inr:,.2f})."
                )
            if actor_role == ActorRole.AI_CEO and amount_inr > self.AI_CEO_MAX_SPEND_INR:
                if not owner_signature:
                    return {
                        "authorized": False,
                        "requires_owner_approval": True,
                        "reason": f"AI CEO financial threshold ₹{self.AI_CEO_MAX_SPEND_INR:,.2f} exceeded (requested: ₹{amount_inr:,.2f}). Escalate to Owner approval queue."
                    }

        # 4. Check Operational Mutation Thresholds
        if action_category == ActionCategory.OPERATIONAL_MUTATION:
            if actor_role == ActorRole.AI_CEO and amount_inr > self.AI_CEO_MAX_SPEND_INR:
                if not owner_signature:
                    return {
                        "authorized": False,
                        "requires_owner_approval": True,
                        "reason": f"AI CEO operational spend ₹{self.AI_CEO_MAX_SPEND_INR:,.2f} exceeded. Escalate to Owner."
                    }

        return {
            "authorized": True,
            "actor_role": actor_role,
            "action_name": action_name,
            "action_category": action_category,
            "requires_owner_approval": False
        }
