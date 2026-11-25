"""
Metered Usage Ledger and Cryptographic SHA-256 Chaining (Rule 79).
Every usage event is idempotent and linked to prior entries in an immutable hash chain.
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple


GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


@dataclass
class UsageRecord:
    entry_id: str
    tenant_id: str
    subscription_id: str
    metric: str  # ai_tokens, api_calls, storage_mb, seats
    quantity: int
    unit: str
    idempotency_key: str
    timestamp: float
    prev_hash: str
    record_hash: str


class UsageLedger:
    """
    Append-only usage event store with cryptographic chaining and deduplication.
    """

    def __init__(self):
        # tenant_id -> list of UsageRecord
        self._ledger: Dict[str, List[UsageRecord]] = {}
        # idempotency_key -> entry_id
        self._dedup: Dict[str, str] = {}

    def _compute_hash(
        self,
        prev_hash: str,
        tenant_id: str,
        metric: str,
        quantity: int,
        idempotency_key: str,
        timestamp: float,
    ) -> str:
        payload = f"{prev_hash}|{tenant_id}|{metric}|{quantity}|{idempotency_key}|{timestamp:.4f}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_usage(
        self,
        tenant_id: str,
        subscription_id: str,
        metric: str,
        quantity: int,
        unit: str,
        idempotency_key: str,
        timestamp: Optional[float] = None,
    ) -> UsageRecord:
        """
        Idempotently appends usage record to tenant chain.
        """
        # Deduplication check
        if idempotency_key in self._dedup:
            existing_id = self._dedup[idempotency_key]
            for r in self._ledger.get(tenant_id, []):
                if r.entry_id == existing_id:
                    return r

        ts = timestamp if timestamp is not None else time.time()
        tenant_chain = self._ledger.setdefault(tenant_id, [])

        prev_hash = tenant_chain[-1].record_hash if tenant_chain else GENESIS_HASH
        record_hash = self._compute_hash(prev_hash, tenant_id, metric, quantity, idempotency_key, ts)

        entry_id = f"usg_{len(tenant_chain) + 1}_{idempotency_key[:8]}"
        record = UsageRecord(
            entry_id=entry_id,
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            metric=metric,
            quantity=quantity,
            unit=unit,
            idempotency_key=idempotency_key,
            timestamp=ts,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )

        tenant_chain.append(record)
        self._dedup[idempotency_key] = entry_id
        return record

    def verify_chain_integrity(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """
        Verifies that every record in the tenant ledger cryptographically chains from genesis.
        """
        chain = self._ledger.get(tenant_id, [])
        if not chain:
            return True, None

        expected_prev = GENESIS_HASH
        for idx, r in enumerate(chain):
            if r.prev_hash != expected_prev:
                return False, f"Broken link at index {idx}: expected prev {expected_prev}, got {r.prev_hash}"

            recomputed = self._compute_hash(
                r.prev_hash, r.tenant_id, r.metric, r.quantity, r.idempotency_key, r.timestamp
            )
            if recomputed != r.record_hash:
                return False, f"Tampered hash at index {idx}: expected {recomputed}, got {r.record_hash}"

            expected_prev = r.record_hash

        return True, None

    def get_aggregated_metric(self, tenant_id: str, metric: str) -> int:
        return sum(r.quantity for r in self._ledger.get(tenant_id, []) if r.metric == metric)
