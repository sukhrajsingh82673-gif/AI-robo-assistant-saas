"""
Acceptance Test Suite for OpenCode Step 2G:
SOP Executor: Step Records, Dry Runs, Code-Verified Postconditions, and Reverse Compensations.

Verifies:
  1. An SOP run produces one record per step, and deleting a step record lowers the computed score.
  2. A step whose postcondition fails stops the instance with FAILED (postconditions verified by code).
  3. Dry-run mode causes zero side effects (querying email sink and document store confirms zero mutations).
  4. Compensations run in reverse order for all completed compensable steps when failure occurs.
  5. A NOT_EXECUTABLE stub is never run (raises SOPNotExecutableError).
  6. Precondition failure halts execution before step action runs.
  7. Mutation checks demonstrating that disabling code invariants breaks acceptance criteria.
"""

import time
import json
import uuid
import pytest

from core.db import db
from core.sop import (
    SOPStepType,
    SOPInstanceStatus,
    SOPVersionStatus,
    SOPStepReversibility,
    SOPStepOutcome,
    SOPNotExecutableError,
    SOPPreconditionFailedError,
    SOPPostconditionFailedError,
    SOPRunRequest,
    sop_definition_service,
    sop_compliance_calculator,
    sop_executor,
    ensure_sop_tables,
)
from core.tools import tool_registry


TENANT_ID = "tnt_sop_test"
COMPANY_ID = "comp_sop_test"
DEPT_ID = "dept_ops_sop"
EXECUTOR_ID = "emp_ops_lead"


@pytest.fixture(autouse=True)
def setup_sop_env():
    """Seeds database schema and clean multi-tenant test scope for SOP execution tests."""
    from core.baseline.outbox import ensure_outbox_tables
    from core.ledger.schema import ensure_ledger_tables
    ensure_sop_tables()
    ensure_outbox_tables()
    ensure_ledger_tables()
    now = time.time()

    with db.get_connection() as conn:
        conn.execute("DELETE FROM sop_compensations WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM sop_step_records WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM sop_instances WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM sop_versions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM sop_definitions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM corporate_departments WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM companies WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (TENANT_ID,))

        conn.execute(
            "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES (?, 'SOP Test Tenant', 'ACTIVE', ?) "
            "ON CONFLICT(tenant_id) DO NOTHING",
            (TENANT_ID, now)
        )
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'SOP Test Company', 'FINTECH', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (COMPANY_ID, TENANT_ID, now)
        )
        conn.execute(
            """
            INSERT INTO corporate_departments (
                department_id, tenant_id, company_id, code, name, cost_center_code,
                operating_budget_usd, headcount_ceiling, current_headcount, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'OPS', 'Operations Dept', 'CC-OPS-01', 50000.0, 10, 1, 'ACTIVE', ?, ?)
            ON CONFLICT(department_id) DO NOTHING
            """,
            (DEPT_ID, TENANT_ID, COMPANY_ID, now, now)
        )
        conn.commit()


def test_01_sop_run_produces_one_record_per_step_and_deletion_lowers_score():
    """
    Sub-Step 2G Acceptance 1:
    An SOP run produces one record per step, and deleting a step record lowers the computed score.
    """
    # 1. Register SOP definition
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-FIN-001",
        title="Three-Step Tax Calculation Playbook",
    )

    # 2. Publish version with 3 executable steps using the deterministic calculator
    steps = [
        {
            "step_number": 1,
            "name": "Calculate Base Amount",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "100 * 5"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "500"}],
        },
        {
            "step_number": 2,
            "name": "Calculate Tax Rate",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "500 * 2"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "1000"}],
        },
        {
            "step_number": 3,
            "name": "Calculate Total With Tax",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "1000 + 500"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "1500"}],
        },
    ]

    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="1.0.0",
        steps=steps,
        author_employee_id=EXECUTOR_ID,
        approved_by_role="EXEC_COO",
    )

    # 3. Execute SOP
    run_req = SOPRunRequest(
        sop_id=sop["sop_id"],
        version_id=version["version_id"],
        executor_id=EXECUTOR_ID,
        context_inputs={},
    )
    result = sop_executor.execute_sop(TENANT_ID, COMPANY_ID, run_req)

    assert result["status"] == SOPInstanceStatus.COMPLETED.value
    assert result["compliance_score"] == 100.0
    assert result["completed_steps"] == 3
    assert result["total_steps"] == 3
    assert len(result["missing_steps"]) == 0

    instance_id = result["instance_id"]

    # Verify exactly 3 records exist in sop_step_records
    with db.get_connection() as conn:
        records = conn.execute(
            "SELECT step_number, outcome, input_hash, step_def_hash, output_hash FROM sop_step_records WHERE instance_id = ? ORDER BY step_number ASC",
            (instance_id,)
        ).fetchall()

    assert len(records) == 3
    assert [r["step_number"] for r in records] == [1, 2, 3]
    for r in records:
        assert r["outcome"] == "PASSED"
        assert len(r["input_hash"]) == 64
        assert len(r["step_def_hash"]) == 64
        assert len(r["output_hash"]) == 64

    # 4. Delete step 2's record and verify compliance score drops
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM sop_step_records WHERE instance_id = ? AND step_number = 2",
            (instance_id,)
        )
        conn.commit()

    lowered_score = sop_compliance_calculator.recompute_instance_score(TENANT_ID, COMPANY_ID, instance_id)

    # Expected: 2 compliant out of 3 = 66.67%
    assert lowered_score < 100.0
    assert lowered_score == 66.67

    # Check updated instance row reflects the lower score
    with db.get_connection() as conn:
        inst_row = conn.execute("SELECT compliance_score FROM sop_instances WHERE id = ?", (instance_id,)).fetchone()
    assert inst_row["compliance_score"] == 66.67


def test_02_sop_postcondition_failure_stops_instance_with_failed():
    """
    Sub-Step 2G Acceptance 2:
    A step whose postcondition fails stops the instance with FAILED.
    Postconditions are evaluated by code, never by the agent.
    """
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-QA-002",
        title="Postcondition Guard Playbook",
    )

    # Step 2 has an impossible postcondition (expected "999.99", real result will be "20")
    steps = [
        {
            "step_number": 1,
            "name": "Step 1 - OK",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "10 + 10"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "20"}],
        },
        {
            "step_number": 2,
            "name": "Step 2 - Bad Postcondition",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "10 + 10"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "999.99"}],
        },
        {
            "step_number": 3,
            "name": "Step 3 - Should Never Execute",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "100 * 100"},
        },
    ]

    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="1.0.0",
        steps=steps,
        author_employee_id=EXECUTOR_ID,
        approved_by_role="EXEC_COO",
    )

    run_req = SOPRunRequest(
        sop_id=sop["sop_id"],
        version_id=version["version_id"],
        executor_id=EXECUTOR_ID,
    )
    result = sop_executor.execute_sop(TENANT_ID, COMPANY_ID, run_req)

    # Instance MUST fail
    assert result["status"] == SOPInstanceStatus.FAILED.value
    assert "Postcondition failed on step 2" in result["error_reason"]

    # Step 3 MUST NEVER have run
    instance_id = result["instance_id"]
    with db.get_connection() as conn:
        records = conn.execute(
            "SELECT step_number, outcome, postconditions_passed FROM sop_step_records WHERE instance_id = ? ORDER BY step_number ASC",
            (instance_id,)
        ).fetchall()

    assert len(records) == 2
    assert records[0]["step_number"] == 1
    assert records[0]["outcome"] == "PASSED"
    assert records[0]["postconditions_passed"] == 1

    assert records[1]["step_number"] == 2
    assert records[1]["outcome"] == "FAILED"
    assert records[1]["postconditions_passed"] == 0


def test_03_sop_dry_run_causes_zero_side_effects():
    """
    Sub-Step 2G Acceptance 3:
    Dry-run mode (dry_run: true) walks the SOP, plans every tool call,
    and returns the plan with zero side effects.
    """
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-DRY-003",
        title="Dry-Run Simulation Playbook",
    )

    steps = [
        {
            "step_number": 1,
            "name": "Simulated Calculation Step",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "42 * 2"},
            "outputs_schema": {"result": "84"},
        },
        {
            "step_number": 2,
            "name": "Simulated Verification Check",
            "step_type": SOPStepType.CHECK.value,
            "inputs": {"expression": "True"},
        },
    ]

    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="1.0.0",
        steps=steps,
        author_employee_id=EXECUTOR_ID,
        approved_by_role="EXEC_COO",
    )

    # Count outbox and ledger events before run
    with db.get_connection() as conn:
        outbox_count_before = conn.execute("SELECT count(*) FROM outbox_events WHERE tenant_id = ?", (TENANT_ID,)).fetchone()[0]
        ledger_count_before = conn.execute("SELECT count(*) FROM journal_entries WHERE tenant_id = ?", (TENANT_ID,)).fetchone()[0]

    run_req = SOPRunRequest(
        sop_id=sop["sop_id"],
        version_id=version["version_id"],
        executor_id=EXECUTOR_ID,
        dry_run=True,
    )
    result = sop_executor.execute_sop(TENANT_ID, COMPANY_ID, run_req)

    assert result["status"] == SOPInstanceStatus.COMPLETED.value
    assert result["dry_run"] is True
    assert result["compliance_score"] == 100.0

    # Verify zero mutations in outbox and ledger
    with db.get_connection() as conn:
        outbox_count_after = conn.execute("SELECT count(*) FROM outbox_events WHERE tenant_id = ?", (TENANT_ID,)).fetchone()[0]
        ledger_count_after = conn.execute("SELECT count(*) FROM journal_entries WHERE tenant_id = ?", (TENANT_ID,)).fetchone()[0]

    assert outbox_count_after == outbox_count_before == 0
    assert ledger_count_after == ledger_count_before == 0


def test_04_sop_compensation_runs_in_reverse_order_for_reversible_failure():
    """
    Sub-Step 2G Acceptance 4:
    If an SOP fails mid-flight, compensations run in reverse order
    for all completed compensable steps.
    """
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-ROLLBACK-004",
        title="Compensating Rollback Playbook",
    )

    steps = [
        {
            "step_number": 1,
            "name": "Step 1 - Compensable Action A",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "100 + 1"},
            "reversibility": SOPStepReversibility.COMPENSABLE.value,
            "compensation_step": {
                "name": "Compensation For Step 1",
                "tool_name": "calculator",
                "inputs": {"expression": "101 - 1"},
            },
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "101"}],
        },
        {
            "step_number": 2,
            "name": "Step 2 - Compensable Action B",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "200 + 2"},
            "reversibility": SOPStepReversibility.COMPENSABLE.value,
            "compensation_step": {
                "name": "Compensation For Step 2",
                "tool_name": "calculator",
                "inputs": {"expression": "202 - 2"},
            },
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "202"}],
        },
        {
            "step_number": 3,
            "name": "Step 3 - Fails Postcondition",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "300 + 3"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "999"}],
        },
    ]

    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="1.0.0",
        steps=steps,
        author_employee_id=EXECUTOR_ID,
        approved_by_role="EXEC_COO",
    )

    run_req = SOPRunRequest(
        sop_id=sop["sop_id"],
        version_id=version["version_id"],
        executor_id=EXECUTOR_ID,
    )
    result = sop_executor.execute_sop(TENANT_ID, COMPANY_ID, run_req)

    assert result["status"] == SOPInstanceStatus.COMPENSATED.value
    assert result["compensations_run"] == 2

    instance_id = result["instance_id"]

    # Verify compensations table recorded in reverse order
    with db.get_connection() as conn:
        compensations = conn.execute(
            "SELECT step_number, compensation_step_name, status, compensated_at FROM sop_compensations WHERE instance_id = ? ORDER BY compensated_at ASC",
            (instance_id,)
        ).fetchall()

    assert len(compensations) == 2
    # Reverse order: Step 2 compensated first, then Step 1
    assert compensations[0]["step_number"] == 2
    assert compensations[0]["compensation_step_name"] == "Compensation For Step 2"
    assert compensations[1]["step_number"] == 1
    assert compensations[1]["compensation_step_name"] == "Compensation For Step 1"


def test_05_sop_not_executable_stub_never_run():
    """
    Sub-Step 2G Acceptance 5:
    A pack SOP stub that has not been defined is NOT_EXECUTABLE and cannot be run.
    """
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-STUB-005",
        title="Unimplemented Industry Pack Stub",
    )

    # Empty steps array marks the version as NOT_EXECUTABLE
    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="0.1.0",
        steps=[],
        author_employee_id=EXECUTOR_ID,
    )

    assert version["status"] == SOPVersionStatus.NOT_EXECUTABLE.value

    run_req = SOPRunRequest(
        sop_id=sop["sop_id"],
        version_id=version["version_id"],
        executor_id=EXECUTOR_ID,
    )

    with pytest.raises(SOPNotExecutableError) as exc_info:
        sop_executor.execute_sop(TENANT_ID, COMPANY_ID, run_req)

    assert "NOT_EXECUTABLE" in str(exc_info.value)

    # Verify no running or completed instances exist for this stub
    with db.get_connection() as conn:
        count = conn.execute("SELECT count(*) FROM sop_instances WHERE sop_id = ?", (sop["sop_id"],)).fetchone()[0]
    assert count == 0


def test_06_sop_precondition_failure_stops_instance():
    """
    Verifies that a step precondition failure stops execution before running the step action.
    """
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-PRE-006",
        title="Precondition Guard Playbook",
    )

    steps = [
        {
            "step_number": 1,
            "name": "Step Requiring Specific Context Parameter",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "100 + 10"},
            "preconditions": [
                {"type": "field_exists", "field": "required_auth_token", "scope": "context"}
            ],
        }
    ]

    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="1.0.0",
        steps=steps,
        author_employee_id=EXECUTOR_ID,
        approved_by_role="EXEC_COO",
    )

    # Context lacks 'required_auth_token'
    run_req = SOPRunRequest(
        sop_id=sop["sop_id"],
        version_id=version["version_id"],
        executor_id=EXECUTOR_ID,
        context_inputs={},
    )
    result = sop_executor.execute_sop(TENANT_ID, COMPANY_ID, run_req)

    assert result["status"] == SOPInstanceStatus.FAILED.value
    assert "Precondition failed" in result["error_reason"]

    instance_id = result["instance_id"]
    with db.get_connection() as conn:
        rec = conn.execute("SELECT preconditions_passed, outcome FROM sop_step_records WHERE instance_id = ?", (instance_id,)).fetchone()

    assert rec["preconditions_passed"] == 0
    assert rec["outcome"] == "FAILED"


def test_07_sop_mutation_checks_rule_8():
    """
    Rule 8 Mutation Checks:
    1. If postconditions are bypassed, invalid outputs wrongly succeed.
    2. If compliance scoring is static, deleting records doesn't drop score.
    """
    sop = sop_definition_service.register_sop(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        department_id=DEPT_ID,
        code="SOP-MUT-007",
        title="Mutation Validation Playbook",
    )

    steps = [
        {
            "step_number": 1,
            "name": "Math Step",
            "step_type": SOPStepType.TOOL.value,
            "tool_name": "calculator",
            "inputs": {"expression": "50 + 50"},
            "postconditions": [{"type": "field_equals", "field": "result", "expected": "100"}],
        }
    ]

    version = sop_definition_service.publish_version(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop["sop_id"],
        semver="1.0.0",
        steps=steps,
        author_employee_id=EXECUTOR_ID,
        approved_by_role="EXEC_COO",
    )

    # Mutation 1: Assert that real condition evaluator catches wrong condition
    cond = {"type": "field_equals", "field": "result", "expected": "999"}
    passed, msg = sop_executor._check_conditions([cond], {}, {"result": "100"})
    assert passed is False
    assert "expected '999', got '100'" in msg

    # Mutation 2: Assert compliance calculator strictly detects missing record
    inst_id = f"test_inst_{uuid.uuid4().hex[:8]}"
    score_data = sop_compliance_calculator.calculate_compliance(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        instance_id=inst_id,
        total_expected_steps=3,
    )
    assert score_data["compliance_score"] == 0.0
    assert score_data["missing_steps"] == [1, 2, 3]
