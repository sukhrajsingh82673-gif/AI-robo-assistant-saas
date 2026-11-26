"""
ZONATA KPI & Goal Engine Subsystem
OpenCode Step 2I: Hierarchical KPI trees, snapshot proofs, thresholds, and Kaizen loops.
"""

import os
from core.db import db
from core.kpi.types import (
    KPIScopeLevel,
    KPIMetricType,
    KPIDirection,
    KPICadence,
    KPIStatus,
    DefectType,
    KaizenProposalType,
    KPIError,
    KPINotFoundError,
    InvalidKPIComputationError,
    MissingComputationProofError,
    KPIDefinitionCreateRequest,
    KPISnapshotModel,
    KPIAlertModel,
    KaizenDefectRecordModel,
    KaizenProposalModel,
)
from core.kpi.calculator import KPICalculator
from core.kpi.engine import KPIEngine, kpi_engine
from core.kpi.kaizen import KaizenEngine, kaizen_engine


def ensure_kpi_tables(conn=None):
    """Initializes the KPI and Kaizen database tables."""
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "migrations", "common", "0026_kpi_goal_engine.sql"
    )
    if os.path.exists(migration_path):
        with open(migration_path, "r", encoding="utf-8") as f:
            sql = f.read()
        if conn:
            conn.executescript(sql)
            conn.commit()
        else:
            with db.get_connection() as c:
                c.executescript(sql)
                c.commit()


__all__ = [
    "KPIScopeLevel",
    "KPIMetricType",
    "KPIDirection",
    "KPICadence",
    "KPIStatus",
    "DefectType",
    "KaizenProposalType",
    "KPIError",
    "KPINotFoundError",
    "InvalidKPIComputationError",
    "MissingComputationProofError",
    "KPIDefinitionCreateRequest",
    "KPISnapshotModel",
    "KPIAlertModel",
    "KaizenDefectRecordModel",
    "KaizenProposalModel",
    "KPICalculator",
    "KPIEngine",
    "kpi_engine",
    "KaizenEngine",
    "kaizen_engine",
    "ensure_kpi_tables",
]
