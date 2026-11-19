"""ZONATA Agent Factory - Autonomous Worker Daemon.

Runs in the background, polling DbQueueOrchestrator for queued builds,
maintaining lease heartbeats, executing the ManufacturingPipeline, and
reaping lost jobs if workers crash (AT-19).
"""

from __future__ import annotations
import logging
import signal
import sys
import time
from typing import Any, Callable, Dict, Optional

from agent_factory.control.orchestrator import DbQueueOrchestrator

logger = logging.getLogger("zonata.af.worker")


class FactoryWorker:
    def __init__(
        self,
        orchestrator: DbQueueOrchestrator,
        pipeline_executor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        poll_interval_seconds: float = 1.0,
        heartbeat_interval_seconds: float = 5.0
    ):
        self.orchestrator = orchestrator
        self.pipeline_executor = pipeline_executor
        self.poll_interval = poll_interval_seconds
        self.heartbeat_interval = heartbeat_interval_seconds
        self._running = False

    def run_once(self, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Claim a single build, process it with heartbeat, and complete it."""
        # 1. First reap any expired/lost jobs from dead workers (AT-19 recovery)
        self.orchestrator.reap_lost_builds(timeout_seconds=60.0)

        # 2. Claim next queued job
        job = self.orchestrator.claim_next_build(tenant_id=tenant_id)
        if not job:
            return None

        build_id = job["build_id"]
        logger.info(f"Worker {self.orchestrator.worker_id} claimed build {build_id}")

        # Send heartbeat
        self.orchestrator.heartbeat(build_id)

        try:
            result = {}
            if self.pipeline_executor:
                result = self.pipeline_executor(job)

            self.orchestrator.complete_build(build_id, status="SUCCEEDED")
            return {
                "build_id": build_id,
                "status": "SUCCEEDED",
                "result": result
            }
        except Exception as e:
            logger.error(f"Error processing build {build_id}: {e}")
            self.orchestrator.complete_build(build_id, status="FAILED", error=str(e))
            return {
                "build_id": build_id,
                "status": "FAILED",
                "error": str(e)
            }

    def run_forever(self, tenant_id: Optional[str] = None):
        """Continuous polling loop with graceful signal handling."""
        self._running = True

        def _handle_signal(signum, frame):
            logger.info(f"Worker received signal {signum}. Shutting down gracefully...")
            self._running = False

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        while self._running:
            job = self.run_once(tenant_id=tenant_id)
            if not job:
                time.sleep(self.poll_interval)
            else:
                time.sleep(0.05)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    from core.db import db
    orchestrator = DbQueueOrchestrator(db_conn_factory=db.get_connection)
    worker = FactoryWorker(orchestrator=orchestrator)
    logger.info(f"Starting ZONATA Factory Worker daemon with ID: {orchestrator.worker_id}")
    worker.run_forever()


if __name__ == "__main__":
    main()
