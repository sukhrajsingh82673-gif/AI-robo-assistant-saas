"""
ZONATA Sovereign Core — Sub-Step 5C: Workload Identity & Service Authentication.
================================================================================
Governed by:
- Rule 42: Least privilege & default deny. Workload identities cannot acquire human sessions.
- SPIFFE-standard identification: spiffe://zonata.internal/ns/{tenant_id}/sa/{service}
- Service-to-service authorization matrix and GitHub App scoped installation tokens.
"""

from __future__ import annotations

import hmac
import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from core.identity.types import (
    MachineInteractiveLoginForbiddenError,
    WorkloadIdentity,
)


@dataclass
class GitHubAppToken:
    installation_id: str
    token: str
    permissions: Dict[str, str]
    repositories: List[str]
    issued_at: float
    expires_at: float


class WorkloadIdentityValidator:
    """Validates mTLS / SPIFFE IDs and enforces service-to-service boundary policies."""

    def __init__(self, trust_domain: str = "zonata.internal"):
        self.trust_domain = trust_domain
        self._revoked_spiffe_ids: Set[str] = set()
        # Allowed caller -> callee service interactions
        self._acl: Dict[str, Set[str]] = {
            "agent_runtime": {"action_gateway", "document_service", "llm_gateway"},
            "action_gateway": {"temporal_adapter", "ledger_service", "openbao_transit"},
            "langgraph_runtime": {"action_gateway", "document_service"},
            "adk_runtime": {"action_gateway", "document_service"},
            "worker_temporal": {"action_gateway", "ledger_service"},
            "github_webhook_worker": {"action_gateway", "event_bus"},
        }

    def revoke_spiffe_id(self, spiffe_id: str) -> None:
        """Revoke a workload SPIFFE credential immediately during incident containment."""
        self._revoked_spiffe_ids.add(spiffe_id)

    def is_spiffe_revoked(self, spiffe_id: str) -> bool:
        """Check if a workload SPIFFE credential has been revoked."""
        return spiffe_id in self._revoked_spiffe_ids

    def parse_spiffe_id(self, spiffe_id: str) -> WorkloadIdentity:
        """
        Parse and validate a SPIFFE ID.
        Format: spiffe://{trust_domain}/ns/{tenant_id}/sa/{service_name}
        """
        prefix = f"spiffe://{self.trust_domain}/"
        if not spiffe_id.startswith(prefix):
            raise ValueError(f"Invalid SPIFFE trust domain in {spiffe_id}; expected {self.trust_domain}")

        path = spiffe_id[len(prefix):]
        parts = path.split("/")
        if len(parts) != 4 or parts[0] != "ns" or parts[2] != "sa":
            raise ValueError(f"Malformed SPIFFE ID format: {spiffe_id}")

        tenant_id = parts[1]
        service_name = parts[3]
        now = time.time()

        return WorkloadIdentity(
            spiffe_id=spiffe_id,
            tenant_id=tenant_id,
            service_name=service_name,
            issued_at=now,
            expires_at=now + 3600,
            is_machine=True,
            allowed_surfaces=list(self._acl.get(service_name, set())),
        )

    def check_service_access(self, caller: WorkloadIdentity, target_service: str) -> bool:
        """Enforce service-to-service least-privilege matrix."""
        if caller.spiffe_id in self._revoked_spiffe_ids:
            return False
        allowed_targets = self._acl.get(caller.service_name, set())
        if target_service not in allowed_targets:
            return False
        return True

    def assert_not_machine_interactive(self, identity: WorkloadIdentity) -> None:
        """Rule 42: Machine identities are forbidden from acquiring human interactive sessions."""
        if identity.is_machine:
            raise MachineInteractiveLoginForbiddenError(
                f"Rule 42 Violation: Workload identity '{identity.spiffe_id}' cannot acquire interactive user session."
            )


class GitHubAppTokenManager:
    """Issues and validates short-lived scoped installation tokens for CI/CD integrations."""

    def __init__(self, signing_secret: Optional[str] = None):
        self.signing_secret = signing_secret or secrets.token_hex(32)
        self._tokens: Dict[str, GitHubAppToken] = {}

    def issue_installation_token(
        self,
        installation_id: str,
        repositories: List[str],
        permissions: Dict[str, str],
        ttl_seconds: int = 3600,
    ) -> GitHubAppToken:
        """Issue a scoped, short-lived GitHub App installation token."""
        now = time.time()
        rand = secrets.token_urlsafe(24)
        raw = f"{installation_id}:{rand}:{now}"
        sig = hmac.new(self.signing_secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        token_str = f"ghs_{installation_id}_{rand}_{sig}"

        token_obj = GitHubAppToken(
            installation_id=installation_id,
            token=token_str,
            permissions=dict(permissions),
            repositories=list(repositories),
            issued_at=now,
            expires_at=now + ttl_seconds,
        )
        self._tokens[token_str] = token_obj
        return token_obj

    def verify_token(self, token_str: str, required_repo: Optional[str] = None, required_perm: Optional[tuple[str, str]] = None) -> GitHubAppToken:
        """Verify token authenticity, expiration, repository boundary, and permissions."""
        token_obj = self._tokens.get(token_str)
        if not token_obj:
            raise PermissionError("Invalid or unknown GitHub App token")

        if time.time() > token_obj.expires_at:
            raise PermissionError("GitHub App token has expired")

        if required_repo and required_repo not in token_obj.repositories and "*" not in token_obj.repositories:
            raise PermissionError(f"GitHub App token not authorized for repository {required_repo}")

        if required_perm:
            perm_key, perm_level = required_perm
            granted = token_obj.permissions.get(perm_key)
            if not granted:
                raise PermissionError(f"GitHub App token missing permission for {perm_key}")
            # Hierarchy: admin > write > read
            levels = {"read": 1, "write": 2, "admin": 3}
            if levels.get(granted, 0) < levels.get(perm_level, 0):
                raise PermissionError(f"GitHub App token insufficient permission level for {perm_key}: requires {perm_level}, got {granted}")

        return token_obj
