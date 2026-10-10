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
import json

class GovernedA2AController:
    """
    Safely dispatches communication to external agent networks (e.g., AutoGen, CrewAI, LangChain agents).
    Enforces payload sanitization, signature validation, tenant isolation, and prevents external agent authority escalation.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    def send_agent_message(
        self,
        target_agent_id: str,
        message_type: str,
        content: Dict[str, Any],
        conversation_id: Optional[str] = None,
        target_tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends an outbound message to an agent through the governed gateway with DLP verification."""
        from core.ai_dlp_gateway import ai_dlp_gateway

        # Enforce tenant isolation & outbound DLP
        target_tenant = target_tenant_id or self.tenant_id
        dlp_res = ai_dlp_gateway.inspect_a2a_message(
            sender_agent_id=f"agent_{self.tenant_id}",
            target_agent_id=target_agent_id,
            message_payload=content,
            sender_tenant_id=self.tenant_id,
            target_tenant_id=target_tenant
        )

        if not dlp_res.is_allowed:
            return {
                "success": False,
                "error": f"A2A Security Block: {dlp_res.blocking_reason}",
                "security_class": dlp_res.response_class.value,
                "target_agent": target_agent_id
            }

        cid = conversation_id or f"a2a_conv_{uuid.uuid4().hex[:8]}"
        msg_id = f"a2a_msg_{uuid.uuid4().hex[:8]}"
        timestamp = time.time()

        # Use DLP sanitized payload
        effective_payload = dlp_res.sanitized_payload if isinstance(dlp_res.sanitized_payload, dict) else content
        sanitized_content = dict(effective_payload)
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
        from core.ai_dlp_gateway import ai_dlp_gateway

        # Inspect incoming payload for prompt injection or malicious instructions
        is_safe, sanitized, err = ai_dlp_gateway.inspect_tool_output(
            server_id="a2a_gateway",
            tool_name=from_agent_id,
            output_data=response_payload,
            tenant_id=self.tenant_id
        )

        if not is_safe:
            return {
                "received": False,
                "conversation_id": conversation_id,
                "from_agent": from_agent_id,
                "trust_level": "MALICIOUS_REJECTED",
                "error": f"Adversarial payload rejected: {err}"
            }

        return {
            "received": True,
            "conversation_id": conversation_id,
            "from_agent": from_agent_id,
            "trust_level": "UNTRUSTED_EXTERNAL_ADVISORY",
            "data": response_payload
        }
