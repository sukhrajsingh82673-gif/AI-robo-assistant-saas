"""
Unit & Contract Tests for Step 7B: Department Platform, Models, Reconciler & Connector SDK.
==========================================================================================
"""

import pytest
from core.departments.base_port import DepartmentBasePort, PortHealthStatus
from core.departments.schema import (
    DepartmentPackManifest, DepartmentPackMetadata, DepartmentCapability, DepartmentPolicyRule
)
from core.departments.models import (
    DepartmentEntity, DepartmentMembership, DepartmentBudget, DepartmentPolicy,
    DepartmentEvent, DepartmentRepository
)
from core.reconciliation.base import Reconciler, DriftDetectedException
from core.connectors.base import BaseConnector, CircuitBreakerOpenException, TokenBucketRateLimiter, CircuitBreaker
from core.connectors.replay import FixtureReplayEngine


class DummyFinancePort(DepartmentBasePort):
    def health_check(self) -> PortHealthStatus:
        return PortHealthStatus(
            status="healthy",
            department_id=self.department_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            details={"ledger_synced": True}
        )

    def status(self):
        return {"active_jobs": 0, "status": "nominal"}

    def config_schema(self):
        return {"type": "object", "properties": {"api_endpoint": {"type": "string"}}}


def test_01_department_base_port():
    port = DummyFinancePort("dept_fin", "tenant_alpha", "co_india", {"api_endpoint": "https://api.internal"})
    health = port.health_check()
    assert health.status == "healthy"
    assert health.department_id == "dept_fin"

    # Audit tap
    evt = port.audit_tap("CLOSE_MONTH", "principal_cfo", {"period": "2026-10"}, gateway_approved=True)
    assert evt.action == "CLOSE_MONTH"
    assert evt.gateway_approved is True
    assert len(port.audit_log) == 1

    # Metric tap
    metric = port.metric_tap("ap_cycle_time_hours", 3.2, {"currency": "INR"})
    assert metric.value == 3.2
    assert len(port.metric_series) == 1


def test_02_department_pack_manifest_validation():
    manifest = DepartmentPackManifest(
        metadata=DepartmentPackMetadata(
            name="finance",
            display_name="Finance & Accounting",
            version="1.0.0",
            description="Core finance capabilities",
            owner_team="finance_ops"
        ),
        capabilities=[
            DepartmentCapability(
                capability_id="ap_matching",
                description="3-way AP matching",
                risk_level="high",
                reserved_human_decision=True
            )
        ],
        policies=[
            DepartmentPolicyRule(
                rule_id="pol_ap_thresh",
                rule_name="AP Gateway Approval Threshold",
                description="Invoices above 100k INR require CFO approval",
                rule_type="gateway_gate",
                parameters={"threshold_inr": 100000}
            )
        ],
        workflows=["wf_month_end_close", "wf_ap_invoice_match"]
    )
    assert manifest.manifest_version == "zonata.department-pack/v1"
    assert manifest.capabilities[0].reserved_human_decision is True


def test_03_canonical_models_and_budget_lifecycle():
    repo = DepartmentRepository()
    dept = DepartmentEntity(
        id="dept_fin_01",
        tenant_id="tenant_alpha",
        company_id="co_india",
        name="Finance Operations",
        code="FIN",
        lead_principal_id="user_cfo"
    )
    repo.create_department(dept)

    budget = DepartmentBudget(
        id="bgt_2026_q4",
        tenant_id="tenant_alpha",
        company_id="co_india",
        department_id=dept.id,
        currency="INR",
        total_budget=500000.0,
        valid_from="2026-10-01",
        valid_to="2026-12-31"
    )
    repo.record_budget(budget)

    assert budget.available_budget() == 500000.0

    # Commit spend
    assert budget.commit_spend(150000.0) is True
    assert budget.available_budget() == 350000.0

    # Commit exceeding spend fails
    assert budget.commit_spend(400000.0) is False

    # Execute spend
    budget.execute_spend(150000.0)
    assert budget.spend_committed == 0.0
    assert budget.spend_actual == 150000.0
    assert budget.available_budget() == 350000.0


def test_04_reconciler_and_drift_detection():
    reconciler = Reconciler[dict, dict](source_system="ZONATA_LEDGER", target_system="ERPNEXT")

    source_records = {
        "inv_001": {"amount": 5000.0, "status": "paid", "customer": "Cust A"},
        "inv_002": {"amount": 12000.0, "status": "unpaid", "customer": "Cust B"},
    }

    # Case 1: Identical target -> zero drift
    target_identical = {
        "inv_001": {"amount": 5000.0, "status": "paid", "customer": "Cust A"},
        "inv_002": {"amount": 12000.0, "status": "unpaid", "customer": "Cust B"},
    }
    res = reconciler.reconcile(source_records, target_identical)
    assert res.has_drift is False
    assert res.drifted_records == 0
    # Must not raise
    reconciler.raise_if_drifted(res)

    # Case 2: Drifted target (amount mismatch & missing record)
    target_drifted = {
        "inv_001": {"amount": 4500.0, "status": "paid", "customer": "Cust A"},  # Amount mismatch
        # inv_002 missing
    }
    res_drift = reconciler.reconcile(source_records, target_drifted)
    assert res_drift.has_drift is True
    assert res_drift.drifted_records == 2

    # Rule 59 Invariant: Never auto-corrects; raises DriftDetectedException
    with pytest.raises(DriftDetectedException):
        reconciler.raise_if_drifted(res_drift)


def test_05_connector_sdk_rate_limiting_and_replay():
    replay_engine = FixtureReplayEngine(replay_mode=True)
    replay_engine.register_fixture(
        service="ERPNext",
        method="GET",
        endpoint="/api/resource/Customer",
        payload=None,
        response={"status": 200, "data": [{"name": "Acme Corp"}]}
    )

    connector = BaseConnector(
        service_name="ERPNext",
        base_url="https://erp.internal",
        rate_limit_rps=50.0,
        replay_engine=replay_engine
    )

    # Replay fixture hit
    resp = connector.execute_request("GET", "/api/resource/Customer")
    assert resp["status"] == 200
    assert resp["data"][0]["name"] == "Acme Corp"

    # Circuit breaker mechanics
    breaker = CircuitBreaker(failure_threshold=2, recovery_time_seconds=1.0)
    assert breaker.can_execute() is True
    breaker.record_failure()
    assert breaker.can_execute() is True
    breaker.record_failure()
    # Now breaker is open
    assert breaker.state == "open"
    assert breaker.can_execute() is False
