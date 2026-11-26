"""
Vulnerability Tracking & CVE Remediation SLA Engine
===================================================
CVSS v3.1 Severity Scoring and Remediation SLAs:
- Critical (CVSS >= 9.0): 24 hours SLA
- High (7.0 <= CVSS < 9.0): 7 days (168h) SLA
- Medium (4.0 <= CVSS < 7.0): 30 days (720h) SLA
- Low (CVSS < 4.0): 90 days (2160h) SLA
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


class Vulnerability(BaseModel):
    cve_id: str
    affected_package: str
    cvss_score: float = Field(..., ge=0.0, le=10.0)
    severity: str
    remediation_sla_hours: int
    discovered_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    remediated_at: Optional[str] = None
    status: str = "open"  # 'open', 'in_remediation', 'remediated', 'risk_accepted'


class VulnerabilityTracker:
    """Classifies vulnerabilities, assigns SLAs, and checks for breaches."""

    @staticmethod
    def classify_severity(cvss_score: float) -> Tuple[str, int]:
        if cvss_score >= 9.0:
            return "critical", 24
        elif cvss_score >= 7.0:
            return "high", 168
        elif cvss_score >= 4.0:
            return "medium", 720
        else:
            return "low", 2160

    def register_vulnerability(self, cve_id: str, affected_package: str, cvss_score: float, discovered_at: Optional[str] = None) -> Vulnerability:
        severity, sla_hrs = self.classify_severity(cvss_score)
        disc = discovered_at or datetime.now(timezone.utc).isoformat()
        return Vulnerability(
            cve_id=cve_id,
            affected_package=affected_package,
            cvss_score=cvss_score,
            severity=severity,
            remediation_sla_hours=sla_hrs,
            discovered_at=disc,
            status="open"
        )

    def evaluate_sla_status(self, vuln: Vulnerability, current_time: Optional[datetime] = None) -> Tuple[str, float]:
        """Evaluates remaining hours and whether the SLA has breached."""
        if vuln.status == "remediated":
            return "remediated", 0.0

        now = current_time or datetime.now(timezone.utc)
        disc_dt = datetime.fromisoformat(vuln.discovered_at)
        deadline = disc_dt + timedelta(hours=vuln.remediation_sla_hours)

        remaining_hours = (deadline - now).total_seconds() / 3600.0

        if remaining_hours < 0:
            return "breached", round(abs(remaining_hours), 2)
        return "within_sla", round(remaining_hours, 2)
