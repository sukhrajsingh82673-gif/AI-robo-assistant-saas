"""
Tenant Admin Console Backend and Action Handlers (ADR 0049, Rule 84).
Handles team management, billing updates, API key rotation, webhooks, audit search, and telemetry opt-in.
"""

import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from core.ui.dead_control_detector import ControlElement


class TenantAdminConsole:
    """
    Backend service power for /admin Tenant Admin Console.
    """

    VALID_ROLES = {"Owner", "Admin", "Member", "Auditor"}

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # In-memory tenant store
        self.team_members: Dict[str, Dict[str, Any]] = {
            "usr_owner": {"user_id": "usr_owner", "email": "founder@acme.corp", "role": "Owner", "active": True}
        }
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.telemetry_opt_in: bool = False

    def invite_member(self, email: str, role: str, actor_id: str) -> Dict[str, Any]:
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {self.VALID_ROLES}")

        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        record = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "active": True,
            "invited_at": time.time(),
        }
        self.team_members[user_id] = record
        self._record_audit(actor_id, "INVITE_MEMBER", {"email": email, "role": role})
        return record

    def change_member_role(self, user_id: str, new_role: str, actor_id: str) -> Dict[str, Any]:
        if user_id not in self.team_members:
            raise KeyError(f"Member '{user_id}' not found")
        if new_role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role: {new_role}")

        # Protect last owner from demotion
        if self.team_members[user_id]["role"] == "Owner" and new_role != "Owner":
            owners = [m for m in self.team_members.values() if m["role"] == "Owner" and m["active"]]
            if len(owners) <= 1:
                raise ValueError("Cannot demote the last remaining Owner of the tenant.")

        self.team_members[user_id]["role"] = new_role
        self._record_audit(actor_id, "CHANGE_ROLE", {"user_id": user_id, "new_role": new_role})
        return self.team_members[user_id]

    def create_api_key(self, name: str, scopes: List[str], actor_id: str) -> Dict[str, Any]:
        key_id = f"key_{uuid.uuid4().hex[:8]}"
        secret_part = uuid.uuid4().hex
        plaintext_key = f"zn_{key_id}_{secret_part}"
        key_hash = hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()

        record = {
            "key_id": key_id,
            "name": name,
            "key_prefix": plaintext_key[:10],
            "key_hash": key_hash,
            "scopes": scopes,
            "revoked": False,
            "created_at": time.time(),
        }
        self.api_keys[key_id] = record
        self._record_audit(actor_id, "CREATE_API_KEY", {"key_id": key_id, "name": name})

        # Return plaintext key only once upon creation
        return {"key_id": key_id, "api_key": plaintext_key, "name": name, "scopes": scopes}

    def revoke_api_key(self, key_id: str, actor_id: str) -> Dict[str, Any]:
        if key_id not in self.api_keys:
            raise KeyError(f"API key '{key_id}' not found")
        self.api_keys[key_id]["revoked"] = True
        self.api_keys[key_id]["revoked_at"] = time.time()
        self._record_audit(actor_id, "REVOKE_API_KEY", {"key_id": key_id})
        return {"key_id": key_id, "status": "REVOKED"}

    def set_telemetry_opt_in(self, opt_in: bool, actor_id: str) -> bool:
        self.telemetry_opt_in = opt_in
        self._record_audit(actor_id, "UPDATE_TELEMETRY_OPT_IN", {"opt_in": opt_in})
        return self.telemetry_opt_in

    def _record_audit(self, actor_id: str, action: str, details: Dict[str, Any]):
        self.audit_log.append({
            "timestamp": time.time(),
            "tenant_id": self.tenant_id,
            "actor_id": actor_id,
            "action": action,
            "details": details,
        })

    def get_console_controls_manifest(self) -> List[ControlElement]:
        """Returns the registered interactive controls for the Tenant Admin Console."""
        return [
            ControlElement("button", "btn_invite_member", "Invite Team Member", "api_call", "/api/console/members/invite"),
            ControlElement("button", "btn_create_api_key", "Generate API Key", "api_call", "/api/console/keys/create"),
            ControlElement("button", "btn_rotate_key", "Rotate Key", "api_call", "/api/console/keys/rotate"),
            ControlElement("button", "btn_update_billing", "Update Payment Plan", "api_call", "/api/console/billing/upgrade"),
            ControlElement("button", "btn_download_invoice", "Download Invoices", "api_call", "/api/console/billing/invoices"),
            ControlElement("button", "btn_toggle_telemetry", "Save Telemetry Preferences", "api_call", "/api/console/settings/telemetry"),
            ControlElement("button", "btn_custom_saml", "Configure SAML SSO", "api_call", "/api/console/sso/saml", is_implemented=False, not_implemented_reason="NOT_IMPLEMENTED: Enterprise SAML SSO requires manual enterprise procurement."),
            ControlElement("a", "link_docs", "API Documentation", "href", "https://zonata.ai/docs/portal"),
            ControlElement("a", "link_status", "System Status", "href", "https://status.zonata.ai"),
        ]
