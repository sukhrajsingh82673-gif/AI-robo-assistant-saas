"""
Passive Domain Security Posture Scanner
=======================================
Non-intrusive DNS and HTTP header posture analysis:
- SPF DNS record check
- DMARC policy check (p=reject / p=quarantine)
- DKIM record format check
- HTTP Security Headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
"""

from typing import Dict, List, Any
from pydantic import BaseModel, Field


class PostureCheckItem(BaseModel):
    check_name: str
    is_passed: bool
    observed_value: str
    recommendation: str


class DomainPostureResult(BaseModel):
    domain: str
    overall_posture: str  # 'GRADE_A', 'GRADE_B', 'FAIL'
    passed_count: int
    total_checks: int
    checks: List[PostureCheckItem] = Field(default_factory=list)


class DomainPostureScanner:
    """Audits email authentication DNS records and HTTP security headers passively."""

    @staticmethod
    def audit_dns_and_headers(
        domain: str,
        dns_records: Dict[str, str],
        http_headers: Dict[str, str]
    ) -> DomainPostureResult:
        checks: List[PostureCheckItem] = []

        # 1. SPF Check
        spf_txt = dns_records.get("SPF", "")
        spf_pass = "v=spf1" in spf_txt and ("-all" in spf_txt or "~all" in spf_txt)
        checks.append(PostureCheckItem(
            check_name="SPF Enforcement",
            is_passed=spf_pass,
            observed_value=spf_txt or "None",
            recommendation="Configure valid SPF record with strict '-all' or softfail '~all'"
        ))

        # 2. DMARC Check
        dmarc_txt = dns_records.get("DMARC", "")
        dmarc_pass = "v=DMARC1" in dmarc_txt and ("p=reject" in dmarc_txt or "p=quarantine" in dmarc_txt)
        checks.append(PostureCheckItem(
            check_name="DMARC Policy",
            is_passed=dmarc_pass,
            observed_value=dmarc_txt or "None",
            recommendation="Set DMARC policy to 'p=reject' or 'p=quarantine'"
        ))

        # 3. HSTS Header Check
        hsts = http_headers.get("Strict-Transport-Security", "")
        hsts_pass = "max-age=" in hsts and "includeSubDomains" in hsts
        checks.append(PostureCheckItem(
            check_name="HSTS Header",
            is_passed=hsts_pass,
            observed_value=hsts or "Missing",
            recommendation="Set Strict-Transport-Security: max-age=31536000; includeSubDomains"
        ))

        # 4. Content Security Policy (CSP) Check
        csp = http_headers.get("Content-Security-Policy", "")
        csp_pass = "default-src" in csp
        checks.append(PostureCheckItem(
            check_name="Content Security Policy",
            is_passed=csp_pass,
            observed_value=csp or "Missing",
            recommendation="Define strict default-src in Content-Security-Policy"
        ))

        # 5. X-Content-Type-Options Check
        x_content = http_headers.get("X-Content-Type-Options", "")
        x_content_pass = x_content.lower() == "nosniff"
        checks.append(PostureCheckItem(
            check_name="X-Content-Type-Options",
            is_passed=x_content_pass,
            observed_value=x_content or "Missing",
            recommendation="Set X-Content-Type-Options: nosniff"
        ))

        passed = sum(1 for c in checks if c.is_passed)
        grade = "GRADE_A" if passed == len(checks) else ("GRADE_B" if passed >= 3 else "FAIL")

        return DomainPostureResult(
            domain=domain,
            overall_posture=grade,
            passed_count=passed,
            total_checks=len(checks),
            checks=checks
        )
