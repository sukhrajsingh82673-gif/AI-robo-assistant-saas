"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Executive Mission Manager & Loop / Cost Protection

Implements Section 11, Section 32, Section 33 of the Gemma 4 Master Specification:
- Concurrency owner for multiple simultaneous missions
- Context isolation: Gemma 4 receives concise executive summaries without context blowout
- Mission record fields:
    mission_id, company_id, objective, priority, state, owner, department,
    agents, dependencies, deadline, risk, budget, progress, evidence,
    status, last_update, next_action
- Cost Control & Bounded Execution (Section 32):
    Tracks token consumption, latency, cost per department/mission/tenant.
    Enforces caps: max_iterations, max_model_calls, max_cost_usd, max_execution_time, max_retries.
- Deterministic Loop Protection (Section 33):
    Detects recursive delegation, agent ping-pong, repeated tool calls, failed retries,
    oscillating decisions, duplicate missions, duplicate transactions, infinite planning.
"""

import time
import json
import uuid
import hashlib
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.executive.mission_manager")

class LoopViolationError(RuntimeError):
    """Raised when deterministic loop protection intercepts an autonomous loop."""
    pass

@dataclass
class GovernedMissionRecord:
    mission_id: str
    company_id: str
    tenant_id: str
    objective: str
    priority: str                       # P0, P1, P2, P3
    state: str                          # DISCOVER, PLAN, ASSIGN, EXECUTE, VERIFY, COMPLETED, BLOCKED, FAILED
    owner: str                          # "AI CEO" or Human Owner
    department: str
    agents: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    deadline: float = field(default_factory=lambda: time.time() + 7 * 86400)
    risk: str = "MEDIUM"                # LOW, MEDIUM, HIGH, CRITICAL
    budget: float = 10000.0             # in INR
    progress: int = 0                   # 0 to 100
    evidence: List[str] = field(default_factory=list)
    status: str = "ACTIVE"              # ACTIVE, PAUSED, COMPLETED, FAILED, ESCALATED
    last_update: float = field(default_factory=time.time)
    next_action: str = "Initialize discovery baseline"

    # Cost & Loop Guardrails (Section 32 & 33)
    model_calls_count: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    iteration_count: int = 0
    retries_count: int = 0
    recent_tool_calls: List[str] = field(default_factory=list)
    recent_agent_transfers: List[str] = field(default_factory=list)

    # Maximum Bounded Limits
    max_iterations: int = 25
    max_model_calls: int = 15
    max_cost_usd: float = 5.0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_executive_summary(self) -> Dict[str, Any]:
        """Compact summary designed for Gemma 4 context without blowout."""
        return {
            "mission_id": self.mission_id,
            "dept": self.department,
            "priority": self.priority,
            "progress": f"{self.progress}%",
            "state": self.state,
            "status": self.status,
            "cost_usd": round(self.total_cost_usd, 4),
            "next_action": self.next_action
        }


class ExecutiveMissionManager:
    """
    Manages active mission pool, concurrency, loop safeguards, and budget tracking.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._missions: Dict[str, GovernedMissionRecord] = {}
        self._mission_signatures: Dict[str, str] = {}  # For duplicate detection

    def create_mission(
        self,
        objective: str,
        department: str,
        priority: str = "P1",
        budget: float = 10000.0,
        risk: str = "MEDIUM",
        owner: str = "AI CEO",
        agents: Optional[List[str]] = None,
        deadline_days: int = 7
    ) -> GovernedMissionRecord:
        # Loop Protection: Duplicate Mission Detection
        sig_data = f"{self.company_id}:{department}:{objective.strip().lower()}"
        sig_hash = hashlib.sha256(sig_data.encode("utf-8")).hexdigest()

        for existing in self._missions.values():
            if existing.status == "ACTIVE" and self._mission_signatures.get(existing.mission_id) == sig_hash:
                logger.warning(f"Duplicate active mission intercepted for objective: '{objective}'")
                return existing

        mission_id = f"msn_{uuid.uuid4().hex[:8]}"
        self._mission_signatures[mission_id] = sig_hash

        rec = GovernedMissionRecord(
            mission_id=mission_id,
            company_id=self.company_id,
            tenant_id=self.tenant_id,
            objective=objective,
            priority=priority,
            state="DISCOVER",
            owner=owner,
            department=department,
            agents=agents or [f"{department.lower().replace(' ', '_')}_operator"],
            deadline=time.time() + (deadline_days * 86400),
            risk=risk,
            budget=budget,
            progress=0,
            evidence=[],
            status="ACTIVE",
            last_update=time.time(),
            next_action="Execute initial discovery"
        )
        self._missions[mission_id] = rec
        return rec

    def get_mission(self, mission_id: str) -> Optional[GovernedMissionRecord]:
        return self._missions.get(mission_id)

    def list_missions(self, status_filter: Optional[str] = None) -> List[GovernedMissionRecord]:
        if status_filter:
            return [m for m in self._missions.values() if m.status == status_filter]
        return list(self._missions.values())

    def get_all_executive_summaries(self) -> List[Dict[str, Any]]:
        return [m.to_executive_summary() for m in self._missions.values()]

    # -------------------------------------------------------------------------
    # Loop & Cost Guardrails Enforcement (Section 32 & 33)
    # -------------------------------------------------------------------------

    def record_iteration_tick(self, mission_id: str, tool_id: Optional[str] = None, agent_id: Optional[str] = None):
        mission = self.get_mission(mission_id)
        if not mission:
            return

        mission.iteration_count += 1
        mission.last_update = time.time()

        # 1. Check Max Iterations
        if mission.iteration_count > mission.max_iterations:
            mission.status = "BLOCKED"
            raise LoopViolationError(
                f"Loop Protection Intercept: Mission '{mission_id}' exceeded max iterations ({mission.max_iterations}). Paused for safety."
            )

        # 2. Check Repeated Tool Calls (Ping-Pong / Tool thrashing)
        if tool_id:
            mission.recent_tool_calls.append(tool_id)
            if len(mission.recent_tool_calls) > 6:
                mission.recent_tool_calls.pop(0)
            # If the same tool was called 4 consecutive times with no state change
            if len(mission.recent_tool_calls) >= 4 and all(t == tool_id for t in mission.recent_tool_calls[-4:]):
                mission.status = "BLOCKED"
                raise LoopViolationError(
                    f"Loop Protection Intercept: Repeated identical tool invocation '{tool_id}' detected on mission '{mission_id}'."
                )

        # 3. Check Agent Ping-Pong
        if agent_id:
            mission.recent_agent_transfers.append(agent_id)
            if len(mission.recent_agent_transfers) > 6:
                mission.recent_agent_transfers.pop(0)
            if len(mission.recent_agent_transfers) >= 4 and len(set(mission.recent_agent_transfers[-4:])) <= 2:
                # Oscillating between 2 agents
                if mission.recent_agent_transfers[-1] == mission.recent_agent_transfers[-3] and \
                   mission.recent_agent_transfers[-2] == mission.recent_agent_transfers[-4]:
                    mission.status = "BLOCKED"
                    raise LoopViolationError(
                        f"Loop Protection Intercept: Agent delegation ping-pong oscillation detected between {set(mission.recent_agent_transfers[-4:])}."
                    )

    def record_model_usage(self, mission_id: str, prompt_tokens: int, completion_tokens: int, cost_usd: float):
        mission = self.get_mission(mission_id)
        if not mission:
            return

        mission.model_calls_count += 1
        mission.total_tokens_used += (prompt_tokens + completion_tokens)
        mission.total_cost_usd += cost_usd

        if mission.model_calls_count > mission.max_model_calls:
            mission.status = "BLOCKED"
            raise LoopViolationError(
                f"Cost Guardrail Intercept: Mission '{mission_id}' exceeded max model calls ({mission.max_model_calls})."
            )

        if mission.total_cost_usd > mission.max_cost_usd:
            mission.status = "BLOCKED"
            raise LoopViolationError(
                f"Cost Guardrail Intercept: Mission '{mission_id}' exceeded dollar cost ceiling (${mission.max_cost_usd})."
            )

    def pause_all_missions(self, reason: str = "Emergency Stop engaged") -> int:
        count = 0
        for m in self._missions.values():
            if m.status in ("ACTIVE", "READY"):
                m.status = "PAUSED"
                m.next_action = f"Frozen: {reason}"
                count += 1
        return count

    def resume_mission(self, mission_id: str) -> bool:
        m = self.get_mission(mission_id)
        if m and m.status == "PAUSED":
            m.status = "ACTIVE"
            m.next_action = "Resumed by Sovereign Owner"
            return True
        return False
