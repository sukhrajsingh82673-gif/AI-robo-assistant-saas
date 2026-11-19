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
import random
import unicodedata
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
    secret = (
        os.environ.get("ZONATA_AUTH_SECRET")
        or os.environ.get("JWT_SECRET")
        or os.environ.get("SESSION_SECRET")
    )
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

def compute_key_fingerprint(key: bytes) -> str:
    """
    Computes a deterministic, non-reversible SHA-256 cryptographic fingerprint of a signing key.
    Enables safe revocation auditing and key tracking without ever exposing raw secret material in logs or revocation lists.
    """
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hashlib.sha256(key).hexdigest()

def get_verification_keys() -> List[bytes]:
    """
    Returns the primary signing key and any active previous rotated keys to support zero-downtime key rotation.
    Enforces expiration window and emergency key fingerprint revocation list.
    """
    primary = get_auth_secret_key()
    keys = [primary]

    # Collect revoked key fingerprints (never raw secrets)
    revoked_fps = set()
    for env_var in ("ZONATA_REVOKED_KEY_FINGERPRINTS", "ZONATA_REVOKED_AUTH_SECRETS"):
        val = os.environ.get(env_var, "")
        for item in val.split(","):
            item = item.strip()
            if item:
                revoked_fps.add(item)
                # If an operator passed a raw secret string, fingerprint it so it matches safely
                revoked_fps.add(compute_key_fingerprint(item.encode("utf-8")))

    # Check rotation window expiry for previous key
    now = time.time()
    rotation_expires_at = None
    exp_str = os.environ.get("ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT")
    if exp_str:
        try:
            rotation_expires_at = float(exp_str)
        except ValueError:
            rotation_expires_at = None

    is_window_valid = (rotation_expires_at is None) or (now <= rotation_expires_at)

    if is_window_valid and (os.environ.get("ZONATA_EMERGENCY_RETIRE_PREVIOUS_KEY", "0") != "1"):
        prev_secret = os.environ.get("ZONATA_PREVIOUS_AUTH_SECRET")
        if prev_secret:
            prev_bytes = prev_secret.encode("utf-8")
            prev_fp = compute_key_fingerprint(prev_bytes)
            if prev_fp not in revoked_fps and prev_bytes != primary:
                keys.append(prev_bytes)
        from .secrets import SecretManager
        prev_managed = SecretManager.get_secret("sec_sovereign_previous_auth_key")
        if prev_managed:
            prev_m_bytes = prev_managed.encode("utf-8")
            prev_m_fp = compute_key_fingerprint(prev_m_bytes)
            if prev_m_fp not in revoked_fps and prev_m_bytes != primary and prev_m_bytes not in keys:
                keys.append(prev_m_bytes)
    return keys

def emergency_retire_previous_secret(secret_or_fingerprint: Optional[str] = None):
    """
    Emergency procedure: Immediately retires and revokes previous signing secret,
    causing all sessions signed with that key to fail verification immediately across all nodes.
    Stores the cryptographic fingerprint rather than raw secret material.
    """
    os.environ["ZONATA_EMERGENCY_RETIRE_PREVIOUS_KEY"] = "1"
    if secret_or_fingerprint:
        # Determine fingerprint
        fp = secret_or_fingerprint
        if len(secret_or_fingerprint) != 64 or not all(c in "0123456789abcdefABCDEF" for c in secret_or_fingerprint):
            fp = compute_key_fingerprint(secret_or_fingerprint.encode("utf-8"))
        existing = os.environ.get("ZONATA_REVOKED_KEY_FINGERPRINTS", "")
        updated = f"{existing},{fp}".strip(",")
        os.environ["ZONATA_REVOKED_KEY_FINGERPRINTS"] = updated
        # Also maintain ZONATA_REVOKED_AUTH_SECRETS with fingerprint for backward compatibility
        existing_rev = os.environ.get("ZONATA_REVOKED_AUTH_SECRETS", "")
        os.environ["ZONATA_REVOKED_AUTH_SECRETS"] = f"{existing_rev},{fp}".strip(",")
    os.environ.pop("ZONATA_PREVIOUS_AUTH_SECRET", None)

def generate_secure_auth_secret(num_bytes: int = 32) -> str:
    """
    Generates a cryptographically secure random authentication secret using CSPRNG.
    Default 32 bytes yields 256 bits of true cryptographic entropy.
    """
    import secrets
    return secrets.token_hex(num_bytes)

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
                    "INSERT INTO auth_revoked_tokens (token_id, revoked_at) VALUES (?, ?) ON CONFLICT (token_id) DO UPDATE SET revoked_at = EXCLUDED.revoked_at",
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
    """Sliding-window rate limiter for sensitive authentication endpoints supporting distributed instances."""
    _records: Dict[str, List[float]] = {}
    _lock = threading.Lock()

    @classmethod
    def is_allowed(cls, key: str, max_requests: int = 5, window_seconds: float = 60.0) -> Tuple[bool, int]:
        now = time.time()
        # Attempt database-backed distributed sliding window across cluster instances with write-lock serialization
        try:
            with db.get_connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                except Exception:
                    pass  # Postgres or connection wrapper manages transactions via __enter__

                # 1. Scoped pruning for THIS rate_key only using idx_auth_rate_limits_key (rate_key, attempt_timestamp)
                conn.execute(
                    "DELETE FROM auth_rate_limits WHERE rate_key = ? AND attempt_timestamp < ?",
                    (key, now - window_seconds)
                )
                rows = conn.execute(
                    "SELECT attempt_timestamp FROM auth_rate_limits WHERE rate_key = ? AND attempt_timestamp >= ? ORDER BY attempt_timestamp ASC",
                    (key, now - window_seconds)
                ).fetchall()
                if len(rows) >= max_requests:
                    oldest = rows[0][0] if isinstance(rows[0], (tuple, list)) else rows[0]["attempt_timestamp"]
                    retry_after = int(window_seconds - (now - oldest)) + 1
                    conn.commit()
                    return False, max(1, retry_after)
                conn.execute(
                    "INSERT INTO auth_rate_limits (rate_key, attempt_timestamp) VALUES (?, ?)",
                    (key, now)
                )
                # 2. Probabilistic background cleanup (1 in 100 requests) to purge abandoned keys without table contention
                if random.random() < 0.01:
                    conn.execute(
                        "DELETE FROM auth_rate_limits WHERE attempt_timestamp < ?",
                        (now - 3600.0,)
                    )
                conn.commit()
                return True, 0
        except Exception:
            # Fallback to local in-memory sliding window if rate_limits table not migrated or DB unreachable
            pass

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

    @classmethod
    def rate_limit_ip_and_account(
        cls,
        ip: str,
        account: Optional[str] = None,
        max_ip_requests: int = 20,
        max_account_requests: int = 5,
        window_seconds: float = 60.0
    ) -> Tuple[bool, int, str]:
        """
        Dual-axis rate limiting evaluating both source IP address and account identifier.
        Returns: (is_allowed: bool, retry_after: int, violation_axis: str)
        """
        ip_key = f"ip:{ip}"
        ip_ok, ip_retry = cls.is_allowed(ip_key, max_requests=max_ip_requests, window_seconds=window_seconds)
        if not ip_ok:
            return False, ip_retry, "IP_RATE_LIMIT_EXCEEDED"
        if account:
            acc_key = f"account:{account.strip().lower()}"
            acc_ok, acc_retry = cls.is_allowed(acc_key, max_requests=max_account_requests, window_seconds=window_seconds)
            if not acc_ok:
                return False, acc_retry, "ACCOUNT_RATE_LIMIT_EXCEEDED"
        return True, 0, ""


DEFAULT_PBKDF2_ITERATIONS = int(os.environ.get("ZONATA_PBKDF2_ITERATIONS") or os.environ.get("PBKDF2_ITERATIONS") or "600000")
if DEFAULT_PBKDF2_ITERATIONS < 10000:
    DEFAULT_PBKDF2_ITERATIONS = 10000
elif DEFAULT_PBKDF2_ITERATIONS > 2000000:
    DEFAULT_PBKDF2_ITERATIONS = 2000000

MAX_PASSWORD_BYTES = 4096

def evaluate_secret_entropy(secret: str) -> Dict[str, Any]:
    """
    Evaluates Shannon entropy and character distribution of a signing secret.
    Distinguishes raw secret length from true cryptographic entropy.
    """
    import math
    from collections import Counter
    if not secret:
        return {"length": 0, "entropy_bits_per_char": 0.0, "total_entropy_bits": 0.0, "unique_chars": 0, "is_high_entropy": False}
    counts = Counter(secret)
    total = len(secret)
    entropy_per_char = -sum((c / total) * math.log2(c / total) for c in counts.values())
    total_entropy = entropy_per_char * total
    unique_chars = len(counts)
    is_high_entropy = (total >= 32) and (entropy_per_char >= 3.0) and (unique_chars >= 10)
    return {
        "length": total,
        "entropy_bits_per_char": round(entropy_per_char, 3),
        "total_entropy_bits": round(total_entropy, 1),
        "unique_chars": unique_chars,
        "is_high_entropy": is_high_entropy
    }


def hash_password(password: str, salt: Optional[str] = None, iterations: Optional[int] = None) -> Tuple[str, str]:
    """
    Computes PBKDF2-HMAC-SHA256 hash with unique cryptographic salt.
    Enforces Unicode NFC normalization and 4096-byte input ceiling to prevent algorithmic DoS.
    Encodes iterations metadata in prefix to support future algorithm and parameter upgrades.
    """
    import secrets
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    norm_password = unicodedata.normalize("NFC", password)
    pw_bytes = norm_password.encode("utf-8")
    if len(pw_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password exceeds maximum supported length ({MAX_PASSWORD_BYTES} bytes)")

    if iterations is None:
        iterations = int(os.environ.get("ZONATA_PBKDF2_ITERATIONS") or os.environ.get("PBKDF2_ITERATIONS") or DEFAULT_PBKDF2_ITERATIONS)
    if iterations < 10000 or iterations > 2000000:
        iterations = DEFAULT_PBKDF2_ITERATIONS
    if not salt:
        salt = secrets.token_hex(16)
    raw_hash = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt.encode("utf-8"), iterations).hex()
    formatted = f"pbkdf2_sha256${iterations}${salt}${raw_hash}"
    return formatted, salt


def verify_password_with_upgrade(password: str, salt: str, expected_hash: str) -> Tuple[bool, bool]:
    """
    Constant-time verification of supplied password against PBKDF2 digest.
    Returns: (is_valid: bool, needs_upgrade: bool)
    Safely rejects malformed encodings without throwing unhandled exceptions.
    Guarantees needs_upgrade is strictly False whenever is_valid is False.
    """
    if not expected_hash or not isinstance(expected_hash, str) or not isinstance(password, str):
        return False, False
    norm_password = unicodedata.normalize("NFC", password)
    pw_bytes = norm_password.encode("utf-8")
    if len(pw_bytes) > MAX_PASSWORD_BYTES:
        return False, False

    current_default_iter = int(os.environ.get("ZONATA_PBKDF2_ITERATIONS") or os.environ.get("PBKDF2_ITERATIONS") or DEFAULT_PBKDF2_ITERATIONS)
    if current_default_iter < 10000 or current_default_iter > 2000000:
        current_default_iter = DEFAULT_PBKDF2_ITERATIONS

    if expected_hash.startswith("pbkdf2_sha256$"):
        parts = expected_hash.split("$")
        if len(parts) == 4:
            _, iter_str, stored_salt, stored_hash = parts
            try:
                iterations = int(iter_str)
                if iterations <= 0 or iterations > 2000000 or not stored_salt or not stored_hash:
                    return False, False
                computed = hashlib.pbkdf2_hmac("sha256", pw_bytes, stored_salt.encode("utf-8"), iterations).hex()
                is_valid = hmac.compare_digest(computed, stored_hash)
                needs_upgrade = is_valid and (iterations < current_default_iter)
                return is_valid, needs_upgrade
            except Exception:
                return False, False
        return False, False

    # Backward compatibility with unformatted raw hex hashes
    for check_iter in [current_default_iter, 100000]:
        try:
            computed = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt.encode("utf-8"), check_iter).hex()
            if hmac.compare_digest(computed, expected_hash):
                return True, True
        except Exception:
            pass
    return False, False


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time verification of supplied password against PBKDF2 digest."""
    is_valid, _ = verify_password_with_upgrade(password, salt, expected_hash)
    return is_valid


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

            is_valid, needs_upgrade = verify_password_with_upgrade(password, cred["salt"], cred["password_hash"])
            if is_valid:
                if needs_upgrade:
                    new_hash, new_salt = hash_password(password)
                    conn.execute(
                        "UPDATE auth_credentials SET password_hash = ?, salt = ?, failed_attempts = 0, locked_until = 0, updated_at = ? WHERE user_id = ? AND password_hash = ?",
                        (new_hash, new_salt, now, uid, cred["password_hash"])
                    )
                else:
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
