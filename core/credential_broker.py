"""
RoboAssistant Company OS 2.0 — Secret-Isolated Credential Broker
Issues opaque credential handles to AI workers. Invariant: Raw passwords and
API keys are never exposed in prompts, logs, or agent messages.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import hashlib
from .db import db
from .secrets import SecretManager

class CredentialStatus:
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    WAITING_FOR_OWNER = "WAITING_FOR_OWNER"

class CredentialBroker:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"
        self.secret_mgr = SecretManager()
        self._ensure_context_exists()

    def _ensure_context_exists(self):
        with db.get_connection() as conn:
            t = conn.execute("SELECT tenant_id FROM tenants WHERE tenant_id = ?", (self.tenant_id,)).fetchone()
            if not t:
                conn.execute(
                    "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (self.tenant_id, "Cred Tenant", "ENTERPRISE", "ACTIVE", time.time())
                )
            c = conn.execute("SELECT company_id FROM companies WHERE company_id = ?", (self.company_id,)).fetchone()
            if not c:
                conn.execute(
                    """
                    INSERT INTO companies (
                        company_id, tenant_id, name, industry, company_type, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (self.company_id, self.tenant_id, "Security Entity", "Operations", "NEW", "OPERATIONAL", time.time())
                )
            conn.commit()

    def register_credential(
        self,
        service_name: str,
        account_label: str,
        secret_value: str,
        auth_type: str = "PASSWORD",
        mfa_required: bool = False
    ) -> str:
        """
        Stores the secret securely in the vault and returns an opaque handle_id.
        The AI employee only ever sees and uses this handle_id.
        """
        handle_id = f"cred_{service_name.lower()}_{uuid.uuid4().hex[:6]}"
        # Store secret in isolated vault
        self.secret_mgr.store_secret(self.tenant_id, handle_id, secret_value)

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO credential_handles (
                    handle_id, tenant_id, company_id, service_name, account_label, auth_type, mfa_required, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    handle_id, self.tenant_id, self.company_id, service_name, account_label,
                    auth_type, 1 if mfa_required else 0, CredentialStatus.ACTIVE, time.time()
                )
            )
            conn.commit()

        return handle_id

    def list_handles(self) -> List[Dict[str, Any]]:
        """
        Lists available credential handles. NEVER exposes the underlying secret value.
        """
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT handle_id, company_id, service_name, account_label, auth_type, mfa_required, status, created_at FROM credential_handles WHERE company_id = ?",
                (self.company_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_handle_status(self, handle_id: str) -> Optional[str]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM credential_handles WHERE handle_id = ?",
                (handle_id,)
            ).fetchone()
            return row["status"] if row else None

    def execute_with_vaulted_credential(self, handle_id: str, caller_agent_id: str) -> bool:
        """
        Verifies that the handle is valid and active before granting authorization to an internal adapter.
        """
        status = self.get_handle_status(handle_id)
        if status != CredentialStatus.ACTIVE:
            return False
        return True
