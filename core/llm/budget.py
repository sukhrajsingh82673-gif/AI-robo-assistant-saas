"""
ZONATA Universal AI Operating System — Hierarchical LLM Budget Engine
Enforces Rule 20: Pre-execution reserve-then-settle budgeting in integer micro-USD.
Hierarchy: TENANT -> COMPANY -> DEPARTMENT -> POSITION/EMPLOYEE -> MISSION -> TASK.
"""

import time
import uuid
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from core.db import db, tenant_scoped, tenant_scope


class BudgetExhaustionError(PermissionError):
    """Raised when an entity's remaining allocation is insufficient to reserve max cost."""
    def __init__(self, entity_type: str, entity_id: str, allocated: int, remaining: int, requested: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.allocated_micro_usd = allocated
        self.remaining_micro_usd = remaining
        self.requested_micro_usd = requested
        super().__init__(
            f"LLM Budget Exhausted for {entity_type} '{entity_id}': "
            f"Requested {requested} micro-USD, but remaining allocation is {remaining} micro-USD "
            f"(Allocated: {allocated} micro-USD)."
        )


@dataclass
class BudgetReservation:
    reservation_id: str
    tenant_id: str
    company_id: str
    entity_chain: List[Tuple[str, str]]  # List of (entity_type, entity_id)
    reserved_micro_usd: int
    mission_id: Optional[str] = None
    task_id: Optional[str] = None


class LLMBudgetManager:
    """Enterprise Hierarchical Budget Manager.
    
    Prevents overspend under concurrency via row-level locks and transactional reserve-then-settle.
    All monetary units are integer micro-USD (1 USD = 1,000,000 micro-USD).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure common DDL tables exist for budget management."""
        try:
            from core.llm import ensure_model_gateway_tables
            ensure_model_gateway_tables()
        except Exception:
            pass

    @tenant_scoped
    def set_budget(
        self,
        tenant_id: str,
        company_id: str,
        entity_type: str,
        entity_id: str,
        allocated_micro_usd: int,
        period_start: Optional[float] = None,
        period_end: Optional[float] = None,
        caller_principal_type: str = "HUMAN",
    ) -> str:
        """Create or update an entity's budget allocation in integer micro-USD. Enforces Rule 15."""
        if caller_principal_type in ("AGENT", "AI_EMPLOYEE", "MODEL", "SYSTEM_AGENT") or caller_principal_type.startswith(("agt_", "ai_emp_")):
            raise PermissionError(f"Rule 15 Violation: Principal '{caller_principal_type}' cannot allocate budgets")

        now = time.time()
        start = period_start or now - 3600.0
        end = period_end or now + (86400.0 * 30.0)
        budget_id = f"bg_{uuid.uuid4().hex[:12]}"

        with self._lock, db.get_connection() as conn:
            cur = conn.cursor()
            is_pg = (getattr(db, "dialect", "") == "postgresql" or getattr(db, "get_dialect", lambda: "")() == "postgresql")
            if is_pg:
                cur.execute("""
                INSERT INTO llm_budget_hierarchies (
                    budget_id, tenant_id, company_id, entity_type, entity_id,
                    period_start, period_end, allocated_micro_usd, reserved_micro_usd,
                    spent_micro_usd, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                ON CONFLICT (tenant_id, company_id, entity_type, entity_id, period_start)
                DO UPDATE SET allocated_micro_usd = EXCLUDED.allocated_micro_usd
                """, (
                    budget_id, tenant_id, company_id, entity_type.upper(), entity_id,
                    start, end, allocated_micro_usd, now
                ))
            else:
                cur.execute("""
                INSERT INTO llm_budget_hierarchies (
                    budget_id, tenant_id, company_id, entity_type, entity_id,
                    period_start, period_end, allocated_micro_usd, reserved_micro_usd,
                    spent_micro_usd, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                ON CONFLICT (tenant_id, company_id, entity_type, entity_id, period_start)
                DO UPDATE SET allocated_micro_usd = EXCLUDED.allocated_micro_usd
                """, (
                    budget_id, tenant_id, company_id, entity_type.upper(), entity_id,
                    start, end, allocated_micro_usd, now
                ))
            conn.commit()
        return budget_id

    @tenant_scoped
    def get_remaining_micro_usd(
        self,
        tenant_id: str,
        company_id: str,
        entity_type: str,
        entity_id: str,
        now: Optional[float] = None
    ) -> Optional[int]:
        """Return the available spend allocation (allocated - reserved - spent) or None if unbudgeted."""
        ts = now or time.time()
        with self._lock, db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT allocated_micro_usd, reserved_micro_usd, spent_micro_usd
            FROM llm_budget_hierarchies
            WHERE tenant_id = ? AND company_id = ? AND entity_type = ? AND entity_id = ?
              AND period_start <= ? AND period_end >= ?
            LIMIT 1
            """, (tenant_id, company_id, entity_type.upper(), entity_id, ts, ts))
            row = cur.fetchone()
            if not row:
                return None
            allocated, reserved, spent = row[0], row[1], row[2]
            return max(0, allocated - (reserved + spent))

    @tenant_scoped
    def reserve(
        self,
        tenant_id: str,
        company_id: str,
        entity_chain: List[Tuple[str, str]],
        max_cost_micro_usd: int,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        now: Optional[float] = None
    ) -> str:
        """Reserve max cost atomically across all levels in entity chain inside a transaction.
        
        Uses row-level locking (FOR UPDATE in PostgreSQL) to prevent race conditions.
        Fails fast if any level in the hierarchy has insufficient available budget.
        """
        if max_cost_micro_usd <= 0:
            return f"res_free_{uuid.uuid4().hex[:8]}"

        ts = now or time.time()
        reservation_id = f"res_{uuid.uuid4().hex[:12]}"

        with self._lock, db.get_connection() as conn:
            cur = conn.cursor()
            is_pg = (getattr(db, "dialect", "") == "postgresql" or getattr(db, "get_dialect", lambda: "")() == "postgresql")

            # 1. Inspect and lock each level in the hierarchy
            locked_budget_ids = []
            for etype, eid in entity_chain:
                etype_upper = etype.upper()
                lock_clause = "FOR UPDATE" if is_pg else ""
                cur.execute(f"""
                SELECT budget_id, allocated_micro_usd, reserved_micro_usd, spent_micro_usd
                FROM llm_budget_hierarchies
                WHERE tenant_id = ? AND company_id = ? AND entity_type = ? AND entity_id = ?
                  AND period_start <= ? AND period_end >= ?
                LIMIT 1 {lock_clause}
                """, (tenant_id, company_id, etype_upper, eid, ts, ts))
                row = cur.fetchone()
                if row:
                    b_id, allocated, reserved, spent = row[0], row[1], row[2], row[3]
                    remaining = allocated - (reserved + spent)
                    if remaining < max_cost_micro_usd:
                        raise BudgetExhaustionError(
                            entity_type=etype_upper,
                            entity_id=eid,
                            allocated=allocated,
                            remaining=remaining,
                            requested=max_cost_micro_usd
                        )
                    locked_budget_ids.append((b_id, etype_upper, eid))

            # 2. If all levels have sufficient budget, increment reserved_micro_usd
            for b_id, etype_upper, eid in locked_budget_ids:
                cur.execute("""
                UPDATE llm_budget_hierarchies
                SET reserved_micro_usd = reserved_micro_usd + ?
                WHERE budget_id = ?
                """, (max_cost_micro_usd, b_id))

            # 3. Create reservation records
            primary_type, primary_id = entity_chain[-1] if entity_chain else ("TENANT", tenant_id)
            cur.execute("""
            INSERT INTO llm_budget_reservations (
                reservation_id, tenant_id, company_id, entity_type, entity_id,
                mission_id, task_id, reserved_micro_usd, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, (
                reservation_id, tenant_id, company_id, primary_type.upper(), primary_id,
                mission_id, task_id, max_cost_micro_usd, ts
            ))
            conn.commit()

        return reservation_id

    @tenant_scoped
    def settle(
        self,
        reservation_id: str,
        actual_cost_micro_usd: int,
        entity_chain: Optional[List[Tuple[str, str]]] = None,
        now: Optional[float] = None,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Settle a pending reservation: convert reserved to spent and release unused headroom."""
        if reservation_id.startswith("res_free_"):
            return {"status": "SETTLED", "actual_cost_micro_usd": 0}

        ts = now or time.time()

        with self._lock, db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT tenant_id, company_id, entity_type, entity_id, reserved_micro_usd, status
            FROM llm_budget_reservations
            WHERE reservation_id = ?
            LIMIT 1
            """, (reservation_id,))
            res_row = cur.fetchone()
            if not res_row:
                return {"status": "UNKNOWN_RESERVATION", "actual_cost_micro_usd": actual_cost_micro_usd}

            tenant_id, company_id, etype, eid, reserved_amount, status = res_row
            if status != "PENDING":
                return {"status": status, "actual_cost_micro_usd": actual_cost_micro_usd}

            # Update hierarchy entities
            chain = entity_chain or [(etype, eid)]
            for c_type, c_id in chain:
                cur.execute("""
                UPDATE llm_budget_hierarchies
                SET reserved_micro_usd = MAX(0, reserved_micro_usd - ?),
                    spent_micro_usd = spent_micro_usd + ?
                WHERE tenant_id = ? AND company_id = ? AND entity_type = ? AND entity_id = ?
                """, (reserved_amount, actual_cost_micro_usd, tenant_id, company_id, c_type.upper(), c_id))

            # Mark reservation settled
            cur.execute("""
            UPDATE llm_budget_reservations
            SET status = 'SETTLED', settled_at = ?
            WHERE reservation_id = ?
            """, (ts, reservation_id))
            conn.commit()

        return {
            "status": "SETTLED",
            "reservation_id": reservation_id,
            "reserved_micro_usd": reserved_amount,
            "actual_cost_micro_usd": actual_cost_micro_usd,
            "released_micro_usd": max(0, reserved_amount - actual_cost_micro_usd)
        }

    @tenant_scoped
    def release(
        self,
        reservation_id: str,
        entity_chain: Optional[List[Tuple[str, str]]] = None,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> None:
        """Release an unused reservation completely back to available spend."""
        if reservation_id.startswith("res_free_"):
            return

        with self._lock, db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT tenant_id, company_id, entity_type, entity_id, reserved_micro_usd, status
            FROM llm_budget_reservations
            WHERE reservation_id = ?
            LIMIT 1
            """, (reservation_id,))
            res_row = cur.fetchone()
            if not res_row or res_row[5] != "PENDING":
                return

            tenant_id, company_id, etype, eid, reserved_amount, _ = res_row
            chain = entity_chain or [(etype, eid)]
            for c_type, c_id in chain:
                cur.execute("""
                UPDATE llm_budget_hierarchies
                SET reserved_micro_usd = MAX(0, reserved_micro_usd - ?)
                WHERE tenant_id = ? AND company_id = ? AND entity_type = ? AND entity_id = ?
                """, (reserved_amount, tenant_id, company_id, c_type.upper(), c_id))

            cur.execute("""
            UPDATE llm_budget_reservations
            SET status = 'RELEASED', settled_at = ?
            WHERE reservation_id = ?
            """, (time.time(), reservation_id))
            conn.commit()


# Global Singleton
llm_budget_manager = LLMBudgetManager()
