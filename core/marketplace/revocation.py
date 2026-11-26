"""
Instant Package Revocation Engine (< 1s revocation) (ADR 0055, Rule 81).
Immediately terminates active sandbox runtimes and invalidates installation tokens.
"""

import time
from typing import Dict, Any, List, Optional
from core.marketplace.sandbox import MarketplaceSandbox


class PackageRevocationEngine:
    """
    Coordinates instantaneous revocation across tenant installations and active runtimes.
    """

    def __init__(self):
        # package_id -> revocation info
        self._revocations: Dict[str, Dict[str, Any]] = {}
        # active sandboxes: list of MarketplaceSandbox
        self._active_sandboxes: List[MarketplaceSandbox] = []

    def register_active_sandbox(self, sandbox: MarketplaceSandbox):
        self._active_sandboxes.append(sandbox)

    def revoke_package_globally(self, package_id: str, reason: str, operator_id: str) -> Dict[str, Any]:
        t0 = time.time()
        self._revocations[package_id] = {
            "package_id": package_id,
            "reason": reason,
            "operator_id": operator_id,
            "revoked_at": t0,
        }

        # Instantly invalidate all running sandbox runtimes
        revoked_count = 0
        for sb in self._active_sandboxes:
            if sb.package_id == package_id:
                sb.revoke()
                revoked_count += 1

        elapsed_ms = (time.time() - t0) * 1000.0

        return {
            "package_id": package_id,
            "status": "REVOKED",
            "runtimes_terminated": revoked_count,
            "elapsed_ms": round(elapsed_ms, 3),
            "revoked_within_sla": elapsed_ms < 1000.0,
        }

    def is_package_revoked(self, package_id: str) -> bool:
        return package_id in self._revocations
