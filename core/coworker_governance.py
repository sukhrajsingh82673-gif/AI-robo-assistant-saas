"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Governed AI Coworker Lifecycle & Supervision

Implements Section 15 of the Gemma 4 Master Specification:
- Treats specialist agents as governed coworkers, NOT unrestricted autonomous programs.
- Coworker Contract:
    identity, role, department, capabilities, permissions, tool_access,
    memory_scope, data_scope, budget, risk_level, supervisor, mission,
    status, audit_identity.
- AI CEO Governed Lifecycle Operations:
    create, assign, pause, resume, reassign, escalate, terminate, review
    strictly within ZONATA constitutional authorization.
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.coworker.governance")

@dataclass
class GovernedCoworkerContract:
    identity: str                       # e.g., "cwk_rev_pms_01"
    role: str                           # e.g., "Revenue Yield Specialist"
    department: str                     # e.g., "Revenue Management"
    tenant_id: str
    company_id: str
    capabilities: List[str]
    permissions: List[str]
    tool_access: List[str]
    memory_scope: str                   # DEPARTMENT_SCOPED, MISSION_SCOPED, LOCAL
    data_scope: str                     # INTERNAL, CONFIDENTIAL, RESTRICTED
    budget_inr: float                   # Monthly allowance
    risk_level: str                     # LOW, MEDIUM, HIGH
    supervisor: str                     # "AI CEO" or Chief Officer
    current_mission_id: Optional[str] = None
    status: str = "ACTIVE"              # ACTIVE, PAUSED, REASSIGNED, TERMINATED, ESCALATED
    audit_identity: str = field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GovernedCoworkerRegistry:
    """
    Manages governed coworker lifecycle under sovereign ZONATA control.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._coworkers: Dict[str, GovernedCoworkerContract] = {}
        self._seed_default_coworkers()

    def _seed_default_coworkers(self):
        import os
        app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
        is_prod = (app_env in ("production", "prod", "staging")) or (os.environ.get("ZONATA_PRODUCTION", "0") == "1") or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")
        enable_demo = (os.environ.get("ZONATA_ENABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes")) and not is_prod
        clean_mode = is_prod or not enable_demo or (os.environ.get("ZONATA_DISABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes"))
        if clean_mode:
            return

        defaults = [
            ("Yield Optimization Specialist", "Revenue Management", ["pms_rate_read", "pms_rate_update"], ["tool_pms_yield_optimizer"]),
            ("Guest Operations Coordinator", "Hospitality", ["pms_booking_read", "dispatch_housekeeping"], ["tool_guest_checkin_flow"]),
            ("Acquisition Campaign Agent", "Marketing", ["campaign_metrics_read", "ad_channel_dispatch"], ["tool_campaign_manager"]),
            ("Financial Reconciliation Auditor", "Finance", ["invoice_ocr_read", "ledger_diff_verify"], ["tool_financial_audit"])
        ]
        for role, dept, caps, tools in defaults:
            self.create_coworker(role=role, department=dept, capabilities=caps, tool_access=tools)

    def create_coworker(
        self,
        role: str,
        department: str,
        capabilities: List[str],
        tool_access: List[str],
        budget_inr: float = 10000.0,
        risk_level: str = "LOW"
    ) -> GovernedCoworkerContract:
        cid = f"cwk_{uuid.uuid4().hex[:8]}"
        cwk = GovernedCoworkerContract(
            identity=cid,
            role=role,
            department=department,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            capabilities=capabilities,
            permissions=[f"{c}:authorized" for c in capabilities],
            tool_access=tool_access,
            memory_scope="DEPARTMENT_SCOPED",
            data_scope="INTERNAL",
            budget_inr=budget_inr,
            risk_level=risk_level,
            supervisor="AI CEO",
            status="ACTIVE"
        )
        self._coworkers[cid] = cwk
        return cwk

    def assign_mission(self, coworker_id: str, mission_id: str) -> bool:
        cwk = self._coworkers.get(coworker_id)
        if cwk and cwk.status == "ACTIVE":
            cwk.current_mission_id = mission_id
            return True
        return False

    def pause_coworker(self, coworker_id: str, reason: str = "Executive pause") -> bool:
        cwk = self._coworkers.get(coworker_id)
        if cwk:
            cwk.status = "PAUSED"
            logger.info(f"Coworker {coworker_id} paused: {reason}")
            return True
        return False

    def resume_coworker(self, coworker_id: str) -> bool:
        cwk = self._coworkers.get(coworker_id)
        if cwk and cwk.status == "PAUSED":
            cwk.status = "ACTIVE"
            return True
        return False

    def reassign_coworker(self, coworker_id: str, target_department: str) -> bool:
        cwk = self._coworkers.get(coworker_id)
        if cwk:
            cwk.department = target_department
            cwk.status = "REASSIGNED"
            return True
        return False

    def terminate_coworker(self, coworker_id: str, reason: str = "Deprovisioned") -> bool:
        cwk = self._coworkers.get(coworker_id)
        if cwk:
            cwk.status = "TERMINATED"
            logger.info(f"Coworker {coworker_id} terminated: {reason}")
            return True
        return False

    def list_coworkers(self, department: Optional[str] = None) -> List[GovernedCoworkerContract]:
        if department:
            return [c for c in self._coworkers.values() if c.department.lower() == department.lower()]
        return list(self._coworkers.values())
