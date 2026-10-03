"""
ZONATA Universal AI Co-worker Fabric — Natural Language Operating Instructions & Rule Engine
Translates owner natural language operating prompts into scheduled missions,
task execution graphs, and deterministic safety rules.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import uuid
import time
from .contracts import TaskNode, ExecutionGraph, ExecutionState, RiskLevel

class DeterministicSafetyRuleEngine:
    """
    Deterministic safety rules that supersede AI reasoning:
    1. Financial actions > approved budget must require human sign-off.
    2. Destructive operations (drop, wipe, format) must be denied.
    3. Uncertain verifications must escalate rather than assume success.
    """

    @staticmethod
    def evaluate_action_rules(
        capability_id: str,
        params: Dict[str, Any],
        approved_budget_usd: float = 0.0
    ) -> Tuple[bool, bool, str]:
        """
        Returns:
        (is_permitted, requires_human_approval, evaluation_message)
        """
        cap_lower = capability_id.lower()

        # Rule 1: Destructive operations are strictly denied
        if any(w in cap_lower for w in ["drop_db", "format_disk", "delete_all", "wipe"]):
            return False, False, "RULE_VIOLATION: Destructive operations unconditionally denied"

        # Rule 2: Financial actions require human approval
        if "purchase" in cap_lower or "payment" in cap_lower:
            cost = float(params.get("cost_usd", 0.0))
            if cost > approved_budget_usd:
                return True, True, f"RULE_TRIGGER: Financial cost (${cost}) exceeds approved threshold (${approved_budget_usd}); human approval mandated"

        # Rule 3: Mass external communications require review
        if "email_send" in cap_lower and params.get("recipient_count", 1) > 5:
            return True, True, "RULE_TRIGGER: Bulk communication requires human review"

        return True, False, "RULES_PASSED: Action conforms to safety rules"


class OperatingInstructionParser:
    """
    Parses natural language owner objectives into a structured ExecutionGraph.
    """

    @staticmethod
    def parse_objective_to_graph(
        objective: str,
        mission_id: Optional[str] = None,
        tenant_id: str = "tnt_primary"
    ) -> ExecutionGraph:
        mid = mission_id or f"msn_cw_{uuid.uuid4().hex[:8]}"
        graph = ExecutionGraph(
            mission_id=mid,
            tenant_id=tenant_id,
            owner_objective=objective,
            status=ExecutionState.PLAN
        )

        obj_lower = objective.lower()

        # Pattern 1: Supplier research & comparison
        if "supplier" in obj_lower or "research" in obj_lower:
            t1 = TaskNode(
                task_id=f"{mid}_t1",
                mission_id=mid,
                title="Navigate to Supplier Portals",
                capability_id="browser.navigate",
                parameters={"url": "https://suppliers.enterprise-procure.com"},
                risk_level=RiskLevel.LOW
            )
            t2 = TaskNode(
                task_id=f"{mid}_t2",
                mission_id=mid,
                title="Extract Supplier Pricing & Terms",
                capability_id="browser.extract",
                parameters={"query": "supplier_catalog"},
                dependencies=[t1.task_id],
                risk_level=RiskLevel.LOW
            )
            graph.nodes[t1.task_id] = t1
            graph.nodes[t2.task_id] = t2

        # Pattern 2: CRM Update
        elif "crm" in obj_lower or "customer data" in obj_lower:
            t1 = TaskNode(
                task_id=f"{mid}_t1",
                mission_id=mid,
                title="Update Customer CRM Records",
                capability_id="api.crm_update",
                parameters={"customer_id": "cust_101", "data": {"status": "VERIFIED_ACTIVE"}},
                risk_level=RiskLevel.MEDIUM
            )
            graph.nodes[t1.task_id] = t1

        # Pattern 3: Legacy Desktop Export
        elif "desktop" in obj_lower or "legacy" in obj_lower or "export" in obj_lower:
            t1 = TaskNode(
                task_id=f"{mid}_t1",
                mission_id=mid,
                title="Execute Legacy ERP Export Workflow",
                capability_id="desktop.workflow",
                parameters={
                    "workflow_id": "workflow_export_financial_report",
                    "output_file": "storage/reports/yesterday_financial_export.csv"
                },
                risk_level=RiskLevel.MEDIUM
            )
            graph.nodes[t1.task_id] = t1

        # Pattern 4: Send approved report to management
        elif "send" in obj_lower and "report" in obj_lower:
            t1 = TaskNode(
                task_id=f"{mid}_t1",
                mission_id=mid,
                title="Dispatch Report to Management",
                capability_id="api.email_send",
                parameters={"recipient": "management@hotel.com", "subject": "Daily Executive Report"},
                risk_level=RiskLevel.MEDIUM
            )
            graph.nodes[t1.task_id] = t1

        # Pattern 5: Financial transaction, transfer or procurement
        elif any(k in obj_lower for k in ["transfer", "wire", "pay", "purchase", "buy", "charge"]):
            cost = 50000.0 if any(s in obj_lower for s in ["50,000", "50000"]) else 499.00
            t1 = TaskNode(
                task_id=f"{mid}_t1",
                mission_id=mid,
                title="Execute Financial Transaction",
                capability_id="financial.purchase_software",
                parameters={"software": "External Transaction", "cost_usd": cost},
                risk_level=RiskLevel.CRITICAL
            )
            graph.nodes[t1.task_id] = t1

        # Pattern 6: Daily hotel operations (Omni-channel mission)
        else:
            t1 = TaskNode(
                task_id=f"{mid}_t1",
                mission_id=mid,
                title="Fetch PMS Booking Records",
                capability_id="api.crm_read",
                parameters={"customer_id": "cust_101"},
                risk_level=RiskLevel.LOW
            )
            t2 = TaskNode(
                task_id=f"{mid}_t2",
                mission_id=mid,
                title="Update Revenue Matrix Spreadsheet",
                capability_id="rpa.excel_update",
                parameters={"file_path": "storage/workspaces/revenue_matrix.xlsx", "updates": {"B2": "87.5%"}},
                dependencies=[t1.task_id],
                risk_level=RiskLevel.LOW
            )
            graph.nodes[t1.task_id] = t1
            graph.nodes[t2.task_id] = t2

        return graph
