"""
ZONATA / RoboAssistant — OpenAPI document assembly
====================================================
Serves a real OpenAPI 3.0.3 document instead of the SPA ``index.html`` that the
static handler used to return for ``/openapi.json``.

The document merges the versioned specs shipped in the repository
(``openapi_v6.json`` … ``openapi_v8.json``) with the core platform endpoints
that are implemented in ``api_server.py``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSIONED_SPECS = ("openapi_v6.json", "openapi_v7.json", "openapi_v8.json")


def _error_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "code": {"type": "string"},
            "detail": {"type": "string"},
        },
    }


def _op(summary: str, tag: str, method: str = "get", secured: bool = True) -> Dict[str, Any]:
    op: Dict[str, Any] = {
        "summary": summary,
        "tags": [tag],
        "responses": {
            "200": {"description": "Successful response"},
            "401": {"description": "Missing or invalid bearer token", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
            "403": {"description": "Tenant isolation violation", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
        },
    }
    if secured:
        op["security"] = [{"bearerAuth": []}]
    return op


def build_openapi() -> Dict[str, Any]:
    paths: Dict[str, Any] = {}
    schemas: Dict[str, Any] = {"Error": _error_schema()}

    for name in _VERSIONED_SPECS:
        candidate = os.path.join(_BASE_DIR, name)
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                spec = json.load(fh)
        except Exception:
            continue
        for path, item in (spec.get("paths") or {}).items():
            paths.setdefault(path, item)
        for key, value in ((spec.get("components") or {}).get("schemas") or {}).items():
            schemas.setdefault(key, value)

    core: Dict[str, Any] = {
        "/healthz": {"get": {**_op("Liveness and subsystem health", "System", secured=False)}},
        "/readyz": {"get": {**_op("Database readiness probe", "System", secured=False)}},
        "/api/auth/environment": {"get": {**_op("Authentication environment posture", "System", secured=False)}},
        "/api/portfolio": {"get": {**_op("List companies in the authenticated tenant portfolio", "Companies")}},
        "/api/companies": {"get": {**_op("List companies", "Companies"), "post": {**_op("Create a company", "Companies", "post")}}},
        "/api/companies/{company_id}": {"get": {**_op("Get a company", "Companies")}},
        "/api/companies/{company_id}/workforce": {"post": {**_op("Create a workforce member", "Workforce", "post")}},
        "/api/companies/{company_id}/missions": {"post": {**_op("Create a mission", "Missions", "post")}},
        "/api/coworker/missions": {"get": {**_op("List background missions", "Missions"), "post": {**_op("Submit a background mission", "Missions", "post")}}},
        "/api/coworker/missions/{mission_id}": {"get": {**_op("Get mission status and deliverables", "Missions")}},
        "/api/ceo/chat": {"post": {**_op("AI CEO grounded conversation (LLM)", "AI CEO", "post")}},
        "/api/ceo/cycle": {"get": {**_op("Run the executive operating cycle", "AI CEO"), "post": {**_op("Run the executive operating cycle", "AI CEO", "post")}}},
        "/api/ceo/intelligence": {"get": {**_op("Company intelligence summary from real data", "AI CEO")}},
        "/api/llm/status": {"get": {**_op("Configured LLM provider and availability", "LLM")}},
        "/api/llm/providers": {"get": {**_op("List selectable LLM providers", "LLM")}},
        "/api/llm/test": {"post": {**_op("Live inference probe against the configured provider", "LLM", "post")}},
        "/api/settings": {"get": {**_op("List settings", "Settings"), "post": {**_op("Persist settings", "Settings", "post")}}},
        "/api/settings/category/{category_id}": {"get": {**_op("Get settings in a category", "Settings")}},
        "/api/settings/effective": {"get": {**_op("Effective enforcement values", "Settings")}},
        "/api/settings/test/{target}": {"post": {**_op("Run a real subsystem diagnostic", "Settings", "post")}},
        "/api/evidence": {"get": {**_op("Tenant-scoped evidence ledger summary", "Evidence")}},
        "/api/kpis": {"get": {**_op("KPIs computed from booked data and the evidence ledger", "Analytics")}},
        "/api/connectors": {"get": {**_op("Connector qualification status", "Integrations")}},
        "/api/run-workload": {"post": {**_op("Launch an operational workload as a real mission", "Missions", "post")}},
    }
    for path, item in core.items():
        paths.setdefault(path, item)

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "ZONATA / RoboAssistant API",
            "version": "1.0.0",
            "description": (
                "Multi-tenant company operating system API. All stateful endpoints "
                "are scoped to the tenant resolved from the verified bearer token. "
                "Endpoints that cannot be executed honestly return explicit error "
                "codes such as NO_COMPANY or NOT_CONFIGURED rather than mock data."
            ),
        },
        "servers": [{"url": "/", "description": "Current deployment"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            "schemas": schemas,
        },
        "paths": dict(sorted(paths.items())),
    }
