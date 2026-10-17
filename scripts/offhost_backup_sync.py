#!/usr/bin/env python3
"""
ZONATA Enterprise SaaS — Off-Host Backup Synchronizer CLI
Operational tool for continuous or batch replication of WAL segments,
base backups, and hot snapshots to remote S3 / MinIO object storage.
Enforces BLK-01 (Off-Host Storage) and BLK-12 (Standardized RTO/RPO Metrics).
"""

import os
import sys
import time
import json
import argparse
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.offhost_backup_replicator import offhost_backup_replicator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("zonata.cli.offhost_sync")


def sync_once(tenant_id: str, verify: bool = False) -> dict:
    """Executes a single synchronization sweep across local backup directories."""
    logger.info(f"Starting off-host synchronization sweep for tenant '{tenant_id}'...")
    start_time = time.time()
    
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tenant_id": tenant_id,
        "wal_segments_synced": 0,
        "base_backups_synced": 0,
        "snapshots_synced": 0,
        "receipts": [],
        "errors": []
    }

    # 1. Sync PostgreSQL WAL Archive
    wal_dir = os.environ.get("PG_WAL_ARCHIVE_DIR", "/var/lib/postgresql/wal_archive")
    if os.path.exists(wal_dir):
        for f in sorted(os.listdir(wal_dir)):
            if not f.endswith(".backup") and not f.startswith("."):
                fp = os.path.join(wal_dir, f)
                if os.path.isfile(fp):
                    try:
                        receipt = offhost_backup_replicator.replicate_wal_segment(fp, tenant_id=tenant_id)
                        results["wal_segments_synced"] += 1
                        results["receipts"].append(receipt.to_dict())
                        if verify:
                            offhost_backup_replicator.verify_offhost_object(receipt.receipt_id, tenant_id)
                    except Exception as e:
                        results["errors"].append({"file": f, "error": str(e)})

    # 2. Sync PostgreSQL Base Backups
    base_dir = os.environ.get("PG_BASE_BACKUP_DIR", "/var/lib/postgresql/base_backups")
    if os.path.exists(base_dir):
        for d in sorted(os.listdir(base_dir)):
            dp = os.path.join(base_dir, d)
            if os.path.isdir(dp):
                try:
                    receipt = offhost_backup_replicator.replicate_base_backup(dp, d, tenant_id=tenant_id)
                    results["base_backups_synced"] += 1
                    results["receipts"].append(receipt.to_dict())
                    if verify:
                        offhost_backup_replicator.verify_offhost_object(receipt.receipt_id, tenant_id)
                except Exception as e:
                    results["errors"].append({"backup": d, "error": str(e)})

    # 3. Sync SQLite Snapshots
    snap_dir = os.path.join(PROJECT_ROOT, "storage", "backups")
    if os.path.exists(snap_dir):
        for f in sorted(os.listdir(snap_dir)):
            if f.endswith(".db"):
                fp = os.path.join(snap_dir, f)
                try:
                    ev_path = os.path.join(PROJECT_ROOT, "storage", "evidence", "audit_ledger.jsonl")
                    receipt = offhost_backup_replicator.replicate_sqlite_snapshot(
                        fp, tenant_id=tenant_id, evidence_path=ev_path if os.path.exists(ev_path) else None
                    )
                    results["snapshots_synced"] += 1
                    results["receipts"].append(receipt.to_dict())
                    if verify:
                        offhost_backup_replicator.verify_offhost_object(receipt.receipt_id, tenant_id)
                except Exception as e:
                    results["errors"].append({"snapshot": f, "error": str(e)})

    duration = round(time.time() - start_time, 3)
    results["duration_seconds"] = duration
    results["status"] = "SUCCESS" if not results["errors"] else "PARTIAL_FAILURE"
    logger.info(
        f"Sweep completed in {duration}s: {results['wal_segments_synced']} WALs, "
        f"{results['base_backups_synced']} base backups, {results['snapshots_synced']} snapshots synced."
    )
    return results


def main():
    parser = argparse.ArgumentParser(description="ZONATA Off-Host Backup Synchronizer")
    parser.add_argument("--tenant-id", default="tnt_primary", help="Tenant ID scope")
    parser.add_argument("--continuous", action="store_true", help="Run continuously as a daemon")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for continuous mode")
    parser.add_argument("--verify", action="store_true", help="Verify cryptographic digest immediately after upload")
    args = parser.parse_args()

    if args.continuous:
        logger.info(f"Starting continuous off-host backup synchronizer daemon (interval: {args.interval}s)...")
        while True:
            try:
                res = sync_once(args.tenant_id, verify=args.verify)
                print(json.dumps(res))
            except Exception as e:
                logger.error(f"Error in off-host sync daemon: {e}")
            time.sleep(args.interval)
    else:
        res = sync_once(args.tenant_id, verify=args.verify)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
