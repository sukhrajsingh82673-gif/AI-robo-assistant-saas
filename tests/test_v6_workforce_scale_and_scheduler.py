"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Test Suite — Workforce Scheduler, Employee Health, & Tenant Resource Quotas
"""

import unittest
import uuid
import time
from core.workforce_scheduler import workforce_scheduler, PriorityTier
from core.employee_health_manager import employee_health_manager, HealthState
from core.tenant_resource_quota import tenant_quota_manager, TenantQuotaExceededError
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState, AuthorityScope

class TestV6WorkforceScaleAndScheduler(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_v6_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_v6_{uuid.uuid4().hex[:6]}"

    def test_workforce_scheduler_priority_and_dependency_resolution(self):
        """
        Verify that WorkforceScheduler executes CRITICAL tasks ahead of NORMAL tasks,
        and respects dependency fulfillment before task dispatch.
        """
        # Register an operational AI employee
        emp = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Scheduler Test Worker",
            role_tier="AI_SPECIALIST",
            template_id="tmpl_spec",
            version="1.0.0",
            department_id="OPERATIONS",
            initial_budget_usd=1000.0,
            authority=AuthorityScope(max_risk_class="MUTATING", max_single_spend_usd=500.0)
        )
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.EVALUATED, "eval", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.APPROVED, "exec", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.PROVISIONED, "sys", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ONBOARDED, "idp", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ACTIVE, "mgr", "live")

        parent_mid = f"miss_parent_{uuid.uuid4().hex[:6]}"
        child_mid = f"miss_child_{uuid.uuid4().hex[:6]}"

        # 1. Enqueue Dependency Parent Task (NORMAL priority)
        parent_task_id = workforce_scheduler.enqueue_mission(
            mission_id=parent_mid,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            department="OPERATIONS",
            required_capabilities=["DATA_ANALYSIS"],
            budget_usd=100.0,
            priority=PriorityTier.NORMAL
        )

        # 2. Enqueue Child Dependent Task (CRITICAL priority, but depends on parent)
        child_task_id = workforce_scheduler.enqueue_mission(
            mission_id=child_mid,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            department="OPERATIONS",
            required_capabilities=["DATA_ANALYSIS"],
            budget_usd=100.0,
            priority=PriorityTier.CRITICAL,
            dependencies=[parent_mid]
        )

        # 3. First schedule call: Parent is dispatched even though Child is CRITICAL,
        # because Child's dependency is unfulfilled.
        dispatched = workforce_scheduler.schedule_next_task(self.tenant_id)
        self.assertIsNotNone(dispatched)
        self.assertEqual(dispatched["mission_id"], parent_mid)

        # 4. Complete parent task
        workforce_scheduler.complete_task(parent_task_id, success=True)

        # 5. Second schedule call: Child is now unblocked and dispatched
        dispatched_child = workforce_scheduler.schedule_next_task(self.tenant_id)
        self.assertIsNotNone(dispatched_child)
        self.assertEqual(dispatched_child["mission_id"], child_mid)

    def test_employee_health_vitals_and_automatic_suspension(self):
        """
        Verify that repeated policy violations transition an employee
        into HealthState.SUSPENDED and trip automatic lifecycle suspension.
        """
        rogue = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Rogue Worker",
            role_tier="AI_SPECIALIST",
            template_id="tmpl_spec",
            version="1.0.0",
            department_id="OPERATIONS",
            initial_budget_usd=500.0
        )
        ai_employee_registry.advance_lifecycle(rogue.employee_id, EmployeeLifecycleState.EVALUATED, "eval", "ok")
        ai_employee_registry.advance_lifecycle(rogue.employee_id, EmployeeLifecycleState.APPROVED, "exec", "ok")
        ai_employee_registry.advance_lifecycle(rogue.employee_id, EmployeeLifecycleState.PROVISIONED, "sys", "ok")
        ai_employee_registry.advance_lifecycle(rogue.employee_id, EmployeeLifecycleState.ONBOARDED, "idp", "ok")
        ai_employee_registry.advance_lifecycle(rogue.employee_id, EmployeeLifecycleState.ACTIVE, "mgr", "live")
        emp_id = rogue.employee_id

        # Record clean missions
        h1 = employee_health_manager.record_mission_outcome(
            employee_id=emp_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            success=True,
            latency_ms=250.0,
            cost_usd=0.05
        )
        self.assertEqual(h1, HealthState.HEALTHY)

        # Incur Policy Violation 1
        h2 = employee_health_manager.record_mission_outcome(
            employee_id=emp_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            success=False,
            latency_ms=120.0,
            cost_usd=0.01,
            policy_violation=True
        )
        self.assertIn(h2, (HealthState.HEALTHY, HealthState.DEGRADED, HealthState.REVIEW_REQUIRED))

        # Incur Policy Violation 2 (Breaches threshold -> Automatic SUSPEND)
        h3 = employee_health_manager.record_mission_outcome(
            employee_id=emp_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            success=False,
            latency_ms=120.0,
            cost_usd=0.01,
            policy_violation=True
        )
        self.assertEqual(h3, HealthState.SUSPENDED)

        vitals = employee_health_manager.get_vitals(emp_id)
        self.assertEqual(vitals.policy_violations, 2)
        self.assertEqual(vitals.health_state, HealthState.SUSPENDED)

    def test_tenant_resource_quota_and_noisy_neighbor_containment(self):
        """
        Verify that Tenant A cannot exceed its active mission or token quota,
        guaranteeing fairness for Tenant B.
        """
        tenant_a = f"tnt_a_{uuid.uuid4().hex[:6]}"
        tenant_b = f"tnt_b_{uuid.uuid4().hex[:6]}"

        # Set tight quota on Tenant A: max 2 active missions
        tenant_quota_manager.set_tenant_quota(
            tenant_id=tenant_a,
            max_active_missions=2,
            max_tokens_per_minute=1000
        )
        # Normal quota on Tenant B: max 50 active missions
        tenant_quota_manager.set_tenant_quota(
            tenant_id=tenant_b,
            max_active_missions=50,
            max_tokens_per_minute=500000
        )

        # Tenant A reserves 2 slots
        self.assertTrue(tenant_quota_manager.check_and_reserve_mission_slot(tenant_a))
        self.assertTrue(tenant_quota_manager.check_and_reserve_mission_slot(tenant_a))

        # Tenant A attempts 3rd slot -> Quota exceeded error (Noisy neighbor stopped)
        with self.assertRaises(TenantQuotaExceededError):
            tenant_quota_manager.check_and_reserve_mission_slot(tenant_a)

        # Tenant B can still freely reserve slots without interference
        self.assertTrue(tenant_quota_manager.check_and_reserve_mission_slot(tenant_b))

        # Release Tenant A slot
        tenant_quota_manager.release_mission_slot(tenant_a)
        # Now Tenant A can reserve again
        self.assertTrue(tenant_quota_manager.check_and_reserve_mission_slot(tenant_a))

if __name__ == "__main__":
    unittest.main()
