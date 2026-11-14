"""Connection and ownership-verification adapters.

Every provider starts as a null adapter. A null adapter says, in plain words,
that nothing was read and no credential was exercised. It never reports a
success and never sets ``verified`` to true.

When a real provider is added, only the matching adapter changes: the service,
the route and the UI contract stay the same.
"""

from __future__ import annotations

import secrets
import time
from typing import Any, Dict, Optional

from core.company_setup.sources import find_source


def _now() -> float:
    return time.time()


class ConnectionAdapter:
    """Base adapter for one provider family."""

    provider_id = "custom"
    available = False

    def unavailable_reason(self) -> str:
        return (
            f"No {self.provider_id} adapter is configured on this deployment. "
            "Nothing was read and no credential was used."
        )

    def test(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "available": False,
            "verified": False,
            "simulated": False,
            "status": "UNAVAILABLE",
            "checked_at": _now(),
            "error": self.unavailable_reason(),
            "read_count": 0,
        }


class _NullAdapter(ConnectionAdapter):
    def __init__(self, provider_id: str):
        self.provider_id = provider_id


_ADAPTERS: Dict[str, ConnectionAdapter] = {
    source_id: _NullAdapter(source_id)
    for source_id in (
        "accounting",
        "banking",
        "payments",
        "commerce",
        "crm",
        "workspace",
        "communications",
        "uploads",
    )
}


def get_adapter(provider_id: str) -> ConnectionAdapter:
    key = str(provider_id or "").strip().lower()
    return _ADAPTERS.get(key) or _NullAdapter(key or "custom")


def adapter_available(provider_id: str) -> bool:
    return bool(get_adapter(provider_id).available)


class OwnershipVerifier:
    """DNS TXT / email ownership verification for a private source.

    No DNS resolver or mailbox adapter is wired on this deployment, so
    :meth:`available` is false and the service must tell the user that
    verification is not configured. It never accepts a guessed token.
    """

    available = False

    def issue_token(self) -> str:
        return f"zonata-verify-{secrets.token_hex(16)}"

    def unavailable_reason(self) -> str:
        return (
            "Ownership verification needs a DNS or mailbox adapter. "
            "None is configured on this deployment, so no private data is read."
        )

    def instructions(self, method: str, token: Optional[str] = None) -> Dict[str, Any]:
        method = str(method or "DNS_TXT").upper()
        source = "the domain's DNS records" if method == "DNS_TXT" else "the mailbox inbox"
        return {
            "method": method,
            "configured": False,
            "token": token,
            "instructions": (
                f"Ownership is proven by publishing a value in {source}. "
                f"{self.unavailable_reason()}"
            ),
        }


def verification_methods_for(provider_id: str) -> list:
    source = find_source(provider_id) or {}
    methods = [str(method).upper() for method in (source.get("methods") or [])]
    if "EMAIL" in methods:
        return ["EMAIL"]
    if any(method in ("OAUTH", "READ_ONLY_API") for method in methods):
        return ["DNS_TXT", "EMAIL"]
    return []
