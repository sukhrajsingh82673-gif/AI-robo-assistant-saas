"""Principal trust boundary for evolution and self-improvement actions.

String prefixes such as ``human:`` are not authentication. In production the
caller must pass a principal object that was produced by the identity layer;
only the test suite may use prefixed strings for convenience.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Union

HUMAN_PRINCIPAL_TYPES = frozenset({"human", "owner"})
_PREFIXES = ("human:", "owner:")


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    principal_id: str
    principal_type: str
    authenticated: bool = True
    tenant_id: Optional[str] = None
    company_id: Optional[str] = None


PrincipalLike = Union[AuthenticatedPrincipal, str]


def _test_mode() -> bool:
    return os.environ.get("ZONATA_TEST_MODE") == "1"


def is_human_principal(actor: PrincipalLike) -> bool:
    if isinstance(actor, AuthenticatedPrincipal):
        return actor.authenticated and actor.principal_type in HUMAN_PRINCIPAL_TYPES
    if _test_mode() and isinstance(actor, str):
        return actor.startswith(_PREFIXES)
    return False


def is_owner_principal(actor: PrincipalLike) -> bool:
    if isinstance(actor, AuthenticatedPrincipal):
        return actor.authenticated and actor.principal_type == "owner"
    if _test_mode() and isinstance(actor, str):
        return actor.startswith("owner:")
    return False


def principal_id(actor: PrincipalLike) -> str:
    if isinstance(actor, AuthenticatedPrincipal):
        return actor.principal_id
    if isinstance(actor, str):
        return actor
    raise TypeError("actor principal must be an AuthenticatedPrincipal or string")
