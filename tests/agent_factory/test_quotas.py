"""Tests for Atomic Quotas and Budget Enforcement (Phase 5)."""

import sqlite3
import pytest
from agent_factory.control.quotas import (
    ensure_quotas_seeded, reserve_quota, release_quota, get_quota_status
)


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_quotas.db")
    schema_path = "/data/data/com.termux/files/home/AI-robo-assistant-saas/migrations/sqlite/0013_agent_factory_core.sql"
    with open(schema_path, "r") as f:
        schema = f.read()
    conn = sqlite3.connect(db_file)
    conn.executescript(schema)
    conn.commit()
    conn.close()

    def get_conn():
        return sqlite3.connect(db_file)

    return get_conn


def test_atomic_quota_reservation_and_limit(test_db):
    conn_factory = test_db
    tenant_id = "tnt_quota_test"
    period = "2026-11"

    with conn_factory() as conn:
        # 1. Seed quotas
        ensure_quotas_seeded(conn, tenant_id, period)
        status = get_quota_status(conn, tenant_id, period)
        assert status["builds"]["used"] == 0.0
        assert status["builds"]["limit"] == 10.0

        # 2. Reserve 4 builds
        ok = reserve_quota(conn, tenant_id, "builds", amount=4.0, period=period)
        assert ok is True

        # 3. Reserve 6 builds (hits limit 10.0 exactly)
        ok = reserve_quota(conn, tenant_id, "builds", amount=6.0, period=period)
        assert ok is True

        # 4. Attempt to reserve 1 more build -> must be rejected atomically
        ok = reserve_quota(conn, tenant_id, "builds", amount=1.0, period=period)
        assert ok is False

        # 5. Release 2 builds
        release_quota(conn, tenant_id, "builds", amount=2.0, period=period)
        status = get_quota_status(conn, tenant_id, period)
        assert status["builds"]["used"] == 8.0

        # 6. Now reservation of 1 succeeds again
        ok = reserve_quota(conn, tenant_id, "builds", amount=1.0, period=period)
        assert ok is True
        status = get_quota_status(conn, tenant_id, period)
        assert status["builds"]["used"] == 9.0
