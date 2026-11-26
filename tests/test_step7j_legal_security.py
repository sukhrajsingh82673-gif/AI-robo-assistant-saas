"""
Unit & Contract Tests for Step 7J: Legal, Compliance, IT & Security Depth.
==========================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.legal.contract_engine import ContractEngine
from core.compliance.policy_mapping import ComplianceMappingManager
from core.it_security.asset_inventory import ITAsset, AssetInventoryManager
from core.it_security.vuln_tracker import VulnerabilityTracker
from core.it_security.posture_scanner import DomainPostureScanner


# --- 1. CONTRACT OBLIGATIONS & REDLINE TESTS ---

def test_01_contract_obligation_extraction():
    sample_text = (
        "This Master Services Agreement is entered into between Acme Cloud Inc and Zonata Solutions India Pvt Ltd, "
        "effective as of 2026-04-01. Customer may terminate by providing 60 days prior written notice of non-renewal. "
        "Each party's aggregate liability shall be capped at fees paid in the preceding twelve months. "
        "This Agreement is governed by the laws of India. Provider guarantees 99.95% uptime availability. "
        "In the event of a security incident or breach within 72 hours, provider shall notify customer."
    )
    ob = ContractEngine.extract_obligations("CTR-001", sample_text)
    assert "Acme Cloud Inc" in ob.parties
    assert ob.effective_date == "2026-04-01"
    assert ob.auto_renewal_notice_days == 60
    assert ob.liability_cap_description == "12_MONTHS_FEES"
    assert ob.governing_law == "India"
    assert ob.sla_availability_pct == 99.95
    assert ob.breach_notification_window_hours == 72


def test_02_contract_redline_and_human_gateway_gate():
    risky_draft = (
        "Vendor agrees to uncapped liability for all direct and indirect damages. "
        "Customer shall remit payment under Net 90 terms. "
        "Vendor shall notify customer of any breach within 24 hours."
    )
    redline = ContractEngine.redline_against_playbook("CTR-002", risky_draft)
    assert redline.is_acceptable_as_is is False
    assert redline.high_risk_deviations >= 1
    clauses = {d.clause for d in redline.deviations}
    assert "Limitation of Liability" in clauses
    assert "Payment Terms" in clauses

    # Rule 62: Contract execution without gateway approval MUST fail
    with pytest.raises(ValueError):
        ContractEngine.execute_contract_via_gateway(
            "CTR-002", "MSA", ["Acme", "Zonata"],
            approval_token="", signatory_principal_id=""
        )

    # Execution with verified human gateway authorization succeeds
    signed = ContractEngine.execute_contract_via_gateway(
        "CTR-002", "MSA", ["Acme", "Zonata"],
        approval_token="GATEWAY-LEGAL-SIG-7788",
        signatory_principal_id="general_counsel_principal"
    )
    assert signed.is_signed is True
    assert signed.approval_token == "GATEWAY-LEGAL-SIG-7788"


# --- 2. COMPLIANCE CONTROLS MAPPING TESTS ---

def test_03_compliance_policy_mapping():
    mgr = ComplianceMappingManager()

    # SOC 2 evaluation
    soc2_res = mgr.evaluate_framework_compliance("SOC2")
    assert soc2_res["total_controls"] >= 2
    assert soc2_res["compliance_rate"] == 1.0

    # GDPR evaluation
    gdpr_res = mgr.evaluate_framework_compliance("GDPR")
    assert gdpr_res["compliance_rate"] == 1.0
    assert any(e.control_id == "Art.32" and e.evidence_status == "PASSED" for e in gdpr_res["evidences"])

    # India DPDP Act evaluation
    dpdp_res = mgr.evaluate_framework_compliance("DPDP")
    assert dpdp_res["compliance_rate"] == 1.0


# --- 3. IT ASSET INVENTORY & EXPIRATION CLOCK TESTS ---

def test_04_it_asset_inventory_expiry_alerts():
    mgr = AssetInventoryManager()
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Certificate expiring in 5 days (Critical Alert)
    cert_expiry = (now + timedelta(days=5)).isoformat()
    mgr.register_asset(ITAsset(
        asset_id="ASSET-CERT-1",
        tenant_id="t1",
        company_id="c1",
        asset_type="tls_certificate",
        name="api.zonata.io Wildcard TLS",
        identifier="CN=*.zonata.io",
        assigned_owner="devops_lead",
        expires_at=cert_expiry
    ))

    # SaaS subscription expiring in 20 days (Info Alert)
    saas_expiry = (now + timedelta(days=20)).isoformat()
    mgr.register_asset(ITAsset(
        asset_id="ASSET-SAAS-1",
        tenant_id="t1",
        company_id="c1",
        asset_type="saas_subscription",
        name="GitHub Enterprise",
        identifier="gh-org-sub-99",
        assigned_owner="it_admin",
        expires_at=saas_expiry
    ))

    alerts = mgr.check_expirations(current_time=now)
    assert len(alerts) == 2
    cert_alert = next(a for a in alerts if a.asset_id == "ASSET-CERT-1")
    assert cert_alert.urgency == "critical"
    assert cert_alert.days_until_expiry == 5


# --- 4. VULNERABILITY TRACKER & REMEDIATION SLAS ---

def test_05_cve_remediation_sla_tracking():
    tracker = VulnerabilityTracker()
    now = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Critical CVE: CVSS 9.8 -> 24h SLA
    crit_vuln = tracker.register_vulnerability(
        cve_id="CVE-2026-4444",
        affected_package="openssl",
        cvss_score=9.8,
        discovered_at=now.isoformat()
    )
    assert crit_vuln.severity == "critical"
    assert crit_vuln.remediation_sla_hours == 24

    # Check status 10 hours later: within SLA
    t_10h = now + timedelta(hours=10)
    status_10, rem_10 = tracker.evaluate_sla_status(crit_vuln, current_time=t_10h)
    assert status_10 == "within_sla"
    assert rem_10 == 14.0

    # Check status 26 hours later: breached SLA
    t_26h = now + timedelta(hours=26)
    status_26, overdue_hrs = tracker.evaluate_sla_status(crit_vuln, current_time=t_26h)
    assert status_26 == "breached"
    assert overdue_hrs == 2.0


# --- 5. PASSIVE DOMAIN POSTURE SCANNER TESTS ---

def test_06_passive_domain_posture_scanner():
    dns_compliant = {
        "SPF": "v=spf1 include:_spf.google.com -all",
        "DMARC": "v=DMARC1; p=reject; rua=mailto:dmarc@zonata.io"
    }
    headers_compliant = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "X-Content-Type-Options": "nosniff"
    }

    res = DomainPostureScanner.audit_dns_and_headers("zonata.io", dns_compliant, headers_compliant)
    assert res.overall_posture == "GRADE_A"
    assert res.passed_count == 5

    # Failing posture: missing DMARC and security headers
    res_fail = DomainPostureScanner.audit_dns_and_headers("insecure.org", {}, {})
    assert res_fail.overall_posture == "FAIL"
    assert res_fail.passed_count == 0
