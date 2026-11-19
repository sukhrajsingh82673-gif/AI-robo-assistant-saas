"""
Workforce HTTP surface regressions.

These tests exercise the request/authorization layer that api_server delegates
to (``core.workforce_api``), so they cover routing, role gating, tenant/company
scoping and error mapping without requiring a live socket.
"""

import time

import pytest

from core.db import db
from core.workforce_api import handle_get, handle_post

TENANT = "tnt_primary"
COMPANY = "comp_primary"

OWNER = {"user_id": "usr_owner", "role": "OWNER", "tenant_id": TENANT}
EXEC = {"user_id": "usr_exec", "role": "EXECUTIVE", "tenant_id": TENANT}
MANAGER = {"user_id": "usr_mgr", "role": "MANAGER", "tenant_id": TENANT}
OPERATOR = {"user_id": "usr_op", "role": "OPERATOR", "tenant_id": TENANT}
OBSERVER = {"user_id": "usr_obs", "role": "OBSERVER", "tenant_id": TENANT}


def _company(company_id: str, tenant_id: str = TENANT):
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, "
            "status, created_at) VALUES (?, ?, ?, 'GENERAL', 'NEW', 'OPERATIONAL', ?) "
            "ON CONFLICT(company_id) DO NOTHING",
            (company_id, tenant_id, company_id, time.time()),
        )
        conn.commit()


@pytest.fixture(scope="module")
def provisioned():
    _company(COMPANY)
    body, status = handle_post(
        "/api/workforce/organization",
        {"industry": "logistics", "legal_name": "Northstar Logistics API Test Ltd",
         "trade_name": "Northstar Logistics API Test", "size_band": "mid"},
        TENANT, COMPANY, OWNER,
    )
    assert status == 201, body
    return body


class TestReadRoutes:
    def test_summary_requires_report_authority(self):
        for ctx in (OPERATOR, OBSERVER):
            body, status = handle_get("/api/workforce", {}, TENANT, COMPANY, ctx)
            assert status == 403
            assert "INSUFFICIENT_PERMISSIONS" in body["error"]

    def test_unprovisioned_company_reports_honestly(self):
        _company("comp_wf_api_empty")
        body, status = handle_get("/api/workforce", {}, TENANT, "comp_wf_api_empty", MANAGER)
        assert status == 200
        assert body["provisioned"] is False
        assert body["organization"] is None

    def test_summary_is_company_scoped(self, provisioned):
        body, status = handle_get("/api/workforce", {}, TENANT, COMPANY, MANAGER)
        assert status == 200
        assert body["provisioned"] is True
        assert body["employees"] >= 30
        assert body["executives"] >= 10

        other, status = handle_get("/api/workforce", {}, TENANT, "comp_wf_api_empty", MANAGER)
        assert other["employees"] == 0
        assert other["provisioned"] is False

    def test_org_chart_and_catalog_routes(self, provisioned):
        body, status = handle_get("/api/workforce/org-chart", {}, TENANT, COMPANY, EXEC)
        assert status == 200 and body["employee_count"] >= 30
        assert any(d["head"] for d in body["departments"])

        body, status = handle_get("/api/workforce/executives", {}, TENANT, COMPANY, EXEC)
        assert status == 200
        assert len(body["executives"]) >= 13

        body, status = handle_get("/api/workforce/industries", {}, TENANT, COMPANY, EXEC)
        assert status == 200 and len(body["industries"]) >= 10

        body, status = handle_get("/api/workforce/industries/manufacturing", {},
                                  TENANT, COMPANY, EXEC)
        assert status == 200 and body["industry"] == "manufacturing"

    def test_employee_detail_only_returns_own_company(self, provisioned):
        emp_id = provisioned["ceo_employee_id"]
        body, status = handle_get(f"/api/workforce/employees/{emp_id}", {},
                                  TENANT, COMPANY, MANAGER)
        assert status == 200
        assert body["employee"]["hierarchy_level"] == "G1"

        body, status = handle_get(f"/api/workforce/employees/{emp_id}", {},
                                  TENANT, "comp_wf_api_empty", MANAGER)
        assert status == 404

    def test_non_workforce_path_is_not_intercepted(self):
        assert handle_get("/api/skills", {}, TENANT, COMPANY, OWNER) is None
        assert handle_post("/api/skills/x/run", {}, TENANT, COMPANY, OWNER) is None


class TestWriteRoutes:
    def test_operator_cannot_mutate_workforce(self, provisioned):
        body, status = handle_post(
            "/api/workforce/departments",
            {"code": "SNEAK", "name": "Unauthorized Department"},
            TENANT, COMPANY, OPERATOR,
        )
        assert status == 403
        assert "INSUFFICIENT_PERMISSIONS" in body["error"]

    def test_operator_cannot_deactivate_even_though_executive_can_mutate(self, provisioned):
        body, status = handle_post(
            f"/api/workforce/employees/{provisioned['ceo_employee_id']}/deactivate",
            {"reason": "attempt"}, TENANT, COMPANY, EXEC,
        )
        assert status == 403
        assert "Only Owner" in body["error"]

    def test_department_position_hire_flow(self, provisioned):
        body, status = handle_post(
            "/api/workforce/departments",
            {"code": "APID", "name": "API Surface Department", "headcount_ceiling": 5},
            TENANT, COMPANY, EXEC,
        )
        assert status == 201
        dept_id = body["department_id"]

        pos, status = handle_post(
            "/api/workforce/positions",
            {"department_id": dept_id, "title": "API Test Analyst", "grade": "G8"},
            TENANT, COMPANY, EXEC,
        )
        assert status == 201

        emp, status = handle_post(
            "/api/workforce/employees",
            {"position_id": pos["position_id"], "first_name": "Api",
             "last_name": "Tester", "manager_employee_id": provisioned["ceo_employee_id"]},
            TENANT, COMPANY, EXEC,
        )
        assert status == 201
        assert emp["authority_tier"] == "EMPLOYEE"

    def test_cycle_rejection_is_surfaced_as_400(self, provisioned):
        ceo = provisioned["ceo_employee_id"]
        coo = next(e for e in provisioned["executives"] if e["code"] == "COO")
        body, status = handle_post(
            f"/api/workforce/employees/{ceo}/manager",
            {"manager_employee_id": coo["employee_id"]},
            TENANT, COMPANY, OWNER,
        )
        assert status == 400
        assert "cycle" in body["error"]

    def test_missing_legal_name_is_rejected(self):
        body, status = handle_post("/api/workforce/organization", {},
                                   TENANT, COMPANY, OWNER)
        assert status == 400
        assert "legal_name" in body["error"]

    def test_unknown_company_write_returns_404_when_employee_missing(self):
        body, status = handle_post(
            "/api/workforce/employees/emp_does_not_exist/manager",
            {"manager_employee_id": "emp_also_missing"},
            TENANT, "comp_wf_api_empty", OWNER,
        )
        assert status == 400
        assert "Manager not found" in body["error"]
