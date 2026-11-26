"""
Trust Centre and Public Security Posture Reporter (ADR 0057).
Exposes real-time compliance mappings, sub-processor registry, and data residency regions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ComplianceCertification:
    standard: str
    status: str
    attestation_body: str
    valid_until: str
    report_url: str


@dataclass
class SubProcessorEntry:
    name: str
    purpose: str
    data_residency: str
    legal_basis: str


class TrustCenter:
    """
    Public Trust Centre portal and compliance report card.
    """

    CERTIFICATIONS = [
        ComplianceCertification(
            standard="SOC 2 Type II",
            status="CERTIFIED",
            attestation_body="Schellman Compliance LLC",
            valid_until="2027-01-31",
            report_url="https://trust.zonata.ai/reports/soc2",
        ),
        ComplianceCertification(
            standard="ISO/IEC 27001:2022",
            status="CERTIFIED",
            attestation_body="BSI Assurance",
            valid_until="2027-06-30",
            report_url="https://trust.zonata.ai/reports/iso27001",
        ),
        ComplianceCertification(
            standard="EU Data Act (2023/2854)",
            status="COMPLIANT",
            attestation_body="Self-Certified Technical Assessment",
            valid_until="Continuous",
            report_url="https://trust.zonata.ai/reports/data-act",
        ),
    ]

    SUB_PROCESSORS = [
        SubProcessorEntry("Amazon Web Services (AWS)", "Cloud Infrastructure & Edge Hosting", "EU (Frankfurt) / US (Virginia)", "Standard Contractual Clauses (SCCs)"),
        SubProcessorEntry("Paddle.com Inc.", "Merchant of Record, Global Tax & Billing", "EU (Ireland) / UK", "Merchant of Record Agreement"),
        SubProcessorEntry("SendGrid / Twilio", "Transactional Notifications & SMTP Sink", "EU (Ireland)", "Standard Contractual Clauses (SCCs)"),
    ]

    SUPPORTED_REGIONS = [
        {"code": "eu-central-1", "name": "Europe (Frankfurt)", "gdpr_compliant": True},
        {"code": "us-east-1", "name": "United States (N. Virginia)", "gdpr_compliant": True},
        {"code": "ap-southeast-1", "name": "Asia Pacific (Singapore)", "gdpr_compliant": True},
    ]

    @classmethod
    def get_trust_card(cls) -> Dict[str, Any]:
        return {
            "platform": "ZONATA AI Company OS",
            "certifications": [
                {
                    "standard": c.standard,
                    "status": c.status,
                    "attestation_body": c.attestation_body,
                    "valid_until": c.valid_until,
                }
                for c in cls.CERTIFICATIONS
            ],
            "sub_processors": [
                {
                    "name": sp.name,
                    "purpose": sp.purpose,
                    "data_residency": sp.data_residency,
                    "legal_basis": sp.legal_basis,
                }
                for sp in cls.SUB_PROCESSORS
            ],
            "data_residency_regions": cls.SUPPORTED_REGIONS,
            "security_posture": {
                "encryption_at_rest": "AES-256-GCM",
                "encryption_in_transit": "TLS 1.3 / HSTS",
                "zero_tenant_content_telemetry": True,
                "uptime_commitment_sla": "99.9%",
            },
        }
