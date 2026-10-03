#!/usr/bin/env python3
"""
ZONATA Universal AI Co-Worker: 24-Hour Soak & Endurance Test Harness

This script provides an operational endurance test harness executing multi-worker
missions, lease management, background jobs, memory tier operations, and telemetry
sampling to qualify long-running operational stability.

Usage:
    python3 scripts/run_soak_harness.py [--duration-hours HOURS] [--interval-seconds SEC]
"""

import sys
import os
import time
import argparse
import logging
import resource
from typing import Dict, Any, List

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.coworker.engine import UniversalCoworkerEngine
from core.coworker.memory_tier import MemoryTier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SOAK-HARNESS] %(message)s",
)
logger = logging.getLogger("soak_harness")


class SoakHarness:
    def __init__(self, duration_hours: float = 24.0, interval_seconds: float = 5.0):
        self.duration_seconds = duration_hours * 3600.0
        self.interval_seconds = interval_seconds
        self.engine = UniversalCoworkerEngine(tenant_id="tenant_soak_testing")
        self.cycles_completed = 0
        self.errors_encountered = 0
        self.start_time = 0.0
        self.initial_memory_kb = 0

    def get_memory_usage_kb(self) -> int:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss

    def run(self):
        logger.info(
            f"Starting ZONATA 24-Hour Soak Harness. Target Duration: {self.duration_seconds/3600:.4f} hours"
        )
        self.start_time = time.time()
        self.initial_memory_kb = self.get_memory_usage_kb()
        logger.info(f"Initial Process RSS Memory: {self.initial_memory_kb} KB")

        # Provision soak worker persona
        worker = self.engine.create_coworker("Operations Assistant")
        logger.info(f"Provisioned Soak Co-Worker Profile: ID={worker.worker_id}, Role={worker.role}")

        while True:
            elapsed = time.time() - self.start_time
            if elapsed >= self.duration_seconds:
                logger.info(
                    f"Soak target duration reached ({elapsed:.2f}s). Completing test harness."
                )
                break

            self.cycles_completed += 1
            current_memory_kb = self.get_memory_usage_kb()
            memory_drift_pct = (
                ((current_memory_kb - self.initial_memory_kb) / max(1, self.initial_memory_kb)) * 100.0
            )

            logger.info(
                f"[Cycle #{self.cycles_completed}] Elapsed: {elapsed:.1f}s / {self.duration_seconds:.1f}s | "
                f"Memory: {current_memory_kb} KB (Drift: {memory_drift_pct:+.2f}%)"
            )

            try:
                # 1. Execute background mission dispatch
                mission_objective = f"Soak cycle {self.cycles_completed}: Process records and verify cryptographic ledger."
                mission = self.engine.background_dispatcher.submit_background_prompt(
                    prompt=mission_objective,
                    parent_worker_id=worker.worker_id,
                )
                assert mission.mission_id is not None, "Submission failed to return valid mission_id"
                
                # 2. Execute memory tier verification
                mem_key = f"soak_metric_cycle_{self.cycles_completed}"
                self.engine.memory_manager.store_memory(
                    tier=MemoryTier.OPERATIONAL_MEMORY,
                    key=mem_key,
                    value={"cycle": self.cycles_completed, "timestamp": time.time()},
                    worker_id=worker.worker_id,
                )
                retrieved = self.engine.memory_manager.retrieve_memory(
                    tier=MemoryTier.OPERATIONAL_MEMORY,
                    key=mem_key,
                )
                assert retrieved is not None, "Operational memory retrieval failed during soak"

                # 3. Query telemetry dashboard snapshot
                snapshot = self.engine.dashboard.get_dashboard_snapshot()
                assert "specialized_runtimes" in snapshot, "Dashboard telemetry missing specialized_runtimes section"

            except Exception as e:
                self.errors_encountered += 1
                logger.error(f"Error during cycle #{self.cycles_completed}: {e}", exc_info=True)

            time.sleep(self.interval_seconds)

        final_memory_kb = self.get_memory_usage_kb()
        final_drift_pct = (
            ((final_memory_kb - self.initial_memory_kb) / max(1, self.initial_memory_kb)) * 100.0
        )

        logger.info("==================================================")
        logger.info("SOAK HARNESS RUN SUMMARY:")
        logger.info(f"Total Duration: {time.time() - self.start_time:.2f} seconds")
        logger.info(f"Cycles Executed: {self.cycles_completed}")
        logger.info(f"Errors Encountered: {self.errors_encountered}")
        logger.info(f"Initial Memory: {self.initial_memory_kb} KB")
        logger.info(f"Final Memory: {final_memory_kb} KB")
        logger.info(f"Memory Drift: {final_drift_pct:+.2f}%")
        logger.info("==================================================")

        if self.errors_encountered > 0:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZONATA 24-Hour Soak Harness")
    parser.add_argument(
        "--duration-hours",
        type=float,
        default=0.001,  # Default to short test run (~3.6 seconds)
        help="Duration to run the harness in hours (default: 0.001 for test run)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=0.5,
        help="Interval between soak iterations in seconds (default: 0.5)",
    )
    args = parser.parse_args()

    harness = SoakHarness(
        duration_hours=args.duration_hours,
        interval_seconds=args.interval_seconds,
    )
    harness.run()
