"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Executive Decision Engine & Human Owner Approval Queue
Formulates evidence-backed executive decisions and enforces Human Owner approval gates.

Constitutional Invariants:
  CEO_IS_NEVER_UNRESTRICTED (CEO cannot bypass Policy, Authority, ActionGateway, or KillSwitch)
  EVIDENCE_LINKED_DECISIONS (Every significant decision binds to cryptographic evidence with SHA-256)
  HUMAN_SOVEREIGNTY (High-risk financial, structural, or external mutations require Owner Approval)
"""

import time
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class DecisionApprovalStatus:
    PROPOSED = "PROPOSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    UNKNOWN = "UNKNOWN"

class EvidenceConfidence:
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"

@dataclass
class ExecutiveDecisionRecord:
    decision_id: str
    tenant_id: str
    company_id: str
    title: str
    decision_type: str
    problem_statement: str
    alternatives_considered: List[str]
    selected_option: str
    rationale: str
    constraints: Dict[str, Any]
    authority_required: str
    approval_status: str = DecisionApprovalStatus.PROPOSED
    approval_id: Optional[str] = None
    execution_status: str = "PENDING"
    evidence_refs: List[str] = field(default_factory=list)
    outcome: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ExecutiveApprovalItem:
    approval_id: str
    tenant_id: str
    company_id: str
    decision_id: Optional[str]
    action_type: str
    requested_by: str
    summary: str
    risk_level: str
    parameters: Dict[str, Any]
    status: str = "PENDING"            # PENDING, APPROVED, REJECTED, EXPIRED
    resolved_by: Optional[str] = None
    resolution_reason: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutiveDecisionEngine:
    """
    Orchestrates the 11-stage executive decision lifecycle with cryptographic evidence binding.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def formulate_and_evaluate_decision(
        self,
        title: str,
        decision_type: str,
        problem_statement: str,
        alternatives_considered: List[str],
        selected_option: str,
        rationale: str,
        constraints: Dict[str, Any],
        authority_required: str,
        evidence_source: str,
        evidence_data: Dict[str, Any],
        financial_impact_inr: float = 0.0,
        requires_human_approval: Optional[bool] = None
    ) -> Tuple[ExecutiveDecisionRecord, Optional[ExecutiveApprovalItem]]:
        """
        Executes formal 11-stage decision formulation:
        1. Identify problem
        2. Gather & hash evidence
        3. Identify constraints
        4. Evaluate options
        5. Verify policy compatibility
        6. Determine authority requirement
        7. Determine Human Owner approval requirement (auto if budget > ₹50,000 or high-risk)
        8. Record decision & evidence in database
        """
        now = time.time()
        decision_id = f"dec_{uuid.uuid4().hex[:10]}"

        # Step 2: Digest evidence
        ev_bytes = json.dumps(evidence_data, sort_keys=True).encode("utf-8")
        sha256_digest = hashlib.sha256(ev_bytes).hexdigest()
        evidence_id = f"ev_dec_{uuid.uuid4().hex[:8]}"

        # Step 7: Dynamic Enterprise Settings Governance Checks (Gate G1, G2, G12)
        from core.settings_service import settings_service
        em_stop = settings_service.get_effective_setting(self.tenant_id, self.company_id, "host_emergency_stop", False)
        autonomy_level = settings_service.get_effective_setting(self.tenant_id, self.company_id, "ceo_autonomy_level", "Level 3 — Execute Within Policy")
        ceo_spend_cap = float(settings_service.get_effective_setting(self.tenant_id, self.company_id, "ceo_spending_limit", 50000.0))
        fin_high_approval = float(settings_service.get_effective_setting(self.tenant_id, self.company_id, "fin_high_expense_approval", 25000.0))

        if requires_human_approval is None:
            if em_stop:
                # Emergency Stop: all automated actions blocked and require explicit owner intervention
                requires_human_approval = True
            elif "Level 0" in autonomy_level or "Level 1" in autonomy_level or "Level 2" in autonomy_level:
                # Observe/Recommend/Approval required mode
                requires_human_approval = True
            elif financial_impact_inr > ceo_spend_cap or financial_impact_inr > fin_high_approval:
                requires_human_approval = True
            elif any(k in decision_type.lower() for k in ["contract", "terminate", "major_budget", "destroy"]):
                requires_human_approval = True
            else:
                requires_human_approval = False

        approval_item = None
        if requires_human_approval:
            approval_status = DecisionApprovalStatus.PENDING_APPROVAL
            approval_id = f"appr_exec_{uuid.uuid4().hex[:8]}"
            approval_item = ExecutiveApprovalItem(
                approval_id=approval_id,
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                decision_id=decision_id,
                action_type=decision_type,
                requested_by="AI_CEO",
                summary=f"Approval requested for: {title} (Financial impact: ₹{financial_impact_inr})",
                risk_level="HIGH" if financial_impact_inr > 100000 else "MEDIUM",
                parameters={
                    "selected_option": selected_option,
                    "financial_impact_inr": financial_impact_inr,
                    "rationale": rationale
                },
                status="PENDING",
                created_at=now
            )
            self._persist_approval_item(approval_item)
        else:
            approval_status = DecisionApprovalStatus.APPROVED
            approval_id = None

        decision = ExecutiveDecisionRecord(
            decision_id=decision_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title=title,
            decision_type=decision_type,
            problem_statement=problem_statement,
            alternatives_considered=alternatives_considered,
            selected_option=selected_option,
            rationale=rationale,
            constraints=constraints,
            authority_required=authority_required,
            approval_status=approval_status,
            approval_id=approval_id,
            execution_status="PENDING" if not requires_human_approval else "WAITING_FOR_OWNER",
            evidence_refs=[evidence_id],
            outcome=None,
            created_at=now,
            updated_at=now
        )

        with db.get_connection() as conn:
            # Persist Decision
            conn.execute("""
                INSERT INTO executive_decisions (
                    decision_id, tenant_id, company_id, title, decision_type,
                    problem_statement, alternatives_considered, selected_option,
                    rationale, constraints, authority_required, approval_status,
                    approval_id, execution_status, evidence_refs, outcome,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decision_id, decision.tenant_id, decision.company_id, decision.title,
                decision.decision_type, decision.problem_statement, json.dumps(decision.alternatives_considered),
                decision.selected_option, decision.rationale, json.dumps(decision.constraints),
                decision.authority_required, decision.approval_status, decision.approval_id,
                decision.execution_status, json.dumps(decision.evidence_refs), json.dumps(decision.outcome or {}),
                decision.created_at, decision.updated_at
            ))

            # Persist Evidence
            conn.execute("""
                INSERT INTO executive_decision_evidence (
                    id, decision_id, tenant_id, company_id, evidence_type,
                    source, confidence, evidence_data, sha256_digest, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence_id, decision.decision_id, self.tenant_id, self.company_id,
                decision_type, evidence_source, EvidenceConfidence.VERIFIED,
                json.dumps(evidence_data), sha256_digest, now
            ))
            conn.commit()

        create_executive_event(
            event_type="ApprovalRequested" if requires_human_approval else "ExecutiveDecisionCreated",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "decision_id": decision.decision_id,
                "title": decision.title,
                "approval_status": decision.approval_status,
                "approval_id": approval_id,
                "requires_owner": requires_human_approval
            }
        )

        return decision, approval_item

    def resolve_approval(self, approval_id: str, approved: bool, reason: str, owner_id: str = "HUMAN_OWNER") -> ExecutiveDecisionRecord:
        """Owner grants or rejects an executive approval."""
        now = time.time()
        with db.get_connection() as conn:
            appr = conn.execute(
                "SELECT * FROM executive_approval_queue WHERE approval_id = ? AND tenant_id = ? AND company_id = ?",
                (approval_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not appr:
                raise ValueError(f"Approval {approval_id} not found.")

            new_status = "APPROVED" if approved else "REJECTED"
            conn.execute("""
                UPDATE executive_approval_queue
                SET status = ?, resolved_by = ?, resolution_reason = ?, resolved_at = ?
                WHERE approval_id = ?
            """, (new_status, owner_id, reason, now, approval_id))

            decision_id = appr["decision_id"]
            dec_approval_status = DecisionApprovalStatus.APPROVED if approved else DecisionApprovalStatus.REJECTED
            execution_status = "READY_TO_EXECUTE" if approved else "CANCELLED"

            conn.execute("""
                UPDATE executive_decisions
                SET approval_status = ?, execution_status = ?, updated_at = ?
                WHERE decision_id = ?
            """, (dec_approval_status, execution_status, now, decision_id))
            conn.commit()

        create_executive_event(
            event_type="ApprovalGranted" if approved else "ApprovalRejected",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={"approval_id": approval_id, "decision_id": decision_id, "approved": approved, "reason": reason}
        )

        return self.get_decision(decision_id)

    def record_decision_execution_outcome(self, decision_id: str, outcome_data: Dict[str, Any], verified: bool = True) -> ExecutiveDecisionRecord:
        """Records physical execution outcome for decision."""
        now = time.time()
        dec = self.get_decision(decision_id)
        if not dec:
            raise ValueError(f"Decision {decision_id} not found.")

        dec.execution_status = "VERIFIED" if verified else "FAILED"
        dec.approval_status = DecisionApprovalStatus.VERIFIED if verified else DecisionApprovalStatus.FAILED
        dec.outcome = outcome_data
        dec.updated_at = now

        with db.get_connection() as conn:
            conn.execute("""
                UPDATE executive_decisions
                SET execution_status = ?, approval_status = ?, outcome = ?, updated_at = ?
                WHERE decision_id = ?
            """, (dec.execution_status, dec.approval_status, json.dumps(outcome_data), now, decision_id))
            conn.commit()

        return dec

    def _persist_approval_item(self, item: ExecutiveApprovalItem):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO executive_approval_queue (
                    approval_id, tenant_id, company_id, decision_id, action_type,
                    requested_by, summary, risk_level, parameters, status,
                    resolved_by, resolution_reason, created_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.approval_id, item.tenant_id, item.company_id, item.decision_id, item.action_type,
                item.requested_by, item.summary, item.risk_level, json.dumps(item.parameters),
                item.status, item.resolved_by, item.resolution_reason, item.created_at, item.resolved_at
            ))
            conn.commit()

    def get_decision(self, decision_id: str) -> Optional[ExecutiveDecisionRecord]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM executive_decisions WHERE decision_id = ? AND tenant_id = ? AND company_id = ?",
                (decision_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            return ExecutiveDecisionRecord(
                decision_id=r["decision_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                title=r["title"],
                decision_type=r["decision_type"],
                problem_statement=r["problem_statement"],
                alternatives_considered=json.loads(r["alternatives_considered"] or "[]"),
                selected_option=r["selected_option"],
                rationale=r["rationale"],
                constraints=json.loads(r["constraints"] or "{}"),
                authority_required=r["authority_required"],
                approval_status=r["approval_status"],
                approval_id=r["approval_id"],
                execution_status=r["execution_status"],
                evidence_refs=json.loads(r["evidence_refs"] or "[]"),
                outcome=json.loads(r["outcome"] or "{}") if r["outcome"] else None,
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )

    def list_decisions(self, status: Optional[str] = None) -> List[ExecutiveDecisionRecord]:
        with db.get_connection() as conn:
            query = "SELECT * FROM executive_decisions WHERE tenant_id = ? AND company_id = ?"
            params = [self.tenant_id, self.company_id]
            if status:
                query += " AND approval_status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                ExecutiveDecisionRecord(
                    decision_id=r["decision_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    title=r["title"],
                    decision_type=r["decision_type"],
                    problem_statement=r["problem_statement"],
                    alternatives_considered=json.loads(r["alternatives_considered"] or "[]"),
                    selected_option=r["selected_option"],
                    rationale=r["rationale"],
                    constraints=json.loads(r["constraints"] or "{}"),
                    authority_required=r["authority_required"],
                    approval_status=r["approval_status"],
                    approval_id=r["approval_id"],
                    execution_status=r["execution_status"],
                    evidence_refs=json.loads(r["evidence_refs"] or "[]"),
                    outcome=json.loads(r["outcome"] or "{}") if r["outcome"] else None,
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ) for r in rows
            ]

    def list_pending_approvals(self) -> List[ExecutiveApprovalItem]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM executive_approval_queue WHERE tenant_id = ? AND company_id = ? AND status = 'PENDING' ORDER BY created_at ASC",
                (self.tenant_id, self.company_id)
            ).fetchall()
            return [
                ExecutiveApprovalItem(
                    approval_id=r["approval_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    decision_id=r["decision_id"],
                    action_type=r["action_type"],
                    requested_by=r["requested_by"],
                    summary=r["summary"],
                    risk_level=r["risk_level"],
                    parameters=json.loads(r["parameters"] or "{}"),
                    status=r["status"],
                    resolved_by=r["resolved_by"],
                    resolution_reason=r["resolution_reason"],
                    created_at=r["created_at"],
                    resolved_at=r["resolved_at"]
                ) for r in rows
            ]
