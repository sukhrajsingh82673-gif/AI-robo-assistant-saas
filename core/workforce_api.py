"""
URA / ZONATA — Workforce Architecture HTTP surface
==================================================

Thin, uniform API over :class:`core.workforce_architecture.WorkforceArchitecture`.

Design rules enforced here (mirrored from the service layer):

* every route is tenant-scoped from the verified token and company-scoped from
  ``_resolve_company_id``; no caller-supplied tenant/company can escape its scope;
* reads require report-viewing authority, writes require owner/executive
  authority — an employee cannot grant itself authority through the API;
* every mutation is blocked by the global kill switch before any DB write;
* service invariants are surfaced as HTTP 400/409 with the invariant message
  intact, never swallowed into a success response.

This module contains no business logic: it validates request shape, delegates to
the service, and maps the result to a status code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.auth import AuthorizationEnforcer
from core.workforce_architecture import WorkforceArchitecture, WorkforceError

WriteResult = Optional[Tuple[Dict[str, Any], int]]


def _arch(tenant_id: str, company_id: str) -> WorkforceArchitecture:
    return WorkforceArchitecture(tenant_id, company_id)


def _role(ctx: Dict[str, Any]) -> str:
    return str((ctx or {}).get("role") or "")


def _deny_read(ctx: Dict[str, Any]) -> Optional[WriteResult]:
    if AuthorizationEnforcer.can_view_reports(_role(ctx)):
        return None
    return ({
        "success": False,
        "error": "INSUFFICIENT_PERMISSIONS: This role cannot view workforce data.",
        "role": _role(ctx),
    }, 403)


def _deny_write(ctx: Dict[str, Any]) -> Optional[WriteResult]:
    if AuthorizationEnforcer.can_approve(_role(ctx)):
        return None
    return ({
        "success": False,
        "error": "INSUFFICIENT_PERMISSIONS: Only Owner or Executive roles can "
                 "change the workforce.",
        "role": _role(ctx),
    }, 403)


def _one(query_params: Dict[str, List[str]], key: str) -> Optional[str]:
    values = (query_params or {}).get(key)
    return values[0] if values else None


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------
def handle_get(path: str, query_params: Dict[str, List[str]], tenant_id: str,
               company_id: str, auth_context: Dict[str, Any]) -> WriteResult:
    if not path.startswith("/api/workforce"):
        return None

    denied = _deny_read(auth_context)
    if denied:
        return denied

    try:
        arch = _arch(tenant_id, company_id)

        if path in ("/api/workforce", "/api/workforce/summary"):
            organization = arch.get_organization()
            employees = arch.list_employees()
            return ({
                "success": True,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "provisioned": organization is not None,
                "organization": organization,
                "departments": len(arch.list_departments()),
                "positions": len(arch.list_positions()),
                "employees": len(employees),
                "executives": len([e for e in employees
                                   if e["hierarchy_level"] in ("G1", "G2")]),
                "capabilities": len(arch.list_capabilities()),
                "agent_instances": len(arch.list_agent_instances()),
            }, 200)

        if path == "/api/workforce/organization":
            return ({"success": True, "organization": arch.get_organization()}, 200)

        if path == "/api/workforce/org-chart":
            return ({"success": True, **arch.org_chart()}, 200)

        if path == "/api/workforce/departments":
            rows = arch.list_departments()
            return ({"success": True, "departments": rows, "count": len(rows)}, 200)

        if path == "/api/workforce/positions":
            rows = arch.list_positions(department_id=_one(query_params, "department_id"))
            return ({"success": True, "positions": rows, "count": len(rows)}, 200)

        if path == "/api/workforce/employees":
            rows = arch.list_employees(department_id=_one(query_params, "department_id"))
            return ({"success": True, "employees": rows, "count": len(rows)}, 200)

        if path.startswith("/api/workforce/employees/") and path.count("/") == 4:
            employee = arch.get_employee(path.split("/")[4])
            if not employee:
                return ({"success": False, "error": "Employee not found in this company."}, 404)
            return ({"success": True, "employee": employee}, 200)

        if path == "/api/workforce/executives":
            return ({"success": True, "executives": arch.list_executives()}, 200)

        if path == "/api/workforce/industries":
            return ({"success": True, "industries": arch.list_industries()}, 200)

        if path.startswith("/api/workforce/industries/"):
            industry = path.split("/")[4]
            return ({"success": True, **arch.get_industry_blueprint(industry)}, 200)

        if path == "/api/workforce/capabilities":
            rows = arch.list_capabilities()
            return ({"success": True, "capabilities": rows, "count": len(rows)}, 200)

        if path == "/api/workforce/agents":
            rows = arch.list_agent_instances(employee_id=_one(query_params, "employee_id"))
            return ({"success": True, "agent_instances": rows, "count": len(rows)}, 200)

        if path == "/api/workforce/sops":
            employee_id = _one(query_params, "employee_id")
            if not employee_id:
                return ({"success": False, "error": "employee_id query parameter is required."}, 400)
            rows = arch.list_employee_sops(employee_id)
            return ({"success": True, "sops": rows, "count": len(rows)}, 200)

        if path == "/api/workforce/kras":
            employee_id = _one(query_params, "employee_id")
            if not employee_id:
                return ({"success": False, "error": "employee_id query parameter is required."}, 400)
            rows = arch.list_kras(employee_id)
            return ({"success": True, "kras": rows, "count": len(rows)}, 200)

        if path == "/api/workforce/collaborations":
            from core.db import db
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM cross_department_collaborations WHERE tenant_id = ? "
                    "AND company_id = ? ORDER BY created_at DESC",
                    (tenant_id, company_id),
                ).fetchall()
            items = [dict(r) for r in rows]
            return ({"success": True, "collaborations": items, "count": len(items)}, 200)

        return None
    except WorkforceError as exc:
        return ({"success": False, "error": str(exc)}, 400)
    except Exception as exc:  # never mask an internal fault as success
        return ({"success": False, "error": f"workforce error: {exc}"}, 500)


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------
def handle_post(path: str, req_data: Dict[str, Any], tenant_id: str,
                company_id: str, auth_context: Dict[str, Any]) -> WriteResult:
    if not path.startswith("/api/workforce"):
        return None

    denied = _deny_write(auth_context)
    if denied:
        return denied

    req_data = req_data or {}
    actor = str((auth_context or {}).get("user_id") or "system")
    try:
        arch = _arch(tenant_id, company_id)

        if path == "/api/workforce/organization":
            legal_name = str(req_data.get("legal_name") or "").strip()
            if not legal_name:
                return ({"success": False, "error": "legal_name is required."}, 400)
            result = arch.provision_organization(
                industry=str(req_data.get("industry") or "saas"),
                legal_name=legal_name,
                trade_name=req_data.get("trade_name"),
                created_by=actor,
                objectives=req_data.get("objectives") or [],
                size_band=str(req_data.get("size_band") or "mid"),
                extra_departments=req_data.get("extra_departments") or [],
            )
            return (result, 201)

        if path == "/api/workforce/departments":
            result = arch.create_department(
                code=str(req_data.get("code") or ""),
                name=str(req_data.get("name") or ""),
                parent_department_id=req_data.get("parent_department_id"),
                budget_usd=float(req_data.get("budget_usd") or 0.0),
                headcount_ceiling=int(req_data.get("headcount_ceiling") or 10),
                created_by=actor,
            )
            return (result, 201)

        if path == "/api/workforce/positions":
            result = arch.create_position(
                department_id=str(req_data.get("department_id") or ""),
                title=str(req_data.get("title") or ""),
                grade=str(req_data.get("grade") or "G8"),
                category=req_data.get("category"),
                job_description=str(req_data.get("job_description") or ""),
                responsibilities=req_data.get("responsibilities") or [],
                required_skills=req_data.get("required_skills") or [],
                required_kras=req_data.get("required_kras") or [],
                permitted_agent_capabilities=req_data.get("permitted_agent_capabilities") or [],
                reports_to_position_id=req_data.get("reports_to_position_id"),
                headcount_limit=int(req_data.get("headcount_limit") or 1),
                created_by=actor,
            )
            return (result, 201)

        if path == "/api/workforce/employees":
            result = arch.hire_employee(
                position_id=str(req_data.get("position_id") or ""),
                first_name=str(req_data.get("first_name") or ""),
                last_name=str(req_data.get("last_name") or ""),
                manager_employee_id=req_data.get("manager_employee_id"),
                employee_code=req_data.get("employee_code"),
                created_by=actor,
                knowledge_clearance=req_data.get("knowledge_clearance"),
            )
            return (result, 201)

        if path.startswith("/api/workforce/employees/") and path.endswith("/manager"):
            employee_id = path.split("/")[4]
            result = arch.assign_manager(
                employee_id=employee_id,
                manager_employee_id=str(req_data.get("manager_employee_id") or ""),
                relationship_type=str(req_data.get("relationship_type") or "SOLID_LINE"),
            )
            return (result, 200)

        if path.startswith("/api/workforce/employees/") and path.endswith("/deactivate"):
            employee_id = path.split("/")[4]
            if not AuthorizationEnforcer.can_mutate_governance(_role(auth_context)):
                return ({
                    "success": False,
                    "error": "INSUFFICIENT_PERMISSIONS: Only Owner authority can "
                             "deactivate an employee.",
                    "role": _role(auth_context),
                }, 403)
            result = arch.deactivate_employee(
                employee_id,
                reason=str(req_data.get("reason") or "api_request"),
                actor_role="OWNER",
            )
            return (result, 200)

        if path == "/api/workforce/sops":
            result = arch.register_sop(
                department_id=str(req_data.get("department_id") or ""),
                code=str(req_data.get("code") or ""),
                title=str(req_data.get("title") or ""),
                category=str(req_data.get("category") or "OPERATIONAL"),
                objective=str(req_data.get("objective") or ""),
                risk_level=str(req_data.get("risk_level") or "MEDIUM"),
            )
            return (result, 201)

        if path.startswith("/api/workforce/sops/") and path.endswith("/versions"):
            sop_id = path.split("/")[4]
            result = arch.publish_sop_version(
                sop_id=sop_id,
                semver=str(req_data.get("semver") or ""),
                steps=req_data.get("steps") or [],
                required_authority_level=str(req_data.get("required_authority_level") or "DELEGATED"),
                author_employee_id=str(req_data.get("author_employee_id") or ""),
                evidence_requirements=req_data.get("evidence_requirements") or [],
                approved_by_role=req_data.get("approved_by_role"),
            )
            return (result, 201)

        if path == "/api/workforce/sop-assignments":
            result = arch.assign_sop(
                employee_id=str(req_data.get("employee_id") or ""),
                version_id=str(req_data.get("version_id") or ""),
            )
            return (result, 201)

        if path == "/api/workforce/kras":
            result = arch.define_kra(
                employee_id=str(req_data.get("employee_id") or ""),
                name=str(req_data.get("name") or ""),
                weight_percentage=float(req_data.get("weight_percentage") or 0),
                accountability_statement=str(req_data.get("accountability_statement") or ""),
            )
            return (result, 201)

        if path == "/api/workforce/kpis":
            result = arch.define_kpi(
                kra_id=str(req_data.get("kra_id") or ""),
                code=str(req_data.get("code") or ""),
                name=str(req_data.get("name") or ""),
                unit=str(req_data.get("unit") or "COUNT"),
                target_value=float(req_data.get("target_value") or 0),
                definition=str(req_data.get("definition") or ""),
                polarity=str(req_data.get("polarity") or "HIGHER_IS_BETTER"),
                data_source_feed=str(req_data.get("data_source_feed") or "corporate_records"),
                verification_method=str(req_data.get("verification_method")
                                         or "TRANSACTION_RECONCILIATION"),
                measurement_frequency=str(req_data.get("measurement_frequency") or "MONTHLY"),
                paired_counter_metric_code=req_data.get("paired_counter_metric_code"),
            )
            return (result, 201)

        if path == "/api/workforce/measurements":
            result = arch.record_measurement(
                kpi_id=str(req_data.get("kpi_id") or ""),
                measured_value=float(req_data.get("measured_value") or 0),
                evidence_ref=str(req_data.get("evidence_ref") or ""),
                counter_metric_value=(float(req_data["counter_metric_value"])
                                      if req_data.get("counter_metric_value") is not None else None),
                mission_id=req_data.get("mission_id"),
            )
            return (result, 201)

        if path == "/api/workforce/evaluations":
            result = arch.evaluate_employee(
                employee_id=str(req_data.get("employee_id") or ""),
                period_start=float(req_data.get("period_start") or 0),
                period_end=float(req_data.get("period_end") or 0),
                evaluator_role=str(req_data.get("evaluator_role") or "EXEC_CHRO"),
                externally_blocked_kpi_ids=req_data.get("externally_blocked_kpi_ids") or [],
                collaboration_sla_score=float(req_data.get("collaboration_sla_score") or 100.0),
            )
            return (result, 200 if result.get("success") else 409)

        if path == "/api/workforce/capabilities":
            result = arch.register_capability(
                code=str(req_data.get("code") or ""),
                name=str(req_data.get("name") or ""),
                category=str(req_data.get("category") or ""),
                risk_class=str(req_data.get("risk_class") or "READ_ONLY"),
                cost_per_call_usd=float(req_data.get("cost_per_call_usd") or 0.001),
                input_schema=req_data.get("input_schema") or {},
                output_schema=req_data.get("output_schema") or {},
            )
            return (result, 201)

        if path == "/api/workforce/agents":
            result = arch.provision_agent(
                employee_id=str(req_data.get("employee_id") or ""),
                capability_code=str(req_data.get("capability_code") or ""),
                task_id=req_data.get("task_id"),
                mission_id=req_data.get("mission_id"),
                ttl_seconds=int(req_data.get("ttl_seconds") or 900),
                allocated_tokens=int(req_data.get("allocated_tokens") or 100000),
                quota=int(req_data["quota"]) if req_data.get("quota") else None,
            )
            return (result, 201)

        if path.startswith("/api/workforce/agents/") and path.endswith("/terminate"):
            instance_id = path.split("/")[4]
            result = arch.terminate_agent(
                instance_id=instance_id,
                employee_id=str(req_data.get("employee_id") or ""),
                reason=str(req_data.get("reason") or "task_complete"),
            )
            return (result, 200)

        if path == "/api/workforce/collaborations":
            result = arch.open_collaboration(
                mission_id=str(req_data.get("mission_id") or ""),
                initiator_department_id=str(req_data.get("initiator_department_id") or ""),
                target_department_id=str(req_data.get("target_department_id") or ""),
                deliverable_description=str(req_data.get("deliverable_description") or ""),
                sla_turnaround_hours=float(req_data.get("sla_turnaround_hours") or 24.0),
                escalation_owner_role=str(req_data.get("escalation_owner_role") or "COO"),
                shared_budget_usd=float(req_data.get("shared_budget_usd") or 0.0),
            )
            return (result, 201)

        if path.startswith("/api/workforce/collaborations/") and path.endswith("/advance"):
            collab_id = path.split("/")[4]
            result = arch.advance_collaboration(
                collab_id=collab_id,
                action=str(req_data.get("action") or "").upper(),
            )
            return (result, 200)

        return None
    except WorkforceError as exc:
        return ({"success": False, "error": str(exc)}, 400)
    except ValueError as exc:
        return ({"success": False, "error": str(exc)}, 400)
    except Exception as exc:
        return ({"success": False, "error": f"workforce error: {exc}"}, 500)
