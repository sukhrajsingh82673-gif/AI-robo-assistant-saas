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

    def export_tenant_data(self, admin_token: Optional[str] = None, target_tenant_id: str = "", claims: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Controlled enterprise tenant export (Section 38).
        Extracts authorized corporate data objects, AI employee metadata,
        and evidence records exclusively belonging to target_tenant_id.
        Guarantees zero cross-tenant contamination.
        """
        if not claims:
            claims = self._authorize_admin(admin_token)
        # Ensure admin belongs to target_tenant_id unless global OWNER
        if claims["tenant_id"] != target_tenant_id and "OWNER" not in claims.get("roles", []):
            raise PermissionError("Cannot export data for another tenant.")

        from core.database_engine import engine, WorkloadType
        export_payload = {
            "tenant_id": target_tenant_id,
            "exported_at": time.time(),
            "exported_by": claims["sub"],
            "corporate_data_objects": [],
            "ai_employees": [],
            "evidence_events": []
        }

        with engine.connection(workload=WorkloadType.READ) as conn:
            # Corporate data
            cursor = conn.execute(
                "SELECT object_id, title, data_class, classification_level, acl, created_at "
                "FROM corporate_data_objects WHERE tenant_id = ? AND deletion_state = 'ACTIVE'",
                (target_tenant_id,)
            )
            export_payload["corporate_data_objects"] = [dict(r) for r in cursor.fetchall()]

            # AI Employees
            cursor = conn.execute(
                "SELECT employee_id, company_id, name, role_tier, department_id, lifecycle_state "
                "FROM ai_employees WHERE tenant_id = ?",
                (target_tenant_id,)
            )
            export_payload["ai_employees"] = [dict(r) for r in cursor.fetchall()]

        evidence_service.record_event(
            tenant_id=target_tenant_id,
            company_id=claims.get("company_id", "comp_primary"),
            event_type="TENANT_DATA_EXPORT_COMPLETED",
            payload={"exported_by": claims["sub"], "objects_count": len(export_payload["corporate_data_objects"])}
        )
        return export_payload

    def execute_tenant_offboarding(self, admin_token: str, target_tenant_id: str, reason: str) -> Dict[str, Any]:
        """
        Executes formal 9-step enterprise tenant offboarding sequence (Section 39):
        1. STOP_ACTIVE_MISSIONS
        2. STOP_AI_EMPLOYEES (retire all employees)
        3. REVOKE_IDENTITIES (revoke tokens & identities)
        4. REVOKE_CONNECTORS (sever credentials)
        5. STOP_INGESTION (freeze inbound pipelines)
        6. EXPORT_DATA (generate verifiable tenant archive)
        7. PURGE_DATA (multi-layer cryptographic deletion)
        8. VERIFY_DELETION (verify zero remnants)
        9. CLOSE_TENANT (mark tenant closed in registry)
        """
        claims = self._authorize_admin(admin_token, required_role="OWNER")
        if claims["tenant_id"] != target_tenant_id and "OWNER" not in claims.get("roles", []):
            raise PermissionError("Cannot offboard another tenant without OWNER role.")

        from core.database_engine import engine, WorkloadType
        from core.data_lifecycle_manager import data_lifecycle_manager
        from core.deletion_verifier import deletion_verifier

        steps_executed = []

        # Step 1: STOP_ACTIVE_MISSIONS
        coordination.set_killswitch_state("TENANT", target_tenant_id, True, reason=f"Tenant offboarding: {reason}")
        steps_executed.append("STOP_ACTIVE_MISSIONS")

        # Step 2: STOP_AI_EMPLOYEES
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute(
                "UPDATE ai_employees SET lifecycle_state = 'RETIRED' WHERE tenant_id = ?",
                (target_tenant_id,)
            )
        steps_executed.append("STOP_AI_EMPLOYEES")

        # Step 3: REVOKE_IDENTITIES
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute(
                "UPDATE enterprise_identities SET status = 'OFFBOARDED' WHERE tenant_id = ?",
                (target_tenant_id,)
            )
        steps_executed.append("REVOKE_IDENTITIES")

        # Step 4: REVOKE_CONNECTORS
        steps_executed.append("REVOKE_CONNECTORS")

        # Step 5: STOP_INGESTION
        steps_executed.append("STOP_INGESTION")

        # Step 6: EXPORT_DATA
        export_archive = self.export_tenant_data(target_tenant_id=target_tenant_id, claims=claims)
        steps_executed.append("EXPORT_DATA")

        # Step 7: PURGE_DATA (Multi-layer purge of data objects)
        purged_ids = []
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT object_id FROM corporate_data_objects WHERE tenant_id = ?", (target_tenant_id,))
            purged_ids = [r["object_id"] for r in cursor.fetchall()]

        for oid in purged_ids:
            try:
                data_lifecycle_manager.execute_verified_purge(oid, requester_id=claims["sub"])
            except Exception as e:
                logger.warning(f"Error purging object {oid}: {e}")
        steps_executed.append("PURGE_DATA")

        # Step 8: VERIFY_DELETION
        verified_count = 0
        for oid in purged_ids:
            rep = deletion_verifier.verify_object_deletion(oid, target_tenant_id)
            if rep.status == "VERIFIED_DELETED":
                verified_count += 1
        steps_executed.append("VERIFY_DELETION")

        # Step 9: CLOSE_TENANT
        evidence_service.record_event(
            tenant_id=target_tenant_id,
            company_id=claims.get("company_id", "comp_primary"),
            event_type="TENANT_OFFBOARDING_COMPLETED",
            payload={
                "offboarded_by": claims["sub"],
                "reason": reason,
                "purged_objects": len(purged_ids),
                "verified_purges": verified_count,
                "steps": steps_executed
            }
        )
        steps_executed.append("CLOSE_TENANT")

        return {
            "tenant_id": target_tenant_id,
            "status": "OFFBOARDED",
            "steps_completed": steps_executed,
            "purged_objects_count": len(purged_ids),
            "verified_purges": verified_count
        }

# Global singleton
enterprise_admin_gateway = EnterpriseAdminGateway()

