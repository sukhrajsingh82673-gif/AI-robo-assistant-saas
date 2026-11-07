"""
ZONATA Autonomous Executive Coworker — Milestone 1: Executive Operating Loop & Governance
Implements the 8-tier operating priority queue, Delegation of Authority (DoA)
governance thresholds ($10,000 ceiling), and integration with the AI CEO Bridge.
"""

from __future__ import annotations
import time
import uuid
import queue
import threading
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .ceo_coworker_bridge import (
    AICeoMissionRequest, AICeoMissionResponse, AICeoCoworkerBridge
)


class OperatingPriority(IntEnum):
    """8-tier operational priority ladder for Executive Coworker dispatch."""
    P1_SECURITY_CRITICAL = 1
    P2_OUTAGE_RECOVERY = 2
    P3_CEO_DIRECTIVE = 3
    P4_EMPLOYEE_BLOCKER = 4
    P5_SCHEDULED_OPERATION = 5
    P6_BACKGROUND_RESEARCH = 6
    P7_CONTINUOUS_PATROL = 7
    P8_ROUTINE_MAINTENANCE = 8


class WorkItemStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED_DOA = "REJECTED_DOA"


@dataclass
class PriorityWorkItem:
    item_id: str
    priority: OperatingPriority
    title: str
    description: str
    cost_estimate_usd: float = 0.0
    mission_request: Optional[AICeoMissionRequest] = None
    requires_human_approval: bool = False
    status: WorkItemStatus = WorkItemStatus.PENDING
    result: Optional[AICeoMissionResponse] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: PriorityWorkItem) -> bool:
        # Priority queue sorts by priority int (lower int = higher urgency)
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at


class ExecutiveOperatingLoop:
    """
    Continuous Executive Operating Loop.
    Enforces Delegation of Authority (DoA) limits, schedules high-priority work,
    and bridges AI CEO directives with verified execution.
    """

    DEFAULT_DOA_CEILING_USD = 10000.00

    def __init__(
        self,
        bridge: Optional[AICeoCoworkerBridge] = None,
        doa_ceiling_usd: float = DEFAULT_DOA_CEILING_USD,
        tenant_id: str = "tnt_primary"
    ):
        self.bridge = bridge or AICeoCoworkerBridge(tenant_id=tenant_id)
        self.doa_ceiling_usd = doa_ceiling_usd
        self.tenant_id = tenant_id
        self._work_queue: queue.PriorityQueue[PriorityWorkItem] = queue.PriorityQueue()
        self._active_items: Dict[str, PriorityWorkItem] = {}
        self._history: List[PriorityWorkItem] = []
        self._lock = threading.RLock()
        self.total_processed: int = 0
        self.total_blocked_doa: int = 0

    def submit_work_item(
        self,
        title: str,
        description: str,
        priority: OperatingPriority = OperatingPriority.P3_CEO_DIRECTIVE,
        cost_estimate_usd: float = 0.0,
        mission_request: Optional[AICeoMissionRequest] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PriorityWorkItem:
        """
        Submits a work item into the priority operating loop.
        Applies Delegation of Authority (DoA) threshold verification.
        """
        item_id = f"wi_{uuid.uuid4().hex[:8]}"
        requires_approval = False
        initial_status = WorkItemStatus.PENDING

        effective_cost = cost_estimate_usd
        if mission_request and mission_request.budget > effective_cost:
            effective_cost = mission_request.budget

        # DoA Evaluation: Spending ceiling check
        if effective_cost > self.doa_ceiling_usd:
            requires_approval = True
            initial_status = WorkItemStatus.AWAITING_APPROVAL

        # If mission request specifies human approval requirement
        if mission_request and mission_request.risk_policy.get("require_human_approval", False):
            requires_approval = True
            initial_status = WorkItemStatus.AWAITING_APPROVAL

        item = PriorityWorkItem(
            item_id=item_id,
            priority=priority,
            title=title,
            description=description,
            cost_estimate_usd=effective_cost,
            mission_request=mission_request,
            requires_human_approval=requires_approval,
            status=initial_status,
            metadata=metadata or {}
        )

        with self._lock:
            self._active_items[item_id] = item
            if not requires_approval:
                self._work_queue.put(item)
            else:
                self.total_blocked_doa += 1

        return item

    def approve_work_item(self, item_id: str, approver_role: str = "CEO") -> bool:
        """Approves a work item held in AWAITING_APPROVAL."""
        with self._lock:
            item = self._active_items.get(item_id)
            if not item or item.status != WorkItemStatus.AWAITING_APPROVAL:
                return False

            item.status = WorkItemStatus.PENDING
            item.requires_human_approval = False
            item.metadata["approved_by"] = approver_role
            item.metadata["approved_at"] = time.time()
            self._work_queue.put(item)
            return True

    def reject_work_item(self, item_id: str, reason: str = "DoA Exceeded") -> bool:
        """Rejects a work item held in AWAITING_APPROVAL."""
        with self._lock:
            item = self._active_items.get(item_id)
            if not item:
                return False

            item.status = WorkItemStatus.REJECTED_DOA
            item.metadata["rejection_reason"] = reason
            item.updated_at = time.time()
            self._history.append(item)
            self._active_items.pop(item_id, None)
            return True

    def process_next(self) -> Optional[PriorityWorkItem]:
        """Dequeues and executes the highest-priority work item."""
        try:
            item = self._work_queue.get_nowait()
        except queue.Empty:
            return None

        with self._lock:
            item.status = WorkItemStatus.IN_PROGRESS
            item.updated_at = time.time()

        try:
            if item.mission_request:
                # Dispatch through AI CEO Coworker Bridge
                resp = self.bridge.execute_ceo_mission(item.mission_request)
                item.result = resp
                item.status = WorkItemStatus.COMPLETED if resp.execution_status in ("COMPLETED", "VERIFIED") else WorkItemStatus.FAILED
            else:
                # Local completion
                item.status = WorkItemStatus.COMPLETED

            item.updated_at = time.time()
            with self._lock:
                self.total_processed += 1
                self._history.append(item)
                self._active_items.pop(item.item_id, None)

        except Exception as ex:
            item.status = WorkItemStatus.FAILED
            item.metadata["error"] = str(ex)
            item.updated_at = time.time()
            with self._lock:
                self._history.append(item)
                self._active_items.pop(item.item_id, None)

        finally:
            self._work_queue.task_done()

        return item

    def run_cycle(self, max_items: int = 10) -> List[PriorityWorkItem]:
        """Executes up to max_items in priority order."""
        processed: List[PriorityWorkItem] = []
        for _ in range(max_items):
            item = self.process_next()
            if not item:
                break
            processed.append(item)
        return processed

    def get_queue_depth(self) -> int:
        return self._work_queue.qsize()

    def get_pending_approvals(self) -> List[PriorityWorkItem]:
        with self._lock:
            return [
                item for item in self._active_items.values()
                if item.status == WorkItemStatus.AWAITING_APPROVAL
            ]

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            pending_count = sum(1 for item in self._active_items.values() if item.status == WorkItemStatus.AWAITING_APPROVAL)
            return {
                "queue_depth": self._work_queue.qsize(),
                "active_count": len(self._active_items),
                "total_processed": self.total_processed,
                "total_blocked_doa": self.total_blocked_doa,
                "doa_ceiling_usd": self.doa_ceiling_usd,
                "pending_approvals_count": pending_count
            }
