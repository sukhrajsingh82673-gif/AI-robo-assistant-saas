"""
ZONATA Universal AI CEO Company Operating System — Data Models & Epistemic Types
Constitutional data models for company discovery, provenance-backed knowledge graphs,
multidimensional evidence-based health evaluation, and generative organization blueprints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import time
import uuid

# --- 1. Epistemic Provenance States ---

class EpistemicState(str, Enum):
    """
    Constitutional classification of information truth state.
    Strict Invariant: Never silently convert an estimate or unverified statement into a fact.
    """
    FACT = "FACT"                  # Authoritatively verified ground truth (e.g. from validated system records)
    OBSERVATION = "OBSERVATION"    # Directly observed by runtime agent, sensor, or scraper
    CALCULATION = "CALCULATION"    # Mathematically computed from verified inputs
    ESTIMATE = "ESTIMATE"          # Approximation given by human or heuristic (NOT fact)
    PREDICTION = "PREDICTION"      # Future forecast or probability distribution
    SIMULATION = "SIMULATION"      # Sandbox or scenario modeling result
    UNVERIFIED = "UNVERIFIED"      # Stated by external source without independent confirmation
    VERIFIED = "VERIFIED"          # Corroborated by dual-source proof or cryptographic ledger

# --- 2. Entity and Relationship Types (Master Spec: 30+ Core Entity Types) ---

class EntityType(str, Enum):
    COMPANY = "Company"
    SUBSIDIARY = "Subsidiary"
    LOCATION = "Location"
    DEPARTMENT = "Department"
    PERSON = "Person"
    AI_WORKFORCE_MEMBER = "AIWorkforceMember"
    PROCESS = "Process"
    PRODUCT = "Product"
    SERVICE = "Service"
    CUSTOMER = "Customer"
    SUPPLIER = "Supplier"
    COMPETITOR = "Competitor"
    SYSTEM = "System"
    APPLICATION = "Application"
    INTEGRATION = "Integration"
    ACCOUNT = "Account"
    ASSET = "Asset"
    MACHINE = "Machine"
    FINANCIAL_ACCOUNT = "FinancialAccount"
    REVENUE_STREAM = "RevenueStream"
    EXPENSE = "Expense"
    CONTRACT = "Contract"
    DOCUMENT = "Document"
    SOP = "SOP"
    KPI = "KPI"
    MISSION = "Mission"
    RISK = "Risk"
    POLICY = "Policy"
    GOAL = "Goal"

class RelationType(str, Enum):
    OWNS = "owns"
    USES = "uses"
    OPERATES = "operates"
    EMPLOYS = "employs"
    GENERATES = "generates"
    COMPETES_WITH = "competes_with"
    RESPONSIBLE_FOR = "responsible_for"
    PRODUCES = "produces"
    DEPENDS_ON = "depends_on"
    INTEGRATES_WITH = "integrates_with"
    MITIGATES = "mitigates"
    MONITORS = "monitors"
    ESCALATES_TO = "escalates_to"

# --- 3. Provenance & Discovery ---

@dataclass
class ProvenanceRecord:
    source: str
    tenant_id: str
    company_id: str
    evidence: str
    epistemic_state: EpistemicState = EpistemicState.UNVERIFIED
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "evidence": self.evidence,
            "epistemic_state": self.epistemic_state.value if isinstance(self.epistemic_state, EpistemicState) else str(self.epistemic_state),
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }

@dataclass
class DiscoveryFinding:
    fact_id: str
    entity_type: EntityType
    entity_id: str
    attribute: str
    value: Any
    provenance: ProvenanceRecord

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else str(self.entity_type),
            "entity_id": self.entity_id,
            "attribute": self.attribute,
            "value": self.value,
            "provenance": self.provenance.to_dict()
        }

# --- 4. CEO Discovery Interview Models ---

class AnswerType(str, Enum):
    ANSWERED = "ANSWERED"
    SKIPPED = "SKIPPED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    ASK_LATER = "ASK_LATER"
    BEST_EVIDENCE = "BEST_EVIDENCE"

@dataclass
class InterviewQuestion:
    question_id: str
    category: str
    text: str
    context_reason: str
    priority: int = 1
    suggested_answers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "category": self.category,
            "text": self.text,
            "context_reason": self.context_reason,
            "priority": self.priority,
            "suggested_answers": self.suggested_answers
        }

@dataclass
class InterviewExchange:
    exchange_id: str
    session_id: str
    tenant_id: str
    company_id: str
    question: InterviewQuestion
    answer_text: Optional[str] = None
    answer_type: AnswerType = AnswerType.ANSWERED
    extracted_facts: List[DiscoveryFinding] = field(default_factory=list)
    asked_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange_id": self.exchange_id,
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "question": self.question.to_dict(),
            "answer_text": self.answer_text,
            "answer_type": self.answer_type.value,
            "extracted_facts": [f.to_dict() for f in self.extracted_facts],
            "asked_at": self.asked_at,
            "answered_at": self.answered_at
        }

@dataclass
class DiscoveryState:
    session_id: str
    tenant_id: str
    company_id: str
    completeness_score: float = 0.0  # 0.0 to 1.0 (0% to 100%)
    status: str = "IN_PROGRESS"      # IN_PROGRESS, READY_FOR_ORG, COMPLETED
    missing_information: List[Dict[str, Any]] = field(default_factory=list)
    deferred_topics: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "completeness_score": round(self.completeness_score, 4),
            "status": self.status,
            "missing_information": self.missing_information,
            "deferred_topics": self.deferred_topics,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

# --- 5. Company Health Engine Models ---

class HealthDimension(str, Enum):
    FINANCIAL = "Financial"
    OPERATIONS = "Operations"
    SALES = "Sales"
    MARKETING = "Marketing"
    CUSTOMER = "Customer"
    TECHNOLOGY = "Technology"
    HUMAN_WORKFORCE = "Human Workforce"
    PRODUCTIVITY = "Productivity"
    RISK = "Risk"
    COMPLIANCE = "Compliance"
    SECURITY = "Security"
    SUPPLY_CHAIN = "Supply Chain"
    INVENTORY = "Inventory"
    QUALITY = "Quality"
    REPUTATION = "Reputation"

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNVERIFIED = "UNVERIFIED"

@dataclass
class HealthIndicator:
    indicator_id: str
    dimension: HealthDimension
    metric_name: str
    value: Any
    source: str
    confidence: Union[EpistemicState, str] = EpistemicState.VERIFIED
    trend: str = "STABLE"
    period: str = "CURRENT"
    status: HealthStatus = HealthStatus.HEALTHY
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "dimension": self.dimension.value if isinstance(self.dimension, HealthDimension) else str(self.dimension),
            "metric_name": self.metric_name,
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence.value if isinstance(self.confidence, EpistemicState) else str(self.confidence),
            "trend": self.trend,
            "period": self.period,
            "status": self.status.value if isinstance(self.status, HealthStatus) else str(self.status),
            "evaluated_at": self.evaluated_at
        }

@dataclass
class CompanyHealthModel:
    company_id: str
    tenant_id: str
    overall_score: float # 0 to 100
    indicators: List[HealthIndicator]
    strengths: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    unverified_areas: List[str] = field(default_factory=list)
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "tenant_id": self.tenant_id,
            "overall_score": round(self.overall_score, 1),
            "indicators": [ind.to_dict() for ind in self.indicators],
            "strengths": self.strengths,
            "vulnerabilities": self.vulnerabilities,
            "unverified_areas": self.unverified_areas,
            "evaluated_at": self.evaluated_at
        }

# --- 6. Dynamic Organization Design Models ---

class AgentLifecycleState(str, Enum):
    NEED_IDENTIFIED = "NEED_IDENTIFIED"
    ROLE_DESIGNED = "ROLE_DESIGNED"
    CAPABILITIES_DEFINED = "CAPABILITIES_DEFINED"
    TOOLS_SELECTED = "TOOLS_SELECTED"
    MODEL_SELECTED = "MODEL_SELECTED"
    KNOWLEDGE_BOUND = "KNOWLEDGE_BOUND"
    POLICY_ASSIGNED = "POLICY_ASSIGNED"
    TESTED = "TESTED"
    CERTIFIED = "CERTIFIED"
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"

@dataclass
class DynamicDepartment:
    id: str
    name: str
    code: str
    justification: str
    responsibilities: List[str]
    processes: List[str] = field(default_factory=list)
    systems_used: List[str] = field(default_factory=list)
    budget_allocation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "justification": self.justification,
            "responsibilities": self.responsibilities,
            "processes": self.processes,
            "systems_used": self.systems_used,
            "budget_allocation": self.budget_allocation
        }

@dataclass
class DynamicWorkforceMember:
    id: str
    name: str
    role: str
    department_id: str
    executive: str
    mission_focus: str
    responsibilities: List[str]
    capabilities: List[str]
    tools: List[str]
    knowledge_sources: List[str]
    model_policy: Dict[str, Any]
    budget: float = 100.0
    risk_class: str = "LOW"
    approval_policy: Dict[str, Any] = field(default_factory=dict)
    kpis: List[Dict[str, Any]] = field(default_factory=list)
    verification_policy: Dict[str, Any] = field(default_factory=dict)
    working_hours: str = "24x7_CONTINUOUS"
    communication_channels: List[str] = field(default_factory=lambda: ["AGENT_BUS", "SLACK", "EMAIL"])
    status: AgentLifecycleState = AgentLifecycleState.ACTIVE
    certification: Dict[str, Any] = field(default_factory=dict)
    authority_scope: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "department_id": self.department_id,
            "executive": self.executive,
            "mission_focus": self.mission_focus,
            "responsibilities": self.responsibilities,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "knowledge_sources": self.knowledge_sources,
            "model_policy": self.model_policy,
            "budget": self.budget,
            "risk_class": self.risk_class,
            "approval_policy": self.approval_policy,
            "kpis": self.kpis,
            "verification_policy": self.verification_policy,
            "working_hours": self.working_hours,
            "communication_channels": self.communication_channels,
            "status": self.status.value if isinstance(self.status, AgentLifecycleState) else str(self.status),
            "certification": self.certification,
            "authority_scope": self.authority_scope
        }

@dataclass
class DynamicOrganization:
    blueprint_id: str
    company_id: str
    tenant_id: str
    industry: str
    rationale: str
    executives: List[Dict[str, Any]]
    departments: List[DynamicDepartment]
    workforce: List[DynamicWorkforceMember]
    reporting_hierarchy: Dict[str, str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "company_id": self.company_id,
            "tenant_id": self.tenant_id,
            "industry": self.industry,
            "rationale": self.rationale,
            "executives": self.executives,
            "departments": [d.to_dict() for d in self.departments],
            "workforce": [w.to_dict() for w in self.workforce],
            "reporting_hierarchy": self.reporting_hierarchy,
            "created_at": self.created_at
        }

# --- 7. Competitive Intelligence Models ---

@dataclass
class CompetitorProfile:
    competitor_id: str
    tenant_id: str
    company_id: str
    name: str
    website: Optional[str] = None
    products: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    public_pricing: Dict[str, Any] = field(default_factory=dict)
    positioning: Optional[str] = None
    customer_sentiment: Optional[str] = None
    source: str = "PUBLIC_WEB"
    confidence: float = 0.9
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor_id": self.competitor_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "name": self.name,
            "website": self.website,
            "products": self.products,
            "services": self.services,
            "public_pricing": self.public_pricing,
            "positioning": self.positioning,
            "customer_sentiment": self.customer_sentiment,
            "source": self.source,
            "confidence": self.confidence,
            "discovered_at": self.discovered_at
        }

# --- 8. Triad Entity Contracts & Invariants ---

class WorkforceTriadType(str, Enum):
    AI_EMPLOYEE = "AI_EMPLOYEE"      # Permanent corporate identity, holds positions, DoA, SOPs, KRAs
    AI_AGENT = "AI_AGENT"            # Ephemeral execution worker, leased via agent_leases
    AI_COWORKER = "AI_COWORKER"      # Host desktop assistant, isolated from corporate DB

@dataclass
class TriadEntityContract:
    triad_type: WorkforceTriadType
    entity_id: str
    tenant_id: str
    company_id: str
    is_autonomous_corporate: bool
    can_hold_position: bool
    can_hold_doa_authority: bool
    requires_concurrency_lease: bool
    host_desktop_isolated: bool

    @classmethod
    def create_ai_employee_contract(cls, employee_id: str, tenant_id: str, company_id: str) -> 'TriadEntityContract':
        return cls(
            triad_type=WorkforceTriadType.AI_EMPLOYEE,
            entity_id=employee_id,
            tenant_id=tenant_id,
            company_id=company_id,
            is_autonomous_corporate=True,
            can_hold_position=True,
            can_hold_doa_authority=True,
            requires_concurrency_lease=False,
            host_desktop_isolated=False
        )

    @classmethod
    def create_ai_agent_contract(cls, agent_id: str, tenant_id: str, company_id: str) -> 'TriadEntityContract':
        return cls(
            triad_type=WorkforceTriadType.AI_AGENT,
            entity_id=agent_id,
            tenant_id=tenant_id,
            company_id=company_id,
            is_autonomous_corporate=False,
            can_hold_position=False,
            can_hold_doa_authority=False,
            requires_concurrency_lease=True,
            host_desktop_isolated=False
        )

    @classmethod
    def create_ai_coworker_contract(cls, coworker_id: str, tenant_id: str, company_id: str) -> 'TriadEntityContract':
        return cls(
            triad_type=WorkforceTriadType.AI_COWORKER,
            entity_id=coworker_id,
            tenant_id=tenant_id,
            company_id=company_id,
            is_autonomous_corporate=False,
            can_hold_position=False,
            can_hold_doa_authority=False,
            requires_concurrency_lease=False,
            host_desktop_isolated=True
        )

