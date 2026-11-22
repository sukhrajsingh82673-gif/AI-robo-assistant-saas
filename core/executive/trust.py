"""
ZONATA Workforce Trust & Autonomy Service
OpenCode Step 2J: Earned autonomy through measured performance.
Rule 19: Conservative by default (SHADOW). Promotion requires verified thresholds and human approval. Demotion is automatic.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, Any, Optional

from core.db import db
from core.evidence_service import evidence_service
from core.work.inbox import human_inbox_service, InboxItemType
from core.executive.types import (
    TrustLevel,
    EmployeeTrustModel,
    PromotionThresholdNotMetError,
    UnauthorizedPromotionApproverError,
    EmployeeSuspendedError,
)


class WorkforceTrustService:
    """
    Manages employee trust levels, promotion thresholds, automatic demotions,
    and suspension/kill-switch controls.
    """

    HUMAN_PRINCIPAL_ROLES = {"OWNER", "HUMAN_BOARD", "HUMAN_ADMIN", "HUMAN"}

    @classmethod
    def get_or_create_trust(
        cls,
        tenant_id: str,
        company_id: str,
        employee_id: str,
    ) -> EmployeeTrustModel:
        """Retrieves or initializes an employee's trust level in SHADOW status."""
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM employee_trust_levels WHERE tenant_id = ? AND company_id = ? AND employee_id = ?",
                (tenant_id, company_id, employee_id)
            ).fetchone()

            if not row:
                trust_id = f"trt_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO employee_trust_levels (
                        id, tenant_id, company_id, employee_id, current_level,
                        tasks_completed_count, verified_pass_rate, sop_compliance_score,
                        policy_violation_count, last_promoted_at, is_suspended, is_killed,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'SHADOW', 0, 1.0, 100.0, 0, NULL, 0, 0, ?, ?)
                    """,
                    (trust_id, tenant_id, company_id, employee_id, now, now)
                )
                conn.commit()
                return EmployeeTrustModel(
                    id=trust_id,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    employee_id=employee_id,
                    current_level=TrustLevel.SHADOW,
                    tasks_completed_count=0,
                    verified_pass_rate=1.0,
                    sop_compliance_score=100.0,
                    policy_violation_count=0,
                    last_promoted_at=None,
                    is_suspended=False,
                    is_killed=False,
                    created_at=now,
                    updated_at=now,
                )

        return EmployeeTrustModel(
            id=row["id"],
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
            employee_id=row["employee_id"],
            current_level=TrustLevel(row["current_level"]),
            tasks_completed_count=row["tasks_completed_count"],
            verified_pass_rate=row["verified_pass_rate"],
            sop_compliance_score=row["sop_compliance_score"],
            policy_violation_count=row["policy_violation_count"],
            last_promoted_at=row["last_promoted_at"],
            is_suspended=bool(row["is_suspended"]),
            is_killed=bool(row["is_killed"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    def update_metrics(
        cls,
        tenant_id: str,
        company_id: str,
        employee_id: str,
        tasks_completed: int,
        verified_pass_rate: float,
        sop_compliance_score: float,
        policy_violations: int = 0,
    ) -> EmployeeTrustModel:
        """Updates measured performance metrics for an employee from verified system records."""
        # Ensure row exists before update
        cls.get_or_create_trust(tenant_id, company_id, employee_id)
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE employee_trust_levels
                SET tasks_completed_count = ?,
                    verified_pass_rate = ?,
                    sop_compliance_score = ?,
                    policy_violation_count = policy_violation_count + ?,
                    updated_at = ?
                WHERE tenant_id = ? AND company_id = ? AND employee_id = ?
                """,
                (
                    tasks_completed, verified_pass_rate, sop_compliance_score,
                    policy_violations, now, tenant_id, company_id, employee_id
                )
            )
            conn.commit()

        # If policy violations occurred, trigger automatic demotion
        if policy_violations > 0:
            cls.demote_employee(
                tenant_id, company_id, employee_id,
                reason=f"Automatic demotion due to {policy_violations} policy violation(s)."
            )

        return cls.get_or_create_trust(tenant_id, company_id, employee_id)

    @classmethod
    def promote_employee(
        cls,
        tenant_id: str,
        company_id: str,
        employee_id: str,
        target_level: TrustLevel,
        approved_by_principal_role: str,
        min_tasks: int = 5,
        min_pass_rate: float = 0.95,
        min_sop_compliance: float = 90.0,
    ) -> EmployeeTrustModel:
        """
        Promotes an employee to a higher trust tier.
        Requires meeting measured performance thresholds and human approval.
        """
        # 1. Rule 15: Human Approval Guard
        if approved_by_principal_role.upper() not in cls.HUMAN_PRINCIPAL_ROLES:
            raise UnauthorizedPromotionApproverError(
                f"Promotion can only be approved by a verified human principal (received '{approved_by_principal_role}')."
            )

        trust = cls.get_or_create_trust(tenant_id, company_id, employee_id)
        if trust.is_suspended or trust.is_killed:
            raise EmployeeSuspendedError(f"Cannot promote suspended or terminated employee '{employee_id}'.")

        # 2. Measured Threshold Checks
        errors = []
        if trust.tasks_completed_count < min_tasks:
            errors.append(f"Completed tasks ({trust.tasks_completed_count}) < required ({min_tasks})")
        if trust.verified_pass_rate < min_pass_rate:
            errors.append(f"Verified pass rate ({trust.verified_pass_rate:.2f}) < required ({min_pass_rate:.2f})")
        if trust.sop_compliance_score < min_sop_compliance:
            errors.append(f"SOP compliance ({trust.sop_compliance_score:.1f}%) < required ({min_sop_compliance:.1f}%)")
        if trust.policy_violation_count > 0:
            errors.append(f"Policy violations ({trust.policy_violation_count}) > 0")

        if errors:
            raise PromotionThresholdNotMetError(
                f"Promotion threshold not met for employee '{employee_id}': {'; '.join(errors)}"
            )

        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE employee_trust_levels
                SET current_level = ?, last_promoted_at = ?, updated_at = ?
                WHERE tenant_id = ? AND company_id = ? AND employee_id = ?
                """,
                (target_level.value, now, now, tenant_id, company_id, employee_id)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="EMPLOYEE_PROMOTED",
            payload={"employee_id": employee_id, "new_level": target_level.value, "approver": approved_by_principal_role},
            action_id=f"prom_{employee_id}_{int(now)}",
        )

        return cls.get_or_create_trust(tenant_id, company_id, employee_id)

    @classmethod
    def demote_employee(
        cls,
        tenant_id: str,
        company_id: str,
        employee_id: str,
        reason: str,
        target_level: TrustLevel = TrustLevel.SHADOW,
    ) -> EmployeeTrustModel:
        """
        Demotes an employee immediately on policy violations or repeated verification failures.
        Dispatches notification to human inbox.
        """
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE employee_trust_levels
                SET current_level = ?, updated_at = ?
                WHERE tenant_id = ? AND company_id = ? AND employee_id = ?
                """,
                (target_level.value, now, tenant_id, company_id, employee_id)
            )
            conn.commit()

        # Enqueue alert into human inbox
        human_inbox_service.create_item(
            tenant_id=tenant_id,
            company_id=company_id,
            item_type=InboxItemType.TASK_INTERVENTION,
            title=f"Employee Demoted: {employee_id} -> {target_level.value}",
            context_data={"employee_id": employee_id, "reason": reason, "target_level": target_level.value},
            target_principal_type="OWNER",
            target_principal_id="principal_owner",
            decision_needed="ACKNOWLEDGE_OR_REVIEW_SUSPENSION",
        )

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="EMPLOYEE_DEMOTED",
            payload={"employee_id": employee_id, "target_level": target_level.value, "reason": reason},
            action_id=f"dem_{employee_id}_{int(now)}",
        )

        return cls.get_or_create_trust(tenant_id, company_id, employee_id)

    @classmethod
    def kill_employee(
        cls,
        tenant_id: str,
        company_id: str,
        employee_id: str,
        reason: str,
    ) -> EmployeeTrustModel:
        """Per-employee kill switch. Suspends employee immediately."""
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE employee_trust_levels
                SET is_killed = 1, is_suspended = 1, current_level = 'SHADOW', updated_at = ?
                WHERE tenant_id = ? AND company_id = ? AND employee_id = ?
                """,
                (now, tenant_id, company_id, employee_id)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="EMPLOYEE_KILLED",
            payload={"employee_id": employee_id, "reason": reason},
            action_id=f"kill_{employee_id}_{int(now)}",
        )

        return cls.get_or_create_trust(tenant_id, company_id, employee_id)
