"""
ZONATA SOP Subsystem
OpenCode Step 2G: Verifiable Standard Operating Procedure Execution Kernel.
"""

import os
from core.db import db
from core.sop.types import (
    SOPStepType,
    SOPInstanceStatus,
    SOPVersionStatus,
    SOPStepReversibility,
    SOPStepOutcome,
    SOPError,
    SOPNotFoundError,
    SOPVersionNotFoundError,
    SOPNotExecutableError,
    SOPPreconditionFailedError,
    SOPPostconditionFailedError,
    SOPStepTimeoutError,
    SOPCompensationFailedError,
    SOPStepExecutionError,
    SOPStepDefinition,
    SOPDefinitionCreateRequest,
    SOPVersionCreateRequest,
    SOPRunRequest,
    SOPStepRecordModel,
)
from core.sop.definition import SOPDefinitionService, sop_definition_service
from core.sop.compliance import SOPComplianceCalculator, sop_compliance_calculator
from core.sop.executor import SOPConditionEvaluator, SOPExecutor, sop_executor


def ensure_sop_tables(conn=None):
    """Initializes the SOP execution tables."""
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "migrations", "common", "0024_sop_executor.sql"
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
    "SOPStepType",
    "SOPInstanceStatus",
    "SOPVersionStatus",
    "SOPStepReversibility",
    "SOPStepOutcome",
    "SOPError",
    "SOPNotFoundError",
    "SOPVersionNotFoundError",
    "SOPNotExecutableError",
    "SOPPreconditionFailedError",
    "SOPPostconditionFailedError",
    "SOPStepTimeoutError",
    "SOPCompensationFailedError",
    "SOPStepExecutionError",
    "SOPStepDefinition",
    "SOPDefinitionCreateRequest",
    "SOPVersionCreateRequest",
    "SOPRunRequest",
    "SOPStepRecordModel",
    "SOPDefinitionService",
    "sop_definition_service",
    "SOPComplianceCalculator",
    "sop_compliance_calculator",
    "SOPConditionEvaluator",
    "SOPExecutor",
    "sop_executor",
    "ensure_sop_tables",
]
