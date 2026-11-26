"""
Tests for Step 7L: Cross-Department Process Workflows
====================================================
Adheres to:
- Rule 58: Preservation of Steps 1-6 baseline.
- Rule 59: Independent re-read verification invariant after state mutations.
- Rule 61: Statutory cited calculation rules (India GST, statutory payroll).
- Rule 62: Mandatory human approval gates (quotes > 20%, compensation, procurement awards, contract signature, fraud release).
- Rule 63: Counterfactual fairness disparity audit bounds [0.95, 1.05].
- Rule 64: Consent verification before outreach.
- Rule 65: Semantic layer query invariants.
"""

import pytest
from core.workflows.departments.base import (
    DepartmentWorkflowContext,
    HumanApprovalRequiredHalt,
    ReReadVerificationFailed
)
from core.workflows.departments.lead_to_cash import LeadToCashWorkflow
from core.workflows.departments.procure_to_pay import ProcureToPayWorkflow
from core.workflows.departments.record_to_report import RecordToReportWorkflow
from core.workflows.departments.hire_to_retire import HireToRetireWorkflow
from core.workflows.departments.plan_to_deliver import PlanToDeliverWorkflow
from core.workflows.departments.support_to_resolution import SupportToResolutionWorkflow
from core.workflows.departments.compliance_audit_cycle import ComplianceAuditCycleWorkflow


def test_01_lead_to_cash_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_alpha",
        company_id="comp_1",
        workflow_name="lead_to_cash"
    )
    wf = LeadToCashWorkflow()
    data = {
        "lead": {
            "lead_id": "l_10",
            "email": "buyer@enterprise.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "company_name": "MegaCorp",
            "has_express_opt_in": True
        },
        "quote": {"unit_price": 500.0, "quantity": 10, "discount_pct": 10.0},
        "contract": {"signature_token": "sig_usr_approved_9921"}
    }
    result = wf.execute(ctx, data)
    assert result["status"] == "COMPLETED"
    assert result["cash_collected"] > 0
    assert len(result["irn"]) == 64
    assert any(s.re_read_verified for s in ctx.steps)


def test_02_lead_to_cash_halt_on_high_discount_without_approval():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_alpha",
        company_id="comp_1",
        workflow_name="lead_to_cash"
    )
    wf = LeadToCashWorkflow()
    data = {
        "lead": {
            "lead_id": "l_11",
            "email": "buyer2@enterprise.com",
            "first_name": "Bob",
            "last_name": "Jones",
            "company_name": "MegaCorp",
            "has_express_opt_in": True
        },
        "quote": {"unit_price": 500.0, "quantity": 10, "discount_pct": 25.0},  # > 20% discount without approval token
        "contract": {"signature_token": "sig_token_123"}
    }
    with pytest.raises(HumanApprovalRequiredHalt) as exc_info:
        wf.execute(ctx, data)
    assert "manager approval token required" in str(exc_info.value)


def test_03_procure_to_pay_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_beta",
        company_id="comp_2",
        workflow_name="procure_to_pay"
    )
    wf = ProcureToPayWorkflow()
    data = {
        "vendor_id": "VEND-100",
        "vendor_name": "Precision Castings GmbH",
        "vendor_country": "DE",
        "award_approval_token": "token_award_signed_by_cpo_123",
        "defects_found": 0,
        "vendor_under_fraud_hold": False
    }
    result = wf.execute(ctx, data)
    assert result["status"] == "COMPLETED"
    assert result["amount_paid"] == 50000.0


def test_04_procure_to_pay_sanctions_freeze():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_beta",
        company_id="comp_2",
        workflow_name="procure_to_pay"
    )
    wf = ProcureToPayWorkflow()
    data = {
        "vendor_id": "VEND-666",
        "vendor_name": "Al-Barakaat Trading Company",
        "vendor_country": "SO",
        "award_approval_token": "token_123"
    }
    result = wf.execute(ctx, data)
    assert result["status"] == "HALTED"
    assert "Sanctions hit detected" in result["reason"]


def test_05_record_to_report_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_gamma",
        company_id="comp_3",
        workflow_name="record_to_report"
    )
    wf = RecordToReportWorkflow()
    result = wf.execute(ctx, {"period": "2026-11"})
    assert result["status"] == "COMPLETED"
    assert result["locked"] is True
    assert result["metrics"]["arr"] == 540000.0
    assert result["metrics"]["ccc"] == 45.0


def test_06_hire_to_retire_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_delta",
        company_id="comp_4",
        workflow_name="hire_to_retire"
    )
    wf = HireToRetireWorkflow()
    data = {
        "comp_approval_token": "GATEWAY-PAY-SIG-9900"
    }
    result = wf.execute(ctx, data)
    assert result["status"] == "COMPLETED"
    assert len(result["audit_hash"]) == 64


def test_07_plan_to_deliver_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_epsilon",
        company_id="comp_5",
        workflow_name="plan_to_deliver"
    )
    wf = PlanToDeliverWorkflow()
    result = wf.execute(ctx, {"order_quantity": 10.0})
    assert result["status"] == "COMPLETED"
    assert result["delivery_status"] == "delivered"
    assert "DHL" in result["tracking_number"]


def test_08_support_to_resolution_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_zeta",
        company_id="comp_6",
        workflow_name="support_to_resolution"
    )
    wf = SupportToResolutionWorkflow()
    data = {
        "ticket_id": "TICK-101",
        "subject": "Need help with billing invoice discrepancy",
        "body": "Could you clarify the billing calculation?",
        "human_approval_token": "token_agent_human_appr_101"
    }
    result = wf.execute(ctx, data)
    assert result["status"] == "COMPLETED"
    assert result["resolution"] == "RESOLVED"


def test_09_compliance_audit_cycle_happy_path():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_eta",
        company_id="comp_7",
        workflow_name="compliance_audit_cycle"
    )
    wf = ComplianceAuditCycleWorkflow()
    result = wf.execute(ctx, {"cycle_id": "audit_2026_q4"})
    assert result["status"] == "COMPLETED"
    assert len(result["seal_hash"]) == 64
    assert result["controls_audited"] > 0


def test_10_rule_59_re_read_mutation_check():
    ctx = DepartmentWorkflowContext(
        tenant_id="ten_test",
        company_id="comp_test",
        workflow_name="test_rule_59"
    )
    wf = LeadToCashWorkflow()
    # Mock a corrupted database where re-read returns mismatched value
    fake_db = {"ent_1": {"status": "PENDING"}}
    with pytest.raises(ReReadVerificationFailed) as exc_info:
        wf.verify_re_read(
            step_name="Test Step",
            entity_id="ent_1",
            expected_values={"status": "PAID"},
            re_read_fn=lambda eid: fake_db.get(eid)
        )
    assert "Rule 59 Re-Read Mismatch" in str(exc_info.value)
