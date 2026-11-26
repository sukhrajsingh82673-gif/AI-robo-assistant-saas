#!/usr/bin/env python3
"""
ZONATA Eval Harness CLI Runner
OpenCode Step 2K: Executes golden eval tasks per department, tracking protocol correctness,
costs in micro-units, latencies, and enforcing threshold gates and Rule 21 disclaimers.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.evals.runner import EvalHarness, SpendCapExceededError, EvalThresholdFailedError
from core.evals.types import RULE_21_DISCLAIMER

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zonata.evals.cli")


def main():
    parser = argparse.ArgumentParser(description="Run ZONATA golden department evals")
    parser.add_argument("--department", type=str, default=None, help="Department to evaluate (e.g. finance, operations). Default: all")
    parser.add_argument("--threshold", type=float, default=0.90, help="Minimum pass rate threshold (default: 0.90 / 90%%)")
    parser.add_argument("--max-spend", type=int, default=100000000, help="Spend cap in micro-units (default: 100000000)")
    parser.add_argument("--tier", type=str, default="WORKER", help="Model tier (default: WORKER)")
    parser.add_argument("--model", type=str, default="mock-deterministic-v1", help="Model name (default: mock-deterministic-v1)")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path for results")

    args = parser.parse_args()

    from core.db import db
    try:
        db.verify_readiness()
    except Exception as e:
        logger.warning("Database readiness verification notice: %s", e)

    harness = EvalHarness()
    departments = [args.department] if args.department else harness.list_available_departments()

    print("================================================================================")
    print("               ZONATA EVALUATION HARNESS & BENCHMARK SUITE                     ")
    print("================================================================================")
    print(f"Rule 21 Compliance: {RULE_21_DISCLAIMER}")
    print(f"Target Departments: {', '.join(departments)}")
    print(f"Pass Rate Threshold: {args.threshold * 100.0:.1f}%")
    print(f"Spend Cap: {args.max_spend} micro-units")
    print("--------------------------------------------------------------------------------")

    all_passed = True
    summaries = {}

    for dept in departments:
        try:
            summary = harness.run_department(
                department=dept,
                tier=args.tier,
                model=args.model,
                threshold=args.threshold,
                max_spend_micro_units=args.max_spend,
            )
            summaries[dept] = summary.dict() if hasattr(summary, "dict") else summary.model_dump()
            print(
                f"[{summary.status.ljust(16)}] Dept: {dept.ljust(18)} | "
                f"Tasks: {summary.passed_tasks}/{summary.total_tasks} ({summary.pass_rate*100.0:5.1f}%) | "
                f"Cost: {summary.total_cost_micro_units:7d} µ-units | Latency: {summary.avg_latency_ms:6.2f}ms"
            )
            if summary.status != "COMPLETED":
                all_passed = False
        except Exception as e:
            logger.error("Failed evaluation on department %s: %s", dept, e)
            all_passed = False
            summaries[dept] = {"status": "ERROR", "error": str(e)}

    print("================================================================================")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summaries, f, indent=2)
        print(f"Results saved to {args.output}")

    if not all_passed:
        print("[GATE FAILED] One or more departments failed to meet the required pass rate threshold.")
        sys.exit(1)
    else:
        print("[GATE PASSED] All departments satisfied golden eval thresholds.")
        sys.exit(0)


if __name__ == "__main__":
    main()
