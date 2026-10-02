"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 3 — AI Employee Operating System
Formal AI Employee model, immutable identity, versioning, capability bindings,
authority scoping, and strict 10-stage lifecycle state machine.

Constitutional Invariants:
  EMPLOYEE != HUMAN
  EMPLOYEE_IDENTITY != EMPLOYEE_AUTHORITY
  NO_AUTHORITY_MERELY_BY_CREATION
  OFFBOARDED_AI_EMPLOYEE -> NO_ACTIVE_EXECUTION
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from core.database_engine import engine, WorkloadType
from core.identity_gateway import identity_gateway, IdentityType, IdentityStatus

logger = logging.getLogger("zonata.ai_employee.os")

class EmployeeLifecycleState:
    PROPOSED = "PROPOSED"
    EVALUATED = "EVALUATED"
    APPROVED = "APPROVED"
    PROVISIONED = "PROVISIONED"
    ONBOARDED = "ONBOARDED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"
    OFFBOARDED = "OFFBOARDED"
    RETIRED = "RETIRED"

class EmployeeRoleTier:
    AI_EXECUTIVE = "AI_EXECUTIVE"
    AI_SPECIALIST = "AI_SPECIALIST"
    AI_WORKER = "AI_WORKER"

@dataclass
class AuthorityScope:
    max_risk_class: str = "LOW_RISK"          # READ_ONLY, LOW_RISK, MUTATING, FINANCIAL, DESTRUCTIVE
    max_single_spend_usd: float = 0.0          # Financial action ceiling
    can_delegate: bool = False                 # Whether employee can spawn child workers
    can_access_restricted_data: bool = False   # Whether employee can access CONFIDENTIAL/RESTRICTED data
    requires_human_approval: bool = True       # Enforce human-in-the-loop for non-read operations
    allowed_domains: List[str] = None          # Network / web domain restrictions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_risk_class": self.max_risk_class,
            "max_single_spend_usd": self.max_single_spend_usd,
            "can_delegate": self.can_delegate,
            "can_access_restricted_data": self.can_access_restricted_data,
            "requires_human_approval": self.requires_human_approval,
            "allowed_domains": self.allowed_domains or []
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthorityScope':
        return cls(
            max_risk_class=data.get("max_risk_class", "LOW_RISK"),
            max_single_spend_usd=float(data.get("max_single_spend_usd", 0.0)),
            can_delegate=bool(data.get("can_delegate", False)),
            can_access_restricted_data=bool(data.get("can_access_restricted_data", False)),
            requires_human_approval=bool(data.get("requires_human_approval", True)),
            allowed_domains=data.get("allowed_domains", [])
        )

@dataclass
class AIEmployee:
    employee_id: str
    tenant_id: str
    company_id: str
    name: str
    role_tier: str
    template_id: str
    version: str
    department_id: str
    team_id: Optional[str]
    supervisor_id: Optional[str]
    capabilities: List[str]
    allowed_tools: List[str]
    allowed_data_domains: List[str]
    allowed_systems: List[str]
    authority: AuthorityScope
    allocated_budget_usd: float
    spent_budget_usd: float
    lifecycle_state: str
    health_status: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any]

    def is_operational(self) -> bool:
        return self.lifecycle_state == EmployeeLifecycleState.ACTIVE

    def remaining_budget(self) -> float:
        return max(0.0, self.allocated_budget_usd - self.spent_budget_usd)

class AIEmployeeRegistry:
    """
    Authoritative registry and lifecycle state machine for corporate AI Employees.
    Ensures that creation of an AI entity does not grant automatic operational authority.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_employees (
                employee_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role_tier TEXT NOT NULL,
                template_id TEXT NOT NULL,
                version TEXT NOT NULL,
                department_id TEXT NOT NULL,
                team_id TEXT,
                supervisor_id TEXT,
                capabilities JSON NOT NULL,
                allowed_tools JSON NOT NULL,
                allowed_data_domains JSON NOT NULL,
                allowed_systems JSON NOT NULL,
                authority_scope JSON NOT NULL,
                allocated_budget_usd REAL NOT NULL DEFAULT 0.0,
                spent_budget_usd REAL NOT NULL DEFAULT 0.0,
                lifecycle_state TEXT NOT NULL DEFAULT 'PROPOSED',
                health_status TEXT NOT NULL DEFAULT 'HEALTHY',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata JSON
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_emp_tenant ON ai_employees(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_emp_state ON ai_employees(lifecycle_state);")

    # -------------------------------------------------------------
    # 1. Proposal & Evaluation Pipeline
    # -------------------------------------------------------------
    def propose_employee(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        role_tier: str,
        template_id: str,
        version: str,
        department_id: str,
        team_id: Optional[str] = None,
        supervisor_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
        allowed_data_domains: Optional[List[str]] = None,
        allowed_systems: Optional[List[str]] = None,
        authority: Optional[AuthorityScope] = None,
        initial_budget_usd: float = 100.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIEmployee:
        """
        Stage 1: Propose AI Employee. Initially created in PROPOSED state with ZERO execution authority.
        """
        emp_id = f"emp_ai_{uuid.uuid4().hex[:12]}"
        now = time.time()
        auth = authority or AuthorityScope()

        emp = AIEmployee(
            employee_id=emp_id,
            tenant_id=tenant_id,
            company_id=company_id,
            name=name,
            role_tier=role_tier,
            template_id=template_id,
            version=version,
            department_id=department_id,
            team_id=team_id,
            supervisor_id=supervisor_id,
            capabilities=capabilities or [],
            allowed_tools=allowed_tools or [],
            allowed_data_domains=allowed_data_domains or ["PUBLIC"],
            allowed_systems=allowed_systems or [],
            authority=auth,
            allocated_budget_usd=initial_budget_usd,
            spent_budget_usd=0.0,
            lifecycle_state=EmployeeLifecycleState.PROPOSED,
            health_status="PENDING_EVALUATION",
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO ai_employees (
                employee_id, tenant_id, company_id, name, role_tier, template_id, version,
                department_id, team_id, supervisor_id, capabilities, allowed_tools,
                allowed_data_domains, allowed_systems, authority_scope, allocated_budget_usd,
                spent_budget_usd, lifecycle_state, health_status, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                emp.employee_id, emp.tenant_id, emp.company_id, emp.name, emp.role_tier,
                emp.template_id, emp.version, emp.department_id, emp.team_id, emp.supervisor_id,
                json.dumps(emp.capabilities), json.dumps(emp.allowed_tools),
                json.dumps(emp.allowed_data_domains), json.dumps(emp.allowed_systems),
                json.dumps(emp.authority.to_dict()), emp.allocated_budget_usd,
                emp.spent_budget_usd, emp.lifecycle_state, emp.health_status,
                emp.created_at, emp.updated_at, json.dumps(emp.metadata)
            ))
        logger.info(f"Proposed new AI Employee: {emp_id} ({name}) under department {department_id}")
        return emp

    # -------------------------------------------------------------
    # 2. Lifecycle State Transitions
    # -------------------------------------------------------------
    def advance_lifecycle(self, employee_id: str, new_state: str, approver_id: Optional[str] = None, reason: str = "") -> bool:
        """
        Strict state transition gate enforcing enterprise approval before activation.
        """
        valid_transitions = {
            EmployeeLifecycleState.PROPOSED: [EmployeeLifecycleState.EVALUATED, EmployeeLifecycleState.RETIRED],
            EmployeeLifecycleState.EVALUATED: [EmployeeLifecycleState.APPROVED, EmployeeLifecycleState.PROPOSED, EmployeeLifecycleState.RETIRED],
            EmployeeLifecycleState.APPROVED: [EmployeeLifecycleState.PROVISIONED, EmployeeLifecycleState.RETIRED],
            EmployeeLifecycleState.PROVISIONED: [EmployeeLifecycleState.ONBOARDED, EmployeeLifecycleState.SUSPENDED],
            EmployeeLifecycleState.ONBOARDED: [EmployeeLifecycleState.ACTIVE, EmployeeLifecycleState.PAUSED],
            EmployeeLifecycleState.ACTIVE: [EmployeeLifecycleState.PAUSED, EmployeeLifecycleState.SUSPENDED, EmployeeLifecycleState.OFFBOARDED],
            EmployeeLifecycleState.PAUSED: [EmployeeLifecycleState.ACTIVE, EmployeeLifecycleState.SUSPENDED, EmployeeLifecycleState.OFFBOARDED],
            EmployeeLifecycleState.SUSPENDED: [EmployeeLifecycleState.ACTIVE, EmployeeLifecycleState.OFFBOARDED, EmployeeLifecycleState.RETIRED],
            EmployeeLifecycleState.OFFBOARDED: [EmployeeLifecycleState.RETIRED],
            EmployeeLifecycleState.RETIRED: []
        }

        emp = self.get_employee(employee_id)
        if not emp:
            raise ValueError(f"AI Employee '{employee_id}' not found.")

        current = emp.lifecycle_state
        allowed = valid_transitions.get(current, [])
        if new_state not in allowed:
            raise PermissionError(f"Invalid lifecycle transition from {current} to {new_state}.")

        # Onboarding action: register with Enterprise Identity Gateway when moving to ONBOARDED / ACTIVE
        if new_state == EmployeeLifecycleState.ONBOARDED:
            identity_gateway.register_identity(
                identity_id=emp.employee_id,
                identity_type=IdentityType.AI_EMPLOYEE,
                tenant_id=emp.tenant_id,
                company_id=emp.company_id,
                display_name=emp.name,
                roles=[emp.role_tier],
                departments=[emp.department_id],
                mfa_verified=False,
                metadata={"template_id": emp.template_id, "version": emp.version}
            )

        # Offboarding action: immediately revoke identity and authority
        if new_state in (EmployeeLifecycleState.OFFBOARDED, EmployeeLifecycleState.RETIRED):
            identity_gateway.offboard_identity(employee_id, reason=f"AI Employee lifecycle: {new_state} - {reason}")

        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE ai_employees
            SET lifecycle_state = ?, updated_at = ?
            WHERE employee_id = ?
            """, (new_state, now, employee_id))

        logger.info(f"AI Employee {employee_id} transitioned: {current} -> {new_state} by {approver_id or 'SYSTEM'}")
        return True

    def get_employee(self, employee_id: str) -> Optional[AIEmployee]:
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM ai_employees WHERE employee_id = ?", (employee_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return AIEmployee(
                employee_id=row["employee_id"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                name=row["name"],
                role_tier=row["role_tier"],
                template_id=row["template_id"],
                version=row["version"],
                department_id=row["department_id"],
                team_id=row["team_id"],
                supervisor_id=row["supervisor_id"],
                capabilities=json.loads(row["capabilities"]),
                allowed_tools=json.loads(row["allowed_tools"]),
                allowed_data_domains=json.loads(row["allowed_data_domains"]),
                allowed_systems=json.loads(row["allowed_systems"]),
                authority=AuthorityScope.from_dict(json.loads(row["authority_scope"])),
                allocated_budget_usd=row["allocated_budget_usd"],
                spent_budget_usd=row["spent_budget_usd"],
                lifecycle_state=row["lifecycle_state"],
                health_status=row["health_status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

    def list_employees(self, tenant_id: str, company_id: Optional[str] = None) -> List[AIEmployee]:
        with engine.connection(workload=WorkloadType.READ) as conn:
            query = "SELECT * FROM ai_employees WHERE tenant_id = ?"
            params = [tenant_id]
            if company_id:
                query += " AND company_id = ?"
                params.append(company_id)
            rows = conn.execute(query, params).fetchall()
            return [
                AIEmployee(
                    employee_id=row["employee_id"],
                    tenant_id=row["tenant_id"],
                    company_id=row["company_id"],
                    name=row["name"],
                    role_tier=row["role_tier"],
                    template_id=row["template_id"],
                    version=row["version"],
                    department_id=row["department_id"],
                    team_id=row["team_id"],
                    supervisor_id=row["supervisor_id"],
                    capabilities=json.loads(row["capabilities"]),
                    allowed_tools=json.loads(row["allowed_tools"]),
                    allowed_data_domains=json.loads(row["allowed_data_domains"]),
                    allowed_systems=json.loads(row["allowed_systems"]),
                    authority=AuthorityScope.from_dict(json.loads(row["authority_scope"])),
                    allocated_budget_usd=row["allocated_budget_usd"],
                    spent_budget_usd=row["spent_budget_usd"],
                    lifecycle_state=row["lifecycle_state"],
                    health_status=row["health_status"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                for row in rows
            ]

# Global singleton
ai_employee_registry = AIEmployeeRegistry()
