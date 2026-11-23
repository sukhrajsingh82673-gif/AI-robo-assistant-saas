"""
ZONATA Cluster Leader Lease & Election Engine
============================================
Enforces distributed single-leader execution using scheduler_leader_leases.
Provides monotonic lease renewals and dead-node failover when expires_at < now.
"""

import time
import logging
from typing import Optional, Dict, Any
from core.db import db, DatabaseDialect

logger = logging.getLogger("zonata.daemon.leader")


class LeaderElector:
    """Manages distributed leader leases with automatic failover for daemon nodes."""

    def __init__(self, lease_key: str = "cluster_daemon_leader", node_id: Optional[str] = None):
        self.lease_key = lease_key
        import uuid
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:12]}"

    def try_acquire_or_renew(self, ttl_seconds: float = 30.0) -> bool:
        """
        Attempts to acquire or renew leadership lease.
        Returns True if this node is the authoritative leader, False otherwise.
        """
        now = time.time()
        expires_at = now + ttl_seconds

        with db.get_connection() as conn:
            cur = conn.cursor()

            # Ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_leader_leases (
                    lease_key TEXT PRIMARY KEY,
                    leader_node_id TEXT NOT NULL,
                    heartbeat_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)

            # Fetch existing lease
            cur.execute("SELECT leader_node_id, expires_at FROM scheduler_leader_leases WHERE lease_key = ?", (self.lease_key,))
            row = cur.fetchone()

            if not row:
                # No lease exists; attempt initial insert
                try:
                    cur.execute(
                        "INSERT INTO scheduler_leader_leases (lease_key, leader_node_id, heartbeat_at, expires_at) VALUES (?, ?, ?, ?)",
                        (self.lease_key, self.node_id, now, expires_at)
                    )
                    conn.commit()
                    return True
                except Exception:
                    # Race condition caught
                    return False

            current_leader, current_expires_at = row[0], float(row[1])

            # Case 1: We are already the leader -> renew
            if current_leader == self.node_id:
                cur.execute(
                    "UPDATE scheduler_leader_leases SET heartbeat_at = ?, expires_at = ? WHERE lease_key = ? AND leader_node_id = ?",
                    (now, expires_at, self.lease_key, self.node_id)
                )
                conn.commit()
                return True

            # Case 2: Another node was leader, but lease expired -> take over
            if current_expires_at < now:
                cur.execute(
                    "UPDATE scheduler_leader_leases SET leader_node_id = ?, heartbeat_at = ?, expires_at = ? WHERE lease_key = ? AND expires_at < ?",
                    (self.node_id, now, expires_at, self.lease_key, now)
                )
                conn.commit()
                # Verify we actually won the takeover
                cur.execute("SELECT leader_node_id FROM scheduler_leader_leases WHERE lease_key = ?", (self.lease_key,))
                check = cur.fetchone()
                return bool(check and check[0] == self.node_id)

            # Case 3: Another node holds a valid, unexpired lease
            return False

    def release_lease(self) -> bool:
        """Voluntarily releases the leadership lease on graceful shutdown."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE scheduler_leader_leases SET expires_at = 0 WHERE lease_key = ? AND leader_node_id = ?",
                (self.lease_key, self.node_id)
            )
            conn.commit()
            return True

    def get_current_leader(self) -> Optional[Dict[str, Any]]:
        """Returns the current leader node info if active."""
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT leader_node_id, heartbeat_at, expires_at FROM scheduler_leader_leases WHERE lease_key = ?", (self.lease_key,))
            row = cur.fetchone()
            if row:
                leader, hb, exp = row[0], float(row[1]), float(row[2])
                return {
                    "leader_node_id": leader,
                    "heartbeat_at": hb,
                    "expires_at": exp,
                    "is_active": exp >= now,
                    "is_self": leader == self.node_id,
                }
            return None
