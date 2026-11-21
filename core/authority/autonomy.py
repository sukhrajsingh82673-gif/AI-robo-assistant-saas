"""
Autonomy Ceiling and Conservative Defaults (Rule 19, OpenCode Step 2C)
"""

import json
import logging
from typing import Optional

from core.db import db
from core.authority.types import AutonomyLevel, AUTONOMY_RANK

logger = logging.getLogger("zonata.authority.autonomy")


def compute_effective_autonomy(
    tenant_id: str,
    company_id: str,
    employee_id: Optional[str] = None,
    owner_setting: AutonomyLevel = AutonomyLevel.AUTONOMOUS,
    capability_live: bool = True,
) -> AutonomyLevel:
    """
    Computes effective autonomy ceiling as the strict minimum of:
    1. The owner's setting
    2. The industry pack's review cap (SKELETON/DRAFT packs cap at SUPERVISED)
    3. The employee's trust level (defaults to SHADOW for new employees)
    4. What the capability truth table says is live
    """
    caps = [owner_setting]

    # 1. Capability truth table cap
    if not capability_live:
        caps.append(AutonomyLevel.SHADOW)

    # 2. Industry pack review cap check
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT raw_manifest FROM installed_industry_packs
            WHERE tenant_id = ? AND company_id = ?
            ORDER BY installed_at DESC LIMIT 1
            """,
            (tenant_id, company_id),
        )
        row = cur.fetchone()
        if row:
            try:
                manifest = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                meta = manifest.get("metadata", {})
                status = meta.get("review_status") or meta.get("status") or ""
                status_upper = str(status).upper()
                if status_upper in ("DRAFT", "SKELETON", "REVIEW_REQUIRED"):
                    logger.info(f"Industry pack review cap active ({status_upper}) for company {company_id}: capping autonomy at SUPERVISED")
                    caps.append(AutonomyLevel.SUPERVISED)
            except Exception:
                pass

        # Check company status table
        cur.execute(
            "SELECT status, operating_rules FROM companies WHERE company_id = ? AND tenant_id = ?",
            (company_id, tenant_id),
        )
        comp_row = cur.fetchone()
        if comp_row:
            comp_status = str(comp_row[0]).upper()
            if comp_status in ("DRAFT", "ONBOARDING"):
                caps.append(AutonomyLevel.SUPERVISED)

            # Check operating rules for autonomy setting
            if comp_row[1]:
                try:
                    op_rules = json.loads(comp_row[1]) if isinstance(comp_row[1], str) else comp_row[1]
                    configured_level = op_rules.get("autonomy_level")
                    if configured_level and configured_level in [lvl.value for lvl in AutonomyLevel]:
                        caps.append(AutonomyLevel(configured_level))
                except Exception:
                    pass

    # 3. Employee trust level check
    if employee_id:
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT trust_level FROM ai_employees
                    WHERE employee_id = ? AND tenant_id = ?
                    """,
                    (employee_id, tenant_id),
                )
                emp_row = cur.fetchone()
                if emp_row and emp_row[0]:
                    trust_str = str(emp_row[0]).upper()
                    if trust_str in [lvl.value for lvl in AutonomyLevel]:
                        caps.append(AutonomyLevel(trust_str))
                    else:
                        caps.append(AutonomyLevel.SHADOW)
                else:
                    caps.append(AutonomyLevel.SHADOW)
        except Exception:
            # If trust_level column not present, default to SHADOW for uncertified agents
            caps.append(AutonomyLevel.SHADOW)

    # Return minimum rank
    min_level = min(caps, key=lambda lvl: AUTONOMY_RANK[lvl])
    return min_level
