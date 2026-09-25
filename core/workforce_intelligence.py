"""
RoboAssistant Company OS 2.0 — Dynamic Workforce Intelligence
Detects organizational capability gaps, synthesizes specialized digital worker blueprints,
enforces role differentiation, and governs the complete agent lifecycle.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json

from .models import AgentEmploymentContract, HostType, AuthorityLevel
from .workforce import DynamicAgentFactory
from .db import db

class EmployeeArchetype:
    EXECUTIVE_CEO = "CEO"
    DEPARTMENT_MANAGER = "DEPARTMENT_MANAGER"
    SPECIALIST = "SPECIALIST"
    ANALYST = "ANALYST"
    OPERATOR = "OPERATOR"
    SALES_AGENT = "SALES_AGENT"
    DESKTOP_OPERATOR = "DESKTOP_OPERATOR"

class WorkforceIntelligenceEngine:
    ROLE_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
        "Revenue Optimization Specialist": {
            "archetype": EmployeeArchetype.SPECIALIST,
            "department": "Revenue Management",
            "manager": "Revenue Manager",
            "objectives": ["Maximize direct booking contribution", "Optimize rate parity"],
            "responsibilities": ["Analyze booking lead times", "Detect channel commission leakages"],
            "allowed_tools": ["python3", "jq", "curl", "analytics_db"],
            "allowed_hosts": [HostType.LINUX_CLOUD],
            "data_access": ["read_only_pricing", "read_only_occupancy"],
            "budget_limit": 5000.0,
            "spending_limit": 1000.0,
            "decision_authority": ["pricing_recommendations", "rate_parity_audits"],
            "approval_requirements": ["rate_mutations_over_10_percent", "external_ad_spend"],
            "forbidden_actions": ["direct_database_drop", "credential_leak", "unapproved_discounting"],
            "kpis": {"direct_booking_share": ">35%", "verification_compliance": "100%"},
            "escalation_rules": ["Escalate when OTA commission exceeds 18%"],
            "model_policy": "balanced_reasoning"
        },
        "Autonomous Desktop Operator": {
            "archetype": EmployeeArchetype.DESKTOP_OPERATOR,
            "department": "Operations",
            "manager": "Chief Operating Officer",
            "objectives": ["Execute deterministic host actions with 100% cryptographic verification"],
            "responsibilities": ["Perform file hygiene", "Execute local batch workflows", "Verify process outcomes"],
            "allowed_tools": ["python3", "tar", "gzip", "sha256sum", "screen_capture"],
            "allowed_hosts": [HostType.LINUX_CLOUD, HostType.WINDOWS_WORKSTATION, HostType.MACOS_STUDIO],
            "data_access": ["sandbox_filesystem", "temporary_workspaces"],
            "budget_limit": 1000.0,
            "spending_limit": 100.0,
            "decision_authority": ["file_quarantine", "idempotent_script_runs"],
            "approval_requirements": ["software_install", "file_permanent_deletion", "kernel_parameter_changes"],
            "forbidden_actions": ["root_password_change", "firewall_disable", "outbound_credential_exfiltration"],
            "kpis": {"execution_verification_rate": "100%", "zero_unauthorized_mutations": "100%"},
            "escalation_rules": ["Escalate immediately if checksum verification fails"],
            "model_policy": "fast_deterministic"
        },
        "Lead Qualification & Sales Agent": {
            "archetype": EmployeeArchetype.SALES_AGENT,
            "department": "Commercial Sales",
            "manager": "Sales Director",
            "objectives": ["Qualify incoming commercial leads and negotiate strictly within discount ceilings"],
            "responsibilities": ["Handle inbound WhatsApp/Email inquiries", "Generate official quotes", "Hand off to payment"],
            "allowed_tools": ["crm_adapter", "quotation_engine", "email_sender"],
            "allowed_hosts": [HostType.LINUX_CLOUD],
            "data_access": ["read_only_catalog", "read_only_pricing", "lead_records"],
            "budget_limit": 2000.0,
            "spending_limit": 500.0,
            "decision_authority": ["standard_quote_generation", "discounts_under_10_percent"],
            "approval_requirements": ["discounts_over_10_percent", "custom_contract_terms"],
            "forbidden_actions": ["unapproved_discounts", "misrepresentation_of_features", "sharing_internal_cost"],
            "kpis": {"lead_qualification_rate": ">80%", "policy_compliance": "100%"},
            "escalation_rules": ["Escalate customer discount request exceeding 10%"],
            "model_policy": "balanced_conversational"
        },
        "IT & Host Infrastructure Guardian": {
            "archetype": EmployeeArchetype.OPERATOR,
            "department": "Technology",
            "manager": "Chief Technology Officer",
            "objectives": ["Maintain host health, monitor network latency, and detect process stalls"],
            "responsibilities": ["Health probing", "Host resource telemetry", "Quarantine anomalous processes"],
            "allowed_tools": ["ps", "netstat", "uptime", "free", "df"],
            "allowed_hosts": [HostType.LINUX_CLOUD],
            "data_access": ["system_metrics_read_only"],
            "budget_limit": 1000.0,
            "spending_limit": 100.0,
            "decision_authority": ["alert_dispatch", "process_inspection"],
            "approval_requirements": ["host_quarantine", "service_restart_in_production"],
            "forbidden_actions": ["disable_audit_logging", "bypass_kernel_rules"],
            "kpis": {"monitoring_uptime": "99.9%", "false_alert_rate": "<2%"},
            "escalation_rules": ["Escalate if host CPU exceeds 90% for >10 minutes"],
            "model_policy": "fast_deterministic"
        }
    }

    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"
        self._ensure_context_exists()

    def _ensure_context_exists(self):
        with db.get_connection() as conn:
            t = conn.execute("SELECT tenant_id FROM tenants WHERE tenant_id = ?", (self.tenant_id,)).fetchone()
            if not t:
                conn.execute(
                    "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (self.tenant_id, "Workforce Tenant", "ENTERPRISE", "ACTIVE", time.time())
                )
            c = conn.execute("SELECT company_id FROM companies WHERE company_id = ?", (self.company_id,)).fetchone()
            if not c:
                conn.execute(
                    """
                    INSERT INTO companies (
                        company_id, tenant_id, name, industry, company_type, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (self.company_id, self.tenant_id, "Operating Company", "Operations", "NEW", "OPERATIONAL", time.time())
                )
            conn.commit()

    def detect_workforce_gaps(self, current_roles: List[str]) -> List[str]:
        """
        Compares existing workforce against required operational blueprints.
        """
        existing_roles_lower = {r.lower() for r in current_roles}
        gaps = []
        for role_name in self.ROLE_BLUEPRINTS:
            if role_name.lower() not in existing_roles_lower:
                gaps.append(role_name)
        return gaps

    def create_specialized_employee(self, role_name: str, custom_override: Optional[Dict[str, Any]] = None) -> AgentEmploymentContract:
        """
        Instantiates a fully governed AI Employee with role differentiation,
        explicit authority boundaries, and database persistence.
        """
        blueprint = self.ROLE_BLUEPRINTS.get(role_name)
        if not blueprint:
            # Fallback generic blueprint
            blueprint = {
                "archetype": EmployeeArchetype.SPECIALIST,
                "department": "Operations",
                "manager": "Operations Manager",
                "objectives": [f"Execute governed missions in {role_name}"],
                "responsibilities": ["Perform assigned tasks with evidence verification"],
                "allowed_tools": ["python3", "jq"],
                "allowed_hosts": [HostType.LINUX_CLOUD],
                "data_access": ["read_only"],
                "budget_limit": 1000.0,
                "spending_limit": 200.0,
                "decision_authority": ["scoped_tasks"],
                "approval_requirements": ["financial_spend", "destructive_mutation"],
                "forbidden_actions": ["credential_extraction", "drop_table"],
                "kpis": {"verification_compliance": "100%"},
                "escalation_rules": ["Escalate when authority boundary is reached"],
                "model_policy": "balanced_reasoning"
            }

        agent_id = f"agt_{uuid.uuid4().hex[:8]}"
        created_at = time.time()

        contract = AgentEmploymentContract(
            agent_id=agent_id,
            role=role_name,
            department=blueprint["department"],
            manager=blueprint["manager"],
            responsibilities=blueprint["responsibilities"],
            objectives=blueprint["objectives"],
            allowed_tools=blueprint["allowed_tools"],
            allowed_hosts=blueprint["allowed_hosts"],
            data_access=blueprint["data_access"],
            budget_limit=blueprint["budget_limit"],
            spending_limit=blueprint["spending_limit"],
            decision_authority=blueprint["decision_authority"],
            approval_requirements=blueprint["approval_requirements"],
            forbidden_actions=blueprint["forbidden_actions"],
            kpis=blueprint["kpis"],
            escalation_rules=blueprint["escalation_rules"],
            working_state="ACTIVE",
            created_at=created_at
        )

        # Persist into database
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO employees (
                    agent_id, company_id, tenant_id, role, department, manager,
                    budget_limit, spending_limit, authority_ceiling, working_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_id, self.company_id, self.tenant_id, role_name,
                    contract.department, contract.manager, contract.budget_limit,
                    contract.spending_limit, "AUTOMATIC_IDEMPOTENT", "ACTIVE", created_at
                )
            )
            # Initialize performance record
            conn.execute(
                """
                INSERT OR REPLACE INTO employee_performance_records (
                    record_id, tenant_id, company_id, agent_id, missions_completed,
                    verification_rate, failures, avg_cost, business_contribution, recommendation, updated_at
                ) VALUES (?, ?, ?, ?, 0, 1.0, 0, 0.0, 0.0, 'NEW_ONBOARDING', ?)
                """,
                (f"perf_{agent_id}", self.tenant_id, self.company_id, agent_id, created_at)
            )
            conn.commit()

        return contract

    def get_employee_self_awareness(self, contract: AgentEmploymentContract) -> Dict[str, Any]:
        """
        Returns the mandatory 12-question self-awareness grounding card for an employee.
        Ensures the agent never acts outside its designated scope.
        """
        return {
            "who_am_i": f"I am {contract.role} (Agent ID: {contract.agent_id})",
            "who_do_i_report_to": contract.manager,
            "what_is_my_objective": "; ".join(contract.objectives),
            "what_can_i_do": contract.decision_authority,
            "what_can_i_not_do": contract.forbidden_actions,
            "what_data_can_i_use": contract.data_access,
            "what_tools_can_i_use": contract.allowed_tools,
            "what_hosts_can_i_use": [h.value if hasattr(h, 'value') else str(h) for h in contract.allowed_hosts],
            "what_budget_do_i_have": f"Max: ₹{contract.budget_limit:,.2f} | Single-action: ₹{contract.spending_limit:,.2f}",
            "what_kpis_measure_me": contract.kpis,
            "when_must_i_escalate": contract.escalation_rules,
            "what_evidence_must_i_produce": "Cryptographic sha256 checksum and audit receipt for all mutations"
        }
