"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Department Objective Operating Engine
Decomposes Corporate Objectives into departmental objectives under Chief Officer ownership.

Constitutional Invariants:
  HIERARCHICAL_INHERITANCE (Department objectives strictly inherit from parent Corporate Objectives)
  CHIEF_OFFICER_OWNERSHIP (Every department objective maps to an accountable Chief Officer role)
  BOUNDED_DEPARTMENTAL_AUTHORITY (Departments cannot exceed corporate authority or budget bounds)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class ChiefOfficerRole:
    COO = "CHIEF_OPERATING_OFFICER"
    CRO = "CHIEF_REVENUE_OFFICER"
    CMO = "CHIEF_MARKETING_OFFICER"
    CFO = "CHIEF_FINANCIAL_OFFICER"
    CTO = "CHIEF_TECHNOLOGY_OFFICER"
    CHRO = "CHIEF_PEOPLE_OFFICER"
    RISK_OFFICER = "CHIEF_RISK_OFFICER"

@dataclass
class DepartmentObjective:
    dept_obj_id: str
    tenant_id: str
    company_id: str
    corporate_objective_id: str
    department: str
    chief_officer_role: str
    title: str
    description: str
    kpi_targets: Dict[str, Any] = field(default_factory=dict)
    kra_targets: List[str] = field(default_factory=list)
    allocated_budget: float = 0.0
    status: str = "ACTIVE"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class DepartmentObjectiveEngine:
    """
    Manages department objective decomposition, Chief Officer assignments, and KPI target linkage.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def derive_department_objectives(
        self,
        corporate_objective_id: str,
        corporate_title: str,
        total_budget: float = 50000.0
    ) -> List[DepartmentObjective]:
        """
        Decomposes a Corporate Objective into canonical Chief Officer / Departmental Objectives.
        Example: "Increase hotel profitability during peak wedding season while maintaining guest service standards"
        ->
        1. CRO / Revenue: Maximize RevPAR & ADR via dynamic pricing
        2. CMO / Marketing: Drive high-margin direct wedding inquiries & banquet bookings
        3. COO / Operations: Optimize housekeeping & front-desk throughput without degrading guest CSAT
        4. CFO / Finance: Audit night ledger, minimize cost leakages, sustain 30% contribution margin
        5. CTO / Tech: Guarantee 99.9% PMS, CRS, and booking engine availability
        """
        dept_plans = [
            {
                "department": "REVENUE",
                "chief_officer": ChiefOfficerRole.CRO,
                "title": f"RevPAR & Rate Yield Optimization ({corporate_title[:30]}...)",
                "description": "Deploy dynamic room pricing and wedding package yields to capture seasonal demand peak.",
                "kpi_targets": {"revpar": 4500.0, "adr": 5200.0, "occupancy_pct": 88.0},
                "kra_targets": ["Manage rate tiers", "Execute PMS rate synchronizations", "Analyze competitor pricing"],
                "budget_share": 0.30
            },
            {
                "department": "OPERATIONS",
                "chief_officer": ChiefOfficerRole.COO,
                "title": f"Operational Service Delivery & Quality Assurance ({corporate_title[:30]}...)",
                "description": "Ensure seamless check-in, guest services, and housekeeping standards during high occupancy.",
                "kpi_targets": {"guest_satisfaction_score": 4.6, "room_turnaround_mins": 35.0, "sla_compliance": 0.95},
                "kra_targets": ["Staff shift coordination", "VIP wedding party handling", "Incident mitigation"],
                "budget_share": 0.25
            },
            {
                "department": "MARKETING",
                "chief_officer": ChiefOfficerRole.CMO,
                "title": f"High-Yield Direct Demand Generation ({corporate_title[:30]}...)",
                "description": "Drive direct banquet and bridal suite reservations with zero third-party commission overhead.",
                "kpi_targets": {"direct_booking_ratio": 0.65, "acquisition_cost_inr": 350.0},
                "kra_targets": ["Promotional campaigns", "Social wedding showcase", "Corporate banquet outreach"],
                "budget_share": 0.20
            },
            {
                "department": "FINANCE",
                "chief_officer": ChiefOfficerRole.CFO,
                "title": f"Cost Containment & Margin Verification ({corporate_title[:30]}...)",
                "description": "Audit daily night reconciliations and enforce procurement expense ceilings.",
                "kpi_targets": {"contribution_margin_pct": 30.0, "night_audit_discrepancy_inr": 0.0},
                "kra_targets": ["Expense approval reviews", "Ledger revenue reconciliation", "Weekly margin reporting"],
                "budget_share": 0.15
            },
            {
                "department": "TECHNOLOGY",
                "chief_officer": ChiefOfficerRole.CTO,
                "title": f"System Reliability & Channel Infrastructure ({corporate_title[:30]}...)",
                "description": "Maintain zero-downtime integration for PMS, payment gateway, and desktop execution fabric.",
                "kpi_targets": {"system_uptime_pct": 99.9, "api_sync_latency_ms": 120.0},
                "kra_targets": ["Channel manager monitoring", "Secret broker security check", "Host daemon health"],
                "budget_share": 0.10
            }
        ]

        now = time.time()
        results = []

        for p in dept_plans:
            dept_obj_id = f"dept_obj_{p['department'].lower()}_{uuid.uuid4().hex[:8]}"
            allocated = round(total_budget * p["budget_share"], 2)
            obj = DepartmentObjective(
                dept_obj_id=dept_obj_id,
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                corporate_objective_id=corporate_objective_id,
                department=p["department"],
                chief_officer_role=p["chief_officer"],
                title=p["title"],
                description=p["description"],
                kpi_targets=p["kpi_targets"],
                kra_targets=p["kra_targets"],
                allocated_budget=allocated,
                status="ACTIVE",
                created_at=now,
                updated_at=now
            )
            self._persist_dept_objective(obj)
            results.append(obj)

            create_executive_event(
                event_type="DepartmentObjectiveCreated",
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                payload={
                    "dept_obj_id": obj.dept_obj_id,
                    "department": obj.department,
                    "chief_officer": obj.chief_officer_role,
                    "corporate_objective_id": corporate_objective_id,
                    "budget": obj.allocated_budget
                }
            )

        return results

    def _persist_dept_objective(self, obj: DepartmentObjective):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO department_objectives (
                    dept_obj_id, tenant_id, company_id, corporate_objective_id,
                    department, chief_officer_role, title, description,
                    kpi_targets, kra_targets, allocated_budget, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dept_obj_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    kpi_targets=excluded.kpi_targets,
                    kra_targets=excluded.kra_targets,
                    allocated_budget=excluded.allocated_budget,
                    status=excluded.status,
                    updated_at=excluded.updated_at
            """, (
                obj.dept_obj_id, obj.tenant_id, obj.company_id, obj.corporate_objective_id,
                obj.department, obj.chief_officer_role, obj.title, obj.description,
                json.dumps(obj.kpi_targets), json.dumps(obj.kra_targets), obj.allocated_budget,
                obj.status, obj.created_at, obj.updated_at
            ))
            conn.commit()

    def get_department_objectives(self, corporate_objective_id: Optional[str] = None) -> List[DepartmentObjective]:
        with db.get_connection() as conn:
            if corporate_objective_id:
                rows = conn.execute(
                    "SELECT * FROM department_objectives WHERE tenant_id = ? AND company_id = ? AND corporate_objective_id = ? ORDER BY created_at ASC",
                    (self.tenant_id, self.company_id, corporate_objective_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM department_objectives WHERE tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                    (self.tenant_id, self.company_id)
                ).fetchall()

            res = []
            for r in rows:
                res.append(DepartmentObjective(
                    dept_obj_id=r["dept_obj_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    corporate_objective_id=r["corporate_objective_id"],
                    department=r["department"],
                    chief_officer_role=r["chief_officer_role"],
                    title=r["title"],
                    description=r["description"],
                    kpi_targets=json.loads(r["kpi_targets"] or "{}"),
                    kra_targets=json.loads(r["kra_targets"] or "[]"),
                    allocated_budget=r["allocated_budget"],
                    status=r["status"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ))
            return res
