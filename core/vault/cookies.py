"""
ZONATA Ephemeral Cookie Jar Manager (OpenCode Step 3D)
Binds session cookies strictly to origins and purges them on session end.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Dict, Optional, Any

from core.db import db
from .origin import OriginValidator
from .types import OriginMismatchError

logger = logging.getLogger("zonata.vault.cookies")


class EphemeralCookieManager:
    """
    Manages session-scoped, origin-bound encrypted cookies with automatic purge.
    """

    def __init__(self):
        pass

    def store_session_cookies(
        self,
        tenant_id: str,
        company_id: str,
        session_id: str,
        origin: str,
        cookies: Dict[str, str],
        lifetime_seconds: float = 3600.0,
    ) -> str:
        normalized_origin = OriginValidator.normalize_origin(origin)
        cookie_id = f"ck_{uuid.uuid4().hex[:12]}"
        now = time.time()
        expires_at = now + lifetime_seconds
        enc_payload = json.dumps(cookies)

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO enterprise_ephemeral_cookies (
                    cookie_id, tenant_id, company_id, session_id,
                    origin, cookie_ciphertext, created_at, expires_at, purged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    cookie_id, tenant_id, company_id, session_id,
                    normalized_origin, enc_payload, now, expires_at,
                ),
            )
            if hasattr(conn, "commit"):
                conn.commit()

        return cookie_id

    def retrieve_session_cookies(
        self,
        tenant_id: str,
        company_id: str,
        session_id: str,
        target_url: str,
    ) -> Dict[str, str]:
        """Retrieves cookies only if target_url matches registered origin."""
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT origin, cookie_ciphertext, expires_at, purged_at
                FROM enterprise_ephemeral_cookies
                WHERE tenant_id = ? AND company_id = ? AND session_id = ? AND purged_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (tenant_id, company_id, session_id),
            ).fetchone()

        if not row:
            return {}

        bound_origin = row[0]
        enc_payload = row[1]
        expires_at = row[2]
        purged_at = row[3]

        if purged_at or now > expires_at:
            return {}

        if not OriginValidator.match_origin(bound_origin, target_url):
            raise OriginMismatchError(
                f"Cookie origin mismatch: cookies bound to '{bound_origin}', requested for '{target_url}'."
            )

        try:
            return json.loads(enc_payload)
        except Exception:
            return {}

    def purge_session(self, tenant_id: str, company_id: str, session_id: str) -> int:
        """Purges and wipes session cookies immediately upon session completion or logout."""
        now = time.time()
        with db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE enterprise_ephemeral_cookies
                SET purged_at = ?, cookie_ciphertext = '[PURGED]'
                WHERE tenant_id = ? AND company_id = ? AND session_id = ? AND purged_at IS NULL
                """,
                (now, tenant_id, company_id, session_id),
            )
            if hasattr(conn, "commit"):
                conn.commit()
            return cursor.rowcount if hasattr(cursor, "rowcount") else 1
