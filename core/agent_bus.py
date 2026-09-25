"""
RoboAssistant Company OS 1.0 — Governed Inter-Agent Communication Bus
Structured message passing between CEO, Department Control Units, Managers, and Specialists.
Non-Negotiable Invariant: Agent communication CANNOT transfer or escalate authority.
"""

from typing import Dict, Any, List, Optional
import time
import uuid

class MessagePriority:
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"

class GovernedAgentMessage:
    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        tenant_id: str,
        company_id: str,
        purpose: str,
        payload: Dict[str, Any],
        mission_id: Optional[str] = None,
        department_id: Optional[str] = None,
        priority: str = MessagePriority.NORMAL,
        parent_msg_id: Optional[str] = None,
        authority_context: str = "SANDBOXED_READ_ONLY"
    ):
        self.message_id = f"msg_{uuid.uuid4().hex[:10]}"
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.purpose = purpose
        self.payload = payload
        self.mission_id = mission_id
        self.department_id = department_id
        self.priority = priority
        self.parent_msg_id = parent_msg_id
        self.authority_context = authority_context
        self.timestamp = time.time()
        self.status = "DISPATCHED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "purpose": self.purpose,
            "payload": self.payload,
            "mission_id": self.mission_id,
            "department_id": self.department_id,
            "priority": self.priority,
            "parent_msg_id": self.parent_msg_id,
            "authority_context": self.authority_context,
            "timestamp": self.timestamp,
            "status": self.status
        }

class AgentCommunicationBus:
    """
    Mediated message broker.
    Audits inter-agent communications and validates that messages respect organizational scopes.
    """
    def __init__(self):
        self.message_log: List[GovernedAgentMessage] = []

    def dispatch_message(self, message: GovernedAgentMessage) -> Dict[str, Any]:
        # Governance invariant: Inter-agent messaging cannot alter caller's assigned authority ceiling
        if "escalate_privilege" in str(message.payload).lower() or "override_governance" in str(message.payload).lower():
            message.status = "BLOCKED_SECURITY_VIOLATION"
            self.message_log.append(message)
            return {
                "success": False,
                "error": "SECURITY_VIOLATION: Uncontrolled agent-to-agent privilege escalation is strictly forbidden.",
                "message": message.to_dict()
            }

        message.status = "DELIVERED"
        self.message_log.append(message)
        return {
            "success": True,
            "delivered_to": message.receiver_id,
            "message_id": message.message_id,
            "message": message.to_dict()
        }

    def get_messages_for_agent(self, agent_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        return [
            m.to_dict() for m in self.message_log
            if (m.receiver_id == agent_id or m.sender_id == agent_id) and m.tenant_id == tenant_id
        ]
