"""HTTP surface for the company setup module.

Routes (all tenant-scoped; the tenant always comes from the verified token,
never from the body or a header):

    GET    /api/v1/companies
    POST   /api/v1/companies
    GET    /api/v1/companies/drafts
    POST   /api/v1/companies/drafts
    GET    /api/v1/companies/drafts/<draft_id>
    DELETE /api/v1/companies/drafts/<draft_id>
    GET    /api/v1/companies/<company_id>
    PATCH  /api/v1/companies/<company_id>
    POST   /api/v1/companies/<company_id>/submit
    GET    /api/v1/companies/<company_id>/build
    POST   /api/v1/companies/<company_id>/build/retry
    GET    /api/v1/companies/<company_id>/connections
    POST   /api/v1/companies/<company_id>/connections
    POST   /api/v1/companies/<company_id>/connections/<connection_id>/test
    DELETE /api/v1/companies/<company_id>/connections/<connection_id>
    GET    /api/v1/companies/<company_id>/deletion
    GET    /api/v1/companies/<company_id>/delete/plan
    POST   /api/v1/companies/<company_id>/delete/request
    POST   /api/v1/companies/<company_id>/delete/confirm-name
    POST   /api/v1/companies/<company_id>/delete/confirm-identity
    POST   /api/v1/companies/<company_id>/delete/cancel
    POST   /api/v1/companies/<company_id>/delete/export
    POST   /api/v1/companies/<company_id>/delete/purge
    GET    /api/v1/companies/<company_id>/export
    GET    /api/v1/companies/<company_id>/legal
    GET    /api/v1/companies/<company_id>/audit
    GET    /api/v1/companies/<company_id>/admins
    POST   /api/v1/companies/<company_id>/admins
    DELETE /api/v1/companies/<company_id>/admins/<user_id>
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.company_setup.permissions import PermissionDenied, Principal
from core.company_setup.service import CompanySetupError, CompanySetupService
from core.company_setup.status import InvalidTransition

logger = logging.getLogger("zonata.company_setup")

BASE = "/api/v1/companies"


def _q(params: Dict[str, List[str]], name: str, default: Optional[str] = None) -> Optional[str]:
    values = params.get(name) or []
    return values[0] if values else default


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


class CompanySetupAPI:
    """Thin dispatcher; all business rules live in the service."""

    def handle(
        self,
        method: str,
        path: str,
        query_params: Dict[str, List[str]],
        body: Dict[str, Any],
        auth_context: Optional[Dict[str, Any]],
        default_company_id: Optional[str] = None,
    ) -> Optional[Tuple[int, Any]]:
        if not path.startswith(BASE):
            return None
        if path != BASE and not path.startswith(BASE + "/"):
            return None

        principal = Principal.from_auth_context(auth_context)
        if not principal.tenant_id:
            return 401, {"error": "Unauthorized", "code": "TENANT_REQUIRED"}

        service = CompanySetupService(principal.tenant_id)
        segments = [seg for seg in path[len(BASE):].split("/") if seg]
        method = method.upper()

        try:
            return self._route(method, segments, query_params, body or {}, principal, service)
        except CompanySetupError as exc:
            return exc.status, exc.to_dict()
        except PermissionDenied as exc:
            return 403, {"error": str(exc), "code": "FORBIDDEN", "action": exc.action}
        except InvalidTransition as exc:
            return 409, {
                "error": str(exc),
                "code": "INVALID_STATUS_TRANSITION",
                "from": exc.current,
                "to": exc.target,
            }
        except ValueError as exc:
            return 400, {"error": str(exc), "code": "BAD_REQUEST"}
        except Exception:
            logger.exception("company setup request failed: %s %s", method, path)
            return 500, {"error": "Internal error", "code": "INTERNAL_ERROR"}

    # ------------------------------------------------------------------ route
    def _route(
        self,
        method: str,
        segments: List[str],
        query: Dict[str, List[str]],
        body: Dict[str, Any],
        principal: Principal,
        service: CompanySetupService,
    ) -> Tuple[int, Any]:
        # Collection + drafts
        if not segments:
            if method == "GET":
                return 200, service.list_companies(
                    page=int(_q(query, "page", "1") or 1),
                    page_size=int(_q(query, "page_size", "20") or 20),
                    status=_q(query, "status"),
                    company_type=_q(query, "type"),
                    query=_q(query, "q"),
                    include_deleted=_truthy(_q(query, "include_deleted")),
                )
            if method == "POST":
                return 201, service.create_company(principal, body)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        head = segments[0]

        if head == "sources" and len(segments) == 2 and segments[1] == "catalogue" and method == "GET":
            from core.company_setup import sources as source_module

            return 200, {"sources": source_module.catalogue()}

        if head == "drafts":
            if len(segments) == 1:
                if method == "GET":
                    return 200, {"drafts": service.list_drafts(principal)}
                if method in ("POST", "PUT", "PATCH"):
                    return 200, service.save_draft(
                        principal,
                        body,
                        company_id=body.get("company_id"),
                        draft_id=body.get("draft_id"),
                    )
                return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}
            draft_id = segments[1]
            if method == "GET":
                return 200, service.get_draft(principal, draft_id)
            if method == "DELETE":
                return 200, service.delete_draft(principal, draft_id)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        company_id = head
        action = segments[1] if len(segments) > 1 else None
        third = segments[2] if len(segments) > 2 else None
        fourth = segments[3] if len(segments) > 3 else None

        if action is None:
            if method == "GET":
                return 200, service.get_company(principal, company_id)
            if method in ("PATCH", "PUT"):
                return 200, service.update_company(principal, company_id, body)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        if action == "submit" and method == "POST":
            return 202, service.submit_company(principal, company_id)

        if action == "build" and method == "GET":
            service.require_company(principal, company_id)
            build = service.get_build(company_id)
            if not build:
                return 404, {"error": "No build run for this company", "code": "BUILD_NOT_FOUND"}
            return 200, build

        if action == "build" and third in ("retry", "resume") and method == "POST":
            return 202, service.retry_build(principal, company_id)

        if action == "connections":
            if method == "GET" and third is None:
                return 200, {"connections": service.list_connections(principal, company_id)}
            if method == "POST" and third is None:
                return 201, service.connect(principal, company_id, body)
            if third and fourth == "test" and method == "POST":
                return 200, service.test_connection(principal, company_id, third)
            if third and fourth == "verify" and method == "POST":
                return 200, service.request_verification(
                    principal, company_id, third, method=body.get("method")
                )
            if third and fourth == "verify" and method == "PUT":
                return 200, service.confirm_verification(
                    principal, company_id, third, token=body.get("token")
                )
            if third and method == "DELETE":
                return 200, service.disconnect(principal, company_id, third)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        if action == "sources":
            if method == "GET" and third is None:
                return 200, service.list_sources(principal, company_id)
            if third and fourth == "skip" and method == "POST":
                return 200, service.skip_source(principal, company_id, third, body.get("reason"))
            if third and fourth == "skip" and method == "DELETE":
                return 200, service.unskip_source(principal, company_id, third)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        if action == "readiness" and method == "GET":
            return 200, service.get_readiness(principal, company_id)

        if action == "files":
            if method == "GET":
                return 200, service.list_files(principal, company_id)
            if method == "POST":
                return 201, service.record_file(principal, company_id, body)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        if action == "deletion" and method == "GET":
            service.require_company(principal, company_id, include_deleted=True)
            return 200, {"deletion": service.get_deletion(company_id)}

        if action == "delete":
            if third == "plan" and method == "GET":
                return 200, service.deletion_plan(principal, company_id)
            if method != "POST":
                return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}
            if third == "request":
                return 200, service.request_deletion(principal, company_id)
            if third == "confirm-name":
                return 200, service.confirm_delete_name(principal, company_id, body.get("name"))
            if third == "confirm-identity":
                return 200, service.confirm_delete_identity(
                    principal,
                    company_id,
                    password=body.get("password"),
                    two_step_code=body.get("two_step_code"),
                )
            if third == "cancel":
                return 200, service.cancel_deletion(principal, company_id)
            if third == "export":
                return 200, service.retry_export(principal, company_id)
            if third == "purge":
                return 200, service.purge_now(principal, company_id)
            return 404, {"error": "Unknown delete step", "code": "NOT_FOUND"}

        if action == "export" and method == "GET":
            return 200, service.download_export_file(principal, company_id)

        if action == "legal" and method == "GET":
            return 200, {"legal_items": service.list_legal_items(principal, company_id)}

        if action == "audit" and method == "GET":
            return 200, service.audit_events(
                principal,
                company_id,
                limit=int(_q(query, "limit", "50") or 50),
                offset=int(_q(query, "offset", "0") or 0),
            )

        if action == "admins":
            if method == "GET":
                return 200, {"admins": service.list_admins(principal, company_id)}
            if method == "POST":
                return 200, service.grant_admin(principal, company_id, body.get("user_id"))
            if method == "DELETE" and third:
                return 200, service.revoke_admin(principal, company_id, third)
            return 405, {"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}

        return 404, {"error": "Endpoint not found", "code": "NOT_FOUND"}


company_setup_api = CompanySetupAPI()
