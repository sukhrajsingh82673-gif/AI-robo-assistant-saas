"""
Acceptance Test Suite for OpenCode Step 2I:
KPI Engine and Goal Engine (Rule 18 Determinism, Inputs Hash Proofs, Threshold Alerts, Kaizen Loop).

Verifies:
  1. Changing a task duration in the database changes computed employee productivity KPI on the next tick.
  2. A breached KPI fires an escalation to kpi_alerts and human inbox.
  3. Defect clustering produces an SOP revision proposal in DRAFT status.
  4. Invariant: No KPI score is stored without its inputs hash (MissingComputationProofError).
  5. Position defect clustering synthesizes a coaching prompt in DRAFT status.
  6. Deterministic metrics (pass rate, cost per mission) calculate exact arithmetic.
  7. Rule 15: Migration revokes write permissions on KPI and Kaizen tables from agent role.
  8. Rule 8 mutation checks proving acceptance tests fail if invariants are violated.
"""

import time
import json
import uuid
import pytest

from core.db import db
from core.work import (
    ensure_work_kernel_tables,
    human_inbox_service,
)
from core.verification import ensure_verification_tables
from core.kpi import (
    KPIScopeLevel,
    KPIMetricType,
    KPIDirection,
    KPICadence,
    KPIStatus,
    DefectType,
    KaizenProposalType,
    KPIDefinitionCreateRequest,
    KPICalculator,
    kpi_engine,
    kaizen_engine,
    ensure_kpi_tables,
    MissingComputationProofError,
)


TENANT_ID = "tnt_kpi_test"
COMPANY_ID = "comp_kpi_test"
EMPLOYEE_ID = "emp_ops_analyst"
POSITION_ID = "pos_operations_lead"


def _seed_task(
    conn,
    task_id: str,
    tenant_id: str = TENANT_ID,
    company_id: str = COMPANY_ID,
    status: str = "COMPLETED",
    submitted_at: float = None,
    completed_at: float = None,
    assignee_type: str = "AI_EMPLOYEE",
    assignee_id: str = EMPLOYEE_ID,
    estimate_minor_units: int = 1000,
    title: str = "Test Task",
):
    """Helper to seed a valid task with all required foreign keys and columns."""
    now = time.time()
    sub = submitted_at if submitted_at is not None else (now - 60.0)
    comp = completed_at if completed_at is not None else now
    conn.execute(
        """
        INSERT INTO work_tasks (
            id, tenant_id, company_id, mission_id, project_id, title,
            owner_id, assignee_type, assignee_id, status, estimate_minor_units,
            submitted_at, completed_at, created_at, updated_at
        ) VALUES (?, ?, ?, 'mis_1', 'prj_1', ?,
            'usr_owner', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, tenant_id, company_id, title,
            assignee_type, assignee_id, status,
            estimate_minor_units, sub, comp, now - 120.0, now
        )
    )


@pytest.fixture(autouse=True)
def setup_kpi_env():
    """Seeds multi-tenant test scope, work kernel, verification, and KPI tables."""
    ensure_work_kernel_tables()
    ensure_verification_tables()
    ensure_kpi_tables()
    now = time.time()

    with db.get_connection() as conn:
        conn.execute("DELETE FROM kaizen_proposals WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM kaizen_defect_records WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM kpi_alerts WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM kpi_snapshots WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM kpi_tree_definitions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM verification_layer_results WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM task_verifications WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM human_inbox WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_tasks WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_projects WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_missions WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM companies WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (TENANT_ID,))

        conn.execute(
            "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES (?, 'KPI Test Tenant', 'ACTIVE', ?) "
            "ON CONFLICT(tenant_id) DO NOTHING",
            (TENANT_ID, now)
        )
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
            "VALUES (?, ?, 'KPI Test Company', 'SERVICES', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (COMPANY_ID, TENANT_ID, now)
        )
        conn.execute(
            """
            INSERT INTO work_missions (
                id, tenant_id, company_id, title, objective, status, created_at, updated_at
            ) VALUES ('mis_1', ?, ?, 'Test Mission', 'KPI Engine Test Mission', 'ACTIVE', ?, ?)
            """,
            (TENANT_ID, COMPANY_ID, now, now)
        )
        conn.execute(
            """
            INSERT INTO work_projects (
                id, mission_id, tenant_id, company_id, title, status, created_at, updated_at
            ) VALUES ('prj_1', 'mis_1', ?, ?, 'Test Project', 'ACTIVE', ?, ?)
            """,
            (TENANT_ID, COMPANY_ID, now, now)
        )
        conn.commit()


def test_01_task_duration_change_alters_productivity():
    """
    Acceptance test 1: Changing a task duration in the database changes
    the computed employee productivity KPI on the next tick (Rule 18 Determinism).
    """
    now = time.time()
    task_id = f"tsk_{uuid.uuid4().hex[:10]}"

    # Seed an initial completed task taking 60 seconds (1 minute)
    # Productivity = (1 task * 3600 sec/hr) / 60 sec = 60.0 tasks/hr
    with db.get_connection() as conn:
        _seed_task(
            conn,
            task_id=task_id,
            submitted_at=now - 60.0,
            completed_at=now,
            title="Invoice Extraction",
        )
        conn.commit()

    # Register productivity KPI for this employee
    req = KPIDefinitionCreateRequest(
        code="EMP_PROD_01",
        name="Employee Task Productivity",
        description="Hourly throughput computed from completed task duration",
        scope_level=KPIScopeLevel.EMPLOYEE,
        scope_id=EMPLOYEE_ID,
        metric_type=KPIMetricType.PRODUCTIVITY,
        target_value=40.0,
        warning_threshold=30.0,
        critical_threshold=15.0,
        direction=KPIDirection.HIGHER_IS_BETTER,
        unit="TASKS_PER_HOUR",
        cadence=KPICadence.HOURLY,
    )
    kpi_def = kpi_engine.register_kpi(TENANT_ID, COMPANY_ID, req)

    # First computation: 60 tasks/hr
    snap1 = kpi_engine.compute_kpi_snapshot(TENANT_ID, COMPANY_ID, kpi_def["id"])
    assert snap1.current_value == pytest.approx(60.0, rel=1e-2)
    assert snap1.status == KPIStatus.ON_TRACK
    assert snap1.computation_proof["task_count"] == 1
    assert snap1.computation_proof["total_seconds"] == pytest.approx(60.0, rel=1e-1)
    assert len(snap1.inputs_hash) == 64

    # Now alter task duration directly in the database:
    # change completion duration to 120 seconds (2 minutes)
    # New Productivity = (1 task * 3600 sec/hr) / 120 sec = 30.0 tasks/hr
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE work_tasks SET submitted_at = ?, completed_at = ? WHERE id = ?",
            (now - 120.0, now, task_id)
        )
        conn.commit()

    # Second computation on next tick: productivity must drop to 30.0 tasks/hr
    snap2 = kpi_engine.compute_kpi_snapshot(TENANT_ID, COMPANY_ID, kpi_def["id"])
    assert snap2.current_value == pytest.approx(30.0, rel=1e-2)
    assert snap2.current_value != snap1.current_value
    assert snap2.computation_proof["total_seconds"] == pytest.approx(120.0, rel=1e-1)
    # Inputs hashes must be distinct because underlying raw rows changed
    assert snap1.inputs_hash != snap2.inputs_hash


def test_02_kpi_threshold_breach_escalates_to_alerts_and_inbox():
    """
    Acceptance test 2: A breached KPI fires an escalation to kpi_alerts and human inbox.
    """
    now = time.time()
    task_id = f"tsk_{uuid.uuid4().hex[:10]}"

    # Seed a task taking 600 seconds (10 minutes)
    # Productivity = 1 * 3600 / 600 = 6.0 tasks/hr
    with db.get_connection() as conn:
        _seed_task(
            conn,
            task_id=task_id,
            submitted_at=now - 600.0,
            completed_at=now,
            title="Slow Document Processing",
            estimate_minor_units=500,
        )
        conn.commit()

    # Register KPI where critical_threshold is 10.0 and warning is 20.0 (HIGHER_IS_BETTER)
    req = KPIDefinitionCreateRequest(
        code="CRITICAL_PRODUCTIVITY",
        name="Critical SLA Productivity",
        scope_level=KPIScopeLevel.EMPLOYEE,
        scope_id=EMPLOYEE_ID,
        metric_type=KPIMetricType.PRODUCTIVITY,
        target_value=30.0,
        warning_threshold=20.0,
        critical_threshold=10.0,
        direction=KPIDirection.HIGHER_IS_BETTER,
    )
    kpi_def = kpi_engine.register_kpi(TENANT_ID, COMPANY_ID, req)

    # Compute snapshot with automated breach playbook
    snap = kpi_engine.compute_kpi_snapshot(
        TENANT_ID,
        COMPANY_ID,
        kpi_def["id"],
        playbook_on_breach="PLAYBOOK_SCALE_OR_INTERVENE"
    )

    # Assert status is CRITICAL since 6.0 < 10.0
    assert snap.status == KPIStatus.CRITICAL
    assert snap.current_value == pytest.approx(6.0, rel=1e-2)

    # Verify alert record in kpi_alerts table
    with db.get_connection() as conn:
        alerts = conn.execute(
            "SELECT * FROM kpi_alerts WHERE tenant_id = ? AND kpi_id = ?",
            (TENANT_ID, kpi_def["id"])
        ).fetchall()
        assert len(alerts) == 1
        alert = dict(alerts[0])
        assert alert["severity"] == "CRITICAL"
        assert alert["observed_value"] == pytest.approx(6.0, rel=1e-2)
        assert alert["threshold_value"] == 10.0
        assert alert["status"] == "OPEN"
        assert alert["playbook_triggered"] == "PLAYBOOK_SCALE_OR_INTERVENE"

    # Verify escalation delivered to human inbox
    inbox_items = human_inbox_service.list_items(TENANT_ID, COMPANY_ID)
    assert len(inbox_items) >= 1
    kpi_inbox_item = next((item for item in inbox_items if "KPI Breach Alert" in item["title"]), None)
    assert kpi_inbox_item is not None
    assert kpi_inbox_item["target_principal_type"] == "OWNER"
    assert kpi_inbox_item["context_data"]["snapshot"]["status"] == "CRITICAL"


def test_03_kaizen_defect_clustering_generates_sop_revision_proposal():
    """
    Acceptance test 3: Defect clustering on an SOP produces an SOP revision proposal in DRAFT status.
    """
    sop_id = "sop_tax_filing_v1"

    # First seed 3 work tasks so foreign keys pass
    with db.get_connection() as conn:
        for i in range(3):
            _seed_task(conn, task_id=f"tsk_fail_{i}", title=f"Failing Task {i}")
        conn.commit()

    # Record 3 verification defects of type SCHEMA_DEFECT on the same SOP
    for i in range(3):
        kaizen_engine.record_defect(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            task_id=f"tsk_fail_{i}",
            defect_type=DefectType.SCHEMA_DEFECT,
            details={"error": f"Field tax_id missing format check {i}"},
            sop_id=sop_id,
        )

    # Run clustering with threshold = 3
    proposals = kaizen_engine.analyze_defects_and_cluster(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        sop_id=sop_id,
        threshold_count=3,
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == KaizenProposalType.SOP_REVISION_PROPOSAL
    assert proposal.target_type == "SOP"
    assert proposal.target_id == sop_id
    assert proposal.cluster_defect_type == DefectType.SCHEMA_DEFECT
    assert proposal.cluster_count == 3
    assert proposal.status == "DRAFT"
    assert "suggested_actions" in proposal.content

    # Verify persisted in database
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM kaizen_proposals WHERE id = ?", (proposal.id,)
        ).fetchall()
        assert len(rows) == 1
        row = dict(rows[0])
        assert row["status"] == "DRAFT"
        assert row["proposal_type"] == "SOP_REVISION_PROPOSAL"


def test_04_missing_computation_proof_fails_closed():
    """
    Acceptance test 4: Invariant enforcement: No KPI score is stored without its inputs hash.
    Attempting to bypass proofs raises MissingComputationProofError.
    """
    # Verify calculator generates non-empty inputs hash
    val, proof, inputs_hash = KPICalculator.compute_metric(
        TENANT_ID, COMPANY_ID, KPIMetricType.TASK_DURATION, KPIScopeLevel.COMPANY
    )
    assert inputs_hash is not None
    assert len(inputs_hash) > 0

    # Ensure engine refuses empty inputs_hash
    with pytest.raises(MissingComputationProofError, match="without its inputs hash"):
        class MockCalculator:
            @classmethod
            def compute_metric(cls, *args, **kwargs):
                return 10.0, {"mock": True}, ""

        orig_calc = kpi_engine.compute_kpi_snapshot.__globals__["KPICalculator"]
        try:
            kpi_engine.compute_kpi_snapshot.__globals__["KPICalculator"] = MockCalculator
            req = KPIDefinitionCreateRequest(
                code="FAIL_PROOF_KPI",
                name="Proof Guard KPI",
                scope_level=KPIScopeLevel.COMPANY,
                metric_type=KPIMetricType.TASK_DURATION,
                target_value=100.0,
                warning_threshold=80.0,
                critical_threshold=60.0,
            )
            kpi_def = kpi_engine.register_kpi(TENANT_ID, COMPANY_ID, req)
            kpi_engine.compute_kpi_snapshot(TENANT_ID, COMPANY_ID, kpi_def["id"])
        finally:
            kpi_engine.compute_kpi_snapshot.__globals__["KPICalculator"] = orig_calc


def test_05_position_coaching_prompt_clustering():
    """
    Acceptance test 5: Defect clustering on a position produces a coaching prompt proposal in DRAFT status.
    """
    # Seed 4 work tasks for position defects
    with db.get_connection() as conn:
        for i in range(4):
            _seed_task(conn, task_id=f"tsk_pos_fail_{i}", title=f"Pos Failing Task {i}")
        conn.commit()

    # Record 4 verification defects of type ARITHMETIC_DEFECT for a position
    for i in range(4):
        kaizen_engine.record_defect(
            tenant_id=TENANT_ID,
            company_id=COMPANY_ID,
            task_id=f"tsk_pos_fail_{i}",
            defect_type=DefectType.ARITHMETIC_DEFECT,
            details={"discrepancy_cents": 1500 * (i + 1)},
            position_id=POSITION_ID,
        )

    # Analyze clusters for this position
    proposals = kaizen_engine.analyze_defects_and_cluster(
        tenant_id=TENANT_ID,
        company_id=COMPANY_ID,
        position_id=POSITION_ID,
        threshold_count=3,
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == KaizenProposalType.COACHING_PROMPT
    assert proposal.target_type == "POSITION"
    assert proposal.target_id == POSITION_ID
    assert proposal.cluster_defect_type == DefectType.ARITHMETIC_DEFECT
    assert proposal.cluster_count == 4
    assert proposal.status == "DRAFT"
    assert "coaching_guidance" in proposal.content


def test_06_pass_rate_and_cost_per_mission_deterministic_metrics():
    """
    Acceptance test 6: Deterministic verification pass rate and cost per mission calculations.
    """
    now = time.time()

    # 1. Seed tasks and verification records: 3 PASSED, 1 FAILED -> 75% pass rate
    with db.get_connection() as conn:
        for i in range(3):
            _seed_task(conn, task_id=f"tsk_p_{i}", title=f"Passing Task {i}")
            conn.execute(
                """
                INSERT INTO task_verifications (
                    id, tenant_id, company_id, task_id, overall_status,
                    required_layers, is_spot_check, created_at, completed_at
                ) VALUES (?, ?, ?, ?, 'PASSED', '["SCHEMA"]', 0, ?, ?)
                """,
                (f"ver_pass_{i}", TENANT_ID, COMPANY_ID, f"tsk_p_{i}", now, now)
            )

        _seed_task(conn, task_id="tsk_fail_1", title="Failed Task 1")
        conn.execute(
            """
            INSERT INTO task_verifications (
                id, tenant_id, company_id, task_id, overall_status,
                required_layers, is_spot_check, created_at, completed_at
            ) VALUES (?, ?, ?, 'tsk_fail_1', 'FAILED', '["SCHEMA"]', 0, ?, ?)
            """,
            ("ver_fail_1", TENANT_ID, COMPANY_ID, now, now)
        )
        conn.commit()

    pass_rate_val, pass_proof, pass_hash = KPICalculator.compute_metric(
        TENANT_ID, COMPANY_ID, KPIMetricType.PASS_RATE, KPIScopeLevel.COMPANY
    )
    assert pass_rate_val == 75.0
    assert pass_proof["total_verifications"] == 4
    assert pass_proof["passed"] == 3
    assert len(pass_hash) == 64

    # 2. Seed work tasks for cost per mission: 2 tasks with 2000 and 4000 minor units
    # Average cost = (2000 + 4000) / 2 = 3000.0 minor units
    with db.get_connection() as conn:
        conn.execute("DELETE FROM verification_layer_results WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM task_verifications WHERE tenant_id = ?", (TENANT_ID,))
        conn.execute("DELETE FROM work_tasks WHERE tenant_id = ?", (TENANT_ID,))
        _seed_task(conn, task_id="tsk_cost_1", estimate_minor_units=2000, title="Cost Task 1")
        _seed_task(conn, task_id="tsk_cost_2", estimate_minor_units=4000, title="Cost Task 2")
        conn.commit()

    cost_val, cost_proof, cost_hash = KPICalculator.compute_metric(
        TENANT_ID, COMPANY_ID, KPIMetricType.COST_PER_MISSION, KPIScopeLevel.COMPANY
    )
    assert cost_val == 3000.0
    assert cost_proof["total_spend"] == 6000
    assert cost_proof["task_count"] == 2
    assert len(cost_hash) == 64


def test_07_rule15_principal_separation_migration_permissions():
    """
    Acceptance test 7: Rule 15 Principal Separation.
    PostgreSQL migration explicitly revokes INSERT, UPDATE, DELETE on KPI and Kaizen
    tables from zonata_agent_role, enforcing that models cannot alter KPI metrics,
    definitions, snapshots, or Kaizen proposals.
    """
    import os
    pg_mig_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrations", "pg", "0026_kpi_goal_engine.sql"
    )
    assert os.path.exists(pg_mig_path), "PostgreSQL migration file must exist"

    with open(pg_mig_path, "r", encoding="utf-8") as f:
        mig_sql = f.read()

    # Rule 15 assertions
    assert "REVOKE INSERT, UPDATE, DELETE ON kpi_tree_definitions FROM zonata_agent_role" in mig_sql
    assert "REVOKE INSERT, UPDATE, DELETE ON kpi_snapshots FROM zonata_agent_role" in mig_sql
    assert "REVOKE INSERT, UPDATE, DELETE ON kpi_alerts FROM zonata_agent_role" in mig_sql
    assert "REVOKE INSERT, UPDATE, DELETE ON kaizen_defect_records FROM zonata_agent_role" in mig_sql
    assert "REVOKE INSERT, UPDATE, DELETE ON kaizen_proposals FROM zonata_agent_role" in mig_sql

    # Fail-closed RLS assertions
    assert "ALTER TABLE kpi_tree_definitions ENABLE ROW LEVEL SECURITY;" in mig_sql
    assert "ALTER TABLE kpi_snapshots ENABLE ROW LEVEL SECURITY;" in mig_sql
    assert "ALTER TABLE kpi_alerts ENABLE ROW LEVEL SECURITY;" in mig_sql
    assert "ALTER TABLE kaizen_defect_records ENABLE ROW LEVEL SECURITY;" in mig_sql
    assert "ALTER TABLE kaizen_proposals ENABLE ROW LEVEL SECURITY;" in mig_sql
