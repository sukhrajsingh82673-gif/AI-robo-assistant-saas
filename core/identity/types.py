"""
ZONATA Sovereign Core — Sub-Step 5C: Identity Models, Contexts & Security Exceptions.
===================================================================================
Governed by:
- Rule 42: Least privilege & default deny.
- Rule 44: Owner principal cannot be minted by any IdP, SCIM payload, API, or agent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class RoleTier(str, Enum):
    """Authoritative role hierarchy."""
    OWNER = "OWNER"
    EXECUTIVE = "EXECUTIVE"
    MANAGER = "MANAGER"
    OPERATOR = "OPERATOR"
    AUDITOR = "AUDITOR"
    OBSERVER = "OBSERVER"
    SYSTEM_AGENT = "SYSTEM_AGENT"


# Roles permitted to be provisioned via SCIM or external IdP group mappings (Rule 44)
SCIM_PERMITTED_ROLES = {
    RoleTier.EXECUTIVE.value,
    RoleTier.MANAGER.value,
    RoleTier.OPERATOR.value,
    RoleTier.AUDITOR.value,
    RoleTier.OBSERVER.value,
}


@dataclass
class IdentityTokenContext:
    user_id: str
    tenant_id: str
    company_id: str
    role: str
    email: str
    audience: str
    auth_time: float
    mfa_verified: bool = False
    amr: List[str] = field(default_factory=list)  # Authentication Methods Reference
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    expires_at: float = field(default_factory=lambda: time.time() + 900)  # 15 min default


@dataclass
class WorkloadIdentity:
    spiffe_id: str
    tenant_id: str
    service_name: str
    issued_at: float
    expires_at: float
    is_machine: bool = True
    allowed_surfaces: List[str] = field(default_factory=list)


# Security Exceptions
class IdentitySecurityError(Exception):
    """Base exception for identity and access violations."""
    pass


class UnauthorizedOwnerPromotionError(IdentitySecurityError):
    """Rule 44: The owner principal cannot be minted or elevated by external IdP, SCIM, or API."""
    pass


class StepUpRequiredError(IdentitySecurityError):
    """Triggered when an operation requires recent multi-factor step-up re-authentication."""
    pass


class MFAEnforcementError(IdentitySecurityError):
    """Triggered when high-privilege users attempt login or action without required MFA."""
    pass


class AudienceMismatchError(IdentitySecurityError):
    """Triggered when a token's audience does not match the target service boundary."""
    pass


class OwnershipTransferCoolingOffError(IdentitySecurityError):
    """Rule 44: Ownership transfer cannot be executed before the cooling-off period elapses."""
    pass


class DualControlApprovalRequiredError(IdentitySecurityError):
    """Rule 44: Ownership or governance transfer requires distinct dual-control authorization."""
    pass


class RecoveryForbiddenByEmailAloneError(IdentitySecurityError):
    """Rule 44: Owner account recovery cannot be completed via email channel alone."""
    pass


class TokenReuseDetectedError(IdentitySecurityError):
    """Triggered when an invalidated refresh token is reused, indicating potential theft."""
    pass


class MachineInteractiveLoginForbiddenError(IdentitySecurityError):
    """Rule 42: Machine and agent workload identities cannot acquire human interactive sessions."""
    pass
