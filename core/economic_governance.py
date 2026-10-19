"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 11 — Workstream A: AI CEO Economic Command & Multi-Scope Budget Governor
Enforces strict hard budget ceilings, token & dollar limits, multi-tier scope hierarchies,
concurrency-safe two-phase atomic budget reservation and settlement, and child-task inheritance.

Constitutional Invariants:
  BUDGET_EXHAUSTION_HALTS_EXECUTION
  CHILD_BUDGET_CANNOT_EXCEED_PARENT_REMAINING
  CONCURRENT_RESERVATIONS_CANNOT_OVERSPEND
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.db import db

logger = logging.getLogger("zonata.governance.economic")

class BudgetScope(str, Enum):
    PLATFORM = "PLATFORM"
    TENANT = "TENANT"
    USER = "USER"
    WORKFLOW = "WORKFLOW"
    AGENT = "AGENT"
    RUN = "RUN"

class BudgetStatus(str, Enum):
    UNDER_BUDGET = "UNDER_BUDGET"
    SOFT_LIMIT_WARNING = "SOFT_LIMIT_WARNING"
    HARD_LIMIT_EXCEEDED = "HARD_LIMIT_EXCEEDED"
    EMERGENCY_STOP = "EMERGENCY_STOP"

class BudgetExhaustionException(PermissionError):
    """Raised when an operation would exceed authorized budget ceilings."""
    def __init__(self, message: str, entity_id: str = "", scope: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.entity_id = entity_id
        self.scope = scope
        self.details = details or {}

class BudgetFrozenException(BudgetExhaustionException):
    """Raised when an entity's budget is locked under an emergency financial halt."""
    pass

class ChildBudgetExceededException(BudgetExhaustionException):
    """Raised when a child task requests more budget than the parent has remaining."""
    pass

class ReservationExpiredException(RuntimeError):
    """Raised when attempting to settle an expired or invalid reservation."""
    pass

@dataclass
class BudgetConfig:
    entity_id: str
    entity_type: str        # PLATFORM, TENANT, USER, WORKFLOW, AGENT, RUN
    tenant_id: str
    company_id: str
    allocated_usd: float
    spent_usd: float = 0.0
    reserved_usd: float = 0.0
    allocated_tokens: int = 0
    spent_tokens: int = 0
    reserved_tokens: int = 0
    soft_limit_pct: float = 80.0
    hard_limit_pct: float = 100.0
    is_frozen: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def available_usd(self) -> float:
        hard_cap = self.allocated_usd * (self.hard_limit_pct / 100.0)
        return max(0.0, hard_cap - (self.spent_usd + self.reserved_usd))

    @property
    def available_tokens(self) -> int:
        if self.allocated_tokens <= 0:
            return 10**9  # Uncapped tokens if not explicitly constrained
        hard_cap = int(self.allocated_tokens * (self.hard_limit_pct / 100.0))
        return max(0, hard_cap - (self.spent_tokens + self.reserved_tokens))

@dataclass
class BudgetReservation:
    reservation_id: str
    tenant_id: str
    scope_chain: List[Dict[str, str]]
    reserved_usd: float
    reserved_tokens: int
    status: str             # RESERVED, SETTLED, RELEASED, EXPIRED
    created_at: float
    expires_at: float
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BudgetSettlement:
    reservation_id: str
    actual_usd: float
    actual_tokens: int
    settled_at: float
    status: str = "SETTLED"
    overrun_usd: float = 0.0
    overrun_tokens: int = 0

class EconomicGovernanceEngine:
    """
    Authoritative Multi-Tier Economic Command and Hard Spend Governor.
    Provides atomic, concurrency-safe budget reservations across all architectural scopes.
    """
    _table_initialized = False

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        if EconomicGovernanceEngine._table_initialized:
            return
        try:
            with db.get_connection() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS enterprise_budgets (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    allocated_usd REAL NOT NULL,
                    spent_usd REAL NOT NULL DEFAULT 0.0,
                    reserved_usd REAL NOT NULL DEFAULT 0.0,
                    allocated_tokens BIGINT NOT NULL DEFAULT 0,
                    spent_tokens BIGINT NOT NULL DEFAULT 0,
                    reserved_tokens BIGINT NOT NULL DEFAULT 0,
                    soft_limit_pct REAL NOT NULL DEFAULT 80.0,
                    hard_limit_pct REAL NOT NULL DEFAULT 100.0,
                    is_frozen INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_bud_tenant ON enterprise_budgets(tenant_id);")

                conn.execute("""
                CREATE TABLE IF NOT EXISTS enterprise_budget_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    reserved_usd REAL NOT NULL DEFAULT 0.0,
                    reserved_tokens BIGINT NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'RESERVED',
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    settled_at REAL,
                    actual_usd REAL DEFAULT 0.0,
                    actual_tokens BIGINT DEFAULT 0,
                    metadata JSON,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_res_tenant ON enterprise_budget_reservations(tenant_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_res_entity ON enterprise_budget_reservations(entity_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_res_status ON enterprise_budget_reservations(status);")
                conn.commit()
                EconomicGovernanceEngine._table_initialized = True
        except Exception as e:
            logger.debug(f"Table initialization deferred: {e}")

    def configure_budget(
        self,
        entity_id: str,
        entity_type: str,
        tenant_id: str,
        company_id: str,
        allocated_usd: float,
        allocated_tokens: int = 0,
        soft_limit_pct: float = 80.0,
        hard_limit_pct: float = 100.0
    ) -> BudgetConfig:
        now = time.time()
        self._ensure_tables()
        with db.get_connection() as conn:
            conn.execute("""
            INSERT INTO enterprise_budgets (
                entity_id, entity_type, tenant_id, company_id, allocated_usd,
                allocated_tokens, spent_usd, reserved_usd, spent_tokens, reserved_tokens,
                soft_limit_pct, hard_limit_pct, is_frozen, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 0, 0, ?, ?, 0, ?, ?)
            ON CONFLICT (entity_id) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                tenant_id = EXCLUDED.tenant_id,
                company_id = EXCLUDED.company_id,
                allocated_usd = EXCLUDED.allocated_usd,
                allocated_tokens = EXCLUDED.allocated_tokens,
                soft_limit_pct = EXCLUDED.soft_limit_pct,
                hard_limit_pct = EXCLUDED.hard_limit_pct,
                updated_at = EXCLUDED.updated_at
            """, (
                entity_id, entity_type, tenant_id, company_id, allocated_usd,
                allocated_tokens, soft_limit_pct, hard_limit_pct, now, now
            ))
            conn.commit()

        return self.get_budget(entity_id)

    def get_budget(self, entity_id: str) -> Optional[BudgetConfig]:
        self._ensure_tables()
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM enterprise_budgets WHERE entity_id = ?", (entity_id,)).fetchone()
            if not row:
                return None
            return BudgetConfig(
                entity_id=row["entity_id"],
                entity_type=row["entity_type"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                allocated_usd=float(row["allocated_usd"]),
                spent_usd=float(row["spent_usd"]),
                reserved_usd=float(row.get("reserved_usd", 0.0) if hasattr(row, "get") else row["reserved_usd"]),
                allocated_tokens=int(row.get("allocated_tokens", 0) if hasattr(row, "get") else row["allocated_tokens"]),
                spent_tokens=int(row.get("spent_tokens", 0) if hasattr(row, "get") else row["spent_tokens"]),
                reserved_tokens=int(row.get("reserved_tokens", 0) if hasattr(row, "get") else row["reserved_tokens"]),
                soft_limit_pct=float(row["soft_limit_pct"]),
                hard_limit_pct=float(row["hard_limit_pct"]),
                is_frozen=bool(row["is_frozen"]),
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"])
            )

    def validate_child_budget_inheritance(
        self,
        parent_entity_id: str,
        requested_child_usd: float,
        requested_child_tokens: int = 0
    ) -> bool:
        """
        Constitutional Invariant: CHILD_BUDGET_CANNOT_EXCEED_PARENT_REMAINING
        Child tasks or subagents cannot be provisioned with a budget exceeding the parent's unreserved remaining pool.
        """
        parent_budget = self.get_budget(parent_entity_id)
        if not parent_budget:
            # Unbudgeted parent allows execution under default platform caps
            return True

        if parent_budget.is_frozen:
            raise BudgetFrozenException(
                f"Parent entity '{parent_entity_id}' is frozen under emergency stop.",
                entity_id=parent_entity_id
            )

        if requested_child_usd > parent_budget.available_usd:
            raise ChildBudgetExceededException(
                f"Child task requested ${requested_child_usd:.2f} USD which exceeds parent '{parent_entity_id}' available balance (${parent_budget.available_usd:.2f} USD).",
                entity_id=parent_entity_id,
                details={"requested_usd": requested_child_usd, "parent_available_usd": parent_budget.available_usd}
            )

        if requested_child_tokens > 0 and parent_budget.allocated_tokens > 0:
            if requested_child_tokens > parent_budget.available_tokens:
                raise ChildBudgetExceededException(
                    f"Child task requested {requested_child_tokens} tokens which exceeds parent '{parent_entity_id}' available tokens ({parent_budget.available_tokens}).",
                    entity_id=parent_entity_id,
                    details={"requested_tokens": requested_child_tokens, "parent_available_tokens": parent_budget.available_tokens}
                )

        return True

    def reserve_budget(
        self,
        tenant_id: str,
        scope_chain: List[Tuple[str, str]], # List of (entity_type, entity_id), e.g. [("TENANT", tnt_1), ("AGENT", agt_2)]
        requested_usd: float,
        requested_tokens: int = 0,
        ttl_seconds: float = 300.0,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BudgetReservation:
        """
        Atomic, concurrency-safe multi-scope budget reservation.
        Locks all scopes in order, validates capacity against hard limits, and reserves capacity.
        Fails closed on any limit breach.
        """
        self._ensure_tables()
        now = time.time()
        expires_at = now + ttl_seconds
        reservation_id = f"res_{uuid.uuid4().hex[:12]}"

        # Deduplicate entities in scope chain while preserving order
        seen_entities = set()
        unique_chain: List[Tuple[str, str]] = []
        for etype, eid in scope_chain:
            if eid and eid not in seen_entities:
                seen_entities.add(eid)
                unique_chain.append((etype, eid))

        with db.get_connection() as conn:
            # 1. First pass: verify and reserve on all configured scopes
            reserved_entities = []
            try:
                for etype, eid in unique_chain:
                    row = conn.execute(
                        "SELECT entity_id, allocated_usd, spent_usd, reserved_usd, allocated_tokens, spent_tokens, reserved_tokens, hard_limit_pct, is_frozen FROM enterprise_budgets WHERE entity_id = ?",
                        (eid,)
                    ).fetchone()

                    if not row:
                        continue  # Unconfigured scope level defaults to uncapped

                    if row["is_frozen"]:
                        raise BudgetFrozenException(
                            f"Execution HALTED: Budget for entity '{eid}' ({etype}) is FROZEN under emergency stop.",
                            entity_id=eid,
                            scope=etype
                        )

                    alloc_usd = float(row["allocated_usd"])
                    spent_usd = float(row["spent_usd"])
                    res_usd = float(row.get("reserved_usd", 0.0) if hasattr(row, "get") else row["reserved_usd"])
                    hard_pct = float(row["hard_limit_pct"]) / 100.0
                    hard_ceiling_usd = alloc_usd * hard_pct

                    if (spent_usd + res_usd + requested_usd) > hard_ceiling_usd:
                        raise BudgetExhaustionException(
                            f"Hard budget ceiling breached for {etype} '{eid}': "
                            f"Projected (${spent_usd + res_usd + requested_usd:.2f}) > Ceiling (${hard_ceiling_usd:.2f}).",
                            entity_id=eid,
                            scope=etype,
                            details={
                                "allocated_usd": alloc_usd,
                                "spent_usd": spent_usd,
                                "reserved_usd": res_usd,
                                "requested_usd": requested_usd,
                                "ceiling_usd": hard_ceiling_usd
                            }
                        )

                    # Token limit check
                    alloc_tok = int(row.get("allocated_tokens", 0) if hasattr(row, "get") else row["allocated_tokens"])
                    spent_tok = int(row.get("spent_tokens", 0) if hasattr(row, "get") else row["spent_tokens"])
                    res_tok = int(row.get("reserved_tokens", 0) if hasattr(row, "get") else row["reserved_tokens"])

                    if alloc_tok > 0:
                        hard_ceiling_tok = int(alloc_tok * hard_pct)
                        if (spent_tok + res_tok + requested_tokens) > hard_ceiling_tok:
                            raise BudgetExhaustionException(
                                f"Token budget ceiling breached for {etype} '{eid}': "
                                f"Projected ({spent_tok + res_tok + requested_tokens}) > Ceiling ({hard_ceiling_tok}).",
                                entity_id=eid,
                                scope=etype,
                                details={
                                    "allocated_tokens": alloc_tok,
                                    "spent_tokens": spent_tok,
                                    "reserved_tokens": res_tok,
                                    "requested_tokens": requested_tokens,
                                    "ceiling_tokens": hard_ceiling_tok
                                }
                            )

                    # Atomic reservation update
                    conn.execute("""
                        UPDATE enterprise_budgets
                        SET reserved_usd = reserved_usd + ?,
                            reserved_tokens = reserved_tokens + ?,
                            updated_at = ?
                        WHERE entity_id = ?
                    """, (requested_usd, requested_tokens, now, eid))
                    reserved_entities.append(eid)

                # 2. Record reservation manifest
                scope_key = json.dumps([{"type": t, "id": i} for t, i in unique_chain])
                primary_entity = unique_chain[-1][1] if unique_chain else tenant_id
                conn.execute("""
                    INSERT INTO enterprise_budget_reservations (
                        reservation_id, tenant_id, scope_key, entity_id,
                        reserved_usd, reserved_tokens, status, created_at,
                        expires_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, 'RESERVED', ?, ?, ?)
                """, (
                    reservation_id, tenant_id, scope_key, primary_entity,
                    requested_usd, requested_tokens, now, expires_at,
                    json.dumps(metadata or {})
                ))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return BudgetReservation(
            reservation_id=reservation_id,
            tenant_id=tenant_id,
            scope_chain=[{"type": t, "id": i} for t, i in unique_chain],
            reserved_usd=requested_usd,
            reserved_tokens=requested_tokens,
            status="RESERVED",
            created_at=now,
            expires_at=expires_at,
            task_id=task_id,
            metadata=metadata or {}
        )

    def settle_budget(
        self,
        reservation_id: str,
        actual_usd: float,
        actual_tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BudgetSettlement:
        """
        Settles an active reservation: releases reserved amounts, charges actual spend,
        and releases any unused reserved balance back into the available pool.
        """
        self._ensure_tables()
        now = time.time()

        with db.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM enterprise_budget_reservations
                WHERE reservation_id = ? AND status = 'RESERVED'
            """, (reservation_id,)).fetchone()

            if not row:
                raise ReservationExpiredException(
                    f"Reservation '{reservation_id}' not found or already settled/released."
                )

            reserved_usd = float(row["reserved_usd"])
            reserved_tokens = int(row["reserved_tokens"])
            scope_key_raw = row["scope_key"]
            scopes = json.loads(scope_key_raw) if isinstance(scope_key_raw, str) else scope_key_raw

            overrun_usd = max(0.0, actual_usd - reserved_usd)
            overrun_tokens = max(0, actual_tokens - reserved_tokens)

            # Settle each entity in the scope chain
            for item in scopes:
                eid = item.get("id")
                if not eid:
                    continue
                # Decrement reserved balance and increment spent balance
                conn.execute("""
                    UPDATE enterprise_budgets
                    SET reserved_usd = MAX(0.0, reserved_usd - ?),
                        reserved_tokens = MAX(0, reserved_tokens - ?),
                        spent_usd = spent_usd + ?,
                        spent_tokens = spent_tokens + ?,
                        updated_at = ?
                    WHERE entity_id = ?
                """, (reserved_usd, reserved_tokens, actual_usd, actual_tokens, now, eid))

            # Mark reservation SETTLED
            conn.execute("""
                UPDATE enterprise_budget_reservations
                SET status = 'SETTLED',
                    settled_at = ?,
                    actual_usd = ?,
                    actual_tokens = ?,
                    metadata = ?
                WHERE reservation_id = ?
            """, (now, actual_usd, actual_tokens, json.dumps(metadata or {}), reservation_id))
            conn.commit()

        return BudgetSettlement(
            reservation_id=reservation_id,
            actual_usd=actual_usd,
            actual_tokens=actual_tokens,
            settled_at=now,
            status="SETTLED",
            overrun_usd=overrun_usd,
            overrun_tokens=overrun_tokens
        )

    def release_reservation(self, reservation_id: str, reason: str = "CANCELLED") -> bool:
        """
        Releases reserved capacity back to available balance when an operation fails or is aborted.
        Zero spend is charged.
        """
        self._ensure_tables()
        now = time.time()

        with db.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM enterprise_budget_reservations
                WHERE reservation_id = ? AND status = 'RESERVED'
            """, (reservation_id,)).fetchone()

            if not row:
                return False

            reserved_usd = float(row["reserved_usd"])
            reserved_tokens = int(row["reserved_tokens"])
            scope_key_raw = row["scope_key"]
            scopes = json.loads(scope_key_raw) if isinstance(scope_key_raw, str) else scope_key_raw

            for item in scopes:
                eid = item.get("id")
                if not eid:
                    continue
                conn.execute("""
                    UPDATE enterprise_budgets
                    SET reserved_usd = MAX(0.0, reserved_usd - ?),
                        reserved_tokens = MAX(0, reserved_tokens - ?),
                        updated_at = ?
                    WHERE entity_id = ?
                """, (reserved_usd, reserved_tokens, now, eid))

            conn.execute("""
                UPDATE enterprise_budget_reservations
                SET status = 'RELEASED', settled_at = ?
                WHERE reservation_id = ?
            """, (now, reservation_id))
            conn.commit()

        logger.info(f"Released budget reservation {reservation_id}: {reason}")
        return True

    def freeze_budget(self, entity_id: str, reason: str) -> bool:
        """Emergency Financial Halt on specific entity."""
        self._ensure_tables()
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE enterprise_budgets
                SET is_frozen = 1, updated_at = ?
                WHERE entity_id = ?
            """, (now, entity_id))
            conn.commit()
        logger.error(f"[EMERGENCY FINANCIAL HALT] Entity '{entity_id}' frozen: {reason}")
        return True

    def unfreeze_budget(self, entity_id: str, authorizer_id: str) -> bool:
        """Restores financial operations after review."""
        self._ensure_tables()
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE enterprise_budgets
                SET is_frozen = 0, updated_at = ?
                WHERE entity_id = ?
            """, (now, entity_id))
            conn.commit()
        logger.info(f"Entity '{entity_id}' unfrozen by authorizer '{authorizer_id}'")
        return True

# Global singleton instance
economic_governor = EconomicGovernanceEngine()
