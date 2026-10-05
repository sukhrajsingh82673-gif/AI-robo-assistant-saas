"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Structured Executive Decision & Intent Classification Engine

Implements Section 8, Section 9, Section 19, Section 31 of the Gemma 4 Master Specification:
- 18 Owner Intent Classifications with Ambiguity & Risk Detection
- Structured ExecutiveDecision Schema (Machine-consumable interface)
- Strict Epistemic Classification (FACT, OBSERVATION, INFERENCE, RECOMMENDATION, PREDICTION, ASSUMPTION, UNKNOWN)
- Auditable DecisionRecord binding to cryptographic SHA-256 evidence digests
"""

import time
import json
import uuid
import hashlib
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

class OwnerIntentType:
    INFORMATION_REQUEST = "INFORMATION_REQUEST"
    ANALYSIS_REQUEST = "ANALYSIS_REQUEST"
    RECOMMENDATION = "RECOMMENDATION"
    PLAN_REQUEST = "PLAN_REQUEST"
    MISSION_REQUEST = "MISSION_REQUEST"
    TASK_REQUEST = "TASK_REQUEST"
    DELEGATION = "DELEGATION"
    APPROVAL = "APPROVAL"
    EXECUTION = "EXECUTION"
    MODIFICATION = "MODIFICATION"
    CANCELLATION = "CANCELLATION"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    STATUS_REQUEST = "STATUS_REQUEST"
    REPORT_REQUEST = "REPORT_REQUEST"
    AUDIT_REQUEST = "AUDIT_REQUEST"
    CONFIGURATION_REQUEST = "CONFIGURATION_REQUEST"
    SELF_IMPROVEMENT_REQUEST = "SELF_IMPROVEMENT_REQUEST"
    UNKNOWN = "UNKNOWN"

ALL_INTENTS = [
    OwnerIntentType.INFORMATION_REQUEST,
    OwnerIntentType.ANALYSIS_REQUEST,
    OwnerIntentType.RECOMMENDATION,
    OwnerIntentType.PLAN_REQUEST,
    OwnerIntentType.MISSION_REQUEST,
    OwnerIntentType.TASK_REQUEST,
    OwnerIntentType.DELEGATION,
    OwnerIntentType.APPROVAL,
    OwnerIntentType.EXECUTION,
    OwnerIntentType.MODIFICATION,
    OwnerIntentType.CANCELLATION,
    OwnerIntentType.EMERGENCY_STOP,
    OwnerIntentType.STATUS_REQUEST,
    OwnerIntentType.REPORT_REQUEST,
    OwnerIntentType.AUDIT_REQUEST,
    OwnerIntentType.CONFIGURATION_REQUEST,
    OwnerIntentType.SELF_IMPROVEMENT_REQUEST,
    OwnerIntentType.UNKNOWN
]

@dataclass
class IntentClassificationResult:
    intent: str
    confidence: float
    is_ambiguous: bool
    is_high_risk: bool
    clarification_question: Optional[str] = None
    target_entities: List[str] = field(default_factory=list)

@dataclass
class EpistemicStatement:
    statement: str
    category: str  # FACT, OBSERVATION, INFERENCE, RECOMMENDATION, PREDICTION, ASSUMPTION, UNKNOWN
    evidence_ref: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StructuredExecutiveDecision:
    """
    Authoritative machine-consumable decision proposed by Gemma 4,
    evaluated and governed by ZONATA Sovereign Authority.
    """
    decision_id: str
    intent: str
    objective: str
    interpretation: str
    confidence: float
    assumptions: List[str]
    missing_information: List[str]
    proposed_actions: List[Dict[str, Any]]
    affected_departments: List[str]
    affected_agents: List[str]
    required_tools: List[str]
    risk_level: str                         # LOW, MEDIUM, HIGH, CRITICAL
    estimated_cost_inr: float
    approval_required: bool
    authorization_scope: str                # AUTOMATIC_IDEMPOTENT, BOUNDED_DELEGATE, OWNER_SOVEREIGN
    expected_outcome: str
    verification_plan: str
    rollback_plan: str
    reporting_plan: str
    epistemic_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DecisionRecord:
    """
    Persistent auditable record of an executive decision binding to evidence.
    """
    decision_id: str
    mission_id: Optional[str]
    timestamp: float
    model: str
    model_version: str
    input_reference: str
    context_reference: str
    decision: Dict[str, Any]
    reasoning_summary: str
    confidence: float
    assumptions: List[str]
    policy_result: str                     # PASS, FAIL, REQUIRES_MODERATION
    authorization_result: str              # AUTHORIZED, PENDING_OWNER, DENIED
    actions: List[Dict[str, Any]]
    outcome: Optional[Dict[str, Any]]
    evidence_hashes: List[str]
    review_status: str                     # PENDING, APPROVED, VERIFIED, ESCALATED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutiveIntentClassifier:
    """
    Deterministic & cognitive classification of owner directives.
    Guarantees that ambiguous or high-risk requests are paused for clarification.
    """

    @classmethod
    def classify(cls, instruction: str) -> IntentClassificationResult:
        inst_lower = instruction.lower().strip()

        # 1. Emergency Stop (Highest Priority)
        if any(w in inst_lower for w in ["emergency stop", "kill switch", "abort all", "freeze all", "halt all"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.EMERGENCY_STOP,
                confidence=1.0,
                is_ambiguous=False,
                is_high_risk=True
            )

        # 2. Cancellation
        if any(w in inst_lower for w in ["cancel mission", "stop campaign", "stop the campaign", "terminate task", "pause mission"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.CANCELLATION,
                confidence=0.98,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 3. Audit / Evidence
        if any(w in inst_lower for w in ["show me the evidence", "show evidence", "audit log", "proof", "merkle", "sha256"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.AUDIT_REQUEST,
                confidence=0.99,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 4. Report
        if any(w in inst_lower for w in ["give me today's ceo report", "ceo report", "executive report", "daily brief", "weekly review"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.REPORT_REQUEST,
                confidence=0.99,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 5. Status / Information
        if any(w in inst_lower for w in ["how are sales", "how is the company", "performance", "check all open missions", "status of"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.STATUS_REQUEST,
                confidence=0.97,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 6. Analysis / Problem Finding
        if any(w in inst_lower for w in ["why did", "what is blocking", "bottleneck", "find the highest-priority problem", "root cause"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.ANALYSIS_REQUEST,
                confidence=0.96,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 7. Delegation
        if any(w in inst_lower for w in ["delegate this to", "assign to", "have marketing", "have operations"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.DELEGATION,
                confidence=0.95,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 8. Plan Request
        if any(w in inst_lower for w in ["create a plan", "formulate plan", "strategy to", "plan to reduce"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.PLAN_REQUEST,
                confidence=0.96,
                is_ambiguous=False,
                is_high_risk=False
            )

        # 9. Financial Commitments / Budget Allocation
        if any(w in inst_lower for w in ["commit", "spend", "budget", "allocate", "invest", "media blitz", "contract"]):
            extracted_nums = [int(n) for n in re.findall(r"\b(\d+)\b", inst_lower)]
            is_high = any(n >= 50000 for n in extracted_nums)
            return IntentClassificationResult(
                intent=OwnerIntentType.MISSION_REQUEST,
                confidence=0.96,
                is_ambiguous=False,
                is_high_risk=is_high
            )

        # 10. Mission / Execution
        if any(w in inst_lower for w in ["increase", "boost", "start a campaign", "launch", "execute", "run "]):
            # Check for ambiguity in parameters
            is_ambiguous = len(inst_lower.split()) < 3
            return IntentClassificationResult(
                intent=OwnerIntentType.MISSION_REQUEST,
                confidence=0.95,
                is_ambiguous=is_ambiguous,
                is_high_risk=False,
                clarification_question="Could you specify the target metric, company, or timeframe for this mission?" if is_ambiguous else None
            )

        # 10. Self Improvement
        if any(w in inst_lower for w in ["learn from", "self improve", "update memory", "adapt workflow"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.SELF_IMPROVEMENT_REQUEST,
                confidence=0.92,
                is_ambiguous=False,
                is_high_risk=False
            )

        # Ambiguous / Short Input Check
        if len(inst_lower.split()) <= 2 and not any(w in inst_lower for w in ["help", "hi", "hello", "status"]):
            return IntentClassificationResult(
                intent=OwnerIntentType.UNKNOWN,
                confidence=0.50,
                is_ambiguous=True,
                is_high_risk=False,
                clarification_question=f"Could you clarify your objective regarding '{instruction}'? You can ask for status, reports, or assign missions."
            )

        return IntentClassificationResult(
            intent=OwnerIntentType.INFORMATION_REQUEST,
            confidence=0.85,
            is_ambiguous=False,
            is_high_risk=False
        )


class StructuredDecisionEngine:
    """
    Synthesizes and validates machine-consumable ExecutiveDecisions.
    Enforces the invariant:
    Gemma 4 proposes -> ZONATA Authority authorizes -> Coworkers execute -> Truth Engine verifies.
    """

    @classmethod
    def synthesize_decision(
        cls,
        intent_res: IntentClassificationResult,
        instruction: str,
        company_id: str,
        tenant_id: str,
        company_name: str = "Royal Hotel Jaipur",
        model_id: str = "gemma-4-31b-it",
        spending_limit_inr: float = 50000.0
    ) -> StructuredExecutiveDecision:
        decision_id = f"dec_gemma_{uuid.uuid4().hex[:8]}"

        # Parse affected departments based on instruction
        inst_lower = instruction.lower()
        depts = []
        if any(k in inst_lower for k in ["booking", "hotel", "room", "guest", "revpar", "yield"]):
            depts.extend(["Revenue Management", "Hospitality Operations"])
        if any(k in inst_lower for k in ["marketing", "campaign", "ad", "sales", "lead"]):
            depts.append("Marketing")
        if any(k in inst_lower for k in ["cost", "budget", "finance", "audit", "invoice", "leakage"]):
            depts.append("Finance")
        if not depts:
            depts = ["Operations", "Strategy"]

        # Financial estimate
        extracted_nums = [float(n) for n in re.findall(r"\b(\d+)\b", instruction)]
        parsed_amount = max([n for n in extracted_nums if n > 100], default=0.0)
        if parsed_amount > 0:
            cost_est = parsed_amount
        else:
            cost_est = 15000.0 if intent_res.intent in (OwnerIntentType.MISSION_REQUEST, OwnerIntentType.PLAN_REQUEST) else 0.0

        needs_approval = cost_est > spending_limit_inr or intent_res.is_high_risk

        actions = []
        if intent_res.intent == OwnerIntentType.EMERGENCY_STOP:
            actions.append({
                "action": "PAUSE_ALL_ACTIVE_MISSIONS",
                "scope": "GLOBAL_COMPANY",
                "authority": "EMERGENCY_CONTAINMENT"
            })
        elif intent_res.intent in (OwnerIntentType.MISSION_REQUEST, OwnerIntentType.PLAN_REQUEST):
            for d in depts:
                actions.append({
                    "action": "DISPATCH_GOVERNED_MISSION",
                    "department": d,
                    "target": instruction[:60],
                    "budget": cost_est / len(depts)
                })
        else:
            actions.append({
                "action": "GENERATE_EXECUTIVE_INTELLIGENCE",
                "scope": "ANALYTIC",
                "authority": "READ_ONLY"
            })

        epistemic = [
            EpistemicStatement(
                statement=f"Owner explicit directive received: '{instruction}'",
                category="FACT",
                confidence=1.0
            ).to_dict(),
            EpistemicStatement(
                statement=f"Departmental assignment to {', '.join(depts)}",
                category="INFERENCE",
                confidence=0.95
            ).to_dict(),
            EpistemicStatement(
                statement=f"Expected business value delivery with verifiable KPI movement",
                category="RECOMMENDATION",
                confidence=0.92
            ).to_dict()
        ]

        return StructuredExecutiveDecision(
            decision_id=decision_id,
            intent=intent_res.intent,
            objective=instruction,
            interpretation=f"Cognitive executive interpretation by {model_id}: Fulfill objective '{instruction}' through coordinated departmental action.",
            confidence=intent_res.confidence,
            assumptions=["Operating conditions remain stable", "Resource quotas sufficient"],
            missing_information=[] if not intent_res.is_ambiguous else ["Exact parameters need clarification"],
            proposed_actions=actions,
            affected_departments=depts,
            affected_agents=[f"{d.lower().replace(' ', '_')}_chief" for d in depts],
            required_tools=[f"{d.lower().replace(' ', '_')}_operator" for d in depts],
            risk_level="HIGH" if intent_res.is_high_risk else ("MEDIUM" if cost_est > 0 else "LOW"),
            estimated_cost_inr=cost_est,
            approval_required=needs_approval,
            authorization_scope="OWNER_SOVEREIGN" if needs_approval else "BOUNDED_DELEGATE",
            expected_outcome=f"Attain target outcome for '{instruction}' verified by Merkle evidence.",
            verification_plan="Continuous KPI tracking against baseline via Physical Truth Engine.",
            rollback_plan="Revert mission parameters to pre-dispatch checkpoint upon unhandled exception.",
            reporting_plan="Publish milestone update to Daily Executive Brief.",
            epistemic_breakdown=epistemic
        )
