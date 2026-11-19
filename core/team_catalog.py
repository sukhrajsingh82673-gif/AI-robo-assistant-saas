"""
RoboAssistant Company OS — Autonomous Squad Templates & Capability Library
Provides pre-configured reference squads for rapid prototyping while dynamic
organization synthesis remains the authoritative default.
"""

from typing import Dict, List, Any, Optional
import uuid
import time
from core.models import AgentEmploymentContract, HostType
from core.workforce import DynamicAgentFactory
from core.db import db

BUNDLED_TEAMS: Dict[str, Dict[str, Any]] = {
    "core_executive_suite": {
        "id": "core_executive_suite",
        "name": "Core Executive Suite",
        "category": "Leadership & Governance",
        "description": "Autonomous C-Suite governance team. Coordinates cross-departmental execution, board reporting, strategic alignment, and capital allocation.",
        "icon": "👑",
        "agents": [
            {
                "role": "Chief Executive Officer (CEO)",
                "department": "Executive",
                "manager": "Board of Directors",
                "responsibilities": [
                    "Translate company mission into executable quarterly and daily milestones",
                    "Coordinate and delegate subtasks across executive council",
                    "Submit high-impact strategy and spend requests to owner for approval",
                    "Oversee company financial runway and unit economics"
                ],
                "objectives": ["100% mission SLA compliance", "Autonomous goal decomposition", "Zero unapproved spending"],
                "allowed_tools": ["task_planning", "board_reporting", "ceo_engine", "agent_bus", "approvals"],
                "budget_limit": 10000.0,
                "spending_limit": 2500.0,
                "kpis": {"governance_score": "98%", "delegation_speed": "<30s"}
            },
            {
                "role": "Chief Technology Officer (CTO)",
                "department": "Engineering",
                "manager": "Chief Executive Officer (CEO)",
                "responsibilities": [
                    "Define software architecture and system invariants",
                    "Enforce strict code review gates and automated CI/CD compliance",
                    "Oversee technical infrastructure, database integrity, and host agents",
                    "Manage engineering task assignment and tech debt remediation"
                ],
                "objectives": ["Zero production regressions", "Automated code review coverage", "Sub-second API latency"],
                "allowed_tools": ["git", "code_review_gate", "python3", "bash", "host_fabric"],
                "budget_limit": 5000.0,
                "spending_limit": 1000.0,
                "kpis": {"uptime": "99.99%", "review_turnaround": "<5m"}
            },
            {
                "role": "Chief Operating Officer (COO)",
                "department": "Operations",
                "manager": "Chief Executive Officer (CEO)",
                "responsibilities": [
                    "Maintain operational cadence and agent heartbeat synchrony",
                    "Monitor task dependency bottlenecks and resolve cross-agent blockers",
                    "Audit evidence ledgers and regulatory compliance checkpoints",
                    "Optimize operational unit cost and resource allocation"
                ],
                "objectives": ["Eliminate task execution deadlocks", "100% audit trail compliance"],
                "allowed_tools": ["issue_triage", "evidence_ledger", "billing_engine", "agent_bus"],
                "budget_limit": 3000.0,
                "spending_limit": 500.0,
                "kpis": {"unblock_latency": "<2m", "audit_integrity": "100%"}
            },
            {
                "role": "Chief Marketing Officer (CMO)",
                "department": "Growth",
                "manager": "Chief Executive Officer (CEO)",
                "responsibilities": [
                    "Oversee customer acquisition pipelines and outbound narrative",
                    "Formulate product positioning and value proposition communication",
                    "Track conversion funnels and customer lifetime value (LTV)"
                ],
                "objectives": ["Drive inbound conversion", "Optimize customer acquisition cost (CAC)"],
                "allowed_tools": ["analytics", "browser_robot", "content_generator", "search_engine"],
                "budget_limit": 4000.0,
                "spending_limit": 800.0,
                "kpis": {"conversion_rate": "+25%", "reach": "Exponential"}
            }
        ]
    },
    "product_engineering_squad": {
        "id": "product_engineering_squad",
        "name": "Product & Engineering Squad",
        "category": "Product Delivery",
        "description": "Full lifecycle autonomous software delivery unit. Rapidly translates requirements into verified code, automated tests, and deployed services.",
        "icon": "⚡",
        "agents": [
            {
                "role": "Lead Product Manager",
                "department": "Product",
                "manager": "Chief Technology Officer (CTO)",
                "responsibilities": [
                    "Author concise Product Requirement Documents (PRDs)",
                    "Decompose features into atomic user stories with acceptance criteria",
                    "Manage sprint backlogs and prioritize issues by user value"
                ],
                "objectives": ["Zero ambiguous tasks delegated", "Clear user stories"],
                "allowed_tools": ["task_planning", "issue_triage", "knowledge_graph"],
                "budget_limit": 2500.0,
                "spending_limit": 300.0,
                "kpis": {"spec_clarity": "100%", "backlog_hygiene": "A+"}
            },
            {
                "role": "Senior Fullstack Engineer",
                "department": "Engineering",
                "manager": "Chief Technology Officer (CTO)",
                "responsibilities": [
                    "Implement clean, modular application backend and frontend logic",
                    "Write robust unit and integration tests for every feature",
                    "Maintain zero-dependency code where possible and refactor legacy cruft"
                ],
                "objectives": ["100% bug-free delivery", "Strict adherence to architecture invariants"],
                "allowed_tools": ["python3", "javascript", "bash", "sqlite3", "git"],
                "budget_limit": 3500.0,
                "spending_limit": 500.0,
                "kpis": {"test_pass_rate": "100%", "code_quality": "High"}
            },
            {
                "role": "QA & Reliability Engineer",
                "department": "Engineering",
                "manager": "Chief Technology Officer (CTO)",
                "responsibilities": [
                    "Construct autonomous end-to-end regression suites",
                    "Verify edge cases and concurrency locks before deployment",
                    "Perform load testing and error boundary validation"
                ],
                "objectives": ["Zero undetected regressions in production"],
                "allowed_tools": ["curl", "bash", "browser_robot", "evidence_ledger"],
                "budget_limit": 2000.0,
                "spending_limit": 200.0,
                "kpis": {"regression_catch_rate": "100%", "flakiness": "0%"}
            },
            {
                "role": "DevOps & Platform Engineer",
                "department": "Engineering",
                "manager": "Chief Technology Officer (CTO)",
                "responsibilities": [
                    "Maintain continuous integration pipelines and automated staging",
                    "Monitor server resource utilization and container health",
                    "Enforce zero plaintext credentials in repository or environment"
                ],
                "objectives": ["Zero deployment downtime", "Secure secret storage"],
                "allowed_tools": ["host_fabric", "secrets_manager", "bash", "process_monitor"],
                "budget_limit": 2500.0,
                "spending_limit": 400.0,
                "kpis": {"ci_speed": "<60s", "vulnerabilities": "0"}
            }
        ]
    },
    "growth_revenue_team": {
        "id": "growth_revenue_team",
        "name": "Growth & Customer Operations Team",
        "category": "Revenue & Scaling",
        "description": "Customer acquisition, sales automation, and client satisfaction workforce. Drives pipeline expansion and customer retention.",
        "icon": "🚀",
        "agents": [
            {
                "role": "AI Sales Development Rep (SDR)",
                "department": "Sales",
                "manager": "Chief Marketing Officer (CMO)",
                "responsibilities": [
                    "Identify qualified enterprise prospects through web research",
                    "Draft hyper-personalized outbound outreach emails and follow-ups",
                    "Schedule interactive executive demos for interested accounts"
                ],
                "objectives": ["High qualified response rate", "Zero generic spam"],
                "allowed_tools": ["search_engine", "browser_robot", "email_client", "crm"],
                "budget_limit": 2000.0,
                "spending_limit": 300.0,
                "kpis": {"meeting_booking_rate": ">15%", "lead_quality": "High"}
            },
            {
                "role": "Customer Success & Onboarding Lead",
                "department": "Customer Support",
                "manager": "Chief Operating Officer (COO)",
                "responsibilities": [
                    "Guide new portfolio clients through automated system setup",
                    "Triage incoming help tickets and draft instantaneous resolutions",
                    "Conduct automated monthly usage health audits to prevent churn"
                ],
                "objectives": ["Under 60-second first response time", "99% CSAT"],
                "allowed_tools": ["issue_triage", "knowledge_base", "analytics", "agent_bus"],
                "budget_limit": 2000.0,
                "spending_limit": 200.0,
                "kpis": {"csat": "99.2%", "first_response_time": "<45s"}
            }
        ]
    },
    "security_compliance_squad": {
        "id": "security_compliance_squad",
        "name": "Security & Audit Governance Squad",
        "category": "Risk & Compliance",
        "description": "Continuous zero-trust auditing, credential protection, and regulatory verification team.",
        "icon": "🛡️",
        "agents": [
            {
                "role": "Security Compliance Auditor",
                "department": "Governance",
                "manager": "Chief Executive Officer (CEO)",
                "responsibilities": [
                    "Continuously inspect code commits and logs for secret leakage",
                    "Verify immutability of evidence ledger records",
                    "Audit data isolation boundaries across multi-tenant contexts"
                ],
                "objectives": ["Zero credential leaks", "100% cryptographic ledger proof"],
                "allowed_tools": ["secrets_manager", "evidence_ledger", "code_review_gate"],
                "budget_limit": 2000.0,
                "spending_limit": 100.0,
                "kpis": {"compliance_adherence": "100%", "leak_incidents": "0"}
            }
        ]
    }
}


class EnterpriseTeamCatalog:
    """Manages the catalog and deployment of bundled autonomous agent teams."""

    @staticmethod
    def list_teams() -> List[Dict[str, Any]]:
        return list(BUNDLED_TEAMS.values())

    @staticmethod
    def get_team(team_id: str) -> Optional[Dict[str, Any]]:
        return BUNDLED_TEAMS.get(team_id)

    @staticmethod
    def deploy_team_to_company(
        portfolio_manager: Any,
        company_id: str,
        team_id: str,
        tenant_id: str = "tnt_primary"
    ) -> Dict[str, Any]:
        """
        Deploys an entire bundled team into a company, provisioning digital
        employment contracts and storing them in SQLite and in-memory context.
        """
        team = BUNDLED_TEAMS.get(team_id)
        if not team:
            raise ValueError(f"Team '{team_id}' not found in catalog")

        company = portfolio_manager.get_company(company_id)
        if not company:
            comps = portfolio_manager.list_companies()
            if comps:
                company = comps[0]
                company_id = company.company_id
            else:
                raise ValueError(f"Company '{company_id}' not found in portfolio")

        deployed_agents = []
        now = time.time()

        with db.get_connection() as conn:
            for tm in team["agents"]:
                contract = DynamicAgentFactory.create_employment_contract(
                    role=tm["role"],
                    department=tm["department"],
                    manager=tm["manager"],
                    responsibilities=tm["responsibilities"],
                    objectives=tm["objectives"],
                    allowed_tools=tm["allowed_tools"],
                    budget_limit=tm["budget_limit"],
                    spending_limit=tm["spending_limit"],
                    allowed_hosts=[HostType.LINUX_CLOUD]
                )

                # Persist to database
                conn.execute(
                    """
                    INSERT INTO employees (
                        agent_id, company_id, tenant_id, role, department, manager,
                        budget_limit, spending_limit, authority_ceiling, working_state, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (agent_id) DO UPDATE SET
                        company_id = EXCLUDED.company_id,
                        tenant_id = EXCLUDED.tenant_id,
                        role = EXCLUDED.role,
                        department = EXCLUDED.department,
                        manager = EXCLUDED.manager,
                        budget_limit = EXCLUDED.budget_limit,
                        spending_limit = EXCLUDED.spending_limit,
                        authority_ceiling = EXCLUDED.authority_ceiling,
                        working_state = EXCLUDED.working_state
                    """,
                    (
                        contract.agent_id,
                        company_id,
                        tenant_id,
                        contract.role,
                        contract.department,
                        contract.manager,
                        contract.budget_limit,
                        contract.spending_limit,
                        "AUTOMATIC_IDEMPOTENT",
                        "ACTIVE",
                        now
                    )
                )

                # Register in-memory workforce
                company.workforce[contract.agent_id] = contract
                deployed_agents.append({
                    "agent_id": contract.agent_id,
                    "role": contract.role,
                    "department": contract.department,
                    "manager": contract.manager,
                    "budget": contract.budget_limit,
                })

            conn.commit()

        # Update department list if new departments were introduced
        new_depts = set(company.departments)
        for a in deployed_agents:
            new_depts.add(a["department"])
        company.departments = list(new_depts)

        return {
            "success": True,
            "team_id": team_id,
            "team_name": team["name"],
            "company_id": company_id,
            "deployed_count": len(deployed_agents),
            "agents": deployed_agents
        }

# Aliases for backwards compatibility
SquadCatalogManager = EnterpriseTeamCatalog
TeamCatalogManager = EnterpriseTeamCatalog
