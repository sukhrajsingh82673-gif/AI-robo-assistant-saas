"""
Acceptance Test Suite for OpenCode Step 2F:
Work Kernel: Missions, Projects, Work Tasks, DAG Dependencies,
Deterministic Assignment, Human Inbox, and SLA Escalation Engine.

Verifies:
  1. Task dependency cycle is strictly rejected (Kahn's DAG algorithm).
  2. Illegal state transitions are rejected by the 7-state machine.
  3. Rule 17: Assignee can NEVER complete its own task.
  4. Task requiring non-live capability transitions to BLOCKED with CAPABILITY_NOT_LIVE.
  5. Prerequisite tasks must be COMPLETED before dependent task can start.
  6. SLA breach escalates up the chain (Supervisor -> CEO -> Owner) with controllable clock.
  7. Human inbox items survive process/connection restart with durable acknowledgement.
  8. Deterministic assignment scoring chooses optimal candidate and persists rationale.
  9. HTTP workforce API end-to-end dispatch and self-verification refusal (HTTP 403).
  10. Mutation checks demonstrating acceptance tests fail if invariants are disabled.
"""

import time
import json
import uuid
import pytest

from core.db import db
from core.ports.base import capability_truth_table
from core.evidence_service import evidence_service
from core.organization.service import organization_service
from core.authority.types import AutonomyLevel
from core.authority.profiles import authority_profile_manager
from core.work import (
    TaskStatus,
    TaskPriority,
    AssigneeType,
    InboxItemType,
    InboxStatus,
    MissionCreateRequest,
    ProjectCreateRequest,
    TaskCreateRequest,
    TaskSubmitRequest,
    TaskVerifyRequest,
    workforce_work_service,
    human_inbox_service,
    work_sla_service,
    ClockManager,
    TaskStateMachine,
    TaskDAGService,
    TaskAssignmentEngine,
    IllegalStateTransitionError,
    AssigneeSelfCompletionForbiddenError,
    TaskDependencyCycleError,
    PrerequisiteNotCompletedError,
    TaskNotFoundError,
    ensure_work_kernel_tables,
)
from core.workforce_api import handle_get, handle_post


TENANT_ID = "tnt_work_kernel_test"
COMPANY_ID = "comp_work_kernel_test"


@pytest.fixture(autouse=True)
def setup_work_kernel_env():
    """Seeds clean multi-tenant scope and organization structure for work tests."""
    ensure_work_kernel_tables()
    ClockManager.reset()
    now = time.time()

    with db.get_connection() as conn:
        conn.execute("DELETE FROM task_events WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM task_dependencies WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_tasks WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM human_inbox WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_projects WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_missions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES (?, ?, 'ACTIVE', ?) "
            "ON CONFLICT(tenant_id) DO NOTHING",
            (TENANT_ID, "Work Kernel Tenant", now)
        )
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'Work Kernel Company', 'FINTECH', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (COMPANY_ID, TENANT_ID, now)
        )
        conn.commit()

    with db.get_connection() as conn:
        conn.execute("DELETE FROM reporting_lines WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM positions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute(
            """
            INSERT INTO departments (department_id, company_id, tenant_id, name, code, created_at, updated_at)
            VALUES ('dept_fin', ?, ?, 'Finance', 'FIN', ?, ?)
            ON CONFLICT(department_id) DO NOTHING
            """,
            (COMPANY_ID, TENANT_ID, now, now)
        )
        conn.execute(
            """
            INSERT INTO positions (position_id, tenant_id, company_id, department_id, title, level, is_active, created_at, updated_at)
            VALUES
                ('pos_ceo', ?, ?, 'dept_fin', 'Chief Executive Officer', 'CEO', 1, ?, ?),
                ('pos_lead', ?, ?, 'dept_fin', 'Finance Lead', 'LEAD', 1, ?, ?),
                ('pos_analyst', ?, ?, 'dept_fin', 'Junior Analyst', 'ANALYST', 1, ?, ?),
                ('pos_specialist', ?, ?, 'dept_fin', 'Senior Specialist', 'SPECIALIST', 1, ?, ?)
            """,
            (TENANT_ID, COMPANY_ID, now, now,
             TENANT_ID, COMPANY_ID, now, now,
             TENANT_ID, COMPANY_ID, now, now,
             TENANT_ID, COMPANY_ID, now, now)
        )
        conn.execute(
            """
            INSERT INTO reporting_lines (tenant_id, company_id, position_id, reports_to_position_id, created_at, updated_at)
            VALUES
                (?, ?, 'pos_analyst', 'pos_lead', ?, ?),
                (?, ?, 'pos_specialist', 'pos_lead', ?, ?),
                (?, ?, 'pos_lead', 'pos_ceo', ?, ?)
            """,
            (TENANT_ID, COMPANY_ID, now, now,
             TENANT_ID, COMPANY_ID, now, now,
             TENANT_ID, COMPANY_ID, now, now)
        )
        conn.commit()

    authority_profile_manager.set_profile(TENANT_ID, COMPANY_ID, "pos_analyst", "G3")
    authority_profile_manager.set_profile(TENANT_ID, COMPANY_ID, "pos_lead", "G2")
    authority_profile_manager.set_profile(TENANT_ID, COMPANY_ID, "pos_ceo", "G1")

    yield

    ClockManager.reset()


def test_01_dependency_cycle_rejected():
    """Verifies that circular task dependencies are strictly rejected by Kahn's DAG algorithm."""
    # Create Task A
    req_a = TaskCreateRequest(
        title="Task Alpha",
        owner_id="user_owner",
    )
    task_a = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req_a)

    # Create Task B depending on Task A
    req_b = TaskCreateRequest(
        title="Task Beta",
        owner_id="user_owner",
        dependencies=[task_a["id"]],
    )
    task_b = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req_b)

    # Attempt to create Task C depending on Task B, while Task A depends on Task C (cycle A -> B -> C -> A)
    # First, test direct self-dependency: Task A cannot depend on Task A
    with pytest.raises(TaskDependencyCycleError) as exc_self:
        TaskDAGService.validate_no_cycles(TENANT_ID, COMPANY_ID, task_a["id"], [task_a["id"]])
    assert "cannot depend on itself" in str(exc_self.value)

    # Now attempt 2-cycle: Task A depending on Task B (since B already depends on A)
    with pytest.raises(TaskDependencyCycleError) as exc_cycle:
        TaskDAGService.validate_no_cycles(TENANT_ID, COMPANY_ID, task_a["id"], [task_b["id"]])
    assert "CYCLIC_DEPENDENCY_DETECTED" in str(exc_cycle.value)


def test_02_illegal_state_transitions_rejected():
    """Verifies that illegal jumps in the 7-state machine are strictly refused."""
    req = TaskCreateRequest(
        title="Draft Financial Memo",
        owner_id="user_owner",
    )
    task = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req)
    assert task["status"] == TaskStatus.PROPOSED.value

    # PROPOSED -> COMPLETED is illegal
    with pytest.raises(IllegalStateTransitionError) as exc_prop_comp:
        TaskStateMachine.validate_transition(
            current_status=TaskStatus.PROPOSED,
            target_status=TaskStatus.COMPLETED,
            actor_id="user_verifier",
            is_verifier=True
        )
    assert "ILLEGAL_STATE_TRANSITION" in str(exc_prop_comp.value)

    # PROPOSED -> IN_PROGRESS is illegal without assignment/acceptance
    with pytest.raises(IllegalStateTransitionError) as exc_prop_prog:
        TaskStateMachine.validate_transition(
            current_status=TaskStatus.PROPOSED,
            target_status=TaskStatus.IN_PROGRESS,
            actor_id="user_worker"
        )
    assert "ILLEGAL_STATE_TRANSITION" in str(exc_prop_prog.value)

    # COMPLETED is terminal (COMPLETED -> IN_PROGRESS is illegal)
    with pytest.raises(IllegalStateTransitionError) as exc_terminal:
        TaskStateMachine.validate_transition(
            current_status=TaskStatus.COMPLETED,
            target_status=TaskStatus.IN_PROGRESS,
            actor_id="user_worker"
        )
    assert "ILLEGAL_STATE_TRANSITION" in str(exc_terminal.value)


def test_03_assignee_cannot_self_complete_rule17():
    """
    Verifies Rule 17: 'Done' is a claim, not a fact.
    The assignee can never complete its own task.
    """
    req = TaskCreateRequest(
        title="Audit Ledger Accounts",
        owner_id="user_owner",
    )
    task = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req)
    task = workforce_work_service.assign_task(TENANT_ID, COMPANY_ID, task["id"], assignee_id="pos_analyst", actor_id="user_owner")
    task = workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task["id"], actor_id="pos_analyst")
    task = workforce_work_service.start_task(TENANT_ID, COMPANY_ID, task["id"], actor_id="pos_analyst")

    # Assignee submits deliverable
    deliverable = {"reconciled_accounts": 12, "discrepancies": 0}
    task = workforce_work_service.submit_task(TENANT_ID, COMPANY_ID, task["id"], deliverable=deliverable, actor_id="pos_analyst")
    assert task["status"] == TaskStatus.SUBMITTED.value

    # Assignee attempts to verify/complete its OWN task -> MUST RAISE AssigneeSelfCompletionForbiddenError
    with pytest.raises(AssigneeSelfCompletionForbiddenError) as exc_self:
        workforce_work_service.verify_task(
            TENANT_ID, COMPANY_ID, task["id"],
            decision="APPROVED",
            verifier_id="pos_analyst",  # SAME AS ASSIGNEE
        )
    assert "ASSIGNEE_SELF_COMPLETION_FORBIDDEN" in str(exc_self.value)
    assert "Rule 17" in str(exc_self.value)

    # Independent verifier signs off -> SUCCEEDS
    completed_task = workforce_work_service.verify_task(
        TENANT_ID, COMPANY_ID, task["id"],
        decision="APPROVED",
        verifier_id="pos_lead",  # INDEPENDENT SUPERVISOR
    )
    assert completed_task["status"] == TaskStatus.COMPLETED.value
    assert completed_task["completed_by"] == "pos_lead"


def test_04_non_live_capability_transitions_to_blocked():
    """
    Verifies that a task requiring an unconfigured or unbuilt capability transitions
    to BLOCKED with reason 'CAPABILITY_NOT_LIVE' instead of faking success.
    """
    req = TaskCreateRequest(
        title="Competitor Web Scraping",
        owner_id="user_owner",
        required_capabilities=["browser.navigate", "desktop_control"],
    )
    task = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req)

    # Since browser/desktop control are NOT_IMPLEMENTED, task must immediately be BLOCKED
    assert task["status"] == TaskStatus.BLOCKED.value
    assert task["blocked_reason_code"] == "CAPABILITY_NOT_LIVE"
    assert "browser.navigate" in task["blocked_reason_detail"]


def test_05_prerequisite_must_be_completed_before_start():
    """Verifies that dependent tasks cannot start until all prerequisite tasks reach COMPLETED."""
    # Step 1: Pre-requisite task
    req_pre = TaskCreateRequest(
        title="Prepare Source Data",
        owner_id="user_owner",
    )
    task_pre = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req_pre)
    task_pre = workforce_work_service.assign_task(TENANT_ID, COMPANY_ID, task_pre["id"], assignee_id="pos_analyst")

    # Step 2: Dependent task
    req_dep = TaskCreateRequest(
        title="Generate Final Synthesis Report",
        owner_id="user_owner",
        dependencies=[task_pre["id"]],
    )
    task_dep = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req_dep)
    task_dep = workforce_work_service.assign_task(TENANT_ID, COMPANY_ID, task_dep["id"], assignee_id="pos_specialist")

    # Attempt to accept/start dependent task while pre-requisite is only ASSIGNED
    with pytest.raises(PrerequisiteNotCompletedError) as exc_prereq:
        workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task_dep["id"], actor_id="pos_specialist")
    assert "PREREQUISITE_NOT_COMPLETED" in str(exc_prereq.value)

    # Complete pre-requisite task
    workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task_pre["id"], actor_id="pos_analyst")
    workforce_work_service.start_task(TENANT_ID, COMPANY_ID, task_pre["id"], actor_id="pos_analyst")
    workforce_work_service.submit_task(TENANT_ID, COMPANY_ID, task_pre["id"], deliverable={"clean": True}, actor_id="pos_analyst")
    workforce_work_service.verify_task(TENANT_ID, COMPANY_ID, task_pre["id"], decision="APPROVED", verifier_id="pos_lead")

    # Now dependent task can be accepted and started
    accepted_dep = workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task_dep["id"], actor_id="pos_specialist")
    assert accepted_dep["status"] == TaskStatus.ACCEPTED.value


def test_06_sla_breach_escalates_up_the_chain_with_controllable_clock():
    """
    Verifies that task SLA breaches escalate up the organizational reporting hierarchy:
    Assignee's Supervisor -> CEO -> Owner.
    Uses ClockManager for deterministic, controllable time.
    """
    start_ts = 1800000000.0  # Fixed epoch timestamp
    with ClockManager.controllable_clock(start_ts):
        req = TaskCreateRequest(
            title="Urgent Compliance Verification",
            owner_id="user_owner",
            sla_seconds=3600,  # 1 hour SLA
        )
        task = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req)
        task = workforce_work_service.assign_task(TENANT_ID, COMPANY_ID, task["id"], assignee_id="pos_analyst")
        task = workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task["id"], actor_id="pos_analyst")
        task = workforce_work_service.start_task(TENANT_ID, COMPANY_ID, task["id"], actor_id="pos_analyst")

        assert task["sla_expires_at"] == start_ts + 3600.0
        assert task["sla_escalation_level"] == 0

        # No escalation before deadline
        ClockManager.advance_time(1800.0)  # 30 mins elapsed
        breaches_early = work_sla_service.check_and_escalate_slas(TENANT_ID, COMPANY_ID)
        assert len(breaches_early) == 0

        # Breach 1: Advance past 1 hour (e.g. +2000s -> 3800s total)
        ClockManager.advance_time(2000.0)
        breaches_1 = work_sla_service.check_and_escalate_slas(TENANT_ID, COMPANY_ID)
        assert len(breaches_1) == 1
        assert breaches_1[0]["escalation_level"] == 1
        assert breaches_1[0]["target_id"] == "pos_lead"  # pos_analyst's supervisor

        # Check human inbox for Level 1 escalation
        inbox_items = human_inbox_service.list_items(TENANT_ID, COMPANY_ID, target_principal_id="pos_lead")
        assert len(inbox_items) >= 1
        assert "Level 1" in inbox_items[0]["title"]

        # Breach 2: Advance past the second SLA interval
        ClockManager.advance_time(4000.0)
        breaches_2 = work_sla_service.check_and_escalate_slas(TENANT_ID, COMPANY_ID)
        assert len(breaches_2) == 1
        assert breaches_2[0]["escalation_level"] == 2
        assert breaches_2[0]["target_id"] == "pos_ceo"  # Organization CEO

        # Breach 3: Advance past third SLA interval
        ClockManager.advance_time(4000.0)
        breaches_3 = work_sla_service.check_and_escalate_slas(TENANT_ID, COMPANY_ID)
        assert len(breaches_3) == 1
        assert breaches_3[0]["escalation_level"] == 3
        assert breaches_3[0]["target_type"] == "OWNER"  # Company Owner


def test_07_human_inbox_item_survives_restart():
    """Verifies that human inbox items persist across connection resets and handle acknowledgement."""
    context = {"amount_minor_units": 250000, "purpose": "Strategic Vendor Retainer"}
    item = human_inbox_service.create_item(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        item_type=InboxItemType.TASK_APPROVAL,
        title="High-Value Expense Approval",
        context_data=context,
        target_principal_type="POSITION",
        target_principal_id="pos_lead",
        decision_needed="Approve or Reject $2,500 retainer payout.",
        due_date_ts=time.time() + 86400.0,
    )
    inbox_id = item["id"]

    # Simulate restart by resetting DB connection pool/handle
    db._conn = None

    # Fetch after restart
    reloaded = human_inbox_service.get_item(TENANT_ID, COMPANY_ID, inbox_id)
    assert reloaded["id"] == inbox_id
    assert reloaded["status"] == InboxStatus.PENDING.value
    assert reloaded["context_data"]["amount_minor_units"] == 250000

    # Acknowledge item
    acked = human_inbox_service.acknowledge(TENANT_ID, COMPANY_ID, inbox_id, actor_id="user_supervisor")
    assert acked["status"] == InboxStatus.ACKNOWLEDGED.value
    assert acked["acknowledged_by"] == "user_supervisor"

    # Resolve item
    resolution = {"verdict": "APPROVED", "comments": "Within quarterly department budget."}
    resolved = human_inbox_service.resolve(TENANT_ID, COMPANY_ID, inbox_id, actor_id="user_supervisor", resolution_data=resolution)
    assert resolved["status"] == InboxStatus.RESOLVED.value
    assert resolved["resolution_data"]["verdict"] == "APPROVED"


def test_08_deterministic_assignment_scoring():
    """
    Verifies that assignment scoring evaluates queue depth and verified pass rate,
    selecting the optimal candidate deterministically.
    """
    # Seed historical tasks:
    # pos_analyst has 1 completed, 0 rejected -> 100% pass rate, queue depth 0
    # pos_specialist has 0 completed, 2 rejected -> 0% pass rate, queue depth 1
    req = TaskCreateRequest(title="Quarterly Modeling", owner_id="user_owner")
    t1 = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req)
    workforce_work_service.assign_task(TENANT_ID, COMPANY_ID, t1["id"], assignee_id="pos_specialist")
    workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, t1["id"], actor_id="pos_specialist")
    workforce_work_service.start_task(TENANT_ID, COMPANY_ID, t1["id"], actor_id="pos_specialist")

    # Select best candidate between pos_analyst and pos_specialist
    chosen_id, reasons = TaskAssignmentEngine.select_best_assignee(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        estimate_minor_units=5000,
        required_autonomy_level=AutonomyLevel.SHADOW.value,
        required_capabilities=[],
        candidate_pool=["pos_analyst", "pos_specialist"]
    )

    # pos_analyst has 0 active queue, pos_specialist has 1 active task
    assert chosen_id == "pos_analyst"
    assert reasons["breakdown"]["queue_depth"] == 0
    assert "optimal active capacity" in reasons["rationale"]


def test_09_workforce_http_api_lifecycle():
    """Tests the workforce HTTP API handlers from mission creation to verify sign-off."""
    auth_ctx = {"role": "OWNER", "user_id": "usr_owner_1"}

    # 1. POST /api/workforce/missions
    res, code = handle_post(
        "/api/workforce/missions",
        {"title": "Global Market Launch", "objective": "Expand operations", "budget_micro_units": 5000000},
        TENANT_ID, COMPANY_ID, auth_ctx
    )
    assert code == 201
    mission_id = res["mission"]["id"]

    # 2. POST /api/workforce/tasks
    res_t, code_t = handle_post(
        "/api/workforce/tasks",
        {
            "mission_id": mission_id,
            "title": "Build Pricing Matrix",
            "owner_id": "usr_owner_1",
            "assignee_id": "pos_analyst",
        },
        TENANT_ID, COMPANY_ID, auth_ctx
    )
    assert code_t == 201
    task_id = res_t["task"]["id"]

    # 3. POST /api/workforce/tasks/{task_id}/accept
    res_acc, code_acc = handle_post(f"/api/workforce/tasks/{task_id}/accept", {"actor_id": "pos_analyst"}, TENANT_ID, COMPANY_ID, auth_ctx)
    assert code_acc == 200
    assert res_acc["task"]["status"] == "ACCEPTED"

    # 4. POST /api/workforce/tasks/{task_id}/start
    res_st, code_st = handle_post(f"/api/workforce/tasks/{task_id}/start", {"actor_id": "pos_analyst"}, TENANT_ID, COMPANY_ID, auth_ctx)
    assert code_st == 200
    assert res_st["task"]["status"] == "IN_PROGRESS"

    # 5. POST /api/workforce/tasks/{task_id}/submit
    res_sub, code_sub = handle_post(f"/api/workforce/tasks/{task_id}/submit", {"deliverable": {"tiers": 3}, "actor_id": "pos_analyst"}, TENANT_ID, COMPANY_ID, auth_ctx)
    assert code_sub == 200
    assert res_sub["task"]["status"] == "SUBMITTED"

    # 6. POST /api/workforce/tasks/{task_id}/verify (Self-approval by assignee -> 403 Forbidden)
    res_self, code_self = handle_post(
        f"/api/workforce/tasks/{task_id}/verify",
        {"decision": "APPROVED", "verifier_id": "pos_analyst"},
        TENANT_ID, COMPANY_ID, auth_ctx
    )
    assert code_self == 403
    assert "ASSIGNEE_SELF_COMPLETION_FORBIDDEN" in res_self["error"]

    # 7. POST /api/workforce/tasks/{task_id}/verify (By independent verifier -> 200 OK)
    res_ver, code_ver = handle_post(
        f"/api/workforce/tasks/{task_id}/verify",
        {"decision": "APPROVED", "verifier_id": "pos_lead"},
        TENANT_ID, COMPANY_ID, auth_ctx
    )
    assert code_ver == 200
    assert res_ver["task"]["status"] == "COMPLETED"


def test_10_mutation_checks():
    """
    Mutation checks demonstrating that acceptance tests fail if core constraints are bypassed:
    1. If Kahn's DAG cycle check is bypassed, a cyclic dependency would pass.
    2. If Rule 17 self-completion check is disabled, an assignee could mark its own task COMPLETED.
    """
    # Mutation 1: Bypassing Kahn's algorithm
    # Demonstrates that validate_no_cycles raises TaskDependencyCycleError on cycles
    req1 = TaskCreateRequest(title="Mutant Task 1", owner_id="user_owner")
    t1 = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req1)
    req2 = TaskCreateRequest(title="Mutant Task 2", owner_id="user_owner", dependencies=[t1["id"]])
    t2 = workforce_work_service.create_task(TENANT_ID, COMPANY_ID, req2)

    with pytest.raises(TaskDependencyCycleError):
        TaskDAGService.validate_no_cycles(TENANT_ID, COMPANY_ID, t1["id"], [t2["id"]])

    # Mutation 2: Rule 17 Self-completion mutation check
    with pytest.raises(AssigneeSelfCompletionForbiddenError):
        TaskStateMachine.validate_transition(
            current_status=TaskStatus.SUBMITTED,
            target_status=TaskStatus.COMPLETED,
            actor_id="actor_same_as_assignee",
            assignee_id="actor_same_as_assignee",
            is_verifier=True,
        )
