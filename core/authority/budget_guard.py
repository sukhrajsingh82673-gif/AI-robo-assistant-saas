"""
Thread-Safe Spend Budget Guard (OpenCode Step 2C, Rule 20)
Atomic reserve-then-settle spend management with concurrency serialization.
"""

import threading
import logging
import time
from typing import Dict, Any, Optional

from core.db import db

logger = logging.getLogger("zonata.authority.budget_guard")


class SpendBudgetGuard:
    """Manages spend budget reservations with strict concurrency locking and zero float arithmetic."""

    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_table()

    def _ensure_table(self, conn=None):
        sql = """
            CREATE TABLE IF NOT EXISTS company_spend_budgets (
                budget_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                category TEXT NOT NULL,
                allocated_minor_units INTEGER NOT NULL,
                spent_minor_units INTEGER NOT NULL DEFAULT 0,
                reserved_minor_units INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE(tenant_id, company_id, category)
            )
        """
        if conn is not None:
            if db.pg_tables_ready(conn, "company_spend_budgets"):
                return
            cur = conn.cursor()
            cur.execute(sql)
            if hasattr(conn, "commit"):
                try:
                    conn.commit()
                except Exception:
                    pass
            return

        with db.get_connection() as c:
            if db.pg_tables_ready(c, "company_spend_budgets"):
                return
            cur = c.cursor()
            cur.execute(sql)
            c.commit()

    def set_budget(
        self,
        tenant_id: str,
        company_id: str,
        category: str,
        allocated_minor_units: int,
    ) -> Dict[str, Any]:
        """Sets or initializes a category spend budget in integer minor units."""
        now = time.time()
        budget_id = f"bg_{company_id}_{category}"
        with self._lock:
            with db.get_connection() as conn:
                self._ensure_table(conn)
                cur = conn.cursor()
                if db.is_postgresql():
                    cur.execute(
                        """
                        INSERT INTO company_spend_budgets (
                            budget_id, tenant_id, company_id, category, allocated_minor_units,
                            spent_minor_units, reserved_minor_units, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
                        ON CONFLICT (tenant_id, company_id, category) DO UPDATE SET
                            allocated_minor_units = EXCLUDED.allocated_minor_units,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (budget_id, tenant_id, company_id, category, allocated_minor_units, now, now),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO company_spend_budgets (
                            budget_id, tenant_id, company_id, category, allocated_minor_units,
                            spent_minor_units, reserved_minor_units, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
                        ON CONFLICT(budget_id) DO UPDATE SET
                            allocated_minor_units = EXCLUDED.allocated_minor_units,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (budget_id, tenant_id, company_id, category, allocated_minor_units, now, now),
                    )
                conn.commit()

        return {
            "budget_id": budget_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "category": category,
            "allocated_minor_units": allocated_minor_units,
        }

    def reserve_and_spend(
        self,
        tenant_id: str,
        company_id: str,
        category: str,
        amount_minor_units: int,
    ) -> bool:
        """
        Atomically reserves and commits spend.
        Guarantees that two concurrent spends at the edge let exactly one pass.
        Returns True if successful, False if budget exhausted.
        """
        if amount_minor_units <= 0:
            return True

        with self._lock:
            with db.get_connection() as conn:
                self._ensure_table(conn)
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT allocated_minor_units, spent_minor_units, reserved_minor_units
                    FROM company_spend_budgets
                    WHERE tenant_id = ? AND company_id = ? AND category = ?
                    """,
                    (tenant_id, company_id, category),
                )
                row = cur.fetchone()
                if not row:
                    # No budget set for this category -> unbudgeted is blocked
                    return False

                allocated, spent, reserved = row
                available = allocated - (spent + reserved)
                if available < amount_minor_units:
                    return False

                now = time.time()
                cur.execute(
                    """
                    UPDATE company_spend_budgets
                    SET spent_minor_units = spent_minor_units + ?, updated_at = ?
                    WHERE tenant_id = ? AND company_id = ? AND category = ?
                      AND (allocated_minor_units - spent_minor_units - reserved_minor_units) >= ?
                    """,
                    (amount_minor_units, now, tenant_id, company_id, category, amount_minor_units),
                )
                conn.commit()
                return cur.rowcount > 0


spend_budget_guard = SpendBudgetGuard()
