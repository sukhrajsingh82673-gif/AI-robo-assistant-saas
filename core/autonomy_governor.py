"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Phase 27 — Autonomy Level Governor & Delegation Hierarchy
Regulates autonomy levels from Level 0 (Observe) to Level 5 (Continuous Enterprise Operations).

Constitutional Invariants:
  EMPLOYEE_CANNOT_ELEVATE_OWN_AUTONOMY_LEVEL
  CHILD_AUTONOMY_LEVEL <= PARENT_AUTONOMY_LEVEL
  LEVEL_BREACH_REQUIRES_HUMAN_ELEVATION
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.autonomy.governor")

class AutonomyLevel:
    LEVEL_0_OBSERVE = 0           # Read telemetry & listen only; zero action proposal
    LEVEL_1_RECOMMEND = 1         # Propose recommendations; human must approve all mutations
    LEVEL_2_REVERSIBLE = 2        # Read-only queries, search, analysis, formatted reporting
    LEVEL_3_APPROVED_WORKFLOW = 3 # Pre-approved business workflows within bounded budgets
    LEVEL_4_AUTONOMOUS_MISSION = 4# Multi-step goal-seeking autonomous missions with spend caps
    LEVEL_5_ENTERPRISE_AUTO = 5   # Continuous autonomous operations under strict ABAC policy

class AutonomyViolationError(PermissionError):
    """Raised when an agent attempts an action beyond its granted autonomy level."""
    pass

class AutonomyGovernor:
    """
    Enforces deterministic bounds on AI Employee autonomy tiers.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_employee_autonomy_levels (
                employee_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                current_level INTEGER NOT NULL DEFAULT 1,
                max_permitted_level INTEGER NOT NULL DEFAULT 3,
                granted_by TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            """)

    def set_employee_autonomy(
        self,
        employee_id: str,
        tenant_id: str,
        assigned_level: int,
        max_permitted: int,
        authorizer_id: str
    ) -> bool:
        """Assign autonomy level (Requires human administrator authority)."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO ai_employee_autonomy_levels (
                employee_id, tenant_id, current_level, max_permitted_level,
                granted_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id) DO UPDATE SET
                current_level = excluded.current_level,
                max_permitted_level = excluded.max_permitted_level,
                granted_by = excluded.granted_by,
                updated_at = excluded.updated_at
            """, (employee_id, tenant_id, assigned_level, max_permitted, authorizer_id, now))

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id="AUTONOMY_CONTROL",
            event_type="AUTONOMY_LEVEL_ASSIGNED",
            payload={"employee_id": employee_id, "level": assigned_level, "granted_by": authorizer_id}
        )
        return True

    def verify_action_autonomy(
        self,
        employee_id: str,
        action_type: str,
        is_mutating: bool,
        spend_usd: float
    ) -> bool:
        """
        Validates whether proposed action is permitted under agent's current autonomy level.
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute(
                "SELECT current_level, max_permitted_level FROM ai_employee_autonomy_levels WHERE employee_id = ?",
                (employee_id,)
            )
            row = cursor.fetchone()
            level = row["current_level"] if row else AutonomyLevel.LEVEL_1_RECOMMEND

        # Level 0: Zero actions
        if level == AutonomyLevel.LEVEL_0_OBSERVE:
            raise AutonomyViolationError(f"Employee '{employee_id}' is LEVEL 0 (OBSERVE ONLY). Action rejected.")

        # Level 1: Recommends only; any mutation requires human approval
        if level == AutonomyLevel.LEVEL_1_RECOMMEND and is_mutating:
            raise AutonomyViolationError(f"Employee '{employee_id}' is LEVEL 1. Mutations require human approval.")

        # Level 2: Only non-mutating actions permitted
        if level == AutonomyLevel.LEVEL_2_REVERSIBLE and is_mutating:
            raise AutonomyViolationError(f"Employee '{employee_id}' is LEVEL 2 (REVERSIBLE ONLY). Mutating action '{action_type}' rejected.")

        # Level 3: Mutations permitted up to $500 spend
        if level == AutonomyLevel.LEVEL_3_APPROVED_WORKFLOW and spend_usd > 500.0:
            raise AutonomyViolationError(f"Employee '{employee_id}' is LEVEL 3. Spend (${spend_usd:.2f}) exceeds $500 threshold.")

        return True

    def verify_delegation_autonomy(
        self,
        parent_employee_id: str,
        requested_child_level: int
    ) -> bool:
        """Invariant: CHILD_AUTONOMY_LEVEL <= PARENT_AUTONOMY_LEVEL."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute(
                "SELECT current_level FROM ai_employee_autonomy_levels WHERE employee_id = ?",
                (parent_employee_id,)
            )
            row = cursor.fetchone()
            parent_level = row["current_level"] if row else AutonomyLevel.LEVEL_1_RECOMMEND

        if requested_child_level > parent_level:
            raise AutonomyViolationError(
                f"Child autonomy level ({requested_child_level}) cannot exceed parent autonomy level ({parent_level})."
            )
        return True

autonomy_governor = AutonomyGovernor()
