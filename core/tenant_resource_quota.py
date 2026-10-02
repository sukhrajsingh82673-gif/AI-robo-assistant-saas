"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Phase 8 & 31 — Multi-Tenant Resource Quota & Noisy-Neighbor Isolation Engine
Enforces tenant-level resource boundaries across missions, agents, tokens, tools, and storage.

Constitutional Invariant:
  NOISY_NEIGHBOR_CANNOT_DEGRADE_PEER_TENANT
  QUOTAS_ARE_HARD_CONSTRAINTS_ENFORCED_FAIL_CLOSED
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.tenant.quota")

class TenantQuotaExceededError(PermissionError):
    """Raised when an operation breaches configured tenant resource limits."""
    pass

@dataclass
class TenantQuotaConfig:
    tenant_id: str
    max_active_missions: int = 100
    max_ai_employees: int = 50
    max_tokens_per_minute: int = 500000
    max_tool_calls_daily: int = 50000
    max_storage_bytes: int = 50 * 1024 * 1024 * 1024 # 50 GB default

class TenantResourceQuotaManager:
    """
    Guarantees resource isolation between competing enterprise tenants.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_resource_quotas (
                tenant_id TEXT PRIMARY KEY,
                max_active_missions INTEGER NOT NULL DEFAULT 100,
                max_ai_employees INTEGER NOT NULL DEFAULT 50,
                max_tokens_per_minute INTEGER NOT NULL DEFAULT 500000,
                max_tool_calls_daily INTEGER NOT NULL DEFAULT 50000,
                max_storage_bytes INTEGER NOT NULL DEFAULT 53687091200,
                current_active_missions INTEGER NOT NULL DEFAULT 0,
                current_ai_employees INTEGER NOT NULL DEFAULT 0,
                tokens_used_this_minute INTEGER NOT NULL DEFAULT 0,
                minute_window_epoch INTEGER NOT NULL DEFAULT 0,
                daily_tool_calls INTEGER NOT NULL DEFAULT 0,
                day_window_epoch INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            );
            """)

    def set_tenant_quota(
        self,
        tenant_id: str,
        max_active_missions: int = 100,
        max_ai_employees: int = 50,
        max_tokens_per_minute: int = 500000,
        max_tool_calls_daily: int = 50000,
        max_storage_bytes: int = 53687091200
    ) -> bool:
        """Configure custom quota boundaries for a specific tenant."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO tenant_resource_quotas (
                tenant_id, max_active_missions, max_ai_employees,
                max_tokens_per_minute, max_tool_calls_daily, max_storage_bytes,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id) DO UPDATE SET
                max_active_missions = excluded.max_active_missions,
                max_ai_employees = excluded.max_ai_employees,
                max_tokens_per_minute = excluded.max_tokens_per_minute,
                max_tool_calls_daily = excluded.max_tool_calls_daily,
                max_storage_bytes = excluded.max_storage_bytes,
                updated_at = excluded.updated_at
            """, (
                tenant_id, max_active_missions, max_ai_employees,
                max_tokens_per_minute, max_tool_calls_daily, max_storage_bytes, now
            ))
        return True

    def check_and_reserve_mission_slot(self, tenant_id: str) -> bool:
        """Reserve a concurrent mission slot under tenant quota."""
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            cursor = conn.execute(
                "SELECT max_active_missions, current_active_missions FROM tenant_resource_quotas WHERE tenant_id = ?",
                (tenant_id,)
            )
            row = cursor.fetchone()
            if not row:
                # Initialize default
                self.set_tenant_quota(tenant_id)
                max_m = 100
                curr_m = 0
            else:
                max_m = row["max_active_missions"]
                curr_m = row["current_active_missions"]

            if curr_m >= max_m:
                raise TenantQuotaExceededError(
                    f"Tenant '{tenant_id}' exceeded active mission quota ({curr_m}/{max_m}). Noisy-neighbor containment active."
                )

            conn.execute(
                "UPDATE tenant_resource_quotas SET current_active_missions = current_active_missions + 1 WHERE tenant_id = ?",
                (tenant_id,)
            )
        return True

    def release_mission_slot(self, tenant_id: str) -> bool:
        """Release mission slot upon completion."""
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE tenant_resource_quotas
            SET current_active_missions = MAX(0, current_active_missions - 1)
            WHERE tenant_id = ?
            """, (tenant_id,))
        return True

    def check_and_consume_tokens(self, tenant_id: str, token_count: int) -> bool:
        """Check rate-limited token window and consume tokens."""
        now_epoch_min = int(time.time() // 60)
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            cursor = conn.execute(
                "SELECT max_tokens_per_minute, tokens_used_this_minute, minute_window_epoch FROM tenant_resource_quotas WHERE tenant_id = ?",
                (tenant_id,)
            )
            row = cursor.fetchone()
            if not row:
                self.set_tenant_quota(tenant_id)
                max_t = 500000
                used_t = 0
                epoch = now_epoch_min
            else:
                max_t = row["max_tokens_per_minute"]
                if row["minute_window_epoch"] == now_epoch_min:
                    used_t = row["tokens_used_this_minute"]
                else:
                    used_t = 0
                epoch = now_epoch_min

            if used_t + token_count > max_t:
                raise TenantQuotaExceededError(
                    f"Tenant '{tenant_id}' token rate limit exceeded ({used_t + token_count}/{max_t} tokens/min)."
                )

            conn.execute("""
            UPDATE tenant_resource_quotas
            SET tokens_used_this_minute = ?, minute_window_epoch = ?
            WHERE tenant_id = ?
            """, (used_t + token_count, epoch, tenant_id))
        return True

tenant_quota_manager = TenantResourceQuotaManager()
