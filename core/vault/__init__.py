"""
ZONATA Enterprise Origin-Bound Credential Vault (OpenCode Step 3D)
"""

from .types import (
    SecretType,
    PrivilegeLevel,
    OriginMismatchError,
    SecretExportForbiddenError,
    HighPrivilegeApprovalRequiredError,
    SecretRevokedOrExpiredError,
    SecretRecord,
)
from .origin import OriginValidator
from .vault import OriginBoundSecretVault
from .injector import CredentialInjector
from .cookies import EphemeralCookieManager

__all__ = [
    "SecretType",
    "PrivilegeLevel",
    "OriginMismatchError",
    "SecretExportForbiddenError",
    "HighPrivilegeApprovalRequiredError",
    "SecretRevokedOrExpiredError",
    "SecretRecord",
    "OriginValidator",
    "OriginBoundSecretVault",
    "CredentialInjector",
    "EphemeralCookieManager",
]
