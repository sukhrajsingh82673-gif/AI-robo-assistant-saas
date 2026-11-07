"""
ZONATA Autonomous Executive Coworker — Milestone 5: Archetype Contracts
Defines the 12 Specialist Archetypes with typed capability schemas and risk budgets.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class SpecialistRole(str, Enum):
    EXECUTIVE_CHIEF_OF_STAFF = "Executive Chief of Staff"
    PYTHON_SOFTWARE_ENGINEER = "Python Software Engineer"
    QA_RELIABILITY_ENGINEER = "QA & Reliability Engineer"
    DEVOPS_PLATFORM_ADMIN = "DevOps & Platform Admin"
    CYBERSECURITY_DEFENSE_AUDITOR = "Cybersecurity Defense Auditor"
    FINANCIAL_ACCOUNTING_ANALYST = "Financial & Accounting Analyst"
    LEGAL_COMPLIANCE_AUDITOR = "Legal & Compliance Auditor"
    RESEARCH_INTELLIGENCE_ANALYST = "Research & Intelligence Analyst"
    CUSTOMER_SUPPORT_SPECIALIST = "Customer Support Specialist"
    SALES_GROWTH_SPECIALIST = "Sales & Growth Specialist"
    DATA_ENGINEERING_SPECIALIST = "Data Engineering Specialist"
    DESKTOP_GUI_OPERATOR = "Desktop & GUI Operator"


@dataclass
class SpecialistArchetypeContract:
    role: SpecialistRole
    division: str
    description: str
    allowed_capabilities: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    default_risk_tier: str = "LOW"
    max_execution_time_sec: float = 300.0
    quota_ram_mb: int = 256


ARCHETYPE_CONTRACTS: Dict[SpecialistRole, SpecialistArchetypeContract] = {
    SpecialistRole.EXECUTIVE_CHIEF_OF_STAFF: SpecialistArchetypeContract(
        role=SpecialistRole.EXECUTIVE_CHIEF_OF_STAFF,
        division="Executive",
        description="Coordinates strategic priorities, decomposes CEO directives, and conducts morning operating loops.",
        allowed_capabilities=["prioritize", "delegate", "synthesize_report", "schedule_audit"],
        input_schema={"type": "object", "properties": {"objective": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"strategic_plan": {"type": "array"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.PYTHON_SOFTWARE_ENGINEER: SpecialistArchetypeContract(
        role=SpecialistRole.PYTHON_SOFTWARE_ENGINEER,
        division="Engineering",
        description="Writes minimal, production-grade Python standard library modules adhering to Ponytail anti-bloat.",
        allowed_capabilities=["python_exec", "ast_check", "git_worktree_modify", "refactor_code"],
        input_schema={"type": "object", "properties": {"task_spec": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"diff": {"type": "string"}}},
        default_risk_tier="MEDIUM",
        quota_ram_mb=256
    ),
    SpecialistRole.QA_RELIABILITY_ENGINEER: SpecialistArchetypeContract(
        role=SpecialistRole.QA_RELIABILITY_ENGINEER,
        division="Engineering",
        description="Executes test suites, measures coverage, diagnoses regression assertions, and runs Ralph loops.",
        allowed_capabilities=["run_pytest", "inspect_traceback", "verify_assertion"],
        input_schema={"type": "object", "properties": {"test_target": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"passed": {"type": "boolean"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.DEVOPS_PLATFORM_ADMIN: SpecialistArchetypeContract(
        role=SpecialistRole.DEVOPS_PLATFORM_ADMIN,
        division="Operations",
        description="Audits POSIX process trees, inspects disk quotas, supervises systemd, and provisions venvs.",
        allowed_capabilities=["ps", "df", "free", "venv_create", "pip_install_isolated"],
        input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"stdout": {"type": "string"}}},
        default_risk_tier="HIGH",
        quota_ram_mb=512
    ),
    SpecialistRole.CYBERSECURITY_DEFENSE_AUDITOR: SpecialistArchetypeContract(
        role=SpecialistRole.CYBERSECURITY_DEFENSE_AUDITOR,
        division="Cybersecurity",
        description="Scans source code for AST vulnerabilities, leaks of credentials, and license compliance.",
        allowed_capabilities=["ast_security_scan", "secret_scan", "license_audit"],
        input_schema={"type": "object", "properties": {"target_path": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"findings": {"type": "array"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.FINANCIAL_ACCOUNTING_ANALYST: SpecialistArchetypeContract(
        role=SpecialistRole.FINANCIAL_ACCOUNTING_ANALYST,
        division="Finance",
        description="Performs ledger reconciliations, audits API cloud billing, and enforces DoA spending ceilings.",
        allowed_capabilities=["reconcile_ledger", "audit_spending", "verify_invoice"],
        input_schema={"type": "object", "properties": {"period": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"reconciled": {"type": "boolean"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.LEGAL_COMPLIANCE_AUDITOR: SpecialistArchetypeContract(
        role=SpecialistRole.LEGAL_COMPLIANCE_AUDITOR,
        division="Compliance",
        description="Audits open-source licenses, data privacy policies, and regulatory hold records.",
        allowed_capabilities=["audit_licenses", "check_gdpr_pii", "verify_terms"],
        input_schema={"type": "object", "properties": {"packages": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"approved": {"type": "boolean"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.RESEARCH_INTELLIGENCE_ANALYST: SpecialistArchetypeContract(
        role=SpecialistRole.RESEARCH_INTELLIGENCE_ANALYST,
        division="Intelligence",
        description="Conducts public technical literature research, competitive analysis, and citation synthesis.",
        allowed_capabilities=["curl", "search_web", "extract_citations", "markdown_synthesis"],
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"brief": {"type": "string"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.CUSTOMER_SUPPORT_SPECIALIST: SpecialistArchetypeContract(
        role=SpecialistRole.CUSTOMER_SUPPORT_SPECIALIST,
        division="Support",
        description="Assists corporate employees with ticketing triage, diagnostic classification, and unblocking.",
        allowed_capabilities=["intake_ticket", "diagnose_blocker", "return_resolution"],
        input_schema={"type": "object", "properties": {"ticket": {"type": "object"}}},
        output_schema={"type": "object", "properties": {"resolved": {"type": "boolean"}}},
        default_risk_tier="LOW",
        quota_ram_mb=128
    ),
    SpecialistRole.SALES_GROWTH_SPECIALIST: SpecialistArchetypeContract(
        role=SpecialistRole.SALES_GROWTH_SPECIALIST,
        division="Growth",
        description="Tracks commercial causality, manages conversion pipelines, and analyzes customer interaction data.",
        allowed_capabilities=["track_causality", "analyze_pipeline", "draft_outreach"],
        input_schema={"type": "object", "properties": {"lead_data": {"type": "object"}}},
        output_schema={"type": "object", "properties": {"conversion_plan": {"type": "object"}}},
        default_risk_tier="LOW",
        quota_ram_mb=256
    ),
    SpecialistRole.DATA_ENGINEERING_SPECIALIST: SpecialistArchetypeContract(
        role=SpecialistRole.DATA_ENGINEERING_SPECIALIST,
        division="Data_AI",
        description="Executes structured SQLite/DuckDB queries, transforms tabular datasets, and builds pipelines.",
        allowed_capabilities=["sqlite_query", "csv_transform", "parquet_convert"],
        input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"rows": {"type": "array"}}},
        default_risk_tier="LOW",
        quota_ram_mb=512
    ),
    SpecialistRole.DESKTOP_GUI_OPERATOR: SpecialistArchetypeContract(
        role=SpecialistRole.DESKTOP_GUI_OPERATOR,
        division="Automation",
        description="Executes 14 desktop GUI primitives, coordinate visual grounding, and screen observations.",
        allowed_capabilities=["observe", "click", "type_text", "screenshot", "verify"],
        input_schema={"type": "object", "properties": {"workflow": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"evidence_hash": {"type": "string"}}},
        default_risk_tier="MEDIUM",
        quota_ram_mb=512
    ),
}
