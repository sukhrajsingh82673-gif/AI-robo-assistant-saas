"""
Tests for Sub-Step 9H: Status Page, Consented Support Grants, Trust Centre, and CRA Runbook (Rules 82 & 83).
"""

import os
import time
import pytest
from core.status.probe import StatusProbeEngine, ServiceStatus
from core.support.grants import SupportGrantEngine
from core.trust.center import TrustCenter
from core.trust.legal_registry import LegalDocumentRegistry

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep9hStatusSupport:

    def test_status_probe_engine_and_incident_lifecycle(self):
        """Verify independent status probe, overall aggregation, and incident state transitions (Rule 83)."""
        engine = StatusProbeEngine()

        # 1. Default overall operational
        assert engine.get_overall_system_status() == ServiceStatus.OPERATIONAL

        # 2. Degrade one service
        engine.update_service_status("Edge Gateway", ServiceStatus.DEGRADED)
        assert engine.get_overall_system_status() == ServiceStatus.DEGRADED

        # 3. Major outage takes precedence
        engine.update_service_status("Billing & Metering", ServiceStatus.MAJOR_OUTAGE)
        assert engine.get_overall_system_status() == ServiceStatus.MAJOR_OUTAGE

        # 4. Declare and resolve incident
        inc = engine.declare_incident(
            title="Billing Webhook Latency Elevated",
            impact="minor",
            initial_message="Investigating delayed webhook processing.",
        )
        assert inc.status == "investigating"
        assert len(engine.list_active_incidents()) == 1

        resolved = engine.update_incident(inc.incident_id, "resolved", "Root cause identified and mitigation deployed.")
        assert resolved.status == "resolved"
        assert len(engine.list_active_incidents()) == 0

        # 5. Static export
        exported = engine.export_status_json()
        assert "status" in exported
        assert "services" in exported

    def test_support_grant_engine_dual_control_and_rule82_barrier(self):
        """Verify Rule 82: Dual-control consent token, expiration, revocation, and reserved action barrier."""
        engine = SupportGrantEngine(signing_secret="sup_sec_test_vault_key_123")
        tenant_id = "tenant_fintech_corp"
        operator_id = "op_dan_support"
        t0 = 1700000000.0

        # 1. Non-admin/owner cannot issue support grant
        with pytest.raises(PermissionError, match="Requires Owner or Admin"):
            engine.issue_support_grant(
                tenant_id=tenant_id,
                issued_by_user_id="usr_member",
                user_role="Member",
                operator_id=operator_id,
                purpose="Review error logs",
            )

        # 2. Owner issues 1-hour support grant
        grant = engine.issue_support_grant(
            tenant_id=tenant_id,
            issued_by_user_id="usr_owner",
            user_role="Owner",
            operator_id=operator_id,
            purpose="Debug stuck reconciliation queue",
            duration_seconds=3600,
            scope="read_diagnostics",
            current_time=t0,
        )
        assert grant.authorized_operator_id == operator_id
        assert grant.tenant_id == tenant_id

        # 3. Valid access for permitted diagnostic action
        ok1, reason1 = engine.validate_access(
            grant.grant_id, operator_id, tenant_id, "READ_DIAGNOSTICS", current_time=t0 + 100
        )
        assert ok1
        assert "Authorized" in reason1

        # 4. RULE 82 INVIOLABLE BARRIER: Support operator CANNOT perform reserved Owner actions
        for forbidden_action in ("TRANSFER_OWNERSHIP", "UPDATE_BANKING_DETAILS", "APPROVE_MONEY_TRANSFER", "DELETE_COMPANY_DATA"):
            ok_res, reason_res = engine.validate_access(
                grant.grant_id, operator_id, tenant_id, forbidden_action, current_time=t0 + 100
            )
            assert not ok_res
            assert "Rule 82 Violation" in reason_res
            assert "strictly reserved for tenant Owners" in reason_res

        # 5. Expired grant fails
        ok_exp, reason_exp = engine.validate_access(
            grant.grant_id, operator_id, tenant_id, "READ_DIAGNOSTICS", current_time=t0 + 7200
        )
        assert not ok_exp
        assert "expired" in reason_exp

        # 6. Revocation terminates session immediately
        engine.revoke_grant(grant.grant_id, revoked_by_user_id="usr_owner")
        ok_rev, reason_rev = engine.validate_access(
            grant.grant_id, operator_id, tenant_id, "READ_DIAGNOSTICS", current_time=t0 + 200
        )
        assert not ok_rev
        assert "explicitly revoked" in reason_rev

    def test_trust_centre_and_legal_registry(self):
        """Verify Trust Centre compliance card and legal document clickwrap consent tracking."""
        # Trust Centre
        card = TrustCenter.get_trust_card()
        assert len(card["certifications"]) >= 3
        assert any(c["standard"] == "SOC 2 Type II" for c in card["certifications"])
        assert any(sp["name"].startswith("Paddle") for sp in card["sub_processors"])
        assert len(card["data_residency_regions"]) >= 3

        # Legal Registry
        registry = LegalDocumentRegistry()
        assert not registry.has_accepted("tenant_agreed", "tos")

        consent = registry.record_consent(
            tenant_id="tenant_agreed",
            user_id="usr_legal",
            doc_id="tos",
            ip_address="198.51.100.55",
        )
        assert consent.doc_id == "tos"
        assert registry.has_accepted("tenant_agreed", "tos")

    def test_cra_incident_runbook_documented(self):
        """Verify CRA Incident & Vulnerability Handling Runbook exists and covers Article 11."""
        runbook_path = os.path.join(REPO_ROOT, "docs", "security", "CRA_INCIDENT_RUNBOOK.md")
        assert os.path.isfile(runbook_path), "CRA_INCIDENT_RUNBOOK.md must exist"

        with open(runbook_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Cyber Resilience Act" in content
        assert "24-Hour" in content
        assert "CSIRT" in content
        assert "72-Hour" in content
        assert "kill-switch" in content
