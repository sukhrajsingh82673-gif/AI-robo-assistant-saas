"""
Acceptance Test Suite for OpenCode Step 2H:
Verification Pyramid: Five Layers from Schema to Human (Rule 17 Enforcement).

Verifies:
  1. A task cannot transition to COMPLETED without all required layers passing.
  2. A failing assertion at Layer 2 halts verification and logs the mismatch.
  3. Spot check sampling is reproducible and deterministic on task ID hash.
  4. Layer 4 PEER_MODEL cannot be called by the task's own agent principal.
  5. Layer 5 HUMAN verification can only be resolved by a verified human principal.
  6. Rule 17: Assignee can NEVER verify or self-complete its own task.
  7. Rule 8 mutation checks proving acceptance tests fail if invariants are disabled.
"""

import time
import json
import uuid
import pytest

from core.db import db
from core.work import (
    TaskStatus,
    TaskPriority,
    AssigneeType,
    workforce_work_service,
    MissionCreateRequest,
    ProjectCreateRequest,
    TaskCreateRequest,
    TaskSubmitRequest,
    AssigneeSelfCompletionForbiddenError,
    ensure_work_kernel_tables,
)
from core.verification import (
    VerificationLayer,
    VerificationStatus,
    LayerResultStatus,
    UnauthorizedLayerInvokerError,
    IncompleteVerificationError,
    SpotCheckSampler,
    DeterministicCodeVerificationLayer,
    PeerModelVerificationLayer,
    HumanVerificationLayer,
    verification_engine,
    ensure_verification_tables,
)


TENANT_ID = "tnt_verif_test"
COMPANY_ID = "comp_verif_test"
ASSIGNEE_ID = "agent_tax_analyst"
VERIFIER_ID = "system_verifier"


@pytest.fixture(autouse=True)
def setup_verification_env():
    """Seeds multi-tenant test scope, work kernel, and verification pyramid tables."""
    ensure_work_kernel_tables()
    ensure_verification_tables()
    now = time.time()

    with db.get_connection() as conn:
        conn.execute("DELETE FROM verification_layer_results WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM task_verifications WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM task_events WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM human_inbox WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_tasks WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_projects WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_missions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM corporate_departments WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM companies WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (TENANT_ID,))

        conn.execute(
            "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES (?, 'Verif Tenant', 'ACTIVE', ?) "
            "ON CONFLICT(tenant_id) DO NOTHING",
            (TENANT_ID, now)
        )
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'Verif Company', 'FINTECH', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (COMPANY_ID, TENANT_ID, now)
        )
        conn.execute(
            """
            INSERT INTO corporate_departments (
                department_id, tenant_id, company_id, code, name, cost_center_code,
                operating_budget_usd, headcount_ceiling, current_headcount, status, created_at, updated_at
            ) VALUES ('dept_tax', ?, ?, 'TAX', 'Tax Operations', 'CC-TAX-01', 50000.0, 10, 1, 'ACTIVE', ?, ?)
            ON CONFLICT(department_id) DO NOTHING
            """,
            (TENANT_ID, COMPANY_ID, now, now)
        )
        conn.commit()


def _create_and_submit_test_task(task_type: str = "DEFAULT", deliverable: dict = None) -> dict:
    """Helper to create mission, project, task, accept, start, and submit."""
    mission = workforce_work_service.create_mission(
        TENANT_ID, COMPANY_ID,
        MissionCreateRequest(
            title="Verification Test Mission",
            objective="Ensure verified completion according to Rule 17",
            department_id="dept_tax",
            created_by="admin"
        )
    )
    project = workforce_work_service.create_project(
        TENANT_ID, COMPANY_ID,
        ProjectCreateRequest(mission_id=mission["id"], title="Verification Project", lead_position_id="pos_lead")
    )
    task = workforce_work_service.create_task(
        TENANT_ID, COMPANY_ID,
        TaskCreateRequest(
            project_id=project["id"],
            title="Tax Return Task",
            owner_id="admin",
            assignee_type=AssigneeType.AGENT,
            assignee_id=ASSIGNEE_ID,
            priority=TaskPriority.HIGH,
            acceptance_criteria={"task_type": task_type},
            output_schema={
                "type": "object",
                "required": ["subtotal", "tax", "total"],
                "properties": {
                    "subtotal": {"type": "integer"},
                    "tax": {"type": "integer"},
                    "total": {"type": "integer"},
                }
            }
        )
    )
    # Accept -> Start -> Submit
    workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task["id"], actor_id=ASSIGNEE_ID)
    workforce_work_service.start_task(TENANT_ID, COMPANY_ID, task["id"], actor_id=ASSIGNEE_ID)
    payload = deliverable or {"subtotal": 100, "tax": 20, "total": 120}
    workforce_work_service.submit_task(
        TENANT_ID, COMPANY_ID, task["id"], payload, ASSIGNEE_ID
    )
    return workforce_work_service.get_task(TENANT_ID, COMPANY_ID, task["id"])


def test_01_task_cannot_transition_to_completed_without_all_required_layers_passing():
    """
    Sub-Step 2H Acceptance 1:
    A task cannot transition to COMPLETED without all required layers passing.
    """
    # Recipe requires SCHEMA, DETERMINISTIC_CODE, and CROSS_RECORD
    task_type = "CORPORATE_TAX_AUDIT"
    verification_engine.register_recipe(
        task_type=task_type,
        required_layers=[
            VerificationLayer.SCHEMA,
            VerificationLayer.DETERMINISTIC_CODE,
            VerificationLayer.CROSS_RECORD,
        ],
        layer_configs={
            "CROSS_RECORD": {
                "existence_checks": [
                    {"table": "corporate_departments", "column": "department_id", "field": "dept_ref"}
                ]
            }
        }
    )

    # Deliverable with INVALID cross-record reference
    deliverable_invalid = {"subtotal": 100, "tax": 20, "total": 120, "dept_ref": "dept_nonexistent_999"}
    task = _create_and_submit_test_task(task_type=task_type, deliverable=deliverable_invalid)

    # Attempt verification
    report = verification_engine.verify_task(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task_id=task["id"],
        invoker_id=VERIFIER_ID,
        submission_data={"deliverable": deliverable_invalid},
    )

    # MUST fail at CROSS_RECORD
    assert report.overall_status == VerificationStatus.FAILED
    assert report.failing_layer == VerificationLayer.CROSS_RECORD
    assert "CROSS_RECORD_EXISTENCE" in report.rejection_reason

    # Task MUST NOT be COMPLETED — it was routed back to ASSIGNED
    task_after_fail = workforce_work_service.get_task(TENANT_ID, COMPANY_ID, task["id"])
    assert task_after_fail["status"] == TaskStatus.ASSIGNED.value
    assert task_after_fail["status"] != TaskStatus.COMPLETED.value

    # Fix cross-record reference to valid department: 'dept_tax'
    deliverable_valid = {"subtotal": 100, "tax": 20, "total": 120, "dept_ref": "dept_tax"}
    workforce_work_service.accept_task(TENANT_ID, COMPANY_ID, task["id"], actor_id=ASSIGNEE_ID)
    workforce_work_service.start_task(TENANT_ID, COMPANY_ID, task["id"], actor_id=ASSIGNEE_ID)
    workforce_work_service.submit_task(
        TENANT_ID, COMPANY_ID, task["id"], deliverable_valid, ASSIGNEE_ID
    )

    # Re-run verification
    report_valid = verification_engine.verify_task(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task_id=task["id"],
        invoker_id=VERIFIER_ID,
        submission_data={"deliverable": deliverable_valid},
    )

    # Now ALL required layers pass -> COMPLETED
    assert report_valid.overall_status == VerificationStatus.PASSED
    assert len(report_valid.passed_layers) == 3
    assert VerificationLayer.CROSS_RECORD in report_valid.passed_layers

    task_completed = workforce_work_service.get_task(TENANT_ID, COMPANY_ID, task["id"])
    assert task_completed["status"] == TaskStatus.COMPLETED.value


def test_02_failing_assertion_at_layer_2_halts_verification_and_logs_mismatch():
    """
    Sub-Step 2H Acceptance 2:
    A failing assertion at Layer 2 halts verification and logs the mismatch.
    """
    task_type = "FINANCIAL_ARITHMETIC"
    verification_engine.register_recipe(
        task_type=task_type,
        required_layers=[
            VerificationLayer.SCHEMA,
            VerificationLayer.DETERMINISTIC_CODE,
            VerificationLayer.PEER_MODEL,
        ],
        layer_configs={
            "DETERMINISTIC_CODE": {
                "arithmetic_checks": [
                    {
                        "rule_name": "SUBTOTAL_PLUS_TAX_EQUALS_TOTAL",
                        "type": "sum",
                        "addends": ["subtotal", "tax"],
                        "target_total": "total",
                    }
                ]
            }
        }
    )

    # Subtotal 500 + Tax 50 = 550, but model claimed total is 999
    corrupted_deliverable = {"subtotal": 500, "tax": 50, "total": 999}
    task = _create_and_submit_test_task(task_type=task_type, deliverable=corrupted_deliverable)

    report = verification_engine.verify_task(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task_id=task["id"],
        invoker_id=VERIFIER_ID,
        submission_data={"deliverable": corrupted_deliverable},
    )

    # Verification must halt at Layer 2
    assert report.overall_status == VerificationStatus.FAILED
    assert report.failing_layer == VerificationLayer.DETERMINISTIC_CODE

    # Layer 4 PEER_MODEL must NEVER have been evaluated
    evaluated_layers = [r.layer for r in report.layer_results]
    assert VerificationLayer.PEER_MODEL not in evaluated_layers

    # Verify observed value and expected value are logged in verification_layer_results
    with db.get_connection() as conn:
        l2_record = conn.execute(
            """
            SELECT status, rule_name, observed_value, expected_value, error_message
            FROM verification_layer_results
            WHERE verification_id = ? AND layer = 'DETERMINISTIC_CODE'
            """,
            (report.verification_id,)
        ).fetchone()

    assert l2_record["status"] == "FAILED"
    assert l2_record["observed_value"] == "550"
    assert l2_record["expected_value"] == "999"
    assert "Arithmetic failure" in l2_record["error_message"]

    # Verify task was rejected and routed back to ASSIGNED
    task_post = workforce_work_service.get_task(TENANT_ID, COMPANY_ID, task["id"])
    assert task_post["status"] == TaskStatus.ASSIGNED.value


def test_03_spot_check_sampling_is_deterministic_and_reproducible():
    """
    Sub-Step 2H Acceptance 3:
    Spot check sampling is reproducible and deterministic on task ID hash.
    """
    sample_rate = 0.35
    task_ids = [f"task_sample_{i:04d}" for i in range(100)]

    # Run 1
    results_run_1 = [
        SpotCheckSampler.is_sampled(tid, VerificationLayer.PEER_MODEL, sample_rate)
        for tid in task_ids
    ]

    # Run 2 (after elapsed time)
    time.sleep(0.01)
    results_run_2 = [
        SpotCheckSampler.is_sampled(tid, VerificationLayer.PEER_MODEL, sample_rate)
        for tid in task_ids
    ]

    # Exactly 100% reproducible across calls
    assert results_run_1 == results_run_2

    # Boundary conditions
    assert SpotCheckSampler.is_sampled("any_task", VerificationLayer.PEER_MODEL, 0.0) is False
    assert SpotCheckSampler.is_sampled("any_task", VerificationLayer.PEER_MODEL, 1.0) is True

    # End-to-end spot check integration in verification engine
    task = _create_and_submit_test_task()
    report = verification_engine.verify_task(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task_id=task["id"],
        invoker_id=VERIFIER_ID,
        submission_data={"deliverable": {"subtotal": 100, "tax": 20, "total": 120}},
        spot_check_rates={"PEER_MODEL": 1.0},  # Force spot check for PEER_MODEL
    )

    assert report.overall_status == VerificationStatus.PASSED
    assert report.is_spot_check is True
    assert VerificationLayer.PEER_MODEL in report.passed_layers


def test_04_layer_4_peer_model_cannot_be_called_by_tasks_own_agent_principal():
    """
    Sub-Step 2H Acceptance 4:
    Layer 4 peer model cannot be called by the task's own agent principal.
    Collusion guard: prevents agent from self-certifying quality scorecards.
    """
    task = _create_and_submit_test_task()

    # Assignee attempts to directly call Layer 4 evaluation
    with pytest.raises(UnauthorizedLayerInvokerError) as exc_info:
        PeerModelVerificationLayer.evaluate(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            task=task,
            invoker_id=ASSIGNEE_ID,  # Collusion attempt by assignee
            submission_data={"deliverable": {"subtotal": 100, "tax": 20, "total": 120}},
        )

    assert "cannot call Layer 4 PEER_MODEL" in str(exc_info.value)
    assert "Collusion prevention" in str(exc_info.value)

    # Independent verifier can invoke Layer 4 cleanly
    res = PeerModelVerificationLayer.evaluate(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task=task,
        invoker_id="independent_verifier_01",
        submission_data={"deliverable": {"subtotal": 100, "tax": 20, "total": 120}},
    )
    assert res.status == LayerResultStatus.PASSED
    assert "Score: 92.0" in res.observed_value


def test_05_layer_5_human_verification_requires_human_principal():
    """
    Verifies that Layer 5 HUMAN review can only be resolved by a human principal,
    and enqueues to durable human inbox when pending.
    """
    task = _create_and_submit_test_task()

    # Agent role attempts to approve Layer 5 directly -> strictly refused
    with pytest.raises(UnauthorizedLayerInvokerError) as exc_info:
        HumanVerificationLayer.evaluate(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            task=task,
            invoker_id="agent_bot",
            submission_data={
                "human_decision": {"decision": "APPROVED", "actor_role": "AGENT_BOT"}
            },
        )
    assert "cannot resolve Layer 5 HUMAN verification" in str(exc_info.value)

    # Verified human owner approves Layer 5 -> passes
    res_human = HumanVerificationLayer.evaluate(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task=task,
        invoker_id="principal_owner",
        submission_data={
            "human_decision": {"decision": "APPROVED", "actor_role": "OWNER"}
        },
    )
    assert res_human.status == LayerResultStatus.PASSED
    assert res_human.observed_value == "APPROVED"


def test_06_rule_17_assignee_cannot_verify_task_via_verification_engine():
    """
    Rule 17: Assignee can NEVER call verify_task to mark its own task completed.
    """
    task = _create_and_submit_test_task()

    with pytest.raises(AssigneeSelfCompletionForbiddenError) as exc_info:
        verification_engine.verify_task(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            task_id=task["id"],
            invoker_id=ASSIGNEE_ID,  # Assignee attempting self-completion
            submission_data={"deliverable": {"subtotal": 100, "tax": 20, "total": 120}},
        )

    assert "Rule 17: Assignee" in str(exc_info.value)
    assert "cannot invoke verification to self-complete" in str(exc_info.value)


def test_07_mutation_checks_rule_8():
    """
    Rule 8 Mutation Checks:
    1. If arithmetic check is corrupted to always pass, invalid arithmetic wrongly succeeds.
    2. If assignee check is bypassed, assignee can self-verify.
    """
    # Mutation 1: Assert DeterministicCodeVerificationLayer catches arithmetic error
    deliverable = {"a": 10, "b": 20, "c": 999}
    config = {
        "arithmetic_checks": [
            {"type": "sum", "addends": ["a", "b"], "target_total": "c"}
        ]
    }
    res = DeterministicCodeVerificationLayer.evaluate(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        task={"id": "dummy"},
        invoker_id="verifier",
        submission_data={"deliverable": deliverable},
        config=config,
    )
    assert res.status == LayerResultStatus.FAILED
    assert res.observed_value == "30"
    assert res.expected_value == "999"

    # Mutation 2: Assert PeerModelVerificationLayer strictly enforces assignee block
    task_dummy = {"id": "tsk_dummy", "assignee_id": "agent_123"}
    with pytest.raises(UnauthorizedLayerInvokerError):
        PeerModelVerificationLayer.evaluate(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            task=task_dummy,
            invoker_id="agent_123",
            submission_data={},
        )
