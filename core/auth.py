"""
RoboAssistant Company OS 1.0 — Multi-Tenant IAM, Cryptographic Tokens & Scoped RBAC
Production Hardened: Enforces 'UNAUTHENTICATED REQUEST != TENANT IDENTITY'.
Strict cryptographic verification, anti-spoofing tenant isolation, and granular RBAC.
"""

import hmac
import hashlib
import time
import uuid
import json
import os
import threading
from typing import Optional, Dict, Any, List, Set, Tuple
from .db import db

def get_auth_secret_key() -> bytes:
    """
    Resolves the sovereign HMAC signing key with strict production safety:
    1. Checks environment variable ZONATA_AUTH_SECRET
    2. Checks SecretManager for managed vault key
    3. In production mode (APP_ENV=production or ZONATA_STRICT_AUTH=1), refuses hardcoded default and raises RuntimeError.
    4. In development mode, falls back to internal dev secret.
    """
    from .secrets import SecretManager
    secret = os.environ.get("ZONATA_AUTH_SECRET")
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
    is_strict = (app_env in ("production", "prod", "staging")) or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1") or (os.environ.get("ZONATA_REQUIRE_EXPLICIT_SECRET", "0") == "1")
    if secret:
        if is_strict and len(secret.strip()) < 32:
            raise RuntimeError("Production Sovereign Security Violation: ZONATA_AUTH_SECRET must be at least 32 characters with high entropy in production mode.")
        return secret.encode("utf-8")
    managed_key = SecretManager.get_secret("sec_sovereign_auth_key")
    if managed_key:
        return managed_key.encode("utf-8")
    if is_strict:
        raise RuntimeError("Production Sovereign Security Violation: ZONATA_AUTH_SECRET environment variable is required in production mode. Hardcoded fallback prohibited.")
    return b"ROBOASSISTANT_INTERNAL_TENANT_HMAC_SECRET_2026"

def get_verification_keys() -> List[bytes]:
    """
    Returns the primary signing key and any previous rotated keys to support zero-downtime key rotation.
    """
    keys = [get_auth_secret_key()]
    prev_secret = os.environ.get("ZONATA_PREVIOUS_AUTH_SECRET")
    if prev_secret:
        keys.append(prev_secret.encode("utf-8"))
    from .secrets import SecretManager
    prev_managed = SecretManager.get_secret("sec_sovereign_previous_auth_key")
    if prev_managed:
        keys.append(prev_managed.encode("utf-8"))
    return keys

def __getattr__(name: str):
    if name == "SECRET_KEY":
        return get_auth_secret_key()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

class UserRole:
    OWNER = "OWNER"
    EXECUTIVE = "EXECUTIVE"
    MANAGER = "MANAGER"
    OPERATOR = "OPERATOR"
    OBSERVER = "OBSERVER"
    AUDITOR = "AUDITOR"
    SYSTEM_AGENT = "SYSTEM_AGENT"
    GLOBAL_ADMIN = "GLOBAL_ADMIN"

class AuthExceptions:
    class AuthenticationError(Exception):
        """Raised when a request lacks valid authentication."""
        pass

    class TenantIsolationViolation(Exception):
        """Raised when an identity attempts to access cross-tenant resources."""
        pass

    class AuthorizationError(Exception):
        """Raised when an authenticated identity lacks sufficient role or permission."""
        pass

class TokenRevocationStore:
    _revoked_token_ids: Set[str] = set()

    @classmethod
    def revoke(cls, token_id: str):
        cls._revoked_token_ids.add(token_id)
        try:
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO auth_revoked_tokens (token_id, revoked_at) VALUES (?, ?)",
                    (token_id, time.time())
                )
                conn.commit()
        except Exception:
            pass  # In-memory revocation remains active even if table not yet migrated

    @classmethod
    def is_revoked(cls, token_id: str) -> bool:
        if token_id in cls._revoked_token_ids:
            return True
        try:
            with db.get_connection() as conn:
                row = conn.execute("SELECT token_id FROM auth_revoked_tokens WHERE token_id = ?", (token_id,)).fetchone()
                if row:
                    cls._revoked_token_ids.add(token_id)
                    return True
        except Exception:
            pass
        return False

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

class RateLimiter:
    """Sliding-window rate limiter for sensitive authentication endpoints."""
    _records: Dict[str, List[float]] = {}
    _lock = threading.Lock()

    @classmethod
    def is_allowed(cls, key: str, max_requests: int = 5, window_seconds: float = 60.0) -> Tuple[bool, int]:
        now = time.time()
        with cls._lock:
            timestamps = cls._records.get(key, [])
            valid_timestamps = [t for t in timestamps if now - t < window_seconds]
            if len(valid_timestamps) >= max_requests:
                cls._records[key] = valid_timestamps
                retry_after = int(window_seconds - (now - valid_timestamps[0])) + 1
                return False, max(1, retry_after)
            valid_timestamps.append(now)
            cls._records[key] = valid_timestamps
            return True, 0


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Computes PBKDF2-HMAC-SHA256 hash with unique cryptographic salt."""
    import secrets
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hashed, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time verification of supplied password against PBKDF2 digest."""
    actual_hash, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(actual_hash, expected_hash)


class UserManager:
    @staticmethod
    def create_user(tenant_id: str, email: str, name: str, role: str = UserRole.OWNER, company_id: Optional[str] = None) -> Dict[str, Any]:
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, tenant_id, email, name, role, "ACTIVE", now)
            )
            conn.commit()
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "company_id": company_id or "comp_primary",
            "email": email,
            "name": name,
            "role": role
        }

    @staticmethod
    def create_user_with_credentials(
        tenant_id: str,
        email: str,
        name: str,
        password: str,
        role: str = UserRole.OWNER,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        now = time.time()
        pw_hash, salt = hash_password(password)
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, tenant_id, email, name, role, "ACTIVE", now)
            )
            conn.execute(
                "INSERT INTO auth_credentials (user_id, password_hash, salt, failed_attempts, locked_until, created_at, updated_at) VALUES (?, ?, ?, 0, 0, ?, ?)",
                (user_id, pw_hash, salt, now, now)
            )
            conn.commit()
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "company_id": company_id or "comp_primary",
            "email": email,
            "name": name,
            "role": role
        }

    @staticmethod
    def authenticate_user(
        email: str,
        password: str,
        tenant_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        now = time.time()
        with db.get_connection() as conn:
            if tenant_id:
                user_row = conn.execute(
                    "SELECT * FROM users WHERE email = ? AND tenant_id = ? AND status = 'ACTIVE'",
                    (email, tenant_id)
                ).fetchone()
            else:
                user_row = conn.execute(
                    "SELECT * FROM users WHERE email = ? AND status = 'ACTIVE'",
                    (email,)
                ).fetchone()

            if not user_row:
                return False, None, "Invalid email or password"

            user_dict = dict(user_row)
            uid = user_dict["user_id"]

            cred_row = conn.execute(
                "SELECT * FROM auth_credentials WHERE user_id = ?",
                (uid,)
            ).fetchone()

            if not cred_row:
                # No credential record in auth_credentials
                return False, None, "Credentials not enrolled for this account"

            cred = dict(cred_row)
            if cred.get("locked_until", 0) > now:
                remaining = int(cred["locked_until"] - now)
                return False, None, f"Account temporarily locked due to failed attempts. Try again in {remaining}s."

            is_valid = verify_password(password, cred["salt"], cred["password_hash"])
            if is_valid:
                conn.execute(
                    "UPDATE auth_credentials SET failed_attempts = 0, locked_until = 0, updated_at = ? WHERE user_id = ?",
                    (now, uid)
                )
                conn.commit()
                return True, user_dict, "OK"
            else:
                fails = cred.get("failed_attempts", 0) + 1
                locked_until = now + 600 if fails >= 5 else 0
                conn.execute(
                    "UPDATE auth_credentials SET failed_attempts = ?, locked_until = ?, updated_at = ? WHERE user_id = ?",
                    (fails, locked_until, now, uid)
                )
                conn.commit()
                return False, None, "Invalid email or password"

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def generate_token(user: Dict[str, Any], expires_in_seconds: int = 86400 * 7) -> str:
        token_id = f"tok_{uuid.uuid4().hex[:12]}"
        now = time.time()
        payload = {
            "token_id": token_id,
            "user_id": user.get("user_id", f"usr_{uuid.uuid4().hex[:6]}"),
            "tenant_id": user["tenant_id"],
            "company_id": user.get("company_id", "comp_primary"),
            "role": user.get("role", UserRole.OPERATOR),
            "permissions": user.get("permissions", []),
            "iat": now,
            "exp": now + expires_in_seconds
        }
        payload_str = json.dumps(payload, sort_keys=True)
        key = get_auth_secret_key()
        sig = hmac.new(key, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_str}.{sig}"

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.rsplit(".", 1)
            if len(parts) != 2:
                return None
            payload_str, sig = parts
            v_keys = get_verification_keys()
            valid = False
            for k in v_keys:
                expected_sig = hmac.new(k, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig, expected_sig):
                    valid = True
                    break
            if not valid:
                return None
            payload = json.loads(payload_str)

            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None

            # Check revocation
            if TokenRevocationStore.is_revoked(payload.get("token_id", "")):
                return None

            return payload
        except Exception:
            return None

    @staticmethod
    def create_session_token(tenant_id: str, user_id: str = "admin", role: str = UserRole.OWNER, company_id: str = "comp_primary") -> str:
        user = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "role": role,
            "permissions": ["*"]
        }
        return UserManager.generate_token(user)

    @staticmethod
    def get_or_create_dev_token(tenant_id: str = "tnt_primary", company_id: str = "comp_primary") -> str:
        """Issues an authenticated developer token for local/dev workloads."""
        user = {
            "user_id": "usr_dev_bootstrap",
            "tenant_id": tenant_id,
            "company_id": company_id,
            "role": UserRole.OWNER,
            "permissions": ["*"]
        }
        return UserManager.generate_token(user, expires_in_seconds=86400 * 30)

token_manager = UserManager

class AuthorizationEnforcer:
    @staticmethod
    def require_tenant(token_payload: Optional[Dict[str, Any]], requested_tenant_id: str) -> bool:
        """
        Constitutional Invariant: UNAUTHENTICATED REQUEST != TENANT IDENTITY.
        Blocks cross-tenant access and header spoofing.
        """
        if not token_payload:
            return False
        # Global admin can inspect all tenants
        if token_payload.get("role") == UserRole.GLOBAL_ADMIN:
            return True
        return token_payload.get("tenant_id") == requested_tenant_id

    @staticmethod
    def can_approve(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.EXECUTIVE, UserRole.GLOBAL_ADMIN]

    @staticmethod
    def can_mutate_governance(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.GLOBAL_ADMIN]

    @staticmethod
    def can_view_reports(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.EXECUTIVE, UserRole.MANAGER, UserRole.AUDITOR, UserRole.GLOBAL_ADMIN]

    @staticmethod
    def can_trip_killswitch(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.EXECUTIVE, UserRole.AUDITOR, UserRole.GLOBAL_ADMIN]

    @staticmethod
    def can_manage_credentials(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.GLOBAL_ADMIN]

    @staticmethod
    def can_execute_missions(role: str) -> bool:
        return role in [UserRole.OWNER, UserRole.EXECUTIVE, UserRole.MANAGER, UserRole.OPERATOR, UserRole.SYSTEM_AGENT, UserRole.GLOBAL_ADMIN]

    @staticmethod
    def enforce_tenant_boundary(token_payload: Optional[Dict[str, Any]], requested_tenant_id: str):
        if not AuthorizationEnforcer.require_tenant(token_payload, requested_tenant_id):
            raise AuthExceptions.TenantIsolationViolation(f"Cross-tenant access prohibited for tenant '{requested_tenant_id}'")

TenantContext = AuthorizationEnforcer
