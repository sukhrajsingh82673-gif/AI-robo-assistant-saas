"""ZONATA Agent Factory - Quota and Budget Enforcement.

Implements atomic quota reservations against af_quota_usage.
Enforces limits for:
- builds
- cost_usd
- agents_published
- tokens
- concurrent_builds
- sandbox_seconds
"""

import time
from typing import Dict, Tuple, Optional


DEFAULT_LIMITS = {
    "builds": 10.0,
    "agents_published": 50.0,
    "tokens": 5_000_000.0,
    "cost_usd": 25.0,
    "sandbox_seconds": 3600.0,
    "concurrent_builds": 4.0
}


def current_period() -> str:
    """Return period in YYYY-MM format."""
    return time.strftime("%Y-%m")


def ensure_quotas_seeded(conn, tenant_id: str, period: Optional[str] = None) -> None:
    """Seed initial quota limits for tenant if not already present."""
    p = period or current_period()
    for metric, limit in DEFAULT_LIMITS.items():
        conn.execute("""
            INSERT OR IGNORE INTO af_quota_usage (tenant_id, period, metric, used, limit_value)
            VALUES (?, ?, ?, 0.0, ?)
        """, (tenant_id, p, metric, limit))


def reserve_quota(
    conn,
    tenant_id: str,
    metric: str,
    amount: float = 1.0,
    period: Optional[str] = None
) -> bool:
    """
    Atomically attempt to reserve quota.
    Returns True if reservation succeeded, False if limit exceeded.
    """
    p = period or current_period()
    ensure_quotas_seeded(conn, tenant_id, p)

    cur = conn.execute("""
        UPDATE af_quota_usage
        SET used = used + ?
        WHERE tenant_id = ? AND period = ? AND metric = ? AND (used + ?) <= limit_value
    """, (amount, tenant_id, p, metric, amount))

    return cur.rowcount > 0


def release_quota(
    conn,
    tenant_id: str,
    metric: str,
    amount: float = 1.0,
    period: Optional[str] = None
) -> None:
    """Release quota (e.g. when concurrent build finishes or build cancelled)."""
    p = period or current_period()
    conn.execute("""
        UPDATE af_quota_usage
        SET used = MAX(0.0, used - ?)
        WHERE tenant_id = ? AND period = ? AND metric = ?
    """, (amount, tenant_id, p, metric))


def get_quota_status(
    conn,
    tenant_id: str,
    period: Optional[str] = None
) -> Dict[str, Dict[str, float]]:
    """Return current usage and limits for tenant."""
    p = period or current_period()
    ensure_quotas_seeded(conn, tenant_id, p)

    cur = conn.execute(
        "SELECT metric, used, limit_value FROM af_quota_usage WHERE tenant_id = ? AND period = ?",
        (tenant_id, p)
    )
    return {
        r[0]: {"used": r[1], "limit": r[2], "remaining": max(0.0, r[2] - r[1])}
        for r in cur.fetchall()
    }
