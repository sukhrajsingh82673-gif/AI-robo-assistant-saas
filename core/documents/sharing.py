"""ZONATA Sovereign Core — Document Sharing, Internal Grants, and External Ephemeral Links.

Implements OpenCode Step 1E:
- Internal access grants: grantee_type (user, role, agent), permission (READ, WRITE, ADMIN).
- Time-limited external share links: token hashed with SHA-256 in database.
- Expired links are rejected with ShareLinkExpiredError.
- Revoked links are rejected with ShareLinkRevokedError.
- External links serve decrypted content securely without exposing raw storage buckets.
"""

from __future__ import annotations
import hashlib
import json
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.db import db
from core.evidence_ledger import EvidenceLedger
from core.documents.evidence import seal_document_event
from core.documents.versioning import get_document_version_payload


class AccessDeniedError(Exception):
    """Raised when user or agent does not have permission to access a document."""
    pass


class ShareLinkExpiredError(Exception):
    """Raised when an external share link has expired."""
    pass


class ShareLinkRevokedError(Exception):
    """Raised when an external share link was revoked."""
    pass


def create_access_grant(
    document_id: str,
    tenant_id: str,
    company_id: str,
    grantee_type: str,
    grantee_id: str,
    permission: str = "READ",
    granted_by: str = "usr_admin",
) -> str:
    """Grants internal access to a document."""
    grant_id = f"grnt_{uuid.uuid4().hex[:16]}"
    now = time.time()
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO access_grants (
                id, tenant_id, company_id, document_id, grantee_type,
                grantee_id, permission, granted_by, granted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (grant_id, tenant_id, company_id, document_id, grantee_type, grantee_id, permission, granted_by, now)
        )
    return grant_id


def check_access(
    document_id: str,
    tenant_id: str,
    user_id: str,
    user_roles: Optional[List[str]] = None,
    required_permission: str = "READ",
) -> bool:
    """Checks whether user has required permission to access document in tenant."""
    roles = user_roles or []
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, sensitivity_level, tombstone FROM documents WHERE id = ?",
            (document_id,)
        )
        row = cur.fetchone()
        if not row:
            return False

        doc_tenant_id, sensitivity, tombstone = row[0], row[1], row[2]
        if tombstone:
            return False

        # Invariant: Strict multi-tenant isolation
        if doc_tenant_id != tenant_id:
            return False

        # Owner / creator / admin or explicit grant check
        cur.execute(
            """
            SELECT permission FROM access_grants
            WHERE document_id = ? AND tenant_id = ? AND revoked_at IS NULL
              AND ((grantee_type = 'user' AND grantee_id = ?)
                OR (grantee_type = 'role' AND grantee_id IN (%s)))
            """ % (",".join(["?"] * len(roles)) if roles else "''"),
            [document_id, tenant_id, user_id] + roles
        )
        grants = [r[0] for r in cur.fetchall()]
        if "ADMIN" in grants:
            return True
        if required_permission == "READ" and ("READ" in grants or "WRITE" in grants):
            return True
        if required_permission == "WRITE" and "WRITE" in grants:
            return True

        # Default fallback: if document is PUBLIC, READ is granted
        if sensitivity == "PUBLIC" and required_permission == "READ":
            return True

        # If user is document creator
        cur.execute("SELECT created_by FROM documents WHERE id = ?", (document_id,))
        creator = cur.fetchone()
        if creator and creator[0] == user_id:
            return True

        return False


def create_share_link(
    document_id: str,
    tenant_id: str,
    company_id: str,
    created_by: str,
    expires_in_seconds: int = 3600,
    ledger: Optional[EvidenceLedger] = None,
) -> Tuple[str, str, float]:
    """Generates an external time-limited share link.

    Returns (link_id, raw_token, expires_at).
    """
    ledger = ledger or EvidenceLedger()
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    link_id = f"sh_{uuid.uuid4().hex[:16]}"
    now = time.time()
    expires_at = now + expires_in_seconds

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO share_links (
                id, tenant_id, company_id, document_id, token_hash,
                expires_at, created_by, revoked_at, access_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0, ?)
            """,
            (link_id, tenant_id, company_id, document_id, token_hash, expires_at, created_by, now)
        )

    seal_document_event(
        ledger=ledger,
        event_type="DOCUMENT_SHARE_LINK_CREATED",
        actor_id=created_by,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={"document_id": document_id, "link_id": link_id, "expires_at": expires_at}
    )

    return link_id, raw_token, expires_at


def access_share_link(raw_token: str) -> Tuple[Dict[str, Any], bytes]:
    """Resolves an external share token.

    Verifies expiration and revocation, then serves document bytes without exposing storage URLs.
    """
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = time.time()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, tenant_id, company_id, document_id, expires_at, revoked_at, access_count
            FROM share_links
            WHERE token_hash = ?
            """,
            (token_hash,)
        )
        row = cur.fetchone()
        if not row:
            raise ShareLinkRevokedError("Invalid or nonexistent share link")

        link_id, tenant_id, company_id, doc_id, expires_at, revoked_at, access_count = row

        if revoked_at is not None:
            raise ShareLinkRevokedError("Share link was revoked")

        if now > expires_at:
            raise ShareLinkExpiredError(f"Share link expired at {expires_at} (current time {now})")

        conn.execute("UPDATE share_links SET access_count = access_count + 1 WHERE id = ?", (link_id,))

    # Read payload securely via versioning engine
    meta, payload = get_document_version_payload(doc_id, verify_on_read=True)
    meta["link_id"] = link_id
    meta["tenant_id"] = tenant_id
    return meta, payload


def revoke_share_link(raw_token: str, revoked_by: str) -> None:
    """Revokes an active share link."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE share_links SET revoked_at = ? WHERE token_hash = ?",
            (time.time(), token_hash)
        )
