"""
ZONATA Executive Brain and Workforce Trust Subsystem
OpenCode Step 2J: Directives, Plan Validation, Decision Records, Risk Register, and Trust Levels.
"""

import os
from core.db import db
from core.executive.types import (
    TrustLevel,
    DirectiveStatus,
    RiskTriggerType,
    RiskSeverity,
    ExecutiveError,
    ClarificationRequiredError,
    PlanValidationFailedError,
    NumberLockViolationError,
    PromotionThresholdNotMetError,
    UnauthorizedPromotionApproverError,
    EmployeeSuspendedError,
    DirectiveModel,
    PlanTaskSpec,
    PlanProjectSpec,
    PlanMissionSpec,
    PlanGraphModel,
    CEODecisionRecordModel,
    RiskRecordModel,
    EmployeeTrustModel,
)
from core.executive.interpreter import CommandInterpreter
from core.executive.planner import PlanValidator, CEOPlanner
from core.executive.decision import CEODecisionService
from core.executive.trust import WorkforceTrustService
from core.executive.risk import CompanyRiskService
from core.executive.reporting import NumberLockValidator, CEOReportingService
from core.executive.cadence import CEOCadenceEngine


def ensure_executive_tables(conn=None):
    """Initializes the Executive Brain and Workforce Trust database tables."""
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "migrations", "common", "0027_ai_ceo_workforce_trust.sql"
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
    "TrustLevel",
    "DirectiveStatus",
    "RiskTriggerType",
    "RiskSeverity",
    "ExecutiveError",
    "ClarificationRequiredError",
    "PlanValidationFailedError",
    "NumberLockViolationError",
    "PromotionThresholdNotMetError",
    "UnauthorizedPromotionApproverError",
    "EmployeeSuspendedError",
    "DirectiveModel",
    "PlanTaskSpec",
    "PlanProjectSpec",
    "PlanMissionSpec",
    "PlanGraphModel",
    "CEODecisionRecordModel",
    "RiskRecordModel",
    "EmployeeTrustModel",
    "CommandInterpreter",
    "PlanValidator",
    "CEOPlanner",
    "CEODecisionService",
    "WorkforceTrustService",
    "CompanyRiskService",
    "NumberLockValidator",
    "CEOReportingService",
    "CEOCadenceEngine",
    "ensure_executive_tables",
]
