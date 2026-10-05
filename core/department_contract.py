"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Standard Department Contract & Dynamic Provisioning Architecture

Implements Section 13 & Section 14 of the Gemma 4 Master Specification:
- Standard Department Contract:
    identity, mission, objectives, capabilities, permitted actions,
    prohibited actions, available agents, available tools, resources,
    current workload, KPIs (extensible), risks, escalation rules, reporting format
- Dynamic provisioning for all 25 enterprise departments:
    Strategy, Finance, Accounting, Sales, Marketing, Operations,
    Human Resources, Customer Support, Product, Engineering, IT,
    Security, Legal/Compliance, Procurement, Administration,
    Business Development, Revenue Management, Data/Analytics, Research,
    Content, Partnerships, Hospitality, Travel, Food/Local Business,
    Distribution, Customer Success.
- Extensible KPI slots without premature locking.
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# 25 Standard Enterprise Departments
STANDARD_DEPARTMENT_CATALOG = [
    "Strategy",
    "Finance",
    "Accounting",
    "Sales",
    "Marketing",
    "Operations",
    "Human Resources",
    "Customer Support",
    "Product",
    "Engineering",
    "IT",
    "Security",
    "Legal/Compliance",
    "Procurement",
    "Administration",
    "Business Development",
    "Revenue Management",
    "Data/Analytics",
    "Research",
    "Content",
    "Partnerships",
    "Hospitality",
    "Travel",
    "Food/Local Business",
    "Distribution",
    "Customer Success"
]

@dataclass
class StandardDepartmentContract:
    identity: str                       # e.g., "dept_revenue_management"
    name: str                           # e.g., "Revenue Management"
    tenant_id: str
    company_id: str
    mission: str
    objectives: List[str]
    capabilities: List[str]
    permitted_actions: List[str]
    prohibited_actions: List[str]
    available_agents: List[str]
    available_tools: List[str]
    resources: Dict[str, Any]
    current_workload_pct: int           # 0 to 100
    kpis: Dict[str, Any]                # Extensible KPI architecture
    risks: List[Dict[str, Any]]
    escalation_rules: List[str]
    reporting_format: str
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DynamicDepartmentRegistry:
    """
    Manages dynamic provisioning and contract verification for enterprise departments.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._departments: Dict[str, StandardDepartmentContract] = {}
        self._seed_default_departments()

    def _seed_default_departments(self):
        """Provisions primary standard operating departments."""
        defaults = [
            ("Revenue Management", "Maximize top-line yield, pricing velocity, and RevPAR pacing within bounded rate corridors.", ["yield_optimization", "rate_pacing"]),
            ("Hospitality", "Coordinate guest service operations, night audits, front-desk workflows, and housekeeping SLAs.", ["night_audit", "housekeeping_dispatch"]),
            ("Marketing", "Execute multi-channel digital acquisition campaigns and localized customer engagement.", ["ad_campaign_dispatch", "social_distribution"]),
            ("Operations", "Supervise daily operational throughput, bottleneck detection, and facilities maintenance.", ["bottleneck_triage", "facility_dispatch"]),
            ("Finance", "Manage corporate cash flows, supplier invoice reconciliation, and cost leakage containment.", ["ledger_reconciliation", "invoice_audit"])
        ]
        for name, mission, caps in defaults:
            self.provision_department(name, mission, capabilities=caps)

    def provision_department(
        self,
        name: str,
        mission: str,
        capabilities: Optional[List[str]] = None,
        budget_inr: float = 50000.0
    ) -> StandardDepartmentContract:
        dept_id = f"dept_{name.lower().replace(' ', '_').replace('/', '_')}"

        caps = capabilities or [f"{name.lower().replace(' ', '_')}_standard_op"]
        permitted = [f"{c}:execute" for c in caps]
        prohibited = [
            "external_secret_exfiltration",
            "unauthorized_contract_signing",
            "destructive_db_mutation",
            "cross_tenant_data_access"
        ]

        contract = StandardDepartmentContract(
            identity=dept_id,
            name=name,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission=mission,
            objectives=[f"Deliver verifiable business outcomes for {name}"],
            capabilities=caps,
            permitted_actions=permitted,
            prohibited_actions=prohibited,
            available_agents=[f"{dept_id}_chief", f"{dept_id}_operator"],
            available_tools=[f"{c}_tool" for c in caps],
            resources={"monthly_budget_inr": budget_inr, "allocated_agents": 2},
            current_workload_pct=45,
            kpis={"status": "EXTENSIBLE_FRAMEWORK_ACTIVE", "metric_slots": ["throughput", "variance", "cost"]},
            risks=[{"category": "OPERATIONAL", "mitigation": "Continuous supervision loop"}],
            escalation_rules=["ESCALATE_TO_AI_CEO_ON_SLA_BREACH", "ESCALATE_TO_OWNER_ON_BUDGET_OVERRUN"],
            reporting_format="EXECUTIVE_SUMMARY_MARKDOWN_V2"
        )
        self._departments[dept_id] = contract
        return contract

    def get_department(self, dept_name_or_id: str) -> Optional[StandardDepartmentContract]:
        for d in self._departments.values():
            if d.identity == dept_name_or_id or d.name.lower() == dept_name_or_id.lower():
                return d
        return None

    def list_departments(self) -> List[StandardDepartmentContract]:
        return list(self._departments.values())
