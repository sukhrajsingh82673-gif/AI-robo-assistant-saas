"""
ZONATA / URA UNIVERSAL AIC CEO SOP ENGINE
Outcome-Oriented SOP Execution, 16-Stage Master Operating Loop,
Event-Driven Executive Cadence, Crisis Governance (Levels 0-4),
Assumption Register, and Opportunity/Threat Valuation Engines.

Standards Alignment:
  - ISO 37000: Operational Oversight & Long-Term Viability
  - ISO 31000: Crisis Management & Risk Treatment
  - ISO 9001: Quality & Continual Process Improvement
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.aic_ceo_constitution import AuthorityLevel, DecisionClass, CrisisLevel

logger = logging.getLogger("zonata.aic_ceo.sop")

# ==============================================================================
# 1. OUTCOME-ORIENTED SOP SPECIFICATION
# ==============================================================================

@dataclass
class OutcomeOrientedSOP:
    sop_id: str
    sop_name: str
    domain: str                         # FINANCIAL, COMMERCIAL, OPERATIONAL, CRISIS, M_AND_A, TECH
    objective: str
    trigger_condition: str
    decision_logic: List[str]
    required_evidence: List[str]
    minimum_authority_level: AuthorityLevel
    execution_options: List[str]
    verification_method: str
    escalation_rule: str
    completion_criteria: str
    is_deviated_allowed: bool = True    # Outcome-oriented flexibility within authority bounds

# ==============================================================================
# 2. 16-STAGE MASTER OPERATING LOOP
# ==============================================================================

class OperatingLoopStage(str, Enum):
    OBSERVE = "OBSERVE"
    UNDERSTAND = "UNDERSTAND"
    DEFINE_OBJECTIVE = "DEFINE_OBJECTIVE"
    ESTABLISH_BASELINE = "ESTABLISH_BASELINE"
    IDENTIFY_CONSTRAINTS = "IDENTIFY_CONSTRAINTS"
    IDENTIFY_GAPS = "IDENTIFY_GAPS"
    RESEARCH = "RESEARCH"
    GENERATE_OPTIONS = "GENERATE_OPTIONS"
    MODEL_ECONOMICS = "MODEL_ECONOMICS"
    ASSESS_RISK = "ASSESS_RISK"
    SELECT = "SELECT"
    AUTHORIZE = "AUTHORIZE"
    DELEGATE = "DELEGATE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    LEARN = "LEARN"

@dataclass
class ExecutiveMissionPlan:
    mission_id: str
    tenant_id: str
    company_id: str
    owner_objective: str
    current_stage: OperatingLoopStage
    baseline_metrics: Dict[str, float]
    target_outcomes: Dict[str, float]
    constraints_identified: List[str]
    resources_allocated_usd: float
    selected_strategy: str
    assigned_agents: List[str]
    required_authority: AuthorityLevel
    evidence_collected: List[Dict[str, Any]]
    execution_complete: bool = False
    outcome_verified: bool = False
    success_criteria_met: bool = False
    is_successful: bool = False
    financial_delta_usd: float = 0.0
    lessons_learned: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

# ==============================================================================
# 3. EVENT-DRIVEN EXECUTIVE CADENCE & CANONICAL SOPS
# ==============================================================================

CANONICAL_EXECUTIVE_SOPS: List[OutcomeOrientedSOP] = [
    OutcomeOrientedSOP(
        sop_id="SOP-FIN-01",
        sop_name="Liquidity & Cash Runway Protection",
        domain="FINANCIAL",
        objective="Preserve minimum 90-day liquid cash runway and prevent debt default.",
        trigger_condition="Cash runway falls below 120 days or unhedged cash burn increases >20%.",
        decision_logic=[
            "1. Audit all committed cash outflows for next 90 days.",
            "2. Freeze all non-essential discretionary capital projects.",
            "3. Enforce immediate invoice collections and shorten DSO.",
            "4. Model scenario runway under 0% revenue shock."
        ],
        required_evidence=["Verified Bank API Ledger", "A/R Aging Schedule", "Committed A/P Run"],
        minimum_authority_level=AuthorityLevel.AIC_CEO,
        execution_options=["Delay discretionary AP", "Enforce discount-for-cash collection", "Draw approved revolver"],
        verification_method="Bank balance verification with cryptographic statement hash.",
        escalation_rule="If runway < 90 days, escalate immediately to Sovereign Owner as Level 2 Disruption.",
        completion_criteria="Cash runway stabilized at >120 days with audited bank reconciliation."
    ),
    OutcomeOrientedSOP(
        sop_id="SOP-COM-01",
        sop_name="High-Velocity Revenue Expansion",
        domain="COMMERCIAL",
        objective="Capture qualified customer demand with positive contribution margin.",
        trigger_condition="Monthly qualified pipeline falls below 3x quota or CAC payback exceeds 18 months.",
        decision_logic=[
            "1. Audit conversion rate at each funnel stage (Lead -> SQO -> Contract).",
            "2. Identify drop-off bottlenecks and ICP misalignment.",
            "3. Enforce margin floor (prohibit discounts exceeding DoA limit).",
            "4. Redeploy SDR and marketing agents toward highest-LTV customer cohorts."
        ],
        required_evidence=["CRM Pipeline Telemetry", "Stripe Cohort Margins", "Customer Contract Ledger"],
        minimum_authority_level=AuthorityLevel.EXECUTIVE_FUNCTION,
        execution_options=["Recalibrate ad spend", "Introduce tier packaging", "Incentivize annual prepayments"],
        verification_method="Gross cash collections reconciled against recognized GAAP revenue.",
        escalation_rule="Escalate to CEO if discounting requests >15% or CAC rises >30%.",
        completion_criteria="Net pipeline reaches 3.5x coverage with verified positive contribution margin."
    ),
    OutcomeOrientedSOP(
        sop_id="SOP-CRI-01",
        sop_name="Crisis Response & Enterprise Containment",
        domain="CRISIS",
        objective="Protect human life, secure assets and data, halt financial hemorrhaging, and restore continuity.",
        trigger_condition="Level 3 or Level 4 incident triggered (cyberattack, physical hazard, severe regulatory indictment).",
        decision_logic=[
            "1. DETECT and CLASSIFY crisis severity (Level 0 through 4).",
            "2. CONTAIN immediately; isolate compromised hosts, revoke privileged tokens, halt automated trading.",
            "3. PROTECT PEOPLE, ASSETS, and DATA.",
            "4. ESTABLISH FACTS vs UNKNOWNS using strict epistemic standards.",
            "5. Execute verified emergency runbook; communicate truthfully without false reassurance."
        ],
        required_evidence=["Incident Audit Ledger", "Host Isolation Logs", "Regulatory Notification Timestamp"],
        minimum_authority_level=AuthorityLevel.AIC_CEO,
        execution_options=["Emergency Killswitch Activation", "Disaster Recovery Failover", "Host Quarantine"],
        verification_method="Independent security telemetry verification and data integrity attestation.",
        escalation_rule="Immediate Sovereign Owner and Board notification within 15 minutes of Level 3/4 classification.",
        completion_criteria="Threat neutralized, root cause documented, systems recovered, post-mortem complete."
    ),
    OutcomeOrientedSOP(
        sop_id="SOP-TECH-01",
        sop_name="Governed AI & Technology Investment",
        domain="TECH",
        objective="Deploy scalable technology and AI capabilities with audited economic ROI.",
        trigger_condition="Proposed tech/AI investment exceeding $10,000 USD or modifying foundational model routing.",
        decision_logic=[
            "1. Evaluate use-case economic value (Cost per Verified Outcome).",
            "2. Conduct Build vs Buy vs License analysis.",
            "3. Audit cybersecurity, data privacy, and prompt injection exposure.",
            "4. Establish deterministic fallback and model replacement procedure."
        ],
        required_evidence=["Security Review Memo", "Vendor Dependency Matrix", "Payback ROI Financial Model"],
        minimum_authority_level=AuthorityLevel.AIC_CEO,
        execution_options=["Phased Canary Pilot", "Vendor API Contract", "Internal Open-Source Deployment"],
        verification_method="Post-deployment audit measuring cost-per-outcome and latency compliance.",
        escalation_rule="Escalate to Sovereign Owner if annual commitment exceeds $50,000 USD.",
        completion_criteria="Operational deployment active with verified positive ROI and deterministic fallback tested."
    )
]

# ==============================================================================
# 4. ASSUMPTION REGISTER
# ==============================================================================

@dataclass
class AssumptionRecord:
    assumption_id: str
    statement: str
    source: str
    confidence: float                   # 0.0 - 1.0
    financial_impact_usd: float
    risk_if_wrong: str
    validation_method: str
    status: str                         # PENDING_VALIDATION, VALIDATED, INVALIDATED
    created_at: float = field(default_factory=time.time)
    validated_at: Optional[float] = None

class AssumptionRegister:
    """
    Maintains and validates high-impact operational and strategic assumptions.
    Prioritizes testing high-impact assumptions before allocating scarce capital.
    """
    def __init__(self):
        self._assumptions: Dict[str, AssumptionRecord] = {}

    def register_assumption(
        self,
        statement: str,
        source: str,
        confidence: float,
        impact_usd: float,
        risk_desc: str,
        validation_method: str
    ) -> AssumptionRecord:
        record = AssumptionRecord(
            assumption_id=f"asm_{uuid.uuid4().hex[:10]}",
            statement=statement,
            source=source,
            confidence=confidence,
            financial_impact_usd=impact_usd,
            risk_if_wrong=risk_desc,
            validation_method=validation_method,
            status="PENDING_VALIDATION"
        )
        self._assumptions[record.assumption_id] = record
        return record

    def validate_assumption(self, assumption_id: str, is_valid: bool) -> Optional[AssumptionRecord]:
        rec = self._assumptions.get(assumption_id)
        if not rec:
            return None
        rec.status = "VALIDATED" if is_valid else "INVALIDATED"
        rec.validated_at = time.time()
        return rec

    def get_unvalidated_high_impact(self, threshold_usd: float = 25000.0) -> List[AssumptionRecord]:
        return [
            a for a in self._assumptions.values()
            if a.status == "PENDING_VALIDATION" and a.financial_impact_usd >= threshold_usd
        ]

# ==============================================================================
# 5. OPPORTUNITY & THREAT ENGINES
# ==============================================================================

@dataclass
class EnterpriseOpportunity:
    opportunity_id: str
    title: str
    category: str                       # REVENUE, COST, AUTOMATION, MARKET, ACQUISITION
    expected_value_usd: float
    probability: float                  # 0.0 - 1.0
    required_investment_usd: float
    estimated_timeframe_days: int
    risk_level: str
    strategic_fit_score: float          # 0 - 10
    reversibility: str
    composite_rank_score: float = 0.0

    def compute_rank(self) -> float:
        # Expected Net Value = (Expected Value * Probability) - Required Investment
        net_ev = (self.expected_value_usd * self.probability) - self.required_investment_usd
        fit_multiplier = self.strategic_fit_score / 10.0
        time_discount = max(1.0 - (self.estimated_timeframe_days / 365.0) * 0.2, 0.5)
        self.composite_rank_score = round(max(net_ev, 0.0) * fit_multiplier * time_discount, 2)
        return self.composite_rank_score

@dataclass
class EnterpriseThreat:
    threat_id: str
    title: str
    category: str                       # COMPETITOR, CHURN, REGULATORY, CYBER, LIQUIDITY, VENDOR
    probability: float                  # 0.0 - 1.0
    potential_loss_usd: float
    mitigation_plan: str
    assigned_owner: str
    monitoring_metric: str
    annualized_loss_expectancy: float = 0.0

    def compute_ale(self) -> float:
        self.annualized_loss_expectancy = round(self.probability * self.potential_loss_usd, 2)
        return self.annualized_loss_expectancy
