"""
Enterprise AI corporate workforce architecture regressions.

Covers the service layer over the canonical 25-table schema: organization
provisioning, multi-level hierarchy, reporting-cycle rejection, employee
identity, SOP versioning, KRA/KPI enforcement, explainable performance,
shared agent capabilities with isolated instances, cross-department
collaboration and tenant/company isolation.
"""

import time

import pytest

from core.db import db
from core.evidence_ledger import EvidenceLedger
from core.workforce_architecture import (
    EXECUTIVE_CATALOG,
    INDUSTRY_BLUEPRINTS,
    WorkforceArchitecture,
    WorkforceError,
)

TENANT = "tnt_primary"
COMPANY = "comp_wf_arch"


def _arch(company=COMPANY, tenant=TENANT):
    return WorkforceArchitecture(tenant, company, ledger=EvidenceLedger())


def _ensure_company(company_id: str, tenant_id: str = TENANT, name: str = "Second Company"):
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, "
            "status, created_at) VALUES (?, ?, ?, 'GENERAL', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (company_id, tenant_id, name, time.time()),
        )
        conn.commit()


def _make_staff(arch, *, dept_code: str, title: str, grade: str = "G8",
                manager_employee_id=None, suffix: str = ""):
    dept = arch.create_department(code=dept_code + suffix, name=f"{title} Unit {suffix}")
    pos = arch.create_position(department_id=dept["department_id"], title=title, grade=grade)
    emp = arch.hire_employee(
        position_id=pos["position_id"], first_name="Test", last_name="Employee",
        manager_employee_id=manager_employee_id,
    )
    return dept, pos, emp


@pytest.fixture(scope="module")
def org():
    """Provision one realistic company once for the module."""
    _ensure_company(COMPANY, name="Workforce Architecture Test Co")
    arch = _arch()
    result = arch.provision_organization(
        industry="saas",
        legal_name="Northstar Workforce Systems Private Limited",
        trade_name="Northstar Workforce Systems",
        created_by="usr_test_owner",
        objectives=["Grow ARR", "Improve delivery quality"],
    )
    return arch, result


class TestCatalogs:
    def test_executive_catalog_covers_full_c_suite(self):
        codes = [e["code"] for e in EXECUTIVE_CATALOG]
        assert len(codes) == len(set(codes))
        for required in ("CEO", "COO", "CFO", "CTO", "CMO", "CSO", "CHRO",
                         "CPO", "CLO", "CRO", "CISO", "CDO", "CKO"):
            assert required in codes
        for item in EXECUTIVE_CATALOG:
            assert item["kras"], f"{item['code']} has no KRAs"
            assert item["role"]

    def test_industry_blueprints_are_data_driven(self):
        assert len(INDUSTRY_BLUEPRINTS) >= 10
        for industry, blueprint in INDUSTRY_BLUEPRINTS.items():
            assert blueprint["departments"], industry
            codes = [d["code"] for d in blueprint["departments"]]
            assert len(codes) == len(set(codes)), industry

    def test_unknown_industry_is_rejected(self):
        with pytest.raises(WorkforceError):
            WorkforceArchitecture.get_industry_blueprint("not_a_real_industry")

    @pytest.mark.parametrize("industry", sorted(INDUSTRY_BLUEPRINTS))
    def test_every_industry_covers_every_chief_role(self, industry):
        """No industry blueprint may silently lose a chief role's department."""
        blueprint = WorkforceArchitecture.get_industry_blueprint(industry)
        codes = {d["code"] for d in blueprint["base_departments"]}
        codes.update(d["code"] for d in blueprint["industry_departments"])
        missing = [e["code"] for e in EXECUTIVE_CATALOG if e["dept"] not in codes]
        assert missing == [], f"{industry} is missing departments for {missing}"

    def test_non_saas_industry_provisions_all_thirteen_executives(self):
        company = "comp_wf_ind_manufacturing"
        _ensure_company(company, name="Manufacturing Coverage Co")
        arch = _arch(company)
        result = arch.provision_organization(
            industry="manufacturing",
            legal_name="Manufacturing Coverage Test Limited",
            trade_name="Manufacturing Coverage Test",
        )
        assert {e["code"] for e in result["executives"]} == {
            e["code"] for e in EXECUTIVE_CATALOG
        }
        employees = arch.list_employees()
        assert len(employees) >= 40
        assert {"G1", "G2", "G3", "G5", "G8"}.issubset(
            {e["hierarchy_level"] for e in employees}
        )
        # Industry-specific department overrides the generic base department.
        titles = {p["title"] for p in arch.list_positions()}
        assert "Production Manager" in titles
        assert "Shift Supervisor" in titles


class TestOrganizationProvisioning:
    def test_provisioning_builds_multi_level_hierarchy(self, org):
        arch, result = org
        assert result["success"] is True
        assert result["departments"] >= 5
        assert len(result["executives"]) >= 10

        employees = arch.list_employees()
        assert len(employees) >= 30
        grades = {e["hierarchy_level"] for e in employees}
        # executive -> director -> manager -> specialist levels all exist
        assert {"G1", "G2", "G3", "G5", "G8"}.issubset(grades)

        ceo = arch.get_employee(result["ceo_employee_id"])
        assert ceo["hierarchy_level"] == "G1"
        assert ceo["reporting_chain"][0]["employee_id"] == ceo["employee_id"]

        # Every non-CEO executive reports to the CEO.
        cfo = next(e for e in result["executives"] if e["code"] == "CFO")
        cfo_emp = arch.get_employee(cfo["employee_id"])
        assert cfo_emp["reporting_chain"][-1]["employee_id"] == ceo["employee_id"]

        # A specialist sits several levels below the CEO.
        specialist = next(e for e in employees
                          if e["hierarchy_level"] == "G8" and e["department_id"])
        chain = arch.reporting_chain(specialist["employee_id"])
        assert len(chain) >= 3

    def test_org_chart_exposes_departments_and_heads(self, org):
        arch, _ = org
        chart = arch.org_chart()
        assert chart["employee_count"] >= 30
        assert any(d["head"] for d in chart["departments"])
        assert len(chart["executives"]) >= 10

    def test_duplicate_organization_rejected(self, org):
        arch, _ = org
        with pytest.raises(WorkforceError):
            arch.provision_organization(
                industry="saas",
                legal_name="Northstar Workforce Systems Private Limited",
                trade_name="Northstar Workforce Systems",
            )

    def test_employee_codes_are_stable_and_unique(self, org):
        arch, _ = org
        employees = arch.list_employees()
        codes = [e["work_email"].split("@")[0] for e in employees]
        assert len(codes) == len(set(codes))
        assert "emp-ceo-001" in codes


class TestHierarchyIntegrity:
    def test_reporting_cycle_is_rejected(self, org):
        arch, result = org
        ceo = result["ceo_employee_id"]
        coo = next(e for e in result["executives"] if e["code"] == "COO")
        with pytest.raises(WorkforceError, match="cycle"):
            arch.assign_manager(employee_id=ceo, manager_employee_id=coo["employee_id"])

    def test_self_management_is_rejected(self, org):
        arch, result = org
        ceo = result["ceo_employee_id"]
        with pytest.raises(WorkforceError, match="themselves"):
            arch.assign_manager(employee_id=ceo, manager_employee_id=ceo)

    def test_position_cannot_report_to_more_junior_position(self, org):
        arch, _ = org
        dept = arch.create_department(code="TESTJ", name="Junior Reporting Test")
        senior = arch.create_position(department_id=dept["department_id"],
                                      title="Senior Test Role", grade="G5")
        with pytest.raises(WorkforceError, match="junior"):
            arch.create_position(
                department_id=dept["department_id"], title="Exec Test Role", grade="G2",
                reports_to_position_id=senior["position_id"],
            )

    def test_headcount_limit_is_enforced(self, org):
        arch, _ = org
        dept = arch.create_department(code="TESTH", name="Headcount Test")
        pos = arch.create_position(department_id=dept["department_id"],
                                   title="Single Seat", grade="G8", headcount_limit=1)
        arch.hire_employee(position_id=pos["position_id"],
                           first_name="First", last_name="Seat")
        with pytest.raises(WorkforceError, match="headcount"):
            arch.hire_employee(position_id=pos["position_id"],
                               first_name="Second", last_name="Seat")

    def test_cross_company_manager_is_rejected(self, org):
        arch, _ = org
        _ensure_company("comp_workforce_other", name="Other Workforce Company")
        other = _arch("comp_workforce_other")
        _, _, other_emp = _make_staff(other, dept_code="OTH", title="Other Staff")
        with pytest.raises(WorkforceError, match="Manager not found"):
            arch.assign_manager(employee_id=org[1]["executives"][0]["employee_id"],
                                manager_employee_id=other_emp["employee_id"])


class TestSopLifecycle:
    def test_sop_versions_are_immutable_and_approved_only(self, org):
        arch, _ = org
        dept = arch.create_department(code="TESTS", name="SOP Test Department")
        sop = arch.register_sop(department_id=dept["department_id"], code="SOP-TEST-1",
                                title="Test Operating Procedure")
        _, _, emp = _make_staff(arch, dept_code="TESTSE", title="SOP Executor")
        steps = [{"action": "collect_evidence", "requires": "source_url"}]

        v1 = arch.publish_sop_version(sop_id=sop["sop_id"], semver="1.0.0", steps=steps,
                                      author_employee_id=emp["employee_id"],
                                      approved_by_role="CHRO")
        assert v1["status"] == "APPROVED"

        with pytest.raises(WorkforceError, match="immutable"):
            arch.publish_sop_version(sop_id=sop["sop_id"], semver="1.0.0", steps=steps,
                                     author_employee_id=emp["employee_id"])

        draft = arch.publish_sop_version(sop_id=sop["sop_id"], semver="1.1.0",
                                         steps=steps, author_employee_id=emp["employee_id"])
        assert draft["status"] == "DRAFT"
        with pytest.raises(WorkforceError, match="APPROVED"):
            arch.assign_sop(employee_id=emp["employee_id"], version_id=draft["version_id"])

        assigned = arch.assign_sop(employee_id=emp["employee_id"], version_id=v1["version_id"])
        assert assigned["success"] is True
        active = arch.list_employee_sops(emp["employee_id"])
        assert [s["sop_version_id"] for s in active] == [v1["version_id"]]

    def test_sop_requires_executable_steps(self, org):
        arch, _ = org
        dept = arch.create_department(code="TESTS2", name="SOP Step Test")
        sop = arch.register_sop(department_id=dept["department_id"], code="SOP-TEST-2",
                                title="No Steps")
        _, _, emp = _make_staff(arch, dept_code="TESTS2E", title="Author")
        with pytest.raises(WorkforceError, match="at least one"):
            arch.publish_sop_version(sop_id=sop["sop_id"], semver="1.0.0", steps=[],
                                     author_employee_id=emp["employee_id"])


class TestKraKpiAndPerformance:
    def _employee_with_kpis(self, arch, *, suffix: str):
        dept = arch.create_department(code=f"PERF{suffix}", name=f"Performance Unit {suffix}")
        pos = arch.create_position(department_id=dept["department_id"],
                                   title="Performance Analyst", grade="G8")
        emp = arch.hire_employee(position_id=pos["position_id"],
                                 first_name="Perf", last_name="Analyst")
        kra = arch.define_kra(employee_id=emp["employee_id"], name="Verified output",
                              weight_percentage=60.0,
                              accountability_statement="Owns verified analytical output")
        kpi = arch.define_kpi(kra_id=kra["kra_id"], code=f"KPI{suffix}", name="Verified items",
                              unit="COUNT", target_value=100.0)
        return emp, kra, kpi

    def test_kra_weights_cannot_exceed_100_percent(self, org):
        arch, _ = org
        emp, _, _ = self._employee_with_kpis(arch, suffix="W")
        with pytest.raises(WorkforceError, match="exceed 100"):
            arch.define_kra(employee_id=emp["employee_id"], name="Overflow",
                            weight_percentage=50.0, accountability_statement="Too much")

    def test_measurement_requires_evidence(self, org):
        arch, _ = org
        _, _, kpi = self._employee_with_kpis(arch, suffix="E")
        with pytest.raises(WorkforceError, match="evidence reference"):
            arch.record_measurement(kpi_id=kpi["kpi_id"], measured_value=110.0,
                                    evidence_ref="  ")

    def test_measurement_is_scored_and_sealed(self, org):
        arch, _ = org
        _, _, kpi = self._employee_with_kpis(arch, suffix="S")
        m = arch.record_measurement(kpi_id=kpi["kpi_id"], measured_value=120.0,
                                    evidence_ref="EV-PERF-120")
        assert m["score_contribution"] > 100
        assert m["anti_gaming_passed"] is True
        assert m["evidence"]["evidence_id"].startswith("EV-")

    def test_performance_refuses_without_measurements(self, org):
        arch, _ = org
        emp, _, _ = self._employee_with_kpis(arch, suffix="N")
        now = time.time()
        result = arch.evaluate_employee(employee_id=emp["employee_id"],
                                        period_start=now - 3600, period_end=now + 60)
        assert result["success"] is False
        assert result["status"] == "INSUFFICIENT_MEASUREMENTS"

    def test_performance_excludes_blocked_and_unmeasured_kpis(self, org):
        arch, _ = org
        emp, kra, kpi = self._employee_with_kpis(arch, suffix="B")
        blocked = arch.define_kpi(kra_id=kra["kra_id"], code="KPIB2",
                                  name="Blocked external metric", unit="COUNT",
                                  target_value=10.0)
        arch.record_measurement(kpi_id=kpi["kpi_id"], measured_value=95.0,
                                evidence_ref="EV-PERF-95")
        now = time.time()
        result = arch.evaluate_employee(
            employee_id=emp["employee_id"],
            period_start=now - 3600, period_end=now + 60,
            externally_blocked_kpi_ids=[blocked["kpi_id"]],
            collaboration_sla_score=90.0,
        )
        assert result["status"] == "COMPLETED"
        included_codes = {i["code"] for i in result["included_kpis"]}
        excluded = {i["code"]: i["reason"] for i in result["excluded_kpis"]}
        assert "KPIB" in included_codes
        assert excluded.get("KPIB2") == "EXTERNAL_DEPENDENCY_BLOCKED"
        assert 0 <= result["composite_score"] <= 120
        assert result["recommendation"] in ("EXCEEDING", "MEETING", "DEVELOPING",
                                            "IMPROVEMENT_PLAN")


class TestAgentFactory:
    def test_capability_registration_is_tenant_scoped(self, org):
        arch, _ = org
        try:
            arch.register_capability(code="web_browsing", name="Governed web browsing",
                                     category="RESEARCH")
        except WorkforceError:
            pass  # already registered by an earlier test in the module
        codes = [c["code"] for c in arch.list_capabilities()]
        assert "web_browsing" in codes

    def test_instances_are_isolated_and_quota_bound(self, org):
        arch, _ = org
        try:
            arch.register_capability(code="browser_research", name="Browser research",
                                     category="RESEARCH")
        except WorkforceError:
            pass
        _, _, alice = _make_staff(arch, dept_code="AGTA", title="Research Specialist")
        _, _, bob = _make_staff(arch, dept_code="AGTB", title="Research Specialist")

        a = arch.provision_agent(employee_id=alice["employee_id"],
                                 capability_code="browser_research", quota=2)
        b = arch.provision_agent(employee_id=bob["employee_id"],
                                 capability_code="browser_research", quota=2)
        assert a["instance_id"] != b["instance_id"]
        assert a["session_id"] != b["session_id"]
        assert a["session_token"] != b["session_token"]

        # Alice cannot read Bob's isolated instance.
        with pytest.raises(WorkforceError, match="another employee"):
            arch.get_agent_instance(b["instance_id"], employee_id=alice["employee_id"])

        arch.provision_agent(employee_id=alice["employee_id"],
                             capability_code="browser_research", quota=2)
        with pytest.raises(WorkforceError, match="quota"):
            arch.provision_agent(employee_id=alice["employee_id"],
                                 capability_code="browser_research", quota=2)

    def test_termination_releases_lease_and_session(self, org):
        arch, _ = org
        _, _, carol = _make_staff(arch, dept_code="AGTC", title="Ops Specialist")
        inst = arch.provision_agent(employee_id=carol["employee_id"],
                                    capability_code="browser_research")
        term = arch.terminate_agent(instance_id=inst["instance_id"],
                                    employee_id=carol["employee_id"])
        assert term["status"] == "TERMINATED"
        with db.get_connection() as conn:
            lease = conn.execute(
                "SELECT lease_state, released_at FROM agent_leases WHERE lease_id = ?",
                (inst["lease_id"],)).fetchone()
            session = conn.execute(
                "SELECT execution_status FROM agent_execution_sessions WHERE session_id = ?",
                (inst["session_id"],)).fetchone()
        assert lease["lease_state"] == "RELEASED" and lease["released_at"]
        assert session["execution_status"] == "COMPLETED"

    def test_unregistered_capability_is_rejected(self, org):
        arch, _ = org
        _, _, dave = _make_staff(arch, dept_code="AGTD", title="Ops Specialist")
        with pytest.raises(WorkforceError, match="not registered"):
            arch.provision_agent(employee_id=dave["employee_id"],
                                 capability_code="does_not_exist")


class TestCollaboration:
    def _mission(self, arch, lead_employee_id: str):
        mission_id = f"mis_col_{int(time.time() * 1000) % 10_000_000}"
        with db.get_connection() as conn:
            conn.execute(
                """INSERT INTO corporate_missions
                   (mission_id, tenant_id, company_id, title, objective_statement,
                    lead_employee_id, sponsor_executive_role, status, priority_level,
                    budget_limit_usd, spent_budget_usd, progress_percentage,
                    target_delivery_timestamp, completed_at, outcome_evidence_hash,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (mission_id, TENANT, COMPANY, "Market expansion study",
                 "Evaluate regional expansion with verified evidence",
                 lead_employee_id, "CEO", "PLANNING", "P1", 5000.0, 0.0, 0.0,
                 time.time() + 86400, None, None, time.time(), time.time()),
            )
            conn.commit()
        return mission_id

    def test_collaboration_requires_two_departments(self, org):
        arch, result = org
        mission_id = self._mission(arch, result["ceo_employee_id"])
        dept = arch.list_departments()[0]
        with pytest.raises(WorkforceError, match="different departments"):
            arch.open_collaboration(
                mission_id=mission_id, initiator_department_id=dept["department_id"],
                target_department_id=dept["department_id"],
                deliverable_description="Same-department task",
            )

    def test_collaboration_lifecycle_is_guarded(self, org):
        arch, result = org
        mission_id = self._mission(arch, result["ceo_employee_id"])
        depts = arch.list_departments()
        initiator = next(d for d in depts if d["code"] == "MKT")
        target = next(d for d in depts if d["code"] == "SALES")
        collab = arch.open_collaboration(
            mission_id=mission_id,
            initiator_department_id=initiator["department_id"],
            target_department_id=target["department_id"],
            deliverable_description="Qualified lead list with verification evidence",
            sla_turnaround_hours=48,
            escalation_owner_role="COO",
        )
        assert collab["status"] == "REQUESTED"
        with pytest.raises(WorkforceError, match="Cannot fulfil"):
            arch.advance_collaboration(collab_id=collab["collab_id"], action="FULFIL")
        assert arch.advance_collaboration(collab_id=collab["collab_id"],
                                          action="ACCEPT")["status"] == "ACCEPTED"
        assert arch.advance_collaboration(collab_id=collab["collab_id"],
                                          action="FULFIL")["status"] == "FULFILLED"

    def test_collaboration_rejects_unknown_escalation_role(self, org):
        arch, result = org
        mission_id = self._mission(arch, result["ceo_employee_id"])
        depts = arch.list_departments()
        with pytest.raises(WorkforceError, match="escalation_owner_role"):
            arch.open_collaboration(
                mission_id=mission_id,
                initiator_department_id=depts[0]["department_id"],
                target_department_id=depts[1]["department_id"],
                deliverable_description="Something",
                escalation_owner_role="NOT_A_ROLE",
            )


class TestIsolationAndLifecycle:
    def test_company_isolation(self, org):
        arch, _ = org
        other = _arch("comp_workforce_other")
        mine = {e["employee_id"] for e in arch.list_employees()}
        theirs = {e["employee_id"] for e in other.list_employees()}
        assert not (mine & theirs)
        sample = next(iter(mine))
        assert other.get_employee(sample) is None
        assert other.list_departments() != arch.list_departments()

    def test_tenant_isolation(self):
        _ensure_company("comp_tenant_b", tenant_id="tnt_bootstrap", name="Tenant B Co")
        arch_b = _arch("comp_tenant_b", tenant="tnt_bootstrap")
        arch_b.provision_organization(industry="media", legal_name="Tenant B Media")
        arch_a = _arch()
        assert arch_a.get_employee(arch_b.list_employees()[0]["employee_id"]) is None
        assert arch_a.org_chart()["organization"]["org_id"] != \
            arch_b.org_chart()["organization"]["org_id"]

    def test_deactivation_retains_history(self, org):
        arch, _ = org
        _, _, emp = _make_staff(arch, dept_code="TERM", title="Leaver")
        result = arch.deactivate_employee(emp["employee_id"], reason="role eliminated",
                                          actor_role="OWNER")
        assert result["status"] == "TERMINATED"
        assert result["history_retained"] is True
        stored = arch.get_employee(emp["employee_id"])
        assert stored is not None
        assert stored["lifecycle_state"] == "TERMINATED"
        with db.get_connection() as conn:
            rel = conn.execute(
                "SELECT is_active FROM employee_reporting_relationships "
                "WHERE employee_id = ? AND is_active = 1", (emp["employee_id"],),
            ).fetchone()
        assert rel is None
        with pytest.raises(WorkforceError, match="Only owner or executive"):
            arch.deactivate_employee(emp["employee_id"], reason="x", actor_role="EMPLOYEE")
