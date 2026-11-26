"""
Tests for Sub-Step 9E: Consoles & Dead-Control Detector (Rules 82 & 84).
"""

import time
import pytest
from core.ui.dead_control_detector import (
    DeadControlDetector,
    ControlElement,
)
from core.ui.tenant_console import TenantAdminConsole
from core.ui.operator_console import PlatformOperatorConsole


class TestStep9eConsoles:

    def test_tenant_admin_console_team_and_keys(self):
        """Verify TenantAdminConsole member management, API key lifecycle, and owner protection."""
        console = TenantAdminConsole(tenant_id="tenant_acme")

        # 1. Invite team member
        inv = console.invite_member("dev@acme.corp", "Admin", actor_id="usr_owner")
        assert inv["role"] == "Admin"
        dev_id = inv["user_id"]

        # 2. Change role
        updated = console.change_member_role(dev_id, "Auditor", actor_id="usr_owner")
        assert updated["role"] == "Auditor"

        # 3. Last owner protection: Demoting last owner must fail
        with pytest.raises(ValueError, match="Cannot demote the last remaining Owner"):
            console.change_member_role("usr_owner", "Member", actor_id="usr_owner")

        # 4. API Key issuance and revocation
        key_res = console.create_api_key("ci-runner-key", ["tasks:read", "tasks:write"], actor_id="usr_owner")
        assert key_res["api_key"].startswith("zn_key_")
        key_id = key_res["key_id"]

        rev_res = console.revoke_api_key(key_id, actor_id="usr_owner")
        assert rev_res["status"] == "REVOKED"
        assert console.api_keys[key_id]["revoked"] is True

        # 5. Telemetry opt-in toggle (Rule 84 & ADR 0056)
        assert not console.telemetry_opt_in
        console.set_telemetry_opt_in(True, actor_id="usr_owner")
        assert console.telemetry_opt_in is True

        # 6. Audit trail exists
        assert len(console.audit_log) >= 5

    def test_platform_operator_console_dual_control_support_access(self):
        """Verify Rule 82: Operators cannot access tenant data without tenant-consented grant."""
        operator = PlatformOperatorConsole()
        op_id = "op_dan_security"
        tenant_id = "tenant_enterprise_finance"
        t0 = 1700000000.0

        # 1. Access without grant is strictly DENIED
        ok1, reason1, _ = operator.access_tenant_diagnostics(op_id, tenant_id, "nonexistent_grant", current_time=t0)
        assert not ok1
        assert "No valid dual-control support grant" in reason1

        # 2. Tenant registers dual-control grant (valid for 1 hour)
        grant_id = "grant_sup_99"
        operator.register_support_grant(
            tenant_id=tenant_id,
            grant_id=grant_id,
            authorized_operator_id=op_id,
            purpose="Debug stuck reconciliation queue",
            expires_at=t0 + 3600,
        )

        # 3. Access with valid grant SUCCEEDS
        ok2, reason2, diag2 = operator.access_tenant_diagnostics(op_id, tenant_id, grant_id, current_time=t0)
        assert ok2
        assert "Access granted" in reason2
        assert diag2["tenant_id"] == tenant_id

        # 4. Access past expiration FAILS
        ok3, reason3, _ = operator.access_tenant_diagnostics(op_id, tenant_id, grant_id, current_time=t0 + 7200)
        assert not ok3
        assert "expired" in reason3

        # 5. Revoked grant FAILS
        operator._support_grants[grant_id]["revoked"] = True
        ok4, reason4, _ = operator.access_tenant_diagnostics(op_id, tenant_id, grant_id, current_time=t0 + 100)
        assert not ok4
        assert "revoked" in reason4

    def test_dead_control_detector_on_console_manifests(self):
        """Verify DeadControlDetector verifies UI controls and flags dead elements (Rule 84)."""
        registered_routes = [
            "/api/console/members/invite",
            "/api/console/keys/create",
            "/api/console/keys/rotate",
            "/api/console/billing/upgrade",
            "/api/console/billing/invoices",
            "/api/console/settings/telemetry",
            "/api/console/sso/saml",
            "/api/operator/tenants/list",
            "/api/operator/flags/killswitch",
            "/api/operator/workers/drain",
            "/api/operator/metrics",
        ]
        detector = DeadControlDetector(registered_api_routes=registered_routes)

        # 1. Audit Tenant Admin Console controls
        tenant_console = TenantAdminConsole("tenant_acme")
        t_controls = tenant_console.get_console_controls_manifest()
        t_audit = detector.audit_controls(t_controls)
        assert t_audit.is_compliant
        assert t_audit.honest_not_implemented_controls == 1  # SAML SSO marked NOT_IMPLEMENTED
        assert len(t_audit.dead_controls) == 0

        # 2. Audit Platform Operator Console controls
        op_console = PlatformOperatorConsole()
        op_controls = op_console.get_console_controls_manifest()
        op_audit = detector.audit_controls(op_controls)
        assert op_audit.is_compliant
        assert len(op_audit.dead_controls) == 0

        # 3. Mutation test: Inject prohibited '#' dead link
        corrupted_controls = list(t_controls) + [
            ControlElement("a", "dead_link_01", "Secret Settings", "href", "#")
        ]
        fail_audit1 = detector.audit_controls(corrupted_controls)
        assert not fail_audit1.is_compliant
        assert len(fail_audit1.dead_controls) == 1
        assert "Prohibited dummy href target '#'" in fail_audit1.dead_controls[0]["error"]

        # 4. Mutation test: Inject button pointing to dead unregistered route
        corrupted_controls2 = list(t_controls) + [
            ControlElement("button", "btn_dead_api", "Purge System", "api_call", "/api/console/ghost_route")
        ]
        fail_audit2 = detector.audit_controls(corrupted_controls2)
        assert not fail_audit2.is_compliant
        assert "points to unregistered or dead backend route" in fail_audit2.dead_controls[0]["error"]
