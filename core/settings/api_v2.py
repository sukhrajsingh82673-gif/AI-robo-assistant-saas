"""HTTP surface for Settings V2.

The API layer is deliberately thin: it authenticates through the verified
request context, builds a ``Principal``, translates JSON into service calls,
and maps typed settings errors to status codes.  It contains no permission
logic and never returns a secret value.

Routes are mounted under ``/api/settings/v2`` by ``api_server.py``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.settings import rbac
from core.settings.errors import (
    ApprovalRequired,
    NotFoundError,
    SettingsError,
    ValidationError,
)
from core.settings.models import ScopeType, SettingStatus
from core.settings.service import SettingsV2Service, settings_v2_service


def _first(query: Dict[str, Any], name: str, default: Optional[str] = None) -> Optional[str]:
    value = (query or {}).get(name)
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else default
    if value is None:
        return default
    return str(value)


def _parse_scope(raw: Any, default: ScopeType = ScopeType.COMPANY) -> ScopeType:
    if raw is None or raw == "":
        return default
    try:
        return ScopeType(str(raw).lower())
    except ValueError:
        raise ValidationError(
            "scope_type must be one of: "
            + ", ".join(scope.value for scope in ScopeType)
        )


def _optional_scope(raw: Any) -> Optional[ScopeType]:
    """Return ``None`` when the caller did not pin a view scope."""
    if raw is None or raw == "":
        return None
    return _parse_scope(raw)


def _optional_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Expected an integer value.")


def _optional_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValidationError("Expected a numeric value.")


class SettingsV2API:
    def __init__(self, service: Optional[SettingsV2Service] = None) -> None:
        self.service = service or settings_v2_service

    # ------------------------------------------------------------------ entry
    def handle(
        self,
        method: str,
        path: str,
        query: Dict[str, Any],
        body: Dict[str, Any],
        auth_context: Dict[str, Any],
        resolved_company_id: Optional[str] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        try:
            principal = rbac.Principal.from_auth_context(auth_context)
            company_id = resolved_company_id or principal.company_id
            subpath = path[len("/api/settings/v2"):].strip("/")
            if method == "GET":
                return self._get(subpath, query, principal, company_id)
            if method == "POST":
                return self._post(subpath, query, body or {}, principal, company_id)
            return 405, {
                "success": False,
                "error": f"Method {method} is not supported for Settings V2.",
                "code": "METHOD_NOT_ALLOWED",
            }
        except ApprovalRequired as exc:
            return exc.status_code, {
                "success": False,
                "code": exc.code,
                "error": str(exc),
                "approval_id": exc.approval_id,
            }
        except SettingsError as exc:
            payload: Dict[str, Any] = {
                "success": False,
                "code": exc.code,
                "error": str(exc),
            }
            hint = getattr(exc, "hint", "")
            if hint:
                payload["hint"] = hint
            return exc.status_code, payload
        except KeyError as exc:
            return 404, {
                "success": False,
                "code": "NOT_FOUND",
                "error": str(exc).strip("'\""),
            }
        except Exception as exc:  # pragma: no cover - defensive boundary
            # Never echo a secret value or an internal stack trace.
            return 500, {
                "success": False,
                "code": "INTERNAL_ERROR",
                "error": f"Settings request failed ({type(exc).__name__}).",
            }

    # -------------------------------------------------------------------- GET
    def _get(
        self,
        subpath: str,
        query: Dict[str, Any],
        principal: rbac.Principal,
        company_id: str,
    ) -> Tuple[int, Dict[str, Any]]:
        if subpath in ("", "registry", "catalog"):
            section = _first(query, "section")
            return 200, {
                "success": True,
                "registry": self.service.registry_catalog(principal, section=section),
            }

        if subpath == "capabilities":
            from core.capability_probe import probe_all_capabilities, summarize_capabilities
            probe_results = probe_all_capabilities()
            summary = summarize_capabilities(probe_results)

            plain_language_map = {
                "OK": "live",
                "ACCEPTED_BY_PROVIDER": "live",
                "SANDBOX": "test only",
                "NOT_CONFIGURED": "not connected",
                "DEGRADED": "degraded",
                "NOT_IMPLEMENTED": "not implemented",
                "FAILED": "failed",
            }

            capabilities_list = []
            for cap_name, res in sorted(probe_results.items()):
                st = res.status.value if hasattr(res.status, "value") else str(res.status)
                plain_lbl = plain_language_map.get(st, st.lower())
                capabilities_list.append({
                    "capability": cap_name,
                    "status": st,
                    "plain_language": plain_lbl,
                    "provider": res.provider,
                    "provider_ref": res.provider_ref,
                    "sandbox": res.sandbox,
                    "latency_ms": round(res.latency_ms, 3),
                    "cost": res.cost,
                    "error": res.error,
                })
            return 200, {
                "success": True,
                "summary": summary,
                "capabilities": capabilities_list
            }

        if subpath == "effective":
            key = _first(query, "key")
            if not key:
                raise ValidationError("'key' is required.")
            payload = self.service.effective(
                principal,
                key,
                company_id=_first(query, "company_id") or company_id,
                department_id=_first(query, "department_id"),
                agent_id=_first(query, "agent_id"),
                user_id=_first(query, "user_id"),
                view_scope=_optional_scope(_first(query, "scope")),
            )
            return 200, {"success": True, "setting": payload}

        if subpath in ("values", "settings"):
            key = _first(query, "key")
            if key:
                payload = self.service.effective(
                    principal,
                    key,
                    company_id=_first(query, "company_id") or company_id,
                )
                return 200, {"success": True, "setting": payload}
            settings = self.service.effective_section(
                principal,
                section=_first(query, "section"),
                category=_first(query, "category"),
                company_id=_first(query, "company_id") or company_id,
                department_id=_first(query, "department_id"),
                agent_id=_first(query, "agent_id"),
                user_id=_first(query, "user_id"),
                view_scope=_optional_scope(_first(query, "scope")),
                include_hidden=str(_first(query, "include_hidden", "0")) == "1",
            )
            return 200, {
                "success": True,
                "settings": settings,
                "count": len(settings),
            }

        if subpath == "secrets":
            return 200, {
                "success": True,
                "secrets": self.service.list_secrets(
                    principal,
                    company_id=_first(query, "company_id") or company_id,
                    scope_type=_parse_scope(_first(query, "scope_type"))
                    if _first(query, "scope_type")
                    else None,
                    scope_id=_first(query, "scope_id"),
                ),
            }

        if subpath == "approvals":
            return 200, {
                "success": True,
                "approvals": self.service.list_approvals(
                    principal,
                    company_id=_first(query, "company_id") or company_id,
                    status=_first(query, "status"),
                ),
            }

        if subpath == "audit":
            events = self.service.list_audit(
                principal,
                company_id=_first(query, "company_id") or company_id,
                key=_first(query, "key"),
                actor=_first(query, "actor"),
                actor_type=_first(query, "actor_type"),
                from_ts=_optional_float(_first(query, "from")),
                to_ts=_optional_float(_first(query, "to")),
                limit=_optional_int(_first(query, "limit")) or 100,
            )
            return 200, {"success": True, "events": events, "count": len(events)}

        if subpath == "audit/verify":
            return 200, {"success": True, "verification": self.service.verify_audit(principal)}

        if subpath == "diff":
            company_a = _first(query, "company_a") or company_id
            company_b = _first(query, "company_b")
            if not company_b:
                raise ValidationError("'company_b' is required.")
            keys = None
            raw_keys = _first(query, "keys")
            if raw_keys:
                keys = [item.strip() for item in raw_keys.split(",") if item.strip()]
            return 200, {
                "success": True,
                "differences": self.service.diff(principal, company_a, company_b, keys),
            }

        if subpath == "revision":
            return 200, {"success": True, "revision": self.service.current_revision(principal)}

        raise NotFoundError(f"Unknown Settings V2 endpoint '/{subpath}'.")

    # ------------------------------------------------------------------- POST
    def _post(
        self,
        subpath: str,
        query: Dict[str, Any],
        body: Dict[str, Any],
        principal: rbac.Principal,
        company_id: str,
    ) -> Tuple[int, Dict[str, Any]]:
        if subpath in ("values", "settings"):
            key = str(body.get("key") or "")
            if not key:
                raise ValidationError("'key' is required.")
            if "value" not in body:
                raise ValidationError("'value' is required.")
            if "expected_version" not in body:
                raise ValidationError(
                    "'expected_version' is required for optimistic concurrency; use 0 for a new override."
                )
            result = self.service.set_value(
                principal,
                key,
                body.get("value"),
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                expected_version=_optional_int(body.get("expected_version")),
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, "result": result}

        if subpath in ("values/reset", "settings/reset"):
            key = str(body.get("key") or "")
            if not key:
                raise ValidationError("'key' is required.")
            result = self.service.reset_value(
                principal,
                key,
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                expected_version=_optional_int(body.get("expected_version")),
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, "result": result}

        if subpath in ("values/bulk", "settings/bulk"):
            changes = body.get("changes")
            preview = bool(body.get("preview", False))
            if preview:
                results = self.service.bulk_preview(
                    principal,
                    changes,
                    company_id=body.get("company_id") or company_id,
                )
                return 200, {"success": True, "preview": results, "count": len(results)}
            result = self.service.bulk_apply(
                principal,
                changes,
                company_id=body.get("company_id") or company_id,
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, result

        if subpath in ("lock", "unlock"):
            key = str(body.get("key") or "")
            if not key:
                raise ValidationError("'key' is required.")
            result = self.service.set_lock(
                principal,
                key,
                subpath == "lock",
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                expected_version=_optional_int(body.get("expected_version")),
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, "result": result}

        if subpath == "secrets":
            name = str(body.get("name") or body.get("key") or "")
            if not name:
                raise ValidationError("'name' is required.")
            if "value" not in body:
                raise ValidationError("'value' is required.")
            result = self.service.put_secret(
                principal,
                name,
                str(body.get("value")),
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, "result": result}

        if subpath == "secrets/rotate":
            name = str(body.get("name") or body.get("key") or "")
            if not name:
                raise ValidationError("'name' is required.")
            if "value" not in body:
                raise ValidationError("'value' is required.")
            result = self.service.put_secret(
                principal,
                name,
                str(body.get("value")),
                rotate=True,
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                reason=str(body.get("reason") or "Secret rotated."),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, "result": result}

        if subpath == "secrets/revoke":
            name = str(body.get("name") or body.get("key") or "")
            if not name:
                raise ValidationError("'name' is required.")
            result = self.service.revoke_secret(
                principal,
                name,
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                reason=str(body.get("reason") or "Secret revoked."),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, "result": result}

        if subpath == "approvals":
            key = str(body.get("key") or "")
            if not key:
                raise ValidationError("'key' is required.")
            if "value" not in body:
                raise ValidationError("'value' is required.")
            result = self.service.propose(
                principal,
                key,
                body.get("value"),
                scope_type=_parse_scope(body.get("scope_type")),
                scope_id=body.get("scope_id"),
                company_id=body.get("company_id") or company_id,
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, {"success": True, **result}

        if subpath.startswith("approvals/") and subpath.endswith("/decide"):
            parts = subpath.split("/")
            if len(parts) != 3:
                raise NotFoundError(f"Unknown Settings V2 endpoint '/{subpath}'.")
            approval_id = parts[1]
            decision = str(body.get("decision") or "").lower()
            if decision in ("approve", "approved", "true"):
                approve = True
            elif decision in ("reject", "rejected", "false"):
                approve = False
            else:
                raise ValidationError("'decision' must be 'approve' or 'reject'.")
            result = self.service.decide_approval(
                principal,
                approval_id,
                approve,
                decision_reason=str(body.get("reason") or body.get("decision_reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, result

        if subpath.startswith("actions/"):
            action_id = subpath.split("/", 1)[1]
            result = self.service.execute_action(
                principal,
                action_id,
                confirmation=str(body.get("confirmation") or ""),
                company_id=body.get("company_id") or company_id,
                reason=str(body.get("reason") or ""),
                request_id=str(body.get("request_id") or ""),
                ip_address=str(body.get("ip_address") or ""),
            )
            return 200, result

        raise NotFoundError(f"Unknown Settings V2 endpoint '/{subpath}'.")


settings_v2_api = SettingsV2API()
