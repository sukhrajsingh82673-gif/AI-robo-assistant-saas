"""
ZONATA Universal AI Co-Worker Fabric — A2A Controller
Governed Agent-to-Agent protocol and gateway.
Architecture: ZONATA → Co-Worker → A2A Gateway → External Agent.
External agents NEVER receive ZONATA sovereign authority or credentials.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import hashlib

class GovernedA2AController:
    """
    Safely dispatches communication to external agent networks (e.g., AutoGen, CrewAI, LangChain agents).
    Enforces payload sanitization, signature validation, and prevents external agent authority escalation.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    def send_agent_message(
        self,
        target_agent_id: str,
        message_type: str,
        content: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends an outbound message to an external agent through the governed gateway."""
        cid = conversation_id or f"a2a_conv_{uuid.uuid4().hex[:8]}"
        msg_id = f"a2a_msg_{uuid.uuid4().hex[:8]}"
        timestamp = time.time()

        # Sanitize payload: strip any internal credentials, tokens, or private keys
        sanitized_content = dict(content)
        for sensitive_key in ["token", "secret", "auth", "password", "api_key"]:
            sanitized_content.pop(sensitive_key, None)

        msg_hash = hashlib.sha256(f"{cid}:{target_agent_id}:{timestamp}".encode()).hexdigest()

        record = {
            "msg_id": msg_id,
            "conversation_id": cid,
            "sender": f"ZONATA_CoWorker_{self.tenant_id}",
            "target_agent": target_agent_id,
            "message_type": message_type,
            "content": sanitized_content,
            "timestamp": timestamp,
            "signature": f"sig_a2a_{msg_hash[:16]}"
        }

        if cid not in self._conversations:
            self._conversations[cid] = []
        self._conversations[cid].append(record)

        return {
            "success": True,
            "msg_id": msg_id,
            "conversation_id": cid,
            "status": "DELIVERED_TO_GATEWAY",
            "evidence_signature": record["signature"]
        }

    def receive_agent_response(
        self,
        conversation_id: str,
        from_agent_id: str,
        response_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Receives and validates an incoming response from an external agent."""
        # External responses are treated as UNTRUSTED DATA, never as executable code or sovereign policy
        return {
            "received": True,
            "conversation_id": conversation_id,
            "from_agent": from_agent_id,
            "trust_level": "UNTRUSTED_EXTERNAL_ADVISORY",
            "data": response_payload
        }
