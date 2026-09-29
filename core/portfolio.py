"""
RoboAssistant Company OS 1.0 — Multi-Entity Company Portfolio & Onboarding Engine
Zero Mock Financials: Financial states begin strictly at 0.0 until verified.
Integrated with normalized SQLite multi-tenant database engine.
"""

from typing import Dict, List, Optional, Any
import uuid
import time
import json
from .models import OperatingContext, DataSource, Mission, AgentEmploymentContract, HostType
from .workforce import DynamicAgentFactory
from .db import db
from .auth import TenantManager

class CompanyPortfolioManager:
    def __init__(self, tenant_id: str = "tnt_primary", load_from_db: bool = False):
        self.tenant_id = tenant_id
        self.companies: Dict[str, OperatingContext] = {}
        self._ensure_tenant_exists()
        if load_from_db:
            self._load_existing_from_db()

    def _ensure_tenant_exists(self):
        with db.get_connection() as conn:
            row = conn.execute("SELECT tenant_id FROM tenants WHERE tenant_id = ?", (self.tenant_id,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (self.tenant_id, "Primary Enterprise", "ENTERPRISE", "ACTIVE", time.time())
                )
                conn.commit()

    def _load_existing_from_db(self):
        try:
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM companies WHERE tenant_id = ? ORDER BY created_at ASC", (self.tenant_id,)).fetchall()
                seen_names = set()
                for r in rows:
                    name_norm = (r["name"] or "").strip().lower()
                    if name_norm in seen_names:
                        continue
                    seen_names.add(name_norm)
                    cid = r["company_id"]
                    # Load departments
                    depts = [dr["name"] for dr in conn.execute("SELECT name FROM departments WHERE company_id = ?", (cid,)).fetchall()]
                    # Load workforce
                    workforce: Dict[str, AgentEmploymentContract] = {}
                    for er in conn.execute("SELECT * FROM employees WHERE company_id = ?", (cid,)).fetchall():
                        contract = AgentEmploymentContract(
                            agent_id=er["agent_id"],
                            role=er["role"],
                            department=er["department"],
                            manager=er["manager"] or "AI CEO",
                            responsibilities=["Execute autonomous workflows"],
                            objectives=["100% verification compliance"],
                            allowed_tools=["python3", "jq", "curl"],
                            allowed_hosts=[HostType.LINUX_CLOUD],
                            data_access=["read_only"],
                            budget_limit=er["budget_limit"],
                            spending_limit=er["spending_limit"],
                            decision_authority=["scoped_tasks"],
                            approval_requirements=["financial_spend", "destructive_mutation"],
                            forbidden_actions=["credential_extraction", "drop_table", "mass_delete"],
                            kpis={},
                            escalation_rules=["Escalate unknown tool requirement to CEO"],
                            working_state=er["working_state"] or "ACTIVE"
                        )
                        workforce[contract.agent_id] = contract

                    # Load data sources
                    data_sources: List[DataSource] = []
                    for sr in conn.execute("SELECT * FROM data_sources WHERE company_id = ?", (cid,)).fetchall():
                        data_sources.append(DataSource(
                            source_id=sr["source_id"],
                            name=sr["name"],
                            source_type=sr["source_type"],
                            connection_method=sr["connection_method"],
                            freshness="Connected",
                            permission_level=sr["permission_level"],
                            health=sr["health"]
                        ))

                    rules = json.loads(r["operating_rules"]) if r["operating_rules"] else []
                    base = json.loads(r["baseline_summary"]) if r["baseline_summary"] else None

                    ctx = OperatingContext(
                        company_id=cid,
                        name=r["name"],
                        industry=r["industry"],
                        company_type=r["company_type"],
                        status=r["status"],
                        revenue=r["revenue"],
                        cost=r["cost"],
                        contribution=r["contribution"],
                        departments=depts or ["Executive", "Operations"],
                        workforce=workforce,
                        missions=[],
                        data_sources=data_sources,
                        operating_rules=rules,
                        understanding_pct=r["understanding_pct"],
                        baseline_summary=base
                    )
                    self.companies[cid] = ctx
        except Exception:
            pass

    def register_company(self, company: OperatingContext):
        existing = self.get_company_by_name(company.name)
        if existing and existing.company_id != company.company_id:
            company.company_id = existing.company_id
        elif not existing:
            # Also check DB for this tenant
            try:
                with db.get_connection() as conn:
                    db_row = conn.execute("SELECT company_id FROM companies WHERE tenant_id = ? AND lower(trim(name)) = lower(trim(?))", (self.tenant_id, company.name)).fetchone()
                    if db_row:
                        company.company_id = db_row["company_id"]
            except Exception:
                pass

        self.companies[company.company_id] = company
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO companies (
                    company_id, tenant_id, name, industry, company_type, status,
                    revenue, cost, contribution, understanding_pct,
                    operating_rules, baseline_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company.company_id,
                    self.tenant_id,
                    company.name,
                    company.industry,
                    company.company_type,
                    company.status,
                    company.revenue,
                    company.cost,
                    company.contribution,
                    company.understanding_pct,
                    json.dumps(company.operating_rules),
                    json.dumps(company.baseline_summary) if company.baseline_summary else None,
                    now
                )
            )
            # Register departments
            for dept_name in company.departments:
                dept_id = f"dept_{company.company_id}_{dept_name.lower().replace(' ', '_')}"
                conn.execute(
                    """
                    INSERT OR IGNORE INTO departments (
                        department_id, company_id, tenant_id, name, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (dept_id, company.company_id, self.tenant_id, dept_name, now)
                )

            # Register workforce
            for emp in company.workforce.values():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO employees (
                        agent_id, company_id, tenant_id, role, department, manager,
                        budget_limit, spending_limit, authority_ceiling, working_state, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        emp.agent_id,
                        company.company_id,
                        self.tenant_id,
                        emp.role,
                        emp.department,
                        emp.manager,
                        emp.budget_limit,
                        emp.spending_limit,
                        "AUTOMATIC_IDEMPOTENT",
                        emp.working_state,
                        now
                    )
                )

            # Register data sources
            for ds in company.data_sources:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO data_sources (
                        source_id, company_id, tenant_id, name, source_type, connection_method,
                        permission_level, health, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ds.source_id,
                        company.company_id,
                        self.tenant_id,
                        ds.name,
                        ds.source_type,
                        ds.connection_method,
                        ds.permission_level,
                        ds.health,
                        now
                    )
                )
            conn.commit()

    def get_company(self, company_id: str) -> Optional[OperatingContext]:
        return self.companies.get(company_id)

    def get_company_by_name(self, name: str) -> Optional[OperatingContext]:
        name_clean = (name or "").strip().lower()
        for c in self.companies.values():
            if c.name.strip().lower() == name_clean:
                return c
        return None

    def list_companies(self) -> List[OperatingContext]:
        seen = set()
        deduped = []
        for c in self.companies.values():
            name_norm = (c.name or "").strip().lower()
            if name_norm not in seen:
                seen.add(name_norm)
                deduped.append(c)
        return deduped

    def onboard_company(
        self,
        name: str,
        country: str = "IN",
        industry: str = "General",
        company_type: str = "NEW",
        operating_rules: Optional[List[str]] = None
    ) -> OperatingContext:
        existing = self.get_company_by_name(name)
        if existing:
            return existing
        ctx = CompanyOnboardingEngine.onboard_new_company(
            name=name,
            industry=industry,
            business_model="Enterprise",
            initial_operating_rules=operating_rules
        )
        ctx.company_type = company_type
        self.register_company(ctx)
        return ctx

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Group-level portfolio performance aggregation computed from real state."""
        total_rev = sum(c.revenue for c in self.companies.values())
        total_cost = sum(c.cost for c in self.companies.values())
        total_contribution = sum(c.contribution for c in self.companies.values())
        total_missions = sum(len(c.missions) for c in self.companies.values())
        total_employees = sum(len(c.workforce) for c in self.companies.values())

        active_count = sum(1 for c in self.companies.values() if c.status == "OPERATIONAL")
        attention_count = sum(1 for c in self.companies.values() if c.status == "ATTENTION")

        return {
            "total_companies": len(self.companies),
            "operational_companies": active_count,
            "attention_required_count": attention_count,
            "total_revenue": total_rev,
            "total_cost": total_cost,
            "total_contribution": total_contribution,
            "total_active_missions": total_missions,
            "total_ai_employees": total_employees,
            "currency_symbol": "₹"
        }

class CompanyOnboardingEngine:
    """
    Handles formal onboarding for New Companies and Existing Real-World Enterprises.
    Starts with 0.0 baseline financials until verified ledger entries are ingested.
    """

    @classmethod
    def onboard_new_company(
        cls,
        name: str,
        industry: str,
        business_model: str,
        target_revenue: float = 0.0,
        initial_operating_rules: Optional[List[str]] = None,
        departments: Optional[List[str]] = None
    ) -> OperatingContext:
        company_id = f"comp_{uuid.uuid4().hex[:6]}"
        rules = initial_operating_rules or [
            "Prefer free and open-source tools before incurring paid software costs.",
            "Require human approval for all external payments over ₹10,000.",
            "Never allow access to unencrypted corporate credentials."
        ]

        depts = departments or ["Executive", "Finance", "Operations", "Marketing", "Sales"]
        workforce: Dict[str, AgentEmploymentContract] = {}

        # AI Manager: Operations
        ops_contract = DynamicAgentFactory.create_employment_contract(
            role="Operations Manager",
            department="Operations",
            manager="AI CEO",
            responsibilities=["Supervise day-to-day workflow", "Maintain process quality"],
            objectives=["Zero operational defect rate", "Cost containment"],
            allowed_tools=["python3", "tar", "jq", "curl"],
            budget_limit=0.0,
            spending_limit=0.0
        )
        workforce[ops_contract.agent_id] = ops_contract

        # AI Specialist: Financial Controller
        fin_contract = DynamicAgentFactory.create_employment_contract(
            role="Financial Controller",
            department="Finance",
            manager="AI CEO",
            responsibilities=["Track revenue and burn", "Audit vendor expenses"],
            objectives=["Maintain positive unit economics"],
            allowed_tools=["python3", "jq"],
            budget_limit=0.0,
            spending_limit=0.0
        )
        workforce[fin_contract.agent_id] = fin_contract

        ctx = OperatingContext(
            company_id=company_id,
            name=name,
            industry=industry,
            company_type="NEW",
            status="OPERATIONAL",
            revenue=0.0,
            cost=0.0,
            contribution=0.0,
            departments=depts,
            workforce=workforce,
            missions=[],
            data_sources=[],
            operating_rules=rules,
            understanding_pct=100.0,
            baseline_summary={
                "status": "INITIALIZED",
                "business_model": business_model,
                "target_revenue": target_revenue,
                "created_at": time.time()
            }
        )
        return ctx

    @classmethod
    def onboard_existing_company(
        cls,
        name: str,
        industry: str,
        website: str = "",
        initial_data_sources: Optional[List[Dict[str, str]]] = None,
        operating_rules: Optional[List[str]] = None,
        departments: Optional[List[str]] = None
    ) -> OperatingContext:
        """
        Existing enterprise onboarding: connects data sources, conducts Understanding Phase,
        and establishes an auditable Company Baseline with zero initial mock numbers.
        """
        company_id = f"comp_{uuid.uuid4().hex[:6]}"
        data_sources: List[DataSource] = []
        initial_sources = initial_data_sources or []

        for ds in initial_sources:
            data_sources.append(DataSource(
                source_id=f"ds_{uuid.uuid4().hex[:6]}",
                name=ds["name"],
                source_type=ds["type"],
                connection_method=ds.get("method", "API"),
                freshness="Connected",
                permission_level="READ_ONLY_VISIBILITY",  # Strict invariant: ingestion != permission to modify
                available_data=ds.get("data", ["records", "metrics"])
            ))

        understanding_pct = min(100.0, float(len(data_sources) * 25.0)) if data_sources else 0.0

        baseline = {
            "status": "CONNECTED_AWAITING_INGESTION" if data_sources else "NO_SOURCES_CONNECTED",
            "connected_sources": len(data_sources),
            "historical_revenue": 0.0,
            "historical_cost": 0.0,
            "historical_contribution": 0.0,
            "established_at": time.time()
        }

        depts = departments or ["Executive", "Revenue Management", "Sales & Marketing", "Front Office", "Operations"]
        workforce: Dict[str, AgentEmploymentContract] = {}

        rev_manager = DynamicAgentFactory.create_employment_contract(
            role="Revenue Optimization Manager",
            department="Revenue Management",
            manager="AI CEO",
            responsibilities=["Analyze ADR and RevPAR", "Reconcile night audit", "Optimize distribution"],
            objectives=["Increase RevPAR", "Lower direct booking acquisition cost"],
            allowed_tools=["python3", "curl", "jq"],
            budget_limit=0.0,
            spending_limit=0.0
        )
        workforce[rev_manager.agent_id] = rev_manager

        ctx = OperatingContext(
            company_id=company_id,
            name=name,
            industry=industry,
            company_type="EXISTING",
            status="OPERATIONAL",
            revenue=0.0,
            cost=0.0,
            contribution=0.0,
            departments=depts,
            workforce=workforce,
            missions=[],
            data_sources=data_sources,
            operating_rules=operating_rules or ["Always check read-only validation before mutating production DB."],
            understanding_pct=understanding_pct,
            baseline_summary=baseline
        )

        return ctx
