"""
Legal Document Registry and Clickwrap Acceptance Tracker.
Maintains versioned legal texts and stores cryptographic records of tenant consent.
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class LegalDocumentVersion:
    doc_id: str
    version: str
    title: str
    effective_date: str
    sha256_hash: str
    content_text: str


@dataclass
class AgreementClickwrap:
    agreement_id: str
    tenant_id: str
    user_id: str
    doc_id: str
    doc_version: str
    accepted_at: float
    ip_address: str
    doc_hash: str


class LegalDocumentRegistry:
    """
    Registry of canonical legal documents: Terms of Service, Privacy Policy, DPA, BAA.
    """

    DOCUMENTS: Dict[str, LegalDocumentVersion] = {
        "tos": LegalDocumentVersion(
            doc_id="tos",
            version="2026.1",
            title="ZONATA Terms of Service",
            effective_date="2026-01-01",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            content_text="Terms of Service governing the use of the ZONATA Autonomous AI Company Platform...",
        ),
        "privacy": LegalDocumentVersion(
            doc_id="privacy",
            version="2026.1",
            title="ZONATA Privacy Policy",
            effective_date="2026-01-01",
            sha256_hash="f4b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b866",
            content_text="Privacy Policy governing personal data processing, zero-tenant-content telemetry, and GDPR rights...",
        ),
        "dpa": LegalDocumentVersion(
            doc_id="dpa",
            version="2026.1",
            title="Data Processing Addendum (DPA)",
            effective_date="2026-01-01",
            sha256_hash="a5b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b877",
            content_text="Standard Contractual Clauses (SCCs) and Article 28 GDPR processor terms...",
        ),
        "baa": LegalDocumentVersion(
            doc_id="baa",
            version="2026.1",
            title="Business Associate Agreement (BAA)",
            effective_date="2026-01-01",
            sha256_hash="b6b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b888",
            content_text="HIPAA Business Associate terms for healthcare and PHI processing...",
        ),
    }

    def __init__(self):
        # agreement_id -> AgreementClickwrap
        self._acceptances: Dict[str, AgreementClickwrap] = {}

    def record_consent(
        self, tenant_id: str, user_id: str, doc_id: str, ip_address: str
    ) -> AgreementClickwrap:
        doc = self.DOCUMENTS.get(doc_id)
        if not doc:
            raise KeyError(f"Unknown legal document: '{doc_id}'")

        agreement_id = f"agr_{tenant_id}_{doc_id}_{doc.version}"
        record = AgreementClickwrap(
            agreement_id=agreement_id,
            tenant_id=tenant_id,
            user_id=user_id,
            doc_id=doc_id,
            doc_version=doc.version,
            accepted_at=time.time(),
            ip_address=ip_address,
            doc_hash=doc.sha256_hash,
        )
        self._acceptances[agreement_id] = record
        return record

    def has_accepted(self, tenant_id: str, doc_id: str) -> bool:
        doc = self.DOCUMENTS.get(doc_id)
        if not doc:
            return False
        agreement_id = f"agr_{tenant_id}_{doc_id}_{doc.version}"
        return agreement_id in self._acceptances
