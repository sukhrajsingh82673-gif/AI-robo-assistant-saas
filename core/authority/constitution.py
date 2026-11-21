"""
Company Constitution Link and Statutory Prohibitions (OpenCode Step 2C)
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from core.db import db
from core.authority.types import PrincipalType, Rule15Violation, GOVERNED_PRINCIPAL_TYPES

logger = logging.getLogger("zonata.authority.constitution")


class ConstitutionManager:
    """Manages versioned corporate constitutions and evaluates constitutional prohibitions."""

    def __init__(self):
        pass

    def get_constitution(self, tenant_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves active company constitution."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT constitution_id, version, mission, objectives, reserved_decisions,
                       prohibited_actions, spend_ceilings, autonomy_ceiling, approved_by
                FROM company_constitutions
                WHERE tenant_id = ? AND company_id = ? AND is_active = 1
                ORDER BY version DESC LIMIT 1
                """,
                (tenant_id, company_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "constitution_id": row[0],
                "version": row[1],
                "mission": row[2],
                "objectives": json.loads(row[3]) if row[3] else [],
                "reserved_decisions": json.loads(row[4]) if row[4] else [],
                "prohibited_actions": json.loads(row[5]) if row[5] else [],
                "spend_ceilings": json.loads(row[6]) if row[6] else {},
                "autonomy_ceiling": row[7],
                "approved_by": row[8],
            }

    def set_constitution(
        self,
        tenant_id: str,
        company_id: str,
        mission: str,
        prohibited_actions: List[str],
        reserved_decisions: Optional[List[str]] = None,
        spend_ceilings: Optional[Dict[str, Any]] = None,
        autonomy_ceiling: str = "SUPERVISED",
        approved_by: str = "HUMAN_OWNER",
        caller_principal_type: str = PrincipalType.OWNER.value,
    ) -> Dict[str, Any]:
        """Sets or amends company constitution. Enforces Rule 15: only OWNER or BOARD can write."""
        if caller_principal_type in [p.value for p in GOVERNED_PRINCIPAL_TYPES] or caller_principal_type not in (
            PrincipalType.OWNER.value,
            PrincipalType.BOARD.value,
            PrincipalType.HUMAN.value,
        ):
            msg = f"Rule 15 Violation: Principal type '{caller_principal_type}' is prohibited from writing company constitution. Only OWNER or BOARD permitted."
            logger.error(msg)
            raise Rule15Violation(msg)

        now = time.time()
        constitution_id = f"const_{company_id}"

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) FROM company_constitutions WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            )
            ver = cur.fetchone()[0] + 1

            # Deactivate previous
            cur.execute(
                "UPDATE company_constitutions SET is_active = 0 WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            )

            cur.execute(
                """
                INSERT INTO company_constitutions (
                    constitution_id, tenant_id, company_id, version, mission, objectives,
                    reserved_decisions, prohibited_actions, spend_ceilings, autonomy_ceiling,
                    is_active, approved_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    f"{constitution_id}_v{ver}", tenant_id, company_id, ver, mission, "[]",
                    json.dumps(reserved_decisions or []), json.dumps(prohibited_actions),
                    json.dumps(spend_ceilings or {}), autonomy_ceiling,
                    approved_by, now, now
                ),
            )
            conn.commit()

        return {
            "constitution_id": f"{constitution_id}_v{ver}",
            "version": ver,
            "mission": mission,
            "prohibited_actions": prohibited_actions,
            "reserved_decisions": reserved_decisions or [],
            "spend_ceilings": spend_ceilings or {},
            "autonomy_ceiling": autonomy_ceiling,
        }

    def evaluate_action_against_constitution(
        self,
        tenant_id: str,
        company_id: str,
        action_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Checks if an action violates constitutional prohibitions. Returns reason if prohibited, else None."""
        const = self.get_constitution(tenant_id, company_id)
        if not const:
            return None

        prohibited = const.get("prohibited_actions", [])
        act_clean = action_name.upper().strip()
        for p in prohibited:
            if p.upper().strip() == act_clean or p.upper().strip() in act_clean:
                return f"Action '{action_name}' is explicitly prohibited by company constitution ({p})"

        return None


constitution_manager = ConstitutionManager()
