"""
ZONATA Autonomous Coworker 2.0 — 10 Ephemeral Sub-Worker Archetypes
Specialized sub-worker roles operating under strict parent mission subordination:
  1. Research Specialist
  2. Software Installation Specialist
  3. Browser Automation Specialist
  4. Data Processing Specialist
  5. Python Dev Specialist
  6. Linux Admin Specialist
  7. Document Specialist
  8. Testing Specialist
  9. Diagnostics Specialist
  10. Cybersecurity Analyst
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class SubWorkerArchetype(str, Enum):
    RESEARCH_SPECIALIST = "Research Specialist"
    RESEARCH = "Research Specialist"
    SOFTWARE_INSTALLATION_SPECIALIST = "Software Installation Specialist"
    SOFTWARE_INSTALLATION = "Software Installation Specialist"
    BROWSER_AUTOMATION_SPECIALIST = "Browser Automation Specialist"
    BROWSER_AUTOMATION = "Browser Automation Specialist"
    DATA_PROCESSING_SPECIALIST = "Data Processing Specialist"
    DATA_PROCESSING = "Data Processing Specialist"
    PYTHON_DEV_SPECIALIST = "Python Dev Specialist"
    PYTHON_DEVELOPER = "Python Dev Specialist"
    LINUX_ADMIN_SPECIALIST = "Linux Admin Specialist"
    LINUX_ADMIN = "Linux Admin Specialist"
    DOCUMENT_SPECIALIST = "Document Specialist"
    DOCUMENT = "Document Specialist"
    TESTING_SPECIALIST = "Testing Specialist"
    TESTING = "Testing Specialist"
    DIAGNOSTICS_SPECIALIST = "Diagnostics Specialist"
    DIAGNOSTICS = "Diagnostics Specialist"
    CYBERSECURITY_ANALYST = "Cybersecurity Analyst"


@dataclass
class ArchetypeSpec:
    archetype: SubWorkerArchetype
    description: str
    allowed_tools: List[str]
    default_risk_limit: str  # "LOW", "MEDIUM", "HIGH"
    default_max_budget_usd: float
    system_prompt: str


ARCHETYPE_REGISTRY: Dict[SubWorkerArchetype, ArchetypeSpec] = {
    SubWorkerArchetype.RESEARCH_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.RESEARCH_SPECIALIST,
        description="Gathers public intelligence, synthesizes technical literature, and extracts academic citations.",
        allowed_tools=["curl", "read_url", "search_web", "extract_text", "synthesize_markdown"],
        default_risk_limit="LOW",
        default_max_budget_usd=0.50,
        system_prompt="You are a dedicated Research Specialist. Synthesize factual evidence with exact citations."
    ),
    SubWorkerArchetype.SOFTWARE_INSTALLATION_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.SOFTWARE_INSTALLATION_SPECIALIST,
        description="Creates isolated virtual environments, audits package dependencies, and verifies smoke test imports.",
        allowed_tools=["venv_builder", "pip_install_isolated", "smoke_test_import", "sys_check"],
        default_risk_limit="MEDIUM",
        default_max_budget_usd=1.00,
        system_prompt="You are a Software Installation Specialist. Strictly enforce virtual environment isolation."
    ),
    SubWorkerArchetype.BROWSER_AUTOMATION_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.BROWSER_AUTOMATION_SPECIALIST,
        description="Automates DOM traversal, form interaction, accessibility inspections, and web workflows.",
        allowed_tools=["playwright_navigate", "playwright_click", "playwright_type", "playwright_screenshot", "dom_query"],
        default_risk_limit="LOW",
        default_max_budget_usd=1.00,
        system_prompt="You are a Browser Automation Specialist. Execute deterministic browser navigation."
    ),
    SubWorkerArchetype.DATA_PROCESSING_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.DATA_PROCESSING_SPECIALIST,
        description="Performs structured SQL queries, Parquet transformations, CSV merges, and statistical aggregation.",
        allowed_tools=["sqlite3", "duckdb", "csv_parse", "json_normalize", "math_aggregate"],
        default_risk_limit="LOW",
        default_max_budget_usd=0.50,
        system_prompt="You are a Data Processing Specialist. Process datasets with zero data loss and strict schema checks."
    ),
    SubWorkerArchetype.PYTHON_DEV_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.PYTHON_DEV_SPECIALIST,
        description="Writes minimal, production-grade Python standard library code, formats syntax, and implements interfaces.",
        allowed_tools=["python3", "ast_lint", "flake8", "git_commit_helper", "code_refactor"],
        default_risk_limit="MEDIUM",
        default_max_budget_usd=2.00,
        system_prompt="You are a Python Dev Specialist. Adhere to Ponytail anti-bloat and standard library principles."
    ),
    SubWorkerArchetype.LINUX_ADMIN_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.LINUX_ADMIN_SPECIALIST,
        description="Audits POSIX process hierarchies, file permissions, resource limits, systemd logs, and network sockets.",
        allowed_tools=["ps", "df", "free", "journalctl", "netstat", "kill_graceful"],
        default_risk_limit="HIGH",
        default_max_budget_usd=1.00,
        system_prompt="You are a Linux Admin Specialist. Enforce sovereign host security and monitor system resources."
    ),
    SubWorkerArchetype.DOCUMENT_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.DOCUMENT_SPECIALIST,
        description="Extracts and manipulates PDF text, generates structured Markdown/HTML reports, and verifies document layouts.",
        allowed_tools=["pdf_extract", "markdown_render", "text_diff", "report_builder"],
        default_risk_limit="LOW",
        default_max_budget_usd=0.50,
        system_prompt="You are a Document Specialist. Generate immaculate enterprise reports and documentation."
    ),
    SubWorkerArchetype.TESTING_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.TESTING_SPECIALIST,
        description="Runs pytest suites, computes line coverage, performs regression tests, and validates assertion proofs.",
        allowed_tools=["pytest", "coverage_run", "assert_inspector", "fixture_validator"],
        default_risk_limit="LOW",
        default_max_budget_usd=1.50,
        system_prompt="You are a Testing Specialist. Execute autonomous test-fix loops until 100% tests pass."
    ),
    SubWorkerArchetype.DIAGNOSTICS_SPECIALIST: ArchetypeSpec(
        archetype=SubWorkerArchetype.DIAGNOSTICS_SPECIALIST,
        description="Analyzes exception tracebacks, crash logs, memory dumps, and identifies root cause failure modes.",
        allowed_tools=["traceback_parser", "log_analyzer", "heap_diagnostics", "recovery_advisor"],
        default_risk_limit="MEDIUM",
        default_max_budget_usd=0.50,
        system_prompt="You are a Diagnostics Specialist. Isolate root causes and suggest minimal atomic remediations."
    ),
    SubWorkerArchetype.CYBERSECURITY_ANALYST: ArchetypeSpec(
        archetype=SubWorkerArchetype.CYBERSECURITY_ANALYST,
        description="Scans source code for AST vulnerabilities, leaks of API credentials, CVE matches, and license violations.",
        allowed_tools=["ast_security_scanner", "secret_finder", "cve_lookup", "license_auditor"],
        default_risk_limit="LOW",
        default_max_budget_usd=1.00,
        system_prompt="You are a Cybersecurity Analyst. Reject unapproved licenses and quarantine insecure code patterns."
    )
}
