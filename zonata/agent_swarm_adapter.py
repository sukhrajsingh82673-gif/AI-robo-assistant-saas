"""
ZONATA Universal AI CEO — Workforce Orchestration Adapter
Connects the dynamic organizational discovery, health diagnostics, and executive cognition
to the Governed Multi-Agent Workforce Orchestrator.

Constitutional Invariant:
ZONATA remains the sovereign authority. The workforce orchestrator coordinates specialists,
while ZONATA verifies truth, checks budgets, enforces policies, and seals the Evidence Ledger.
"""

from typing import Dict, List, Optional, Any
import time
import uuid

from core.workforce_orchestrator import (
    DynamicWorkforcePlanner,
    SpecialistRoleCatalog,
    StructuredMissionResult
)
from core.workforce_runtime import SwarmWorkforceRuntime
from core.evidence_ledger import EvidenceLedger

# Singleton planner instance
_shared_runtime = SwarmWorkforceRuntime()
_shared_ledger = EvidenceLedger()
workforce_planner = DynamicWorkforcePlanner(runtime=_shared_runtime, ledger=_shared_ledger)


class AgentWorkforceAdapter:
    """
    ZONATA-Native Adapter for Governed Multi-Agent Workforce Orchestration.
    """

    @classmethod
    def create_mission_workforce(
        cls,
        tenant_id: str,
        company_id: str,
        mission_objective: str,
        budget_usd: float = 100.0,
        max_delegation_depth: int = 3
    ) -> Dict[str, Any]:
        mission_id = f"msn_{uuid.uuid4().hex[:8]}"
        return workforce_planner.plan_workforce_for_objective(
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            objective=mission_objective,
            budget_usd=budget_usd,
            max_delegation_depth=max_delegation_depth
        )

    @classmethod
    def execute_workforce(
        cls,
        workforce_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> StructuredMissionResult:
        return workforce_planner.execute_workforce_mission(
            workforce_id=workforce_id,
            input_parameters=parameters
        )

    @classmethod
    def list_workforces(
        cls,
        tenant_id: str,
        company_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return workforce_planner.list_workforces(tenant_id=tenant_id, company_id=company_id)

    @classmethod
    def get_workforce_details(cls, workforce_id: str) -> Dict[str, Any]:
        return workforce_planner.get_workforce_status(workforce_id)

    @classmethod
    def kill_workforce(cls, workforce_id: str, reason: str = "HOST_OVERRIDE") -> bool:
        return workforce_planner.quarantine_workforce(workforce_id, reason=reason)

    @classmethod
    def get_specialist_catalog(cls) -> List[Dict[str, Any]]:
        return SpecialistRoleCatalog.list_roles()

    @classmethod
    def run_sales_bottleneck_demonstration(
        cls,
        tenant_id: str = "tnt_primary",
        company_id: str = "cmp_demo"
    ) -> Dict[str, Any]:
        """
        Controlled Demonstration Test:
        Objective: 'Analyze our current sales pipeline and identify the top three operational bottlenecks.'
        Synthesizes Sales Analyst + Operations Analyst + Verification Specialist.
        """
        objective = "Analyze our current sales pipeline and identify the top three operational bottlenecks."
        plan = cls.create_mission_workforce(
            tenant_id=tenant_id,
            company_id=company_id,
            mission_objective=objective,
            budget_usd=100.0
        )
        workforce_id = plan["workforce_id"]
        result = cls.execute_workforce(workforce_id)

        return {
            "workforce_id": workforce_id,
            "objective": objective,
            "squad": plan["specialists"],
            "result": result.to_dict(),
            "evidence_count": len(result.evidence_refs),
            "status": "COMPLETED"
        }
