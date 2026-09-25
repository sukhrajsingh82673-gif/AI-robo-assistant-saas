"""
RoboAssistant Company OS 1.0 — Multi-Tenant IAM & Scoped Authorization
Role-Based Access Control (RBAC) and cryptographically signed session tokens.
"""

import hmac
import hashlib
import time
import uuid
import json
from typing import Optional, Dict, Any, List
from .db import db

SECRET_KEY = b"ROBOASSISTANT_INTERNAL_TENANT_HMAC_SECRET_2026"

class UserRole:
    OWNER = "OWNER"
    EXECUTIVE = "EXECUTIVE"
    MANAGER = "MANAGER"
    OBSERVER = "OBSERVER"
    AUDITOR = "AUDITOR"

class TenantManager:
    @staticmethod
    def create_tenant(name: str, plan: str = "ENTERPRISE") -> Dict[str, Any]:
        tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (tenant_id, name, plan, "ACTIVE", now)
            )
            conn.commit()
        return {"tenant_id": tenant_id, "name": name, "plan": plan, "status": "ACTIVE"}

    @staticmethod
    def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def list_tenants() -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM tenants ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

class UserManager:
    @staticmethod
    def create_user(tenant_id: str, email: str, name: str, role: str = UserRole.OWNER) -> Dict[str, Any]:
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, tenant_id, email, name, role, "ACTIVE", now)
            )
            conn.commit()
        return {"user_id": user_id, "tenant_id": tenant_id, "email": email, "name": name, "role": role}

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def generate_token(user: Dict[str, Any]) -> str:
        payload = {
            "user_id": user["user_id"],
            "tenant_id": user["tenant_id"],
            "role": user["role"],
            "exp": time.time() + 86400 * 7 # 7 days
        }
        payload_str = json.dumps(payload, sort_keys=True)
        sig = hmac.new(SECRET_KEY, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_str}.{sig}"

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.rsplit(".", 1)
            if len(parts) != 2:
                return None
            payload_str, sig = parts
            expected_sig = hmac.new(SECRET_KEY, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            payload = json.loads(payload_str)
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None

class AuthorizationEnforcer:
    @staticmethod
    def require_tenant(token_payload: Optional[Dict[str, Any]], requested_tenant_id: str) -> bool:
        """Strict tenant isolation invariant enforcement."""
        if not token_payload:
            return False
        return token_payload.get("tenant_id") == requested_tenant_id

    @staticmethod
    def can_approve(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.EXECUTIVE]

    @staticmethod
    def can_mutate_governance(role: str) -> bool:
        return role == UserRole.OWNER

    @staticmethod
    def can_view_reports(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.EXECUTIVE, UserRole.MANAGER, UserRole.AUDITOR]
