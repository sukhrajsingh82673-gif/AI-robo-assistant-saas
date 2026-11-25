#!/usr/bin/env python3
"""
Step 9 End-to-End Product Readiness Qualification Scenario (Sub-Step 9L).
Executes the complete customer lifecycle from onboarding to billing, API, marketplace,
dual-control support, mobile passkeys, EU Data Act switching, and canary deployment.
"""

import sys
import os
import time
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from core.onboarding.wizard import OnboardingWizard
from core.onboarding.demo_company import DemoCompanySeeder
from core.onboarding.importer import CsvDataImporter
from core.billing.port import SandboxBillingAdapter
from core.billing.plans import PlanRegistry
from core.billing.metering import UsageLedger
from core.billing.cost_caps import CostCapManager
from core.billing.lifecycle import BillingLifecycleManager, AccountStatus
from core.api.public_v1 import PublicApiRouter
from core.webhooks.standard_webhooks import StandardWebhooksSigner, SSRFValidator
from core.marketplace.manifest import MarketplaceManifest, CapabilityRequirement
from core.marketplace.registry import MarketplaceRegistry
from core.marketplace.sandbox import MarketplaceSandbox, SandboxViolationError
from core.marketplace.revocation import PackageRevocationEngine
from core.support.grants import SupportGrantEngine
from core.ui.mobile_approvals import MobileApprovalService
from core.ui.dead_control_detector import DeadControlDetector
from core.ui.accessibility_checker import AccessibilityChecker
from core.compliance.data_act_export import DataActExportEngine
from core.release.canary import ProgressiveCanaryRollout, CanaryHealthMetric
from core.reliability.slo_tracker import SloTracker


def run_complete_step9_scenario() -> dict:
    scenario_log = []
    tenant_id = "tenant_enterprise_phoenix"

    # 1. Onboarding & Demo Company
    wizard = OnboardingWizard(tenant_id=tenant_id)
    wizard.submit_profile("Phoenix Aerospace GmbH", "DE", "Aerospace & Defense")
    wizard.select_departments(["finance", "engineering", "legal"])
    wizard.select_plan("team")
    wizard.invite_team(["cto@phoenix-aero.de", "cfo@phoenix-aero.de"])
    wizard_state = wizard.complete_onboarding(seed_demo=True)
    assert wizard_state.is_complete
    demo_data = DemoCompanySeeder.seed_demo_tenant(tenant_id)
    assert demo_data["is_demo"] is True
    scenario_log.append("1. Onboarding wizard completed & demo company seeded.")

    # 2. Billing Subscription & Metering Ledger
    billing = SandboxBillingAdapter()
    cus = billing.create_customer(tenant_id, "billing@phoenix-aero.de", "Phoenix Aerospace")
    sub = billing.create_subscription(tenant_id, "plan_team_v1")
    ledger = UsageLedger()
    t0 = time.time()
    for idx in range(10):
        ledger.record_usage(
            tenant_id, sub["subscription_id"], "ai_tokens", 50000, "tokens", f"phoenix_tx_{idx}", timestamp=t0 + idx
        )
    valid_chain, _ = ledger.verify_chain_integrity(tenant_id)
    assert valid_chain
    inv = billing.calculate_invoice(tenant_id, subtotal_cents=9900, tax_rate_bps=1900)  # 19% German VAT
    assert inv["total_cents"] == 9900 + ((9900 * 1900) // 10000)
    scenario_log.append("2. Subscription active, 10 events chained via SHA-256, invoice integer pennies verified.")

    # 3. Spend Safeguards & Cost Caps
    cap_mgr = CostCapManager()
    cap_mgr.set_caps(tenant_id, hard_cap_cents=10000)  # $100 cap
    alert_soft = cap_mgr.record_spend(tenant_id, 8500)
    assert alert_soft.level == "SOFT_CAP"
    alert_hard = cap_mgr.record_spend(tenant_id, 2000)
    assert alert_hard.level == "HARD_CAP"
    allowed, _ = cap_mgr.is_spend_allowed(tenant_id, estimated_cents=500)
    assert not allowed
    scenario_log.append("4. Cost caps: 80% soft cap alert fired; 100% hard cap auto-halt enforced.")

    # 4. Delinquency & Rule 78 Legal Hold Protection
    lifecycle = BillingLifecycleManager()
    lifecycle.register_account(tenant_id, legal_hold=False)
    st_grace = lifecycle.mark_payment_failed(tenant_id, current_time=t0)
    assert st_grace == AccountStatus.PAST_DUE_GRACE
    st_ro = lifecycle.evaluate_lifecycle(tenant_id, current_time=t0 + (16 * 86400))
    assert st_ro == AccountStatus.RESTRICTED_READ_ONLY
    # Place under legal hold
    lifecycle.set_legal_hold(tenant_id, True)
    can_purge, reason_hold = lifecycle.can_purge_tenant_data(tenant_id)
    assert not can_purge
    assert "Legal Hold" in reason_hold
    scenario_log.append("5. Delinquency transitions verified; Rule 78 legal hold strictly protects customer data.")

    # 5. Public API, Webhooks & SSRF Protection
    api = PublicApiRouter()
    wh_body = json.dumps({"url": "https://hooks.phoenix-aero.de/events", "event_types": ["task.completed"]})
    st_wh, _, res_wh = api.dispatch(
        "POST", "/api/public/v1/webhooks",
        {"X-Tenant-ID": tenant_id, "Idempotency-Key": "wh_idem_key_1", "X-Test-Mode": "1"},
        wh_body
    )
    assert st_wh == 201
    wh_data = json.loads(res_wh)
    # SSRF check
    safe_target, _ = SSRFValidator.is_url_safe("https://metadata.google.internal")
    assert not safe_target
    # Webhook signature
    signer = StandardWebhooksSigner(active_secret=wh_data["secret"])
    hdr = signer.generate_header("msg_001", '{"status": "ok"}', timestamp=int(t0))
    assert signer.verify_header("msg_001", '{"status": "ok"}', hdr, current_time=t0)
    scenario_log.append("6. Public API registered webhook, SSRF blocked, Standard Webhook HMAC verified.")

    # 6. Marketplace Sandboxing & Instant Revocation
    mkt = MarketplaceRegistry()
    pkg = MarketplaceManifest(
        package_id="ext.cad_parser",
        name="CAD Parser",
        version="1.0.0",
        publisher="Siemens Partner",
        description="CAD parsing",
        entrypoint="cad.py",
        capabilities_requested=[CapabilityRequirement("storage:read", "drawings", "Read CAD files")],
    )
    mkt.submit_package(pkg, "def parse(f): return len(f)")
    mkt.install_package(tenant_id, "ext.cad_parser", "1.0.0", ["storage:read:drawings"])
    sandbox = MarketplaceSandbox(tenant_id, "ext.cad_parser", ["storage:read:drawings"])
    assert sandbox.execute_operation("storage:read", "drawings")["status"] == "SUCCESS"
    # Unconsented operation blocked
    try:
        sandbox.execute_operation("network:egress", "exfil.org")
        assert False, "Ungranted egress must fail"
    except SandboxViolationError:
        pass
    # Instant revocation
    rev_engine = PackageRevocationEngine()
    rev_engine.register_active_sandbox(sandbox)
    rev_res = rev_engine.revoke_package_globally("ext.cad_parser", "Advisory", "op_sec")
    assert rev_res["revoked_within_sla"] is True
    scenario_log.append("7. Marketplace sandboxing enforced; ungranted egress blocked; < 1s revocation verified.")

    # 7. Dual-Control Support Access Guard (Rule 82)
    sup_engine = SupportGrantEngine(signing_secret="phoenix_sup_secret")
    grant = sup_engine.issue_support_grant(
        tenant_id=tenant_id,
        issued_by_user_id="usr_phoenix_cfo",
        user_role="Owner",
        operator_id="op_dan",
        purpose="Inspect stuck export",
        current_time=t0,
    )
    ok_sup, _ = sup_engine.validate_access(grant.grant_id, "op_dan", tenant_id, "READ_DIAGNOSTICS", current_time=t0 + 100)
    assert ok_sup
    # Rule 82 barrier
    ok_barrier, reason_b = sup_engine.validate_access(grant.grant_id, "op_dan", tenant_id, "TRANSFER_OWNERSHIP", current_time=t0 + 100)
    assert not ok_barrier
    assert "Rule 82 Violation" in reason_b
    scenario_log.append("8. Dual-control support verified; operator strictly blocked from reserved owner actions.")

    # 8. Mobile Approvals & Passkeys
    mob = MobileApprovalService(tenant_id=tenant_id)
    t_id = mob.create_approval_ticket("finance", "Approve Titanium Sheet PO", 1500000, "ag_cfo", {})
    # High value mandates passkey
    ok_pass_fail, _, _ = mob.submit_decision(t_id, "usr_cfo", True, passkey_signature=None)
    assert not ok_pass_fail
    ok_pass_succ, _, _ = mob.submit_decision(t_id, "usr_cfo", True, passkey_signature="passkey_fido2_signature")
    assert ok_pass_succ
    scenario_log.append("9. Mobile high-value approval enforced biometric passkey.")

    # 9. EU Data Act Export
    export = DataActExportEngine.generate_full_tenant_export(
        tenant_id=tenant_id,
        company_profile={"name": "Phoenix Aerospace GmbH"},
        subscriptions=[{"id": sub["subscription_id"]}],
        usage_ledger=[{"metric": "ai_tokens", "quantity": 500000}],
        invoices=[{"id": "inv_01", "total_cents": 11781}],
        audit_trail=[{"action": "ONBOARDING", "timestamp": t0}],
    )
    assert export.exit_fees_charged_cents == 0
    assert "Regulation (EU) 2023/2854" in export.regulatory_framework
    scenario_log.append("10. EU Data Act full portable archive generated with zero switching fees.")

    # 10. Progressive Canary & SLO Gate
    rollout = ProgressiveCanaryRollout("v9.0.0", "v8.0.0")
    rollout.advance_stage(CanaryHealthMetric(5, 0.02, 110.0, True))
    rollout.advance_stage(CanaryHealthMetric(25, 0.03, 115.0, True))
    rollout.advance_stage(CanaryHealthMetric(50, 0.04, 120.0, True))
    rollout.advance_stage(CanaryHealthMetric(100, 0.02, 115.0, True))
    assert rollout.active_traffic_percent == 100
    slo = SloTracker()
    slo.record_event("api_availability", True, count=10000)
    assert slo.is_release_permitted()[0] is True
    scenario_log.append("11. Progressive canary rollout completed to 100%; SLO error budgets healthy.")

    return {
        "tenant_id": tenant_id,
        "qualification_status": "CERTIFIED_PRODUCT_READY",
        "milestones_passed": len(scenario_log),
        "scenario_log": scenario_log,
    }


def main():
    print("=== EXECUTING STEP 9 END-TO-END QUALIFICATION SCENARIO ===")
    res = run_complete_step9_scenario()
    print(json.dumps(res, indent=2))
    print("\n>>> STEP 9 END-TO-END QUALIFICATION SCENARIO: SUCCESS <<<")
    return 0


if __name__ == "__main__":
    sys.exit(main())
