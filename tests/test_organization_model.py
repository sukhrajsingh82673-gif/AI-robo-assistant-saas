"""
Unit & Acceptance Tests for Sub-Step 2D: Organization Model (Board to Agent)
OpenCode Step 2D Acceptance Criteria:
1. Cycle in reporting lines is rejected.
2. Two CEOs rejected.
3. Handover pack contains exactly the open items from the database.
4. An AI occupant cannot edit its own position, authority, or reporting line (Rule 15).
5. Two companies with different packs get different initial structures with identical code.
6. Vacant seat routes work to supervisor.
7. Org chart is computed dynamically by query, never stored as text.
8. Employees can use agents; agents can NEVER command or invoke employees.
"""

import json
import pytest
import time
import uuid

from core.db import db
from core.action_envelope import ActionEnvelope
from core.action_gateway import action_gateway
from core.authority.types import PrincipalType, ActionClass
from core.organization import (
    OrgLevel,
    OccupantType,
    AssignmentStatus,
    organization_service,
    ensure_organization_tables,
    SingleCEOViolationError,
    ReportingCycleError,
    AIOrganizationSelfEditError,
    PositionNotFoundError,
)


def _seed_tenant_and_company(tenant_id: str, company_id: str) -> None:
    """Seeds tenant and company records to satisfy foreign key constraints."""
    now = time.time()
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at)
            VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)
            """,
            (tenant_id, f"Tenant {tenant_id}", now),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, currency, timezone, created_at)
            VALUES (?, ?, ?, 'TECH', 'PVT_LTD', 'OPERATIONAL', 'USD', 'UTC', ?)
            """,
            (company_id, tenant_id, f"Company {company_id}", now),
        )
        conn.commit()


@pytest.fixture(autouse=True)
def setup_org_tables():
    """Ensure organization tables exist for all test runs."""
    ensure_organization_tables()


# =============================================================================
# 1. CYCLE IN REPORTING LINES IS REJECTED
# =============================================================================

def test_cycle_in_reporting_lines_is_rejected():
    """Proves that any cycle in reporting lines (self, 2-node, multi-node) is strictly rejected."""
    tenant_id = f"ten_org_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_org_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_id)

    # Setup 4 positions in a hierarchy: CEO -> VP -> Manager -> Lead
    pos_ceo = organization_service.create_position(
        tenant_id, company_id, "Chief Executive Officer", OrgLevel.CEO, caller_principal_type="HUMAN"
    )["position_id"]
    pos_vp = organization_service.create_position(
        tenant_id, company_id, "VP Engineering", OrgLevel.DIRECTOR, caller_principal_type="HUMAN"
    )["position_id"]
    pos_mgr = organization_service.create_position(
        tenant_id, company_id, "Engineering Manager", OrgLevel.MANAGER, caller_principal_type="HUMAN"
    )["position_id"]
    pos_lead = organization_service.create_position(
        tenant_id, company_id, "Tech Lead", OrgLevel.TEAM_LEAD, caller_principal_type="HUMAN"
    )["position_id"]

    # Valid reporting lines: Lead -> Manager -> VP -> CEO
    organization_service.set_reporting_line(tenant_id, company_id, pos_lead, pos_mgr, caller_principal_type="HUMAN")
    organization_service.set_reporting_line(tenant_id, company_id, pos_mgr, pos_vp, caller_principal_type="HUMAN")
    organization_service.set_reporting_line(tenant_id, company_id, pos_vp, pos_ceo, caller_principal_type="HUMAN")

    # Mutation / Cycle Check 1: Self-cycle (Lead reports to Lead)
    with pytest.raises(ReportingCycleError) as exc_self:
        organization_service.set_reporting_line(tenant_id, company_id, pos_lead, pos_lead, caller_principal_type="HUMAN")
    assert "Self-reporting cycle rejected" in str(exc_self.value)

    # Mutation / Cycle Check 2: 2-node cycle (VP reports to Manager while Manager reports to VP)
    with pytest.raises(ReportingCycleError) as exc_2node:
        organization_service.set_reporting_line(tenant_id, company_id, pos_vp, pos_mgr, caller_principal_type="HUMAN")
    assert "cycle" in str(exc_2node.value).lower()

    # Mutation / Cycle Check 3: Multi-node cycle (CEO reports to Lead -> completes loop Lead -> Mgr -> VP -> CEO -> Lead)
    with pytest.raises(ReportingCycleError) as exc_multi:
        organization_service.set_reporting_line(tenant_id, company_id, pos_ceo, pos_lead, caller_principal_type="HUMAN")
    assert "cycle" in str(exc_multi.value).lower()

    # Confirm hierarchy remains intact and acyclic
    assert organization_service.get_supervisor(tenant_id, company_id, pos_lead) == pos_mgr
    assert organization_service.get_supervisor(tenant_id, company_id, pos_mgr) == pos_vp
    assert organization_service.get_supervisor(tenant_id, company_id, pos_vp) == pos_ceo
    assert organization_service.get_supervisor(tenant_id, company_id, pos_ceo) is None


# =============================================================================
# 2. TWO CEOS REJECTED
# =============================================================================

def test_two_ceos_rejected():
    """Proves that exactly one CEO position is permitted per company."""
    tenant_id = f"ten_org_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_org_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_id)

    # First CEO creation succeeds
    ceo_pos = organization_service.create_position(
        tenant_id=tenant_id,
        company_id=company_id,
        title="Chief Executive Officer",
        level=OrgLevel.CEO,
        caller_principal_type="HUMAN",
    )
    assert ceo_pos["level"] == "CEO"

    # Attempting to create a second position with level CEO fails
    with pytest.raises(SingleCEOViolationError) as exc_level:
        organization_service.create_position(
            tenant_id=tenant_id,
            company_id=company_id,
            title="Co-Chief Executive Officer",
            level=OrgLevel.CEO,
            caller_principal_type="HUMAN",
        )
    assert "already has an active CEO position" in str(exc_level.value)

    # Attempting to create a second position with CEO title fails even if passed level C_SUITE
    with pytest.raises(SingleCEOViolationError) as exc_title:
        organization_service.create_position(
            tenant_id=tenant_id,
            company_id=company_id,
            title="CEO",
            level=OrgLevel.C_SUITE,
            caller_principal_type="HUMAN",
        )
    assert "already has an active CEO position" in str(exc_title.value)

    # Attempting to elevate an existing position to CEO via update_position fails
    cto_pos = organization_service.create_position(
        tenant_id=tenant_id,
        company_id=company_id,
        title="Chief Technology Officer",
        level=OrgLevel.C_SUITE,
        caller_principal_type="HUMAN",
    )
    with pytest.raises(SingleCEOViolationError) as exc_update:
        organization_service.update_position(
            tenant_id=tenant_id,
            company_id=company_id,
            position_id=cto_pos["position_id"],
            level=OrgLevel.CEO,
            caller_principal_type="HUMAN",
        )
    assert "already has CEO" in str(exc_update.value)

    # Multi-tenant isolation: A different company CAN create its own CEO
    other_company_id = f"cmp_other_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, other_company_id)
    other_ceo = organization_service.create_position(
        tenant_id=tenant_id,
        company_id=other_company_id,
        title="Chief Executive Officer",
        level=OrgLevel.CEO,
        caller_principal_type="HUMAN",
    )
    assert other_ceo["company_id"] == other_company_id


# =============================================================================
# 3. HANDOVER PACK CONTAINS EXACTLY OPEN ITEMS FROM DATABASE
# =============================================================================

def test_handover_pack_contains_exactly_open_items_from_db():
    """Proves that handover pack generation extracts exactly the open tasks and pending approvals from DB."""
    tenant_id = f"ten_org_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_org_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_id)

    prev_ai_id = f"ai_worker_{uuid.uuid4().hex[:8]}"
    succ_ai_id = f"ai_successor_{uuid.uuid4().hex[:8]}"

    pos = organization_service.create_position(
        tenant_id, company_id, "DevOps Engineer", OrgLevel.EMPLOYEE, caller_principal_type="HUMAN"
    )
    pos_id = pos["position_id"]

    # Assign initial occupant
    organization_service.assign_position(
        tenant_id, company_id, pos_id, OccupantType.AI_EMPLOYEE, prev_ai_id, caller_principal_type="HUMAN"
    )

    # Seed Database with Tasks: 2 open, 1 completed
    task_open_1 = f"tsk_{uuid.uuid4().hex[:8]}"
    task_open_2 = f"tsk_{uuid.uuid4().hex[:8]}"
    task_closed = f"tsk_{uuid.uuid4().hex[:8]}"
    now = time.time()

    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO mission_tasks (task_id, mission_id, company_id, tenant_id, title, assigned_agent, stage, dependencies, state, tool_requirements, created_at)
            VALUES (?, 'msn_1', ?, ?, 'Deploy Terraform Stack', ?, 'EXEC', '[]', 'IN_PROGRESS', '[]', ?),
                   (?, 'msn_1', ?, ?, 'Configure Monitoring Alarms', ?, 'EXEC', '[]', 'ASSIGNED', '[]', ?),
                   (?, 'msn_1', ?, ?, 'Old Completed Task', ?, 'EXEC', '[]', 'COMPLETED', '[]', ?)
            """,
            (
                task_open_1, company_id, tenant_id, prev_ai_id, now,
                task_open_2, company_id, tenant_id, prev_ai_id, now,
                task_closed, company_id, tenant_id, prev_ai_id, now - 100,
            ),
        )

        # Seed Database with Approvals: 1 pending, 1 approved
        appr_pending = f"appr_{uuid.uuid4().hex[:8]}"
        appr_approved = f"appr_{uuid.uuid4().hex[:8]}"
        c.execute(
            """
            INSERT INTO action_approvals (approval_id, tenant_id, company_id, action_id, action_class, payload_digest, requester_id, maker_id, approver_id, status, expires_at, created_at)
            VALUES (?, ?, ?, 'act_1', 'COMMIT_SPEND', 'digest_1', ?, ?, 'sup_1', 'PENDING', ?, ?),
                   (?, ?, ?, 'act_2', 'COMMIT_SPEND', 'digest_2', ?, ?, 'sup_1', 'APPROVED', ?, ?)
            """,
            (
                appr_pending, tenant_id, company_id, prev_ai_id, prev_ai_id, now + 3600, now,
                appr_approved, tenant_id, company_id, prev_ai_id, prev_ai_id, now + 3600, now - 50,
            ),
        )
        conn.commit()

    # Generate Handover Pack
    pack = organization_service.generate_handover_pack(
        tenant_id=tenant_id,
        company_id=company_id,
        position_id=pos_id,
        previous_occupant_type=OccupantType.AI_EMPLOYEE,
        previous_occupant_id=prev_ai_id,
        successor_occupant_type=OccupantType.AI_EMPLOYEE,
        successor_occupant_id=succ_ai_id,
    )

    # Acceptance Invariant: Pack contains EXACTLY the open tasks (not the completed one)
    open_task_ids = [t["task_id"] for t in pack["open_tasks"]]
    assert len(open_task_ids) == 2
    assert task_open_1 in open_task_ids
    assert task_open_2 in open_task_ids
    assert task_closed not in open_task_ids

    # Acceptance Invariant: Pack contains EXACTLY the pending approval (not the approved one)
    pending_appr_ids = [a["approval_id"] for a in pack["pending_approvals"]]
    assert len(pending_appr_ids) == 1
    assert appr_pending in pending_appr_ids
    assert appr_approved not in pending_appr_ids

    # Verify handover pack row exists in database
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT status, open_tasks, pending_approvals FROM handover_packs WHERE pack_id = ?", (pack["pack_id"],))
        row = c.fetchone()
        assert row is not None
        assert row[0] == "GENERATED"
        persisted_tasks = json.loads(row[1])
        assert len(persisted_tasks) == 2


# =============================================================================
# 4. AI OCCUPANT CANNOT EDIT POSITION, AUTHORITY, OR REPORTING LINE (RULE 15)
# =============================================================================

def test_ai_occupant_cannot_edit_position_authority_or_reporting_line():
    """Proves that AI employees and agents cannot mutate positions, assignments, or reporting lines."""
    tenant_id = f"ten_org_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_org_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_id)

    # Human creates initial seat
    pos = organization_service.create_position(
        tenant_id, company_id, "Staff Engineer", OrgLevel.EMPLOYEE, caller_principal_type="HUMAN"
    )
    pos_id = pos["position_id"]

    # AI Employee attempts create_position -> Rejected
    with pytest.raises(AIOrganizationSelfEditError) as exc_create:
        organization_service.create_position(
            tenant_id, company_id, "Rogue Architect", OrgLevel.DIRECTOR, caller_principal_type="AI_EMPLOYEE"
        )
    assert "Rule 15 Violation" in str(exc_create.value)

    # Agent attempts create_position -> Rejected
    with pytest.raises(AIOrganizationSelfEditError):
        organization_service.create_position(
            tenant_id, company_id, "Rogue Agent", OrgLevel.AGENT, caller_principal_type="AGENT"
        )

    # AI Employee attempts update_position (e.g. promoting self or raising spend limit) -> Rejected
    with pytest.raises(AIOrganizationSelfEditError) as exc_update:
        organization_service.update_position(
            tenant_id, company_id, pos_id, spend_limit_minor_units=999_999_999, caller_principal_type="AI_EMPLOYEE"
        )
    assert "Rule 15 Violation" in str(exc_update.value)

    # AI Employee attempts assign_position -> Rejected
    with pytest.raises(AIOrganizationSelfEditError) as exc_assign:
        organization_service.assign_position(
            tenant_id, company_id, pos_id, OccupantType.AI_EMPLOYEE, "rogue_ai", caller_principal_type="AI_EMPLOYEE"
        )
    assert "Rule 15 Violation" in str(exc_assign.value)

    # AI Employee attempts set_reporting_line -> Rejected
    with pytest.raises(AIOrganizationSelfEditError) as exc_rep:
        organization_service.set_reporting_line(
            tenant_id, company_id, pos_id, pos_id, caller_principal_type="AI_EMPLOYEE"
        )
    assert "Rule 15 Violation" in str(exc_rep.value)


# =============================================================================
# 5. TWO COMPANIES WITH DIFFERENT PACKS GET DIFFERENT INITIAL STRUCTURES
# =============================================================================

def test_two_companies_different_packs_get_different_initial_structures():
    """Proves that two companies with different industry packs get structurally distinct org models with identical code."""
    tenant_id = f"ten_multi_{uuid.uuid4().hex[:8]}"
    company_saas = f"cmp_saas_{uuid.uuid4().hex[:8]}"
    company_clinic = f"cmp_clinic_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_saas)
    _seed_tenant_and_company(tenant_id, company_clinic)

    # Company 1 installs SaaS Enterprise Pack
    saas_res = organization_service.bootstrap_org_from_pack(
        tenant_id=tenant_id,
        company_id=company_saas,
        pack_id="saas_enterprise",
        owner_user_id="user_saas_owner",
    )
    assert saas_res["positions_created"] >= 6
    assert saas_res["departments_created"] >= 3

    # Company 2 installs Outpatient Clinic Pack
    clinic_res = organization_service.bootstrap_org_from_pack(
        tenant_id=tenant_id,
        company_id=company_clinic,
        pack_id="clinic_health",
        owner_user_id="user_clinic_owner",
    )
    assert clinic_res["positions_created"] >= 5
    assert clinic_res["departments_created"] >= 3

    # Retrieve positions for both companies
    saas_positions = organization_service.list_positions(tenant_id, company_saas)
    clinic_positions = organization_service.list_positions(tenant_id, company_clinic)

    saas_titles = {p["title"] for p in saas_positions}
    clinic_titles = {p["title"] for p in clinic_positions}

    # Verify SaaS specific roles exist in Company 1, not Company 2
    assert "Chief Technology Officer" in saas_titles
    assert "VP of Engineering" in saas_titles
    assert "Chief Technology Officer" not in clinic_titles

    # Verify Clinic specific roles exist in Company 2, not Company 1
    assert "Medical Director & Practice Principal" in clinic_titles
    assert "Clinical Nurse Supervisor" in clinic_titles
    assert "Clinical Nurse Supervisor" not in saas_titles

    # Verify departments are completely distinct
    saas_depts = {d["code"] for d in organization_service.list_departments(tenant_id, company_saas)}
    clinic_depts = {d["code"] for d in organization_service.list_departments(tenant_id, company_clinic)}

    assert "ENG" in saas_depts
    assert "REV" in saas_depts
    assert "CLIN" in clinic_depts
    assert "BILL" in clinic_depts


# =============================================================================
# 6. VACANT SEAT ROUTES WORK TO SUPERVISOR
# =============================================================================

def test_vacant_seat_routes_work_to_supervisor():
    """Proves that when a seat is vacant, effective assignee resolution traverses to supervisor."""
    tenant_id = f"ten_org_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_org_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_id)

    # Setup 3 positions: CEO -> Manager -> Specialist
    pos_ceo = organization_service.create_position(tenant_id, company_id, "Chief Executive Officer", OrgLevel.CEO, caller_principal_type="HUMAN")["position_id"]
    pos_mgr = organization_service.create_position(tenant_id, company_id, "Operations Manager", OrgLevel.MANAGER, caller_principal_type="HUMAN")["position_id"]
    pos_spec = organization_service.create_position(tenant_id, company_id, "Billing Specialist", OrgLevel.EMPLOYEE, caller_principal_type="HUMAN")["position_id"]

    organization_service.set_reporting_line(tenant_id, company_id, pos_spec, pos_mgr, caller_principal_type="HUMAN")
    organization_service.set_reporting_line(tenant_id, company_id, pos_mgr, pos_ceo, caller_principal_type="HUMAN")

    # Only assign the CEO; Manager and Specialist seats remain vacant
    organization_service.assign_position(tenant_id, company_id, pos_ceo, OccupantType.HUMAN, "user_ceo_principal", caller_principal_type="HUMAN")

    assert organization_service.is_position_vacant(tenant_id, company_id, pos_spec) is True
    assert organization_service.is_position_vacant(tenant_id, company_id, pos_mgr) is True
    assert organization_service.is_position_vacant(tenant_id, company_id, pos_ceo) is False

    # Resolving work for vacant Specialist climbs to vacant Manager, then to CEO
    effective_spec = organization_service.resolve_effective_assignee(tenant_id, company_id, pos_spec)
    assert effective_spec["is_routed"] is True
    assert effective_spec["effective_position_id"] == pos_ceo
    assert effective_spec["occupant_id"] == "user_ceo_principal"
    assert effective_spec["route_chain"] == [pos_spec, pos_mgr, pos_ceo]

    # Now fill the Manager seat with an AI employee
    organization_service.assign_position(tenant_id, company_id, pos_mgr, OccupantType.AI_EMPLOYEE, "ai_mgr_101", caller_principal_type="HUMAN")

    # Resolving work for Specialist now halts at Manager
    effective_spec_2 = organization_service.resolve_effective_assignee(tenant_id, company_id, pos_spec)
    assert effective_spec_2["is_routed"] is True
    assert effective_spec_2["effective_position_id"] == pos_mgr
    assert effective_spec_2["occupant_id"] == "ai_mgr_101"
    assert effective_spec_2["route_chain"] == [pos_spec, pos_mgr]


# =============================================================================
# 7. ORG CHART COMPUTED BY QUERY, NEVER STORED AS TEXT
# =============================================================================

def test_org_chart_computed_by_query_never_stored_as_text():
    """Proves org chart is constructed dynamically from SQL relations without text blobs."""
    tenant_id = f"ten_org_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_org_{uuid.uuid4().hex[:8]}"
    _seed_tenant_and_company(tenant_id, company_id)

    organization_service.bootstrap_org_from_pack(tenant_id, company_id, "saas_enterprise", "owner_1")
    chart = organization_service.compute_org_chart(tenant_id, company_id)

    assert chart["tenant_id"] == tenant_id
    assert chart["company_id"] == company_id
    assert chart["total_positions"] >= 6
    assert isinstance(chart["hierarchy"], list)
    assert len(chart["hierarchy"]) >= 1

    root_ceo = chart["hierarchy"][0]
    assert root_ceo["level"] == "CEO"
    assert len(root_ceo["direct_reports"]) >= 2

    # Verify no static text org chart table exists
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%org_chart%'")
        assert c.fetchone()[0] == 0


# =============================================================================
# 8. AGENTS CAN NEVER COMMAND EMPLOYEES IN GATEWAY
# =============================================================================

def test_agents_can_never_command_employees_in_gateway():
    """Proves ActionGateway Step 4 strictly enforces that agents cannot invoke or command employees."""
    tenant_id = f"ten_gw_{uuid.uuid4().hex[:8]}"
    company_id = f"cmp_gw_{uuid.uuid4().hex[:8]}"

    # Envelope 1: Agent principal attempting to command an AI employee
    env_agent_to_emp = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="agent_worker_42",
        capability_id="task.delegate",
        target="employees/emp_senior_lead",
        intent="Instruct employee to execute task",
        parameters={"task_id": "tsk_01"},
        action_class=ActionClass.WRITE_INTERNAL.value,
        principal_id="agent_worker_42",
        principal_type=PrincipalType.AGENT.value,
        target_principal_id="emp_senior_lead",
        target_principal_type=PrincipalType.AI_EMPLOYEE.value,
    )
    dec_denied = action_gateway.evaluate_decision_gate(env_agent_to_emp)
    assert dec_denied.allowed is False
    assert dec_denied.step_number == 4
    assert dec_denied.rule_id == "AGENT_CANNOT_CALL_EMPLOYEE"

    # Envelope 2: AI Employee principal delegating to an agent -> Allowed through Step 4
    env_emp_to_agent = ActionEnvelope.create(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id="emp_lead_01",
        capability_id="tool.calculator",
        target="tools/calculator",
        intent="Employee uses tool agent",
        parameters={"expression": "100 + 200"},
        action_class=ActionClass.READ_INTERNAL.value,
        principal_id="emp_lead_01",
        principal_type=PrincipalType.AI_EMPLOYEE.value,
        target_principal_id="agent_calc",
        target_principal_type=PrincipalType.AGENT.value,
    )
    dec_allowed = action_gateway.evaluate_decision_gate(env_emp_to_agent)
    # Passed Step 4
    step_4 = next((s for s in dec_allowed.decision_path if s.get("step") == 4), None)
    assert step_4 is not None
    assert step_4["status"] == "PASSED"
