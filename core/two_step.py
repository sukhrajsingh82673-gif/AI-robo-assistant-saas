"""Real TOTP two-step verification for ZONATA accounts.

What is real here:
  * RFC 6238 TOTP (HMAC-SHA1, 6 digits, 30-second period, +/- one step);
  * the shared secret is encrypted at rest with AES-GCM using a key derived
    from the deployment's auth secret;
  * replay protection: a step can be used once, and failed attempts lock the
    account for a short window;
  * enrollment is explicit: a pending secret only becomes active after the
    user proves they can generate a code.

What is not here: SMS, WebAuthn/passkeys, recovery codes. Those are separate
providers and are not claimed by this module.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from typing import Any, Dict, Optional, Tuple

from core.auth import get_auth_secret_key
from core.db import db

try:  # pragma: no cover - import guard mirrors core/settings/secrets.py
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # pragma: no cover
    AESGCM = None  # type: ignore

DIGITS = 6
PERIOD = 30
WINDOW = 1
MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 300
ISSUER = "ZONATA"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_two_step (
    user_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'TOTP',
    secret_ciphertext TEXT NOT NULL,
    secret_nonce TEXT NOT NULL,
    key_id TEXT NOT NULL,
    pending INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0,
    last_used_step INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    confirmed_at REAL,
    updated_at REAL NOT NULL
);
"""


class TwoStepError(Exception):
    """A refusal with a stable code the API and UI can explain."""

    def __init__(self, code: str, message: str, status: int = 400, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.detail = detail or {}


def _b32encode(raw: bytes) -> str:
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _b32decode(secret: str) -> bytes:
    value = str(secret or "").strip().upper().replace(" ", "")
    padding = "=" * ((8 - len(value) % 8) % 8)
    return base64.b32decode(value + padding)


def _encryption_key() -> bytes:
    # Separate derived key: rotating the auth secret intentionally invalidates
    # two-step secrets instead of silently reusing the token-signing key.
    return hmac.new(get_auth_secret_key(), b"zonata-totp-storage-v1", hashlib.sha256).digest()


def _key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:12]


def code_at(secret: str, timestamp: Optional[float] = None) -> str:
    """The RFC 6238 code for a timestamp (defaults to now)."""
    at = time.time() if timestamp is None else float(timestamp)
    counter = int(at // PERIOD)
    digest = hmac.new(_b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** DIGITS)).zfill(DIGITS)


def provisioning_uri(email: str, secret: str) -> str:
    from urllib.parse import quote

    label = quote(f"{ISSUER}:{email or 'account'}", safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD}"
    )


def _match(secret: str, code: str, last_used_step: int, at: Optional[float]) -> Tuple[bool, int]:
    candidate = str(code or "").strip().replace(" ", "")
    if not candidate.isdigit() or len(candidate) != DIGITS:
        return False, 0
    now = time.time() if at is None else float(at)
    counter = int(now // PERIOD)
    for delta in (0, -WINDOW, WINDOW):
        step = counter + delta
        if step <= last_used_step:
            continue
        if hmac.compare_digest(code_at(secret, step * PERIOD), candidate):
            return True, step
    return False, 0


class TwoStepService:
    """Database-backed enrollment and verification for one account."""

    def __init__(self, clock=time.time) -> None:
        self._clock = clock
        self._ensure_schema()

    # ------------------------------------------------------------------ schema
    @staticmethod
    def _ensure_schema() -> None:
        with db.get_connection() as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    # ------------------------------------------------------------------- state
    def status(self, user_id: str) -> Dict[str, Any]:
        row = self._row(user_id)
        if not row:
            return {"enabled": False, "pending": False, "method": None, "configured": True}
        return {
            "enabled": not bool(row["pending"]),
            "pending": bool(row["pending"]),
            "method": row["method"],
            "configured": True,
            "confirmed_at": row["confirmed_at"],
        }

    def enrolled(self, user_id: str) -> bool:
        row = self._row(user_id)
        return bool(row and not row["pending"])

    # ------------------------------------------------------------- enrollment
    def begin_enrollment(self, user_id: str, tenant_id: str, email: str) -> Dict[str, Any]:
        row = self._row(user_id)
        if row and not row["pending"]:
            raise TwoStepError(
                "TWO_STEP_ALREADY_ENABLED",
                "Two-step verification is already on for this account",
                status=409,
            )
        secret = _b32encode(os.urandom(20))
        ciphertext, nonce, key_id = self._encrypt(secret)
        now = self._clock()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO user_two_step (user_id, tenant_id, method, secret_ciphertext, secret_nonce, "
                "key_id, pending, failed_attempts, locked_until, last_used_step, created_at, confirmed_at, updated_at) "
                "VALUES (?, ?, 'TOTP', ?, ?, ?, 1, 0, 0, 0, ?, NULL, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET tenant_id=excluded.tenant_id, method='TOTP', "
                "secret_ciphertext=excluded.secret_ciphertext, secret_nonce=excluded.secret_nonce, "
                "key_id=excluded.key_id, pending=1, failed_attempts=0, locked_until=0, "
                "last_used_step=0, confirmed_at=NULL, updated_at=excluded.updated_at",
                (user_id, tenant_id, ciphertext, nonce, key_id, now, now),
            )
            conn.commit()
        return {"secret": secret, "otpauth_uri": provisioning_uri(email, secret), "issuer": ISSUER}

    def confirm_enrollment(self, user_id: str, code: str) -> Dict[str, Any]:
        row = self._row(user_id)
        if not row:
            raise TwoStepError("TWO_STEP_NOT_STARTED", "Start two-step setup first", status=409)
        if not row["pending"]:
            raise TwoStepError("TWO_STEP_ALREADY_ENABLED", "Two-step verification is already on", status=409)
        self._check_lock(row)
        secret = self._decrypt(row)
        ok, step = _match(secret, code, int(row["last_used_step"] or 0), self._clock())
        if not ok:
            self._register_failure(user_id, row)
            raise TwoStepError("INVALID_TWO_STEP_CODE", "That code is not valid. Check the clock on your device.", status=403)
        now = self._clock()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE user_two_step SET pending=0, failed_attempts=0, locked_until=0, "
                "last_used_step=?, confirmed_at=?, updated_at=? WHERE user_id=?",
                (step, now, now, user_id),
            )
            conn.commit()
        return {"enabled": True, "method": "TOTP"}

    def verify_code(self, user_id: str, code: str) -> Tuple[bool, str]:
        row = self._row(user_id)
        if not row or row["pending"]:
            return False, "not_enrolled"
        try:
            self._check_lock(row)
        except TwoStepError as err:
            return False, err.code
        secret = self._decrypt(row)
        ok, step = _match(secret, code, int(row["last_used_step"] or 0), self._clock())
        if not ok:
            self._register_failure(user_id, row)
            return False, "invalid"
        now = self._clock()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE user_two_step SET last_used_step=?, failed_attempts=0, locked_until=0, "
                "updated_at=? WHERE user_id=?",
                (step, now, user_id),
            )
            conn.commit()
        return True, "ok"

    def disable(self, user_id: str) -> None:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM user_two_step WHERE user_id = ?", (user_id,))
            conn.commit()

    # ----------------------------------------------------------------- helpers
    def _row(self, user_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM user_two_step WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def _check_lock(self, row: Dict[str, Any]) -> None:
        locked_until = float(row.get("locked_until") or 0)
        if locked_until > self._clock():
            retry = max(1, int(locked_until - self._clock()))
            raise TwoStepError(
                "TWO_STEP_LOCKED",
                f"Too many incorrect codes. Try again in {retry}s.",
                status=429,
                detail={"retry_after": retry},
            )

    def _register_failure(self, user_id: str, row: Dict[str, Any]) -> None:
        failures = int(row.get("failed_attempts") or 0) + 1
        locked_until = self._clock() + LOCK_SECONDS if failures >= MAX_FAILED_ATTEMPTS else 0
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE user_two_step SET failed_attempts=?, locked_until=?, updated_at=? WHERE user_id=?",
                (failures, locked_until, self._clock(), user_id),
            )
            conn.commit()

    def _encrypt(self, secret: str) -> Tuple[str, str, str]:
        if AESGCM is None:  # pragma: no cover
            raise TwoStepError("TWO_STEP_UNAVAILABLE", "Encryption support is not installed", status=503)
        key = _encryption_key()
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, secret.encode("utf-8"), None)
        return (
            base64.b64encode(ciphertext).decode("ascii"),
            base64.b64encode(nonce).decode("ascii"),
            _key_id(key),
        )

    def _decrypt(self, row: Dict[str, Any]) -> str:
        if AESGCM is None:  # pragma: no cover
            raise TwoStepError("TWO_STEP_UNAVAILABLE", "Encryption support is not installed", status=503)
        key = _encryption_key()
        if row.get("key_id") and row["key_id"] != _key_id(key):
            raise TwoStepError(
                "TWO_STEP_KEY_UNAVAILABLE",
                "The key that protects this two-step secret is not available. Sign in and enroll again.",
                status=503,
            )
        try:
            nonce = base64.b64decode(row["secret_nonce"])
            ciphertext = base64.b64decode(row["secret_ciphertext"])
            return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
        except TwoStepError:
            raise
        except Exception:
            raise TwoStepError(
                "TWO_STEP_KEY_UNAVAILABLE",
                "This two-step secret cannot be read with the current key. Enroll again.",
                status=503,
            )
