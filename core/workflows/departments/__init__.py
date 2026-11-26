"""
Cross-Department Process Workflows
==================================
Compiled enterprise Temporal durable execution workflows:
1. LeadToCashWorkflow (Marketing -> Sales -> Legal -> Finance)
2. ProcureToPayWorkflow (Operations -> Procurement -> QC -> Finance)
3. RecordToReportWorkflow (Finance -> Accounting -> Operations -> BI)
4. HireToRetireWorkflow (HR -> Hiring Team -> Payroll -> IT Security)
5. PlanToDeliverWorkflow (Sales -> Operations -> QC -> Logistics)
6. SupportToResolutionWorkflow (Support -> Engineering -> QA)
7. ComplianceAuditCycleWorkflow (Compliance -> IT Security -> HR -> Finance)
"""

from core.workflows.departments.base import (
    DepartmentBaseWorkflow,
    DepartmentWorkflowContext,
    WorkflowStepRecord,
    ReReadVerificationFailed,
    HumanApprovalRequiredHalt
)
from core.workflows.departments.lead_to_cash import LeadToCashWorkflow
from core.workflows.departments.procure_to_pay import ProcureToPayWorkflow
from core.workflows.departments.record_to_report import RecordToReportWorkflow
from core.workflows.departments.hire_to_retire import HireToRetireWorkflow
from core.workflows.departments.plan_to_deliver import PlanToDeliverWorkflow
from core.workflows.departments.support_to_resolution import SupportToResolutionWorkflow
from core.workflows.departments.compliance_audit_cycle import ComplianceAuditCycleWorkflow

__all__ = [
    "DepartmentBaseWorkflow",
    "DepartmentWorkflowContext",
    "WorkflowStepRecord",
    "ReReadVerificationFailed",
    "HumanApprovalRequiredHalt",
    "LeadToCashWorkflow",
    "ProcureToPayWorkflow",
    "RecordToReportWorkflow",
    "HireToRetireWorkflow",
    "PlanToDeliverWorkflow",
    "SupportToResolutionWorkflow",
    "ComplianceAuditCycleWorkflow"
]
