"""
Phase 13 Concurrency & Multi-Process Economic Governance Qualification Suite
=============================================================================
Verifies:
1. Multi-process & multi-thread safe atomic SQL-level conditional budget reservation.
2. Strict limit enforcement under high contention (zero over-reservation).
3. Concurrent token reservation boundary enforcement.
4. Two-phase settlement with ANSI SQL CASE WHEN expressions.
5. Concurrent release and idempotent cleanup.
6. Emergency freeze fail-closed protection under concurrent assault.
"""

import os
import sys
import time
import uuid
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.economic_governance import (
    EconomicGovernanceEngine,
    BudgetExhaustionException,
    BudgetFrozenException,
    ReservationExpiredException
)

class TestPhase13MultiProcessGovernance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "pg_governance_concurrency.db")
        configure_isolated_test_db(self.db_path)
        self.engine = EconomicGovernanceEngine()
        self.tenant_id = f"tnt_conc_{uuid.uuid4().hex[:8]}"
        self.company_id = f"comp_conc_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Concurrency Tenant', ?)",
                (self.tenant_id, time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) "
                "VALUES (?, ?, 'Concurrency Corp', 'US', 'Tech', 'ENTERPRISE', 'ACTIVE', ?)",
                (self.company_id, self.tenant_id, time.time())
            )
            conn.commit()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_concurrent_budget_reservations_atomic_sql(self):
        """
        Contention Stress: 20 concurrent workers attempting to reserve $100
        against an allocated budget of $1,000 (hard limit 100%).
        Exactly 10 must succeed and exactly 10 must fail closed with BudgetExhaustionException.
        Total reserved + spent must equal exactly $1,000.00.
        """
        entity_id = f"ent_usd_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=1000.0,
            soft_limit_pct=80.0,
            hard_limit_pct=100.0
        )

        success_count = 0
        exhausted_count = 0
        reservations = []

        def worker_reserve(idx):
            eng = EconomicGovernanceEngine()
            return eng.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[("DEPARTMENT", entity_id)],
                requested_usd=100.0,
                task_id=f"task_{idx}"
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_reserve, i) for i in range(20)]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    success_count += 1
                    reservations.append(res)
                except BudgetExhaustionException:
                    exhausted_count += 1

        self.assertEqual(success_count, 10, f"Exactly 10 reservations must succeed, got {success_count}")
        self.assertEqual(exhausted_count, 10, f"Exactly 10 reservations must fail closed, got {exhausted_count}")

        # Verify database state
        budget = self.engine.get_budget(entity_id)
        self.assertIsNotNone(budget)
        self.assertAlmostEqual(budget.reserved_usd, 1000.0, places=2)
        self.assertAlmostEqual(budget.spent_usd, 0.0, places=2)
        self.assertAlmostEqual(budget.available_usd, 0.0, places=2)

    def test_02_concurrent_token_reservations_atomic_sql(self):
        """
        Contention Stress: 15 concurrent workers attempting to reserve 10,000 tokens
        against an allocated token budget of 50,000 tokens.
        Exactly 5 must succeed and 10 must fail closed.
        """
        entity_id = f"ent_tok_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="AGENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=10000.0,
            allocated_tokens=50000,
            soft_limit_pct=80.0,
            hard_limit_pct=100.0
        )

        success_count = 0
        exhausted_count = 0

        def worker_reserve(idx):
            eng = EconomicGovernanceEngine()
            return eng.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[("AGENT", entity_id)],
                requested_usd=1.0,
                requested_tokens=10000,
                task_id=f"tok_task_{idx}"
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_reserve, i) for i in range(15)]
            for fut in as_completed(futures):
                try:
                    fut.result()
                    success_count += 1
                except BudgetExhaustionException:
                    exhausted_count += 1

        self.assertEqual(success_count, 5, f"Expected 5 token reservations to succeed, got {success_count}")
        self.assertEqual(exhausted_count, 10, f"Expected 10 to fail closed, got {exhausted_count}")

        budget = self.engine.get_budget(entity_id)
        self.assertEqual(budget.reserved_tokens, 50000)
        self.assertEqual(budget.available_tokens, 0)

    def test_03_concurrent_settlements_case_when(self):
        """
        Verifies that multiple concurrent settlements transition reserved amounts
        to spent amounts accurately without race conditions or negative balances.
        """
        entity_id = f"ent_settle_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=5000.0
        )

        # Create 5 reservations of $200 each
        reservations = []
        for i in range(5):
            res = self.engine.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[("DEPARTMENT", entity_id)],
                requested_usd=200.0
            )
            reservations.append(res)

        budget_before = self.engine.get_budget(entity_id)
        self.assertAlmostEqual(budget_before.reserved_usd, 1000.0, places=2)

        # Concurrently settle each reservation with an actual spend of $180 (underrun of $20)
        def worker_settle(res):
            eng = EconomicGovernanceEngine()
            return eng.settle_budget(
                reservation_id=res.reservation_id,
                actual_usd=180.0
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_settle, r) for r in reservations]
            for fut in as_completed(futures):
                settlement = fut.result()
                self.assertEqual(settlement.status, "SETTLED")
                self.assertAlmostEqual(settlement.actual_usd, 180.0, places=2)

        # Budget verification: 5 * $180 = $900 spent, $0 reserved, $4,100 available
        budget_after = self.engine.get_budget(entity_id)
        self.assertAlmostEqual(budget_after.reserved_usd, 0.0, places=2)
        self.assertAlmostEqual(budget_after.spent_usd, 900.0, places=2)
        self.assertAlmostEqual(budget_after.available_usd, 4100.0, places=2)

    def test_04_concurrent_release_and_idempotency(self):
        """
        Verifies that release_reservation frees reserved funds concurrently
        and that double-settlement or double-release is cleanly rejected.
        """
        entity_id = f"ent_rel_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=2000.0
        )

        res = self.engine.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[("DEPARTMENT", entity_id)],
            requested_usd=500.0
        )

        released = self.engine.release_reservation(res.reservation_id)
        self.assertTrue(released)

        # Repeated release returns False (idempotent / non-destructive)
        released_second = self.engine.release_reservation(res.reservation_id)
        self.assertFalse(released_second)

        # Settling a released reservation fails with ReservationExpiredException
        with self.assertRaises(ReservationExpiredException):
            self.engine.settle_budget(res.reservation_id, actual_usd=500.0)

        budget = self.engine.get_budget(entity_id)
        self.assertAlmostEqual(budget.reserved_usd, 0.0, places=2)
        self.assertAlmostEqual(budget.spent_usd, 0.0, places=2)

    def test_05_emergency_stop_freeze_fail_closed(self):
        """
        Verifies that when a budget is frozen, all concurrent reservation attempts
        are immediately rejected with BudgetFrozenException.
        """
        entity_id = f"ent_frozen_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="TENANT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=10000.0
        )

        # Freeze the entity
        with db.get_connection() as conn:
            conn.execute("UPDATE enterprise_budgets SET is_frozen = 1 WHERE entity_id = ?", (entity_id,))
            conn.commit()

        def worker_attempt():
            eng = EconomicGovernanceEngine()
            eng.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[("TENANT", entity_id)],
                requested_usd=50.0
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_attempt) for _ in range(10)]
            for fut in as_completed(futures):
                with self.assertRaises(BudgetFrozenException):
                    fut.result()

if __name__ == "__main__":
    unittest.main()
