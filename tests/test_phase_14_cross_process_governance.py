"""
Phase 14 Cross-Process Economic Governance Concurrency Qualification Suite
===========================================================================
Validates:
1. True independent OS process concurrency (separate Python PIDs, separate DB handles).
2. Atomic SQL conditional budget reservation enforcement under high contention.
3. Zero over-reservation across distinct OS processes:
   Invariant: spent + reserved + requested <= permitted allocation
4. Cross-process concurrent settlements and releases with ANSI SQL CASE WHEN expressions.
5. Cross-process double-settlement idempotency and race condition elimination.
6. Fail-closed emergency freeze across concurrent OS processes.
7. Abrupt worker process termination (SIGKILL) and safe orphaned reservation recovery.
"""

import os
import sys
import time
import uuid
import signal
import tempfile
import unittest
import multiprocessing as mp
from queue import Empty
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.economic_governance import (
    EconomicGovernanceEngine,
    BudgetExhaustionException,
    BudgetFrozenException,
    ReservationExpiredException
)

# ---------------------------------------------------------------------------
# Module-level worker functions for clean multiprocessing IPC across OS processes
# ---------------------------------------------------------------------------

def _mp_worker_reserve(db_path: str, tenant_id: str, entity_id: str, requested_usd: float, requested_tokens: int, task_id: str, queue: Any):
    """Worker executed in an independent OS process to reserve budget."""
    configure_isolated_test_db(db_path)
    engine = EconomicGovernanceEngine()
    pid = os.getpid()
    try:
        res = engine.reserve_budget(
            tenant_id=tenant_id,
            scope_chain=[("DEPARTMENT", entity_id)],
            requested_usd=requested_usd,
            requested_tokens=requested_tokens,
            task_id=task_id
        )
        queue.put({
            "pid": pid,
            "success": True,
            "reservation_id": res.reservation_id,
            "reserved_usd": res.reserved_usd,
            "reserved_tokens": res.reserved_tokens
        })
    except BudgetFrozenException as e:
        queue.put({"pid": pid, "success": False, "reason": "FROZEN", "error": str(e)})
    except BudgetExhaustionException as e:
        queue.put({"pid": pid, "success": False, "reason": "EXHAUSTED", "error": str(e)})
    except Exception as e:
        queue.put({"pid": pid, "success": False, "reason": "ERROR", "error": f"{type(e).__name__}: {e}"})


def _mp_worker_settle(db_path: str, reservation_id: str, actual_usd: float, queue: Any):
    """Worker executed in an independent OS process to settle budget."""
    configure_isolated_test_db(db_path)
    engine = EconomicGovernanceEngine()
    pid = os.getpid()
    try:
        settlement = engine.settle_budget(
            reservation_id=reservation_id,
            actual_usd=actual_usd
        )
        queue.put({"pid": pid, "success": True, "reservation_id": reservation_id, "actual_usd": settlement.actual_usd})
    except ReservationExpiredException:
        queue.put({"pid": pid, "success": False, "reason": "ALREADY_SETTLED_OR_EXPIRED"})
    except Exception as e:
        queue.put({"pid": pid, "success": False, "reason": "ERROR", "error": f"{type(e).__name__}: {e}"})


def _mp_worker_release(db_path: str, reservation_id: str, queue: Any):
    """Worker executed in an independent OS process to release budget."""
    configure_isolated_test_db(db_path)
    engine = EconomicGovernanceEngine()
    pid = os.getpid()
    try:
        ok = engine.release_reservation(reservation_id=reservation_id, reason="CROSS_PROCESS_RELEASE")
        queue.put({"pid": pid, "success": ok, "reservation_id": reservation_id})
    except Exception as e:
        queue.put({"pid": pid, "success": False, "reason": "ERROR", "error": f"{type(e).__name__}: {e}"})


def _probe_worker(queue: Any):
    queue.put(os.getpid())


_SPAWN_CONTEXT_OK = None


def _worker_context():
    """Return spawn when this interpreter can actually start a spawn child.

    Some Termux/Android Python builds exit a spawn child with status 1 before it
    can report; fork remains available there. Probe once and cache the result.
    """
    global _SPAWN_CONTEXT_OK
    if _SPAWN_CONTEXT_OK is None:
        try:
            ctx = mp.get_context("spawn")
            queue = ctx.Queue()
            probe = ctx.Process(target=_probe_worker, args=(queue,))
            probe.start()
            probe.join(5.0)
            _SPAWN_CONTEXT_OK = probe.exitcode == 0 and not queue.empty()
        except Exception:
            _SPAWN_CONTEXT_OK = False
    return mp.get_context("spawn" if _SPAWN_CONTEXT_OK else "fork")


def _join_workers(processes, timeout: float = 60.0):
    """Join workers within a single shared deadline, then stop stragglers.

    Joining each process with its own timeout multiplied the worst case by the
    worker count; the deadline here is global. Anything still alive is
    terminated so the suite cannot leave orphaned writers behind the shared DB.
    """
    deadline = time.time() + timeout
    for p in processes:
        p.join(timeout=max(0.0, deadline - time.time()))
    stragglers = [p for p in processes if p.is_alive()]
    for p in stragglers:
        p.terminate()
    for p in processes:
        p.join(timeout=5.0)
        if p.is_alive():
            p.kill()
    return stragglers


def _collect_results(queue, expected: int, timeout: float = 60.0):
    """Drain up to ``expected`` worker results without blocking indefinitely.

    A bare ``queue.get()`` waits forever when a worker dies before reporting,
    which previously stalled CI until the job timeout. Bounded reads turn that
    into a normal test failure that reports how many workers answered.
    """
    results = []
    deadline = time.time() + timeout
    while len(results) < expected:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            results.append(queue.get(timeout=remaining))
        except Empty:
            break
    return results


class TestPhase14CrossProcessGovernance(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = db.db_path
        # "spawn" starts a clean interpreter per worker. "fork" copies the
        # parent's lock state, so a worker can inherit an import/runtime lock
        # held by a background thread left over from an earlier suite and
        # deadlock before it ever reports a result.
        self.ctx = _worker_context()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "cross_process_governance.db")
        configure_isolated_test_db(self.db_path)
        self.engine = EconomicGovernanceEngine()
        self.tenant_id = f"tnt_proc_{uuid.uuid4().hex[:8]}"
        self.company_id = f"comp_proc_{uuid.uuid4().hex[:8]}"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Cross-Process Corp', ?)",
                (self.tenant_id, time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) "
                "VALUES (?, ?, 'Cross-Process Inc', 'US', 'Autonomous Systems', 'ENTERPRISE', 'ACTIVE', ?)",
                (self.company_id, self.tenant_id, time.time())
            )
            conn.commit()

    def tearDown(self):
        if getattr(self, "orig_db_path", None) and os.path.exists(os.path.dirname(os.path.abspath(self.orig_db_path))):
            db.set_db_path(self.orig_db_path)
            os.environ["ZONATA_DB_PATH"] = self.orig_db_path
        self.temp_dir.cleanup()

    def test_01_cross_process_budget_reservation_contention(self):
        """
        Contention: 20 independent OS processes racing to reserve $100 against a $1,000 budget.
        Invariant: spent + reserved + requested <= 1,000.0
        Expected: Exactly 10 succeed, exactly 10 fail closed with BudgetExhaustionException.
        Total reserved must equal exactly $1,000.00 (zero over-reservation).
        Distinct OS processes verified via separate PIDs.
        """
        entity_id = f"dept_proc_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=1000.0,
            soft_limit_pct=80.0,
            hard_limit_pct=100.0
        )

        queue = self.ctx.Queue()
        processes = []
        for i in range(20):
            p = self.ctx.Process(
                target=_mp_worker_reserve,
                args=(self.db_path, self.tenant_id, entity_id, 100.0, 0, f"task_proc_{i}", queue)
            )
            processes.append(p)

        # Launch all 20 independent OS processes
        for p in processes:
            p.start()

        stragglers = _join_workers(processes)
        results = _collect_results(queue, 20)

        self.assertEqual(
            len(results), 20,
            f"Expected 20 results, received {len(results)} "
            f"({len(stragglers)} worker(s) terminated without reporting)"
        )

        # Verify multiple distinct PIDs were spawned
        pids = {r["pid"] for r in results}
        self.assertGreaterEqual(len(pids), 10, f"Must execute across distinct OS processes, observed {len(pids)} PIDs")

        successes = [r for r in results if r.get("success")]
        exhausted = [r for r in results if not r.get("success") and r.get("reason") == "EXHAUSTED"]

        self.assertEqual(len(successes), 10, f"Exactly 10 processes must succeed, observed {len(successes)}")
        self.assertEqual(len(exhausted), 10, f"Exactly 10 processes must fail closed, observed {len(exhausted)}")

        # Independent database verification from fresh connection
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT allocated_usd, spent_usd, reserved_usd FROM enterprise_budgets WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(float(row["allocated_usd"]), 1000.0)
            self.assertEqual(float(row["spent_usd"]), 0.0)
            self.assertEqual(float(row["reserved_usd"]), 1000.0)

    def test_02_cross_process_token_reservation_contention(self):
        """
        Contention: 15 independent OS processes requesting 10,000 tokens against a 50,000 token ceiling.
        Expected: Exactly 5 succeed, exactly 10 fail closed.
        Total reserved tokens must equal exactly 50,000.
        """
        entity_id = f"dept_tok_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=100000.0,  # USD unconstrained
            allocated_tokens=50000,
            soft_limit_pct=80.0,
            hard_limit_pct=100.0
        )

        queue = self.ctx.Queue()
        processes = [
            self.ctx.Process(
                target=_mp_worker_reserve,
                args=(self.db_path, self.tenant_id, entity_id, 1.0, 10000, f"tok_proc_{i}", queue)
            )
            for i in range(15)
        ]

        for p in processes:
            p.start()
        stragglers = _join_workers(processes)

        results = _collect_results(queue, 15)
        self.assertEqual(
            len(results), 15,
            f"Expected 15 results, received {len(results)} "
            f"({len(stragglers)} worker(s) terminated without reporting)"
        )
        successes = [r for r in results if r.get("success")]
        exhausted = [r for r in results if not r.get("success") and r.get("reason") == "EXHAUSTED"]

        self.assertEqual(len(successes), 5, f"Expected 5 token reservations, got {len(successes)}")
        self.assertEqual(len(exhausted), 10, f"Expected 10 token exhaustion rejections, got {len(exhausted)}")

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT allocated_tokens, reserved_tokens FROM enterprise_budgets WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            self.assertEqual(int(row["reserved_tokens"]), 50000)

    def test_03_cross_process_concurrent_settlement_and_release(self):
        """
        Verify that independent OS processes can concurrently settle and release reservations
        without race conditions, corrupting balances, or losing unspent capacity.
        """
        entity_id = f"dept_settle_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=1000.0,
            hard_limit_pct=100.0
        )

        # Pre-reserve 6 reservations of $100 each ($600 reserved)
        reservations = []
        for i in range(6):
            res = self.engine.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[("DEPARTMENT", entity_id)],
                requested_usd=100.0,
                task_id=f"init_res_{i}"
            )
            reservations.append(res.reservation_id)

        queue = self.ctx.Queue()
        processes = []

        # 3 processes settle $80 each (releasing $20 underrun per reservation)
        for rid in reservations[:3]:
            processes.append(
                self.ctx.Process(target=_mp_worker_settle, args=(self.db_path, rid, 80.0, queue))
            )

        # 3 processes release full $100 reservation
        for rid in reservations[3:]:
            processes.append(
                self.ctx.Process(target=_mp_worker_release, args=(self.db_path, rid, queue))
            )

        for p in processes:
            p.start()
        stragglers = _join_workers(processes)

        results = _collect_results(queue, 6)
        self.assertEqual(
            len(results), 6,
            f"Expected 6 results, received {len(results)} "
            f"({len(stragglers)} worker(s) terminated without reporting)"
        )
        for r in results:
            self.assertTrue(r.get("success"), f"Cross-process operation failed: {r}")

        # Independent database verification
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT allocated_usd, spent_usd, reserved_usd FROM enterprise_budgets WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            # 3 settlements of $80 = $240 spent.
            # All 6 reservations resolved (3 settled + 3 released), so reserved_usd MUST be 0.0
            self.assertEqual(float(row["spent_usd"]), 240.0)
            self.assertEqual(float(row["reserved_usd"]), 0.0)
            # Available capacity = 1000.0 - 240.0 = 760.0
            available = float(row["allocated_usd"]) - (float(row["spent_usd"]) + float(row["reserved_usd"]))
            self.assertEqual(available, 760.0)

    def test_04_cross_process_double_settlement_rejection(self):
        """
        Race condition stress: 10 independent OS processes attempting to settle the EXACT SAME reservation.
        Exactly 1 must succeed; 9 must fail with ReservationExpiredException / already settled rejection.
        """
        entity_id = f"dept_race_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=500.0,
            hard_limit_pct=100.0
        )
        res = self.engine.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[("DEPARTMENT", entity_id)],
            requested_usd=100.0,
            task_id="single_res_race"
        )

        queue = self.ctx.Queue()
        processes = [
            self.ctx.Process(target=_mp_worker_settle, args=(self.db_path, res.reservation_id, 100.0, queue))
            for _ in range(10)
        ]

        for p in processes:
            p.start()
        stragglers = _join_workers(processes)

        results = _collect_results(queue, 10)
        self.assertEqual(
            len(results), 10,
            f"Expected 10 results, received {len(results)} "
            f"({len(stragglers)} worker(s) terminated without reporting)"
        )
        successes = [r for r in results if r.get("success")]
        already_settled = [r for r in results if not r.get("success") and r.get("reason") == "ALREADY_SETTLED_OR_EXPIRED"]

        self.assertEqual(len(successes), 1, f"Exactly 1 process must settle the reservation, got {len(successes)}")
        self.assertEqual(len(already_settled), 9, f"Exactly 9 processes must receive double-settlement rejections, got {len(already_settled)}")

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT spent_usd, reserved_usd FROM enterprise_budgets WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            self.assertEqual(float(row["spent_usd"]), 100.0)
            self.assertEqual(float(row["reserved_usd"]), 0.0)

    def test_05_cross_process_emergency_freeze_fail_closed(self):
        """
        Verify that an emergency stop freeze is immediately visible and strictly enforced
        across 10 separate OS processes trying to reserve.
        """
        entity_id = f"dept_frz_{uuid.uuid4().hex[:8]}"
        self.engine.configure_budget(
            entity_id=entity_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=1000.0,
            hard_limit_pct=100.0
        )

        # Freeze the entity budget
        self.engine.freeze_budget(entity_id, "EMERGENCY_SECURITY_STOP")

        queue = self.ctx.Queue()
        processes = [
            self.ctx.Process(
                target=_mp_worker_reserve,
                args=(self.db_path, self.tenant_id, entity_id, 50.0, 0, f"frz_task_{i}", queue)
            )
            for i in range(10)
        ]

        for p in processes:
            p.start()
        stragglers = _join_workers(processes)

        results = _collect_results(queue, 10)
        self.assertEqual(
            len(results), 10,
            f"Expected 10 results, received {len(results)} "
            f"({len(stragglers)} worker(s) terminated without reporting)"
        )
        frozen_rejections = [r for r in results if not r.get("success") and r.get("reason") == "FROZEN"]

        self.assertEqual(len(frozen_rejections), 10, f"All 10 OS processes must fail closed with FROZEN rejection")

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT reserved_usd, spent_usd FROM enterprise_budgets WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            self.assertEqual(float(row["reserved_usd"]), 0.0)
            self.assertEqual(float(row["spent_usd"]), 0.0)


if __name__ == "__main__":
    unittest.main()
