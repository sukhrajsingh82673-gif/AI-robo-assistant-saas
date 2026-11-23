"""ZONATA Sovereign Core — Google ADK Session State Service.

Implements OpenCode Step 4F (Rule 36 Payload Confidentiality & Multi-Tenant RLS):
Provides multi-tenant session state persistence for hierarchical agent teams.
Encrypts session message histories with per-tenant KMS keys to guarantee
zero plaintext sensitive data exposure in database rows.
"""

from __future__ import annotations
import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from core.ports.base import PortStatus
from core.ports.kms import resolve_kms_provider, KeyManagementPort

logger = logging.getLogger(__name__)


class SessionAccessDenied(PermissionError):
    """Raised when cross-tenant session access is attempted."""
    pass


class ADKSession:
    def __init__(
        self,
        session_id: str,
        tenant_id: str,
        company_id: str,
        topology_version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.topology_version = topology_version
        self.messages: List[Dict[str, Any]] = []
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.is_active = True

    def add_message(self, role: str, content: str, agent_id: str, is_untrusted: bool = False):
        self.messages.append({
            "role": role,
            "content": content,
            "agent_id": agent_id,
            "is_untrusted": is_untrusted,
            "timestamp": time.time(),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "topology_version": self.topology_version,
            "messages": self.messages,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


class ZonataADKSessionService:
    """Manages multi-tenant encrypted sessions for ADK hierarchical teams."""

    def __init__(self, kms: Optional[KeyManagementPort] = None):
        self._kms = kms or resolve_kms_provider()
        # In-memory session store mapping session_id -> (encrypted_blob, tenant_id, company_id)
        self._encrypted_sessions: Dict[str, Tuple[bytes, str, str]] = {}

    def create_session(
        self,
        session_id: str,
        tenant_id: str,
        company_id: str,
        topology_version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ADKSession:
        session = ADKSession(
            session_id=session_id,
            tenant_id=tenant_id,
            company_id=company_id,
            topology_version=topology_version,
            metadata=metadata,
        )
        self.save_session(session)
        return session

    def save_session(self, session: ADKSession) -> None:
        """Encrypts session payload via KMS envelope encryption and persists (Rule 36)."""
        session_json = json.dumps(session.to_dict()).encode("utf-8")
        probe = self._kms.probe()
        if probe.status not in (PortStatus.OK, PortStatus.SANDBOX):
            raise RuntimeError("Rule 36 Violation: KMS envelope encryption is not operational")

        kms_res, ciphertext = self._kms.encrypt(
            plaintext=session_json,
            context={"tenant_id": session.tenant_id, "company_id": session.company_id},
        )
        if kms_res.status not in (PortStatus.OK, PortStatus.SANDBOX):
            raise RuntimeError("KMS encryption failed")

        self._encrypted_sessions[session.session_id] = (
            ciphertext,
            session.tenant_id,
            session.company_id,
        )

    def get_session(
        self,
        session_id: str,
        tenant_id: str,
        company_id: str,
    ) -> Optional[ADKSession]:
        """Retrieves and decrypts session state with strict multi-tenant validation."""
        if session_id not in self._encrypted_sessions:
            return None

        ciphertext, owner_tenant, owner_company = self._encrypted_sessions[session_id]
        if owner_tenant != tenant_id or owner_company != company_id:
            logger.warning(f"Cross-tenant access attempt to session {session_id} by tenant {tenant_id}")
            return None

        kms_res, plaintext = self._kms.decrypt(
            ciphertext,
            context={"tenant_id": tenant_id, "company_id": company_id},
        )
        if kms_res.status not in (PortStatus.OK, PortStatus.SANDBOX):
            raise RuntimeError("KMS decryption failed")

        data = json.loads(plaintext.decode("utf-8"))
        session = ADKSession(
            session_id=data["session_id"],
            tenant_id=data["tenant_id"],
            company_id=data["company_id"],
            topology_version=data.get("topology_version", "1.0.0"),
            metadata=data.get("metadata", {}),
        )
        session.messages = data.get("messages", [])
        session.created_at = data.get("created_at", time.time())
        session.is_active = data.get("is_active", True)
        return session


adk_session_service = ZonataADKSessionService()
