"""
Tests for Sub-Step 9G: Mobile PWA, Approval Guard, and WCAG 2.2 AA Accessibility (ADR 0054 & ADR 0057).
"""

import os
import json
import pytest
from core.ui.mobile_approvals import MobileApprovalService
from core.ui.accessibility_checker import AccessibilityChecker

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep9gMobileAccessibility:

    def test_pwa_manifest_and_service_worker_exist(self):
        """Verify Web App Manifest and Service Worker conform to PWA standards."""
        manifest_path = os.path.join(REPO_ROOT, "web", "pwa", "manifest.json")
        sw_path = os.path.join(REPO_ROOT, "web", "pwa", "sw.js")

        assert os.path.isfile(manifest_path), "web/pwa/manifest.json must exist"
        assert os.path.isfile(sw_path), "web/pwa/sw.js must exist"

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest.get("name") == "ZONATA AI Autonomous Company Operating System"
        assert manifest.get("short_name") == "ZONATA"
        assert manifest.get("display") == "standalone"
        assert manifest.get("start_url") == "/mobile"
        assert len(manifest.get("icons", [])) >= 2
        assert len(manifest.get("shortcuts", [])) >= 2

        with open(sw_path, "r", encoding="utf-8") as f:
            sw_code = f.read()

        assert "self.addEventListener('install'" in sw_code
        assert "self.addEventListener('fetch'" in sw_code
        assert "self.addEventListener('push'" in sw_code

    def test_mobile_approvals_offline_guard_and_passkey_enforcement(self):
        """Verify high-risk passkey requirement and offline read-only mutation block."""
        service = MobileApprovalService(tenant_id="tenant_pwa_client")

        # 1. Standard low-value ticket ($50.00 / 5000 cents)
        t_low = service.create_approval_ticket(
            department="marketing",
            title="Sponsor local developer meetup",
            amount_cents=5000,
            requested_by="ag_marketing_01",
            details={},
        )
        assert not service._tickets[t_low]["requires_passkey"]

        # Low value succeeds without passkey
        ok1, reason1, item1 = service.submit_decision(t_low, user_id="usr_cmo", approved=True)
        assert ok1
        assert item1["status"] == "APPROVED"

        # 2. High-value ticket ($25,000 / 2,500,000 cents >= $10,000 threshold)
        t_high = service.create_approval_ticket(
            department="finance",
            title="Wire vendor server cluster prepayment",
            amount_cents=2_500_000,
            requested_by="ag_cfo_01",
            details={"vendor": "Equinix"},
        )
        assert service._tickets[t_high]["requires_passkey"]

        # High value fails without passkey
        ok_no_pass, reason_no_pass, _ = service.submit_decision(t_high, user_id="usr_cfo", approved=True)
        assert not ok_no_pass
        assert "requires biometric Passkey" in reason_no_pass

        # High value fails with invalid passkey
        ok_bad_pass, reason_bad_pass, _ = service.submit_decision(
            t_high, user_id="usr_cfo", approved=True, passkey_signature="invalid_signature"
        )
        assert not ok_bad_pass
        assert "verification failed" in reason_bad_pass

        # High value succeeds with valid passkey
        ok_good_pass, _, item_high = service.submit_decision(
            t_high, user_id="usr_cfo", approved=True, passkey_signature="webauthn_valid_attestation_sig"
        )
        assert ok_good_pass
        assert item_high["status"] == "APPROVED"

        # 3. Offline mutation guard: attempting mutation while offline is blocked
        t_offline = service.create_approval_ticket("legal", "Approve NDA", 0, "ag_legal", {})
        ok_off, reason_off, _ = service.submit_decision(t_offline, user_id="usr_gc", approved=True, is_offline=True)
        assert not ok_off
        assert "Cannot approve mutations in offline mode" in reason_off

    def test_accessibility_checker_compliant_and_mutation_detection(self):
        """Verify AccessibilityChecker passes valid HTML and detects WCAG 2.2 AA violations."""
        # 1. Compliant template
        valid_html = """
        <header role="banner">
            <h1>ZONATA Mobile Console</h1>
        </header>
        <main role="main">
            <img src="/icons/logo.png" alt="ZONATA Logo" id="logo_img" />
            <form>
                <label for="tenant_name_input">Company Name</label>
                <input type="text" id="tenant_name_input" />
                <button type="submit" id="btn_submit">Save Changes</button>
            </form>
        </main>
        """
        report = AccessibilityChecker.audit_html_template(valid_html)
        assert report.is_compliant_wcag_22_aa is True
        assert len(report.violations) == 0

        # 2. Mutation: Missing img alt
        bad_img_html = '<img src="/icon.png" id="avatar" />'
        r_img = AccessibilityChecker.audit_html_template(bad_img_html)
        assert not r_img.is_compliant_wcag_22_aa
        assert any(v.rule_id == "img-alt-required" for v in r_img.violations)

        # 3. Mutation: Unlabelled form input
        bad_input_html = '<input type="text" id="secret_input" />'
        r_input = AccessibilityChecker.audit_html_template(bad_input_html)
        assert not r_input.is_compliant_wcag_22_aa
        assert any(v.rule_id == "input-label-required" for v in r_input.violations)

        # 4. Mutation: Custom button lacking keyboard tabindex
        bad_btn_html = '<div role="button" id="custom_btn">Click Me</div>'
        r_btn = AccessibilityChecker.audit_html_template(bad_btn_html)
        assert not r_btn.is_compliant_wcag_22_aa
        assert any(v.rule_id == "custom-button-keyboard-focusable" for v in r_btn.violations)

        # 5. VPAT ACR documentation exists
        vpat_path = os.path.join(REPO_ROOT, "docs", "accessibility", "DRAFT_ACR_VPAT.md")
        assert os.path.isfile(vpat_path), "DRAFT_ACR_VPAT.md must exist"
