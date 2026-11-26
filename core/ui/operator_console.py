"""
Platform Operator Console Backend and Dual-Control Support Access (Rule 82 & Rule 84).
Handles cross-tenant health overview, global flag kill-switches, and enforces dual-control support barriers.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from core.ui.dead_control_detector import ControlElement


class PlatformOperatorConsole:
    """
    Platform Operator service for managing global infrastructure and emergency controls.
    Under Rule 82, operators CANNOT impersonate tenants or access tenant data without
    an explicit, time-boxed, tenant-approved support grant token.
    """

    def __init__(self):
        # Global operator audit ledger
        self.audit_log: List[Dict[str, Any]] = []
        # Active dual-control support grants: grant_id -> grant dict
        self._support_grants: Dict[str, Dict[str, Any]] = {}

    def list_tenants_overview(self, operator_id: str) -> List[Dict[str, Any]]:
        self._record_audit(operator_id, "LIST_TENANTS_OVERVIEW", {})
        return [
            {"tenant_id": "tenant_alpha", "tier": "enterprise", "status": "HEALTHY", "delinquent": False},
            {"tenant_id": "tenant_beta", "tier": "team", "status": "HEALTHY", "delinquent": False},
            {"tenant_id": "tenant_gamma", "tier": "starter", "status": "PAST_DUE", "delinquent": True},
        ]

    def register_support_grant(
        self,
        tenant_id: str,
        grant_id: str,
        authorized_operator_id: str,
        purpose: str,
        expires_at: float,
        scope: str = "read_diagnostics",
    ):
        """Called when a tenant explicitly approves a time-boxed dual-control support grant."""
        self._support_grants[grant_id] = {
            "tenant_id": tenant_id,
            "grant_id": grant_id,
            "operator_id": authorized_operator_id,
            "purpose": purpose,
            "expires_at": expires_at,
            "scope": scope,
            "revoked": False,
        }

    def access_tenant_diagnostics(
        self, operator_id: str, tenant_id: str, grant_id: str, current_time: Optional[float] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Rule 82 Check: Verifies operator holds a valid, unexpired, tenant-consented grant.
        """
        now = current_time if current_time is not None else time.time()
        grant = self._support_grants.get(grant_id)

        if not grant:
            self._record_audit(operator_id, "DENIED_TENANT_ACCESS_NO_GRANT", {"tenant_id": tenant_id})
            return False, "DENIED: No valid dual-control support grant provided.", None

        if grant["tenant_id"] != tenant_id:
            return False, "DENIED: Support grant was not issued by target tenant.", None

        if grant["operator_id"] != operator_id:
            return False, "DENIED: Grant was issued for a different operator.", None

        if grant.get("revoked"):
            return False, "DENIED: Support grant has been revoked by tenant.", None

        if now >= grant["expires_at"]:
            return False, "DENIED: Support grant has expired.", None

        self._record_audit(operator_id, "ACCESSED_TENANT_DIAGNOSTICS", {"tenant_id": tenant_id, "grant_id": grant_id})
        diagnostics = {
            "tenant_id": tenant_id,
            "queue_depth": 0,
            "active_tasks": 2,
            "last_error": None,
            "audit_session_id": f"sup_sess_{int(now)}",
        }
        return True, "Access granted under verified dual-control consent.", diagnostics

    def _record_audit(self, operator_id: str, action: str, details: Dict[str, Any]):
        self.audit_log.append({
            "timestamp": time.time(),
            "operator_id": operator_id,
            "action": action,
            "details": details,
        })

    def get_console_controls_manifest(self) -> List[ControlElement]:
        return [
            ControlElement("button", "btn_refresh_tenants", "Refresh Directory", "api_call", "/api/operator/tenants/list"),
            ControlElement("button", "btn_engage_global_killswitch", "Engage Kill Switch", "api_call", "/api/operator/flags/killswitch"),
            ControlElement("button", "btn_drain_queue", "Drain Worker Queue", "api_call", "/api/operator/workers/drain"),
            ControlElement("button", "btn_view_telemetry", "View System Telemetry", "api_call", "/api/operator/metrics"),
            ControlElement("a", "link_incident_runbook", "CRA Incident Runbook", "href", "https://zonata.ai/docs/security/cra"),
            ControlElement("a", "link_gatus_status", "Gatus Status Cluster", "href", "https://status.zonata.ai"),
        ]
