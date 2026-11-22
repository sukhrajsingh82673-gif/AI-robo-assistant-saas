"""
Acceptance Test Suite for OpenCode Step 2J:
AI CEO Executive Brain and Workforce Trust (Directives, Plan Validation, Decision Records, Risk Register, Trust Levels).

Verifies:
  1. An ambiguous high-stakes command produces a question, not a plan (ClarificationRequiredError).
  2. A plan exceeding budget is rejected with deterministic reasons (PlanValidationFailedError).
  3. A plan exceeding position authority is rejected with deterministic reasons (PlanValidationFailedError).
  4. A plan step needing the browser is marked BLOCKED: CAPABILITY_NOT_LIVE.
  5. A new employee starts in SHADOW (Rule 19) and cannot be promoted without meeting measured thresholds.
  6. Promotion requires human principal approval; agent principal approval is refused (Rule 15).
  7. A policy violation demotes automatically to SHADOW and enqueues an alert in the human inbox.
  8. The AI CEO principal cannot edit the constitution or its own authority (Rule 15).
  9. Number-Lock: Narrative text containing unverified numbers is rejected and replaced by a verified template (Rule 18).
  10. Risk register triggers create proposed corrective tasks in the Work Kernel, not silent actions.
"""

import time
import json
import uuid
import pytest

from core.db import db
from core.authority.types import PrincipalType, Rule15Violation
from core.authority.constitution import ConstitutionManager
from core.work import ensure_work_kernel_tables, human_inbox_service
from core.organization import ensure_organization_tables
from core.executive import (
    TrustLevel,
    DirectiveStatus,
    RiskTriggerType,
    RiskSeverity,
    ClarificationRequiredError,
    PlanValidationFailedError,
    PromotionThresholdNotMetError,
    UnauthorizedPromotionApproverError,
    NumberLockViolationError,
    DirectiveModel,
    PlanTaskSpec,
    PlanProjectSpec,
    PlanMissionSpec,
    PlanGraphModel,
    CommandInterpreter,
    PlanValidator,
    CEOPlanner,
    CEODecisionService,
    WorkforceTrustService,
    CompanyRiskService,
    NumberLockValidator,
    CEOReportingService,
    ensure_executive_tables,
)


TENANT_ID = "tnt_ceo_test"
COMPANY_ID = "comp_ceo_test"
EMPLOYEE_ID = "emp_ops_bot_01"


@pytest.fixture(autouse=True)
def setup_executive_env():
    """Seeds test scope, organization, work kernel, and executive tables."""
    ensure_organization_tables()
    ensure_work_kernel_tables()
    ensure_executive_tables()
    now = time.time()

    with db.get_connection() as conn:
        conn.execute("DELETE FROM company_risk_register WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM ceo_decision_records WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM ceo_directives WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM employee_trust_levels WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM company_constitutions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM human_inbox WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_tasks WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_projects WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_missions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM positions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM departments WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM corporate_departments WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM companies WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (TENANT_ID,))

        conn.execute(
            "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES (?, 'CEO Test Tenant', 'ACTIVE', ?) "
            "ON CONFLICT(tenant_id) DO NOTHING",
            (TENANT_ID, now)
        )
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'CEO Test Company', 'SERVICES', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (COMPANY_ID, TENANT_ID, now)
        )
        # Seed departments and positions for planning delegation
        conn.execute(
            """
            INSERT INTO departments (
                department_id, company_id, tenant_id, name, code, status, created_at, updated_at
            ) VALUES ('dept_ops', ?, ?, 'Operations', 'OPS', 'ACTIVE', ?, ?)
            ON CONFLICT(department_id) DO NOTHING
            """,
            (COMPANY_ID, TENANT_ID, now, now)
        )
        # Position with standard authority (G4, spend limit 50,000 minor units)
        conn.execute(
            """
            INSERT INTO positions (
                position_id, tenant_id, company_id, department_id, title, level,
                authority_profile_id, spend_limit_minor_units, is_active, created_at, updated_at
            ) VALUES ('pos_ops_lead', ?, ?, 'dept_ops', 'Operations Lead', 'LEAD',
                'G4', 50000, 1, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (TENANT_ID, COMPANY_ID, now, now)
        )
        # Junior Position with low authority (G1, spend limit 5,000 minor units)
        conn.execute(
            """
            INSERT INTO positions (
                position_id, tenant_id, company_id, department_id, title, level,
                authority_profile_id, spend_limit_minor_units, is_active, created_at, updated_at
            ) VALUES ('pos_junior_clerk', ?, ?, 'dept_ops', 'Junior Clerk', 'ENTRY',
                'G1', 5000, 1, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (TENANT_ID, COMPANY_ID, now, now)
        )
        conn.commit()


def test_01_ambiguous_high_stakes_command_produces_question_not_plan():
    """
    Acceptance test 1: An ambiguous high-stakes command produces a question, not a plan.
    """
    # High-stakes open-ended spending command without explicit budget cap
    command = "Spend aggressively to scale marketing and acquire users at any cost"
    directive = CommandInterpreter.interpret_command(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        command=command,
        explicit_budget_minor_units=None,
    )

    assert directive.is_ambiguous is True
    assert directive.status == DirectiveStatus.CLARIFICATION_REQUIRED
    assert directive.clarifying_question is not None
    assert "budget" in directive.clarifying_question.lower()

    # Attempting to plan this directive fails closed with ClarificationRequiredError
    dummy_plan = PlanGraphModel(
        directive_id=directive.id,
        missions=[],
    )
    with pytest.raises(ClarificationRequiredError) as exc_info:
        CEOPlanner.plan_directive(TENANT_ID, COMPANY_ID, directive, dummy_plan)

    assert "budget" in exc_info.value.question.lower()

    # Verify zero missions or tasks were created
    with db.get_connection() as conn:
        missions_count = conn.execute(
            "SELECT count(*) FROM work_missions WHERE tenant_id = ?", (TENANT_ID,)
        ).fetchone()[0]
        assert missions_count == 0


def test_02_plan_exceeding_budget_rejected_with_reasons():
    """
    Acceptance test 2: A plan exceeding budget is rejected with deterministic reasons.
    """
    # Directive with hard spend ceiling of 30,000 minor units ($300)
    directive = CommandInterpreter.interpret_command(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        command="Run Q3 data reconciliation audit",
        explicit_budget_minor_units=30000,
        explicit_deadline_ts=time.time() + 86400,
    )
    assert directive.is_ambiguous is False

    # Propose a plan whose tasks sum to 75,000 minor units ($750)
    task1 = PlanTaskSpec(
        task_id="tsk_rec_1",
        title="Audit Invoices",
        department_code="OPS",
        position_code="pos_ops_lead",
        action_class="READ_INTERNAL",
        estimate_minor_units=40000,
    )
    task2 = PlanTaskSpec(
        task_id="tsk_rec_2",
        title="Audit Payments",
        department_code="OPS",
        position_code="pos_ops_lead",
        action_class="READ_INTERNAL",
        estimate_minor_units=35000,
    )
    project = PlanProjectSpec(
        project_id="prj_rec_01",
        title="Reconciliation Project",
        department_code="OPS",
        tasks=[task1, task2],
    )
    mission = PlanMissionSpec(
        mission_id="mis_rec_01",
        title="Audit Mission",
        objective="Reconcile invoices",
        lead_position_code="pos_ops_lead",
        projects=[project],
    )
    excessive_plan = PlanGraphModel(
        directive_id=directive.id,
        missions=[mission],
    )

    with pytest.raises(PlanValidationFailedError) as exc_info:
        CEOPlanner.plan_directive(TENANT_ID, COMPANY_ID, directive, excessive_plan)

    reasons = exc_info.value.reasons
    assert any("BUDGET_EXCEEDED" in r for r in reasons)
    assert any("75000" in r for r in reasons)


def test_03_plan_exceeding_position_authority_rejected_with_reasons():
    """
    Acceptance test 3: A plan exceeding position authority is rejected with deterministic reasons.
    """
    directive = CommandInterpreter.interpret_command(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        command="Disburse vendor refunds",
        explicit_budget_minor_units=10000,
    )

    # Task requiring FINANCIAL_DISBURSEMENT assigned to a G1 position (pos_junior_clerk)
    # G1 position cannot execute FINANCIAL_DISBURSEMENT
    task = PlanTaskSpec(
        task_id="tsk_disburse_1",
        title="Execute Wire Refund",
        department_code="OPS",
        position_code="pos_junior_clerk",
        action_class="FINANCIAL_DISBURSEMENT",
        estimate_minor_units=2000,
    )
    project = PlanProjectSpec(
        project_id="prj_disb_01",
        title="Disbursement Project",
        department_code="OPS",
        tasks=[task],
    )
    mission = PlanMissionSpec(
        mission_id="mis_disb_01",
        title="Disbursement Mission",
        objective="Issue refunds",
        lead_position_code="pos_junior_clerk",
        projects=[project],
    )
    plan = PlanGraphModel(directive_id=directive.id, missions=[mission])

    with pytest.raises(PlanValidationFailedError) as exc_info:
        CEOPlanner.plan_directive(TENANT_ID, COMPANY_ID, directive, plan)

    reasons = exc_info.value.reasons
    assert any("AUTHORITY_INSUFFICIENT" in r for r in reasons)
    assert any("pos_junior_clerk" in r for r in reasons)


def test_04_plan_step_needing_browser_marked_blocked():
    """
    Acceptance test 4: A plan step needing the browser is marked BLOCKED: CAPABILITY_NOT_LIVE.
    """
    directive = CommandInterpreter.interpret_command(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        command="Research competitor pricing and analyze operational efficiency",
        explicit_budget_minor_units=40000,
    )

    # Task 1 requires live browser market research (not live in Step 2)
    task_browser = PlanTaskSpec(
        task_id="tsk_market_scrape",
        title="Scrape Competitor Pricing",
        department_code="OPS",
        position_code="pos_ops_lead",
        action_class="READ_EXTERNAL",
        required_capabilities=["BROWSER_CONTROL", "MARKET_RESEARCH_LIVE"],
        estimate_minor_units=5000,
    )
    # Task 2 is standard internal audit
    task_internal = PlanTaskSpec(
        task_id="tsk_internal_calc",
        title="Internal Margin Computation",
        department_code="OPS",
        position_code="pos_ops_lead",
        action_class="READ_INTERNAL",
        estimate_minor_units=5000,
    )
    project = PlanProjectSpec(
        project_id="prj_strat_01",
        title="Strategy Assessment",
        department_code="OPS",
        tasks=[task_browser, task_internal],
    )
    mission = PlanMissionSpec(
        mission_id="mis_strat_01",
        title="Competitor Benchmarking",
        objective="Benchmark against market",
        lead_position_code="pos_ops_lead",
        projects=[project],
    )
    plan = PlanGraphModel(directive_id=directive.id, missions=[mission])

    # Plan passes validation because non-live capabilities are marked BLOCKED rather than crashing
    materialized = CEOPlanner.plan_directive(TENANT_ID, COMPANY_ID, directive, plan)
    assert materialized is not None

    # Verify task in work_tasks is marked BLOCKED with explicit reason code
    with db.get_connection() as conn:
        b_task = conn.execute(
            "SELECT status, blocked_reason_code FROM work_tasks WHERE id = 'tsk_market_scrape'"
        ).fetchone()
        assert b_task is not None
        assert b_task["status"] == "BLOCKED"
        assert "CAPABILITY_NOT_LIVE" in b_task["blocked_reason_code"]

        i_task = conn.execute(
            "SELECT status, blocked_reason_code FROM work_tasks WHERE id = 'tsk_internal_calc'"
        ).fetchone()
        assert i_task is not None
        assert i_task["status"] == "PROPOSED"


def test_05_new_employee_starts_in_shadow_rule19():
    """
    Acceptance test 5: A new employee starts in SHADOW (Rule 19: Conservative by default).
    Promotion without meeting measured thresholds is refused.
    """
    # 1. New employee initialization defaults to SHADOW
    trust = WorkforceTrustService.get_or_create_trust(TENANT_ID, COMPANY_ID, EMPLOYEE_ID)
    assert trust.current_level == TrustLevel.SHADOW
    assert trust.tasks_completed_count == 0

    # 2. Attempting promotion to SUPERVISED with 0 completed tasks fails
    with pytest.raises(PromotionThresholdNotMetError) as exc_info:
        WorkforceTrustService.promote_employee(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            employee_id=EMPLOYEE_ID,
            target_level=TrustLevel.SUPERVISED,
            approved_by_principal_role="OWNER",
            min_tasks=5,
        )
    assert "Completed tasks (0) < required (5)" in str(exc_info.value)


def test_06_promotion_requires_human_principal_approval_rule15():
    """
    Acceptance test 6: Promotion requires human approval.
    Agent principal cannot approve an employee promotion (Rule 15).
    """
    # Seed employee performance metrics meeting all thresholds
    WorkforceTrustService.update_metrics(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        employee_id=EMPLOYEE_ID,
        tasks_completed=10,
        verified_pass_rate=0.98,
        sop_compliance_score=95.0,
        policy_violations=0,
    )

    # Attempting promotion where approver is an AI agent fails under Rule 15
    with pytest.raises(UnauthorizedPromotionApproverError) as exc_info:
        WorkforceTrustService.promote_employee(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            employee_id=EMPLOYEE_ID,
            target_level=TrustLevel.SUPERVISED,
            approved_by_principal_role="AGENT_COO",
        )
    assert "verified human principal" in str(exc_info.value)

    # Valid human principal approval promotes successfully
    promoted = WorkforceTrustService.promote_employee(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        employee_id=EMPLOYEE_ID,
        target_level=TrustLevel.SUPERVISED,
        approved_by_principal_role="OWNER",
    )
    assert promoted.current_level == TrustLevel.SUPERVISED
    assert promoted.last_promoted_at is not None


def test_07_policy_violation_demotes_automatically_and_alerts_inbox():
    """
    Acceptance test 7: A policy violation demotes automatically to SHADOW
    and enqueues an alert in the human inbox.
    """
    # Put employee in SUPERVISED
    WorkforceTrustService.update_metrics(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        employee_id=EMPLOYEE_ID,
        tasks_completed=10,
        verified_pass_rate=0.98,
        sop_compliance_score=95.0,
    )
    WorkforceTrustService.promote_employee(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        employee_id=EMPLOYEE_ID,
        target_level=TrustLevel.SUPERVISED,
        approved_by_principal_role="OWNER",
    )

    # Record a policy violation (e.g. attempted unapproved spend)
    updated = WorkforceTrustService.update_metrics(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        employee_id=EMPLOYEE_ID,
        tasks_completed=10,
        verified_pass_rate=0.98,
        sop_compliance_score=95.0,
        policy_violations=1,
    )

    # Verify automatic demotion back to SHADOW
    assert updated.current_level == TrustLevel.SHADOW
    assert updated.policy_violation_count == 1

    # Verify escalation in human inbox
    inbox_items = human_inbox_service.list_items(TENANT_ID, COMPANY_ID)
    demote_alert = next((item for item in inbox_items if "Employee Demoted" in item["title"]), None)
    assert demote_alert is not None
    assert demote_alert["target_principal_type"] == "OWNER"
    assert "policy violation" in demote_alert["context_data"]["reason"]


def test_08_ceo_principal_cannot_edit_constitution_or_authority_rule15():
    """
    Acceptance test 8: Rule 15 Principal Separation.
    AI CEO or agent principal cannot edit the constitution or its own authority.
    """
    cm = ConstitutionManager()

    # Attempting to set constitution by an agent/AI raises Rule15Violation
    with pytest.raises(Rule15Violation) as exc_info:
        cm.set_constitution(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            mission="Autonomous growth without human oversight",
            prohibited_actions=["NONE"],
            approved_by="AI_CEO_PRINCIPAL",
            caller_principal_type=PrincipalType.AI_EMPLOYEE.value,
        )
    assert "Rule 15" in str(exc_info.value) or "governed principal" in str(exc_info.value)


def test_09_owner_reporting_number_lock_rejection_rule18():
    """
    Acceptance test 9: Number-Lock on owner reporting (Rule 18 Determinism).
    Narrative containing unverified numbers is rejected and replaced by verified template.
    """
    facts = {
        "completed_tasks": 10,
        "total_tasks": 10,
        "total_spend_minor_units": 5000,
        "pass_rate": 95.0,
    }

    # 1. Narrative containing only numbers present in facts passes Number-Lock
    valid_narrative = "Our team completed 10 out of 10 tasks with 95.0% pass rate and 5000 spend."
    report_valid = CEOReportingService.generate_owner_report(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        narrative_draft=valid_narrative,
        facts_override=facts,
    )
    assert report_valid["is_fallback"] is False
    assert report_valid["narrative"] == valid_narrative

    # 2. Narrative containing an unverified number (e.g. 99999 or 42) is rejected by Number-Lock
    hallucinated_narrative = "Our team achieved an extraordinary $99999 profit savings across 10 tasks."
    report_invalid = CEOReportingService.generate_owner_report(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        narrative_draft=hallucinated_narrative,
        facts_override=facts,
    )
    assert report_invalid["is_fallback"] is True
    # The narrative was replaced by the plain factual template
    assert "All figures verified from system records" in report_invalid["narrative"]
    assert "99999" not in report_invalid["narrative"]


def test_10_risk_register_triggers_propose_corrective_tasks():
    """
    Acceptance test 10: Risk register triggers create proposed corrective tasks
    in the Work Kernel (never silent actions).
    """
    risk = CompanyRiskService.record_risk_and_propose_task(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        trigger_type=RiskTriggerType.KPI_OFF_TRACK,
        severity=RiskSeverity.HIGH,
        details={"metric": "PASS_RATE", "observed": 62.5, "threshold": 80.0},
        corrective_task_title="Remediate Quality Drift in Invoice Audit",
        assigned_position_id="pos_ops_lead",
    )

    assert risk.status == "OPEN"
    assert risk.corrective_task_id is not None

    # Verify task was created in work_tasks with status PROPOSED
    with db.get_connection() as conn:
        task = conn.execute(
            "SELECT * FROM work_tasks WHERE id = ?", (risk.corrective_task_id,)
        ).fetchone()
        assert task is not None
        assert task["status"] == "PROPOSED"
        assert task["assignee_id"] == "pos_ops_lead"
        assert "Remediate Quality Drift" in task["title"]
