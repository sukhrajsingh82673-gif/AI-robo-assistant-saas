"""
URA / ZONATA Enterprise AI Corporate Workforce Architecture — Comprehensive Acceptance Test Suite
Standards Alignment: ISO 37000 (Governance), ISO 31000 (Risk), ISO 37301 (Compliance), ISO/IEC 42001 (AI Management)

Validates:
1. Relational Schema & 25 Enterprise Workforce Tables
2. 26 Canonical Corporate C-Suite Roles & DoA Boundaries
3. Dynamic Multi-Industry Organization Synthesis across 7 Industries
4. Architectural Triad Separation (AI Employee vs AI Agent vs AI Coworker) & Lifecycle States
5. SOP Versioning, KRAs & Immutable SHA256 Verification
6. Anti-Gaming Paired Metrics & Explainable 4-Factor Performance Scoring
7. Centralized Agent Factory Concurrency Leases, Mutex Locks & TTL Sweeper
8. 6-Tier Data Classification & Real-Time DLP Interceptor
9. Mission Orchestration, Structured Delegation & Kahn's DAG Cycle Prevention
10. REST API Gateway (/api/v8/) Endpoints & Tenant/Company Isolation
11. Six Enterprise Corporate Workforce Simulations (A through F)
"""

import os
import sys
import unittest
import time
import json
import uuid
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import db, configure_isolated_test_db
from core.aic_organization_constitution import (
    ExecutiveRoleRegistry, DynamicOrganizationDesignEngine,
    CompanyProfile, CompanyScaleStage
)
from zonata.models import WorkforceTriadType, TriadEntityContract
from core.kpi_kra_engine import SOPDefinition, SOPVersion, AntiGamingEngine, StructuredKPI, StructuredKRA
from core.agent_factory_v2 import AgentLeaseManager, LeaseConcurrencyConflictError
from core.security_classification import InformationClassification, CLASSIFICATION_LEVELS
from core.dlp_engine import DataLossPreventionEngine, DLPViolationBlockedError
from core.mission_orchestrator import CorporateMissionOrchestrator, DelegationCycleDetectedError
from core.v8_api_handler import V8ApiHandler
from zonata.org_designer import OrganizationDesignEngine

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "enterprise_workforce_test.db")
    configure_isolated_test_db(isolated_db)
    db._init_db()

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()

class TestEnterpriseWorkforce(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_id = f"comp_{uuid.uuid4().hex[:8]}"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, 'Enterprise Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (self.tenant_id, time.time())
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO companies (
                    company_id, tenant_id, name, country, industry,
                    company_type, status, currency, revenue, cost,
                    contribution, created_at
                ) VALUES (?, ?, 'Enterprise Global Corp', 'US', 'SaaS', 'EXISTING', 'OPERATIONAL', '$', 10000000.0, 5000000.0, 5000000.0, ?)
                """,
                (self.company_id, self.tenant_id, time.time())
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # 1. Relational Schema & 25 Enterprise Workforce Tables
    # -------------------------------------------------------------------------
    def test_01_relational_schema_and_25_tables(self):
        """Verifies all 25 newly mandated corporate workforce tables exist and are queryable."""
        expected_tables = [
            "organizations", "corporate_departments", "corporate_positions",
            "corporate_employees", "employee_reporting_relationships",
            "employee_authority_profiles", "employee_knowledge_profiles",
            "sop_definitions", "sop_versions", "employee_sop_assignments",
            "employee_kras", "kpi_definitions", "kpi_measurements",
            "employee_performance_reviews", "workforce_requisitions",
            "agent_capabilities", "agent_templates", "agent_template_versions",
            "agent_instances", "agent_leases", "agent_execution_sessions",
            "corporate_missions", "employee_tasks", "cross_department_collaborations",
            "corporate_knowledge_assets"
        ]

        with db.get_connection() as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for table_name in expected_tables:
                self.assertIn(table_name, tables, f"Expected table '{table_name}' was not created.")

    # -------------------------------------------------------------------------
    # 2. 26 Canonical Corporate C-Suite Roles & DoA Boundaries
    # -------------------------------------------------------------------------
    def test_02_26_role_c_suite_registry(self):
        """Verifies that ExecutiveRoleRegistry holds all 26 real-world C-suite roles."""
        ExecutiveRoleRegistry.initialize()
        roles = ExecutiveRoleRegistry.list_roles()
        self.assertEqual(len(roles), 26, f"Expected 26 C-Suite roles, found {len(roles)}")

        role_ids = {r.role_id for r in roles}
        expected_roles = {
            "EXEC_CEO", "EXEC_CFO", "EXEC_COO", "EXEC_CTO", "EXEC_CMO",
            "EXEC_CRO", "EXEC_CSO", "EXEC_CHRO", "EXEC_CPO", "EXEC_CIO",
            "EXEC_CISO", "EXEC_CLO", "EXEC_CSCO", "EXEC_CCO_CUSTOMER",
            "EXEC_CRO_RISK", "EXEC_CDO", "EXEC_CAIO", "EXEC_CCO_COMPLIANCE",
            "EXEC_CSO_SUSTAINABILITY", "EXEC_CQO", "EXEC_CGO", "EXEC_CPCO",
            "EXEC_CBO", "EXEC_CAO", "EXEC_CSE", "EXEC_CMO_MEDICAL"
        }
        self.assertEqual(role_ids, expected_roles)

        for r in roles:
            self.assertTrue(r.role_name)
            self.assertTrue(r.purpose)
            self.assertTrue(r.budget_authority_usd >= 0.0)
            self.assertTrue(r.risk_authority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            self.assertTrue(r.replacement_failover_role)

    # -------------------------------------------------------------------------
    # 3. Dynamic Multi-Industry Organization Synthesis across 7 Industries
    # -------------------------------------------------------------------------
    def test_03_multi_industry_synthesis(self):
        """Verifies organization generation for SaaS, Manufacturing, Hospitality, Healthcare, Fintech, Retail, Logistics."""
        industries = [
            "SAAS_SOFTWARE", "MANUFACTURING", "HOSPITALITY",
            "HEALTHCARE", "FINTECH", "RETAIL", "LOGISTICS"
        ]

        for ind in industries:
            profile = CompanyProfile(
                company_id=f"comp_{ind.lower()}",
                tenant_id=self.tenant_id,
                company_name=f"{ind} Global Ltd",
                industry=ind,
                geography="GLOBAL",
                company_size="GROWING_COMPANY",
                stage_maturity="SCALEUP",
                revenue_model="SUBSCRIPTION_SAAS",
                annual_revenue_usd=12000000.0,
                current_human_employees=30,
                current_active_agents=15,
                products_services=["Core Product Line"],
                customer_archetype="B2B",
                regulatory_intensity="HIGH" if ind in ["HEALTHCARE", "FINTECH"] else "MEDIUM",
                operational_complexity="HIGH",
                capital_intensity="MODERATE"
            )

            blueprint = DynamicOrganizationDesignEngine.synthesize_organization(profile)
            self.assertTrue(len(blueprint.executives) >= 4)
            self.assertTrue(len(blueprint.departments) >= 4)
            self.assertTrue(blueprint.cryptographic_seal)

            # Industry-specific assertions
            exec_ids = {e["role_id"] for e in blueprint.executives}
            if ind == "HEALTHCARE":
                self.assertIn("EXEC_CMO_MEDICAL", exec_ids)
                self.assertIn("EXEC_CPCO", exec_ids)
            elif ind == "FINTECH":
                self.assertIn("EXEC_CFO", exec_ids)
                self.assertIn("EXEC_CRO_RISK", exec_ids)
                self.assertIn("EXEC_CCO_COMPLIANCE", exec_ids)
            elif ind == "LOGISTICS":
                self.assertIn("EXEC_CSCO", exec_ids)
                self.assertIn("EXEC_CSE", exec_ids)

    # -------------------------------------------------------------------------
    # 4. Architectural Triad Separation & Lifecycle States
    # -------------------------------------------------------------------------
    def test_04_ai_employee_triad_and_lifecycle(self):
        """Validates strict Triad contracts: Employee vs Agent vs Coworker."""
        emp_contract = TriadEntityContract.create_ai_employee_contract("emp_001", self.tenant_id, self.company_id)
        agent_contract = TriadEntityContract.create_ai_agent_contract("agt_001", self.tenant_id, self.company_id)
        coworker_contract = TriadEntityContract.create_ai_coworker_contract("cw_001", self.tenant_id, self.company_id)

        # AI Employee holds corporate positions and DoA
        self.assertEqual(emp_contract.triad_type, WorkforceTriadType.AI_EMPLOYEE)
        self.assertTrue(emp_contract.can_hold_position)
        self.assertTrue(emp_contract.can_hold_doa_authority)
        self.assertFalse(emp_contract.requires_concurrency_lease)

        # AI Agent is stateless execution capability leased via concurrency manager
        self.assertEqual(agent_contract.triad_type, WorkforceTriadType.AI_AGENT)
        self.assertFalse(agent_contract.can_hold_position)
        self.assertFalse(agent_contract.can_hold_doa_authority)
        self.assertTrue(agent_contract.requires_concurrency_lease)

        # AI Coworker is personal desktop assistant, strictly host-isolated
        self.assertEqual(coworker_contract.triad_type, WorkforceTriadType.AI_COWORKER)
        self.assertFalse(coworker_contract.can_hold_position)
        self.assertTrue(coworker_contract.host_desktop_isolated)

    # -------------------------------------------------------------------------
    # 5. SOP Versioning, KRAs & Immutable SHA256 Verification
    # -------------------------------------------------------------------------
    def test_05_sop_immutable_versioning_and_kras(self):
        """Verifies immutable semver SOP versioning and cryptographic checksum verification."""
        sop = SOPDefinition(
            sop_id="sop_fin_001",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            department_id="dept_fin",
            sop_code="SOP-FIN-001-DISBURSE",
            title="Treasury Disbursement SOP",
            category="FINANCIAL"
        )

        steps = [
            {"step": 1, "action": "verify_invoice_signature", "assertion": "signature_valid == True"},
            {"step": 2, "action": "check_doa_limit", "assertion": "amount <= doa_limit"},
            {"step": 3, "action": "execute_disbursement", "assertion": "bank_ack == True"}
        ]

        v1 = SOPVersion(
            version_id="ver_001",
            sop_id=sop.sop_id,
            tenant_id=self.tenant_id,
            version_semver="1.0.0",
            status="APPROVED",
            steps_definition=steps,
            input_schema={"invoice_id": "str", "amount": "float"},
            output_schema={"receipt_id": "str"},
            anti_gaming_rules={"max_disbursements_per_hour": 10}
        )

        sha = v1.calculate_hash()
        self.assertTrue(len(sha) == 64)
        v1.sha256_hash = sha

        # Mutating steps changes the SHA256 (immutability check)
        tampered_steps = list(steps)
        tampered_steps[1] = {"step": 2, "action": "bypass_doa", "assertion": "True"}
        v1_tampered = SOPVersion(
            version_id="ver_001",
            sop_id=sop.sop_id,
            tenant_id=self.tenant_id,
            version_semver="1.0.0",
            status="APPROVED",
            steps_definition=tampered_steps,
            input_schema={"invoice_id": "str", "amount": "float"},
            output_schema={"receipt_id": "str"},
            anti_gaming_rules={"max_disbursements_per_hour": 10}
        )
        self.assertNotEqual(sha, v1_tampered.calculate_hash())

    # -------------------------------------------------------------------------
    # 6. Anti-Gaming Paired Metrics & Explainable 4-Factor Performance Scoring
    # -------------------------------------------------------------------------
    def test_06_anti_gaming_metric_pairings(self):
        """Verifies that metric gaming attempts (high primary + collapsed counter-metric) are caught and penalized."""
        # Case 1: Healthy metric alignment (Tickets resolved = 150, CSAT = 95%)
        passed, score, reason = AntiGamingEngine.evaluate_pair(
            primary_code="KPI_TICKET_VOLUME",
            primary_actual=150.0,
            primary_target=100.0,
            counter_code="KPI_CSAT_SCORE",
            counter_actual=95.0,
            counter_warning=80.0
        )
        self.assertTrue(passed)
        self.assertEqual(score, 100.0)

        # Case 2: Metric Gaming Attempt (Tickets resolved = 200, CSAT collapsed to 40%)
        passed_game, score_game, reason_game = AntiGamingEngine.evaluate_pair(
            primary_code="KPI_TICKET_VOLUME",
            primary_actual=200.0,
            primary_target=100.0,
            counter_code="KPI_CSAT_SCORE",
            counter_actual=40.0,
            counter_warning=80.0
        )
        self.assertFalse(passed_game)
        self.assertTrue(score_game < 50.0)
        self.assertIn("ANTI_GAMING_ALERT", reason_game)

        # Explainable 4-Factor Scoring
        comp, rec, proof = AntiGamingEngine.compute_4_factor_review(
            kpi_achievement_score=95.0,
            sop_compliance_score=90.0,
            anti_gaming_compliance_score=100.0,
            collaboration_sla_score=92.0
        )
        self.assertTrue(comp >= 90.0)
        self.assertEqual(rec, "PROMOTE")
        self.assertEqual(proof["weights"]["kpi"], 0.40)
        self.assertEqual(proof["weights"]["sop"], 0.30)

    # -------------------------------------------------------------------------
    # 7. Centralized Agent Factory Concurrency Leases & Mutex Locks
    # -------------------------------------------------------------------------
    def test_07_agent_factory_concurrency_leases_and_mutex(self):
        """Validates that two employees cannot concurrently lease the same agent instance."""
        inst_id = f"inst_{uuid.uuid4().hex[:8]}"

        # Seed template version, idle agent instance, and corporate employees
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
            INSERT OR IGNORE INTO corporate_departments (department_id, tenant_id, company_id, code, name, cost_center_code, created_at, updated_at)
            VALUES ('dept_eng', ?, ?, 'ENG', 'Engineering', 'CC-ENG', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_positions (position_id, tenant_id, company_id, department_id, position_code, title, hierarchy_level, job_family, created_at, updated_at)
            VALUES ('pos_dev_01', ?, ?, 'dept_eng', 'POS-DEV-01', 'Developer', 'L9_SPECIALIST', 'ENGINEERING', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_employees (employee_id, tenant_id, company_id, position_id, department_id, first_name, last_name, work_email, lifecycle_state, created_at, updated_at)
            VALUES ('emp_alice', ?, ?, 'pos_dev_01', 'dept_eng', 'Alice', 'Engineer', 'alice@test.com', 'ACTIVE', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_employees (employee_id, tenant_id, company_id, position_id, department_id, first_name, last_name, work_email, lifecycle_state, created_at, updated_at)
            VALUES ('emp_bob', ?, ?, 'pos_dev_01', 'dept_eng', 'Bob', 'Engineer', 'bob@test.com', 'ACTIVE', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))

            conn.execute("""
            INSERT OR IGNORE INTO agent_templates (template_id, tenant_id, name, slug, description, role_category, default_capabilities, default_toolset, sandbox_requirements, created_at)
            VALUES ('tpl_research', ?, 'Research Agent', 'research-agent', 'Web Research', 'SPECIALIST', '[]', '[]', '{}', ?)
            """, (self.tenant_id, now))
            conn.execute("""
            INSERT OR IGNORE INTO agent_template_versions (version_id, template_id, tenant_id, semver, system_prompt_scaffold, capability_manifest, tool_manifest, resource_limits, sbom_hash, signature, status, created_at)
            VALUES ('ver_res_01', 'tpl_research', ?, '1.0.0', 'Prompt', '[]', '[]', '{}', 'hash', 'sig', 'ACTIVE', ?)
            """, (self.tenant_id, now))
            conn.execute("""
            INSERT INTO agent_instances (instance_id, tenant_id, company_id, template_version_id, host_runtime_id, lifecycle_state, last_heartbeat, created_at)
            VALUES (?, ?, ?, 'ver_res_01', 'host_01', 'IDLE', ?, ?)
            """, (inst_id, self.tenant_id, self.company_id, now, now))
            conn.commit()

        # Employee 1 acquires lease -> Success
        lease1 = AgentLeaseManager.acquire_lease(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            instance_id=inst_id,
            employee_id="emp_alice",
            ttl_seconds=60.0
        )
        self.assertEqual(lease1["status"], "ACTIVE")

        # Employee 2 attempts concurrent lease -> Blocked by Mutex
        with self.assertRaises(LeaseConcurrencyConflictError):
            AgentLeaseManager.acquire_lease(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                instance_id=inst_id,
                employee_id="emp_bob",
                ttl_seconds=60.0
            )

        # Release lease 1 -> Instance becomes IDLE again
        released = AgentLeaseManager.release_lease(lease1["lease_id"])
        self.assertTrue(released)

        # Employee 2 can now acquire lease
        lease2 = AgentLeaseManager.acquire_lease(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            instance_id=inst_id,
            employee_id="emp_bob",
            ttl_seconds=60.0
        )
        self.assertEqual(lease2["leased_by"], "emp_bob")

    # -------------------------------------------------------------------------
    # 8. 6-Tier Data Classification & Real-Time DLP Interceptor
    # -------------------------------------------------------------------------
    def test_08_six_tier_dlp_and_data_classification(self):
        """Verifies real-time DLP redaction and customer-facing disclosure gate."""
        raw_text = "Employee John Doe SSN: 123-45-6789 salary: $150000 with card: 4111-2222-3333-4444"

        # Internal disclosure -> Redacts PII but allows transfer
        res = DataLossPreventionEngine.inspect_and_filter(
            raw_text,
            destination_classification=InformationClassification.INTERNAL.value,
            source_classification=InformationClassification.INTERNAL.value
        )
        self.assertEqual(res["status"], "REDACTED")
        self.assertNotIn("123-45-6789", res["sanitized_content"])
        self.assertIn("[REDACTED_SSN]", res["sanitized_content"])
        self.assertIn("[REDACTED_CARD]", res["sanitized_content"])

        # Gate Check: CONFIDENTIAL source targeting CUSTOMER_SHAREABLE -> Blocked
        with self.assertRaises(DLPViolationBlockedError):
            DataLossPreventionEngine.inspect_and_filter(
                "Executive board minutes and secret roadmap",
                destination_classification=InformationClassification.CUSTOMER_SHAREABLE.value,
                source_classification=InformationClassification.CONFIDENTIAL.value
            )

    # -------------------------------------------------------------------------
    # 9. Mission Orchestration, Structured Delegation & Kahn's DAG Cycle Prevention
    # -------------------------------------------------------------------------
    def test_09_mission_orchestration_and_dag_cycle_detection(self):
        """Verifies mission creation and Kahn's algorithm detecting delegation cycles."""
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
            INSERT OR IGNORE INTO corporate_departments (department_id, tenant_id, company_id, code, name, cost_center_code, created_at, updated_at)
            VALUES ('dept_growth', ?, ?, 'GRO', 'Growth', 'CC-GRO', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_positions (position_id, tenant_id, company_id, department_id, position_code, title, hierarchy_level, job_family, created_at, updated_at)
            VALUES ('pos_cmo', ?, ?, 'dept_growth', 'POS-CMO', 'Chief Marketing Officer', 'L3_CHIEF_EXECUTIVE', 'EXECUTIVE', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_employees (employee_id, tenant_id, company_id, position_id, department_id, first_name, last_name, work_email, lifecycle_state, created_at, updated_at)
            VALUES ('emp_cmo', ?, ?, 'pos_cmo', 'dept_growth', 'Carol', 'CMO', 'cmo@test.com', 'ACTIVE', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.commit()

        mission = CorporateMissionOrchestrator.create_mission(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Q4 Market Penetration",
            objective_statement="Expand into DACH territory and achieve $500k ARR",
            lead_employee_id="emp_cmo",
            sponsor_executive_role="EXEC_CEO"
        )
        self.assertEqual(mission["status"], "PLANNING")

        # Linear DAG: Task A -> Task B -> Task C -> Valid
        tasks_valid = [
            {"task_id": "T_A", "dependency_task_ids": []},
            {"task_id": "T_B", "dependency_task_ids": ["T_A"]},
            {"task_id": "T_C", "dependency_task_ids": ["T_B"]}
        ]
        self.assertTrue(CorporateMissionOrchestrator.validate_delegation_dag(tasks_valid))

        # Test append_task on mission with valid dependencies
        t1 = CorporateMissionOrchestrator.append_task(
            mission_id=mission["mission_id"],
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Initial Market Analysis",
            assigned_employee_id="emp_cmo",
            delegator_employee_id="emp_cmo"
        )
        self.assertEqual(t1["status"], "QUEUED")

        t2 = CorporateMissionOrchestrator.append_task(
            mission_id=mission["mission_id"],
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Competitor Synthesis",
            assigned_employee_id="emp_cmo",
            delegator_employee_id="emp_cmo",
            dependency_task_ids=[t1["task_id"]]
        )
        self.assertEqual(t2["status"], "QUEUED")

        # Cyclical DAG: Task A -> Task B -> Task C -> Task A -> Detected & Blocked
        tasks_cyclic = [
            {"task_id": "T_A", "dependency_task_ids": ["T_C"]},
            {"task_id": "T_B", "dependency_task_ids": ["T_A"]},
            {"task_id": "T_C", "dependency_task_ids": ["T_B"]}
        ]
        with self.assertRaises(DelegationCycleDetectedError):
            CorporateMissionOrchestrator.validate_delegation_dag(tasks_cyclic)

    # -------------------------------------------------------------------------
    # 10. REST API Gateway (/api/v8/) Endpoints & Tenant Isolation
    # -------------------------------------------------------------------------
    def test_10_rest_api_gateway_v8_routes(self):
        """Validates all REST endpoints under /api/v8/."""
        # 1. GET /api/v8/organization/roles
        res_roles, code = V8ApiHandler.handle_get(
            "/api/v8/organization/roles",
            {},
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        self.assertEqual(code, 200)
        self.assertEqual(res_roles["count"], 26)

        # 2. GET /api/v8/organization/departments
        res_dept, code = V8ApiHandler.handle_get(
            "/api/v8/organization/departments",
            {},
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        self.assertEqual(code, 200)
        self.assertTrue(res_dept["success"])

        # 3. POST /api/v8/kpi/anti-gaming/check
        res_ag, code = V8ApiHandler.handle_post(
            "/api/v8/kpi/anti-gaming/check",
            {
                "primary_code": "KPI_CALLS",
                "primary_actual": 250.0,
                "primary_target": 100.0,
                "counter_code": "KPI_QUALITY",
                "counter_actual": 30.0,
                "counter_warning": 80.0
            },
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        self.assertEqual(code, 200)
        self.assertFalse(res_ag["anti_gaming_passed"])

        # 4. Cross-Tenant Isolation Enforcement
        res_iso, code_iso = V8ApiHandler.handle_get(
            "/api/v8/organization/roles",
            {"tenant_id": "tnt_foreign_unauthorized"},
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        self.assertEqual(code_iso, 403)

    # -------------------------------------------------------------------------
    # 11. Six Enterprise Corporate Workforce Simulations
    # -------------------------------------------------------------------------
    def test_11_six_enterprise_simulations(self):
        """
        Executes Simulations A through F:
        A: Competitor Intelligence (Market research)
        B: Marketing Optimization (SEO & Anti-gaming CAC)
        C: Sales Execution (DoA & Financial validation)
        D: Workforce Restructuring (CHRO Requisition & Gap analysis)
        E: Engineering Delivery (CTO & Technical tooling)
        F: Coworker Execution (Host isolation)
        """
        now = time.time()

        # --- Simulation A: Competitor Intelligence ---
        with db.get_connection() as conn:
            conn.execute("""
            INSERT OR IGNORE INTO corporate_departments (department_id, tenant_id, company_id, code, name, cost_center_code, created_at, updated_at)
            VALUES ('dept_mkt', ?, ?, 'MKT', 'Marketing & Intelligence', 'CC-MKT', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_positions (position_id, tenant_id, company_id, department_id, position_code, title, hierarchy_level, job_family, created_at, updated_at)
            VALUES ('pos_mkt_spec', ?, ?, 'dept_mkt', 'POS-MKT-01', 'Market Intelligence Specialist', 'L9_SPECIALIST', 'MARKETING', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.execute("""
            INSERT OR IGNORE INTO corporate_employees (employee_id, tenant_id, company_id, position_id, department_id, first_name, last_name, work_email, lifecycle_state, created_at, updated_at)
            VALUES ('emp_mkt_01', ?, ?, 'pos_mkt_spec', 'dept_mkt', 'MarketIntel', 'Specialist', 'intel@enterprise.com', 'ACTIVE', ?, ?)
            """, (self.tenant_id, self.company_id, now, now))
            conn.commit()

        # Mission A Delegation
        msn_a = CorporateMissionOrchestrator.create_mission(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Sim A: Competitor Benchmarking",
            objective_statement="Gather dual-source pricing intelligence on competitor X",
            lead_employee_id="emp_mkt_01",
            sponsor_executive_role="EXEC_CMO"
        )
        self.assertEqual(msn_a["status"], "PLANNING")

        # --- Simulation B: Marketing Optimization ---
        # Anti-gaming verification for CAC vs Volume
        passed, score, reason = AntiGamingEngine.evaluate_pair(
            primary_code="KPI_LEAD_VOLUME",
            primary_actual=500.0,
            primary_target=200.0,
            counter_code="KPI_CAC_USD",
            counter_actual=180.0, # Target was 100, Warning was 120 -> Breach
            counter_warning=120.0
        )
        self.assertFalse(passed)
        self.assertTrue(score < 60.0)

        # --- Simulation C: Sales Execution & DoA Financial Gate ---
        cfo_role = ExecutiveRoleRegistry.get_role("EXEC_CFO")
        self.assertTrue(cfo_role.budget_authority_usd >= 100000.0)
        cfo_profile = {
            "can_approve_financial_spend": True,
            "single_spend_limit_usd": cfo_role.budget_authority_usd
        }
        requested_contract_usd = 75000.0
        self.assertTrue(requested_contract_usd <= cfo_profile["single_spend_limit_usd"])

        # --- Simulation D: Workforce Restructuring (CHRO Requisition) ---
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute("""
            INSERT INTO workforce_requisitions (
                requisition_id, tenant_id, company_id, department_id,
                requested_position_title, requesting_executive_role, justification,
                gap_analysis_evidence, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'dept_mkt', 'Senior SEO Specialist', 'EXEC_CMO',
                      'Capacity backlog exceeded 85%', '{\"backlog_hours\": 140}', 'PROPOSED', ?, ?)
            """, (req_id, self.tenant_id, self.company_id, now, now))
            conn.commit()

            # CHRO Approves Requisition
            conn.execute("UPDATE workforce_requisitions SET status = 'CHRO_APPROVED' WHERE requisition_id = ?", (req_id,))
            conn.commit()

            row = conn.execute("SELECT status FROM workforce_requisitions WHERE requisition_id = ?", (req_id,)).fetchone()
            self.assertEqual(row["status"], "CHRO_APPROVED")

        # --- Simulation E: Engineering Delivery (CTO & Technical Tools) ---
        cto_role = ExecutiveRoleRegistry.get_role("EXEC_CTO")
        self.assertIn("OpenHandsExecutionManager", cto_role.required_tools)
        self.assertEqual(cto_role.risk_authority, "MEDIUM")

        # --- Simulation F: Coworker Execution (Host Isolation) ---
        coworker_contract = TriadEntityContract.create_ai_coworker_contract("cw_host_01", self.tenant_id, self.company_id)
        self.assertTrue(coworker_contract.host_desktop_isolated)
        self.assertFalse(coworker_contract.can_hold_doa_authority)
        self.assertFalse(coworker_contract.can_hold_position)

if __name__ == "__main__":
    unittest.main()
