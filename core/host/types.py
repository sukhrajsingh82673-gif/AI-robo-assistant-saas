"""
ZONATA Host Permission Model & Device Management Types
======================================================
OpenCode Step 3B: Host permission model and the host agent.
Enforces Rule 15 (Principal separation: only humans create grants)
and Rule 23 (Consent enforced on host).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any


class GrantMode(str, Enum):
    OBSERVE = "OBSERVE"                      # Read/screenshot only; no synthetic inputs
    CONFIRM_EACH = "CONFIRM_EACH"            # Every individual synthetic action requires human confirmation on host
    AUTONOMOUS_IN_SCOPE = "AUTONOMOUS_IN_SCOPE"  # Autonomous execution within strictly granted application/folder allowlist


class GrantScope(str, Enum):
    PERSONAL = "PERSONAL"                    # Owner's own tasks; owner's grant only
    COMPANY = "COMPANY"                      # Company operations; requires AI CEO policy gate + owner's grant


class DeviceStatus(str, Enum):
    PENDING = "PENDING"
    PAIRED = "PAIRED"
    REVOKED = "REVOKED"
    OFFLINE = "OFFLINE"


class HostSessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HALTED = "HALTED"
    EXPIRED = "EXPIRED"
    DISCONNECTED = "DISCONNECTED"


class GrantEventType(str, Enum):
    GRANT_CREATED = "GRANT_CREATED"
    GRANT_REVOKED = "GRANT_REVOKED"
    GRANT_EXPIRED = "GRANT_EXPIRED"
    COMMAND_ALLOWED = "COMMAND_ALLOWED"
    COMMAND_DENIED = "COMMAND_DENIED"
    KILL_SWITCH_ENGAGED = "KILL_SWITCH_ENGAGED"
    HEARTBEAT_LOST = "HEARTBEAT_LOST"


# Deny-by-default applications: NEVER permitted unless explicitly named in a grant AND confirmed
DENIED_BY_DEFAULT_APPS: Set[str] = {
    # Password Managers
    "1password",
    "bitwarden",
    "keepass",
    "keepassxc",
    "lastpass",
    "dashlane",
    "enpass",
    "nordpass",
    "keeper",
    # Banking and Payment Portals
    "chase",
    "bankofamerica",
    "wellsfargo",
    "paypal",
    "stripe_dashboard",
    "venmo",
    "revolut",
    "wise",
    # OS Security & Key Management
    "windows_defender",
    "keychain_access",
    "control_panel",
    "system_settings",
    "regedit",
    "sudo",
    "terminal_root",
    "zonata_host_agent",
}


@dataclass
class DeviceRecord:
    device_id: str
    tenant_id: str
    company_id: str
    owner_id: str
    device_name: str
    os_type: str
    public_key: str
    pairing_status: DeviceStatus
    pairing_code_hash: Optional[str] = None
    pairing_code_expires_at: Optional[float] = None
    last_seen_at: Optional[float] = None
    created_at: float = 0.0


@dataclass
class HostGrantRecord:
    grant_id: str
    device_id: str
    tenant_id: str
    company_id: str
    scope_type: GrantScope
    mode: GrantMode
    allowed_apps: List[str]
    allowed_folders: List[str]
    allowed_domains: List[str]
    allowed_actions: List[str]
    created_by_principal_id: str
    created_by_principal_type: str
    valid_from: float
    valid_until: float
    status: str = "ACTIVE"
    revoked_at: Optional[float] = None
    revoked_by_principal_id: Optional[str] = None
    created_at: float = 0.0


@dataclass
class GrantEventRecord:
    event_id: str
    grant_id: Optional[str]
    device_id: str
    tenant_id: str
    company_id: str
    event_type: GrantEventType
    details: Dict[str, Any]
    actor_id: str
    actor_type: str
    timestamp: float


@dataclass
class HostSessionRecord:
    session_id: str
    device_id: str
    tenant_id: str
    company_id: str
    status: HostSessionStatus
    last_sequence_no: int = 0
    last_heartbeat_at: Optional[float] = None
    created_at: float = 0.0


class HostSecurityViolation(Exception):
    """Raised when host security policies, replay checks, or grants are violated."""
    pass


class ReplayDetectedError(HostSecurityViolation):
    """Raised when an envelope with a duplicate nonce or stale sequence number is received."""
    pass


class OutOfGrantError(HostSecurityViolation):
    """Raised when an action exceeds the bounds of granted applications or modes."""
    pass


class DeniedByDefaultError(HostSecurityViolation):
    """Raised when an action targets a protected application category without explicit confirmation."""
    pass


class StepUpAuthenticationRequiredError(HostSecurityViolation):
    """Raised when pairing or grant creation lacks human step-up authentication."""
    pass


def ensure_host_permission_tables(conn: Optional[Any] = None) -> None:
    """Ensures devices, host_grants, grant_events, and host_sessions exist."""
    import pathlib
    from core.db import db, DatabaseDialect

    migration_file = "0029_host_permission_model.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    def _apply_on_conn(target_conn):
        if db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                sql_text = sql_path.read_text(encoding="utf-8")
                if hasattr(target_conn, "executescript"):
                    target_conn.executescript(sql_text)
                else:
                    for stmt in sql_text.split(";"):
                        s = stmt.strip()
                        if s:
                            target_conn.execute(s)
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                sql_text = sql_path.read_text(encoding="utf-8")
                target_conn.execute(sql_text)

    if conn is not None:
        _apply_on_conn(conn)
        return

    with db.get_connection() as connection:
        _apply_on_conn(connection)

