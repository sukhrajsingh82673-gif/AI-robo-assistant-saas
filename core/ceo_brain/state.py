"""
RoboAssistant Company OS 2.0 — CEO Live State Engine
Maintains continuous live business state across Identity, Economics,
Operations, Workforce, Strategy, Risks, Opportunities, and Epistemic Truth.
"""

from typing import Dict, Any, List, Optional
import time
from ..models import OperatingContext
from ..knowledge_graph import CompanyKnowledgeGraph, TruthState
from ..departments import DepartmentControlUnit
from ..approvals import ApprovalPipeline
from ..intelligence import RiskEngine, OpportunityEngine
from ..db import db

class CEOCompanyState:
    def __init__(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        industry: str,
        business_model: str
    ):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.name = name
        self.industry = industry
        self.business_model = business_model
        
        # Economics
        self.gross_revenue: float = 0.0
        self.operating_cost: float = 0.0
        self.contribution_margin: float = 0.0
        self.cash_position: Optional[float] = None
        self.burn_rate_monthly: float = 0.0
        self.discretionary_budget_limit: float = 1000000.0  # e.g. ₹10 Lakh
        self.discretionary_budget_spent: float = 0.0
        
        # Operations
        self.capacity_units: float = 100.0
        self.utilization_pct: float = 0.0
        self.bottlenecks: List[Dict[str, Any]] = []
        self.sla_compliance_pct: float = 100.0
        
        # Workforce & Departments
        self.departments: List[str] = []
        self.workforce_count: int = 0
        self.ai_spend_to_date: float = 0.0
        
        # Strategy & Objectives
        self.strategic_horizon: str = "90_days"
        self.strategic_objectives: List[Dict[str, Any]] = []
        self.operating_rules: List[str] = []
        self.owner_preferences: Dict[str, Any] = {
            "risk_tolerance": "MODERATE",
            "spending_philosophy": "ROI_DRIVEN",
            "reporting_style": "EXECUTIVE_FIRST"
        }
        
        # Epistemic Truth Store
        self.facts: Dict[str, Dict[str, Any]] = {}
        self.last_updated: float = time.time()

    def set_fact(
        self,
        key: str,
        value: Any,
        source: str,
        truth_state: str = TruthState.MEASURED,
        confidence: float = 1.0
    ):
        self.facts[key] = {
            "value": value,
            "source": source,
            "timestamp": time.time(),
            "truth_state": truth_state,
            "confidence": confidence
        }

    def get_fact(self, key: str) -> Optional[Dict[str, Any]]:
        return self.facts.get(key)

    def to_dict(self) -> Dict[str, Any]:
        margin_pct = (self.contribution_margin / self.gross_revenue * 100.0) if self.gross_revenue > 0 else 0.0
        return {
            "identity": {
                "tenant_id": self.tenant_id,
                "company_id": self.company_id,
                "name": self.name,
                "industry": self.industry,
                "business_model": self.business_model
            },
            "economics": {
                "gross_revenue": self.gross_revenue,
                "operating_cost": self.operating_cost,
                "contribution_margin": self.contribution_margin,
                "contribution_margin_pct": round(margin_pct, 2),
                "cash_position": self.cash_position if self.cash_position is not None else "UNAVAILABLE",
                "budget_ceiling": self.discretionary_budget_limit,
                "budget_spent": self.discretionary_budget_spent,
                "budget_available": max(0.0, self.discretionary_budget_limit - self.discretionary_budget_spent)
            },
            "operations": {
                "capacity": self.capacity_units,
                "utilization_pct": self.utilization_pct,
                "bottlenecks": self.bottlenecks,
                "sla_compliance_pct": self.sla_compliance_pct
            },
            "workforce": {
                "departments": self.departments,
                "workforce_count": self.workforce_count,
                "ai_spend_to_date": self.ai_spend_to_date
            },
            "strategy": {
                "horizon": self.strategic_horizon,
                "active_objectives": self.strategic_objectives,
                "operating_rules": self.operating_rules,
                "owner_preferences": self.owner_preferences
            },
            "epistemic_facts_count": len(self.facts),
            "last_updated": self.last_updated
        }


class CEOStateEngine:
    """
    Constructs and maintains live CEOCompanyState instances for all tenant portfolio companies.
    """
    _ACTIVE_STATES: Dict[str, CEOCompanyState] = {}

    @classmethod
    def get_or_build_state(
        cls,
        tenant_id: str,
        company_id: str,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        business_model: Optional[str] = None
    ) -> CEOCompanyState:
        key = f"{tenant_id}:{company_id}"
        if key in cls._ACTIVE_STATES:
            return cls._ACTIVE_STATES[key]

        # Load from DB or initialize
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM companies WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id)
            ).fetchone()

        c_name = row["name"] if row else (name or "Enterprise Entity")
        c_ind = row["industry"] if row else (industry or "General Business")
        c_model = business_model or ("Ground-Up Venture" if (row and row["company_type"] == "NEW") else "Operating Enterprise")

        state = CEOCompanyState(
            tenant_id=tenant_id,
            company_id=company_id,
            name=c_name,
            industry=c_ind,
            business_model=c_model
        )

        if row:
            state.gross_revenue = float(row["revenue"] or 0.0)
            state.operating_cost = float(row["cost"] or 0.0)
            state.contribution_margin = float(row["contribution"] or 0.0)

        # Hydrate facts from knowledge graph
        facts = CompanyKnowledgeGraph.query_facts(tenant_id, company_id)
        for f in facts:
            state.set_fact(
                key=f"{f['category']}:{f['predicate']}",
                value=f["object_val"],
                source=f.get("provenance_source", "KNOWLEDGE_GRAPH"),
                truth_state=f.get("truth_state", TruthState.MEASURED),
                confidence=float(f.get("confidence", 1.0))
            )

        # Hydrate departments
        depts = DepartmentControlUnit.list_departments(tenant_id, company_id)
        state.departments = [d["name"] for d in depts]

        cls._ACTIVE_STATES[key] = state
        return state

    @classmethod
    def sync_financials(cls, tenant_id: str, company_id: str, revenue: float, cost: float):
        state = cls.get_or_build_state(tenant_id, company_id)
        state.gross_revenue = revenue
        state.operating_cost = cost
        state.contribution_margin = revenue - cost
        state.last_updated = time.time()
