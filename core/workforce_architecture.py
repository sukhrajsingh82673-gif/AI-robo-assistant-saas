"""
URA / ZONATA — Enterprise AI Corporate Workforce Architecture
=============================================================

This module is the *service and lifecycle layer* for the 25-table corporate
workforce schema that already exists in ``core/db.py``. It does not introduce a
second hierarchy, a second policy engine or a second agent registry.

Separation of concerns (enforced here):

    AI Employee  -> owns a position, responsibilities, authority, KRA/KPI and outcomes
    AI Agent     -> a reusable execution capability, provisioned per task
    AI Coworker  -> computer-operation capability (``core.coworker``), not an employee

Everything is tenant- and company-scoped. Every mutating operation is
authority-checked and sealed in the tenant evidence ledger. Nothing here calls a
language model: hierarchy, authority, scoring and quotas are deterministic so
they are reproducible and testable.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.db import db
from core.evidence_ledger import EvidenceLedger
from core.models import PhysicalVerification

# ---------------------------------------------------------------------------
# Organizational catalogs
# ---------------------------------------------------------------------------

# Grade -> (authority tier, single-spend limit USD, monthly limit USD,
#           can_hire, can_delegate, can_modify_sops)
GRADE_AUTHORITY: Dict[str, Dict[str, Any]] = {
    "G1": {"tier": "OWNER", "single": 1_000_000, "monthly": 5_000_000,
           "can_hire": True, "can_delegate": True, "can_modify_sops": True},
    "G2": {"tier": "EXECUTIVE", "single": 250_000, "monthly": 1_000_000,
           "can_hire": True, "can_delegate": True, "can_modify_sops": True},
    "G3": {"tier": "EXECUTIVE", "single": 100_000, "monthly": 400_000,
           "can_hire": True, "can_delegate": True, "can_modify_sops": True},
    "G4": {"tier": "MANAGER", "single": 25_000, "monthly": 100_000,
           "can_hire": False, "can_delegate": True, "can_modify_sops": True},
    "G5": {"tier": "MANAGER", "single": 10_000, "monthly": 50_000,
           "can_hire": False, "can_delegate": True, "can_modify_sops": False},
    "G6": {"tier": "MANAGER", "single": 2_500, "monthly": 15_000,
           "can_hire": False, "can_delegate": True, "can_modify_sops": False},
    "G7": {"tier": "EMPLOYEE", "single": 500, "monthly": 5_000,
           "can_hire": False, "can_delegate": False, "can_modify_sops": False},
    "G8": {"tier": "EMPLOYEE", "single": 250, "monthly": 2_500,
           "can_hire": False, "can_delegate": False, "can_modify_sops": False},
    "G9": {"tier": "EMPLOYEE", "single": 100, "monthly": 1_000,
           "can_hire": False, "can_delegate": False, "can_modify_sops": False},
}

TIER_RANK = {"EMPLOYEE": 0, "MANAGER": 1, "EXECUTIVE": 2, "OWNER": 3}

# C-suite catalog. Configurable: additional executives can be created with
# create_position(); this is the default corporate leadership set.
EXECUTIVE_CATALOG: List[Dict[str, Any]] = [
    {"code": "CEO", "title": "Chief Executive Officer", "dept": "EXEC", "grade": "G1",
     "role": "Corporate strategy, capital allocation and enterprise outcomes",
     "kras": ["Company growth", "Capital efficiency", "Strategic execution"],
     "capabilities": ["corporate_intelligence", "decision_support"]},
    {"code": "COO", "title": "Chief Operating Officer", "dept": "OPS", "grade": "G2",
     "role": "Operations, process quality, capacity and service delivery",
     "kras": ["Operational throughput", "SLA completion", "Unit cost"],
     "capabilities": ["workflow_analysis", "process_automation", "report_generation"]},
    {"code": "CFO", "title": "Chief Financial Officer", "dept": "FIN", "grade": "G2",
     "role": "Financial planning, controls, treasury and reporting",
     "kras": ["Budget variance", "Cash runway", "Close accuracy"],
     "capabilities": ["financial_analysis", "reconciliation", "report_generation"]},
    {"code": "CTO", "title": "Chief Technology Officer", "dept": "TECH", "grade": "G2",
     "role": "Technology strategy, engineering quality and platform reliability",
     "kras": ["Release reliability", "Engineering velocity", "Security defects"],
     "capabilities": ["code_analysis", "repository_research", "testing", "terminal_execution"]},
    {"code": "CMO", "title": "Chief Marketing Officer", "dept": "MKT", "grade": "G2",
     "role": "Marketing strategy, brand, organic and paid acquisition",
     "kras": ["Qualified pipeline contribution", "CAC efficiency", "Organic visibility"],
     "capabilities": ["seo_research", "content_analysis", "campaign_analytics", "web_browsing"]},
    {"code": "CSO", "title": "Chief Sales Officer", "dept": "SALES", "grade": "G2",
     "role": "Revenue strategy, pipeline, conversion and deal governance",
     "kras": ["Verified revenue", "Win rate", "Sales cycle time"],
     "capabilities": ["lead_discovery", "lead_verification", "proposal_preparation", "crm_updates"]},
    {"code": "CHRO", "title": "Chief Human Resources Officer", "dept": "HR", "grade": "G2",
     "role": "Organizational design, workforce planning, SOP/KPI governance",
     "kras": ["Workforce utilisation", "SOP compliance", "Performance coverage"],
     "capabilities": ["workforce_analytics", "report_generation"]},
    {"code": "CPO", "title": "Chief Product Officer", "dept": "PROD", "grade": "G2",
     "role": "Product strategy, roadmap and product quality",
     "kras": ["Adoption", "Roadmap delivery", "Product quality"],
     "capabilities": ["document_research", "data_analysis", "report_generation"]},
    {"code": "CLO", "title": "Chief Legal & Compliance Officer", "dept": "LEGAL", "grade": "G2",
     "role": "Regulatory compliance, contracts and legal risk",
     "kras": ["Compliance findings closed", "Contract cycle time", "Policy exceptions"],
     "capabilities": ["document_research", "compliance_review"]},
    {"code": "CRO", "title": "Chief Risk Officer", "dept": "RISK", "grade": "G2",
     "role": "Enterprise risk, controls and incident governance",
     "kras": ["Risk register coverage", "Control effectiveness", "Incident recurrence"],
     "capabilities": ["data_analysis", "compliance_review", "report_generation"]},
    {"code": "CISO", "title": "Chief Information Security Officer", "dept": "SEC", "grade": "G2",
     "role": "Security architecture, identity and threat response",
     "kras": ["Critical findings remediated", "Mean time to detect", "Access review completion"],
     "capabilities": ["code_analysis", "log_analysis", "compliance_review"]},
    {"code": "CDO", "title": "Chief Data Officer", "dept": "DATA", "grade": "G2",
     "role": "Data platform, governance, quality and analytics",
     "kras": ["Data quality", "Pipeline freshness", "Governed access"],
     "capabilities": ["data_analysis", "report_generation", "knowledge_retrieval"]},
    {"code": "CKO", "title": "Chief Knowledge Officer", "dept": "KNOW", "grade": "G2",
     "role": "Corporate knowledge, SOP library and institutional memory",
     "kras": ["Knowledge coverage", "SOP currency", "Retrieval accuracy"],
     "capabilities": ["knowledge_retrieval", "document_research", "report_generation"]},
]

# Base departments are created for every organization; industry blueprints add
# or extend them. All are data, not branches in code.
BASE_DEPARTMENTS: List[Dict[str, Any]] = [
    {"code": "EXEC", "name": "Executive Office", "parent": None, "positions": []},
    {"code": "OPS", "name": "Operations", "parent": "EXEC", "positions": [
        ("Operations Director", "G3"), ("Operations Manager", "G5"),
        ("Process Supervisor", "G6"), ("Operations Specialist", "G8")]},
    {"code": "FIN", "name": "Finance", "parent": "EXEC", "positions": [
        ("Finance Director", "G3"), ("Financial Controller", "G4"),
        ("Accounting Manager", "G5"), ("Financial Analyst", "G8"),
        ("Reconciliation Specialist", "G8")]},
    {"code": "HR", "name": "Human Resources", "parent": "EXEC", "positions": [
        ("Talent Director", "G3"), ("Recruitment Manager", "G5"),
        ("Workforce Planning Specialist", "G7"), ("Performance Analyst", "G8")]},
    {"code": "TECH", "name": "Technology", "parent": "EXEC", "positions": [
        ("Engineering Director", "G3"), ("Engineering Manager", "G5"),
        ("Technical Lead", "G6"), ("Software Engineer", "G8"), ("QA Engineer", "G8")]},
    {"code": "LEGAL", "name": "Legal & Compliance", "parent": "EXEC", "positions": [
        ("Legal Director", "G3"), ("Compliance Manager", "G5"), ("Compliance Analyst", "G8")]},
    {"code": "RISK", "name": "Risk Management", "parent": "EXEC", "positions": [
        ("Risk Director", "G3"), ("Risk Manager", "G5"), ("Risk Analyst", "G8")]},
    {"code": "SEC", "name": "Information Security", "parent": "TECH", "positions": [
        ("Security Director", "G3"), ("Security Manager", "G5"), ("Security Engineer", "G8")]},
    {"code": "DATA", "name": "Data & Analytics", "parent": "TECH", "positions": [
        ("Data Director", "G3"), ("Data Manager", "G5"), ("Data Analyst", "G8")]},
    {"code": "KNOW", "name": "Knowledge & Intelligence", "parent": "EXEC", "positions": [
        ("Knowledge Director", "G3"), ("Knowledge Manager", "G5"), ("Research Analyst", "G8")]},
    # Commercial departments exist in every industry so the whole C-suite has a
    # home. Industry blueprints replace these entries with sector-specific roles.
    {"code": "MKT", "name": "Marketing", "parent": "EXEC", "positions": [
        ("Marketing Director", "G3"), ("Marketing Manager", "G5"),
        ("SEO Specialist", "G8"), ("Content Researcher", "G8")]},
    {"code": "SALES", "name": "Sales", "parent": "EXEC", "positions": [
        ("Sales Director", "G3"), ("Sales Manager", "G5"), ("Account Executive", "G7")]},
    {"code": "PROD", "name": "Product", "parent": "EXEC", "positions": [
        ("Product Director", "G3"), ("Product Manager", "G5"), ("Product Analyst", "G8")]},
    {"code": "CS", "name": "Customer Success", "parent": "EXEC", "positions": [
        ("Customer Success Manager", "G5"), ("Support Specialist", "G8")]},
]

INDUSTRY_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "saas": {"label": "SaaS / Software", "departments": [
        {"code": "PROD", "name": "Product", "parent": "EXEC", "positions": [
            ("Product Director", "G3"), ("Product Manager", "G5"),
            ("UX Researcher", "G7"), ("Product Analyst", "G8")]},
        {"code": "MKT", "name": "Marketing", "parent": "EXEC", "positions": [
            ("Marketing Director", "G3"), ("Digital Marketing Manager", "G5"),
            ("SEO Manager", "G6"), ("SEO Specialist", "G8"), ("Content Researcher", "G8")]},
        {"code": "SALES", "name": "Sales", "parent": "EXEC", "positions": [
            ("Sales Director", "G3"), ("Sales Manager", "G5"),
            ("Lead Generation Supervisor", "G6"), ("Lead Research Specialist", "G8"),
            ("Account Executive", "G7")]},
        {"code": "CS", "name": "Customer Success", "parent": "EXEC", "positions": [
            ("Customer Success Director", "G3"), ("CS Manager", "G5"),
            ("Support Specialist", "G8")]},
    ]},
    "ecommerce": {"label": "E-commerce / Retail", "departments": [
        {"code": "MKT", "name": "Marketing", "parent": "EXEC", "positions": [
            ("Marketing Director", "G3"), ("Performance Marketing Manager", "G5"),
            ("SEO Specialist", "G8"), ("Content Researcher", "G8")]},
        {"code": "SALES", "name": "Sales & Merchandising", "parent": "EXEC", "positions": [
            ("Sales Director", "G3"), ("Category Manager", "G5"),
            ("Merchandising Analyst", "G8")]},
        {"code": "SCM", "name": "Supply Chain", "parent": "OPS", "positions": [
            ("Supply Chain Manager", "G5"), ("Inventory Analyst", "G8"),
            ("Logistics Coordinator", "G9")]},
        {"code": "CS", "name": "Customer Support", "parent": "EXEC", "positions": [
            ("Support Manager", "G5"), ("Support Specialist", "G8")]},
    ]},
    "professional_services": {"label": "Professional Services", "departments": [
        {"code": "DEL", "name": "Delivery", "parent": "OPS", "positions": [
            ("Delivery Director", "G3"), ("Engagement Manager", "G5"),
            ("Consultant", "G7"), ("Delivery Analyst", "G8")]},
        {"code": "SALES", "name": "Business Development", "parent": "EXEC", "positions": [
            ("BD Director", "G3"), ("BD Manager", "G5"), ("Proposal Specialist", "G8")]},
        {"code": "MKT", "name": "Marketing", "parent": "EXEC", "positions": [
            ("Marketing Manager", "G5"), ("Content Researcher", "G8")]},
    ]},
    "manufacturing": {"label": "Manufacturing", "departments": [
        {"code": "PLANT", "name": "Plant Operations", "parent": "OPS", "positions": [
            ("Plant Director", "G3"), ("Production Manager", "G5"),
            ("Shift Supervisor", "G6"), ("Production Operator", "G9")]},
        {"code": "QA", "name": "Quality Assurance", "parent": "OPS", "positions": [
            ("Quality Manager", "G5"), ("Quality Inspector", "G8")]},
        {"code": "SCM", "name": "Procurement & Supply Chain", "parent": "EXEC", "positions": [
            ("Procurement Director", "G3"), ("Procurement Manager", "G5"),
            ("Supply Analyst", "G8")]},
        {"code": "HSE", "name": "Health, Safety & Environment", "parent": "OPS", "positions": [
            ("HSE Manager", "G5"), ("HSE Officer", "G8")]},
    ]},
    "healthcare": {"label": "Healthcare", "departments": [
        {"code": "CLIN", "name": "Clinical Operations", "parent": "OPS", "positions": [
            ("Clinical Director", "G3"), ("Clinical Manager", "G5"),
            ("Care Coordinator", "G8")]},
        {"code": "QA", "name": "Quality & Patient Safety", "parent": "OPS", "positions": [
            ("Quality Manager", "G5"), ("Patient Safety Analyst", "G8")]},
        {"code": "COMP", "name": "Regulatory Compliance", "parent": "LEGAL", "positions": [
            ("Compliance Manager", "G5"), ("Compliance Analyst", "G8")]},
    ]},
    "financial_services": {"label": "Financial Services", "departments": [
        {"code": "CRED", "name": "Credit & Lending", "parent": "OPS", "positions": [
            ("Credit Director", "G3"), ("Credit Manager", "G5"), ("Credit Analyst", "G8")]},
        {"code": "TREAS", "name": "Treasury", "parent": "FIN", "positions": [
            ("Treasury Manager", "G5"), ("Treasury Analyst", "G8")]},
        {"code": "COMP", "name": "Financial Compliance", "parent": "LEGAL", "positions": [
            ("Compliance Manager", "G5"), ("KYC Analyst", "G8")]},
        {"code": "SALES", "name": "Relationship Management", "parent": "EXEC", "positions": [
            ("Relationship Director", "G3"), ("Relationship Manager", "G5")]},
    ]},
    "education": {"label": "Education", "departments": [
        {"code": "ACAD", "name": "Academic Operations", "parent": "OPS", "positions": [
            ("Academic Director", "G3"), ("Program Manager", "G5"),
            ("Curriculum Specialist", "G7"), ("Instructor", "G8")]},
        {"code": "ADM", "name": "Admissions", "parent": "EXEC", "positions": [
            ("Admissions Manager", "G5"), ("Admissions Counselor", "G8")]},
        {"code": "QA", "name": "Academic Quality", "parent": "OPS", "positions": [
            ("Quality Manager", "G5"), ("Assessment Analyst", "G8")]},
    ]},
    "logistics": {"label": "Logistics & Transport", "departments": [
        {"code": "FLEET", "name": "Fleet Operations", "parent": "OPS", "positions": [
            ("Fleet Director", "G3"), ("Fleet Manager", "G5"),
            ("Dispatch Supervisor", "G6"), ("Dispatch Coordinator", "G9")]},
        {"code": "WH", "name": "Warehousing", "parent": "OPS", "positions": [
            ("Warehouse Manager", "G5"), ("Inventory Analyst", "G8")]},
        {"code": "SCM", "name": "Network Planning", "parent": "OPS", "positions": [
            ("Network Planning Manager", "G5"), ("Route Analyst", "G8")]},
    ]},
    "media": {"label": "Media & Publishing", "departments": [
        {"code": "EDIT", "name": "Editorial", "parent": "OPS", "positions": [
            ("Editorial Director", "G3"), ("Managing Editor", "G5"),
            ("Staff Writer", "G8"), ("Fact Checker", "G8")]},
        {"code": "MKT", "name": "Audience & Marketing", "parent": "EXEC", "positions": [
            ("Audience Director", "G3"), ("Growth Manager", "G5"),
            ("SEO Specialist", "G8")]},
        {"code": "SALES", "name": "Advertising Sales", "parent": "EXEC", "positions": [
            ("Ad Sales Director", "G3"), ("Ad Sales Manager", "G5")]},
    ]},
    "real_estate": {"label": "Real Estate", "departments": [
        {"code": "PROP", "name": "Property Operations", "parent": "OPS", "positions": [
            ("Property Director", "G3"), ("Property Manager", "G5"),
            ("Facilities Coordinator", "G9")]},
        {"code": "LEAS", "name": "Leasing & Sales", "parent": "EXEC", "positions": [
            ("Leasing Director", "G3"), ("Leasing Manager", "G5"),
            ("Leasing Agent", "G8")]},
        {"code": "DEV", "name": "Development", "parent": "OPS", "positions": [
            ("Development Manager", "G5"), ("Project Coordinator", "G9")]},
    ]},
    "insurance": {"label": "Insurance", "departments": [
        {"code": "UNDW", "name": "Underwriting", "parent": "OPS", "positions": [
            ("Underwriting Director", "G3"), ("Underwriting Manager", "G5"),
            ("Underwriting Analyst", "G8")]},
        {"code": "CLM", "name": "Claims", "parent": "OPS", "positions": [
            ("Claims Director", "G3"), ("Claims Manager", "G5"),
            ("Claims Adjuster", "G8")]},
        {"code": "ACT", "name": "Actuarial", "parent": "FIN", "positions": [
            ("Chief Actuary", "G4"), ("Actuarial Analyst", "G8")]},
        {"code": "COMP", "name": "Insurance Compliance", "parent": "LEGAL", "positions": [
            ("Compliance Manager", "G5"), ("Policy Auditor", "G8")]},
    ]},
    "energy_utilities": {"label": "Energy & Utilities", "departments": [
        {"code": "GRID", "name": "Grid Operations", "parent": "OPS", "positions": [
            ("Grid Director", "G3"), ("Grid Manager", "G5"),
            ("Control Room Supervisor", "G6"), ("Grid Operator", "G9")]},
        {"code": "HSE", "name": "Health, Safety & Environment", "parent": "OPS", "positions": [
            ("HSE Director", "G3"), ("HSE Manager", "G5"), ("HSE Officer", "G8")]},
        {"code": "ASSET", "name": "Asset Management", "parent": "OPS", "positions": [
            ("Asset Manager", "G5"), ("Maintenance Planner", "G8")]},
        {"code": "REG", "name": "Regulatory Affairs", "parent": "LEGAL", "positions": [
            ("Regulatory Manager", "G5"), ("Regulatory Analyst", "G8")]},
    ]},
    "hospitality": {"label": "Hospitality & Tourism", "departments": [
        {"code": "HOTEL", "name": "Hotel Operations", "parent": "OPS", "positions": [
            ("Hotel Director", "G3"), ("Hotel Manager", "G5"),
            ("Front Office Supervisor", "G6"), ("Guest Services Agent", "G9")]},
        {"code": "FNB", "name": "Food & Beverage", "parent": "OPS", "positions": [
            ("F&B Manager", "G5"), ("Kitchen Supervisor", "G6")]},
        {"code": "REV", "name": "Revenue Management", "parent": "FIN", "positions": [
            ("Revenue Manager", "G5"), ("Revenue Analyst", "G8")]},
        {"code": "GUEST", "name": "Guest Experience", "parent": "EXEC", "positions": [
            ("Guest Experience Manager", "G5"), ("Guest Relations Specialist", "G8")]},
    ]},
    "telecommunications": {"label": "Telecommunications", "departments": [
        {"code": "NET", "name": "Network Operations", "parent": "OPS", "positions": [
            ("Network Director", "G3"), ("Network Manager", "G5"),
            ("NOC Supervisor", "G6"), ("NOC Engineer", "G8")]},
        {"code": "FIELD", "name": "Field Engineering", "parent": "OPS", "positions": [
            ("Field Operations Manager", "G5"), ("Field Technician", "G8")]},
        {"code": "SUB", "name": "Subscriber Operations", "parent": "EXEC", "positions": [
            ("Subscriber Director", "G3"), ("Subscriber Manager", "G5"),
            ("Billing Analyst", "G8")]},
        {"code": "REG", "name": "Regulatory & Spectrum", "parent": "LEGAL", "positions": [
            ("Regulatory Manager", "G5"), ("Spectrum Analyst", "G8")]},
    ]},
    "agriculture": {"label": "Agriculture & Agribusiness", "departments": [
        {"code": "FARM", "name": "Farm Operations", "parent": "OPS", "positions": [
            ("Farm Director", "G3"), ("Farm Manager", "G5"),
            ("Field Supervisor", "G6"), ("Farm Operator", "G9")]},
        {"code": "QUAL", "name": "Quality & Food Safety", "parent": "OPS", "positions": [
            ("Quality Manager", "G5"), ("Food Safety Analyst", "G8")]},
        {"code": "SCM", "name": "Procurement & Supply Chain", "parent": "EXEC", "positions": [
            ("Procurement Director", "G3"), ("Procurement Manager", "G5"),
            ("Supply Analyst", "G8")]},
        {"code": "AGRI", "name": "Agronomy", "parent": "OPS", "positions": [
            ("Chief Agronomist", "G4"), ("Agronomy Analyst", "G8")]},
    ]},
}

POSITION_CATEGORIES = [
    "EXECUTIVE", "VP", "DIRECTOR", "HEAD", "SENIOR_MANAGER", "MANAGER",
    "TEAM_LEAD", "SUPERVISOR", "SPECIALIST", "ANALYST", "COORDINATOR", "OPERATOR",
]


def _now() -> float:
    return time.time()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _tier_for_grade(grade: str) -> str:
    return GRADE_AUTHORITY.get(grade, GRADE_AUTHORITY["G9"])["tier"]


class WorkforceError(ValueError):
    """Raised when a workforce operation violates an architectural invariant."""


# A database is reconciled at most once per process per database file. Schema
# reconciliation runs the additive migrations in ``Database._init_db``.
_SCHEMA_RECONCILED: set = set()


class WorkforceArchitecture:
    """Governed corporate organization, employee, SOP, KPI and agent lifecycle."""

    VERSION = "1.0.0"
    DEFAULT_AGENT_QUOTA = 4

    def __init__(self, tenant_id: str, company_id: str,
                 ledger: Optional[EvidenceLedger] = None):
        if not tenant_id or not company_id:
            raise WorkforceError("tenant_id and company_id are required.")
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._ensure_schema()
        self.ledger = ledger or self._tenant_ledger()

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        """Self-heal databases created before the workforce schema shipped.

        Older pilot databases contain an ``employee_kras`` table created by the
        V7 KPI engine and an ``organizations`` table without ``company_id``. The
        probes below check the exact columns this service writes, so a drifted
        database is reconciled before the first operation instead of failing
        halfway through a transaction.
        """
        key = (str(getattr(db, "dialect", "")), str(getattr(db, "db_path", "")))
        if key in _SCHEMA_RECONCILED:
            return
        try:
            with db.get_connection() as conn:
                conn.execute("SELECT 1 FROM corporate_employees LIMIT 1")
                conn.execute("SELECT 1 FROM agent_instances LIMIT 1")
                conn.execute("SELECT 1 FROM cross_department_collaborations LIMIT 1")
                conn.execute("SELECT weight_percentage, position_id, "
                             "accountability_statement, updated_at "
                             "FROM employee_kras LIMIT 1")
                conn.execute("SELECT company_id FROM organizations LIMIT 1")
        except Exception:
            try:
                db._init_db()
            except Exception:
                pass
        _SCHEMA_RECONCILED.add(key)

    def _tenant_ledger(self) -> EvidenceLedger:
        try:
            from core.tenancy import get_ledger
            return get_ledger(self.tenant_id)
        except Exception:
            return EvidenceLedger()

    def _seal(self, *, action: str, subject: str, expected: str, actual: str,
              verified: bool, details: str,
              extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            package = self.ledger.seal_evidence(
                action_id=_id("act_wf"),
                mission_id=_id("mis_wf"),
                agent_id="workforce_architecture",
                verifications=[PhysicalVerification(
                    check_type="workforce_contract",
                    target_path=subject,
                    expected_val=expected,
                    actual_val=actual,
                    verified=verified,
                    details=details,
                )],
                metadata={
                    "tenant_id": self.tenant_id,
                    "company_id": self.company_id,
                    "engine": "workforce_architecture",
                    "engine_version": self.VERSION,
                    "action": action,
                    **(extra or {}),
                },
            )
            return {
                "evidence_id": package.evidence_id,
                "evidence_status": getattr(package.status, "value", str(package.status)),
                "sha256_digest": package.sha256_digest,
            }
        except Exception as exc:  # evidence must never mask the operation result
            return {"evidence_id": None, "evidence_status": "SEAL_FAILED",
                    "error": str(exc)[:200]}

    def _conn(self):
        return db.get_connection()

    # ------------------------------------------------------------------
    # Catalogs
    # ------------------------------------------------------------------
    @staticmethod
    def list_executives() -> List[Dict[str, Any]]:
        return [dict(item) for item in EXECUTIVE_CATALOG]

    @staticmethod
    def list_industries() -> List[Dict[str, Any]]:
        return [
            {"industry": key, "label": value["label"],
             "departments": [d["code"] for d in value["departments"]]}
            for key, value in sorted(INDUSTRY_BLUEPRINTS.items())
        ]

    @staticmethod
    def get_industry_blueprint(industry: str) -> Dict[str, Any]:
        blueprint = INDUSTRY_BLUEPRINTS.get(industry)
        if not blueprint:
            raise WorkforceError(
                f"Unknown industry '{industry}'. Known: {sorted(INDUSTRY_BLUEPRINTS)}"
            )
        return {
            "industry": industry,
            "label": blueprint["label"],
            "base_departments": [dict(d) for d in BASE_DEPARTMENTS],
            "industry_departments": [dict(d) for d in blueprint["departments"]],
        }

    # ------------------------------------------------------------------
    # Organization provisioning
    # ------------------------------------------------------------------
    def provision_organization(
        self,
        *,
        industry: str,
        legal_name: str,
        trade_name: Optional[str] = None,
        created_by: str = "system",
        objectives: Optional[List[str]] = None,
        size_band: str = "mid",
        extra_departments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a complete corporate structure: org, departments, positions,
        executives and their reporting lines."""
        blueprint = self.get_industry_blueprint(industry)
        if size_band not in ("startup", "mid", "enterprise"):
            raise WorkforceError("size_band must be startup, mid or enterprise.")

        org_id = _id("org")
        now = _now()
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT org_id, trade_name FROM organizations WHERE tenant_id = ? "
                "AND company_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, self.company_id),
            ).fetchone()
        if existing:
            raise WorkforceError(
                f"Company '{self.company_id}' already has an active organization "
                f"'{existing['trade_name']}' ({existing['org_id']}). A company has "
                "exactly one enterprise root; add departments to the existing "
                "organization instead of provisioning a second one."
            )

        departments: Dict[str, Dict[str, Any]] = {
            d["code"]: dict(d) for d in blueprint["base_departments"]
        }
        departments["EXEC"]["positions"] = []
        # Industry blueprints replace base departments of the same code with
        # sector-specific roles instead of colliding with them.
        for dept in blueprint["industry_departments"]:
            merged = dict(dept)
            merged["parent"] = dept.get("parent") or "EXEC"
            departments[dept["code"]] = merged
        for extra in (extra_departments or []):
            code = str(extra["code"]).upper()
            departments[code] = {
                "code": code,
                "name": extra["name"],
                "parent": extra.get("parent") or "EXEC",
                "positions": [tuple(p) for p in (extra.get("positions") or [])],
            }
        departments = dict([("EXEC", departments.pop("EXEC"))] + list(departments.items()))

        codes = list(departments.keys())
        if len(codes) != len(set(codes)):
            raise WorkforceError("Duplicate department codes in blueprint.")

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO organizations
                   (org_id, tenant_id, company_id, parent_org_id, legal_name, trade_name,
                    jurisdiction, tax_identifier, incorporation_date, fiscal_year_start_month,
                    base_currency, governance_model, status, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (org_id, self.tenant_id, self.company_id, None, legal_name,
                 trade_name or legal_name,
                 "IN", None, now, 4, "INR", "AUTONOMOUS_EXECUTIVE_HYBRID", "ACTIVE",
                 _json({"industry": industry, "size_band": size_band,
                        "objectives": objectives or []}), now, now),
            )
            conn.commit()

        dept_ids: Dict[str, str] = {}
        for dept in departments.values():
            parent_id = dept_ids.get(dept["parent"]) if dept.get("parent") else None
            dept_ids[dept["code"]] = self._insert_department(
                conn=None, org_id=org_id, code=dept["code"], name=dept["name"],
                parent_id=parent_id, budget_usd=0.0,
                headcount_ceiling={"startup": 6, "mid": 15, "enterprise": 40}[size_band],
                created_by=created_by,
            )

        # Executive positions + employees. The CEO is hired first, then every
        # other C-suite executive reports to the CEO (solid line).
        executives: List[Dict[str, Any]] = []
        exec_position_by_dept: Dict[str, str] = {}
        employee_by_position: Dict[str, str] = {}
        ceo_employee_id: Optional[str] = None

        for item in EXECUTIVE_CATALOG:
            if item["dept"] not in dept_ids:
                continue
            position = self.create_position(
                department_id=dept_ids[item["dept"]],
                title=item["title"],
                grade=item["grade"],
                category="EXECUTIVE",
                job_description=item["role"],
                responsibilities=[item["role"]],
                required_kras=item["kras"],
                permitted_agent_capabilities=item["capabilities"],
                reports_to_position_id=None,
                created_by=created_by,
            )
            employee = self.hire_employee(
                position_id=position["position_id"],
                first_name=item["code"],
                last_name="Executive",
                manager_employee_id=ceo_employee_id,
                created_by=created_by,
                employee_code=f"EMP-{item['code']}-001",
            )
            if item["code"] == "CEO":
                ceo_employee_id = employee["employee_id"]
            exec_position_by_dept[item["dept"]] = position["position_id"]
            employee_by_position[position["position_id"]] = employee["employee_id"]
            executives.append({
                "code": item["code"],
                "employee_id": employee["employee_id"],
                "employee_code": employee["employee_code"],
                "position_id": position["position_id"],
            })

        # Departmental workforce: directors report to their executive, managers
        # to the nearest senior position, specialists to their supervisor.
        for dept in departments.values():
            dept_positions = sorted(dept["positions"], key=lambda p: self._grade_rank(p[1]))
            created: Dict[str, Dict[str, Any]] = {}
            for title, grade in dept_positions:
                senior = [p for p in created.values()
                          if self._grade_rank(p["grade"]) < self._grade_rank(grade)]
                if senior:
                    parent = max(senior, key=lambda p: self._grade_rank(p["grade"]))
                    reports_to_position_id = parent["position_id"]
                    manager_employee_id = employee_by_position[parent["position_id"]]
                elif dept["code"] in exec_position_by_dept:
                    reports_to_position_id = exec_position_by_dept[dept["code"]]
                    manager_employee_id = ceo_employee_id if dept["code"] == "EXEC" else \
                        employee_by_position[reports_to_position_id]
                else:
                    reports_to_position_id = None
                    manager_employee_id = ceo_employee_id
                position = self.create_position(
                    department_id=dept_ids[dept["code"]],
                    title=title,
                    grade=grade,
                    reports_to_position_id=reports_to_position_id,
                    created_by=created_by,
                )
                employee = self.hire_employee(
                    position_id=position["position_id"],
                    first_name=title,
                    last_name="Staff",
                    manager_employee_id=manager_employee_id,
                    created_by=created_by,
                )
                created[title] = position
                employee_by_position[position["position_id"]] = employee["employee_id"]

        with self._conn() as conn:
            conn.execute(
                "UPDATE corporate_departments SET head_position_id = ? "
                "WHERE department_id = ?",
                (exec_position_by_dept.get("EXEC"), dept_ids["EXEC"]),
            )
            conn.commit()

        evidence = self._seal(
            action="PROVISION_ORGANIZATION",
            subject=f"org://{org_id}",
            expected="COMPLETE_HIERARCHY",
            actual=f"{len(dept_ids)} departments, {len(executives)} executives",
            verified=bool(executives) and len(dept_ids) >= 5,
            details=f"Provisioned {legal_name} ({industry}) with {len(dept_ids)} departments.",
            extra={"org_id": org_id, "created_by": created_by},
        )
        return {
            "success": True,
            "org_id": org_id,
            "industry": industry,
            "departments": len(dept_ids),
            "executives": executives,
            "ceo_employee_id": ceo_employee_id,
            "evidence": evidence,
        }

    # ------------------------------------------------------------------
    # Departments and positions
    # ------------------------------------------------------------------
    def _insert_department(self, *, conn, org_id: str, code: str, name: str,
                           parent_id: Optional[str], budget_usd: float,
                           headcount_ceiling: int, created_by: str) -> str:
        department_id = _id("dept")
        now = _now()
        with self._conn() as c:
            c.execute(
                """INSERT INTO corporate_departments
                   (department_id, tenant_id, company_id, parent_department_id, code,
                    name, cost_center_code, head_position_id, operating_budget_usd,
                    headcount_ceiling, current_headcount, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (department_id, self.tenant_id, self.company_id, parent_id, code,
                 name, f"CC-{code}-{self.company_id[-4:]}", None, float(budget_usd),
                 int(headcount_ceiling), 0, "ACTIVE", now, now),
            )
            c.commit()
        return department_id

    def create_department(self, *, code: str, name: str, parent_department_id: Optional[str] = None,
                          budget_usd: float = 0.0, headcount_ceiling: int = 10,
                          created_by: str = "system") -> Dict[str, Any]:
        code = code.strip().upper()
        if not code or not name.strip():
            raise WorkforceError("Department code and name are required.")
        if budget_usd < 0 or headcount_ceiling < 1:
            raise WorkforceError("budget_usd must be >= 0 and headcount_ceiling >= 1.")
        with self._conn() as conn:
            parent = None
            if parent_department_id:
                parent = conn.execute(
                    "SELECT department_id FROM corporate_departments "
                    "WHERE department_id = ? AND tenant_id = ? AND company_id = ?",
                    (parent_department_id, self.tenant_id, self.company_id),
                ).fetchone()
                if not parent:
                    raise WorkforceError("Parent department not found in this company.")
            existing = conn.execute(
                "SELECT department_id FROM corporate_departments "
                "WHERE company_id = ? AND code = ?",
                (self.company_id, code),
            ).fetchone()
            if existing:
                raise WorkforceError(f"Department code '{code}' already exists.")
        department_id = self._insert_department(
            conn=None, org_id="", code=code, name=name.strip(),
            parent_id=parent_department_id, budget_usd=budget_usd,
            headcount_ceiling=headcount_ceiling, created_by=created_by,
        )
        return {"success": True, "department_id": department_id, "code": code,
                "name": name.strip(), "parent_department_id": parent_department_id}

    def list_departments(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM corporate_departments WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY code",
                (self.tenant_id, self.company_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_position(self, *, department_id: str, title: str, grade: str,
                        category: Optional[str] = None,
                        job_description: str = "",
                        responsibilities: Optional[List[str]] = None,
                        required_skills: Optional[List[str]] = None,
                        required_kras: Optional[List[str]] = None,
                        permitted_agent_capabilities: Optional[List[str]] = None,
                        reports_to_position_id: Optional[str] = None,
                        headcount_limit: int = 1,
                        created_by: str = "system") -> Dict[str, Any]:
        if grade not in GRADE_AUTHORITY:
            raise WorkforceError(f"Unknown grade '{grade}'. Known: {sorted(GRADE_AUTHORITY)}")
        title = title.strip()
        if not title:
            raise WorkforceError("Position title is required.")
        category = (category or self._category_for_grade(grade)).upper()
        if category not in POSITION_CATEGORIES:
            raise WorkforceError(f"Unknown position category '{category}'.")

        with self._conn() as conn:
            dept = conn.execute(
                "SELECT department_id FROM corporate_departments "
                "WHERE department_id = ? AND tenant_id = ? AND company_id = ?",
                (department_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not dept:
                raise WorkforceError("Department not found in this company.")
            if reports_to_position_id:
                parent = conn.execute(
                    "SELECT position_id, hierarchy_level FROM corporate_positions "
                    "WHERE position_id = ? AND tenant_id = ? AND company_id = ?",
                    (reports_to_position_id, self.tenant_id, self.company_id),
                ).fetchone()
                if not parent:
                    raise WorkforceError("Reporting position not found in this company.")
                if self._grade_rank(grade) < self._grade_rank(parent["hierarchy_level"]):
                    raise WorkforceError(
                        "A position cannot report to a more junior position "
                        f"({grade} -> {parent['hierarchy_level']})."
                    )
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM corporate_positions "
                "WHERE company_id = ? AND department_id = ?",
                (self.company_id, department_id),
            ).fetchone()["n"]
            position_code = f"POS-{uuid.uuid4().hex[:8].upper()}"

        authority = GRADE_AUTHORITY[grade]
        position_id = _id("pos")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO corporate_positions
                   (position_id, tenant_id, company_id, department_id,
                    reports_to_position_id, position_code, title, hierarchy_level,
                    job_family, headcount_limit, current_filled_count,
                    default_authority_profile_id, is_executive, is_active,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (position_id, self.tenant_id, self.company_id, department_id,
                 reports_to_position_id, position_code, title, grade,
                 category, int(headcount_limit), 0, None,
                 1 if authority["tier"] in ("EXECUTIVE", "OWNER") else 0, 1, now, now),
            )
            conn.commit()

        profile = self._ensure_authority_profile(
            name=f"{title} ({grade})",
            tier=authority["tier"],
            max_single=authority["single"],
            max_monthly=authority["monthly"],
            can_hire=authority["can_hire"],
            can_delegate=authority["can_delegate"],
            can_modify_sops=authority["can_modify_sops"],
        )
        with self._conn() as conn:
            conn.execute(
                "UPDATE corporate_positions SET default_authority_profile_id = ? "
                "WHERE position_id = ?",
                (profile["profile_id"], position_id),
            )
            conn.commit()

        return {
            "success": True,
            "position_id": position_id,
            "position_code": position_code,
            "title": title,
            "grade": grade,
            "category": category,
            "department_id": department_id,
            "job_description": job_description,
            "responsibilities": responsibilities or [],
            "required_skills": required_skills or [],
            "required_kras": required_kras or [],
            "permitted_agent_capabilities": permitted_agent_capabilities or [],
            "authority_profile_id": profile["profile_id"],
            "authority": profile,
            "reports_to_position_id": reports_to_position_id,
        }

    @staticmethod
    def _grade_rank(grade: str) -> int:
        try:
            return int(str(grade).lstrip("G"))
        except ValueError:
            return 99

    @staticmethod
    def _category_for_grade(grade: str) -> str:
        return {
            "G1": "EXECUTIVE", "G2": "EXECUTIVE", "G3": "DIRECTOR",
            "G4": "HEAD", "G5": "MANAGER", "G6": "SUPERVISOR",
            "G7": "SPECIALIST", "G8": "ANALYST", "G9": "COORDINATOR",
        }.get(grade, "SPECIALIST")

    def list_positions(self, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = ("SELECT * FROM corporate_positions WHERE tenant_id = ? AND company_id = ?")
        params: List[Any] = [self.tenant_id, self.company_id]
        if department_id:
            sql += " AND department_id = ?"
            params.append(department_id)
        sql += " ORDER BY hierarchy_level, title"
        with self._conn() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def _ensure_authority_profile(self, *, name: str, tier: str, max_single: float,
                                  max_monthly: float, can_hire: bool,
                                  can_delegate: bool, can_modify_sops: bool) -> Dict[str, Any]:
        signature = hashlib.sha256(
            _json([self.tenant_id, self.company_id, name, tier, max_single,
                   max_monthly, can_hire, can_delegate, can_modify_sops]).encode()
        ).hexdigest()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM employee_authority_profiles WHERE signature_hash = ? "
                "AND tenant_id = ? AND company_id = ?",
                (signature, self.tenant_id, self.company_id),
            ).fetchone()
            if row:
                item = dict(row)
                item["tier"] = tier
                return item
        profile_id = _id("auth")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO employee_authority_profiles
                   (profile_id, tenant_id, company_id, name, max_spend_single_usd,
                    max_spend_monthly_usd, max_risk_level, can_hire, can_fire,
                    can_enter_contracts, can_delegate, can_modify_sops,
                    dual_approval_required, allowed_data_classifications,
                    forbidden_tool_patterns, approved_tools, signature_hash,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (profile_id, self.tenant_id, self.company_id, name, float(max_single),
                 float(max_monthly),
                 "HIGH" if tier in ("EXECUTIVE", "OWNER") else "MEDIUM" if tier == "MANAGER" else "LOW",
                 1 if can_hire else 0, 0, 1 if tier in ("EXECUTIVE", "OWNER") else 0,
                 1 if can_delegate else 0, 1 if can_modify_sops else 0,
                 1 if tier in ("EXECUTIVE", "OWNER") else 0,
                 _json(["PUBLIC", "INTERNAL"] if tier == "EMPLOYEE" else
                       ["PUBLIC", "INTERNAL", "CONFIDENTIAL"] if tier == "MANAGER" else
                       ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]),
                 _json([]), _json([]), signature, now, now),
            )
            conn.commit()
        return {"profile_id": profile_id, "tier": tier,
                "max_spend_single_usd": max_single, "max_spend_monthly_usd": max_monthly,
                "can_hire": can_hire, "can_delegate": can_delegate,
                "can_modify_sops": can_modify_sops, "signature_hash": signature}

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------
    def hire_employee(self, *, position_id: str, first_name: str, last_name: str,
                      manager_employee_id: Optional[str] = None,
                      employee_code: Optional[str] = None,
                      created_by: str = "system",
                      knowledge_clearance: Optional[str] = None) -> Dict[str, Any]:
        with self._conn() as conn:
            position = conn.execute(
                "SELECT * FROM corporate_positions WHERE position_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (position_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not position:
                raise WorkforceError("Position not found in this company.")
            if position["current_filled_count"] >= position["headcount_limit"]:
                raise WorkforceError(
                    f"Position '{position['title']}' is at its headcount limit "
                    f"({position['headcount_limit']})."
                )
            department = conn.execute(
                "SELECT * FROM corporate_departments WHERE department_id = ?",
                (position["department_id"],),
            ).fetchone()
            if department["current_headcount"] >= department["headcount_ceiling"]:
                raise WorkforceError(
                    f"Department '{department['name']}' is at its headcount ceiling."
                )
            if manager_employee_id:
                manager = conn.execute(
                    "SELECT * FROM corporate_employees WHERE employee_id = ? "
                    "AND tenant_id = ? AND company_id = ?",
                    (manager_employee_id, self.tenant_id, self.company_id),
                ).fetchone()
                if not manager:
                    raise WorkforceError("Manager not found in this company.")

        employee_id = _id("emp")
        code = employee_code or self._next_employee_code(department["code"])
        if self._employee_code_taken(code):
            raise WorkforceError(f"Employee code '{code}' already exists in this company.")
        authority = self._profile_by_id(position["default_authority_profile_id"])
        knowledge = self._ensure_knowledge_profile(knowledge_clearance or
                                                  ("INTERNAL" if authority["tier"] == "EMPLOYEE" else "CONFIDENTIAL"))
        now = _now()
        domain = self.company_id.replace("comp_", "")
        email = f"{code.lower()}@{domain}.test"
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO corporate_employees
                   (employee_id, tenant_id, company_id, position_id, department_id,
                    identity_type, first_name, last_name, work_email, lifecycle_state,
                    authority_profile_id, knowledge_profile_id, performance_rating,
                    total_tokens_used, total_cost_usd, allocated_monthly_budget_usd,
                    spent_monthly_budget_usd, emergency_killswitch, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (employee_id, self.tenant_id, self.company_id, position_id,
                 position["department_id"], "AI_EMPLOYEE", first_name, last_name, email,
                 "ACTIVE", authority["profile_id"], knowledge["profile_id"], 100.0,
                 0, 0.0, float(authority["max_spend_monthly_usd"]), 0.0, 0, now, now),
            )
            conn.execute(
                "UPDATE corporate_positions SET current_filled_count = current_filled_count + 1 "
                "WHERE position_id = ?", (position_id,),
            )
            conn.execute(
                "UPDATE corporate_departments SET current_headcount = current_headcount + 1 "
                "WHERE department_id = ?", (position["department_id"],),
            )
            conn.commit()

        if manager_employee_id:
            self.assign_manager(employee_id=employee_id,
                                manager_employee_id=manager_employee_id)

        evidence = self._seal(
            action="HIRE_EMPLOYEE",
            subject=f"employee://{employee_id}",
            expected="PROVISIONED_WITH_AUTHORITY",
            actual=f"{code} {authority['tier']}",
            verified=True,
            details=f"Hired {first_name} {last_name} into '{position['title']}'.",
            extra={"employee_id": employee_id, "position_id": position_id},
        )
        return {
            "success": True,
            "employee_id": employee_id,
            "employee_code": code,
            "position_id": position_id,
            "department_id": position["department_id"],
            "title": position["title"],
            "grade": position["hierarchy_level"],
            "authority_tier": authority["tier"],
            "reporting_manager_id": manager_employee_id,
            "knowledge_profile_id": knowledge["profile_id"],
            "evidence": evidence,
        }

    def _next_employee_code(self, department_code: str) -> str:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT employee_id FROM corporate_employees WHERE company_id = ?",
                (self.company_id,),
            ).fetchall()
        return f"EMP-{department_code}-{len(rows) + 1:03d}"

    def _employee_code_taken(self, code: str) -> bool:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT 1 FROM corporate_employees WHERE company_id = ? "
                "AND work_email LIKE ?", (self.company_id, f"{code.lower()}@%"),
            ).fetchone()
        return bool(rows)

    def _profile_by_id(self, profile_id: Optional[str]) -> Dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM employee_authority_profiles WHERE profile_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (profile_id, self.tenant_id, self.company_id),
            ).fetchone()
        if not row:
            return {"profile_id": None, "tier": "EMPLOYEE",
                    "max_spend_single_usd": 0.0, "max_spend_monthly_usd": 0.0,
                    "can_hire": 0, "can_delegate": 0, "can_modify_sops": 0}
        item = dict(row)
        if item["max_spend_single_usd"] >= 1_000_000:
            item["tier"] = "OWNER"
        elif item["can_hire"] and item["max_spend_single_usd"] >= 100_000:
            item["tier"] = "EXECUTIVE"
        elif item["can_delegate"]:
            item["tier"] = "MANAGER"
        else:
            item["tier"] = "EMPLOYEE"
        return item

    def _ensure_knowledge_profile(self, clearance: str) -> Dict[str, Any]:
        profile_id = _id("know")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM employee_knowledge_profiles WHERE tenant_id = ? "
                "AND company_id = ? AND clearance_level = ?",
                (self.tenant_id, self.company_id, clearance),
            ).fetchone()
            if row:
                return dict(row)
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO employee_knowledge_profiles
                   (profile_id, tenant_id, company_id, clearance_level, permitted_domains,
                    permitted_systems, forbidden_topics, max_retrieval_tokens,
                    data_residency_jurisdictions, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (profile_id, self.tenant_id, self.company_id, clearance,
                 _json(["company_knowledge", "department_knowledge"]),
                 _json(["corporate_records"]), _json(["credentials", "other_tenants"]),
                 8192, _json(["IN"]), now, now),
            )
            conn.commit()
        return {"profile_id": profile_id, "clearance_level": clearance}

    # ------------------------------------------------------------------
    # Reporting relationships
    # ------------------------------------------------------------------
    def assign_manager(self, *, employee_id: Optional[str] = None,
                       manager_employee_id: str,
                       position_id: Optional[str] = None,
                       relationship_type: str = "SOLID_LINE") -> Dict[str, Any]:
        """Assign a manager to an employee, or to every employee in a position."""
        if relationship_type not in ("SOLID_LINE", "MATRIX", "PROJECT"):
            raise WorkforceError("relationship_type must be SOLID_LINE, MATRIX or PROJECT.")
        with self._conn() as conn:
            manager = conn.execute(
                "SELECT * FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (manager_employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not manager:
                raise WorkforceError("Manager not found in this company.")

            if position_id:
                targets = [r["employee_id"] for r in conn.execute(
                    "SELECT employee_id FROM corporate_employees WHERE position_id = ? "
                    "AND tenant_id = ? AND company_id = ?",
                    (position_id, self.tenant_id, self.company_id),
                ).fetchall()]
            else:
                if not employee_id:
                    raise WorkforceError("employee_id or position_id is required.")
                targets = [employee_id]

            results = []
            for target_id in targets:
                target = conn.execute(
                    "SELECT * FROM corporate_employees WHERE employee_id = ? "
                    "AND tenant_id = ? AND company_id = ?",
                    (target_id, self.tenant_id, self.company_id),
                ).fetchone()
                if not target:
                    raise WorkforceError(f"Employee {target_id} not found in this company.")
                if target_id == manager_employee_id:
                    raise WorkforceError("An employee cannot report to themselves.")
                if self._would_create_cycle(target_id, manager_employee_id):
                    raise WorkforceError(
                        "Reporting assignment rejected: it would create a management cycle."
                    )
                conn.execute(
                    "UPDATE employee_reporting_relationships SET is_active = 0, "
                    "effective_to = ? WHERE employee_id = ? AND relationship_type = ? "
                    "AND is_active = 1", (_now(), target_id, relationship_type),
                )
                now = _now()
                conn.execute(
                    """INSERT INTO employee_reporting_relationships
                       (relationship_id, tenant_id, company_id, employee_id,
                        manager_employee_id, relationship_type, effective_from,
                        effective_to, delegation_scope, is_active, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (_id("rel"), self.tenant_id, self.company_id, target_id,
                     manager_employee_id, relationship_type, now, None,
                     _json({}), 1, now),
                )
                results.append({"employee_id": target_id,
                                "manager_employee_id": manager_employee_id})
            conn.commit()
        return {"success": True, "assignments": results,
                "relationship_type": relationship_type}

    def _would_create_cycle(self, employee_id: str, manager_employee_id: str) -> bool:
        """Walk the manager's chain; if we reach employee_id, it is a cycle."""
        seen = set()
        current = manager_employee_id
        with self._conn() as conn:
            while current and current not in seen:
                if current == employee_id:
                    return True
                seen.add(current)
                row = conn.execute(
                    "SELECT manager_employee_id FROM employee_reporting_relationships "
                    "WHERE employee_id = ? AND is_active = 1 AND relationship_type = 'SOLID_LINE' "
                    "ORDER BY effective_from DESC LIMIT 1",
                    (current,),
                ).fetchone()
                current = row["manager_employee_id"] if row else None
        return False

    def reporting_chain(self, employee_id: str) -> List[Dict[str, Any]]:
        chain: List[Dict[str, Any]] = []
        current = employee_id
        seen = set()
        with self._conn() as conn:
            while current and current not in seen:
                seen.add(current)
                row = conn.execute(
                    "SELECT e.employee_id, e.first_name, e.last_name, e.position_id, "
                    "e.department_id, p.title, p.hierarchy_level "
                    "FROM corporate_employees e JOIN corporate_positions p "
                    "ON e.position_id = p.position_id WHERE e.employee_id = ? "
                    "AND e.tenant_id = ? AND e.company_id = ?",
                    (current, self.tenant_id, self.company_id),
                ).fetchone()
                if not row:
                    break
                chain.append(dict(row))
                rel = conn.execute(
                    "SELECT manager_employee_id FROM employee_reporting_relationships "
                    "WHERE employee_id = ? AND is_active = 1 AND relationship_type = 'SOLID_LINE' "
                    "ORDER BY effective_from DESC LIMIT 1",
                    (current,),
                ).fetchone()
                current = rel["manager_employee_id"] if rel else None
            for emp in chain:
                emp["reports_to"] = (
                    chain[chain.index(emp) + 1]["employee_id"]
                    if chain.index(emp) + 1 < len(chain) else None
                )
        return chain

    def list_employees(self, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = (
            "SELECT e.*, p.title, p.hierarchy_level, p.position_code, "
            "(SELECT manager_employee_id FROM employee_reporting_relationships r "
            " WHERE r.employee_id = e.employee_id AND r.is_active = 1 "
            " AND r.relationship_type = 'SOLID_LINE' ORDER BY r.effective_from DESC LIMIT 1) "
            "AS manager_employee_id "
            "FROM corporate_employees e JOIN corporate_positions p "
            "ON e.position_id = p.position_id "
            "WHERE e.tenant_id = ? AND e.company_id = ?"
        )
        params: List[Any] = [self.tenant_id, self.company_id]
        if department_id:
            sql += " AND e.department_id = ?"
            params.append(department_id)
        sql += " ORDER BY p.hierarchy_level, e.employee_code" if False else " ORDER BY p.hierarchy_level, e.created_at"
        with self._conn() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT e.*, p.title, p.hierarchy_level, p.position_code, p.job_family "
                "FROM corporate_employees e JOIN corporate_positions p "
                "ON e.position_id = p.position_id "
                "WHERE e.employee_id = ? AND e.tenant_id = ? AND e.company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["reporting_chain"] = self.reporting_chain(employee_id)
        item["sops"] = self.list_employee_sops(employee_id)
        item["kras"] = self.list_kras(employee_id)
        return item

    def deactivate_employee(self, employee_id: str, *, reason: str,
                            actor_role: str = "OWNER") -> Dict[str, Any]:
        """Deactivate without deleting history (constitutional requirement)."""
        if actor_role not in ("OWNER", "EXECUTIVE", "GLOBAL_ADMIN"):
            raise WorkforceError("Only owner or executive authority may deactivate an employee.")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not row:
                raise WorkforceError("Employee not found in this company.")
            if row["lifecycle_state"] == "TERMINATED":
                return {"success": True, "employee_id": employee_id, "status": "TERMINATED"}
            conn.execute(
                "UPDATE corporate_employees SET lifecycle_state = 'TERMINATED', "
                "emergency_killswitch = 1, updated_at = ? WHERE employee_id = ?",
                (_now(), employee_id),
            )
            conn.execute(
                "UPDATE employee_reporting_relationships SET is_active = 0, effective_to = ? "
                "WHERE employee_id = ? AND is_active = 1", (_now(), employee_id),
            )
            conn.execute(
                "UPDATE corporate_positions SET current_filled_count = "
                "MAX(current_filled_count - 1, 0) WHERE position_id = ?",
                (row["position_id"],),
            )
            conn.execute(
                "UPDATE corporate_departments SET current_headcount = "
                "MAX(current_headcount - 1, 0) WHERE department_id = ?",
                (row["department_id"],),
            )
            conn.commit()
        evidence = self._seal(
            action="DEACTIVATE_EMPLOYEE", subject=f"employee://{employee_id}",
            expected="HISTORY_RETAINED", actual="TERMINATED", verified=True,
            details=f"Deactivated employee; records retained. Reason: {reason[:200]}",
            extra={"employee_id": employee_id},
        )
        return {"success": True, "employee_id": employee_id,
                "status": "TERMINATED", "history_retained": True, "evidence": evidence}

    # ------------------------------------------------------------------
    # SOPs
    # ------------------------------------------------------------------
    def register_sop(self, *, department_id: str, code: str, title: str,
                     category: str = "OPERATIONAL", objective: str = "",
                     risk_level: str = "MEDIUM") -> Dict[str, Any]:
        code = code.strip().upper()
        with self._conn() as conn:
            dept = conn.execute(
                "SELECT department_id FROM corporate_departments WHERE department_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (department_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not dept:
                raise WorkforceError("Department not found in this company.")
            if conn.execute(
                "SELECT 1 FROM sop_definitions WHERE company_id = ? AND sop_code = ?",
                (self.company_id, code),
            ).fetchone():
                raise WorkforceError(f"SOP code '{code}' already exists.")
        sop_id = _id("sop")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sop_definitions
                   (sop_id, tenant_id, company_id, department_id, sop_code, title,
                    category, cadence, risk_level, objective, trigger_conditions,
                    is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sop_id, self.tenant_id, self.company_id, department_id, code,
                 title, category, "EVENT_DRIVEN", risk_level, objective or title,
                 _json([]), 1, now, now),
            )
            conn.commit()
        return {"success": True, "sop_id": sop_id, "sop_code": code, "title": title}

    def publish_sop_version(self, *, sop_id: str, semver: str,
                            steps: List[Dict[str, Any]],
                            required_authority_level: str = "DELEGATED",
                            author_employee_id: str,
                            evidence_requirements: Optional[List[str]] = None,
                            approved_by_role: Optional[str] = None) -> Dict[str, Any]:
        """Publish an immutable SOP version. Previous versions are never mutated."""
        with self._conn() as conn:
            sop = conn.execute(
                "SELECT * FROM sop_definitions WHERE sop_id = ? AND tenant_id = ? "
                "AND company_id = ?", (sop_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not sop:
                raise WorkforceError("SOP not found in this company.")
            if conn.execute(
                "SELECT 1 FROM sop_versions WHERE sop_id = ? AND version_semver = ?",
                (sop_id, semver),
            ).fetchone():
                raise WorkforceError(f"SOP version '{semver}' already exists; versions are immutable.")
            author = conn.execute(
                "SELECT employee_id FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (author_employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not author:
                raise WorkforceError("Author employee not found in this company.")
            if not isinstance(steps, list) or not steps:
                raise WorkforceError("An SOP version needs at least one executable step.")
            if not all(isinstance(s, dict) and s.get("action") for s in steps):
                raise WorkforceError("Every SOP step needs an 'action' field.")

        payload = _json({"steps": steps, "authority": required_authority_level})
        version_id = _id("sopv")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sop_versions
                   (version_id, sop_id, tenant_id, version_semver, status, steps_definition,
                    input_schema, output_schema, anti_gaming_rules, required_authority_level,
                    evidence_requirements, author_employee_id, approved_by_role, approved_at,
                    sha256_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (version_id, sop_id, self.tenant_id, semver,
                 "APPROVED" if approved_by_role else "DRAFT",
                 _json(steps), _json({}), _json({}), _json([]),
                 required_authority_level, _json(evidence_requirements or []),
                 author_employee_id, approved_by_role, now if approved_by_role else None,
                 hashlib.sha256(payload.encode()).hexdigest(), now),
            )
            conn.execute(
                "UPDATE sop_definitions SET updated_at = ? WHERE sop_id = ?", (now, sop_id),
            )
            conn.commit()
        evidence = self._seal(
            action="PUBLISH_SOP_VERSION", subject=f"sop://{sop_id}/{semver}",
            expected="IMMUTABLE_VERSION", actual="SEALED", verified=True,
            details=f"Published SOP {sop['sop_code']} version {semver}.",
            extra={"sop_id": sop_id, "version_id": version_id},
        )
        return {"success": True, "sop_id": sop_id, "version_id": version_id,
                "semver": semver, "status": "APPROVED" if approved_by_role else "DRAFT",
                "sha256_hash": hashlib.sha256(payload.encode()).hexdigest(),
                "evidence": evidence}

    def assign_sop(self, *, employee_id: str, version_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            emp = conn.execute(
                "SELECT * FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not emp:
                raise WorkforceError("Employee not found in this company.")
            ver = conn.execute(
                "SELECT * FROM sop_versions WHERE version_id = ? AND tenant_id = ?",
                (version_id, self.tenant_id),
            ).fetchone()
            if not ver:
                raise WorkforceError("SOP version not found in this tenant.")
            if ver["status"] != "APPROVED":
                raise WorkforceError("Only an APPROVED SOP version can be assigned.")
            if conn.execute(
                "SELECT 1 FROM employee_sop_assignments WHERE employee_id = ? "
                "AND sop_version_id = ? AND assignment_status = 'ACTIVE'",
                (employee_id, version_id),
            ).fetchone():
                raise WorkforceError("This SOP version is already assigned to the employee.")
            conn.execute(
                "UPDATE employee_sop_assignments SET assignment_status = 'SUPERSEDED' "
                "WHERE employee_id = ? AND assignment_status = 'ACTIVE'", (employee_id,),
            )
        assignment_id = _id("sopa")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO employee_sop_assignments
                   (assignment_id, tenant_id, company_id, employee_id, position_id,
                    sop_version_id, assignment_status, compliance_score,
                    total_executions, failed_executions, last_executed_at, assigned_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (assignment_id, self.tenant_id, self.company_id, employee_id,
                 emp["position_id"], version_id, "ACTIVE", 100.0, 0, 0, None, now),
            )
            conn.commit()
        return {"success": True, "assignment_id": assignment_id,
                "employee_id": employee_id, "sop_version_id": version_id}

    def list_employee_sops(self, employee_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT a.*, v.version_semver, d.sop_code, d.title "
                "FROM employee_sop_assignments a "
                "JOIN sop_versions v ON a.sop_version_id = v.version_id "
                "JOIN sop_definitions d ON v.sop_id = d.sop_id "
                "WHERE a.employee_id = ? AND a.tenant_id = ? AND a.company_id = ? "
                "AND a.assignment_status = 'ACTIVE'",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # KRA / KPI
    # ------------------------------------------------------------------
    def define_kra(self, *, employee_id: str, name: str, weight_percentage: float,
                   accountability_statement: str) -> Dict[str, Any]:
        if not 0 < weight_percentage <= 100:
            raise WorkforceError("KRA weight_percentage must be between 0 and 100.")
        with self._conn() as conn:
            emp = conn.execute(
                "SELECT * FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not emp:
                raise WorkforceError("Employee not found in this company.")
            total = conn.execute(
                "SELECT COALESCE(SUM(weight_percentage), 0) AS w FROM employee_kras "
                "WHERE employee_id = ?", (employee_id,),
            ).fetchone()["w"]
        if total + weight_percentage > 100.0001:
            raise WorkforceError(
                f"KRA weights would exceed 100% (current {total:.2f}%)."
            )
        kra_id = _id("kra")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO employee_kras
                   (kra_id, tenant_id, company_id, employee_id, position_id,
                    strategic_objective_id, name, weight_percentage,
                    accountability_statement, responsibility,
                    associated_workflows, associated_kpi_ids, allowed_tools,
                    authority_scope, escalation_rules, expected_outcomes,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kra_id, self.tenant_id, self.company_id, employee_id,
                 emp["position_id"], None, name, float(weight_percentage),
                 accountability_statement, accountability_statement,
                 _json([]), _json([]), _json([]), _json({}), _json([]), _json([]),
                 now, now),
            )
            conn.commit()
        return {"success": True, "kra_id": kra_id, "employee_id": employee_id,
                "name": name, "weight_percentage": weight_percentage}

    def list_kras(self, employee_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM employee_kras WHERE employee_id = ? AND tenant_id = ? "
                "AND company_id = ? ORDER BY weight_percentage DESC",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def define_kpi(self, *, kra_id: str, code: str, name: str, unit: str,
                   target_value: float, definition: str = "",
                   polarity: str = "HIGHER_IS_BETTER",
                   data_source_feed: str = "corporate_records",
                   verification_method: str = "TRANSACTION_RECONCILIATION",
                   measurement_frequency: str = "MONTHLY",
                   paired_counter_metric_code: Optional[str] = None) -> Dict[str, Any]:
        if polarity not in ("HIGHER_IS_BETTER", "LOWER_IS_BETTER"):
            raise WorkforceError("polarity must be HIGHER_IS_BETTER or LOWER_IS_BETTER.")
        with self._conn() as conn:
            kra = conn.execute(
                "SELECT * FROM employee_kras WHERE kra_id = ? AND tenant_id = ? "
                "AND company_id = ?", (kra_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not kra:
                raise WorkforceError("KRA not found in this company.")
            if conn.execute(
                "SELECT 1 FROM kpi_definitions WHERE tenant_id = ? AND code = ? "
                "AND kra_id = ?", (self.tenant_id, code, kra_id),
            ).fetchone():
                raise WorkforceError(f"KPI code '{code}' already exists for this KRA.")
            paired_id = None
            if paired_counter_metric_code:
                paired = conn.execute(
                    "SELECT kpi_id FROM kpi_definitions WHERE tenant_id = ? AND code = ?",
                    (self.tenant_id, paired_counter_metric_code),
                ).fetchone()
                if not paired:
                    raise WorkforceError("Paired counter-metric not found.")
                paired_id = paired["kpi_id"]
        kpi_id = _id("kpi")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO kpi_definitions
                   (kpi_id, tenant_id, company_id, kra_id, code, name, definition,
                    unit, polarity, target_value, threshold_warning, threshold_critical,
                    paired_counter_metric_id, counter_metric_weight, data_source_feed,
                    verification_method, measurement_frequency, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kpi_id, self.tenant_id, self.company_id, kra_id, code, name,
                 definition or name, unit, polarity, float(target_value),
                 0.8 * float(target_value) if polarity == "HIGHER_IS_BETTER" else 1.2 * float(target_value),
                 0.5 * float(target_value) if polarity == "HIGHER_IS_BETTER" else 1.5 * float(target_value),
                 paired_id, 0.5, data_source_feed, verification_method,
                 measurement_frequency, now),
            )
            conn.commit()
        return {"success": True, "kpi_id": kpi_id, "kra_id": kra_id, "code": code,
                "target_value": target_value, "unit": unit}

    def record_measurement(self, *, kpi_id: str, measured_value: float,
                           evidence_ref: str, counter_metric_value: Optional[float] = None,
                           mission_id: Optional[str] = None) -> Dict[str, Any]:
        """A measurement without a real evidence reference is refused."""
        if not evidence_ref or not str(evidence_ref).strip():
            raise WorkforceError(
                "A KPI measurement requires an evidence reference; self-awarded "
                "success is not accepted."
            )
        with self._conn() as conn:
            kpi = conn.execute(
                "SELECT k.*, r.employee_id FROM kpi_definitions k "
                "JOIN employee_kras r ON k.kra_id = r.kra_id "
                "WHERE k.kpi_id = ? AND k.tenant_id = ? AND k.company_id = ?",
                (kpi_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not kpi:
                raise WorkforceError("KPI not found in this company.")
            counter = counter_metric_value
            if kpi["paired_counter_metric_id"] and counter is None:
                raise WorkforceError(
                    "This KPI requires its paired counter-metric value to prevent gaming."
                )
            anti_gaming_passed = True
            if counter is not None:
                # A rising primary metric while its counter-metric degrades is a
                # gaming signal, not an achievement.
                anti_gaming_passed = not (
                    kpi["polarity"] == "HIGHER_IS_BETTER" and
                    measured_value > kpi["target_value"] and
                    counter < (kpi["threshold_warning"] or 0)
                )
            if kpi["polarity"] == "HIGHER_IS_BETTER":
                variance = ((measured_value - kpi["target_value"]) /
                            kpi["target_value"] * 100) if kpi["target_value"] else 0.0
            else:
                variance = ((kpi["target_value"] - measured_value) /
                            kpi["target_value"] * 100) if kpi["target_value"] else 0.0
            score = max(0.0, min(120.0, 100.0 + variance))
            if not anti_gaming_passed:
                score = min(score, 50.0)
            measurement_id = _id("kmp")
            now = _now()
            payload = _json({"evidence_ref": str(evidence_ref),
                             "measured_value": measured_value,
                             "counter_metric_value": counter})
            conn.execute(
                """INSERT INTO kpi_measurements
                   (measurement_id, tenant_id, company_id, kpi_id, employee_id,
                    mission_id, measured_value, counter_metric_value,
                    anti_gaming_passed, variance_percentage, score_contribution,
                    raw_evidence_json, evidence_sha256, measured_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (measurement_id, self.tenant_id, self.company_id, kpi_id,
                 kpi["employee_id"], mission_id, float(measured_value), counter,
                 1 if anti_gaming_passed else 0, round(variance, 4), round(score, 4),
                 payload, hashlib.sha256(payload.encode()).hexdigest(), now),
            )
            conn.commit()
        evidence = self._seal(
            action="RECORD_KPI_MEASUREMENT", subject=f"kpi://{kpi_id}",
            expected="EVIDENCE_BACKED_MEASUREMENT",
            actual=f"value={measured_value} score={round(score, 2)}",
            verified=anti_gaming_passed,
            details=f"Recorded KPI measurement against evidence '{evidence_ref}'.",
            extra={"kpi_id": kpi_id, "measurement_id": measurement_id},
        )
        return {"success": True, "measurement_id": measurement_id,
                "kpi_id": kpi_id, "employee_id": kpi["employee_id"],
                "measured_value": measured_value, "variance_percentage": round(variance, 4),
                "score_contribution": round(score, 4),
                "anti_gaming_passed": anti_gaming_passed, "evidence": evidence}

    # ------------------------------------------------------------------
    # Performance evaluation
    # ------------------------------------------------------------------
    def evaluate_employee(self, *, employee_id: str,
                          period_start: float, period_end: float,
                          evaluator_role: str = "EXEC_CHRO",
                          externally_blocked_kpi_ids: Optional[List[str]] = None,
                          collaboration_sla_score: float = 100.0) -> Dict[str, Any]:
        """Explainable evaluation. Never scores an unmeasured KPI, and never
        penalises an employee for a blocked external dependency."""
        blocked = set(externally_blocked_kpi_ids or [])
        if not 0 <= collaboration_sla_score <= 100:
            raise WorkforceError("collaboration_sla_score must be 0..100.")
        with self._conn() as conn:
            emp = conn.execute(
                "SELECT * FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not emp:
                raise WorkforceError("Employee not found in this company.")
            kras = conn.execute(
                "SELECT * FROM employee_kras WHERE employee_id = ? AND tenant_id = ? "
                "AND company_id = ?", (employee_id, self.tenant_id, self.company_id),
            ).fetchall()
            if not kras:
                raise WorkforceError("Employee has no KRAs; define measurable KRAs first.")
            kpi_rows = conn.execute(
                "SELECT k.*, r.weight_percentage AS kra_weight FROM kpi_definitions k "
                "JOIN employee_kras r ON k.kra_id = r.kra_id "
                "WHERE r.employee_id = ? AND k.tenant_id = ? AND k.company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchall()
            measurements = conn.execute(
                "SELECT * FROM kpi_measurements WHERE employee_id = ? AND tenant_id = ? "
                "AND company_id = ? AND measured_at >= ? AND measured_at <= ? "
                "ORDER BY measured_at DESC",
                (employee_id, self.tenant_id, self.company_id, period_start, period_end),
            ).fetchall()
            sop_row = conn.execute(
                "SELECT COALESCE(AVG(compliance_score), 100.0) AS s, "
                "COALESCE(SUM(total_executions), 0) AS n "
                "FROM employee_sop_assignments WHERE employee_id = ? "
                "AND assignment_status = 'ACTIVE'", (employee_id,),
            ).fetchone()

        latest: Dict[str, Any] = {}
        for m in measurements:
            if m["kpi_id"] not in latest:
                latest[m["kpi_id"]] = dict(m)

        included: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []
        for kpi in kpi_rows:
            kpi_id = kpi["kpi_id"]
            if kpi_id in blocked:
                excluded.append({"kpi_id": kpi_id, "code": kpi["code"],
                                 "reason": "EXTERNAL_DEPENDENCY_BLOCKED"})
                continue
            m = latest.get(kpi_id)
            if not m:
                excluded.append({"kpi_id": kpi_id, "code": kpi["code"],
                                 "reason": "NOT_MEASURED"})
                continue
            included.append({
                "kpi_id": kpi_id, "code": kpi["code"],
                "weight": float(kpi["kra_weight"]),
                "score": float(m["score_contribution"]),
                "anti_gaming_passed": bool(m["anti_gaming_passed"]),
                "measurement_id": m["measurement_id"],
            })

        if not included:
            return {
                "success": False,
                "status": "INSUFFICIENT_MEASUREMENTS",
                "employee_id": employee_id,
                "detail": ("No KPI has a verified measurement in this period. "
                           "Refusing to produce a performance score."),
                "excluded": excluded,
            }

        total_weight = sum(item["weight"] for item in included) or 1.0
        kpi_score = sum(item["score"] * item["weight"] for item in included) / total_weight
        anti_gaming_score = 100.0 * (
            sum(1 for i in included if i["anti_gaming_passed"]) / len(included)
        )
        sop_score = float(sop_row["s"]) if sop_row else 100.0

        weights = {"kpi": 0.55, "sop": 0.20, "anti_gaming": 0.10, "collaboration": 0.15}
        composite = (
            weights["kpi"] * kpi_score
            + weights["sop"] * sop_score
            + weights["anti_gaming"] * anti_gaming_score
            + weights["collaboration"] * collaboration_sla_score
        )
        if composite >= 90:
            recommendation = "EXCEEDING"
        elif composite >= 75:
            recommendation = "MEETING"
        elif composite >= 60:
            recommendation = "DEVELOPING"
        else:
            recommendation = "IMPROVEMENT_PLAN"

        review_id = _id("rev")
        now = _now()
        proof = {
            "weights": weights,
            "included_kpis": included,
            "excluded_kpis": excluded,
            "components": {
                "kpi_achievement_score": round(kpi_score, 4),
                "sop_compliance_score": round(sop_score, 4),
                "anti_gaming_compliance_score": round(anti_gaming_score, 4),
                "collaboration_sla_score": round(float(collaboration_sla_score), 4),
            },
            "formula": "composite = 0.55*kpi + 0.20*sop + 0.10*anti_gaming + 0.15*collaboration",
        }
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO employee_performance_reviews
                   (review_id, tenant_id, company_id, employee_id, review_period_start,
                    review_period_end, kpi_achievement_score, sop_compliance_score,
                    anti_gaming_compliance_score, collaboration_sla_score,
                    composite_performance_score, evaluator_role, recommendation,
                    mathematical_proof_json, is_sealed, sealed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (review_id, self.tenant_id, self.company_id, employee_id,
                 float(period_start), float(period_end), round(kpi_score, 4),
                 round(sop_score, 4), round(anti_gaming_score, 4),
                 round(float(collaboration_sla_score), 4), round(composite, 4),
                 evaluator_role, recommendation, _json(proof), 1, now),
            )
            conn.execute(
                "UPDATE corporate_employees SET performance_rating = ?, updated_at = ? "
                "WHERE employee_id = ?", (round(composite, 4), now, employee_id),
            )
            conn.commit()
        evidence = self._seal(
            action="EVALUATE_EMPLOYEE", subject=f"employee://{employee_id}/review",
            expected="EXPLAINABLE_COMPOSITE", actual=f"{round(composite, 2)} {recommendation}",
            verified=True,
            details=(f"Evaluated {len(included)} measured KPIs, "
                     f"{len(excluded)} excluded (no measurement or external block)."),
            extra={"review_id": review_id, "employee_id": employee_id},
        )
        return {
            "success": True,
            "status": "COMPLETED",
            "review_id": review_id,
            "employee_id": employee_id,
            "composite_score": round(composite, 4),
            "recommendation": recommendation,
            "components": proof["components"],
            "included_kpis": included,
            "excluded_kpis": excluded,
            "weights": weights,
            "evidence": evidence,
        }

    # ------------------------------------------------------------------
    # Agent factory (capabilities are shared; instances are isolated)
    # ------------------------------------------------------------------
    def register_capability(self, *, code: str, name: str, category: str,
                            risk_class: str = "READ_ONLY",
                            cost_per_call_usd: float = 0.001,
                            input_schema: Optional[Dict[str, Any]] = None,
                            output_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        code = code.strip().lower()
        if not name.strip() or not category.strip():
            raise WorkforceError("Capability name and category are required.")
        if risk_class not in ("READ_ONLY", "LOW_RISK", "HIGH_RISK", "IRREVERSIBLE"):
            raise WorkforceError("Invalid capability risk_class.")
        with self._conn() as conn:
            if conn.execute(
                "SELECT 1 FROM agent_capabilities WHERE tenant_id = ? AND code = ?",
                (self.tenant_id, code),
            ).fetchone():
                raise WorkforceError(f"Capability '{code}' already registered.")
        capability_id = _id("cap")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO agent_capabilities
                   (capability_id, tenant_id, code, name, category, input_schema,
                    output_schema, risk_class, cost_per_call_usd, is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (capability_id, self.tenant_id, code, name, category,
                 _json(input_schema or {}), _json(output_schema or {}),
                 risk_class, float(cost_per_call_usd), 1, now),
            )
            conn.commit()
        return {"success": True, "capability_id": capability_id, "code": code,
                "name": name, "category": category, "risk_class": risk_class}

    def list_capabilities(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_capabilities WHERE tenant_id = ? AND is_active = 1 "
                "ORDER BY category, code", (self.tenant_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _ensure_agent_template(self, capability: Dict[str, Any]) -> str:
        """Create the reusable template + signed version for a capability once."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT v.version_id FROM agent_templates t "
                "JOIN agent_template_versions v ON v.template_id = t.template_id "
                "WHERE t.tenant_id = ? AND t.slug = ? AND v.status = 'ACTIVE' "
                "ORDER BY v.created_at DESC LIMIT 1",
                (self.tenant_id, capability["code"]),
            ).fetchone()
            if row:
                return row["version_id"]

        template_id = _id("tpl")
        version_id = _id("tplv")
        now = _now()
        manifest = _json([capability["code"]])
        sbom = hashlib.sha256(
            _json([capability["code"], capability["capability_id"]]).encode()
        ).hexdigest()
        signature = "sig-" + hashlib.sha256(
            _json([self.tenant_id, capability["code"], sbom]).encode()
        ).hexdigest()[:24]
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO agent_templates
                   (template_id, tenant_id, name, slug, description, role_category,
                    default_capabilities, default_toolset, sandbox_requirements, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (template_id, self.tenant_id, capability["name"], capability["code"],
                 f"Reusable agent capability: {capability['name']}",
                 capability["category"], manifest, _json([]),
                 _json({"isolation": "PER_INSTANCE_SESSION"}), now),
            )
            conn.execute(
                """INSERT INTO agent_template_versions
                   (version_id, template_id, tenant_id, semver, system_prompt_scaffold,
                    capability_manifest, tool_manifest, resource_limits, sbom_hash,
                    signature, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (version_id, template_id, self.tenant_id, "1.0.0",
                 f"Execute '{capability['code']}' strictly within the delegated task scope.",
                 manifest, _json([]),
                 _json({"max_tokens": 100000, "max_runtime_seconds": 900}),
                 sbom, signature, "ACTIVE", now),
            )
            conn.commit()
        return version_id

    def provision_agent(self, *, employee_id: str, capability_code: str,
                        task_id: Optional[str] = None,
                        mission_id: Optional[str] = None,
                        ttl_seconds: int = 900,
                        allocated_tokens: int = 100000,
                        quota: Optional[int] = None) -> Dict[str, Any]:
        """Provision an isolated agent instance for one employee's task."""
        if ttl_seconds <= 0 or ttl_seconds > 86400:
            raise WorkforceError("ttl_seconds must be between 1 and 86400.")
        quota = quota or self.DEFAULT_AGENT_QUOTA
        with self._conn() as conn:
            emp = conn.execute(
                "SELECT * FROM corporate_employees WHERE employee_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (employee_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not emp:
                raise WorkforceError("Employee not found in this company.")
            if emp["lifecycle_state"] != "ACTIVE":
                raise WorkforceError("Only ACTIVE employees may provision agents.")
            capability = conn.execute(
                "SELECT * FROM agent_capabilities WHERE tenant_id = ? AND code = ? "
                "AND is_active = 1", (self.tenant_id, capability_code.strip().lower()),
            ).fetchone()
            if not capability:
                raise WorkforceError(
                    f"Capability '{capability_code}' is not registered for this tenant."
                )
            active = conn.execute(
                "SELECT COUNT(*) AS n FROM agent_instances WHERE bound_employee_id = ? "
                "AND lifecycle_state IN ('IDLE','LEASED','RUNNING')",
                (employee_id,),
            ).fetchone()["n"]
            if active >= quota:
                raise WorkforceError(
                    f"Agent quota reached for this employee ({active}/{quota}). "
                    "Release an instance before provisioning another."
                )

        version_id = self._ensure_agent_template(dict(capability))
        instance_id = _id("agi")
        lease_id = _id("lease")
        session_id = _id("ags")
        memory_scope_id = _id("mem")
        now = _now()
        session_token = secrets.token_hex(24)
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO agent_instances
                   (instance_id, tenant_id, company_id, template_version_id,
                    bound_employee_id, host_runtime_id, lifecycle_state, current_lease_id,
                    allocated_tokens, used_tokens, cost_incurred_usd, last_heartbeat,
                    created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (instance_id, self.tenant_id, self.company_id, version_id,
                 employee_id, "zonata-governed-runtime", "LEASED", lease_id,
                 int(allocated_tokens), 0, 0.0, now, now),
            )
            conn.execute(
                """INSERT INTO agent_leases
                   (lease_id, tenant_id, company_id, instance_id, leased_by_employee_id,
                    mission_id, task_id, lease_state, acquired_at, expires_at, released_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lease_id, self.tenant_id, self.company_id, instance_id,
                 employee_id, mission_id, task_id, "ACTIVE", now,
                 now + ttl_seconds, None),
            )
            conn.execute(
                """INSERT INTO agent_execution_sessions
                   (session_id, lease_id, tenant_id, company_id, instance_id,
                    session_token_hash, memory_scope_id, isolation_tier,
                    credential_handle_ids, execution_status, tokens_consumed,
                    cost_usd, started_at, ended_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, lease_id, self.tenant_id, self.company_id, instance_id,
                 hashlib.sha256(session_token.encode()).hexdigest(), memory_scope_id,
                 "EPHEMERAL_CONTAINER", _json([]), "RUNNING", 0, 0.0, now, None),
            )
            conn.commit()

        evidence = self._seal(
            action="PROVISION_AGENT", subject=f"agent://{instance_id}",
            expected="ISOLATED_INSTANCE", actual=f"capability={capability['code']}",
            verified=True,
            details=(f"Provisioned '{capability['code']}' for {employee_id} "
                     f"(lease {ttl_seconds}s)."),
            extra={"instance_id": instance_id, "employee_id": employee_id,
                   "capability": capability["code"]},
        )
        return {
            "success": True,
            "instance_id": instance_id,
            "capability": capability["code"],
            "employee_id": employee_id,
            "lease_id": lease_id,
            "session_id": session_id,
            "session_token": session_token,
            "expires_at": now + ttl_seconds,
            "isolation_tier": "EPHEMERAL_CONTAINER",
            "evidence": evidence,
        }

    def list_agent_instances(self, employee_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = ("SELECT i.*, t.name AS capability_name, t.slug AS capability_code "
               "FROM agent_instances i JOIN agent_template_versions v "
               "ON i.template_version_id = v.version_id JOIN agent_templates t "
               "ON v.template_id = t.template_id "
               "WHERE i.tenant_id = ? AND i.company_id = ?")
        params: List[Any] = [self.tenant_id, self.company_id]
        if employee_id:
            sql += " AND i.bound_employee_id = ?"
            params.append(employee_id)
        sql += " ORDER BY i.created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def get_agent_instance(self, instance_id: str, *, employee_id: str) -> Dict[str, Any]:
        """Employee-scoped read. Another employee's instance is invisible."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent_instances WHERE instance_id = ? AND tenant_id = ? "
                "AND company_id = ?", (instance_id, self.tenant_id, self.company_id),
            ).fetchone()
        if not row:
            raise WorkforceError("Agent instance not found.")
        if row["bound_employee_id"] != employee_id:
            raise WorkforceError("Agent instance is bound to another employee.")
        return dict(row)

    def terminate_agent(self, *, instance_id: str, employee_id: str,
                        reason: str = "task_complete") -> Dict[str, Any]:
        instance = self.get_agent_instance(instance_id, employee_id=employee_id)
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "UPDATE agent_instances SET lifecycle_state = 'TERMINATED', "
                "last_heartbeat = ? WHERE instance_id = ?", (now, instance_id),
            )
            conn.execute(
                "UPDATE agent_leases SET lease_state = 'RELEASED', released_at = ? "
                "WHERE lease_id = ?", (now, instance["current_lease_id"]),
            )
            conn.execute(
                "UPDATE agent_execution_sessions SET execution_status = 'COMPLETED', "
                "ended_at = ? WHERE instance_id = ? AND execution_status = 'RUNNING'",
                (now, instance_id),
            )
            conn.commit()
        evidence = self._seal(
            action="TERMINATE_AGENT", subject=f"agent://{instance_id}",
            expected="RESOURCES_RELEASED", actual="TERMINATED", verified=True,
            details=f"Released agent instance; reason={reason[:120]}",
            extra={"instance_id": instance_id, "employee_id": employee_id},
        )
        return {"success": True, "instance_id": instance_id,
                "status": "TERMINATED", "resources_released": True,
                "evidence": evidence}

    # ------------------------------------------------------------------
    # Cross-department collaboration
    # ------------------------------------------------------------------
    def open_collaboration(self, *, mission_id: str, initiator_department_id: str,
                           target_department_id: str, deliverable_description: str,
                           sla_turnaround_hours: float = 24.0,
                           escalation_owner_role: str = "COO",
                           shared_budget_usd: float = 0.0) -> Dict[str, Any]:
        if initiator_department_id == target_department_id:
            raise WorkforceError(
                "A collaboration requires two different departments; an internal "
                "task is not a collaboration."
            )
        if not deliverable_description.strip():
            raise WorkforceError("A collaboration needs an accountable deliverable.")
        if sla_turnaround_hours <= 0:
            raise WorkforceError("sla_turnaround_hours must be positive.")
        valid_roles = {e["code"] for e in EXECUTIVE_CATALOG}
        if escalation_owner_role not in valid_roles:
            raise WorkforceError(
                f"escalation_owner_role must be one of {sorted(valid_roles)}."
            )
        with self._conn() as conn:
            mission = conn.execute(
                "SELECT * FROM corporate_missions WHERE mission_id = ? AND tenant_id = ? "
                "AND company_id = ?", (mission_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not mission:
                raise WorkforceError("Mission not found in this company.")
            for dept_id in (initiator_department_id, target_department_id):
                if not conn.execute(
                    "SELECT 1 FROM corporate_departments WHERE department_id = ? "
                    "AND tenant_id = ? AND company_id = ?",
                    (dept_id, self.tenant_id, self.company_id),
                ).fetchone():
                    raise WorkforceError("Department not found in this company.")
        collab_id = _id("col")
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO cross_department_collaborations
                   (collab_id, mission_id, tenant_id, company_id, initiator_dept_id,
                    target_dept_id, deliverable_description, sla_turnaround_hours,
                    shared_budget_usd, escalation_owner_role, status, accepted_at,
                    fulfilled_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (collab_id, mission_id, self.tenant_id, self.company_id,
                 initiator_department_id, target_department_id,
                 deliverable_description, float(sla_turnaround_hours),
                 float(shared_budget_usd), escalation_owner_role, "REQUESTED",
                 None, None, now),
            )
            conn.commit()
        evidence = self._seal(
            action="OPEN_COLLABORATION", subject=f"collab://{collab_id}",
            expected="ACCOUNTABLE_DELIVERABLE", actual="REQUESTED", verified=True,
            details=f"{initiator_department_id} -> {target_department_id}: "
                    f"{deliverable_description[:160]}",
            extra={"collab_id": collab_id, "mission_id": mission_id},
        )
        return {"success": True, "collab_id": collab_id, "status": "REQUESTED",
                "escalation_owner_role": escalation_owner_role, "evidence": evidence}

    def advance_collaboration(self, *, collab_id: str, action: str) -> Dict[str, Any]:
        transitions = {"ACCEPT": ("REQUESTED", "ACCEPTED", "accepted_at"),
                       "FULFIL": ("ACCEPTED", "FULFILLED", "fulfilled_at")}
        if action not in transitions:
            raise WorkforceError("action must be ACCEPT or FULFIL.")
        required, target, column = transitions[action]
        now = _now()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM cross_department_collaborations WHERE collab_id = ? "
                "AND tenant_id = ? AND company_id = ?",
                (collab_id, self.tenant_id, self.company_id),
            ).fetchone()
            if not row:
                raise WorkforceError("Collaboration not found in this company.")
            if row["status"] != required:
                raise WorkforceError(
                    f"Cannot {action.lower()} a collaboration in status {row['status']}."
                )
            conn.execute(
                f"UPDATE cross_department_collaborations SET status = ?, {column} = ? "
                "WHERE collab_id = ?", (target, now, collab_id),
            )
            conn.commit()
        return {"success": True, "collab_id": collab_id, "status": target}

    # ------------------------------------------------------------------
    # Read models
    # ------------------------------------------------------------------
    def get_organization(self) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM organizations WHERE tenant_id = ? AND company_id = ? "
                "AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, self.company_id),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            item["metadata"] = {}
        item["departments"] = len(self.list_departments())
        item["employees"] = len(self.list_employees())
        return item

    def org_chart(self) -> Dict[str, Any]:
        departments = self.list_departments()
        employees = self.list_employees()
        by_dept: Dict[str, List[Dict[str, Any]]] = {}
        for emp in employees:
            by_dept.setdefault(emp["department_id"], []).append({
                "employee_id": emp["employee_id"],
                "employee_code": emp.get("work_email", "").split("@")[0].upper() or emp["employee_id"],
                "name": f"{emp['first_name']} {emp['last_name']}".strip(),
                "title": emp["title"],
                "grade": emp["hierarchy_level"],
                "manager_employee_id": emp.get("manager_employee_id"),
                "lifecycle_state": emp["lifecycle_state"],
            })
        nodes = []
        for dept in departments:
            head = next(
                (e for e in by_dept.get(dept["department_id"], [])
                 if e["grade"] in ("G1", "G2")), None
            )
            nodes.append({
                "department_id": dept["department_id"],
                "code": dept["code"],
                "name": dept["name"],
                "parent_department_id": dept["parent_department_id"],
                "headcount": dept["current_headcount"],
                "headcount_ceiling": dept["headcount_ceiling"],
                "head": head,
                "employees": by_dept.get(dept["department_id"], []),
            })
        return {
            "organization": self.get_organization(),
            "departments": nodes,
            "employee_count": len(employees),
            "executives": [e for e in employees if e["hierarchy_level"] in ("G1", "G2")],
        }
