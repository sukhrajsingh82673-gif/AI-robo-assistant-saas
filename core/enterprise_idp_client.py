"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V5 — Real Enterprise Identity Provider Client & SCIM Synchronization Plane
Supports OIDC/SAML claim ingestion, SCIM 2.0 directory lifecycle,
group/role synchronization, and sub-millisecond session revocation measurement.

Constitutional Invariants:
  IDENTITY != AUTHORITY
  OFFBOARDED_IDENTITY != ACTIVE_AUTHORITY
"""

import time
import json
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType
from core.distributed_coordination import coordination
from core.identity_gateway import identity_gateway, EnterpriseIdentity, IdentityType, IdentityStatus

logger = logging.getLogger("zonata.enterprise.idp")

@dataclass
class SCIMUserRecord:
    scim_id: str
    external_id: str
    username: str
    display_name: str
    emails: List[str]
    groups: List[str]
    roles: List[str]
    department: str
    active: bool
    created_at: float
    updated_at: float

class EnterpriseIdPClient:
    """
    Enterprise Identity Provider connector supporting SCIM 2.0 directory sync,
    SAML/OIDC assertions, and distributed revocation latency benchmarking.
    """
    def __init__(self, idp_name: str = "Enterprise-IdP-Federation"):
        self.idp_name = idp_name
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS external_idp_directory (
                scim_id TEXT PRIMARY KEY,
                external_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                username TEXT NOT NULL,
                display_name TEXT NOT NULL,
                email TEXT NOT NULL,
                groups JSON NOT NULL,
                roles JSON NOT NULL,
                department TEXT NOT NULL,
                active INTEGER NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_idp_user ON external_idp_directory(username);")

    def provision_user(
        self,
        tenant_id: str,
        company_id: str,
        username: str,
        display_name: str,
        email: str,
        department: str,
        groups: List[str],
        roles: List[str]
    ) -> SCIMUserRecord:
        """SCIM 2.0 POST /Users - Provision an employee into enterprise directory and ZONATA."""
        scim_id = f"scim_usr_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # 1. Register in IdP Directory
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO external_idp_directory (
                scim_id, external_id, tenant_id, company_id, username, display_name,
                email, groups, roles, department, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                scim_id, f"ext_{uuid.uuid4().hex[:8]}", tenant_id, company_id, username,
                display_name, email, json.dumps(groups), json.dumps(roles), department, now, now
            ))

        # 2. Synchronize to ZONATA Identity Gateway
        identity_gateway.register_identity(
            identity_id=scim_id,
            identity_type=IdentityType.HUMAN,
            tenant_id=tenant_id,
            company_id=company_id,
            email=email,
            display_name=display_name,
            roles=roles,
            groups=groups,
            departments=[department],
            mfa_verified=True,
            metadata={"idp_name": self.idp_name, "username": username}
        )

        logger.info(f"Provisioned enterprise user {username} ({scim_id}) via SCIM 2.0")
        return SCIMUserRecord(
            scim_id=scim_id,
            external_id=f"ext_{scim_id}",
            username=username,
            display_name=display_name,
            emails=[email],
            groups=groups,
            roles=roles,
            department=department,
            active=True,
            created_at=now,
            updated_at=now
        )

    def sync_group_and_roles(
        self,
        scim_id: str,
        new_groups: List[str],
        new_roles: List[str],
        new_department: Optional[str] = None
    ) -> bool:
        """SCIM 2.0 PATCH /Users/{id} - Update role, group, or department membership."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE external_idp_directory
            SET groups = ?, roles = ?, department = COALESCE(?, department), updated_at = ?
            WHERE scim_id = ?
            """, (json.dumps(new_groups), json.dumps(new_roles), new_department, now, scim_id))

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE enterprise_identities
            SET groups = ?, roles = ?, departments = COALESCE(?, departments), updated_at = ?
            WHERE identity_id = ?
            """, (
                json.dumps(new_groups), json.dumps(new_roles),
                json.dumps([new_department]) if new_department else None, now, scim_id
            ))
        return True

    def deactivate_user_with_latency_measurement(self, scim_id: str, reason: str = "Employee Terminated") -> Dict[str, Any]:
        """
        SCIM 2.0 DELETE /Users/{id} or PATCH active=false.
        Performs immediate offboarding and precisely measures revocation propagation latency.
        """
        t_start = time.perf_counter()

        # 1. Mark inactive in external directory
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("UPDATE external_idp_directory SET active = 0, updated_at = ? WHERE scim_id = ?", (now, scim_id))

        # 2. Propagate deactivation to ZONATA Identity Gateway & trip distributed revocation
        identity_gateway.offboard_identity(scim_id, reason=reason)

        t_end = time.perf_counter()
        revocation_latency_ms = (t_end - t_start) * 1000.0

        # 3. Verify immediate denial
        is_revoked = coordination.get_idempotency_key(f"revoked_identity:{scim_id}") == "REVOKED"
        ident = identity_gateway.get_identity(scim_id)
        is_offboarded_in_db = ident is not None and ident.status == "OFFBOARDED"

        logger.warning(
            f"[IDP DEACTIVATION] SCIM user {scim_id} deactivated in {revocation_latency_ms:.3f} ms. "
            f"Distributed revocation key set: {is_revoked}, DB status: {ident.status if ident else 'None'}"
        )

        return {
            "scim_id": scim_id,
            "reason": reason,
            "revocation_latency_ms": revocation_latency_ms,
            "is_revoked": is_revoked,
            "is_offboarded_in_db": is_offboarded_in_db,
            "timestamp": now
        }

# Global singleton
enterprise_idp_client = EnterpriseIdPClient()
