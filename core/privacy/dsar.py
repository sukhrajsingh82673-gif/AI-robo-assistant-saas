"""
ZONATA Sovereign Core — Sub-Step 5F: Privacy Engineering, DSAR & Crypto-Shredding.
==================================================================================
Governed by:
- Digital Personal Data Protection Act 2023 (DPDP) & GDPR Art. 15, 17, 33.
- Data Subject Access Request (DSAR) portable bundles.
- Right to Erasure through cryptographic key shredding.
- Statutory 72-hour regulatory breach notification packages.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from core.ports.secrets import get_secrets_provider

logger = logging.getLogger("zonata.privacy.dsar")


@dataclass
class DSARPackage:
    request_id: str
    user_id: str
    tenant_id: str
    exported_at: float
    data_categories: List[str]
    records: Dict[str, Any]
    package_sha256: str


@dataclass
class BreachNotificationReport:
    incident_id: str
    discovered_at: float
    statutory_deadline_at: float  # 72 hours from discovery
    affected_tenants: List[str]
    compromised_categories: List[str]
    root_cause: str
    containment_status: str
    remediation_actions: List[str]
    regulator_notice_ready: bool = True


class DSARManager:
    """Manages Data Subject Access Requests (DSAR) under GDPR Art. 15 & DPDP."""

    def generate_export_bundle(
        self,
        user_id: str,
        tenant_id: str,
        identity_record: Dict[str, Any],
        activity_records: List[Dict[str, Any]],
        consent_records: List[Dict[str, Any]],
    ) -> DSARPackage:
        """Assembles a verifiable, portable personal data bundle for the user."""
        now = time.time()
        request_id = f"dsar_{uuid.uuid4().hex[:12]}"

        raw_data = {
            "identity": identity_record,
            "activities": activity_records,
            "consents": consent_records,
            "exported_at": now,
        }

        canonical_json = json.dumps(raw_data, sort_keys=True)
        sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return DSARPackage(
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            exported_at=now,
            data_categories=["identity", "activity_logs", "consent_history"],
            records=raw_data,
            package_sha256=sha256,
        )


class CryptoShredder:
    """Implements Right to Erasure (GDPR Art. 17) via cryptographic key destruction."""

    def __init__(self, secrets_port=None):
        self.secrets_port = secrets_port or get_secrets_provider()

    def shred_tenant_data(self, tenant_id: str, reason: str = "GDPR Art 17 Erasure") -> Dict[str, Any]:
        """
        Destroys the tenant's Transit encryption keys in the Secrets vault.
        All ciphertexts encrypted under the tenant's keys become mathematically irretrievable.
        """
        res, success = self.secrets_port.destroy_tenant_keys(tenant_id=tenant_id)
        if not success:
            raise RuntimeError(f"Crypto-shredding failed for tenant {tenant_id}: {res.error}")

        return {
            "tenant_id": tenant_id,
            "status": "SHREDDED",
            "reason": reason,
            "timestamp": time.time(),
            "provider_ref": res.provider_ref,
        }


class BreachNotificationCoordinator:
    """Coordinates breach containment and 72-hour statutory regulatory reporting."""

    STATUTORY_WINDOW_HOURS = 72.0

    def generate_notification(
        self,
        incident_id: str,
        discovered_at: float,
        affected_tenants: List[str],
        compromised_categories: List[str],
        root_cause: str,
        containment_status: str = "CONTAINED",
        remediation_actions: Optional[List[str]] = None,
    ) -> BreachNotificationReport:
        deadline = discovered_at + (self.STATUTORY_WINDOW_HOURS * 3600.0)
        remediations = remediation_actions or [
            "Credentials revoked across affected scopes",
            "Active sessions terminated and tokens invalidated",
            "Root-cause patch verified in CI and deployed",
        ]

        return BreachNotificationReport(
            incident_id=incident_id,
            discovered_at=discovered_at,
            statutory_deadline_at=deadline,
            affected_tenants=list(affected_tenants),
            compromised_categories=list(compromised_categories),
            root_cause=root_cause,
            containment_status=containment_status,
            remediation_actions=remediations,
            regulator_notice_ready=True,
        )
