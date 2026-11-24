"""
Generic Reconciliation Engine (ZONATA Step 7 Department Platform)
==================================================================
Adheres to:
- Rule 59: Systems of Record are Ports (Drift Detection)
- Invariant: Drift is never auto-corrected silently; it triggers structured alerts.
"""

from typing import TypeVar, Generic, Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

T = TypeVar("T")  # Source / Primary system record type
U = TypeVar("U")  # Target / Secondary system record type


class DriftDifference(BaseModel):
    field: str
    source_val: Any
    target_val: Any
    severity: str = "warning"  # 'warning', 'critical'
    description: str


class ReconciliationResult(BaseModel):
    reconciliation_id: str
    reconciled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_system: str
    target_system: str
    total_source_records: int
    total_target_records: int
    matched_records: int
    drifted_records: int
    differences: List[DriftDifference] = Field(default_factory=list)
    has_drift: bool = False


class DriftDetectedException(Exception):
    """Raised when drift between authoritative source and mirror exceeds tolerance."""
    def __init__(self, result: ReconciliationResult):
        self.result = result
        super().__init__(
            f"Drift detected between {result.source_system} and {result.target_system}: "
            f"{result.drifted_records} records drifted, {len(result.differences)} field mismatches."
        )


class Reconciler(Generic[T, U]):
    """Generic base class for scheduled or on-demand cross-system reconciliation."""

    def __init__(self, source_system: str, target_system: str, tolerance: float = 0.0):
        self.source_system = source_system
        self.target_system = target_system
        self.tolerance = tolerance

    def compare_records(self, source_record: T, target_record: U) -> List[DriftDifference]:
        """Subclasses implement specific field-by-field or hash comparison logic."""
        diffs: List[DriftDifference] = []
        s_dict = source_record if isinstance(source_record, dict) else getattr(source_record, "__dict__", {})
        t_dict = target_record if isinstance(target_record, dict) else getattr(target_record, "__dict__", {})

        for key in set(s_dict.keys()).union(set(t_dict.keys())):
            sv = s_dict.get(key)
            tv = t_dict.get(key)
            if sv != tv:
                diffs.append(DriftDifference(
                    field=key,
                    source_val=sv,
                    target_val=tv,
                    severity="critical" if key in ("amount", "balance", "status", "tax_id") else "warning",
                    description=f"Field {key} mismatch: {sv} != {tv}"
                ))
        return diffs

    def reconcile(self, source_records: Dict[str, T], target_records: Dict[str, U]) -> ReconciliationResult:
        import uuid
        matched = 0
        drifted = 0
        all_diffs: List[DriftDifference] = []

        all_keys = set(source_records.keys()).union(set(target_records.keys()))
        for key in all_keys:
            if key not in source_records:
                drifted += 1
                all_diffs.append(DriftDifference(
                    field="record_presence",
                    source_val=None,
                    target_val=key,
                    severity="critical",
                    description=f"Record {key} missing in source system {self.source_system}"
                ))
            elif key not in target_records:
                drifted += 1
                all_diffs.append(DriftDifference(
                    field="record_presence",
                    source_val=key,
                    target_val=None,
                    severity="critical",
                    description=f"Record {key} missing in target system {self.target_system}"
                ))
            else:
                diffs = self.compare_records(source_records[key], target_records[key])
                if diffs:
                    drifted += 1
                    all_diffs.extend(diffs)
                else:
                    matched += 1

        has_drift = drifted > 0
        return ReconciliationResult(
            reconciliation_id=f"rec_{uuid.uuid4().hex[:12]}",
            source_system=self.source_system,
            target_system=self.target_system,
            total_source_records=len(source_records),
            total_target_records=len(target_records),
            matched_records=matched,
            drifted_records=drifted,
            differences=all_diffs,
            has_drift=has_drift
        )

    def raise_if_drifted(self, result: ReconciliationResult) -> None:
        """Enforces Rule 59: Never auto-correct; raise exception to halt or alert."""
        if result.has_drift:
            raise DriftDetectedException(result)
