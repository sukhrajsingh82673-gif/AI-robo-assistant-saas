"""
ZONATA Sovereign Core — Identity & Access Package.
"""

from core.identity.types import (
    RoleTier,
    SCIM_PERMITTED_ROLES,
    IdentityTokenContext,
    WorkloadIdentity,
    IdentitySecurityError,
    UnauthorizedOwnerPromotionError,
    StepUpRequiredError,
    MFAEnforcementError,
    AudienceMismatchError,
    OwnershipTransferCoolingOffError,
    DualControlApprovalRequiredError,
    RecoveryForbiddenByEmailAloneError,
    TokenReuseDetectedError,
    MachineInteractiveLoginForbiddenError,
)
from core.identity.ownership import OwnershipGovernance, OwnershipTransferRecord
from core.identity.api_keys import APIKeyManager, APIKeyRecord
from core.identity.workload import WorkloadIdentityValidator, GitHubAppTokenManager, GitHubAppToken

__all__ = [
    "RoleTier",
    "SCIM_PERMITTED_ROLES",
    "IdentityTokenContext",
    "WorkloadIdentity",
    "IdentitySecurityError",
    "UnauthorizedOwnerPromotionError",
    "StepUpRequiredError",
    "MFAEnforcementError",
    "AudienceMismatchError",
    "OwnershipTransferCoolingOffError",
    "DualControlApprovalRequiredError",
    "RecoveryForbiddenByEmailAloneError",
    "TokenReuseDetectedError",
    "MachineInteractiveLoginForbiddenError",
    "OwnershipGovernance",
    "OwnershipTransferRecord",
    "APIKeyManager",
    "APIKeyRecord",
    "WorkloadIdentityValidator",
    "GitHubAppTokenManager",
    "GitHubAppToken",
]
