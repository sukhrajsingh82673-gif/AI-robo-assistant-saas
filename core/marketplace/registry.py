"""
Marketplace Package Registry & Security Review Pipeline (Rule 81).
Performs static analysis on extension packages and enforces the commercial truth rule on paid packages.
"""

import time
import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from core.marketplace.manifest import MarketplaceManifest


class PackageReviewStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class MarketplaceRegistry:
    """
    Registry of third-party marketplace packages.
    Scans packages for dangerous patterns (eval, exec, hardcoded keys) before approval.
    """

    DANGEROUS_PATTERNS = [
        re.compile(r'\b(eval|exec|compile)\s*\('),
        re.compile(r'\bos\.system\s*\('),
        re.compile(r'\bsubprocess\.(Popen|call|run)\s*\('),
        re.compile(r'sk_live_[0-9a-zA-Z]{24,}'),
    ]

    def __init__(self):
        # (package_id, version) -> package dict
        self._packages: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # (tenant_id, package_id) -> installation dict
        self._installations: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def submit_package(self, manifest: MarketplaceManifest, source_code: str) -> Dict[str, Any]:
        """
        Submits extension package and runs automated static analysis review.
        """
        key = (manifest.package_id, manifest.version)
        digest = manifest.compute_digest()

        # Run static analysis
        review_status = PackageReviewStatus.APPROVED
        rejection_reasons = []

        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(source_code):
                review_status = PackageReviewStatus.REJECTED
                rejection_reasons.append(f"Security violation: package contains prohibited pattern '{pattern.pattern}'.")

        record = {
            "package_id": manifest.package_id,
            "version": manifest.version,
            "manifest": manifest,
            "digest": digest,
            "review_status": review_status,
            "rejection_reasons": rejection_reasons,
            "submitted_at": time.time(),
        }
        self._packages[key] = record
        return record

    def install_package(
        self, tenant_id: str, package_id: str, version: str, consented_capabilities: List[str]
    ) -> Dict[str, Any]:
        """
        Installs package for tenant.
        Commercial Truth: If package is 'paid', raises NotImplementedError with NOT_IMPLEMENTED.
        """
        key = (package_id, version)
        pkg = self._packages.get(key)
        if not pkg:
            raise KeyError(f"Package '{package_id}' version '{version}' not found in registry.")

        if pkg["review_status"] != PackageReviewStatus.APPROVED:
            raise PermissionError(f"Cannot install package: status is '{pkg['review_status']}'.")

        manifest: MarketplaceManifest = pkg["manifest"]

        # Commercial Truth check: paid listings report NOT_IMPLEMENTED
        if manifest.pricing_type == "paid" or manifest.price_cents > 0:
            raise NotImplementedError("NOT_IMPLEMENTED: Commercial marketplace billing rails are scheduled for future certification.")

        inst_key = (tenant_id, package_id)
        inst_record = {
            "tenant_id": tenant_id,
            "package_id": package_id,
            "version": version,
            "consented_capabilities": list(consented_capabilities),
            "status": "INSTALLED",
            "installed_at": time.time(),
        }
        self._installations[inst_key] = inst_record
        return inst_record

    def get_installation(self, tenant_id: str, package_id: str) -> Optional[Dict[str, Any]]:
        return self._installations.get((tenant_id, package_id))
