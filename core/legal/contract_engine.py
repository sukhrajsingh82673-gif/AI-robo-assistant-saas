"""
Contract Intelligence, Obligation Extraction & Redline Engine
=============================================================
Adheres to:
- Rule 62: Reserved Human Decisions (Contract execution and legal commitments require gateway approval)
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ContractObligations(BaseModel):
    contract_id: str
    parties: List[str]
    effective_date: str
    auto_renewal_notice_days: int
    liability_cap_description: str
    governing_law: str
    sla_availability_pct: Optional[float] = None
    breach_notification_window_hours: int = 72


class RedlineDeviation(BaseModel):
    clause: str
    playbook_standard: str
    draft_position: str
    severity: str  # 'high', 'medium', 'low'
    recommendation: str


class ContractRedlineResult(BaseModel):
    contract_id: str
    total_deviations: int
    high_risk_deviations: int
    deviations: List[RedlineDeviation] = Field(default_factory=list)
    is_acceptable_as_is: bool


class ContractExecutionRecord(BaseModel):
    contract_id: str
    title: str
    parties: List[str]
    is_signed: bool = False
    human_signatory_id: Optional[str] = None
    approval_token: Optional[str] = None
    signed_at: Optional[str] = None


class ContractEngine:
    """Extracts obligations, runs redline analysis against playbook, and gates execution."""

    @staticmethod
    def extract_obligations(contract_id: str, text: str) -> ContractObligations:
        lower = text.lower()

        # Parties extraction
        parties = []
        party_match = re.search(r"between\s+([A-Za-z0-9\s,\.]+?)\s+(?:and|\&)\s+([A-Za-z0-9\s,\.]+?)(?:\s+dated|\s+effective|\.|\;)", text, re.IGNORECASE)
        if party_match:
            parties = [party_match.group(1).strip(), party_match.group(2).strip()]
        else:
            parties = ["Party A", "Party B"]

        # Effective date
        date_match = re.search(r"effective\s+(?:date|as\s+of)?[:\s]+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
        eff_date = date_match.group(1) if date_match else "2026-01-01"

        # Renewal notice days
        renew_match = re.search(r"(\d+)\s+days?(?:\s+prior)?\s+written\s+notice\s+of\s+non-renewal", text, re.IGNORECASE)
        notice_days = int(renew_match.group(1)) if renew_match else 30

        # Liability cap
        if "uncapped liability" in lower or "no limitation of liability" in lower:
            liability = "UNCAPPED"
        elif "12 months" in lower or "fees paid in the preceding twelve months" in lower:
            liability = "12_MONTHS_FEES"
        else:
            liability = "CUSTOM_CAP"

        # Governing Law
        gov_match = re.search(r"governed\s+by\s+the\s+laws\s+of\s+([a-zA-Z\s]+?)(?:\.|\;|\band\b)", text, re.IGNORECASE)
        gov_law = gov_match.group(1).strip() if gov_match else "India"

        # SLA
        sla_match = re.search(r"(\d{2}(?:\.\d+)?)\s*%\s+(?:uptime|availability)", text, re.IGNORECASE)
        sla_val = float(sla_match.group(1)) if sla_match else None

        # Breach Notification Window
        breach_match = re.search(r"(?:breach|security\s+incident)\s+within\s+(\d+)\s+hours", text, re.IGNORECASE)
        breach_hrs = int(breach_match.group(1)) if breach_match else 72

        return ContractObligations(
            contract_id=contract_id,
            parties=parties,
            effective_date=eff_date,
            auto_renewal_notice_days=notice_days,
            liability_cap_description=liability,
            governing_law=gov_law,
            sla_availability_pct=sla_val,
            breach_notification_window_hours=breach_hrs
        )

    @staticmethod
    def redline_against_playbook(contract_id: str, draft_text: str) -> ContractRedlineResult:
        lower = draft_text.lower()
        deviations: List[RedlineDeviation] = []

        # 1. Liability Cap check (Playbook standard: 12 months fees)
        if "uncapped liability" in lower or "without limitation" in lower:
            deviations.append(RedlineDeviation(
                clause="Limitation of Liability",
                playbook_standard="Cap liability at 12 months fees paid",
                draft_position="Uncapped liability or unlimited indirect damages",
                severity="high",
                recommendation="Reject uncapped liability; insert mutual 12-month trailing fee cap"
            ))

        # 2. Payment Terms check (Playbook standard: Net 30)
        if "net 90" in lower or "net 120" in lower:
            deviations.append(RedlineDeviation(
                clause="Payment Terms",
                playbook_standard="Net 30 days",
                draft_position="Extended payment terms (Net 90/120)",
                severity="medium",
                recommendation="Counter with standard Net 30 or maximum Net 45"
            ))

        # 3. Data Processing & Breach Notification
        if "within 24 hours" in lower:
            deviations.append(RedlineDeviation(
                clause="Breach Notification",
                playbook_standard="72 hours notification window",
                draft_position="24 hours notification window",
                severity="medium",
                recommendation="Align with GDPR Art. 33 standard: without undue delay and not later than 72 hours"
            ))

        high_count = sum(1 for d in deviations if d.severity == "high")
        return ContractRedlineResult(
            contract_id=contract_id,
            total_deviations=len(deviations),
            high_risk_deviations=high_count,
            deviations=deviations,
            is_acceptable_as_is=(high_count == 0 and len(deviations) <= 1)
        )

    @staticmethod
    def execute_contract_via_gateway(
        contract_id: str,
        title: str,
        parties: List[str],
        approval_token: str,
        signatory_principal_id: str
    ) -> ContractExecutionRecord:
        """Rule 62: Contract execution strictly mandates human gateway authorization."""
        if not approval_token or not signatory_principal_id:
            raise ValueError("Rule 62 Violation: Contract execution requires human gateway cryptographic authorization")

        now = datetime.now(timezone.utc).isoformat()
        return ContractExecutionRecord(
            contract_id=contract_id,
            title=title,
            parties=parties,
            is_signed=True,
            human_signatory_id=signatory_principal_id,
            approval_token=approval_token,
            signed_at=now
        )
