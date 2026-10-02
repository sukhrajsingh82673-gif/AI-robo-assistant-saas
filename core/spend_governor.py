"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 17 — Enterprise Financial Governance & Spend Governor
Multi-tier budget enforcement (Tenant -> Company -> Department -> Team -> Employee -> Mission -> Action).
Soft limits, hard limits, and emergency financial halts.

Constitutional Invariants:
  BUDGET_EXHAUSTION_HALTS_EXECUTION
  FINANCIAL_ACTIONS_BOUND_BY_CLEARANCE
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType
from core.distributed_coordination import coordination

logger = logging.getLogger("zonata.spend.governor")

class BudgetStatus:
    UNDER_BUDGET = "UNDER_BUDGET"
    SOFT_LIMIT_WARNING = "SOFT_LIMIT_WARNING"
    HARD_LIMIT_EXCEEDED = "HARD_LIMIT_EXCEEDED"
    EMERGENCY_STOP = "EMERGENCY_STOP"

@dataclass
class BudgetConfig:
    entity_id: str
    entity_type: str        # TENANT, COMPANY, DEPARTMENT, TEAM, AI_EMPLOYEE, MISSION
    allocated_usd: float
    soft_limit_pct: float   # e.g. 80.0%
    hard_limit_pct: float   # e.g. 100.0%
    spent_usd: float
    is_frozen: bool

class SpendGovernor:
    """
    Enterprise-wide Multi-Tier Spend Governor.
    Prevents runaway token or compute consumption from draining corporate budgets.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_budgets (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                allocated_usd REAL NOT NULL,
                spent_usd REAL NOT NULL DEFAULT 0.0,
                soft_limit_pct REAL NOT NULL DEFAULT 80.0,
                hard_limit_pct REAL NOT NULL DEFAULT 100.0,
                is_frozen INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bud_tenant ON enterprise_budgets(tenant_id);")

    def configure_budget(
        self,
        entity_id: str,
        entity_type: str,
        tenant_id: str,
        company_id: str,
        allocated_usd: float,
        soft_limit_pct: float = 80.0,
        hard_limit_pct: float = 100.0
    ):
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO enterprise_budgets (
                entity_id, entity_type, tenant_id, company_id, allocated_usd,
                soft_limit_pct, hard_limit_pct, is_frozen, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (entity_id, entity_type, tenant_id, company_id, allocated_usd, soft_limit_pct, hard_limit_pct, now, now))

    def evaluate_spend(self, entity_id: str, requested_spend_usd: float) -> Tuple[str, str]:
        """
        Check if an entity has budget capacity for an operation.
        Returns: (status: BudgetStatus, reason: str)
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM enterprise_budgets WHERE entity_id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                # Default unconfigured budget permits low-cost dev execution
                return BudgetStatus.UNDER_BUDGET, "Uncapped budget default."

        if row["is_frozen"]:
            return BudgetStatus.EMERGENCY_STOP, f"Budget for {entity_id} is frozen under emergency stop."

        current_spent = row["spent_usd"]
        allocated = row["allocated_usd"]
        projected = current_spent + requested_spend_usd

        hard_ceiling = allocated * (row["hard_limit_pct"] / 100.0)
        soft_ceiling = allocated * (row["soft_limit_pct"] / 100.0)

        if projected > hard_ceiling:
            return BudgetStatus.HARD_LIMIT_EXCEEDED, f"Projected spend (${projected:.2f}) exceeds hard budget ceiling (${hard_ceiling:.2f})."

        if projected >= soft_ceiling:
            return BudgetStatus.SOFT_LIMIT_WARNING, f"Projected spend (${projected:.2f}) reached soft limit warning threshold."

        return BudgetStatus.UNDER_BUDGET, "Spend approved within budget."

    def record_spend(self, entity_id: str, actual_spend_usd: float):
        """Atomically record incurred cost and update spent tally."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE enterprise_budgets
            SET spent_usd = spent_usd + ?, updated_at = ?
            WHERE entity_id = ?
            """, (actual_spend_usd, now, entity_id))

    def freeze_budget(self, entity_id: str, reason: str) -> bool:
        """Trigger emergency financial stop."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE enterprise_budgets
            SET is_frozen = 1, updated_at = ?
            WHERE entity_id = ?
            """, (now, entity_id))
        logger.error(f"[EMERGENCY SPEND HALT] Budget for entity {entity_id} frozen: {reason}")
        return True

# Global singleton
spend_governor = SpendGovernor()
