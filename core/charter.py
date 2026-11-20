"""ZONATA Sovereign Core — Enterprise Charter & Values Engine.

Implements Sections 1, 4 (Laws L2, L3, L5), and 6 of the ZONATA Master Architecture:
- Machine-readable Charter per company: mission, values, red lines, brand voice, spending caps.
- Evaluated as deterministic gate input before any model call or tool execution.
- Red lines are absolute prohibitions: violation causes immediate hard block, never warning.
- Records all Charter rules evaluated in every decision.
"""

from __future__ import annotations
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("zonata.core.charter")


@dataclass
class RedLine:
    id: str
    rule: str
    pattern_regex: Optional[str] = None
    action_targets: List[str] = field(default_factory=list)
    description: str = ""
    severity: str = "CRITICAL"


@dataclass
class SpendingLimit:
    role: str
    max_per_transaction_usd: float
    max_daily_usd: float
    requires_dual_approval_above_usd: float


@dataclass
class CharterVerdict:
    allowed: bool
    status_code: str  # PASSED, REDLINE_VIOLATED, SPENDING_LIMIT_EXCEEDED, BRAND_VOICE_VIOLATED
    violated_rules: List[str] = field(default_factory=list)
    evaluated_rules: List[str] = field(default_factory=list)
    reason: str = "Charter checks passed"
    accountable_owner_id: Optional[str] = None


@dataclass
class CompanyCharter:
    tenant_id: str
    company_id: str
    version: str = "1.0.0"
    mission: str = "Autonomous sovereign enterprise excellence."
    values: List[str] = field(default_factory=lambda: [
        "Integrity and Truthfulness",
        "Customer Data Confidentiality",
        "Deterministic Safety and Accountability",
        "Zero Fabrication of Measurements"
    ])
    red_lines: List[RedLine] = field(default_factory=list)
    brand_voice: Dict[str, Any] = field(default_factory=lambda: {
        "prohibited_phrases": [
            "guaranteed 100% returns",
            "risk-free investment",
            "cure all diseases",
            "unlimited confidential access"
        ],
        "mandatory_disclaimers": [],
        "tone": "professional, transparent, objective"
    })
    spending_limits: Dict[str, SpendingLimit] = field(default_factory=dict)
    accountable_owners: Dict[str, str] = field(default_factory=dict)  # role/process -> principal_id
    risk_appetite: str = "CONSERVATIVE"  # CONSERVATIVE, BALANCED, AGGRESSIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @classmethod
    def default_for_company(cls, tenant_id: str, company_id: str, owner_id: str) -> "CompanyCharter":
        """Generate a robust, default enterprise Charter with standard safety red lines."""
        standard_red_lines = [
            RedLine(
                id="RL-01",
                rule="no_unauthorized_exfiltration",
                pattern_regex=r"(?i)(send|upload|exfiltrate|post)\s+.*?(password|credential|secret|token|confidential|customer).*?\s+to",
                description="Absolute ban on exfiltrating credentials or bulk customer data outside tenant boundary."
            ),
            RedLine(
                id="RL-02",
                rule="no_self_approved_spending",
                description="No employee or agent may approve their own purchase order or expenditure.",
                action_targets=["finance.payout", "finance.spend", "procurement.order"]
            ),
            RedLine(
                id="RL-03",
                rule="no_unverified_marketing_claims",
                pattern_regex=r"(?i)(guaranteed|100%|risk-free|miracle|flawless)\s+(profit|success|result)",
                description="Prohibits deceptive or unsubstantiated marketing statements."
            ),
            RedLine(
                id="RL-04",
                rule="no_discriminatory_screening",
                pattern_regex=r"(?i)(filter|screen|reject)\s+by\s+(race|gender|religion|caste|ethnicity|sexual\s+orientation)",
                description="Fairness law: zero discrimination in hiring, credit, or evaluation processes."
            ),
            RedLine(
                id="RL-05",
                rule="no_unauthorized_destruction",
                action_targets=["storage.delete_all", "db.drop_database", "tenant.purge"],
                description="Prohibits bulk destructive actions without dual executive control."
            )
        ]

        standard_limits = {
            "ai_employee": SpendingLimit(role="ai_employee", max_per_transaction_usd=100.0, max_daily_usd=500.0, requires_dual_approval_above_usd=50.0),
            "department_head": SpendingLimit(role="department_head", max_per_transaction_usd=1000.0, max_daily_usd=5000.0, requires_dual_approval_above_usd=500.0),
            "ai_ceo": SpendingLimit(role="ai_ceo", max_per_transaction_usd=10000.0, max_daily_usd=50000.0, requires_dual_approval_above_usd=5000.0),
            "human_owner": SpendingLimit(role="human_owner", max_per_transaction_usd=1000000.0, max_daily_usd=5000000.0, requires_dual_approval_above_usd=100000.0),
        }

        owners = {
            "company": owner_id,
            "finance": owner_id,
            "security": owner_id,
            "legal": owner_id,
            "operations": owner_id,
            "general": owner_id
        }

        return cls(
            tenant_id=tenant_id,
            company_id=company_id,
            red_lines=standard_red_lines,
            spending_limits=standard_limits,
            accountable_owners=owners
        )

    def evaluate_request(
        self,
        request_text: str,
        action_name: str = "",
        role: str = "ai_employee",
        amount_usd: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> CharterVerdict:
        """Deterministic evaluation of an action/request against the Charter."""
        context = context or {}
        evaluated = []
        violated = []

        # 1. Evaluate Red Lines
        for rl in self.red_lines:
            evaluated.append(rl.rule)
            # Action target match
            if rl.action_targets and action_name:
                for target in rl.action_targets:
                    if target == action_name or action_name.startswith(target):
                        if rl.rule == "no_self_approved_spending":
                            requester = context.get("requester_id")
                            approver = context.get("approver_id")
                            if context.get("is_self_approval") or (requester and approver and requester == approver):
                                violated.append(f"RedLine violated: {rl.rule} ({rl.description})")
                                break
                        else:
                            violated.append(f"RedLine violated: {rl.rule} ({rl.description})")
                            break

            # Regex pattern match
            if rl.pattern_regex and request_text:
                if re.search(rl.pattern_regex, request_text):
                    violated.append(f"RedLine violated: {rl.rule} ({rl.description})")

        if violated:
            return CharterVerdict(
                allowed=False,
                status_code="REDLINE_VIOLATED",
                violated_rules=violated,
                evaluated_rules=evaluated,
                reason="; ".join(violated),
                accountable_owner_id=self.accountable_owners.get("security", self.accountable_owners.get("company"))
            )

        # 2. Evaluate Brand Voice for outward-facing communications
        is_outward = context.get("is_outward_communication", False)
        if is_outward and request_text:
            prohibited = self.brand_voice.get("prohibited_phrases", [])
            for phrase in prohibited:
                evaluated.append(f"brand_voice_check:{phrase}")
                if phrase.lower() in request_text.lower():
                    violated.append(f"Brand voice violation: prohibited phrase '{phrase}' detected")

            if violated:
                return CharterVerdict(
                    allowed=False,
                    status_code="BRAND_VOICE_VIOLATED",
                    violated_rules=violated,
                    evaluated_rules=evaluated,
                    reason="; ".join(violated),
                    accountable_owner_id=self.accountable_owners.get("marketing", self.accountable_owners.get("company"))
                )

        # 3. Evaluate Spending Limits
        if amount_usd is not None and amount_usd > 0:
            limit = self.spending_limits.get(role)
            evaluated.append(f"spending_limit_check:{role}")
            if limit:
                if amount_usd > limit.max_per_transaction_usd:
                    violated.append(
                        f"Spending limit exceeded: transaction ${amount_usd:.2f} > max limit ${limit.max_per_transaction_usd:.2f} for role '{role}'"
                    )
            else:
                # Unregistered role spending money is denied by default
                violated.append(f"No spending authority assigned to role '{role}'")

            if violated:
                return CharterVerdict(
                    allowed=False,
                    status_code="SPENDING_LIMIT_EXCEEDED",
                    violated_rules=violated,
                    evaluated_rules=evaluated,
                    reason="; ".join(violated),
                    accountable_owner_id=self.accountable_owners.get("finance", self.accountable_owners.get("company"))
                )

        return CharterVerdict(
            allowed=True,
            status_code="PASSED",
            violated_rules=[],
            evaluated_rules=evaluated,
            reason="All Charter red lines, brand rules, and budget limits passed",
            accountable_owner_id=self.accountable_owners.get("company")
        )
