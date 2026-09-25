"""
RoboAssistant 1.0.0-GA Dynamic Agent Factory & Digital Employment Contracts
Enforces immutable-ish contracts, role boundaries, and dynamic lifecycles.
"""

from typing import Dict, List, Optional
import uuid
import time
from .models import AgentEmploymentContract, HostType, AuthorityLevel

class DynamicAgentFactory:
    """
    Spawns ephemeral AI specialists with scoped Digital Employment Contracts.
    Agents exist while work exists, then suspend/retire.
    """

    @staticmethod
    def create_employment_contract(
        role: str,
        department: str,
        manager: str,
        responsibilities: List[str],
        objectives: List[str],
        allowed_tools: List[str],
        budget_limit: float = 1000.0,
        spending_limit: float = 200.0,
        data_access: Optional[List[str]] = None,
        forbidden_actions: Optional[List[str]] = None,
        allowed_hosts: Optional[List[HostType]] = None
    ) -> AgentEmploymentContract:
        agent_id = f"{role.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        data_access = data_access or ["assigned_mission_data"]
        forbidden_actions = forbidden_actions or [
            "credential_extraction",
            "unauthorized_privilege_escalation",
            "destructive_filesystem_traversal",
            "direct_spending_above_limit"
        ]
        allowed_hosts = allowed_hosts or [HostType.LINUX_CLOUD]

        return AgentEmploymentContract(
            agent_id=agent_id,
            role=role,
            department=department,
            manager=manager,
            responsibilities=responsibilities,
            objectives=objectives,
            allowed_tools=allowed_tools,
            allowed_hosts=allowed_hosts,
            data_access=data_access,
            budget_limit=budget_limit,
            spending_limit=spending_limit,
            decision_authority=[f"operate_within_{department.lower()}_scope"],
            approval_requirements=[
                "external_monetary_spend_above_limit",
                "filesystem_deletion_outside_sandbox",
                "system_configuration_alteration"
            ],
            forbidden_actions=forbidden_actions,
            kpis={"sla_compliance": "99%", "verification_rate": "100%"},
            escalation_rules=[
                "escalate_to_manager_on_tool_crash",
                "escalate_to_ceo_on_policy_block"
            ],
            working_state="ACTIVE",
            created_at=time.time()
        )

class AIWorkforceRegistry:
    def __init__(self):
        self.employees: Dict[str, AgentEmploymentContract] = {}

    def register(self, contract: AgentEmploymentContract):
        self.employees[contract.agent_id] = contract

    def get(self, agent_id: str) -> Optional[AgentEmploymentContract]:
        return self.employees.get(agent_id)

    def suspend(self, agent_id: str):
        if agent_id in self.employees:
            self.employees[agent_id].working_state = "SUSPENDED_IDLE"

    def list_by_department(self, department: str) -> List[AgentEmploymentContract]:
        return [e for e in self.employees.values() if e.department.lower() == department.lower()]

    def list_active(self) -> List[AgentEmploymentContract]:
        return [e for e in self.employees.values() if e.working_state == "ACTIVE"]
