"""
ZONATA Sovereign Core — Sub-Step 5F: Audit, Privacy & Compliance Test Suite.
============================================================================
Verifies:
- Merkle audit log hash-chaining and tamper detection.
- Micro Focus Common Event Format (CEF) emission.
- Data Subject Access Request (DSAR) bundle generation (GDPR Art. 15 / DPDP).
- Crypto-shredding key destruction (Right to Erasure / GDPR Art. 17).
- Statutory 72-hour regulatory breach notification reporting (GDPR Art. 33).
- Rule 46: Ban on unverified compliance marketing claims (grep linter & mutation checks).
"""

import time
import pytest

from core.audit.siem_exporter import (
    AuditChainTamperedError,
    AuditEvent,
    SIEMExporter,
)
from core.privacy.dsar import (
    BreachNotificationCoordinator,
    BreachNotificationReport,
    CryptoShredder,
    DSARManager,
    DSARPackage,
)
from core.compliance.control_matrix import (
    ControlMatrixGenerator,
    Rule46ClaimViolation,
)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestAuditPrivacyCompliance:

    def test_01_audit_event_hash_chaining_and_tamper_detection(self):
        """Verifies linear SHA-256 hash chaining and tamper detection."""
        exporter = SIEMExporter()

        evt1 = exporter.log_event(
            actor_id="usr_admin_1",
            actor_role="EXECUTIVE",
            tenant_id="ten_alpha",
            company_id="cmp_alpha",
            action="SECRET_ROTATED",
            target_resource="openbao://transit/keys/db_key",
            status="SUCCESS",
            details={"key": "db_key", "version": 2},
        )

        evt2 = exporter.log_event(
            actor_id="usr_admin_2",
            actor_role="AUDITOR",
            tenant_id="ten_alpha",
            company_id="cmp_alpha",
            action="AUDIT_INSPECTED",
            target_resource="core/evidence_ledger",
            status="SUCCESS",
        )

        events = exporter.get_events()
        assert len(events) == 2
        assert events[0].prev_event_hash == SIEMExporter.GENESIS_HASH
        assert events[1].prev_event_hash == events[0].event_hash
        assert SIEMExporter.verify_chain(events) is True

        # Mutation: Alter event 1 payload
        events[0].action = "MALICIOUS_TAMPER"
        with pytest.raises(AuditChainTamperedError, match="hash altered"):
            SIEMExporter.verify_chain(events)

    def test_02_cef_log_formatting(self):
        """Emits standard Micro Focus Common Event Format (CEF:0) strings."""
        exporter = SIEMExporter()
        evt = exporter.log_event(
            actor_id="usr_ops_1",
            actor_role="OPERATOR",
            tenant_id="ten_beta",
            company_id="cmp_beta",
            action="AGENT_DISPATCHED",
            target_resource="agent://temporal/payroll_agent",
            status="SUCCESS",
            evidence_id="ev_pkg_987",
            details={"run_id": "run_123"},
        )

        cef = evt.to_cef()
        assert cef.startswith("CEF:0|ZONATA|SovereignOS|1.0|AGENT_DISPATCHED|AGENT_DISPATCHED|3|")
        assert "src=usr_ops_1" in cef
        assert "srole=OPERATOR" in cef
        assert "cs1=ten_beta" in cef
        assert "cs3=ev_pkg_987" in cef
        assert "outcome=SUCCESS" in cef

    def test_03_dsar_export_bundle_generation(self):
        """Generates portable, verifiable DSAR package for data subject."""
        manager = DSARManager()

        identity_info = {"user_id": "usr_john_doe", "email": "john@corp.com", "mfa": True}
        activities = [{"action": "login", "time": time.time() - 3600}]
        consents = [{"purpose": "ai_inference", "granted": True, "time": time.time() - 86400}]

        pkg = manager.generate_export_bundle(
            user_id="usr_john_doe",
            tenant_id="ten_gamma",
            identity_record=identity_info,
            activity_records=activities,
            consent_records=consents,
        )

        assert pkg.user_id == "usr_john_doe"
        assert pkg.tenant_id == "ten_gamma"
        assert len(pkg.package_sha256) == 64
        assert "identity" in pkg.data_categories
        assert pkg.records["identity"]["email"] == "john@corp.com"

    def test_04_crypto_shredding_erasure(self):
        """Right to Erasure via cryptographic shredding of tenant Transit keys."""
        shredder = CryptoShredder()
        receipt = shredder.shred_tenant_data("ten_to_shred", reason="DPDP Right to Erasure")
        assert receipt["status"] == "SHREDDED"
        assert receipt["tenant_id"] == "ten_to_shred"
        assert "provider_ref" in receipt

    def test_05_breach_notification_report(self):
        """Generates 72-hour statutory regulatory breach notification reports."""
        coord = BreachNotificationCoordinator()
        discovered_time = 1700000000.0

        report = coord.generate_notification(
            incident_id="inc_sec_2026_01",
            discovered_at=discovered_time,
            affected_tenants=["ten_omega"],
            compromised_categories=["financial_records"],
            root_cause="Third-party vendor compromise",
        )

        assert report.incident_id == "inc_sec_2026_01"
        assert report.statutory_deadline_at == discovered_time + (72.0 * 3600.0)
        assert report.regulator_notice_ready is True
        assert len(report.remediation_actions) >= 3

    def test_06_control_matrix_generation_and_rule46_verification(self):
        """Generates CONTROL_MATRIX.md and verifies compliance with Rule 46."""
        md = ControlMatrixGenerator.generate_markdown()
        assert "# ZONATA Sovereign OS — Security Controls & Implementation Matrix" in md
        assert "ISO-27001" in md
        assert "SOC2" in md
        assert "HIPAA" in md
        assert "DPDP" in md
        assert "GDPR" in md
        assert "IMPLEMENTED_CONTROL" in md

        # Linter passes on honest control matrix
        ControlMatrixGenerator.verify_rule_46(md)

    def test_07_mutation_check_rule_46_banned_claims_flagged(self):
        """Mutation Check (Rule 8 & 46): Disallowed claims like '100% compliant' must be rejected."""
        tainted_claim_1 = "Our solution is 100% compliant with SOC 2 requirements."
        with pytest.raises(Rule46ClaimViolation, match="Rule 46 Violation.*100% compliant"):
            ControlMatrixGenerator.verify_rule_46(tainted_claim_1)

        tainted_claim_2 = "This architecture is certified secure by internal engineers."
        with pytest.raises(Rule46ClaimViolation, match="Rule 46 Violation.*certified secure"):
            ControlMatrixGenerator.verify_rule_46(tainted_claim_2)

        tainted_claim_3 = "Guaranteed compliant with all regulatory frameworks."
        with pytest.raises(Rule46ClaimViolation, match="Rule 46 Violation.*Guaranteed compliant"):
            ControlMatrixGenerator.verify_rule_46(tainted_claim_3)
