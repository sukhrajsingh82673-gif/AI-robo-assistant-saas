"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — AI CEO Executive Operating Layer Test Suite
Validates persistent ExecutiveState, Corporate Objectives, Versioned Strategy,
Strategic Priorities, Department Objectives, Workforce Discovery, Governed Missions,
Budget Containment, Risk & Opportunity Management, First-Class UNKNOWN Handling,
Cryptographic Decision Records, Approval Queue, 11-Stage Control Loop, and
the Closed-Loop 22-Step Sovereign Acceptance Scenario.
"""

import unittest
import time
import json
import uuid
import hashlib

from core.db import db
from core.executive_state import ExecutiveStateManager, ExecutiveStateSnapshot
from core.corporate_objectives import CorporateObjectiveEngine, ObjectiveProvenance, ObjectiveStatus
from core.corporate_strategy import CorporateStrategyEngine, StrategyStatus
from core.strategic_priorities import StrategicPriorityEngine, PriorityLevel, ItemType
from core.department_objectives import DepartmentObjectiveEngine, ChiefOfficerRole
from core.executive_workforce import ExecutiveWorkforcePlanner, WorkforcePlanningTier
from core.executive_missions import ExecutiveMissionPlanner
from core.executive_resources import ExecutiveResourceAllocator, BudgetContainmentViolation
from core.executive_risk import ExecutiveRiskEngine, RiskSeverity, RiskStatus
from core.executive_opportunity import OpportunityEngine, OpportunityStatus
from core.ceo_observation import CEOObservationEngine, ObservationType, ObservationConfidence
from core.executive_decision import ExecutiveDecisionEngine, DecisionApprovalStatus
from core.ceo_performance import CEOPerformanceEngine
from core.executive_control_loop import ExecutiveControlLoop, ControlLoopStage
from core.ai_ceo_v8 import AICEOExecutiveOperatingLayer

class TestZonataV8ExecutiveOperatingLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tenant_id = f"tnt_v8_{uuid.uuid4().hex[:6]}"
        cls.company_id = f"comp_v8_{uuid.uuid4().hex[:6]}"

        # Seed isolated tenant and company
        with db.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at)
                VALUES (?, 'V8 Test Enterprise Tenant', 'ENTERPRISE', 'ACTIVE', ?)
            """, (cls.tenant_id, time.time()))
            conn.execute("""
                INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, currency, created_at)
                VALUES (?, ?, 'Royal Hotel Jaipur', 'Hospitality', 'EXISTING', 'OPERATIONAL', '₹', ?)
            """, (cls.company_id, cls.tenant_id, time.time()))
            conn.commit()

        cls.ceo = AICEOExecutiveOperatingLayer(cls.tenant_id, cls.company_id)

    # -------------------------------------------------------------------------
    # 1. Persistent Executive State
    # -------------------------------------------------------------------------
    def test_01_executive_state_persistence_and_versioning(self):
        """Validates structured persistent ExecutiveState and atomic version increments."""
        state_mgr = ExecutiveStateManager(self.tenant_id, self.company_id)
        snap1 = state_mgr.get_state()
        self.assertIsNotNone(snap1)
        self.assertEqual(snap1.tenant_id, self.tenant_id)
        self.assertEqual(snap1.company_id, self.company_id)
        self.assertEqual(snap1.company.get("company_name"), "Royal Hotel Jaipur")
        self.assertGreaterEqual(snap1.version, 1)

        # Update state
        snap2 = state_mgr.update_state({"finance": {"committed_budget": 45000.0}}, last_loop_stage="PLAN")
        self.assertEqual(snap2.version, snap1.version + 1)
        self.assertEqual(snap2.last_loop_stage, "PLAN")
        self.assertEqual(snap2.finance.get("committed_budget"), 45000.0)

    # -------------------------------------------------------------------------
    # 2. Corporate Objective Engine
    # -------------------------------------------------------------------------
    def test_02_corporate_objective_compilation_and_provenance(self):
        """Compiles raw intent into structured measurable dimensions with strict provenance."""
        obj_engine = CorporateObjectiveEngine(self.tenant_id, self.company_id)
        intent = "Increase hotel profitability during peak wedding season while maintaining guest service standards"
        obj = obj_engine.compile_intent_to_objective(
            raw_intent=intent,
            provenance=ObjectiveProvenance.OWNER_DEFINED
        )
        self.assertEqual(obj.provenance, ObjectiveProvenance.OWNER_DEFINED)
        self.assertIn("revpar", obj.target_dimensions)
        self.assertIn("guest_satisfaction_score", obj.target_dimensions)
        self.assertIn("contribution_margin", obj.target_dimensions)
        self.assertEqual(obj.status, ObjectiveStatus.ACTIVE)

        # Retrieve and verify persistence
        retrieved = obj_engine.get_objective(obj.objective_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, intent)

    # -------------------------------------------------------------------------
    # 3. Corporate Strategy & Versioning
    # -------------------------------------------------------------------------
    def test_03_corporate_strategy_formulation_and_versioning(self):
        """Ensures strategies are versioned and never overwrite historical receipts."""
        strat_engine = CorporateStrategyEngine(self.tenant_id, self.company_id)
        obj_id = f"obj_{uuid.uuid4().hex[:6]}"

        # Formulate initial version (1.0.0)
        strat = strat_engine.formulate_strategy_for_objective(
            objective_id=obj_id,
            title="Dynamic Peak Rate Strategy",
            rationale="Maximize rate yield on wedding dates",
            required_budget=50000.0
        )
        self.assertEqual(strat.version, "1.0.0")

        # Adjust strategy with evidence (1.0.0 -> 1.1.0)
        adjusted = strat_engine.adjust_strategy(
            strategy_id=strat.strategy_id,
            reason="Exceeded preliminary revenue target",
            evidence=["ev_test_audit_001"],
            adjusted_budget=60000.0
        )
        self.assertEqual(adjusted.version, "1.1.0")
        self.assertEqual(adjusted.required_budget, 60000.0)

        # Audit receipts must preserve history
        versions = strat_engine.get_strategy_versions(strat.strategy_id)
        self.assertEqual(len(versions), 2)
        self.assertIsNone(versions[0].previous_version)
        self.assertEqual(versions[0].new_version, "1.0.0")
        self.assertEqual(versions[1].previous_version, "1.0.0")
        self.assertEqual(versions[1].new_version, "1.1.0")

    # -------------------------------------------------------------------------
    # 4. Strategic Priorities & Decision Record Requirement
    # -------------------------------------------------------------------------
    def test_04_strategic_priority_management_with_decision_receipt(self):
        """Priority shifts must produce an immutable ExecutiveDecisionRecord."""
        prio_engine = StrategicPriorityEngine(self.tenant_id, self.company_id)
        item_id = f"strat_{uuid.uuid4().hex[:6]}"

        res = prio_engine.set_priority(
            item_type=ItemType.STRATEGY,
            item_id=item_id,
            new_priority=PriorityLevel.P0,
            reason="Existential competitive threat in local market",
            evidence_ref="ev_market_comp_001"
        )
        self.assertEqual(res["new_priority"], PriorityLevel.P0)
        self.assertIsNotNone(res["decision_record_id"])

        # Verify decision record was written
        dec_engine = ExecutiveDecisionEngine(self.tenant_id, self.company_id)
        dec = dec_engine.get_decision(res["decision_record_id"])
        self.assertIsNotNone(dec)
        self.assertEqual(dec.decision_type, "PRIORITY_UPDATE")
        self.assertEqual(dec.selected_option, PriorityLevel.P0)

    # -------------------------------------------------------------------------
    # 5. Department Objectives & Chief Officer Ownership
    # -------------------------------------------------------------------------
    def test_05_department_objective_decomposition(self):
        """Decomposes corporate objective into bounded Chief Officer departments."""
        dept_engine = DepartmentObjectiveEngine(self.tenant_id, self.company_id)
        corp_id = f"obj_{uuid.uuid4().hex[:6]}"
        dept_objs = dept_engine.derive_department_objectives(
            corporate_objective_id=corp_id,
            corporate_title="Hotel Peak Season Optimization",
            total_budget=50000.0
        )
        self.assertEqual(len(dept_objs), 5)
        depts = [d.department for d in dept_objs]
        self.assertIn("REVENUE", depts)
        self.assertIn("OPERATIONS", depts)
        self.assertIn("MARKETING", depts)
        self.assertIn("FINANCE", depts)
        self.assertIn("TECHNOLOGY", depts)

        # Verify budgets sum to total
        total_allocated = sum(d.allocated_budget for d in dept_objs)
        self.assertEqual(round(total_allocated, 2), 50000.0)

    # -------------------------------------------------------------------------
    # 6. Executive Workforce Planning & Discovery Order
    # -------------------------------------------------------------------------
    def test_06_workforce_planning_canonical_discovery_order(self):
        """Validates 6-tier workforce discovery: existing specialists/employees checked first."""
        wf_planner = ExecutiveWorkforcePlanner(self.tenant_id, self.company_id)
        # 1. Specialist matching discovery
        plan_res = wf_planner.plan_workforce_for_department_objective(
            department="GROWTH",
            objective_id="obj_test_01",
            objective_title="Outbound Sales Pipeline",
            required_capabilities=["Sales", "SDR"],
            budget_allocated=12000.0
        )
        self.assertIsNotNone(plan_res.plan_id)
        self.assertEqual(plan_res.selected_tier, WorkforcePlanningTier.EXISTING_SPECIALIST)
        self.assertGreater(len(plan_res.assigned_worker_ids), 0)

        # 2. Unknown capability gap identification
        gap_plan = wf_planner.plan_workforce_for_department_objective(
            department="QUANTUM",
            objective_id="obj_test_gap",
            objective_title="Quantum Physics Teleportation",
            required_capabilities=["QUANTUM_TELEPORTATION"],
            budget_allocated=5000.0
        )
        self.assertTrue(gap_plan.workforce_gap_identified)
        self.assertEqual(gap_plan.selected_tier, WorkforcePlanningTier.NEW_CAPABILITY_REQUEST)

    # -------------------------------------------------------------------------
    # 7. Governed Result-Oriented Missions
    # -------------------------------------------------------------------------
    def test_07_result_oriented_mission_execution_and_verification(self):
        """Enforces TASK_SUCCESS != BUSINESS_OUTCOME with physical cryptographic digest."""
        msn_planner = ExecutiveMissionPlanner(self.tenant_id, self.company_id)
        msn = msn_planner.create_mission(
            objective_id="obj_test_02",
            department="OPERATIONS",
            manager="CHIEF_OPERATING_OFFICER",
            employee="ops_lead_01",
            title="Front Desk Wedding Check-in Streamlining",
            expected_output="Digital check-in kiosk deployed",
            expected_business_outcome="Average wait time < 3 minutes",
            kpi={"wait_time_mins": 3.0},
            kra=["Front desk operations"],
            acceptance_criteria=["Zero check-in queues"],
            budget=4000.0
        )
        self.assertEqual(msn.status, "EXECUTE")

        # Complete with physical SHA-256 evidence
        ev_data = {"check_in_timestamps": [10, 12, 14], "measured_wait_min": 2.4}
        ev_digest = hashlib.sha256(json.dumps(ev_data, sort_keys=True).encode()).hexdigest()

        completed = msn_planner.record_mission_completion(
            mission_id=msn.mission_id,
            actual_output="Kiosk active and serving arrivals",
            actual_outcome="Average arrival wait reduced to 2.4 mins",
            evidence_digest=ev_digest
        )
        self.assertEqual(completed.status, "COMPLETED")
        self.assertEqual(completed.outcome_status, "VERIFIED_ACHIEVED")
        self.assertIn(ev_digest[:16], completed.verified_outcome)

    # -------------------------------------------------------------------------
    # 8. Hierarchical Budget Containment
    # -------------------------------------------------------------------------
    def test_08_budget_hierarchy_and_containment_violation_defense(self):
        """Enforces child allocation <= parent limit; blocks overdraft escalation."""
        allocator = ExecutiveResourceAllocator(self.tenant_id, self.company_id)

        # Parent allocation: Company
        parent = allocator.allocate_budget(
            scope_type="COMPANY",
            scope_id="comp_root",
            requested_budget=100000.0
        )

        # Valid child: Department
        child = allocator.allocate_budget(
            scope_type="DEPARTMENT",
            scope_id="dept_revenue",
            requested_budget=40000.0,
            parent_allocation_id=parent.allocation_id
        )
        self.assertEqual(child.budget_limit, 40000.0)

        # Overdraft child: Exceeds remaining parent budget (100k - 40k = 60k remaining)
        with self.assertRaises(BudgetContainmentViolation):
            allocator.allocate_budget(
                scope_type="DEPARTMENT",
                scope_id="dept_marketing",
                requested_budget=70000.0,  # 40k + 70k = 110k > 100k
                parent_allocation_id=parent.allocation_id
            )

    # -------------------------------------------------------------------------
    # 9. Risk & Opportunity Engines
    # -------------------------------------------------------------------------
    def test_09_risk_and_opportunity_governance(self):
        """Identifies and tracks risks and commercial opportunities."""
        risk_eng = ExecutiveRiskEngine(self.tenant_id, self.company_id)
        risk = risk_eng.identify_risk(
            category="OPERATIONAL",
            title="Housekeeping shortage on peak wedding weekend",
            description="High occupancy may strain room turnaround",
            probability=0.8,
            impact=0.7,
            owner="CHIEF_OPERATING_OFFICER",
            mitigation="Pre-contract temporary banquet cleaning staff"
        )
        self.assertEqual(risk.severity, RiskSeverity.HIGH)

        opp_eng = OpportunityEngine(self.tenant_id, self.company_id)
        opp = opp_eng.discover_opportunity(
            title="Premium Bridal Suite Add-on Package",
            source="MARKET_ANALYSIS",
            estimated_value=85000.0,
            confidence=0.85
        )
        self.assertEqual(opp.status, OpportunityStatus.DISCOVERED)

    # -------------------------------------------------------------------------
    # 10. Observation Telemetry & First-Class UNKNOWN Handling
    # -------------------------------------------------------------------------
    def test_10_observation_telemetry_and_first_class_unknown_handling(self):
        """Missing or unverifiable metrics MUST yield first-class UNKNOWN state."""
        obs_eng = CEOObservationEngine(self.tenant_id, self.company_id)

        telemetry = {
            "revpar": {"baseline": 3800.0, "target": 4500.0, "actual": 4650.0},
            "unreachable_metric": {"baseline": 100.0, "target": 120.0, "actual": None}
        }
        observations = obs_eng.scan_kpi_deviations(telemetry)
        types = [o.observation_type for o in observations]
        self.assertIn(ObservationType.NORMAL, types)
        self.assertIn(ObservationType.UNKNOWN, types)

        unknown_obs = [o for o in observations if o.observation_type == ObservationType.UNKNOWN][0]
        self.assertEqual(unknown_obs.confidence, ObservationConfidence.UNKNOWN)
        self.assertEqual(unknown_obs.category, "KPI_DATA_GAP")

    # -------------------------------------------------------------------------
    # 11. Executive Decisions & Human Owner Approval Queue
    # -------------------------------------------------------------------------
    def test_11_executive_decisions_and_approval_queue(self):
        """High-risk financial decisions (> ₹50,000) automatically route to Owner Approval."""
        dec_eng = ExecutiveDecisionEngine(self.tenant_id, self.company_id)

        decision, approval = dec_eng.formulate_and_evaluate_decision(
            title="Major Ballroom Renovation Contract",
            decision_type="CAPITAL_EXPENDITURE",
            problem_statement="Upgrade ballroom AV for wedding season",
            alternatives_considered=["Vendor A ₹150,000", "Vendor B ₹180,000"],
            selected_option="Vendor A ₹150,000",
            rationale="Better warranty and SLA",
            constraints={"budget_cap": 200000.0},
            authority_required="OWNER_EXECUTIVE",
            evidence_source="PROCUREMENT_TENDERS",
            evidence_data={"tender_id": "TND_2026_01", "quotes": [150000, 180000]},
            financial_impact_inr=150000.0
        )
        self.assertEqual(decision.approval_status, DecisionApprovalStatus.PENDING_APPROVAL)
        self.assertIsNotNone(approval)
        self.assertEqual(approval.status, "PENDING")

        # Owner approves
        resolved_dec = dec_eng.resolve_approval(
            approval_id=approval.approval_id,
            approved=True,
            reason="Approved after tender review by Owner"
        )
        self.assertEqual(resolved_dec.approval_status, DecisionApprovalStatus.APPROVED)
        self.assertEqual(resolved_dec.execution_status, "READY_TO_EXECUTE")

    # -------------------------------------------------------------------------
    # 12. 11-Stage Executive Control Loop
    # -------------------------------------------------------------------------
    def test_12_executive_control_loop_single_tick_and_full_cycle(self):
        """Validates persistent 11-stage state machine transitions."""
        loop = ExecutiveControlLoop(self.tenant_id, self.company_id)

        # Single tick
        tick_res = loop.tick(stage_override=ControlLoopStage.OBSERVE)
        self.assertEqual(tick_res.completed_stage, ControlLoopStage.OBSERVE)
        self.assertEqual(tick_res.next_stage, ControlLoopStage.ASSESS)
        self.assertEqual(tick_res.status, "SUCCESS")

        # Full cycle traversal
        cycle_res = loop.run_full_cycle()
        self.assertEqual(len(cycle_res), 11)
        stages_traversed = [r.completed_stage for r in cycle_res]
        self.assertEqual(stages_traversed, [
            ControlLoopStage.OBSERVE,
            ControlLoopStage.ASSESS,
            ControlLoopStage.PRIORITIZE,
            ControlLoopStage.PLAN,
            ControlLoopStage.DELEGATE,
            ControlLoopStage.EXECUTE,
            ControlLoopStage.MONITOR,
            ControlLoopStage.VERIFY,
            ControlLoopStage.EVALUATE,
            ControlLoopStage.ADJUST,
            ControlLoopStage.REPORT,
        ])

    # -------------------------------------------------------------------------
    # 13. Complete 22-Step Closed-Loop Sovereign Scenario
    # -------------------------------------------------------------------------
    def test_13_closed_loop_sovereign_acceptance_scenario(self):
        """Validates the complete 22-step Royal Hotel Jaipur profitability closed loop."""
        res = self.ceo.execute_closed_loop_scenario(
            owner_goal="Increase Royal Hotel Jaipur profitability during peak wedding season while maintaining guest-service standards."
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["scenario"], "ROYAL_HOTEL_JAIPUR_PROFITABILITY")
        self.assertEqual(res["strategy_version"], "1.1.0")
        self.assertGreaterEqual(len(res["audit_trail"]), 12)
        self.assertEqual(res["execution_classification"], "LOCAL_REAL_EXECUTION")

    # -------------------------------------------------------------------------
    # 14. CEO Natural Language Chat Interface
    # -------------------------------------------------------------------------
    def test_14_ceo_natural_language_chat_interface(self):
        """Interacts with CEO via structured natural language queries."""
        q1 = self.ceo.chat_query("How is the company performing?")
        self.assertEqual(q1["intent"], "PERFORMANCE_QUERY")
        self.assertIn("Operational Rating", q1["answer"])

        q2 = self.ceo.chat_query("What are our biggest KPI gaps?")
        self.assertEqual(q2["intent"], "KPI_DEVIATION_QUERY")

        q3 = self.ceo.chat_query("Which department is overloaded?")
        self.assertEqual(q3["intent"], "DEPARTMENT_CAPACITY_QUERY")

    # -------------------------------------------------------------------------
    # 15. Tenant & Company Isolation
    # -------------------------------------------------------------------------
    def test_15_tenant_and_company_isolation(self):
        """Cross-tenant queries must return zero records; complete security boundary."""
        other_tenant = f"tnt_other_{uuid.uuid4().hex[:6]}"
        with db.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at)
                VALUES (?, 'Other Tenant', 'ENTERPRISE', 'ACTIVE', ?)
            """, (other_tenant, time.time()))
            conn.commit()

        other_ceo = AICEOExecutiveOperatingLayer(other_tenant, self.company_id)

        # Other tenant queries should not see our objectives or strategies
        other_objs = other_ceo.objective_engine.get_objectives()
        self.assertEqual(len(other_objs), 0)

        other_strats = other_ceo.strategy_engine.get_active_strategies()
        self.assertEqual(len(other_strats), 0)

if __name__ == "__main__":
    unittest.main()
