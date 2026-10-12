"""
RoboAssistant 1.0.0-GA / ROBO-GA-1.0.0-PROD
Automated Cross-Domain Validation Matrix & Governance Regression Suite
"""

import os
import sys
import unittest
import uuid
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
sys.path.insert(0, "/roboassistant")

from core.models import AuthorityLevel, MissionStatus, EvidenceStatus, HostType, ActionContract
from core.evidence_ledger import EvidenceLedger
from core.control_kernel import UniversalControlKernel
from core.portfolio import CompanyPortfolioManager, CompanyOnboardingEngine
from core.ceo import CeoCommandEngine, ExecutiveReportEngine
from core.tool_fabric import CapabilityRegistry, ToolDiscoveryEngine
from core.workforce import DynamicAgentFactory
from workloads.hospitality import run_hospitality_night_audit
from workloads.manufacturing import run_manufacturing_bottleneck_analysis
from workloads.saas import run_saas_churn_analysis
from workloads.personal import run_personal_file_hygiene
from workloads.universal_computer import run_universal_capability_discovery_task
from core.db import db, configure_isolated_test_db

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "validation_matrix_test.db")
    configure_isolated_test_db(isolated_db)
    isolated_ledger = os.path.join(MODULE_TEMP_DIR.name, "validation_matrix_ledger.jsonl")
    os.environ["ZONATA_EVIDENCE_PATH"] = isolated_ledger

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if "ZONATA_EVIDENCE_PATH" in os.environ:
        del os.environ["ZONATA_EVIDENCE_PATH"]
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()

class TestRoboAssistantValidationMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.ledger_file = os.path.join(tempfile.gettempdir(), f"test_audit_ledger_{uuid.uuid4().hex[:8]}.jsonl")
        cls.ledger = EvidenceLedger(cls.ledger_file)
        cls.kernel = UniversalControlKernel(cls.ledger)
        cls.registry = CapabilityRegistry()
        cls.portfolio_mgr = CompanyPortfolioManager()
        cls.ceo_command = CeoCommandEngine(cls.portfolio_mgr)
        cls.ceo_reports = ExecutiveReportEngine(cls.portfolio_mgr)

    def test_01_onboarding_both_paths(self):
        """Test dual onboarding workflows: New Company and Existing Enterprise."""
        # 1. Existing Enterprise Onboarding
        hotel = CompanyOnboardingEngine.onboard_existing_company(
            name="Royal Haveli Resort & Spa",
            industry="Hospitality & Leisure",
            website="https://royalhaveli.example.com",
            initial_data_sources=[
                {"name": "Opera Cloud PMS", "type": "PMS", "method": "API", "data": ["folios", "reservations"]},
                {"name": "Simphony Cloud POS", "type": "POS", "method": "API", "data": ["f_and_b_bills"]},
                {"name": "Razorpay Payment Gateway", "type": "API", "method": "WEBHOOK", "data": ["settlements"]}
            ]
        )
        self.portfolio_mgr.register_company(hotel)
        self.assertEqual(hotel.company_type, "EXISTING")
        self.assertEqual(len(hotel.data_sources), 3)
        # Verify read-only visibility invariant on connected data
        self.assertEqual(hotel.data_sources[0].permission_level, "READ_ONLY_VISIBILITY")
        self.assertIsNotNone(hotel.baseline_summary)

        # 2. New Ground-Up Company Onboarding
        mfg = CompanyOnboardingEngine.onboard_new_company(
            name="Apex Precision Manufacturing",
            industry="Aerospace Components",
            business_model="Contract CNC Machining",
            target_revenue=5000000.0
        )
        self.portfolio_mgr.register_company(mfg)
        self.assertEqual(mfg.company_type, "NEW")
        self.assertGreater(len(mfg.workforce), 0)

        # 3. SaaS Company
        saas = CompanyOnboardingEngine.onboard_new_company(
            name="CloudScale Digital SaaS",
            industry="Cloud Infrastructure",
            business_model="B2B Subscription",
            target_revenue=10000000.0
        )
        self.portfolio_mgr.register_company(saas)

        # 4. Personal Context
        pers = CompanyOnboardingEngine.onboard_new_company(
            name="Personal Operations",
            industry="Executive Productivity",
            business_model="Private Operations",
            target_revenue=0.0
        )
        self.portfolio_mgr.register_company(pers)

        summary = self.portfolio_mgr.get_portfolio_summary()
        self.assertEqual(summary["total_companies"], 4)
        self.assertEqual(summary["operational_companies"], 4)

    def test_02_ceo_command_vs_executive_reports(self):
        """Verify strict distinction between Strategic Command and Executive Intelligence."""
        hotel = self.portfolio_mgr.list_companies()[0]

        # Strategic Command: Apply cost-minimization rule
        res = self.ceo_command.execute_directive(hotel.company_id, "For this hotel, always try free or existing tools before spending money")
        self.assertTrue(res["success"])
        self.assertEqual(res["command_type"], "POLICY_UPDATE")
        self.assertTrue(any("COST_MINIMIZATION" in r for r in hotel.operating_rules))

        # Strategic Command: Set budget ceiling
        res_budget = self.ceo_command.execute_directive(hotel.company_id, "Set monthly AI operations budget to ₹50,000")
        self.assertTrue(res_budget["success"])

        # Executive Intelligence: Daily Executive Briefing
        briefing = self.ceo_reports.generate_daily_executive_briefing()
        self.assertIn("financial_summary", briefing)
        self.assertIn("what_happened", briefing["executive_answers"])
        self.assertIn("recommended_priorities_today", briefing["executive_answers"])

        # Executive Intelligence: Morning Executive Meeting
        dialogue = self.ceo_reports.conduct_morning_executive_meeting(hotel.company_id)
        self.assertGreater(len(dialogue), 2)
        self.assertEqual(dialogue[0]["speaker"], "AI CEO")

    def test_03_capability_not_equal_to_authority_invariant(self):
        """
        Verify fundamental invariant: Capability != Authority.
        Acquiring capability or attempting forbidden action must be stopped.
        """
        contract = DynamicAgentFactory.create_employment_contract(
            role="Test Agent",
            department="Operations",
            manager="AI CEO",
            responsibilities=["Testing security invariants"],
            objectives=["Ensure failure on forbidden action"],
            allowed_tools=["python3"]
        )

        # Test forbidden action enforcement
        forbidden_action = ActionContract(
            action_id="ACT-FORBIDDEN-001",
            mission_id="MSN-TEST-SEC",
            agent_id=contract.agent_id,
            capability="credential_extraction",  # Explicitly forbidden
            target="/etc/shadow",
            host=HostType.LINUX_CLOUD,
            scope="root",
            permissions_required=AuthorityLevel.NEVER_ALLOWED,
            resources_locked=[],
            expected_outcome="Forbidden dump",
            verification_requirements=[]
        )

        res = self.kernel.execute_action(forbidden_action, contract)
        self.assertFalse(res["success"])
        self.assertIn("SECURITY_POLICY_VIOLATION", res["error"])

        # Test tool discovery under locked authority ceiling
        disc_engine = ToolDiscoveryEngine(self.registry)
        disc_res = disc_engine.discover_and_provision(
            required_tool="playwright",
            authority_ceiling="SANDBOXED_READ_ONLY"
        )
        # Should be blocked from elevating authority
        self.assertFalse(disc_res["success"])
        self.assertEqual(disc_res["status"], "AUTHORITY_CEILING_BLOCKED")

    def test_04_execute_all_5_reference_workloads(self):
        """
        Run the complete cross-domain 5-workload validation matrix:
        Workload A (Hospitality), Workload B (Manufacturing), Workload C (SaaS),
        Workload D (Personal), and Workload E (Universal Computer Task).
        """
        hotel = [c for c in self.portfolio_mgr.list_companies() if c.name == "Royal Haveli Resort & Spa"][0]
        mfg = [c for c in self.portfolio_mgr.list_companies() if c.name == "Apex Precision Manufacturing"][0]
        saas = [c for c in self.portfolio_mgr.list_companies() if c.name == "CloudScale Digital SaaS"][0]
        pers = [c for c in self.portfolio_mgr.list_companies() if c.name == "Personal Operations"][0]

        # Workload A: Hospitality
        mis_a = run_hospitality_night_audit(hotel, self.kernel)
        self.assertEqual(mis_a.status, MissionStatus.SUCCESS)
        self.assertIn("VERIFIED", mis_a.verification_summary)

        # Workload B: Manufacturing
        mis_b = run_manufacturing_bottleneck_analysis(mfg, self.kernel)
        self.assertEqual(mis_b.status, MissionStatus.SUCCESS)
        self.assertIn("VERIFIED", mis_b.verification_summary)

        # Workload C: SaaS
        mis_c = run_saas_churn_analysis(saas, self.kernel)
        self.assertEqual(mis_c.status, MissionStatus.SUCCESS)
        self.assertIn("VERIFIED", mis_c.verification_summary)

        # Workload D: Personal Operations
        mis_d = run_personal_file_hygiene(pers, self.kernel)
        self.assertEqual(mis_d.status, MissionStatus.SUCCESS)
        self.assertIn("VERIFIED", mis_d.verification_summary)

        # Workload E: Universal Autonomous Capability Discovery
        mis_e = run_universal_capability_discovery_task(mfg, self.kernel, self.registry)
        self.assertEqual(mis_e.status, MissionStatus.SUCCESS)
        self.assertIn("VERIFIED", mis_e.verification_summary)

    def test_05_physical_truth_and_merkle_ledger_integrity(self):
        """
        Assert that physical files exist, hashes match, and the Merkle chain is unbroken.
        """
        expected_files = [
            "/roboassistant/storage/sandbox/hospitality_night_audit.json",
            "/roboassistant/storage/sandbox/mfg_corrective_plan.json",
            "/roboassistant/storage/sandbox/saas_retention_campaign.json",
            "/roboassistant/storage/sandbox/file_cleanup_manifest.json",
            "/roboassistant/storage/sandbox/universal_database_analysis.json",
            "/roboassistant/storage/sandbox/universal_analytics.db"
        ]

        for path in expected_files:
            self.assertTrue(os.path.exists(path), f"File missing: {path}")
            self.assertGreater(os.path.getsize(path), 0, f"File empty: {path}")

        # Merkle Ledger Validation
        self.assertTrue(self.ledger.verify_ledger_integrity(), "Merkle Audit Ledger cryptographic chain broken!")
        root = self.ledger.get_merkle_root()
        self.assertIsNotNone(root)
        self.assertEqual(len(root), 64)  # SHA-256 hex string

if __name__ == "__main__":
    unittest.main()
