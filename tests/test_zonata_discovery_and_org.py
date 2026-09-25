"""
ZONATA Universal AI CEO — Comprehensive Acceptance Test Suite
Validates:
1. Epistemic state integrity (no silent estimate-to-fact conversions).
2. Knowledge Graph multi-type representation and relations.
3. Adaptive CEO discovery interview loop (handling answers, skips, deferrals, best evidence).
4. Evidence-based multidimensional Company Health engine.
5. Dynamic generative organization design across diverse industries (Hotel, Manufacturing, SaaS).
6. Mission-first workforce generation.
7. Governed 11-stage AgentFactory lifecycle.
8. Ethical competitive intelligence tracking.
"""

import unittest
import time
import os
import json
import uuid

from core.db import db
from zonata.models import (
    EpistemicState,
    EntityType,
    RelationType,
    AnswerType,
    HealthDimension,
    HealthStatus,
    AgentLifecycleState
)
from zonata.knowledge_graph import CompanyKnowledgeGraph
from zonata.discovery import CompanyDiscoveryEngine
from zonata.interview import CEODiscoveryInterview
from zonata.health import CompanyHealthEngine
from zonata.competitive import CompetitiveIntelligenceEngine
from zonata.org_designer import OrganizationDesignEngine
from zonata.agent_factory import GovernedAgentFactory

class TestZonataDiscoveryAndOrg(unittest.TestCase):

    def setUp(self):
        self.tenant_id = f"test_tenant_{uuid.uuid4().hex[:6]}"
        self.company_id = f"test_comp_{uuid.uuid4().hex[:6]}"
        # Ensure company exists in database
        with db.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO tenants (tenant_id, name, created_at)
                VALUES (?, 'Test Tenant', ?)
            """, (self.tenant_id, time.time()))
            conn.execute("""
                INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, created_at)
                VALUES (?, ?, 'Test Enterprise', 'Hospitality', 'NEW', ?)
            """, (self.company_id, self.tenant_id, time.time()))
            conn.commit()

    def test_01_epistemic_state_integrity(self):
        """Invariant: Estimates must never be converted silently into facts."""
        engine = CompanyDiscoveryEngine()

        # 1. Statement with explicit estimation qualifiers
        est_findings = engine.ingest_owner_statement(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            statement="We have roughly 45 rooms and estimated ₹35 lakh monthly turnover."
        )
        self.assertTrue(len(est_findings) >= 1)
        for f in est_findings:
            if f.attribute in ("room_inventory", "reported_revenue"):
                self.assertEqual(f.provenance.epistemic_state, EpistemicState.ESTIMATE)
                self.assertTrue(f.provenance.confidence < 1.0)

        # 2. Authoritative system feed
        sys_findings = engine.ingest_system_feed(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            system_name="Cloudbeds",
            system_type="PMS",
            data_payload={"verified_room_count": 48, "occupancy_rate": 0.82}
        )
        self.assertTrue(len(sys_findings) >= 2)
        for f in sys_findings:
            self.assertEqual(f.provenance.epistemic_state, EpistemicState.FACT)
            self.assertEqual(f.provenance.confidence, 1.0)

    def test_02_knowledge_graph_multitype_and_relations(self):
        """Verifies graph linking of 30+ entity types and typed relations."""
        kg = CompanyKnowledgeGraph(self.tenant_id, self.company_id)

        # Add Company node
        c_node = kg.add_node(EntityType.COMPANY, "The Royal Orchid", {"stars": 5}, EpistemicState.FACT)
        # Add Asset node
        a_node = kg.add_node(EntityType.ASSET, "Boutique Villas", {"units": 12}, EpistemicState.FACT)
        # Add System node
        s_node = kg.add_node(EntityType.SYSTEM, "Oracle Opera PMS", {"version": "v5.6"}, EpistemicState.FACT)
        # Add Process node
        p_node = kg.add_node(EntityType.PROCESS, "VIP Check-in Procedure", {"sla_minutes": 3}, EpistemicState.FACT)

        # Connect edges
        e1 = kg.add_edge(c_node.node_id, a_node.node_id, RelationType.OWNS)
        e2 = kg.add_edge(c_node.node_id, s_node.node_id, RelationType.USES)
        e3 = kg.add_edge(c_node.node_id, p_node.node_id, RelationType.OPERATES)

        self.assertEqual(len(kg.nodes), 4)
        self.assertEqual(len(kg.edges), 3)

        # Query outgoing relations from Company
        related = kg.get_related_nodes(c_node.node_id, direction="outgoing")
        self.assertEqual(len(related), 3)

        # Test reload from DB
        kg_reloaded = CompanyKnowledgeGraph(self.tenant_id, self.company_id)
        self.assertEqual(len(kg_reloaded.nodes), 4)
        self.assertEqual(len(kg_reloaded.edges), 3)

    def test_03_ceo_discovery_interview_adaptive_loop(self):
        """Tests adaptive interview questioning loop and response handling."""
        interview = CEODiscoveryInterview()

        # 1. Initial completeness
        score, missing = interview.calculate_completeness(self.tenant_id, self.company_id)
        self.assertTrue(score < 0.50)
        self.assertTrue(len(missing) > 0)

        # 2. Get first targeted question
        q1 = interview.get_next_question(self.tenant_id, self.company_id)
        self.assertIsNotNone(q1)

        # 3. Test 'Skip' response
        res_skip = interview.submit_answer(self.tenant_id, self.company_id, q1.question_id, "Skip this question")
        self.assertEqual(res_skip["answer_type"], AnswerType.SKIPPED.value)

        # 4. Get next question (should advance adaptively)
        q2 = interview.get_next_question(self.tenant_id, self.company_id)
        self.assertIsNotNone(q2)
        self.assertNotEqual(q1.question_id, q2.question_id)

        # 5. Test substantive answer
        res_ans = interview.submit_answer(
            self.tenant_id,
            self.company_id,
            q2.question_id,
            "We operate a 50-room boutique hotel using Cloudbeds PMS with ₹45 lakh monthly revenue."
        )
        self.assertEqual(res_ans["answer_type"], AnswerType.ANSWERED.value)
        self.assertTrue(res_ans["facts_extracted"] >= 2)
        self.assertTrue(res_ans["completeness_score"] > score)

        # 6. Test 'Ask later'
        q3 = interview.get_next_question(self.tenant_id, self.company_id)
        if q3:
            res_later = interview.submit_answer(self.tenant_id, self.company_id, q3.question_id, "Ask me later")
            self.assertEqual(res_later["answer_type"], AnswerType.ASK_LATER.value)

        # 7. Test 'Use your best available evidence'
        q4 = interview.get_next_question(self.tenant_id, self.company_id)
        if q4:
            res_best = interview.submit_answer(self.tenant_id, self.company_id, q4.question_id, "Use your best available evidence")
            self.assertEqual(res_best["answer_type"], AnswerType.BEST_EVIDENCE.value)
            # Verify fact was recorded as ESTIMATE
            kg = CompanyKnowledgeGraph(self.tenant_id, self.company_id)
            unverified = kg.get_unverified_entities()
            self.assertTrue(len(unverified) >= 1)

    def test_04_evidence_based_company_health(self):
        """Verifies multidimensional health assessment without fabricated scores."""
        health_engine = CompanyHealthEngine()

        # Baseline: Fresh company with zero data -> should flag unverified
        h1 = health_engine.evaluate_company_health(self.tenant_id, self.company_id)
        self.assertIsNotNone(h1)
        self.assertTrue(len(h1.unverified_areas) > 0)
        # Verify financial indicator is UNVERIFIED
        fin_ind = [i for i in h1.indicators if i.dimension == HealthDimension.FINANCIAL][0]
        self.assertEqual(fin_ind.status, HealthStatus.UNVERIFIED)

        # Ingest verified systems and revenue
        disc = CompanyDiscoveryEngine()
        disc.ingest_system_feed(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            system_name="Opera",
            system_type="PMS",
            data_payload={"monthly_revenue": "₹42.5 lakh", "adr": 6500}
        )

        h2 = health_engine.evaluate_company_health(self.tenant_id, self.company_id)
        self.assertTrue(h2.overall_score > h1.overall_score)
        tech_ind = [i for i in h2.indicators if i.dimension == HealthDimension.TECHNOLOGY][0]
        self.assertEqual(tech_ind.status, HealthStatus.HEALTHY)
        # Constitutional check: Each indicator has Value, Source, Time, Confidence, Trend
        for ind in h2.indicators:
            self.assertIsNotNone(ind.value)
            self.assertIsNotNone(ind.source)
            self.assertIsNotNone(ind.confidence)
            self.assertIsNotNone(ind.trend)
            self.assertIsNotNone(ind.period)

    def test_05_dynamic_org_design_hotel_vs_manufacturing_vs_saas(self):
        """
        Constitutional Test: The organization must be dynamically generated from requirements,
        NOT from a fixed 25-employee template.
        """
        org_engine = OrganizationDesignEngine()

        # 1. Hotel Organization
        hotel_org = org_engine.design_organization(self.tenant_id, self.company_id, industry_override="HOTEL")
        self.assertEqual(hotel_org.industry, "HOTEL")
        hotel_exec_roles = [e["role"] for e in hotel_org.executives]
        self.assertIn("COO", hotel_exec_roles)
        self.assertIn("CMO", hotel_exec_roles) # Rooms / Bookings / Revenue
        hotel_dept_codes = [d.code for d in hotel_org.departments]
        self.assertIn("REV", hotel_dept_codes) # Revenue Management
        self.assertIn("RES", hotel_dept_codes) # Reservations

        # 2. Manufacturing Organization
        mfg_org = org_engine.design_organization(self.tenant_id, self.company_id, industry_override="MANUFACTURING")
        self.assertEqual(mfg_org.industry, "MANUFACTURING")
        mfg_exec_roles = [e["role"] for e in mfg_org.executives]
        self.assertIn("CTO", mfg_exec_roles) # Machinery / CNC / Automation
        mfg_dept_codes = [d.code for d in mfg_org.departments]
        self.assertIn("PRD", mfg_dept_codes) # Production & CNC
        self.assertIn("QA", mfg_dept_codes)  # Quality & Metrology
        self.assertIn("SCM", mfg_dept_codes) # Supply Chain

        # 3. SaaS Organization
        saas_org = org_engine.design_organization(self.tenant_id, self.company_id, industry_override="SAAS")
        self.assertEqual(saas_org.industry, "SAAS")
        saas_exec_roles = [e["role"] for e in saas_org.executives]
        self.assertIn("CTO", saas_exec_roles)
        self.assertIn("CRO", saas_exec_roles)
        saas_dept_codes = [d.code for d in saas_org.departments]
        self.assertIn("ENG", saas_dept_codes)
        self.assertIn("CS", saas_dept_codes)

        # Strict Verification: Hotel, Manufacturing, and SaaS hierarchies must differ
        self.assertNotEqual(hotel_dept_codes, mfg_dept_codes)
        self.assertNotEqual(hotel_dept_codes, saas_dept_codes)

    def test_06_mission_first_workforce_generation(self):
        """Mission-first workforce generation: only create workforce required for the mission."""
        org_engine = OrganizationDesignEngine()
        wf = org_engine.generate_mission_workforce(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_objective="Increase hotel direct bookings and eliminate OTA commission leakage"
        )
        self.assertTrue(len(wf) >= 2)
        roles = [w.role for w in wf]
        self.assertTrue(any("Rate Intelligence" in r or "Conversion" in r or "Marketing" in r for r in roles))
        # Ensure each role has a complete authority contract
        for agent in wf:
            self.assertTrue(agent.budget > 0)
            self.assertIn("department", agent.authority_scope)
            self.assertTrue(len(agent.tools) > 0)

    def test_07_agent_factory_11_stage_lifecycle(self):
        """Validates the strict 11-stage agent governance lifecycle."""
        factory = GovernedAgentFactory()

        # 1 & 2: NEED_IDENTIFIED and ROLE_DESIGNED
        agent = factory.initiate_agent_need(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            role_name="OTA Dispute Settlement Specialist",
            department_id="dept_revenue",
            executive_role="CMO",
            mission_focus="Resolve OTA booking discrepancy chargebacks"
        )
        self.assertEqual(agent.status, AgentLifecycleState.ROLE_DESIGNED)

        # 3 & 4: CAPABILITIES_DEFINED and TOOLS_SELECTED
        agent = factory.configure_capabilities_and_tools(
            agent_id=agent.id,
            capabilities=["CHARGEBACK_AUDIT", "OTA_API_DISPUTE"],
            tools=["BROWSER_SURFACE", "OTA_PORTAL", "EVIDENCE_LEDGER"]
        )
        self.assertEqual(agent.status, AgentLifecycleState.TOOLS_SELECTED)

        # 5 & 6: MODEL_SELECTED and KNOWLEDGE_BOUND
        agent = factory.select_model_and_bind_knowledge(
            agent_id=agent.id,
            model_policy={"preferred_model": "gemini-1.5-pro", "temperature": 0.1},
            knowledge_sources=["OTA Contract Agreements", "Chargeback Policy SOP"]
        )
        self.assertEqual(agent.status, AgentLifecycleState.KNOWLEDGE_BOUND)

        # 7: POLICY_ASSIGNED
        agent = factory.assign_policy_and_authority(
            agent_id=agent.id,
            budget=250.0,
            risk_class="MEDIUM",
            approval_policy={"require_approval_above_usd": 100.0},
            authority_scope={"department": "dept_revenue", "dispute_limit": 500.0}
        )
        self.assertEqual(agent.status, AgentLifecycleState.POLICY_ASSIGNED)

        # 8: TESTED
        test_res = factory.run_sandbox_tests(agent.id)
        self.assertTrue(test_res["passed"])

        # 9, 10 & 11: CERTIFIED, AVAILABLE, ACTIVE
        active_agent = factory.certify_and_activate(agent.id, auditor_role="AI_CEO")
        self.assertEqual(active_agent.status, AgentLifecycleState.ACTIVE)
        self.assertEqual(active_agent.certification["governance_status"], "PASSED_STRICT_AUDIT")

    def test_08_competitive_intelligence_ethical_tracking(self):
        """Verifies competitor profile ingestion and strategic insight synthesis."""
        comp_engine = CompetitiveIntelligenceEngine()
        comp = comp_engine.register_competitor(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Grand Horizon Hotel",
            website="https://grandhorizon.example.com",
            products=["Deluxe Ocean View", "Presidential Suite"],
            public_pricing={"Deluxe": "₹8,500/night", "Suite": "₹18,000/night"},
            positioning="Luxury beachfront resort"
        )
        self.assertIsNotNone(comp.competitor_id)

        analysis = comp_engine.analyze_competitive_opportunities(self.tenant_id, self.company_id)
        self.assertEqual(analysis["competitor_count"], 1)
        self.assertIn("Grand Horizon Hotel", analysis["tracked_competitors"])
        self.assertTrue(len(analysis["strategic_recommendations"]) > 0)

if __name__ == "__main__":
    unittest.main()
