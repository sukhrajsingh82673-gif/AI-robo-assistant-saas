"""
Authority Profiles (G1 to G9) and Rule 15 Principal Separation (OpenCode Step 2C)
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from core.db import db
from core.authority.types import ActionClass, PrincipalType, Rule15Violation, GOVERNED_PRINCIPAL_TYPES
from core.workforce_architecture import GRADE_AUTHORITY, TIER_RANK

logger = logging.getLogger("zonata.authority.profiles")


class AuthorityProfileManager:
    """Manages and enforces corporate authority profiles across G1 to G9 tiers."""

    def __init__(self):
        pass

    def get_profile(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolves authority profile from authority_profiles table, or falls back to standard GRADE_AUTHORITY."""
        # 1. Check database for customized profile
        if principal_id:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT profile_id, grade, tier, single_spend_limit_usd, monthly_spend_limit_usd,
                           can_hire, can_delegate, can_modify_sops, allowed_action_classes
                    FROM authority_profiles
                    WHERE tenant_id = ? AND company_id = ? AND principal_id = ?
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (tenant_id, company_id, principal_id),
                )
                row = cur.fetchone()
                if row:
                    allowed_actions = json.loads(row[8]) if row[8] else None
                    return {
                        "profile_id": row[0],
                        "grade": row[1],
                        "tier": row[2],
                        "single": row[3],
                        "monthly": row[4],
                        "can_hire": bool(row[5]),
                        "can_delegate": bool(row[6]),
                        "can_modify_sops": bool(row[7]),
                        "allowed_action_classes": allowed_actions,
                    }

        # 2. Fall back to standard G1-G9 catalog from code
        effective_grade = grade or "G9"
        std = GRADE_AUTHORITY.get(effective_grade, GRADE_AUTHORITY["G9"])
        return {
            "profile_id": f"std_{effective_grade.lower()}",
            "grade": effective_grade,
            "tier": std["tier"],
            "single": std["single"],
            "monthly": std["monthly"],
            "can_hire": std["can_hire"],
            "can_delegate": std["can_delegate"],
            "can_modify_sops": std["can_modify_sops"],
            "allowed_action_classes": None,
        }

    def set_profile(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        grade: str,
        single_spend_limit_usd: Optional[int] = None,
        monthly_spend_limit_usd: Optional[int] = None,
        can_hire: Optional[bool] = None,
        can_delegate: Optional[bool] = None,
        can_modify_sops: Optional[bool] = None,
        caller_principal_type: str = PrincipalType.HUMAN.value,
    ) -> Dict[str, Any]:
        """Sets or updates an authority profile. Enforces Rule 15 principal separation."""
        if caller_principal_type in [p.value for p in GOVERNED_PRINCIPAL_TYPES]:
            msg = f"Rule 15 Violation: Principal type '{caller_principal_type}' is prohibited from writing authority profiles."
            logger.error(msg)
            raise Rule15Violation(msg)

        std = GRADE_AUTHORITY.get(grade, GRADE_AUTHORITY["G9"])
        single = single_spend_limit_usd if single_spend_limit_usd is not None else std["single"]
        monthly = monthly_spend_limit_usd if monthly_spend_limit_usd is not None else std["monthly"]
        hire = can_hire if can_hire is not None else std["can_hire"]
        delegate = can_delegate if can_delegate is not None else std["can_delegate"]
        modify_sops = can_modify_sops if can_modify_sops is not None else std["can_modify_sops"]

        now = time.time()
        profile_id = f"prof_{principal_id}"

        with db.get_connection() as conn:
            cur = conn.cursor()
            if db.is_postgresql():
                cur.execute(
                    """
                    INSERT INTO authority_profiles (
                        profile_id, tenant_id, company_id, principal_id, grade, tier,
                        single_spend_limit_usd, monthly_spend_limit_usd, can_hire, can_delegate,
                        can_modify_sops, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (profile_id) DO UPDATE SET
                        grade = EXCLUDED.grade,
                        tier = EXCLUDED.tier,
                        single_spend_limit_usd = EXCLUDED.single_spend_limit_usd,
                        monthly_spend_limit_usd = EXCLUDED.monthly_spend_limit_usd,
                        can_hire = EXCLUDED.can_hire,
                        can_delegate = EXCLUDED.can_delegate,
                        can_modify_sops = EXCLUDED.can_modify_sops,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        profile_id, tenant_id, company_id, principal_id, grade, std["tier"],
                        single, monthly, int(hire), int(delegate), int(modify_sops), now, now
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO authority_profiles (
                        profile_id, tenant_id, company_id, principal_id, grade, tier,
                        single_spend_limit_usd, monthly_spend_limit_usd, can_hire, can_delegate,
                        can_modify_sops, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile_id, tenant_id, company_id, principal_id, grade, std["tier"],
                        single, monthly, int(hire), int(delegate), int(modify_sops), now, now
                    ),
                )
            conn.commit()

        return {
            "profile_id": profile_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "principal_id": principal_id,
            "grade": grade,
            "tier": std["tier"],
            "single": single,
            "monthly": monthly,
            "can_hire": hire,
            "can_delegate": delegate,
            "can_modify_sops": modify_sops,
        }


authority_profile_manager = AuthorityProfileManager()
