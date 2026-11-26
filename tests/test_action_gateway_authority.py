"""
Acceptance Test Suite for OpenCode Step 2C:
Authority, Approvals, Delegations, Segregation of Duties, and Principal Separation in ActionGateway.

Verifies:
  1. Action above employee limit refused, needs higher tier approval
  2. Altering payload after approval voids it (SHA-256 digest mismatch)
  3. Self-approval strictly refused
  4. Delegation beyond delegator's authority refused
  5. Revoked delegate refused immediately
  6. Agent principal cannot call an employee
  7. Rule 15: Agent principal cannot write authority, budget, policy, constitution, or kill switch
  8. Two concurrent spends at budget edge let exactly one pass
  9. Killed company refuses everything within one call
  10. DRAFT pack company cannot reach autonomous level
  11. Ledger posting above threshold requires approval through ActionGateway engine
  12. Explain endpoint returns complete machine-readable decision path
"""

import concurrent.futures
import hashlib
import json
import time
import uuid
import pytest

from core.db import db
from core.action_envelope import ActionEnvelope, RiskClass
from core.action_gateway import action_gateway, ActionGatewayRejection
from core.authority import (
    ActionClass,
    AutonomyLevel,
    PrincipalType,
    Rule15Violation,
    SelfApprovalError,
    AIApprovalError,
    DelegationAuthorityExceededError,
    ensure_authority_tables,
    compute_effective_autonomy,
    authority_profile_manager,
    delegation_manager,
    approvals_manager,
    constitution_manager,
)
from core.authority.budget_guard import spend_budget_guard
from core.killswitch_matrix import KillSwitchMatrix
from core.ledger.kernel import LedgerKernel, LedgerError
from core.ledger.schema import AccountType
from core.llm.budget import llm_budget_manager
from core.llm.policy import tenant_model_policy_manager
from core.industry_packs.loader import IndustryPackLoader


@pytest.fixture(autouse=True)
def setup_authority_test_env():
    """Ensures clean authority tables and seeded tenant/company scope for tests."""
    ensure_authority_tables()
    spend_budget_guard._ensure_table()
    now = time.time()
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES ('tnt_step2c', 'Step 2C Tenant', 'ACTIVE', ?) "
            "ON CONFLICT(tenant_id) DO UPDATE SET status = 'ACTIVE'",
            (now,),
        )
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES ('comp_step2c', 'tnt_step2c', 'Step 2C Company', 'TECH', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO UPDATE SET status = 'OPERATIONAL'",
            (now,),
        )
        conn.commit()
    yield


# =============================================================================
# ACCEPTANCE TEST 1: Action above employee limit refused, needs higher tier approval
# =============================================================================

def test_01_action_above_employee_limit_refused_needs_higher_tier():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    emp_id = "emp_g7_junior"

    # G7 single spend limit is $500 (50,000 cents)
    action_spend_cents = 100_000  # $1,000.00 USD
    payload = {"vendor": "CloudCorp", "amount_minor_units": action_spend_cents, "service": "compute"}

    env_unapproved = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=emp_id,
        capability_id="billing.spend",
        target="vendors/cloudcorp",
        intent="Purchase additional cloud compute",
        parameters=payload,
        action_class="COMMIT_SPEND",
        principal_id=emp_id,
        principal_grade="G7",
        spend_amount_minor_units=action_spend_cents,
    )

    # 1. Unapproved action must be rejected at Step 5 with AUTHORITY_LIMIT_EXCEEDED
    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(env_unapproved)
    assert exc_info.value.step == 5
    assert exc_info.value.rule == "AUTHORITY_LIMIT_EXCEEDED"
    assert "Higher tier approval required" in exc_info.value.message

    # 2. Allocate operating budget
    spend_budget_guard.set_budget(tenant_id, company_id, "OPERATING", 500_000)

    # 3. Create approval request and approve by Manager G5 (limit $10,000)
    appr_req = approvals_manager.create_approval_request(
        tenant_id=tenant_id,
        company_id=company_id,
        action_id=env_unapproved.action_id,
        action_class="COMMIT_SPEND",
        payload=payload,
        requester_id=emp_id,
        maker_id=emp_id,
        approver_role="MANAGER",
    )
    approvals_manager.approve(
        approval_id=appr_req["approval_id"],
        tenant_id=tenant_id,
        company_id=company_id,
        approver_id="mgr_g5_ops",
        approver_type="HUMAN",
        approver_role="MANAGER",
        decision_reason="Approved for compute scaling",
    )

    # 4. Re-submit action with valid approval ID attached -> Must succeed!
    env_approved = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=emp_id,
        capability_id="billing.spend",
        target="vendors/cloudcorp",
        intent="Purchase additional cloud compute",
        parameters=payload,
        action_class="COMMIT_SPEND",
        principal_id=emp_id,
        principal_grade="G7",
        spend_amount_minor_units=action_spend_cents,
        approval_id=appr_req["approval_id"],
    )

    outcome = action_gateway.execute_action(env_approved)
    assert outcome["status"] == "VERIFIED"
    assert "evidence" in outcome


# =============================================================================
# ACCEPTANCE TEST 2: Altering payload after approval voids it (SHA-256 mismatch)
# =============================================================================

def test_02_altering_payload_after_approval_voids_it():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    emp_id = "emp_g6_buyer"

    spend_budget_guard.set_budget(tenant_id, company_id, "OPERATING", 1_000_000)

    approved_payload = {"vendor": "OfficeSuppliesCo", "amount_minor_units": 300_000, "item": "laptops"}
    appr_req = approvals_manager.create_approval_request(
        tenant_id=tenant_id,
        company_id=company_id,
        action_id="act_tamper_test",
        action_class="COMMIT_SPEND",
        payload=approved_payload,
        requester_id=emp_id,
        maker_id=emp_id,
        approver_role="MANAGER",
    )
    approvals_manager.approve(
        approval_id=appr_req["approval_id"],
        tenant_id=tenant_id,
        company_id=company_id,
        approver_id="mgr_g4_director",
        approver_type="HUMAN",
        approver_role="MANAGER",
    )

    # Malicious alteration: increase amount or change vendor
    tampered_payload = {"vendor": "OfficeSuppliesCo", "amount_minor_units": 450_000, "item": "laptops"}

    tampered_env = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=emp_id,
        capability_id="billing.spend",
        target="vendors/officesupplies",
        intent="Procure hardware",
        parameters=tampered_payload,
        action_class="COMMIT_SPEND",
        principal_id=emp_id,
        principal_grade="G6",
        spend_amount_minor_units=450_000,
        approval_id=appr_req["approval_id"],
    )

    # Must fail at Step 8 with APPROVAL_PAYLOAD_MISMATCH
    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(tampered_env)
    assert exc_info.value.step == 8
    assert exc_info.value.rule == "APPROVAL_PAYLOAD_MISMATCH"
    assert "altered after approval" in exc_info.value.message


# =============================================================================
# ACCEPTANCE TEST 3: Self-approval strictly refused
# =============================================================================

def test_03_self_approval_strictly_refused():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    emp_requester = "emp_ops_requester"

    payload = {"budget_increase_usd": 5000}
    appr_req = approvals_manager.create_approval_request(
        tenant_id=tenant_id,
        company_id=company_id,
        action_id="act_self_appr",
        action_class="COMMIT_SPEND",
        payload=payload,
        requester_id=emp_requester,
        maker_id=emp_requester,
        approver_role="MANAGER",
    )

    # Requester attempting to approve own request must raise SelfApprovalError
    with pytest.raises(SelfApprovalError) as exc_info:
        approvals_manager.approve(
            approval_id=appr_req["approval_id"],
            tenant_id=tenant_id,
            company_id=company_id,
            approver_id=emp_requester,  # Self-approval!
            approver_type="HUMAN",
            approver_role="MANAGER",
        )
    assert "Self-approval strictly refused" in str(exc_info.value)


# =============================================================================
# ACCEPTANCE TEST 4: Delegation beyond delegator's authority refused
# =============================================================================

def test_04_delegation_beyond_delegator_authority_refused():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    delegator_g6 = "emp_manager_g6"  # G6 single limit is $2,500
    delegate_g8 = "emp_staff_g8"

    now = time.time()

    # 1. Attempting to delegate $10,000 spend (which exceeds G6 limit of $2,500)
    invalid_scope = {"max_single_spend_usd": 10_000}
    with pytest.raises(DelegationAuthorityExceededError) as exc_info:
        delegation_manager.create_delegation(
            tenant_id=tenant_id,
            company_id=company_id,
            delegator_id=delegator_g6,
            delegate_id=delegate_g8,
            scope=invalid_scope,
            starts_at=now,
            expires_at=now + 3600.0,
            delegator_grade="G6",
            caller_principal_type="HUMAN",
        )
    assert "exceeds delegator's authority limit" in str(exc_info.value)

    # 2. Delegator with G7 (can_delegate=False) attempting to delegate authority
    delegator_g7 = "emp_staff_g7"
    with pytest.raises(DelegationAuthorityExceededError) as exc_info:
        delegation_manager.create_delegation(
            tenant_id=tenant_id,
            company_id=company_id,
            delegator_id=delegator_g7,
            delegate_id=delegate_g8,
            scope={"max_single_spend_usd": 100},
            starts_at=now,
            expires_at=now + 3600.0,
            delegator_grade="G7",
            caller_principal_type="HUMAN",
        )
    assert "lacks delegation privileges" in str(exc_info.value)


# =============================================================================
# ACCEPTANCE TEST 5: Revoked delegate refused immediately
# =============================================================================

def test_05_revoked_delegate_refused_immediately():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    delegator_g4 = "emp_exec_g4"  # G4 limit is $25,000
    delegate_g8 = "emp_acting_g8"  # Base G8 limit is $250 (25,000 cents)

    spend_budget_guard.set_budget(tenant_id, company_id, "OPERATING", 1_000_000)

    now = time.time()
    delegation = delegation_manager.create_delegation(
        tenant_id=tenant_id,
        company_id=company_id,
        delegator_id=delegator_g4,
        delegate_id=delegate_g8,
        scope={"max_single_spend_usd": 5_000},  # $5,000 delegated limit
        starts_at=now - 60.0,
        expires_at=now + 3600.0,
        delegator_grade="G4",
        caller_principal_type="HUMAN",
    )

    action_spend_cents = 100_000  # $1,000.00 USD (exceeds G8's $250 base, but within $5,000 delegation)
    env = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=delegate_g8,
        capability_id="billing.spend",
        target="vendors/hosting",
        intent="Hosting renewal",
        parameters={"amount_minor_units": action_spend_cents},
        action_class="COMMIT_SPEND",
        principal_id=delegate_g8,
        principal_grade="G8",
        spend_amount_minor_units=action_spend_cents,
    )

    # 1. While delegation is active, execution succeeds!
    outcome = action_gateway.execute_action(env)
    assert outcome["status"] == "VERIFIED"

    # 2. Revoke delegation
    revoked = delegation_manager.revoke_delegation(
        delegation_id=delegation["delegation_id"],
        tenant_id=tenant_id,
        company_id=company_id,
        revoked_by="emp_exec_g4",
        caller_principal_type="HUMAN",
    )
    assert revoked is True

    # 3. On the very next call, delegate is refused immediately!
    env_after_revocation = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=delegate_g8,
        capability_id="billing.spend",
        target="vendors/hosting_next",
        intent="Hosting renewal next",
        parameters={"amount_minor_units": action_spend_cents},
        action_class="COMMIT_SPEND",
        principal_id=delegate_g8,
        principal_grade="G8",
        spend_amount_minor_units=action_spend_cents,
    )

    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(env_after_revocation)
    assert exc_info.value.step == 5
    assert exc_info.value.rule == "AUTHORITY_LIMIT_EXCEEDED"
    assert "exceeds single spend limit $250.00 for grade G8" in exc_info.value.message


# =============================================================================
# ACCEPTANCE TEST 6: An agent principal cannot call an employee
# =============================================================================

def test_06_agent_principal_cannot_call_employee():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"

    env_agent_calling_emp = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="agt_autonomous_crawler",
        capability_id="agent.invoke_employee",
        target="employees/emp_alice_hr",
        intent="Assign task to employee",
        parameters={"task_id": "tsk_prepare_payroll"},
        action_class="WRITE_INTERNAL",
        principal_type="AGENT",
        principal_id="agt_autonomous_crawler",
        target_principal_type="AI_EMPLOYEE",
        target_principal_id="emp_alice_hr",
    )

    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(env_agent_calling_emp)
    assert exc_info.value.step == 4
    assert exc_info.value.rule == "AGENT_CANNOT_CALL_EMPLOYEE"
    assert "cannot command or delegate to employee" in exc_info.value.message


# =============================================================================
# ACCEPTANCE TEST 7: Rule 15: Agent principal cannot write governance tables
# =============================================================================

def test_07_agent_principal_cannot_write_governance_tables_rule_15():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    agent_id = "agt_rogue_bot"

    # a) Writing authority profiles
    with pytest.raises(Rule15Violation):
        authority_profile_manager.set_profile(
            tenant_id=tenant_id,
            company_id=company_id,
            principal_id=agent_id,
            grade="G1",
            caller_principal_type="AGENT",
        )

    # b) Allocating budgets
    with pytest.raises(PermissionError) as exc_info:
        llm_budget_manager.set_budget(
            tenant_id=tenant_id,
            company_id=company_id,
            entity_type="AGENT",
            entity_id=agent_id,
            allocated_micro_usd=100_000_000,
            caller_principal_type="AGENT",
        )
    assert "Rule 15 Violation" in str(exc_info.value)

    # c) Writing policies
    with pytest.raises(PermissionError) as exc_info:
        tenant_model_policy_manager.set_policy(
            tenant_id=tenant_id,
            company_id=company_id,
            allowed_providers=["sandbox"],
            caller_principal_type="AGENT",
        )
    assert "Rule 15 Violation" in str(exc_info.value)

    # d) Writing company constitution
    with pytest.raises(Rule15Violation):
        constitution_manager.set_constitution(
            tenant_id=tenant_id,
            company_id=company_id,
            mission="Takeover",
            prohibited_actions=[],
            caller_principal_type="AGENT",
        )

    # e) Mutating pack review status
    with pytest.raises(PermissionError) as exc_info:
        IndustryPackLoader().install_pack(
            tenant_id=tenant_id,
            company_id=company_id,
            pack_data={"schema_version": "zonata.industry-pack/v1"},
            caller_principal_type="AGENT",
        )
    assert "Rule 15 Violation" in str(exc_info.value)

    # f) AI / Agent approving money or permissions
    appr_req = approvals_manager.create_approval_request(
        tenant_id=tenant_id,
        company_id=company_id,
        action_id="act_gov_test",
        action_class="COMMIT_SPEND",
        payload={"amount": 1000},
        requester_id="human_user",
        maker_id="human_user",
    )
    with pytest.raises(AIApprovalError):
        approvals_manager.approve(
            approval_id=appr_req["approval_id"],
            tenant_id=tenant_id,
            company_id=company_id,
            approver_id=agent_id,
            approver_type="AGENT",
        )

    # g) Creating delegations
    with pytest.raises(Rule15Violation):
        delegation_manager.create_delegation(
            tenant_id=tenant_id,
            company_id=company_id,
            delegator_id=agent_id,
            delegate_id="agt_sub_bot",
            scope={"max_single_spend_usd": 100},
            starts_at=time.time(),
            expires_at=time.time() + 1000,
            caller_principal_type="AGENT",
        )

    # h) Activating kill switch
    with pytest.raises(PermissionError) as exc_info:
        KillSwitchMatrix(tenant_id).activate(
            level="COMPANY",
            target_id=company_id,
            reason="Agent attempted kill",
            activated_by="AGENT",
        )
    assert "Rule 15 Violation" in str(exc_info.value)

    # Also test rejection via ActionGateway pipeline
    env_gov_write = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=agent_id,
        capability_id="policy.update",
        target="governance/authority_profiles",
        intent="Elevate own authority to G1",
        parameters={"grade": "G1"},
        action_class="CHANGE_PERMISSION",
        principal_type="AGENT",
        principal_id=agent_id,
    )
    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(env_gov_write)
    assert exc_info.value.step == 4
    assert exc_info.value.rule == "PRINCIPAL_WRITES_GOVERNANCE_BLOCKED"


# =============================================================================
# ACCEPTANCE TEST 8: Two concurrent spends at budget edge let exactly one pass
# =============================================================================

def test_08_two_concurrent_spends_at_edge_of_budget_let_exactly_one_pass():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    category = f"CONCURRENT_TEST_{uuid.uuid4().hex[:6]}"

    # Budget has $100.00 (10,000 minor units).
    # Two threads will concurrently attempt to spend $80.00 (8,000 minor units) each.
    # $80 + $80 = $160 > $100 -> Exactly 1 must pass, 1 must fail!
    spend_budget_guard.set_budget(tenant_id, company_id, category, allocated_minor_units=10_000)

    def worker_spend(worker_id: int):
        env = ActionEnvelope.create(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=f"worker_{worker_id}",
            capability_id="billing.spend",
            target="payment_gateway/charge",
            intent=f"Concurrent charge {worker_id}",
            parameters={"budget_category": category, "amount_minor_units": 8_000},
            action_class="COMMIT_SPEND",
            principal_id=f"emp_worker_{worker_id}",
            principal_grade="G4",  # G4 limit is $25,000
            spend_amount_minor_units=8_000,
        )
        try:
            res = action_gateway.execute_action(env)
            return (True, res["status"])
        except ActionGatewayRejection as e:
            return (False, e.rule)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_spend, 1)
        f2 = executor.submit(worker_spend, 2)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"
    assert failures[0][1] == "BUDGET_EXHAUSTED"


# =============================================================================
# ACCEPTANCE TEST 9: Killed company refuses everything within one call
# =============================================================================

def test_09_killed_company_refuses_everything_within_one_call():
    tenant_id = "tnt_step2c"
    company_id = "comp_killed_test"

    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'Killed Test Co', 'TECH', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO UPDATE SET status = 'OPERATIONAL'",
            (company_id, tenant_id, time.time()),
        )
        conn.commit()

    env = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="agt_worker_ks",
        capability_id="data.read",
        target="storage/reports",
        intent="Read report",
        parameters={},
        action_class="READ_INTERNAL",
        principal_id="emp_worker_ks",
        principal_grade="G8",
    )

    # 1. Action succeeds when not killed
    outcome = action_gateway.execute_action(env)
    assert outcome["status"] == "VERIFIED"

    # 2. Engage KillSwitch for COMPANY level
    ks = KillSwitchMatrix(tenant_id)
    ks.activate(level="COMPANY", target_id=company_id, reason="Fraudulent activity detected", activated_by="HUMAN_OWNER")

    # 3. On the very next call, ActionGateway immediately refuses at Step 1!
    env_after_kill = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="agt_worker_ks",
        capability_id="data.read",
        target="storage/reports",
        intent="Read report after kill",
        parameters={},
        action_class="READ_INTERNAL",
        principal_id="emp_worker_ks",
        principal_grade="G8",
    )

    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(env_after_kill)
    assert exc_info.value.step == 1
    assert exc_info.value.rule == "KILL_SWITCH_ACTIVE"
    assert "active COMPANY kill switch" in exc_info.value.message


# =============================================================================
# ACCEPTANCE TEST 10: A DRAFT pack company cannot reach autonomous level
# =============================================================================

def test_10_draft_pack_company_cannot_reach_autonomous_level():
    tenant_id = "tnt_step2c"
    company_id = "comp_draft_pack_co"
    now = time.time()

    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'Draft Pack Co', 'HEALTHCARE', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO UPDATE SET status = 'OPERATIONAL'",
            (company_id, tenant_id, now),
        )
        # Install an industry pack with review_status="DRAFT"
        draft_manifest = json.dumps({
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {
                "pack_id": "draft_clinic_pack",
                "name": "Draft Medical Clinic",
                "version": "0.1.0",
                "industry_code": "Q86",
                "review_status": "DRAFT",
            }
        })
        conn.execute(
            """
            INSERT INTO installed_industry_packs (id, tenant_id, company_id, pack_id, name, version, isic_code, raw_manifest, installed_at)
            VALUES (?, ?, ?, 'draft_clinic_pack', 'Draft Medical Clinic', '0.1.0', 'Q86', ?, ?)
            ON CONFLICT (tenant_id, company_id, pack_id) DO UPDATE SET raw_manifest = EXCLUDED.raw_manifest
            """,
            (f"inst_{uuid.uuid4().hex[:12]}", tenant_id, company_id, draft_manifest, now)
        )
        conn.commit()

    # Rule 19: Compute effective autonomy when owner requested AUTONOMOUS
    effective_autonomy = compute_effective_autonomy(
        tenant_id=tenant_id,
        company_id=company_id,
        owner_setting=AutonomyLevel.AUTONOMOUS,
    )
    # Must be capped at SUPERVISED!
    assert effective_autonomy == AutonomyLevel.SUPERVISED

    # Autonomous execution attempted through gateway must be refused with AUTONOMY_CEILING_EXCEEDED
    env_autonomous = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="agt_autonomous_dr",
        capability_id="clinic.prescribe",
        target="records/prescriptions",
        intent="Autonomous prescription without doctor review",
        parameters={"rx_id": "rx_101"},
        action_class="WRITE_INTERNAL",
        principal_id="agt_autonomous_dr",
        principal_grade="G5",
        is_autonomous=True,  # Autonomous mode
    )

    with pytest.raises(ActionGatewayRejection) as exc_info:
        action_gateway.execute_action(env_autonomous)
    assert exc_info.value.step == 5
    assert exc_info.value.rule == "AUTONOMY_CEILING_EXCEEDED"
    assert "capping autonomy at SUPERVISED" in exc_info.value.message or "ceiling is 'SUPERVISED'" in exc_info.value.message


# =============================================================================
# ACCEPTANCE TEST 11: Ledger posting above threshold requires ActionGateway approval
# =============================================================================

def test_11_ledger_posting_above_threshold_requires_approval_through_engine():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"
    kernel = LedgerKernel()

    # Create Accounts
    cash_acct = kernel.create_account(tenant_id, company_id, f"1010_{uuid.uuid4().hex[:4]}", "Operating Cash", AccountType.ASSET, "USD")
    rev_acct = kernel.create_account(tenant_id, company_id, f"4010_{uuid.uuid4().hex[:4]}", "Subscription Revenue", AccountType.REVENUE, "USD")

    # High-value transaction: $50,000 USD (5,000,000 minor units). Exceeds G6 limit ($2,500) and $1,000 threshold.
    posting_amount = 5_000_000
    spend_budget_guard.set_budget(tenant_id, company_id, "OPERATING", 10_000_000)

    entry_id = kernel.create_journal_entry(
        tenant_id=tenant_id,
        company_id=company_id,
        entry_number=f"JE-{uuid.uuid4().hex[:6]}",
        date="2026-04-01",
        description="High-value enterprise contract close",
        created_by="emp_bookkeeper_g6",
    )
    kernel.add_journal_line(tenant_id, company_id, entry_id, cash_acct, debit_amount=posting_amount, credit_amount=0, currency="USD")
    kernel.add_journal_line(tenant_id, company_id, entry_id, rev_acct, debit_amount=0, credit_amount=posting_amount, currency="USD")

    poster_g6 = "emp_bookkeeper_g6"

    # 1. Posting without approval must be rejected by ActionGateway through LedgerKernel
    with pytest.raises(LedgerError) as exc_info:
        kernel.post_journal_entry(
            tenant_id=tenant_id,
            company_id=company_id,
            entry_id=entry_id,
            principal_id=poster_g6,
            principal_grade="G6",
            approval_id=None,
        )
    assert "LEDGER_POSTING_REQUIRES_APPROVAL" in str(exc_info.value)

    # 2. Obtain ActionGateway approval for exact payload
    appr_payload = {
        "entry_id": entry_id,
        "amount_minor_units": posting_amount,
    }
    appr_req = approvals_manager.create_approval_request(
        tenant_id=tenant_id,
        company_id=company_id,
        action_id=f"act_ledger_{entry_id}",
        action_class="POST_LEDGER",
        payload=appr_payload,
        requester_id=poster_g6,
        maker_id=poster_g6,
        approver_role="CFO",
    )
    approvals_manager.approve(
        approval_id=appr_req["approval_id"],
        tenant_id=tenant_id,
        company_id=company_id,
        approver_id="emp_cfo_g2",
        approver_type="HUMAN",
        approver_role="EXECUTIVE",
        decision_reason="Approved high-value enterprise contract journal posting",
    )

    # 3. Post with valid approval attached -> Must succeed!
    posted = kernel.post_journal_entry(
        tenant_id=tenant_id,
        company_id=company_id,
        entry_id=entry_id,
        principal_id=poster_g6,
        principal_grade="G6",
        approval_id=appr_req["approval_id"],
    )
    assert posted["status"].value == "POSTED"
    assert posted["posted_at"] > 0


# =============================================================================
# ACCEPTANCE TEST 12: Explain endpoint returns machine-readable decision path
# =============================================================================

def test_12_explain_endpoint_returns_decision_path():
    tenant_id = "tnt_step2c"
    company_id = "comp_step2c"

    env = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="agt_explain_demo",
        capability_id="billing.spend",
        target="vendors/demo",
        intent="Demo unapproved spend",
        parameters={"amount_minor_units": 500_000},
        action_class="COMMIT_SPEND",
        principal_id="emp_explain_g8",
        principal_grade="G8",
        spend_amount_minor_units=500_000,
    )

    # Trigger rejection
    with pytest.raises(ActionGatewayRejection):
        action_gateway.execute_action(env)

    # Call explain endpoint
    explanation = action_gateway.explain_decision(tenant_id, company_id, env.action_id)
    assert explanation["found"] is True
    assert explanation["action_id"] == env.action_id
    assert explanation["allowed"] is False
    assert explanation["denied_at_step"] == 5
    assert explanation["rule_id"] == "AUTHORITY_LIMIT_EXCEEDED"
    assert len(explanation["decision_path"]) >= 5
    # Steps 1 to 4 passed, Step 5 denied
    assert explanation["decision_path"][0]["gate"] == "KILL_SWITCH"
    assert explanation["decision_path"][0]["status"] == "PASSED"
    assert explanation["decision_path"][4]["gate"] == "AUTHORITY_PROFILE"
    assert explanation["decision_path"][4]["status"] == "DENIED"
