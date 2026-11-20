"""Unit & Integration Tests for Stage 6: Real Adapters & Global Packs.

Verifies:
- Law L9: Real and sandboxed adapters for outside services.
- SandboxedPaymentAdapter: Idempotency enforcement and Merkle evidence sealing.
- TransactionalEmailAdapter: Secure delivery without credential exposure.
- CorporateCalendarAdapter: Conflict detection engine.
- EnterpriseCRMAdapter: Contact deduplication and persistence.
- S3CompatibleStorageAdapter: Upload, hash digest verification, and retrieval.
- RegionalComplianceEngine:
  - India GST (Intra-state CGST+SGST vs Inter-state IGST in INR)
  - US Sales Tax (State nexus calculation in USD)
  - DPDP 2023 Consent & Purpose Limitation validation
  - HIPAA PHI Data Sanitization
"""

import time
import pytest
from core.adapters.providers import (
    SandboxedPaymentAdapter,
    TransactionalEmailAdapter,
    CorporateCalendarAdapter,
    EnterpriseCRMAdapter,
    S3CompatibleStorageAdapter,
)
from core.region_packs.engine import RegionalComplianceEngine
from agent_factory.adapters.zonata import ZonataEvidenceAdapter


@pytest.fixture
def payment_adapter():
    adapter = ZonataEvidenceAdapter()
    return SandboxedPaymentAdapter(evidence_port=adapter)


@pytest.fixture
def compliance_engine():
    return RegionalComplianceEngine()


def test_stage6_payment_idempotency_and_evidence(payment_adapter):
    """Verify payment adapter guarantees idempotency and seals Merkle evidence."""
    tenant = "tnt_stage6"
    company = "comp_stage6"
    idempotency_key = "idemp_order_99812_charge"

    # Transaction 1: Process initial charge
    res1 = payment_adapter.process_charge(
        tenant_id=tenant,
        company_id=company,
        amount=2500.0,
        currency="USD",
        customer_id="cust_corp_44",
        idempotency_key=idempotency_key
    )
    assert res1.success
    assert res1.status == "SETTLED"
    assert res1.evidence_id is not None
    assert res1.evidence_id.startswith("EV-")

    # Transaction 2: Exact duplicate call with same idempotency key
    res2 = payment_adapter.process_charge(
        tenant_id=tenant,
        company_id=company,
        amount=2500.0,
        currency="USD",
        customer_id="cust_corp_44",
        idempotency_key=idempotency_key
    )
    # Must return same transaction without generating double charge
    assert res2.success
    assert res2.transaction_id == res1.transaction_id
    assert res2.metadata.get("cached") is True


def test_stage6_email_and_calendar_adapters():
    """Verify transactional email sink and calendar conflict detection."""
    email_adapter = TransactionalEmailAdapter()
    calendar_adapter = CorporateCalendarAdapter()

    # Email delivery
    res = email_adapter.send_email(
        tenant_id="tnt_6",
        company_id="comp_6",
        to_address="procurement@partner.com",
        subject="Signed Order Confirmation",
        body_text="Your contract has been fully executed."
    )
    assert res.delivered
    assert len(email_adapter.sent_mailbox) == 1
    assert email_adapter.sent_mailbox[0]["to"] == "procurement@partner.com"

    # Calendar scheduling & conflict detection
    now = time.time()
    evt1 = calendar_adapter.create_event(
        tenant_id="tnt_6",
        company_id="comp_6",
        title="Q3 Strategy Review",
        start_time=now + 3600,
        end_time=now + 7200,
        organizer="ceo@zonata.com",
        attendees=["cfo@zonata.com", "coo@zonata.com"]
    )
    assert evt1.event_id is not None

    # Check conflict for overlapping meeting with cfo
    conflicts = calendar_adapter.check_conflict(
        tenant_id="tnt_6",
        company_id="comp_6",
        attendees=["cfo@zonata.com"],
        start_time=now + 5000,
        end_time=now + 8000
    )
    assert len(conflicts) > 0
    assert "Conflict for cfo@zonata.com" in conflicts[0]


def test_stage6_crm_deduplication_and_s3_storage():
    """Verify CRM contact deduplication and S3-compatible storage engine."""
    crm = EnterpriseCRMAdapter()
    storage = S3CompatibleStorageAdapter(local_base_path="storage/test_vault")

    # CRM Upsert 1
    c1 = crm.upsert_contact(
        tenant_id="tnt_crm",
        company_id="comp_crm",
        email="CTO@EnterpriseCorp.com",
        name="John Doe",
        company_name="Enterprise Corp"
    )
    assert c1.email == "cto@enterprisecorp.com"

    # CRM Upsert 2 (same normalized email, updated name)
    c2 = crm.upsert_contact(
        tenant_id="tnt_crm",
        company_id="comp_crm",
        email="cto@enterprisecorp.com",
        name="Jonathan Doe",
        company_name="Enterprise Corp Inc"
    )
    assert c2.contact_id == c1.contact_id
    assert c2.name == "Jonathan Doe"

    # Storage upload & download
    payload = b"ZONATA Enterprise Master Blueprint v2 Artifact"
    obj = storage.upload_object(
        tenant_id="tnt_storage",
        bucket="releases",
        key="blueprint.bin",
        data=payload
    )
    assert obj.size_bytes == len(payload)
    assert obj.sha256_hash is not None

    downloaded = storage.download_object(tenant_id="tnt_storage", bucket="releases", key="blueprint.bin")
    assert downloaded == payload


def test_stage6_regional_india_gst_and_dpdp(compliance_engine):
    """Verify India Region Pack: GST tax calculation and DPDP 2023 consent validation."""
    # Test 1: Intra-state GST (9% CGST + 9% SGST = 18%)
    gst_intra = compliance_engine.calculate_tax(
        region_code="india",
        amount=10000.0,
        context={"is_inter_state": False}
    )
    assert gst_intra.currency == "INR"
    assert gst_intra.tax_amount == 1800.0
    assert gst_intra.total_amount == 11800.0
    assert gst_intra.tax_breakdown == {"CGST": 900.0, "SGST": 900.0}

    # Test 2: Inter-state GST (18% IGST)
    gst_inter = compliance_engine.calculate_tax(
        region_code="india",
        amount=10000.0,
        context={"is_inter_state": True}
    )
    assert gst_inter.tax_amount == 1800.0
    assert gst_inter.tax_breakdown == {"IGST": 1800.0}

    # Test 3: DPDP compliance check
    dpdp_res = compliance_engine.validate_dpdp_compliance({
        "consent_granted": True,
        "purpose_specified": "Employee payroll and insurance coverage",
        "data_fiduciary_id": "FID-IN-98102"
    })
    assert dpdp_res["compliant"] is True


def test_stage6_regional_us_sales_tax_and_hipaa(compliance_engine):
    """Verify US Region Pack: State sales tax and HIPAA PHI redaction."""
    # Test 1: California Sales Tax (7.25%)
    us_tax_ca = compliance_engine.calculate_tax(
        region_code="us",
        amount=1000.0,
        context={"state": "CA"}
    )
    assert us_tax_ca.currency == "USD"
    assert us_tax_ca.tax_amount == 72.50
    assert us_tax_ca.total_amount == 1072.50

    # Test 2: Texas Sales Tax (6.25%)
    us_tax_tx = compliance_engine.calculate_tax(
        region_code="us",
        amount=1000.0,
        context={"state": "TX"}
    )
    assert us_tax_tx.tax_amount == 62.50

    # Test 3: HIPAA PHI Sanitization
    unclean_text = "Patient John Smith SSN 123-45-6789 with MRN 981245 contacted doctor at 415-555-1234."
    clean_text, count = compliance_engine.sanitize_hipaa_phi(unclean_text)
    assert count == 3
    assert "[REDACTED-SSN]" in clean_text
    assert "[REDACTED-MRN]" in clean_text
    assert "[REDACTED-PHONE]" in clean_text
    assert "123-45-6789" not in clean_text
