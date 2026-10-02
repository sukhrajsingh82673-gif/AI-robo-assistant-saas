"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Architecture — Employee Template Schema & Registry
Defines the formal governed specification from which ZONATA instantiates
Type B (Universal) and Type C (Project-Specific) AI Employees.

Constitutional Invariants:
  TEMPLATE != AGENT
  TEMPLATE == GOVERNED_OPERATIONAL_SPECIFICATION
  IMMUTABLE_VERSIONING (No silent mutation of production templates)
"""

import time
import json
import uuid
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.v7.employee_template")

class TemplateType:
    UNIVERSAL = "UNIVERSAL"
    PROJECT_SPECIFIC = "PROJECT_SPECIFIC"

class TemplateStatus:
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    EVALUATED = "EVALUATED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

@dataclass
class EmployeeTemplate:
    template_id: str
    tenant_id: str
    company_id: str
    name: str
    version: str
    template_type: str                  # UNIVERSAL or PROJECT_SPECIFIC
    status: str                         # TemplateStatus
    business_purpose: str
    role_definition: str
    department: str
    job_family: str
    responsibilities: List[str]
    objectives: List[str]
    sop_references: List[Dict[str, Any]]
    kras: List[Dict[str, Any]]
    kpis: List[Dict[str, Any]]
    success_metrics: List[str]
    failure_conditions: List[str]
    required_knowledge: List[str]
    knowledge_sources: List[str]
    allowed_data_classes: List[str]
    required_tools: List[str]
    allowed_capabilities: List[str]
    authority_scope: Dict[str, Any]
    budget_limit: float
    token_budget: int
    tool_budget: int
    autonomy_level: int                 # 0 to 5
    manager_id: Optional[str] = None
    supervisor_id: Optional[str] = None
    project_id: Optional[str] = None
    description: str = ""
    preferred_agents: List[str] = field(default_factory=list)
    required_agents: List[str] = field(default_factory=list)
    collaboration_rules: Dict[str, Any] = field(default_factory=dict)
    approval_requirements: Dict[str, Any] = field(default_factory=dict)
    working_schedule: str = "24x7_CONTINUOUS"
    communication_policy: Dict[str, Any] = field(default_factory=dict)
    escalation_policy: Dict[str, Any] = field(default_factory=dict)
    reporting_policy: Dict[str, Any] = field(default_factory=dict)
    ceo_visibility: bool = True
    security_policy: Dict[str, Any] = field(default_factory=dict)
    compliance_policy: Dict[str, Any] = field(default_factory=dict)
    evaluation_policy: Dict[str, Any] = field(default_factory=dict)
    replacement_policy: Dict[str, Any] = field(default_factory=dict)
    retirement_policy: Dict[str, Any] = field(default_factory=dict)
    created_by: str = "HUMAN_OWNER"
    approved_by: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version_hash: str = ""
    template_signature: str = ""

    def calculate_version_hash(self) -> str:
        """Deterministic canonical SHA-256 hash of template specification."""
        content = {
            "template_id": self.template_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "project_id": self.project_id,
            "name": self.name,
            "version": self.version,
            "template_type": self.template_type,
            "role_definition": self.role_definition,
            "department": self.department,
            "responsibilities": self.responsibilities,
            "objectives": self.objectives,
            "sop_references": self.sop_references,
            "kras": self.kras,
            "kpis": self.kpis,
            "allowed_data_classes": self.allowed_data_classes,
            "required_tools": self.required_tools,
            "allowed_capabilities": self.allowed_capabilities,
            "authority_scope": self.authority_scope,
            "budget_limit": self.budget_limit,
            "token_budget": self.token_budget,
            "tool_budget": self.tool_budget,
            "autonomy_level": self.autonomy_level,
            "manager_id": self.manager_id
        }
        canonical_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

    def sign(self, secret_key: str = "zonata_v7_template_secret") -> str:
        """Generate HMAC-SHA256 signature over version hash."""
        h = self.calculate_version_hash()
        self.version_hash = h
        sig = hmac.new(secret_key.encode('utf-8'), h.encode('utf-8'), hashlib.sha256).hexdigest()
        self.template_signature = sig
        return sig

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmployeeTemplateRegistry:
    """
    Authoritative persistent repository for AI Employee Templates.
    Enforces immutable versioning, tenant isolation, and cryptographic integrity.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_templates (
                template_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                project_id TEXT,
                name TEXT NOT NULL,
                latest_version TEXT NOT NULL,
                template_type TEXT NOT NULL,
                status TEXT NOT NULL,
                department TEXT NOT NULL,
                job_family TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_template_versions (
                version_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                version_hash TEXT NOT NULL,
                signature TEXT NOT NULL,
                specification JSON NOT NULL,
                created_by TEXT NOT NULL,
                approved_by TEXT,
                created_at REAL NOT NULL,
                UNIQUE(template_id, version)
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tmpl_tenant ON employee_templates(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tmpl_vers ON employee_template_versions(template_id, version);")

    def create_template(self, template: EmployeeTemplate) -> EmployeeTemplate:
        """
        Register a new Employee Template and its initial immutable version.
        """
        now = time.time()
        template.created_at = now
        template.updated_at = now
        template.version_hash = template.calculate_version_hash()
        template.template_signature = template.sign()

        version_id = f"tv_{uuid.uuid4().hex[:12]}"
        spec_json = json.dumps(template.to_dict())

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO employee_templates (
                template_id, tenant_id, company_id, project_id, name,
                latest_version, template_type, status, department, job_family,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.template_id, template.tenant_id, template.company_id,
                template.project_id, template.name, template.version,
                template.template_type, template.status, template.department,
                template.job_family, now, now
            ))

            conn.execute("""
            INSERT INTO employee_template_versions (
                version_id, template_id, tenant_id, company_id, version,
                status, version_hash, signature, specification, created_by,
                approved_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, template.template_id, template.tenant_id,
                template.company_id, template.version, template.status,
                template.version_hash, template.template_signature,
                spec_json, template.created_by, template.approved_by, now
            ))

        evidence_service.record_event(
            tenant_id=template.tenant_id,
            company_id=template.company_id,
            event_type="EMPLOYEE_TEMPLATE_CREATED",
            payload={
                "template_id": template.template_id,
                "name": template.name,
                "version": template.version,
                "type": template.template_type,
                "version_hash": template.version_hash
            }
        )
        return template

    def create_version(self, template_id: str, new_template: EmployeeTemplate, actor: str) -> EmployeeTemplate:
        """
        Immutably publish a new version of an existing template without mutating prior versions.
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            row = conn.execute(
                "SELECT * FROM employee_templates WHERE template_id = ?",
                (template_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Template {template_id} does not exist.")

        now = time.time()
        new_template.template_id = template_id
        new_template.created_at = now
        new_template.updated_at = now
        new_template.created_by = actor
        new_template.version_hash = new_template.calculate_version_hash()
        new_template.template_signature = new_template.sign()

        version_id = f"tv_{uuid.uuid4().hex[:12]}"
        spec_json = json.dumps(new_template.to_dict())

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO employee_template_versions (
                version_id, template_id, tenant_id, company_id, version,
                status, version_hash, signature, specification, created_by,
                approved_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, template_id, new_template.tenant_id,
                new_template.company_id, new_template.version, new_template.status,
                new_template.version_hash, new_template.template_signature,
                spec_json, actor, new_template.approved_by, now
            ))

            conn.execute("""
            UPDATE employee_templates
            SET latest_version = ?, status = ?, updated_at = ?
            WHERE template_id = ?
            """, (new_template.version, new_template.status, now, template_id))

        evidence_service.record_event(
            tenant_id=new_template.tenant_id,
            company_id=new_template.company_id,
            event_type="EMPLOYEE_TEMPLATE_VERSION_CREATED",
            payload={
                "template_id": template_id,
                "new_version": new_template.version,
                "actor": actor,
                "version_hash": new_template.version_hash
            }
        )
        return new_template

    def get_template(self, template_id: str, version: Optional[str] = None) -> Optional[EmployeeTemplate]:
        """Fetch template, optionally specifying version (defaults to latest)."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            if version:
                row = conn.execute("""
                SELECT specification FROM employee_template_versions
                WHERE template_id = ? AND version = ?
                """, (template_id, version)).fetchone()
            else:
                row = conn.execute("""
                SELECT v.specification FROM employee_template_versions v
                JOIN employee_templates t ON v.template_id = t.template_id AND v.version = t.latest_version
                WHERE t.template_id = ?
                """, (template_id,)).fetchone()

        if not row:
            return None
        data = json.loads(row["specification"])
        return EmployeeTemplate(**data)

    def list_templates(self, tenant_id: str, company_id: Optional[str] = None, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List templates matching tenant and optional company/type filters."""
        query = "SELECT * FROM employee_templates WHERE tenant_id = ?"
        params = [tenant_id]
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        if template_type:
            query += " AND template_type = ?"
            params.append(template_type)

        with engine.connection(workload=WorkloadType.READ) as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def approve_template(self, template_id: str, version: str, approver: str) -> bool:
        """Promote template version to APPROVED status."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            cursor = conn.execute("""
            UPDATE employee_template_versions
            SET status = 'APPROVED', approved_by = ?
            WHERE template_id = ? AND version = ?
            """, (approver, template_id, version))
            if cursor.rowcount == 0:
                return False

            conn.execute("""
            UPDATE employee_templates
            SET status = 'APPROVED', updated_at = ?
            WHERE template_id = ? AND latest_version = ?
            """, (now, template_id, version))

        return True

employee_template_registry = EmployeeTemplateRegistry()
