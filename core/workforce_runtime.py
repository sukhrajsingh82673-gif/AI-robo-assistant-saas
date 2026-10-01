"""
RoboAssistant Company OS — Workforce Runtime Interface & Ephemeral Swarm Execution Engine
Provides an abstract WorkforceRuntime contract and concrete SwarmWorkforceRuntime.
Implements multi-agent directional collaboration graphs, role delegation, handoff mechanics,
configurable delegation limits, cycle detection, runtime budget ceilings, and emergency kill switches.

Architectural Rule:
The workforce runtime coordinates agents; ZONATA retains 100% of the authority,
policy enforcement, credential brokerage, tool sandboxing, and evidence verification.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
import hashlib

class SpecialistStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    PROVISIONING = "PROVISIONING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"

class WorkforceLifecycleState(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    PROVISIONING = "PROVISIONING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    DISBANDED = "DISBANDED"
    QUARANTINED = "QUARANTINED"

@dataclass
class SpecialistRole:
    id: str
    name: str
    role: str
    department: str
    mission_id: str
    tenant_id: str
    company_id: str
    capabilities: List[str]
    allowed_tools: List[str]
    forbidden_tools: List[str]
    model_policy: Dict[str, Any]
    context_scope: Dict[str, Any]
    authority_scope: str = "SANDBOXED_READ_ONLY"
    budget: float = 100.0
    cost_spent: float = 0.0
    time_limit_seconds: int = 1800
    max_delegation_depth: int = 3
    risk_level: str = "LOW"
    status: SpecialistStatus = SpecialistStatus.READY
    current_task: Optional[str] = None
    created_at: float = field(default_factory=time.time)

@dataclass
class CollaborationMessage:
    id: str
    workforce_id: str
    mission_id: str
    sender_id: str
    sender_role: str
    recipient_id: str
    recipient_role: str
    message_type: str  # "TASK_DELEGATION", "HANDOFF", "REPORT", "QUERY", "EVIDENCE_SUBMISSION"
    content: str
    delegation_depth: int
    attachments: Dict[str, Any] = field(default_factory=dict)
    tool_references: List[str] = field(default_factory=list)
    decision_references: List[str] = field(default_factory=list)
    evidence_references: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

@dataclass
class RuntimeBudget:
    max_cost_usd: float = 50.0
    max_execution_seconds: float = 1800.0
    max_tool_calls: int = 100
    max_external_requests: int = 50
    max_delegated_agents: int = 8
    
    current_cost_usd: float = 0.0
    current_tool_calls: int = 0
    current_external_requests: int = 0
    start_time: float = field(default_factory=time.time)

    def is_exhausted(self) -> Tuple[bool, str]:
        if self.current_cost_usd >= self.max_cost_usd:
            return True, f"Cost budget limit reached: ${self.current_cost_usd:.2f} >= ${self.max_cost_usd:.2f}"
        if self.current_tool_calls >= self.max_tool_calls:
            return True, f"Tool call budget reached: {self.current_tool_calls} >= {self.max_tool_calls}"
        if self.current_external_requests >= self.max_external_requests:
            return True, f"External request budget reached: {self.current_external_requests} >= {self.max_external_requests}"
        elapsed = time.time() - self.start_time
        if elapsed >= self.max_execution_seconds:
            return True, f"Execution time limit reached: {elapsed:.1f}s >= {self.max_execution_seconds:.1f}s"
        return False, "Budget healthy"


class WorkforceRuntime(ABC):
    """
    Abstract Workforce Orchestration Interface.
    Enables pluggable runtime backends (Swarm, LangGraph, etc.)
    without rewriting ZONATA's company OS and authority logic.
    """

    @abstractmethod
    def create_workforce(
        self,
        workforce_id: str,
        mission_id: str,
        tenant_id: str,
        company_id: str,
        specialists: List[SpecialistRole],
        communication_flows: List[Tuple[str, str]],
        budget: RuntimeBudget,
        max_delegation_depth: int = 3
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def add_specialist(self, workforce_id: str, specialist: SpecialistRole) -> bool:
        pass

    @abstractmethod
    def define_role(self, workforce_id: str, role_definition: Dict[str, Any]) -> SpecialistRole:
        pass

    @abstractmethod
    def assign_capability(self, workforce_id: str, agent_id: str, capability: str) -> bool:
        pass

    @abstractmethod
    def create_collaboration(self, workforce_id: str, sender_role: str, recipient_role: str) -> bool:
        pass

    @abstractmethod
    def send_message(
        self,
        workforce_id: str,
        sender_id: str,
        recipient_id: str,
        content: str,
        message_type: str = "QUERY",
        attachments: Optional[Dict[str, Any]] = None
    ) -> CollaborationMessage:
        pass

    @abstractmethod
    def delegate_task(
        self,
        workforce_id: str,
        delegator_id: str,
        assignee_id: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def request_handoff(
        self,
        workforce_id: str,
        from_agent_id: str,
        to_agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def pause_workforce(self, workforce_id: str) -> bool:
        pass

    @abstractmethod
    def resume_workforce(self, workforce_id: str) -> bool:
        pass

    @abstractmethod
    def terminate_workforce(self, workforce_id: str, reason: str = "COMPLETED") -> bool:
        pass

    @abstractmethod
    def collect_results(self, workforce_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def collect_evidence(self, workforce_id: str) -> List[Dict[str, Any]]:
        pass


class SwarmWorkforceRuntime(WorkforceRuntime):
    """
    Concrete Multi-Agent Workforce Orchestration Runtime.
    Implements directional communication topology, role handoffs,
    strict delegation depth caps, cycle detection, and budget governance.
    """

    def __init__(self):
        self.workforces: Dict[str, Dict[str, Any]] = {}
        self.specialists: Dict[str, SpecialistRole] = {}
        self.messages: Dict[str, List[CollaborationMessage]] = {}
        self.evidence_records: Dict[str, List[Dict[str, Any]]] = {}
        self.call_chains: Dict[str, List[str]] = {}

    def create_workforce(
        self,
        workforce_id: str,
        mission_id: str,
        tenant_id: str,
        company_id: str,
        specialists: List[SpecialistRole],
        communication_flows: List[Tuple[str, str]],
        budget: RuntimeBudget,
        max_delegation_depth: int = 3
    ) -> Dict[str, Any]:
        # Validate tenant and company scoping
        for s in specialists:
            if s.tenant_id != tenant_id:
                raise PermissionError(f"Tenant mismatch: Agent {s.id} tenant '{s.tenant_id}' != '{tenant_id}'")
            if s.company_id != company_id:
                raise PermissionError(f"Company mismatch: Agent {s.id} company '{s.company_id}' != '{company_id}'")

        # Map directional communications
        flow_graph: Dict[str, Set[str]] = {}
        for s in specialists:
            flow_graph[s.id] = set()
            self.specialists[s.id] = s

        for sender, recipient in communication_flows:
            if sender in flow_graph:
                flow_graph[sender].add(recipient)

        workforce = {
            "workforce_id": workforce_id,
            "mission_id": mission_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "state": WorkforceLifecycleState.READY,
            "specialist_ids": [s.id for s in specialists],
            "lead_specialist_id": specialists[0].id if specialists else None,
            "communication_graph": {k: list(v) for k, v in flow_graph.items()},
            "budget": budget,
            "max_delegation_depth": max_delegation_depth,
            "kill_switch_active": False,
            "paused": False,
            "tasks": [],
            "results": {},
            "created_at": time.time(),
            "updated_at": time.time()
        }
        self.workforces[workforce_id] = workforce
        self.messages[workforce_id] = []
        self.evidence_records[workforce_id] = []
        self.call_chains[workforce_id] = []
        return workforce

    def add_specialist(self, workforce_id: str, specialist: SpecialistRole) -> bool:
        wf = self.workforces.get(workforce_id)
        if not wf:
            raise KeyError(f"Workforce '{workforce_id}' not found")
        if wf["kill_switch_active"]:
            raise RuntimeError(f"Workforce '{workforce_id}' is quarantined by kill switch")

        # Scoping check
        if specialist.tenant_id != wf["tenant_id"] or specialist.company_id != wf["company_id"]:
            raise PermissionError("Cross-tenant or cross-company specialist insertion blocked")

        if len(wf["specialist_ids"]) >= wf["budget"].max_delegated_agents:
            raise RuntimeError(f"Budget limit reached for max delegated agents ({wf['budget'].max_delegated_agents})")

        self.specialists[specialist.id] = specialist
        if specialist.id not in wf["specialist_ids"]:
            wf["specialist_ids"].append(specialist.id)
            wf["communication_graph"][specialist.id] = []
        return True

    def define_role(self, workforce_id: str, role_definition: Dict[str, Any]) -> SpecialistRole:
        wf = self.workforces.get(workforce_id)
        if not wf:
            raise KeyError(f"Workforce '{workforce_id}' not found")

        role_id = role_definition.get("id") or f"spec_{uuid.uuid4().hex[:8]}"
        spec = SpecialistRole(
            id=role_id,
            name=role_definition.get("name", "Specialist"),
            role=role_definition.get("role", "Generalist"),
            department=role_definition.get("department", "Operations"),
            mission_id=wf["mission_id"],
            tenant_id=wf["tenant_id"],
            company_id=wf["company_id"],
            capabilities=role_definition.get("capabilities", []),
            allowed_tools=role_definition.get("allowed_tools", []),
            forbidden_tools=role_definition.get("forbidden_tools", ["destructive_fs", "raw_secrets", "direct_sql"]),
            model_policy=role_definition.get("model_policy", {"provider": "gemini", "model": "gemini-1.5-flash"}),
            context_scope=role_definition.get("context_scope", {"tenant_id": wf["tenant_id"], "company_id": wf["company_id"]}),
            authority_scope=role_definition.get("authority_scope", "SANDBOXED_READ_ONLY"),
            budget=role_definition.get("budget", 50.0),
            max_delegation_depth=role_definition.get("max_delegation_depth", wf["max_delegation_depth"]),
            risk_level=role_definition.get("risk_level", "LOW"),
            status=SpecialistStatus.READY
        )
        self.add_specialist(workforce_id, spec)
        return spec

    def assign_capability(self, workforce_id: str, agent_id: str, capability: str) -> bool:
        spec = self.specialists.get(agent_id)
        if not spec:
            raise KeyError(f"Specialist '{agent_id}' not found")
        if capability not in spec.capabilities:
            spec.capabilities.append(capability)
        return True

    def create_collaboration(self, workforce_id: str, sender_role: str, recipient_role: str) -> bool:
        wf = self.workforces.get(workforce_id)
        if not wf:
            raise KeyError(f"Workforce '{workforce_id}' not found")
        graph = wf["communication_graph"]
        if sender_role not in graph:
            graph[sender_role] = []
        if recipient_role not in graph[sender_role]:
            graph[sender_role].append(recipient_role)
        return True

    def send_message(
        self,
        workforce_id: str,
        sender_id: str,
        recipient_id: str,
        content: str,
        message_type: str = "QUERY",
        attachments: Optional[Dict[str, Any]] = None
    ) -> CollaborationMessage:
        wf = self.workforces.get(workforce_id)
        if not wf:
            raise KeyError(f"Workforce '{workforce_id}' not found")
        if wf["kill_switch_active"]:
            raise RuntimeError("Kill switch engaged: messaging halted")
        if wf["paused"]:
            raise RuntimeError("Workforce paused: messaging suspended")

        # Budget Check
        exhausted, reason = wf["budget"].is_exhausted()
        if exhausted:
            wf["state"] = WorkforceLifecycleState.BLOCKED
            raise RuntimeError(f"Workforce blocked by budget exhaustion: {reason}")

        # Validate Directional Graph
        graph = wf["communication_graph"]
        allowed_recipients = graph.get(sender_id, [])
        if recipient_id not in allowed_recipients and sender_id != wf.get("lead_specialist_id"):
            raise PermissionError(
                f"Communication flow violation: '{sender_id}' is not authorized to contact '{recipient_id}'. "
                f"Allowed recipients: {allowed_recipients}"
            )

        # Cycle & Loop Protection
        recent_chain = self.call_chains[workforce_id]
        if len(recent_chain) >= 2:
            if recent_chain[-1] == recipient_id and recent_chain[-2] == sender_id:
                # Cycle detected: A -> B -> A
                wf["state"] = WorkforceLifecycleState.BLOCKED
                raise RuntimeError(
                    f"Agent loop cycle detected ({sender_id} -> {recipient_id} -> {sender_id}). Execution paused."
                )

        # Message Count Limits (Max 50 turns per mission)
        if len(self.messages[workforce_id]) >= 50:
            wf["state"] = WorkforceLifecycleState.BLOCKED
            raise RuntimeError("Maximum message turn limit (50) exceeded. Escalate to ZONATA AI CEO.")

        sender = self.specialists.get(sender_id)
        recipient = self.specialists.get(recipient_id)
        depth = len(recent_chain) + 1

        if depth > wf["max_delegation_depth"]:
            wf["state"] = WorkforceLifecycleState.BLOCKED
            raise RuntimeError(f"Maximum delegation depth ({wf['max_delegation_depth']}) exceeded at depth {depth}.")


        msg = CollaborationMessage(
            id=f"cmsg_{uuid.uuid4().hex[:10]}",
            workforce_id=workforce_id,
            mission_id=wf["mission_id"],
            sender_id=sender_id,
            sender_role=sender.role if sender else "ExternalCoordinator",
            recipient_id=recipient_id,
            recipient_role=recipient.role if recipient else "Worker",
            message_type=message_type,
            content=content,
            delegation_depth=depth,
            attachments=attachments or {}
        )
        self.messages[workforce_id].append(msg)
        self.call_chains[workforce_id].append(sender_id)
        return msg

    def delegate_task(
        self,
        workforce_id: str,
        delegator_id: str,
        assignee_id: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        msg = self.send_message(
            workforce_id=workforce_id,
            sender_id=delegator_id,
            recipient_id=assignee_id,
            content=task.get("instruction", "Execute assigned task"),
            message_type="TASK_DELEGATION",
            attachments=task
        )
        assignee = self.specialists.get(assignee_id)
        if assignee:
            assignee.status = SpecialistStatus.EXECUTING
            assignee.current_task = task.get("title", task.get("instruction", "Task"))

        wf = self.workforces[workforce_id]
        wf["tasks"].append({
            "task_id": task.get("id", f"tsk_{uuid.uuid4().hex[:8]}"),
            "delegator_id": delegator_id,
            "assignee_id": assignee_id,
            "title": task.get("title", "Delegated Task"),
            "status": "IN_PROGRESS",
            "message_id": msg.id,
            "assigned_at": time.time()
        })
        return {"status": "DELEGATED", "task_id": task.get("id"), "message_id": msg.id}

    def request_handoff(
        self,
        workforce_id: str,
        from_agent_id: str,
        to_agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        msg = self.send_message(
            workforce_id=workforce_id,
            sender_id=from_agent_id,
            recipient_id=to_agent_id,
            content=f"Handoff execution context: {context.get('summary', 'Scope transition')}",
            message_type="HANDOFF",
            attachments=context
        )
        from_spec = self.specialists.get(from_agent_id)
        to_spec = self.specialists.get(to_agent_id)
        if from_spec:
            from_spec.status = SpecialistStatus.COMPLETED
        if to_spec:
            to_spec.status = SpecialistStatus.EXECUTING
            to_spec.current_task = f"Handoff from {from_spec.name if from_spec else from_agent_id}"

        return {"status": "HANDOFF_SUCCESSFUL", "message_id": msg.id, "from": from_agent_id, "to": to_agent_id}

    def pause_workforce(self, workforce_id: str) -> bool:
        wf = self.workforces.get(workforce_id)
        if wf:
            wf["paused"] = True
            wf["state"] = WorkforceLifecycleState.WAITING
            return True
        return False

    def resume_workforce(self, workforce_id: str) -> bool:
        wf = self.workforces.get(workforce_id)
        if wf and not wf["kill_switch_active"]:
            wf["paused"] = False
            wf["state"] = WorkforceLifecycleState.EXECUTING
            return True
        return False

    def terminate_workforce(self, workforce_id: str, reason: str = "COMPLETED") -> bool:
        wf = self.workforces.get(workforce_id)
        if not wf:
            return False
        wf["state"] = WorkforceLifecycleState.DISBANDED if reason == "DISBANDED" else WorkforceLifecycleState.COMPLETED
        for sid in wf["specialist_ids"]:
            spec = self.specialists.get(sid)
            if spec:
                spec.status = SpecialistStatus.COMPLETED
        return True

    def trigger_kill_switch(self, workforce_id: str, reason: str = "EMERGENCY_QUARANTINE") -> bool:
        wf = self.workforces.get(workforce_id)
        if not wf:
            return False
        wf["kill_switch_active"] = True
        wf["state"] = WorkforceLifecycleState.QUARANTINED
        for sid in wf["specialist_ids"]:
            spec = self.specialists.get(sid)
            if spec:
                spec.status = SpecialistStatus.TERMINATED
        return True

    def record_evidence(self, workforce_id: str, evidence: Dict[str, Any]) -> None:
        if workforce_id in self.evidence_records:
            self.evidence_records[workforce_id].append(evidence)

    def collect_results(self, workforce_id: str) -> Dict[str, Any]:
        wf = self.workforces.get(workforce_id, {})
        return {
            "workforce_id": workforce_id,
            "mission_id": wf.get("mission_id"),
            "state": wf.get("state"),
            "tasks": wf.get("tasks", []),
            "results": wf.get("results", {}),
            "evidence_count": len(self.evidence_records.get(workforce_id, [])),
            "messages_count": len(self.messages.get(workforce_id, [])),
            "budget_spent": wf.get("budget", RuntimeBudget()).current_cost_usd,
            "specialists": [
                {
                    "id": sid,
                    "name": self.specialists[sid].name,
                    "role": self.specialists[sid].role,
                    "status": self.specialists[sid].status.value,
                    "current_task": self.specialists[sid].current_task,
                    "capabilities": self.specialists[sid].capabilities,
                }
                for sid in wf.get("specialist_ids", []) if sid in self.specialists
            ]
        }

    def collect_evidence(self, workforce_id: str) -> List[Dict[str, Any]]:
        return self.evidence_records.get(workforce_id, [])
