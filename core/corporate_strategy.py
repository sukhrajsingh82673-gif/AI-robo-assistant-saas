"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Corporate Strategy Engine & Strategic Versioning
Formulates, versions, tracks, and adjusts strategic plans linked to corporate objectives.

Constitutional Invariants:
  IMMUTABLE_STRATEGY_HISTORY (Never mutate historical strategy records; all changes create version receipts)
  EVIDENCE_LINKED_RATIONALE (Strategic assumptions and rationale must link to verified evidence)
  CONTAINED_RESOURCE_BOUNDS (Strategies specify required capabilities, workforce, and budget limits)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class StrategyStatus:
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ACHIEVED = "ACHIEVED"
    ABANDONED = "ABANDONED"

@dataclass
class StrategicPlan:
    strategy_id: str
    tenant_id: str
    company_id: str
    objective_id: str
    version: str
    title: str
    rationale: str
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    required_workforce: List[str] = field(default_factory=list)
    required_budget: float = 0.0
    expected_outcomes: List[str] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    review_date: float = field(default_factory=lambda: time.time() + 30 * 86400)
    status: str = StrategyStatus.ACTIVE
    owner: str = "AI_CEO"
    evidence_refs: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StrategyVersionRecord:
    version_id: str
    strategy_id: str
    tenant_id: str
    company_id: str
    previous_version: Optional[str]
    new_version: str
    reason: str
    evidence: List[str]
    affected_objectives: List[str]
    affected_departments: List[str]
    affected_workforce: List[str]
    affected_missions: List[str]
    approval_id: Optional[str]
    ceo_version: str = "V8.0.0"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CorporateStrategyEngine:
    """
    Formulates and maintains versioned corporate strategy with complete provenance and auditability.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def formulate_strategy_for_objective(
        self,
        objective_id: str,
        title: str,
        rationale: str,
        assumptions: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        required_capabilities: Optional[List[str]] = None,
        required_workforce: Optional[List[str]] = None,
        required_budget: float = 50000.0,
        expected_outcomes: Optional[List[str]] = None,
        milestones: Optional[List[Dict[str, Any]]] = None,
        risks: Optional[List[str]] = None,
        evidence_refs: Optional[List[str]] = None
    ) -> StrategicPlan:
        """Creates the initial strategy (version 1.0.0) for an objective."""
        strategy_id = f"strat_{uuid.uuid4().hex[:10]}"
        now = time.time()
        plan = StrategicPlan(
            strategy_id=strategy_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            objective_id=objective_id,
            version="1.0.0",
            title=title,
            rationale=rationale,
            assumptions=assumptions or ["Demand elasticity remains stable", "Peak wedding season holds 85%+ market occupancy"],
            constraints=constraints or ["Maximum budget ceiling ₹100,000", "No degradation of guest satisfaction score below 4.5"],
            dependencies=dependencies or ["PMS integration operational", "Revenue rate optimizer online"],
            required_capabilities=required_capabilities or ["REVENUE_OPTIMIZATION", "DYNAMIC_PRICING", "HOSPITALITY_OPERATIONS"],
            required_workforce=required_workforce or ["Revenue Manager", "Guest Experience Lead"],
            required_budget=required_budget,
            expected_outcomes=expected_outcomes or ["Increase RevPAR by 18%", "Sustain ADR above ₹5,200", "Achieve 30% contribution margin"],
            milestones=milestones or [
                {"name": "M1: Rate parity & peak surge pricing live", "target_day": 7, "status": "PENDING"},
                {"name": "M2: Wedding package dynamic yield activation", "target_day": 14, "status": "PENDING"},
                {"name": "M3: Night audit variance reconciliation", "target_day": 30, "status": "PENDING"}
            ],
            risks=risks or ["Competitor price undercutting", "Front-desk service bottleneck during check-in"],
            review_date=now + 14 * 86400,
            status=StrategyStatus.ACTIVE,
            owner="AI_CEO",
            evidence_refs=evidence_refs or [f"ev_strat_init_{uuid.uuid4().hex[:8]}"],
            created_at=now,
            updated_at=now
        )

        self._persist_plan(plan)

        # Record initial version in audit ledger
        self._record_version(
            strategy_id=plan.strategy_id,
            previous_version=None,
            new_version=plan.version,
            reason=f"Initial strategy formulated for objective {objective_id}: '{title}'",
            evidence=plan.evidence_refs,
            affected_objectives=[objective_id],
            affected_departments=["REVENUE", "OPERATIONS", "MARKETING"],
            affected_workforce=plan.required_workforce,
            affected_missions=[]
        )

        create_executive_event(
            event_type="StrategyCreated",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={"strategy_id": plan.strategy_id, "title": plan.title, "version": plan.version}
        )

        return plan

    def adjust_strategy(
        self,
        strategy_id: str,
        reason: str,
        evidence: List[str],
        new_assumptions: Optional[List[str]] = None,
        new_constraints: Optional[List[str]] = None,
        adjusted_budget: Optional[float] = None,
        affected_missions: Optional[List[str]] = None,
        approval_id: Optional[str] = None
    ) -> StrategicPlan:
        """
        Adjusts an existing strategy, incrementing version (e.g. 1.0.0 -> 1.1.0)
        and sealing a version receipt in strategy_versions.
        """
        current = self.get_strategy(strategy_id)
        if not current:
            raise ValueError(f"Strategy {strategy_id} not found for tenant {self.tenant_id}")

        # Compute next version
        parts = current.version.split(".")
        if len(parts) == 3:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            new_version = f"{major}.{minor + 1}.0"
        else:
            new_version = f"{current.version}.1"

        now = time.time()
        prev_version = current.version
        current.version = new_version
        current.updated_at = now
        if new_assumptions is not None:
            current.assumptions = new_assumptions
        if new_constraints is not None:
            current.constraints = new_constraints
        if adjusted_budget is not None:
            current.required_budget = adjusted_budget
        if evidence:
            current.evidence_refs.extend(evidence)

        self._persist_plan(current)

        # Record immutable version receipt
        self._record_version(
            strategy_id=strategy_id,
            previous_version=prev_version,
            new_version=new_version,
            reason=reason,
            evidence=evidence,
            affected_objectives=[current.objective_id],
            affected_departments=["REVENUE", "OPERATIONS"],
            affected_workforce=current.required_workforce,
            affected_missions=affected_missions or [],
            approval_id=approval_id
        )

        create_executive_event(
            event_type="StrategyAdjusted",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "strategy_id": strategy_id,
                "previous_version": current.version,
                "new_version": new_version,
                "reason": reason
            }
        )

        return current

    def _persist_plan(self, plan: StrategicPlan):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO strategic_plans (
                    strategy_id, tenant_id, company_id, objective_id, version,
                    title, rationale, assumptions, constraints, dependencies,
                    required_capabilities, required_workforce, required_budget,
                    expected_outcomes, milestones, risks, review_date, status,
                    owner, evidence_refs, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id) DO UPDATE SET
                    version=excluded.version,
                    title=excluded.title,
                    rationale=excluded.rationale,
                    assumptions=excluded.assumptions,
                    constraints=excluded.constraints,
                    dependencies=excluded.dependencies,
                    required_capabilities=excluded.required_capabilities,
                    required_workforce=excluded.required_workforce,
                    required_budget=excluded.required_budget,
                    expected_outcomes=excluded.expected_outcomes,
                    milestones=excluded.milestones,
                    risks=excluded.risks,
                    review_date=excluded.review_date,
                    status=excluded.status,
                    evidence_refs=excluded.evidence_refs,
                    updated_at=excluded.updated_at
            """, (
                plan.strategy_id, plan.tenant_id, plan.company_id, plan.objective_id, plan.version,
                plan.title, plan.rationale, json.dumps(plan.assumptions), json.dumps(plan.constraints),
                json.dumps(plan.dependencies), json.dumps(plan.required_capabilities), json.dumps(plan.required_workforce),
                plan.required_budget, json.dumps(plan.expected_outcomes), json.dumps(plan.milestones),
                json.dumps(plan.risks), plan.review_date, plan.status, plan.owner, json.dumps(plan.evidence_refs),
                plan.created_at, plan.updated_at
            ))
            conn.commit()

    def _record_version(
        self,
        strategy_id: str,
        previous_version: Optional[str],
        new_version: str,
        reason: str,
        evidence: List[str],
        affected_objectives: List[str],
        affected_departments: List[str],
        affected_workforce: List[str],
        affected_missions: List[str],
        approval_id: Optional[str] = None
    ) -> StrategyVersionRecord:
        ver_id = f"strat_ver_{uuid.uuid4().hex[:10]}"
        now = time.time()
        rec = StrategyVersionRecord(
            version_id=ver_id,
            strategy_id=strategy_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            previous_version=previous_version,
            new_version=new_version,
            reason=reason,
            evidence=evidence,
            affected_objectives=affected_objectives,
            affected_departments=affected_departments,
            affected_workforce=affected_workforce,
            affected_missions=affected_missions,
            approval_id=approval_id,
            ceo_version="V8.0.0",
            created_at=now
        )
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO strategy_versions (
                    version_id, strategy_id, tenant_id, company_id, previous_version,
                    new_version, reason, evidence, affected_objectives, affected_departments,
                    affected_workforce, affected_missions, approval_id, ceo_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.version_id, rec.strategy_id, rec.tenant_id, rec.company_id, rec.previous_version,
                rec.new_version, rec.reason, json.dumps(rec.evidence), json.dumps(rec.affected_objectives),
                json.dumps(rec.affected_departments), json.dumps(rec.affected_workforce), json.dumps(rec.affected_missions),
                rec.approval_id, rec.ceo_version, rec.created_at
            ))
            conn.commit()
        return rec

    def get_strategy(self, strategy_id: str) -> Optional[StrategicPlan]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM strategic_plans WHERE strategy_id = ? AND tenant_id = ? AND company_id = ?",
                (strategy_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            return self._row_to_plan(r)

    def get_active_strategies(self) -> List[StrategicPlan]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM strategic_plans WHERE tenant_id = ? AND company_id = ? AND status = ? ORDER BY created_at DESC",
                (self.tenant_id, self.company_id, StrategyStatus.ACTIVE)
            ).fetchall()
            return [self._row_to_plan(r) for r in rows]

    def get_strategy_versions(self, strategy_id: str) -> List[StrategyVersionRecord]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM strategy_versions WHERE strategy_id = ? AND tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                (strategy_id, self.tenant_id, self.company_id)
            ).fetchall()
            res = []
            for r in rows:
                res.append(StrategyVersionRecord(
                    version_id=r["version_id"],
                    strategy_id=r["strategy_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    previous_version=r["previous_version"],
                    new_version=r["new_version"],
                    reason=r["reason"],
                    evidence=json.loads(r["evidence"] or "[]"),
                    affected_objectives=json.loads(r["affected_objectives"] or "[]"),
                    affected_departments=json.loads(r["affected_departments"] or "[]"),
                    affected_workforce=json.loads(r["affected_workforce"] or "[]"),
                    affected_missions=json.loads(r["affected_missions"] or "[]"),
                    approval_id=r["approval_id"],
                    ceo_version=r["ceo_version"],
                    created_at=r["created_at"]
                ))
            return res

    def _row_to_plan(self, r: Any) -> StrategicPlan:
        return StrategicPlan(
            strategy_id=r["strategy_id"],
            tenant_id=r["tenant_id"],
            company_id=r["company_id"],
            objective_id=r["objective_id"],
            version=r["version"],
            title=r["title"],
            rationale=r["rationale"],
            assumptions=json.loads(r["assumptions"] or "[]"),
            constraints=json.loads(r["constraints"] or "[]"),
            dependencies=json.loads(r["dependencies"] or "[]"),
            required_capabilities=json.loads(r["required_capabilities"] or "[]"),
            required_workforce=json.loads(r["required_workforce"] or "[]"),
            required_budget=r["required_budget"],
            expected_outcomes=json.loads(r["expected_outcomes"] or "[]"),
            milestones=json.loads(r["milestones"] or "[]"),
            risks=json.loads(r["risks"] or "[]"),
            review_date=r["review_date"],
            status=r["status"],
            owner=r["owner"],
            evidence_refs=json.loads(r["evidence_refs"] or "[]"),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )
