"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 19 — Enterprise Administration Gateway
Authorized corporate control plane for tenant administrators, security officers, and executive owners.

Constitutional Invariant:
  ADMINISTRATIVE_MUTATIONS_REQUIRE_STRICT_AUTHORIZATION
  ALL_ADMIN_ACTIONS_SEALED_IN_EVIDENCE_LEDGER
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from core.identity_gateway import identity_gateway
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState
from core.corporate_data_plane import corporate_data_gateway
from core.spend_governor import spend_governor
from core.distributed_coordination import coordination
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.admin.gateway")

class EnterpriseAdminGateway:
    """
    Control plane entry point for enterprise administrators.
    """
    AUTHORIZED_ADMIN_ROLES = {"ADMIN", "OWNER", "SECURITY_ADMIN", "COMPLIANCE_OFFICER"}

    def _authorize_admin(self, admin_token: str, required_role: Optional[str] = None) -> Dict[str, Any]:
        """Verify token and ensure user holds enterprise administration privileges."""
        valid, claims, reason = identity_gateway.verify_token(admin_token)
        if not valid or not claims:
            raise PermissionError(f"Admin authentication failed: {reason}")

        user_roles = set(claims.get("roles", []))
        if not user_roles.intersection(self.AUTHORIZED_ADMIN_ROLES):
            raise PermissionError(f"User '{claims.get('sub')}' lacks enterprise administration authority (Roles: {user_roles}).")

        if required_role and required_role not in user_roles and "OWNER" not in user_roles:
            raise PermissionError(f"Specific role '{required_role}' required for this administrative action.")

        return claims

    def suspend_employee(self, admin_token: str, employee_id: str, reason: str) -> bool:
        """Suspend an AI Employee immediately."""
        claims = self._authorize_admin(admin_token)
        admin_id = claims["sub"]
        tenant_id = claims["tenant_id"]

        success = ai_employee_registry.advance_lifecycle(
            employee_id=employee_id,
            new_state=EmployeeLifecycleState.SUSPENDED,
            approver_id=admin_id,
            reason=reason
        )

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=claims.get("company_id", "comp_primary"),
            event_type="ADMIN_SUSPEND_EMPLOYEE",
            payload={"admin_id": admin_id, "employee_id": employee_id, "reason": reason}
        )
        return success

    def terminate_employee(self, admin_token: str, employee_id: str, reason: str) -> bool:
        """Permanently retire and offboard an AI Employee."""
        claims = self._authorize_admin(admin_token)
        admin_id = claims["sub"]
        tenant_id = claims["tenant_id"]

        ai_employee_registry.advance_lifecycle(
            employee_id=employee_id,
            new_state=EmployeeLifecycleState.OFFBOARDED,
            approver_id=admin_id,
            reason=reason
        )

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=claims.get("company_id", "comp_primary"),
            event_type="ADMIN_TERMINATE_EMPLOYEE",
            payload={"admin_id": admin_id, "employee_id": employee_id, "reason": reason}
        )
        return True

    def revoke_identity(self, admin_token: str, target_identity_id: str, reason: str) -> bool:
        """Immediately sever identity authority and revoke sessions."""
        claims = self._authorize_admin(admin_token)
        admin_id = claims["sub"]
        tenant_id = claims["tenant_id"]

        success = identity_gateway.offboard_identity(target_identity_id, reason=f"Admin {admin_id}: {reason}")
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=claims.get("company_id", "comp_primary"),
            event_type="ADMIN_REVOKE_IDENTITY",
            payload={"admin_id": admin_id, "target_identity_id": target_identity_id, "reason": reason}
        )
        return success

    def trip_emergency_killswitch(self, admin_token: str, scope: str, target_id: str, reason: str) -> bool:
        """Trip a fleet or entity killswitch."""
        claims = self._authorize_admin(admin_token, required_role="SECURITY_ADMIN")
        admin_id = claims["sub"]
        tenant_id = claims["tenant_id"]

        coordination.set_killswitch_state(scope, target_id, True, reason=f"Admin {admin_id}: {reason}")
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=claims.get("company_id", "comp_primary"),
            event_type="ADMIN_EMERGENCY_KILLSWITCH_TRIPPED",
            payload={"admin_id": admin_id, "scope": scope, "target_id": target_id, "reason": reason}
        )
        return True

# Global singleton
enterprise_admin_gateway = EnterpriseAdminGateway()
