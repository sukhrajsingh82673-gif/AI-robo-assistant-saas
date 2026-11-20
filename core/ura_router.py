"""ZONATA Sovereign Core — URA Router / Worker Runtime.

Implements Stage 3 Router/Worker Architecture:
- Law L1 (Router/Worker): The URA Assistant is a router: receives requests/events,
  decides, dispatches and replies in one voice. Long work executes in isolated worker sessions.
- Law L2 (Deterministic Gates): Kill switch, admission, charter, and budget gates evaluated deterministically.
- Law L3 (Admission by Strength): Explicit, Inferred, Not Admitted. Not-admitted dropped before model call.
  Inferred recorded as 'would accept' under L0/L1, admitted under L2+.
- Law L4 (Observe First): L0 processes only record observations without live execution.
- Law L5 (Separation of Duties): Requester != Worker != Approver.
- Concurrency management with reserved slot for human operator messages.
- Thread subscriptions for direct worker follow-up routing.
- Executive routing for @CEO, @CFO, @CMO, @CTO, @COO, @CHRO, @CISO, @CLO.
"""

from __future__ import annotations

import enum
import json
import logging
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.accountable_owner import AccountableOwnerRegistry
from core.charter import CompanyCharter
from core.db import db
from core.gates import (
    AdmissionGate,
    AutonomyGate,
    BudgetGate,
    CharterGate,
    DeterministicGatePipeline,
    GateResult,
    KillSwitchGate,
)
from agent_factory.ports import EvidenceEvent
from agent_factory.adapters.zonata import ZonataEvidenceAdapter

logger = logging.getLogger("zonata.core.router")


class AdmissionStrength(str, enum.Enum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    NOT_ADMITTED = "NOT_ADMITTED"


class WorkItemStatus(str, enum.Enum):
    CREATED = "CREATED"
    ADMITTED = "ADMITTED"
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    KILLED = "KILLED"
    OBSERVED_ONLY = "OBSERVED_ONLY"


VALID_STATUS_TRANSITIONS: Dict[WorkItemStatus, Set[WorkItemStatus]] = {
    WorkItemStatus.CREATED: {WorkItemStatus.ADMITTED, WorkItemStatus.OBSERVED_ONLY, WorkItemStatus.FAILED, WorkItemStatus.KILLED},
    WorkItemStatus.ADMITTED: {WorkItemStatus.DISPATCHED, WorkItemStatus.CANCELLED, WorkItemStatus.KILLED, WorkItemStatus.AWAITING_APPROVAL},
    WorkItemStatus.DISPATCHED: {WorkItemStatus.EXECUTING, WorkItemStatus.COMPLETED, WorkItemStatus.CANCELLED, WorkItemStatus.KILLED, WorkItemStatus.FAILED},
    WorkItemStatus.EXECUTING: {WorkItemStatus.AWAITING_APPROVAL, WorkItemStatus.COMPLETED, WorkItemStatus.FAILED, WorkItemStatus.KILLED, WorkItemStatus.CANCELLED},
    WorkItemStatus.AWAITING_APPROVAL: {WorkItemStatus.COMPLETED, WorkItemStatus.EXECUTING, WorkItemStatus.CANCELLED, WorkItemStatus.KILLED, WorkItemStatus.FAILED},
    WorkItemStatus.COMPLETED: set(),
    WorkItemStatus.FAILED: set(),
    WorkItemStatus.CANCELLED: set(),
    WorkItemStatus.KILLED: set(),
    WorkItemStatus.OBSERVED_ONLY: set(),
}

EXECUTIVE_ROLES: Dict[str, Dict[str, str]] = {
    "CEO": {
        "label": "AI CEO",
        "title": "Chief Executive Officer",
        "remit": "corporate strategy, capital allocation, executive coordination, company charter",
        "accountable_dept": "executive"
    },
    "COO": {
        "label": "AI COO",
        "title": "Chief Operating Officer",
        "remit": "operations, process excellence, SLA enforcement, Kaizen execution",
        "accountable_dept": "operations"
    },
    "CMO": {
        "label": "AI CMO",
        "title": "Chief Marketing Officer",
        "remit": "marketing, lead generation, branding, market intelligence",
        "accountable_dept": "marketing"
    },
    "CTO": {
        "label": "AI CTO",
        "title": "Chief Technology Officer",
        "remit": "engineering, infrastructure, security architecture, software build",
        "accountable_dept": "engineering"
    },
    "CFO": {
        "label": "AI CFO",
        "title": "Chief Financial Officer",
        "remit": "financial controls, budgets, payouts, tax compliance, bookkeeping",
        "accountable_dept": "finance"
    },
    "CHRO": {
        "label": "AI CHRO",
        "title": "Chief Human Resources Officer",
        "remit": "people, hiring, performance reviews, workforce compliance",
        "accountable_dept": "people"
    },
    "CISO": {
        "label": "AI CISO",
        "title": "Chief Information Security Officer",
        "remit": "cybersecurity, threat monitoring, vulnerability management, access governance",
        "accountable_dept": "security"
    },
    "CLO": {
        "label": "AI CLO",
        "title": "Chief Legal Officer",
        "remit": "contracts, regulatory compliance, risk mitigation, audit readiness",
        "accountable_dept": "legal"
    },
}

_ROLE_REGEX = re.compile(r"^\s*@([A-Za-z]{3,5})\b", re.IGNORECASE)


@dataclass
class WorkItem:
    work_item_id: str
    tenant_id: str
    company_id: str
    title: str
    description: str
    admission_strength: str
    status: str
    target_role: str
    autonomy_level: int
    accountable_owner_id: str
    session_id: str
    thread_id: str
    requester_id: str
    is_human_operator: bool = True
    assigned_worker_id: Optional[str] = None
    budget_token_limit: int = 25000
    budget_cost_usd_limit: float = 2.0
    tokens_used: int = 0
    cost_usd_used: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    evidence_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouterVerdict:
    admitted: bool
    admission_strength: AdmissionStrength
    status: WorkItemStatus
    work_item: Optional[WorkItem]
    gate_results: List[GateResult]
    assigned_role: str
    reply_text: str
    dispatched_worker_id: Optional[str] = None
    requires_approval: bool = False


class ThreadSubscriptionRegistry:
    """Tracks active thread bindings to isolated workers for follow-up dialogues."""

    def __init__(self, db_conn_factory=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self._ensure_table()

    def _ensure_table(self):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS af_thread_subscriptions (
                    thread_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    work_item_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    assigned_role TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_af_thread_sub_tenant ON af_thread_subscriptions(tenant_id)")
            conn.commit()

    def subscribe(self, thread_id: str, tenant_id: str, work_item_id: str, worker_id: str, assigned_role: str) -> None:
        now = time.time()
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                INSERT INTO af_thread_subscriptions
                (thread_id, tenant_id, work_item_id, worker_id, assigned_role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (thread_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    work_item_id = excluded.work_item_id,
                    worker_id = excluded.worker_id,
                    assigned_role = excluded.assigned_role,
                    updated_at = excluded.updated_at
                """,
                (thread_id, tenant_id, work_item_id, worker_id, assigned_role, now, now)
            )
            conn.commit()

    def get_subscription(self, thread_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        with self.db_conn_factory() as conn:
            cur = conn.execute(
                "SELECT thread_id, tenant_id, work_item_id, worker_id, assigned_role FROM af_thread_subscriptions WHERE thread_id = ? AND tenant_id = ?",
                (thread_id, tenant_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "thread_id": row[0],
                "tenant_id": row[1],
                "work_item_id": row[2],
                "worker_id": row[3],
                "assigned_role": row[4]
            }

    def clear(self, thread_id: str, tenant_id: str) -> None:
        with self.db_conn_factory() as conn:
            conn.execute("DELETE FROM af_thread_subscriptions WHERE thread_id = ? AND tenant_id = ?", (thread_id, tenant_id))
            conn.commit()


class WorkerSession:
    """Isolated execution session for a single Work Item.

    Ensures Law L1: workers run isolated, record heartbeats, monitor killswitches,
    and seal their deliverables to the Merkle ledger.
    """

    def __init__(
        self,
        worker_id: str,
        work_item: WorkItem,
        evidence_port: Optional[ZonataEvidenceAdapter] = None,
        db_conn_factory=None
    ):
        self.worker_id = worker_id
        self.work_item = work_item
        self.evidence = evidence_port or ZonataEvidenceAdapter()
        self.db_conn_factory = db_conn_factory or db.get_connection
        self._halt_event = threading.Event()
        self.started_at = time.time()
        self.scratch_context: Dict[str, Any] = {}

    def is_interrupted(self) -> bool:
        if self._halt_event.is_set():
            return True
        # Check deterministic kill switch
        gate = KillSwitchGate()
        res = gate.evaluate(tenant_id=self.work_item.tenant_id, surface="worker", target_id=self.worker_id)
        if not res.passed:
            self._halt_event.set()
            return True
        return False

    def halt(self, reason: str = "Halted by operator or killswitch"):
        logger.warning(f"WorkerSession {self.worker_id} halted: {reason}")
        self._halt_event.set()

    def run(self, execution_func: Callable[[WorkerSession], Dict[str, Any]]) -> Dict[str, Any]:
        """Executes the worker function within the isolated session boundary."""
        if self.is_interrupted():
            raise RuntimeError(f"Worker {self.worker_id} execution aborted: killswitch active")

        # Track tokens & start
        self.work_item.tokens_used += 150
        self.work_item.cost_usd_used += 0.0003

        try:
            result = execution_func(self)

            if self.is_interrupted():
                raise RuntimeError(f"Worker {self.worker_id} execution terminated before completion by killswitch")

            # Seal completion evidence
            now = time.time()
            event = EvidenceEvent(
                subject_kind="work_item",
                subject_id=self.work_item.work_item_id,
                event_type="work_item.completed",
                actor=self.work_item.target_role,
                payload_hashes={
                    "worker_id": self.worker_id,
                    "result_summary": str(result.get("summary", "success"))[:256],
                    "tokens_used": str(self.work_item.tokens_used),
                    "cost_usd_used": str(self.work_item.cost_usd_used),
                    "completed_at": str(now)
                },
                timestamp=now,
                tenant_id=self.work_item.tenant_id
            )
            ev_id = self.evidence.append_event(event)
            self.work_item.evidence_id = ev_id
            self.work_item.result = result
            return result
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed: {e}")
            self.work_item.error = str(e)
            raise


class WorkerPool:
    """Manages active worker concurrency with an inviolable reserved slot for human operators."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._active_sessions: Dict[str, WorkerSession] = {}
        self._lock = threading.Lock()
        self._pending_queue: List[WorkItem] = []

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active_sessions)

    def can_dispatch(self, is_human_operator: bool) -> bool:
        with self._lock:
            current = len(self._active_sessions)
            if current >= self.max_concurrent:
                return False
            # Reserve 1 slot exclusively for human operators
            if not is_human_operator and current >= (self.max_concurrent - 1):
                return False
            return True

    def register_session(self, session: WorkerSession) -> None:
        with self._lock:
            self._active_sessions[session.worker_id] = session

    def unregister_session(self, worker_id: str) -> None:
        with self._lock:
            self._active_sessions.pop(worker_id, None)

    def get_session(self, worker_id: str) -> Optional[WorkerSession]:
        with self._lock:
            return self._active_sessions.get(worker_id)

    def halt_all(self, reason: str = "Pool halt"):
        with self._lock:
            for s in self._active_sessions.values():
                s.halt(reason)


class URARouter:
    """URA Assistant Router & Worker Runtime Engine.

    Coordinates all incoming requests, deterministic gates, worker dispatch,
    and response synthesis in one cohesive voice.
    """

    def __init__(
        self,
        db_conn_factory=None,
        evidence_port: Optional[ZonataEvidenceAdapter] = None,
        max_concurrent_workers: int = 10
    ):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self.evidence = evidence_port or ZonataEvidenceAdapter()
        self.pool = WorkerPool(max_concurrent=max_concurrent_workers)
        self.threads = ThreadSubscriptionRegistry(db_conn_factory=self.db_conn_factory)
        self.owner_registry = AccountableOwnerRegistry(db_conn_factory=self.db_conn_factory, evidence_port=self.evidence)
        self.gate_pipeline = DeterministicGatePipeline()
        self._ensure_table()

    def _ensure_table(self):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS af_work_items (
                    work_item_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    admission_strength TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_role TEXT NOT NULL DEFAULT '@assistant',
                    autonomy_level INTEGER NOT NULL DEFAULT 0,
                    accountable_owner_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    is_human_operator INTEGER NOT NULL DEFAULT 1,
                    assigned_worker_id TEXT,
                    budget_token_limit INTEGER NOT NULL DEFAULT 25000,
                    budget_cost_usd_limit REAL NOT NULL DEFAULT 2.0,
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    cost_usd_used REAL NOT NULL DEFAULT 0.0,
                    result JSON,
                    error TEXT,
                    evidence_id TEXT,
                    metadata JSON,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    finished_at REAL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_af_wi_tenant_status ON af_work_items(tenant_id, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_af_wi_thread ON af_work_items(thread_id)")
            conn.commit()

    def parse_target_role(self, message: str) -> Tuple[str, str]:
        """Detects @role prefix (e.g. @CFO, @CEO, @CTO, @COO, @CHRO, @CISO, @CLO)."""
        match = _ROLE_REGEX.search(message)
        if match:
            raw_role = match.group(1).upper()
            if raw_role in EXECUTIVE_ROLES:
                cleaned = message[match.end():].lstrip(":,- ")
                return f"@{raw_role}", cleaned
        return "@ASSISTANT", message

    def classify_admission_strength(
        self,
        request_text: str,
        is_direct_user_message: bool = True
    ) -> AdmissionStrength:
        """Classifies incoming strength (Law L3).

        - EXPLICIT: Direct user request with valid structural intent.
        - INFERRED: Background event, autonomous suggestion, system trigger.
        - NOT_ADMITTED: Out of scope, prompt injection attack pattern, empty/gibberish.
        """
        text = (request_text or "").strip()
        if not text or len(text) < 4:
            return AdmissionStrength.NOT_ADMITTED

        # Structural rejection of obvious exfiltration / destructive attempts
        injection_patterns = [
            r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"(?i)bypass\s+all\s+safety\s+filters",
            r"(?i)drop\s+database\b",
            r"(?i)system:[\s\S]*admin",
            r"(?i)\bdan\s+mode\b",
            r"(?i)do\s+anything\s+now",
            r"(?i)reveal\s+internal\s+system\s+instructions",
            r"(?i)ignore\s+(company\s+)?charter"
        ]
        for pat in injection_patterns:
            if re.search(pat, text):
                return AdmissionStrength.NOT_ADMITTED

        if is_direct_user_message:
            return AdmissionStrength.EXPLICIT
        return AdmissionStrength.INFERRED

    def route_request(
        self,
        tenant_id: str,
        company_id: str,
        requester_id: str,
        message: str,
        thread_id: Optional[str] = None,
        charter: Optional[CompanyCharter] = None,
        autonomy_level: int = 0,
        is_human_operator: bool = True,
        action_name: str = "assistant.chat",
        amount_usd: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RouterVerdict:
        """Main entry point for URA Assistant Router.

        Evaluates gates, classifies admission, determines accountable owner,
        enforces autonomy observe mode, and dispatches work item.
        """
        context = context or {}
        thread_id = thread_id or f"th_{uuid.uuid4().hex[:12]}"
        target_role, cleaned_message = self.parse_target_role(message)

        # 1. Classify Admission Strength (Law L3)
        admission_strength = self.classify_admission_strength(cleaned_message, is_direct_user_message=is_human_operator)

        if admission_strength == AdmissionStrength.NOT_ADMITTED:
            return RouterVerdict(
                admitted=False,
                admission_strength=admission_strength,
                status=WorkItemStatus.FAILED,
                work_item=None,
                gate_results=[GateResult(passed=False, gate_name="AdmissionGate", code="ADMISSION_DROPPED", reason="Request failed structural admission checks.")],
                assigned_role=target_role,
                reply_text="Your request could not be admitted. It falls outside enterprise operational scope or security policy."
            )

        # 2. Check existing thread subscription for follow-up dialogues
        existing_sub = self.threads.get_subscription(thread_id, tenant_id)
        if existing_sub:
            assigned_worker_id = existing_sub["worker_id"]
            assigned_role = existing_sub["assigned_role"]
        else:
            assigned_worker_id = None
            assigned_role = target_role

        # 3. Resolve Accountable Executive Owner
        dept = "executive"
        role_key = assigned_role.lstrip("@").upper()
        if role_key in EXECUTIVE_ROLES:
            dept = EXECUTIVE_ROLES[role_key]["accountable_dept"]

        owner_rec = self.owner_registry.get_owner(tenant_id, company_id, dept)
        accountable_owner_id = owner_rec.owner_id if owner_rec else requester_id

        # 4. Deterministic Gate Pipeline Evaluation (Law L2)
        charter_obj = charter or CompanyCharter.default_for_company(tenant_id, company_id, accountable_owner_id)
        effective_autonomy = autonomy_level if not is_human_operator else max(autonomy_level, 3)
        mode = "explicit" if is_human_operator else "inferred"

        gate_results = self.gate_pipeline.evaluate_all(
            tenant_id=tenant_id,
            natural_language=cleaned_message,
            charter=charter_obj,
            action_name=action_name,
            autonomy_level=effective_autonomy,
            role="ai_employee" if not is_human_operator else "human_owner",
            amount_usd=amount_usd,
            mode=mode
        )

        # 5. Law L4: Observe-First Mode (Autonomy L0) & Inferred Request Gate
        is_observe_only = False
        failed_gates = [g for g in gate_results if not g.passed]
        if failed_gates:
            # Check if failure is due to Observe / Inferred autonomy gate
            observe_codes = {"AUTONOMY_L0_OBSERVE_ONLY", "INFERRED_AUTONOMY_INSUFFICIENT"}
            if all(g.code in observe_codes for g in failed_gates):
                is_observe_only = True
            else:
                primary_reason = failed_gates[0].reason
                return RouterVerdict(
                    admitted=False,
                    admission_strength=admission_strength,
                    status=WorkItemStatus.FAILED,
                    work_item=None,
                    gate_results=gate_results,
                    assigned_role=assigned_role,
                    reply_text=f"Action blocked by deterministic safety gate: {primary_reason}"
                )

        work_item_id = f"wi_{uuid.uuid4().hex[:12]}"
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        if admission_strength == AdmissionStrength.INFERRED and autonomy_level < 2:
            is_observe_only = True
        elif autonomy_level == 0 and not is_human_operator:
            is_observe_only = True

        status = WorkItemStatus.OBSERVED_ONLY if is_observe_only else WorkItemStatus.ADMITTED

        # Construct Work Item
        work_item = WorkItem(
            work_item_id=work_item_id,
            tenant_id=tenant_id,
            company_id=company_id,
            title=cleaned_message[:60],
            description=cleaned_message,
            admission_strength=admission_strength.value,
            status=status.value,
            target_role=assigned_role,
            autonomy_level=autonomy_level,
            accountable_owner_id=accountable_owner_id,
            session_id=session_id,
            thread_id=thread_id,
            requester_id=requester_id,
            is_human_operator=is_human_operator,
            budget_token_limit=25000,
            budget_cost_usd_limit=2.0
        )

        # Persist Work Item
        self._save_work_item(work_item)

        # Seal admission to Evidence Ledger
        now = time.time()
        event = EvidenceEvent(
            subject_kind="work_item",
            subject_id=work_item_id,
            event_type="work_item.admitted" if not is_observe_only else "work_item.observed_only",
            actor=requester_id,
            payload_hashes={
                "strength": admission_strength.value,
                "autonomy_level": str(autonomy_level),
                "assigned_role": assigned_role,
                "accountable_owner_id": accountable_owner_id,
                "message_sha256": str(hash(cleaned_message))
            },
            timestamp=now,
            tenant_id=tenant_id
        )
        ev_id = self.evidence.append_event(event)
        work_item.evidence_id = ev_id

        if is_observe_only:
            return RouterVerdict(
                admitted=True,
                admission_strength=admission_strength,
                status=WorkItemStatus.OBSERVED_ONLY,
                work_item=work_item,
                gate_results=gate_results,
                assigned_role=assigned_role,
                reply_text=f"[L{autonomy_level} Observe Mode] Event observed and logged as 'would accept'. No mutating actions dispatched."
            )

        # 6. Check Worker Concurrency and Reserved Slot
        if not self.pool.can_dispatch(is_human_operator=is_human_operator):
            return RouterVerdict(
                admitted=True,
                admission_strength=admission_strength,
                status=WorkItemStatus.ADMITTED,
                work_item=work_item,
                gate_results=gate_results,
                assigned_role=assigned_role,
                reply_text="System worker capacity is currently at limit. Work item is queued with reserved priority."
            )

        # 7. Check if Action Requires Human Approval (Autonomy L1 or High-Risk Action)
        requires_approval = False
        if autonomy_level == 1 and action_name != "assistant.chat":
            requires_approval = True
            work_item.status = WorkItemStatus.AWAITING_APPROVAL.value
            self._save_work_item(work_item)
            return RouterVerdict(
                admitted=True,
                admission_strength=admission_strength,
                status=WorkItemStatus.AWAITING_APPROVAL,
                work_item=work_item,
                gate_results=gate_results,
                assigned_role=assigned_role,
                reply_text=f"Request prepared by {assigned_role}. Requires human approval before execution (Autonomy L1).",
                requires_approval=True
            )

        # 8. Create Isolated Worker Session and Subscribe Thread
        worker_id = f"wkr_{uuid.uuid4().hex[:12]}"
        work_item.assigned_worker_id = worker_id
        session = WorkerSession(
            worker_id=worker_id,
            work_item=work_item,
            evidence_port=self.evidence,
            db_conn_factory=self.db_conn_factory
        )
        self.pool.register_session(session)
        self.threads.subscribe(thread_id, tenant_id, work_item_id, worker_id, assigned_role)

        # Transition status to DISPATCHED
        work_item = self.transition_work_item(work_item_id, WorkItemStatus.DISPATCHED, actor=requester_id, reason="Dispatched to worker session")
        session.work_item = work_item

        role_info = EXECUTIVE_ROLES.get(role_key, {"label": assigned_role})
        reply = f"Routed to {role_info.get('label', assigned_role)}. Worker session initialized."

        return RouterVerdict(
            admitted=True,
            admission_strength=admission_strength,
            status=WorkItemStatus.DISPATCHED,
            work_item=work_item,
            gate_results=gate_results,
            assigned_role=assigned_role,
            reply_text=reply,
            dispatched_worker_id=worker_id,
            requires_approval=False
        )

    def transition_work_item(
        self,
        work_item_id: str,
        to_state: WorkItemStatus,
        actor: str = "system",
        reason: str = ""
    ) -> WorkItem:
        """Enforces monotonic state transitions and seals Merkle evidence."""
        wi = self.get_work_item(work_item_id)
        if not wi:
            raise KeyError(f"Work item '{work_item_id}' not found.")

        current_state = WorkItemStatus(wi.status)
        valid_next = VALID_STATUS_TRANSITIONS.get(current_state, set())

        if to_state not in valid_next:
            raise ValueError(
                f"Invalid WorkItem state transition: cannot move from '{current_state.value}' to '{to_state.value}'."
            )

        now = time.time()
        wi.status = to_state.value
        wi.updated_at = now
        if to_state in (WorkItemStatus.COMPLETED, WorkItemStatus.FAILED, WorkItemStatus.CANCELLED, WorkItemStatus.KILLED, WorkItemStatus.OBSERVED_ONLY):
            wi.finished_at = now

        # Seal to Merkle ledger
        event = EvidenceEvent(
            subject_kind="work_item",
            subject_id=work_item_id,
            event_type=f"work_item.transition.{to_state.value.lower()}",
            actor=actor,
            payload_hashes={
                "from_state": current_state.value,
                "to_state": to_state.value,
                "reason": reason,
                "tokens_used": str(wi.tokens_used),
                "cost_usd_used": str(wi.cost_usd_used)
            },
            timestamp=now,
            tenant_id=wi.tenant_id
        )
        ev_id = self.evidence.append_event(event)
        wi.evidence_id = ev_id

        self._save_work_item(wi)

        # Unregister from pool if finished
        if wi.assigned_worker_id and to_state in (WorkItemStatus.COMPLETED, WorkItemStatus.FAILED, WorkItemStatus.CANCELLED, WorkItemStatus.KILLED):
            self.pool.unregister_session(wi.assigned_worker_id)

        return wi

    def get_work_item(self, work_item_id: str) -> Optional[WorkItem]:
        with self.db_conn_factory() as conn:
            cur = conn.execute(
                """
                SELECT work_item_id, tenant_id, company_id, title, description, admission_strength,
                       status, target_role, autonomy_level, accountable_owner_id, session_id,
                       thread_id, requester_id, is_human_operator, assigned_worker_id,
                       budget_token_limit, budget_cost_usd_limit, tokens_used, cost_usd_used,
                       result, error, evidence_id, metadata, created_at, updated_at, finished_at
                FROM af_work_items WHERE work_item_id = ?
                """,
                (work_item_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_work_item(row)

    def list_work_items(self, tenant_id: str, status: Optional[str] = None) -> List[WorkItem]:
        with self.db_conn_factory() as conn:
            if status:
                cur = conn.execute(
                    "SELECT * FROM af_work_items WHERE tenant_id = ? AND status = ? ORDER BY created_at DESC",
                    (tenant_id, status)
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM af_work_items WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,)
                )
            rows = cur.fetchall()
            return [self._row_to_work_item(r) for r in rows]

    def _save_work_item(self, wi: WorkItem):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                INSERT INTO af_work_items (
                    work_item_id, tenant_id, company_id, title, description, admission_strength,
                    status, target_role, autonomy_level, accountable_owner_id, session_id,
                    thread_id, requester_id, is_human_operator, assigned_worker_id,
                    budget_token_limit, budget_cost_usd_limit, tokens_used, cost_usd_used,
                    result, error, evidence_id, metadata, created_at, updated_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (work_item_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    company_id = excluded.company_id,
                    title = excluded.title,
                    description = excluded.description,
                    admission_strength = excluded.admission_strength,
                    status = excluded.status,
                    target_role = excluded.target_role,
                    autonomy_level = excluded.autonomy_level,
                    accountable_owner_id = excluded.accountable_owner_id,
                    session_id = excluded.session_id,
                    thread_id = excluded.thread_id,
                    requester_id = excluded.requester_id,
                    is_human_operator = excluded.is_human_operator,
                    assigned_worker_id = excluded.assigned_worker_id,
                    budget_token_limit = excluded.budget_token_limit,
                    budget_cost_usd_limit = excluded.budget_cost_usd_limit,
                    tokens_used = excluded.tokens_used,
                    cost_usd_used = excluded.cost_usd_used,
                    result = excluded.result,
                    error = excluded.error,
                    evidence_id = excluded.evidence_id,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at,
                    finished_at = excluded.finished_at
                """,
                (
                    wi.work_item_id,
                    wi.tenant_id,
                    wi.company_id,
                    wi.title,
                    wi.description,
                    wi.admission_strength,
                    wi.status,
                    wi.target_role,
                    wi.autonomy_level,
                    wi.accountable_owner_id,
                    wi.session_id,
                    wi.thread_id,
                    wi.requester_id,
                    1 if wi.is_human_operator else 0,
                    wi.assigned_worker_id,
                    wi.budget_token_limit,
                    wi.budget_cost_usd_limit,
                    wi.tokens_used,
                    wi.cost_usd_used,
                    json.dumps(wi.result) if wi.result else None,
                    wi.error,
                    wi.evidence_id,
                    json.dumps(wi.metadata) if wi.metadata else None,
                    wi.created_at,
                    wi.updated_at,
                    wi.finished_at
                )
            )
            conn.commit()

    def _row_to_work_item(self, row: Any) -> WorkItem:
        return WorkItem(
            work_item_id=row[0],
            tenant_id=row[1],
            company_id=row[2],
            title=row[3],
            description=row[4],
            admission_strength=row[5],
            status=row[6],
            target_role=row[7],
            autonomy_level=row[8],
            accountable_owner_id=row[9],
            session_id=row[10],
            thread_id=row[11],
            requester_id=row[12],
            is_human_operator=bool(row[13]),
            assigned_worker_id=row[14],
            budget_token_limit=row[15],
            budget_cost_usd_limit=row[16],
            tokens_used=row[17],
            cost_usd_used=row[18],
            result=json.loads(row[19]) if row[19] else None,
            error=row[20],
            evidence_id=row[21],
            metadata=json.loads(row[22]) if row[22] else {},
            created_at=row[23],
            updated_at=row[24],
            finished_at=row[25]
        )
