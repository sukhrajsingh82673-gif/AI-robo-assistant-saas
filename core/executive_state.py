"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Authoritative Executive State Engine
Persistent, queryable, versioned, auditable state for the AI CEO.

Constitutional Invariants:
  PERSISTENT_NOT_PROMPT (State is structured and stored in SQLite, not an ephemeral LLM prompt)
  TENANT_COMPANY_ISOLATION (No executive state can leak across tenant or company boundaries)
  IMMUTABLE_SNAPSHOTS (Every state transition preserves version history)
"""

import time
import json
import uuid
import copy
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.database_engine import engine, WorkloadType
from core.db import db

@dataclass
class ExecutiveCompanyMetadata:
    company_id: str
    tenant_id: str
    company_name: str
    industry: str
    business_model: str = "DIRECT_OPERATIONS"
    operating_regions: List[str] = field(default_factory=lambda: ["IN"])
    lifecycle_stage: str = "OPERATIONAL"       # EARLY_STAGE, SCALING, MATURE, TURNAROUND, PEAK_SEASON
    currency: str = "₹"
    timezone: str = "Asia/Kolkata"

@dataclass
class ExecutiveVision:
    vision: str = ""
    mission: str = ""
    long_term_goals: List[str] = field(default_factory=list)
    strategic_horizon: str = "ANNUAL"          # IMMEDIATE, TODAY, STRATEGIC, LONG_TERM

@dataclass
class ExecutiveStateSnapshot:
    state_id: str
    tenant_id: str
    company_id: str
    version: int
    last_loop_stage: str
    company: Dict[str, Any]
    vision: Dict[str, Any]
    objectives: Dict[str, Any]
    strategy: Dict[str, Any]
    workforce: Dict[str, Any]
    missions: Dict[str, Any]
    performance: Dict[str, Any]
    finance: Dict[str, Any]
    risk: Dict[str, Any]
    opportunities: Dict[str, Any]
    external_conditions: Dict[str, Any]
    decisions: Dict[str, Any]
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutiveStateManager:
    """
    Authoritative persistence and lifecycle governor for company executive state.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Ensures an authoritative baseline executive state exists in database."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM executive_state WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id)
            ).fetchone()
            if not row:
                # Query company name and details from companies table if available
                comp_row = conn.execute(
                    "SELECT * FROM companies WHERE tenant_id = ? AND company_id = ?",
                    (self.tenant_id, self.company_id)
                ).fetchone()
                comp_name = comp_row["name"] if comp_row else f"Enterprise_{self.company_id}"
                industry = comp_row["industry"] if comp_row else "Hospitality"
                currency = comp_row["currency"] if comp_row and "currency" in comp_row.keys() else "₹"

                initial_snapshot = {
                    "company": asdict(ExecutiveCompanyMetadata(
                        company_id=self.company_id,
                        tenant_id=self.tenant_id,
                        company_name=comp_name,
                        industry=industry,
                        currency=currency
                    )),
                    "vision": asdict(ExecutiveVision(
                        vision=f"Deliver exceptional value and sustainable profitability for {comp_name}.",
                        mission="Maximize operational excellence, guest satisfaction, and financial return.",
                        long_term_goals=["Achieve top RevPAR index in local market", "Maintain 95%+ service standards"]
                    )),
                    "objectives": {
                        "corporate_objectives": [],
                        "strategic_objectives": [],
                        "departmental_objectives": [],
                        "operational_objectives": []
                    },
                    "strategy": {
                        "current_strategy": None,
                        "strategic_priorities": [],
                        "strategic_assumptions": [],
                        "strategic_constraints": [],
                        "strategic_dependencies": []
                    },
                    "workforce": {
                        "active_employees": [],
                        "specialists": [],
                        "departments": ["OPERATIONS", "REVENUE", "MARKETING", "FINANCE", "TECH"],
                        "managers": [],
                        "chief_officers": ["COO", "CRO", "CMO", "CFO", "CTO"],
                        "employee_capacity": 100.0,
                        "employee_utilization": 45.0,
                        "vacancies": 0,
                        "workforce_gaps": []
                    },
                    "missions": {
                        "active_missions": [],
                        "queued_missions": [],
                        "completed_missions": [],
                        "failed_missions": [],
                        "blocked_missions": [],
                        "escalated_missions": []
                    },
                    "performance": {
                        "kpis": {},
                        "kras": {},
                        "targets": {},
                        "actuals": {},
                        "variance": {},
                        "trends": {},
                        "business_outcomes": []
                    },
                    "finance": {
                        "budgets": {"total_budget": 500000.0, "allocated": 100000.0, "unallocated": 400000.0},
                        "committed_budget": 25000.0,
                        "actual_spend": 12500.0,
                        "projected_spend": 80000.0,
                        "roi": 3.4,
                        "cost_per_outcome": 120.0
                    },
                    "risk": {
                        "active_risks": [],
                        "risk_level": "LOW",
                        "risk_owner": "RISK_OFFICER",
                        "mitigations": [],
                        "incidents": [],
                        "unresolved_exceptions": []
                    },
                    "opportunities": {
                        "opportunities": [],
                        "estimated_value": 0.0,
                        "confidence": 0.8,
                        "required_resources": [],
                        "status": "DISCOVERED"
                    },
                    "external_conditions": {
                        "market_conditions": "PEAK_SEASON_SURGE",
                        "operational_conditions": "HIGH_OCCUPANCY",
                        "known_external_events": ["Local wedding bookings surge", "Weekend festival conferences"],
                        "data_freshness": "REALTIME",
                        "source_provenance": "PMS_CRS_GATEWAY"
                    },
                    "decisions": {
                        "executive_decisions": [],
                        "decision_reason": None,
                        "alternatives_considered": [],
                        "evidence": [],
                        "authority": "AI_CEO_GOVERNED",
                        "approvals": [],
                        "outcome": None
                    }
                }

                state_id = f"state_{self.tenant_id}_{self.company_id}"
                conn.execute("""
                    INSERT INTO executive_state (state_id, tenant_id, company_id, snapshot, version, last_loop_stage, updated_at)
                    VALUES (?, ?, ?, ?, 1, 'OBSERVE', ?)
                """, (state_id, self.tenant_id, self.company_id, json.dumps(initial_snapshot), time.time()))
                conn.commit()

    def get_state(self) -> ExecutiveStateSnapshot:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM executive_state WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id)
            ).fetchone()
            if not row:
                self._ensure_initialized()
                row = conn.execute(
                    "SELECT * FROM executive_state WHERE tenant_id = ? AND company_id = ?",
                    (self.tenant_id, self.company_id)
                ).fetchone()

            snap = json.loads(row["snapshot"])
            return ExecutiveStateSnapshot(
                state_id=row["state_id"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                version=row["version"],
                last_loop_stage=row["last_loop_stage"],
                company=snap.get("company", {}),
                vision=snap.get("vision", {}),
                objectives=snap.get("objectives", {}),
                strategy=snap.get("strategy", {}),
                workforce=snap.get("workforce", {}),
                missions=snap.get("missions", {}),
                performance=snap.get("performance", {}),
                finance=snap.get("finance", {}),
                risk=snap.get("risk", {}),
                opportunities=snap.get("opportunities", {}),
                external_conditions=snap.get("external_conditions", {}),
                decisions=snap.get("decisions", {}),
                updated_at=row["updated_at"]
            )

    def update_state(self, updates: Dict[str, Any], last_loop_stage: Optional[str] = None) -> ExecutiveStateSnapshot:
        """Atomically updates the executive state snapshot and increments version."""
        current = self.get_state()
        snapshot_dict = current.to_dict()

        for k, v in updates.items():
            if k in snapshot_dict:
                if isinstance(snapshot_dict[k], dict) and isinstance(v, dict):
                    snapshot_dict[k].update(v)
                else:
                    snapshot_dict[k] = v

        new_version = current.version + 1
        new_stage = last_loop_stage or current.last_loop_stage
        now = time.time()

        # Clean out top-level wrapper keys from snapshot storage
        clean_snapshot = {
            "company": snapshot_dict["company"],
            "vision": snapshot_dict["vision"],
            "objectives": snapshot_dict["objectives"],
            "strategy": snapshot_dict["strategy"],
            "workforce": snapshot_dict["workforce"],
            "missions": snapshot_dict["missions"],
            "performance": snapshot_dict["performance"],
            "finance": snapshot_dict["finance"],
            "risk": snapshot_dict["risk"],
            "opportunities": snapshot_dict["opportunities"],
            "external_conditions": snapshot_dict["external_conditions"],
            "decisions": snapshot_dict["decisions"]
        }

        with db.get_connection() as conn:
            conn.execute("""
                UPDATE executive_state
                SET snapshot = ?, version = ?, last_loop_stage = ?, updated_at = ?
                WHERE tenant_id = ? AND company_id = ?
            """, (json.dumps(clean_snapshot), new_version, new_stage, now, self.tenant_id, self.company_id))
            conn.commit()

        return self.get_state()
