"""
ZONATA Origin-Bound Credential Vault Types & Errors (OpenCode Step 3D)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class SecretType(str, Enum):
    PASSWORD = "PASSWORD"
    API_KEY = "API_KEY"
    COOKIE_JAR = "COOKIE_JAR"
    OAUTH_TOKEN = "OAUTH_TOKEN"
    SSH_KEY = "SSH_KEY"


class PrivilegeLevel(str, Enum):
    STANDARD = "STANDARD"
    HIGH_PRIVILEGE = "HIGH_PRIVILEGE"


class OriginMismatchError(Exception):
    """Raised when attempting to inject credentials into a non-matching origin."""
    pass


class SecretExportForbiddenError(Exception):
    """Raised when an attempt is made to export or extract plaintext secrets."""
    pass


class HighPrivilegeApprovalRequiredError(Exception):
    """Raised when high-privilege credentials require human ActionGateway approval."""
    pass


class SecretRevokedOrExpiredError(Exception):
    """Raised when a secret is revoked, expired, or inactive."""
    pass


@dataclass
class SecretRecord:
    secret_id: str
    tenant_id: str
    company_id: str
    name: str
    origin: str
    username_ciphertext: Optional[str]
    secret_ciphertext: str
    secret_type: SecretType
    privilege_level: PrivilegeLevel = PrivilegeLevel.STANDARD
    allowed_agent_ids: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_used_at: Optional[float] = None
    revoked_at: Optional[float] = None

    @property
    def placeholder(self) -> str:
        return f"{{{{CREDENTIAL:{self.name}}}}}"

    def to_safe_dict(self) -> Dict[str, Any]:
        """Safe non-confidential dictionary for audits."""
        return {
            "secret_id": self.secret_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "name": self.name,
            "origin": self.origin,
            "has_username": bool(self.username_ciphertext),
            "secret_type": self.secret_type.value,
            "privilege_level": self.privilege_level.value,
            "placeholder": self.placeholder,
            "allowed_agent_ids": self.allowed_agent_ids,
            "allowed_roles": self.allowed_roles,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_revoked": bool(self.revoked_at),
        }
