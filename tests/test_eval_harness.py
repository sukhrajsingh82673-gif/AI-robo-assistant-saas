"""
OpenCode Step 2K — Eval Harness Acceptance Test Suite.

Verifies:
1. All 6 departments (finance, operations, sales, hr, procurement, customer_support) have >= 10 golden tasks in YAML.
2. Eval tasks evaluate deterministically with protocol correctness, latency, and cost micro-units tracking.
3. Eval runs persist into eval_runs database table with multi-tenant schema support.
4. Spend cap violations trigger SpendCapExceededError.
5. Below-threshold pass rates result in FAILED_THRESHOLD status.
6. Rule 21 disclaimer is strictly enforced and present in results and logs.
"""

import os
import unittest
import pytest

from core.db import configure_isolated_test_db, db
from core.evals import (
    ensure_eval_tables,
    EvalHarness,
    EvalTask,
    RULE_21_DISCLAIMER,
    SpendCapExceededError,
)


class TestEvalHarness(unittest.TestCase):
    """Acceptance tests for the OpenCode Step 2K Eval Harness."""

    @classmethod
    def setUpClass(cls):
        cls.db_path = configure_isolated_test_db()
        ensure_eval_tables()

    def setUp(self):
        self.harness = EvalHarness()

    def test_01_all_six_departments_present_with_at_least_ten_tasks(self):
        """All 6 required departments must have at least 10 golden tasks."""
        expected_departments = [
            "customer_support",
            "finance",
            "hr",
            "operations",
            "procurement",
            "sales",
        ]
        available = self.harness.list_available_departments()
        for dept in expected_departments:
            self.assertIn(dept, available, f"Department {dept} missing from evals/departments/")
            tasks = self.harness.load_department_tasks(dept)
            self.assertGreaterEqual(
                len(tasks), 10, f"Department {dept} must have at least 10 tasks, found {len(tasks)}"
            )

    def test_02_task_deterministic_evaluation_tracks_cost_and_latency(self):
        """Evaluating a task deterministically records cost in micro-units and non-zero latency."""
        tasks = self.harness.load_department_tasks("finance")
        task = tasks[0]
        res = self.harness.evaluate_task_deterministic(task)

        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)
        self.assertGreater(res.cost_micro_units, 0)
        self.assertGreaterEqual(res.latency_ms, 0.0)
        self.assertEqual(len(res.errors), 0)

    def test_03_department_eval_persists_to_eval_runs_table(self):
        """Running department eval persists summary record into eval_runs."""
        summary = self.harness.run_department(
            department="operations",
            tier="WORKER",
            model="test-deterministic-worker",
            threshold=0.90,
        )

        self.assertEqual(summary.status, "COMPLETED")
        self.assertGreaterEqual(summary.pass_rate, 0.90)
        self.assertEqual(summary.total_tasks, 10)
        self.assertEqual(summary.passed_tasks, 10)
        self.assertGreater(summary.total_cost_micro_units, 0)
        self.assertIn(RULE_21_DISCLAIMER, summary.disclaimer)

        # Verify database record
        with db.get_connection() as conn:
            cur = conn.execute(
                "SELECT department, tier, model, total_tasks, passed_tasks, pass_rate, status FROM eval_runs WHERE id = ?",
                (summary.id,),
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "operations")
            self.assertEqual(row[1], "WORKER")
            self.assertEqual(row[2], "test-deterministic-worker")
            self.assertEqual(row[3], 10)
            self.assertEqual(row[4], 10)
            self.assertAlmostEqual(row[5], 1.0)
            self.assertEqual(row[6], "COMPLETED")

    def test_04_spend_cap_exceeded_raises_error(self):
        """When spend cap is lower than accumulated task costs, SpendCapExceededError is raised."""
        with self.assertRaises(SpendCapExceededError):
            self.harness.run_department(
                department="sales",
                max_spend_micro_units=50,  # lower than single task cost of 150
            )

    def test_05_threshold_failure_marks_run_failed(self):
        """When pass rate falls below threshold, status is marked FAILED_THRESHOLD."""
        # Use high threshold 1.01 so it cannot be met
        summary = self.harness.run_department(
            department="hr",
            threshold=1.01,
        )
        self.assertEqual(summary.status, "FAILED_THRESHOLD")

    def test_06_rule_21_measurement_disclaimer_invariant(self):
        """Rule 21 requires synthetic pass rates never be presented as evidence of human parity."""
        self.assertIn("Synthetic pass rates", RULE_21_DISCLAIMER)
        self.assertIn("never presented as evidence of human parity", RULE_21_DISCLAIMER)

        summary = self.harness.run_department(department="customer_support")
        self.assertEqual(summary.disclaimer, RULE_21_DISCLAIMER)
