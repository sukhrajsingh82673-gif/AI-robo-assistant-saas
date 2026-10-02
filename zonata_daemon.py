#!/usr/bin/env python3
"""
ZONATA Universal AI Company Operating System — Autonomous 24x7x365 Supervisor Daemon
Stand-alone daemon process monitoring live company vitals, schedules, workers, and storage.
"""

import sys
import time
import signal
import os
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.supervisor import CompanySupervisorDaemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SupervisorDaemon] %(message)s"
)
logger = logging.getLogger("zonata.daemon")

def main():
    tenant_id = os.environ.get("ZONATA_TENANT_ID", "tnt_primary")
    company_id = os.environ.get("ZONATA_COMPANY_ID", "comp_primary")
    tick_interval = float(os.environ.get("ZONATA_TICK_INTERVAL", "10.0"))

    logger.info("=" * 65)
    logger.info(" ZONATA AUTONOMOUS 24x7x365 COMPANY SUPERVISOR DAEMON")
    logger.info("=" * 65)
    logger.info(f" Tenant Scope      : {tenant_id}")
    logger.info(f" Company Scope     : {company_id}")
    logger.info(f" Tick Interval     : {tick_interval} seconds")
    logger.info("=" * 65)

    daemon = CompanySupervisorDaemon(
        tenant_id=tenant_id,
        company_id=company_id,
        tick_interval_sec=tick_interval
    )

    def handle_exit(signum, frame):
        logger.info("[*] Received shutdown signal. Stopping supervisor daemon gracefully...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    daemon.start()
    logger.info("[*] Autonomous supervision loop running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_exit(None, None)

if __name__ == "__main__":
    main()
