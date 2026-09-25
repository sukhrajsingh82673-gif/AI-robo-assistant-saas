"""
RoboAssistant Company OS 1.0 — First-Class Approvals Pipeline
Full approval object lifecycle: REQUEST -> CONTEXT -> RISK -> CONSEQUENCE -> EVIDENCE -> APPROVER -> DECISION -> AUDIT.
"""

from typing import List, Dict, Any, Optional
import time
import uuid
import hashlib
from .db import db
from .auth import AuthorizationEnforcer, UserRole

class ApprovalPipeline:
    @staticmethod
    def create_request(
        tenant_id: str,
        company_id: str,
        agent_id: str,
        action_desc: str,
        reason: str,
        risk_level: str = "MEDIUM",
        consequence: str = "Execution of scoped action",
        mission_id: Optional[str] = None
    ) -> Dict[str, Any]:
        request_id = f"apr_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO approvals (
                    request_id, tenant_id, company_id, mission_id, agent_id,
                    action_desc, reason, risk_level, consequence, status, requested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (request_id, tenant_id, company_id, mission_id, agent_id,
                 action_desc, reason, risk_level, consequence, "PENDING", now)
            )
            conn.commit()

        return {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "agent_id": agent_id,
            "action_desc": action_desc,
            "reason": reason,
            "risk_level": risk_level,
            "consequence": consequence,
            "status": "PENDING",
            "requested_at": now
        }

    @staticmethod
    def decide_request(
        tenant_id: str,
        request_id: str,
        approver_user: Dict[str, Any],
        approved: bool,
        rejection_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        if not AuthorizationEnforcer.can_approve(approver_user.get("role", "")):
            return {
                "success": False,
                "error": "INSUFFICIENT_PERMISSIONS: Only Owner or Executive roles can decide approvals."
            }

        now = time.time()
        status = "APPROVED" if approved else "REJECTED"
        grant_hash = None
        if approved:
            raw_grant = f"{request_id}:{approver_user['user_id']}:{now}:SIGN_APPROVED"
            grant_hash = f"GRANT_{hashlib.sha256(raw_grant.encode('utf-8')).hexdigest()[:24]}"

        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE approvals
                SET status = ?, approver_user_id = ?, signed_grant_hash = ?, decided_at = ?
                WHERE tenant_id = ? AND request_id = ?
                """,
                (status, approver_user["user_id"], grant_hash, now, tenant_id, request_id)
            )
            conn.commit()

        return {
            "success": True,
            "request_id": request_id,
            "status": status,
            "signed_grant_hash": grant_hash,
            "decided_at": now
        }

    @staticmethod
    def list_approvals(tenant_id: str, company_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            sql = "SELECT * FROM approvals WHERE tenant_id = ?"
            params = [tenant_id]
            if company_id:
                sql += " AND company_id = ?"
                params.append(company_id)
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY requested_at DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
