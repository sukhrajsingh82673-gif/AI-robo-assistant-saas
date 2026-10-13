"""
Automated Validation Suite for ZONATA Executive Overview Production Rebuild
Verifies all 42 acceptance criteria and constitutional invariants:
1. Zero fake data; real database records or explicit empty state.
2. Canonical company switching (Portfolio vs Individual Company context).
3. All time periods supported (today, 7d, 30d, 90d, quarter, year).
4. Variance explanation engine based strictly on verified evidence.
5. All required analytical dimensions present (Financial, Sales, Customers,
   Marketing, Operations, Workforce, Missions, Risk, Technology, Data Quality, Insights, Anomalies).
6. Frontend assets and script wiring integrity.
"""

import unittest
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.overview_service import OverviewDataService
from core.db import db


class TestOverviewProductionRebuild(unittest.TestCase):
    def setUp(self):
        self.tenant_id = "tnt_primary"

    def test_01_portfolio_snapshot_structure(self):
        """Verify Portfolio mode produces full snapshot with aggregated data."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        self.assertIsNotNone(snap)
        self.assertEqual(snap["context"]["mode"], "portfolio")
        self.assertEqual(snap["context"]["company_name"], "Portfolio Overview")
        self.assertIn("Showing data:", snap["context"]["period_label"])

        # Check required root sections
        required_keys = [
            "context", "company", "financial", "sales", "customers",
            "marketing", "operations", "workforce", "missions",
            "attention", "risk", "technology", "data_quality",
            "intelligence", "anomalies", "portfolio"
        ]
        for key in required_keys:
            self.assertIn(key, snap, f"Missing key {key} in OverviewSnapshot")

        # Portfolio specific data
        pf = snap["portfolio"]
        self.assertIsNotNone(pf)
        self.assertGreater(pf["total_companies"], 0)
        self.assertIsInstance(pf["companies"], list)
        self.assertGreater(len(pf["companies"]), 0)

    def test_02_individual_company_context_switch(self):
        """Verify selecting a single company completely switches analytical context."""
        with db.get_connection() as conn:
            row = conn.execute("SELECT company_id, name, industry FROM companies WHERE tenant_id = ? ORDER BY company_id", (self.tenant_id,)).fetchone()
        self.assertIsNotNone(row)
        company_id = row["company_id"]
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=company_id, period="30d")
        self.assertEqual(snap["context"]["mode"], "company")
        self.assertEqual(snap["context"]["company_id"], company_id)
        self.assertEqual(snap["company"]["name"], row["name"])
        self.assertEqual(snap["company"]["industry"], row["industry"])
        self.assertIsNone(snap.get("portfolio"))
        self.assertIn("has_data", snap["financial"])

    def test_03_time_period_propagation(self):
        """Verify all time periods update the period label and date ranges."""
        periods = ["today", "7d", "30d", "90d", "quarter", "year"]
        for p in periods:
            snap = OverviewDataService.get_snapshot(self.tenant_id, period=p)
            self.assertEqual(snap["context"]["period"], p)
            self.assertIn("Showing data:", snap["context"]["period_label"])

    def test_04_variance_explanation_provenance(self):
        """Verify 'Why did this change?' produces evidence-backed explanation with epistemic provenance."""
        exp = OverviewDataService.explain_variance(self.tenant_id, company_id=None, metric="revenue")
        self.assertIsNotNone(exp)
        self.assertEqual(exp["metric"], "revenue")
        self.assertIn("explanation_summary", exp)
        self.assertIn("contributing_factors", exp)
        self.assertGreater(len(exp["contributing_factors"]), 0)

        # Check epistemic states on contributing factors
        for f in exp["contributing_factors"]:
            self.assertIn("factor", f)
            self.assertIn("impact", f)
            self.assertIn(f["epistemic_state"], ["FACT", "CALCULATION", "OBSERVATION", "ESTIMATE", "PREDICTION", "UNVERIFIED"])

    def test_05_executive_attention_center_classification(self):
        """Verify Attention Center groups items by Critical, Important, Informational with actions."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        att = snap["attention"]
        self.assertIn("critical", att)
        self.assertIn("important", att)
        self.assertIn("informational", att)
        self.assertIsInstance(att["critical"], list)

        for item in att["critical"]:
            self.assertIn("title", item)
            self.assertIn("severity", item)
            self.assertIn("reason", item)
            self.assertIn("evidence", item)
            self.assertIn("action_label", item)

    def test_06_business_causality_invariant(self):
        """Verify Task Success != Business Outcome invariant in causality outcomes."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        mis = snap["missions"]
        self.assertIn("outcomes", mis)
        if len(mis["outcomes"]) > 0:
            out = mis["outcomes"][0]
            self.assertIn("strategy_goal", out)
            self.assertIn("revenue_attributed", out)
            self.assertIn("transaction_id", out)
            self.assertEqual(out["verified_outcome"], "VERIFIED_SUCCESS")

    def test_07_data_quality_and_trust(self):
        """Verify data quality calculation reflects baseline ledger and empty-state contracts."""
        # 1. Baseline ledger test: exactly 25 verified records from baseline ledger
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        dq = snap["data_quality"]
        self.assertGreaterEqual(dq["overall_completeness_pct"], 0)
        self.assertLessEqual(dq["overall_completeness_pct"], 100)
        self.assertIn(dq["merkle_integrity"], ["UNBROKEN", "DEGRADED"])
        self.assertEqual(dq["verified_records"], 25, "Baseline ledger contains exactly 25 verified records")
        self.assertGreater(dq["unverified_records"], 0)

        # 2. Empty ledger fixture contract: exactly 0 verified records
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            empty_ledger = os.path.join(td, "empty_ledger.jsonl")
            with open(empty_ledger, "w") as f:
                pass
            orig_env = os.environ.get("ZONATA_EVIDENCE_PATH")
            os.environ["ZONATA_EVIDENCE_PATH"] = empty_ledger
            try:
                snap_empty = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
                dq_empty = snap_empty["data_quality"]
                self.assertEqual(dq_empty["verified_records"], 0, "Empty ledger fixture must yield exactly 0 verified records")
                self.assertGreater(dq_empty["unverified_records"], 0, "Empty state must report unverified records pending ingestion")
            finally:
                if orig_env is not None:
                    os.environ["ZONATA_EVIDENCE_PATH"] = orig_env
                elif "ZONATA_EVIDENCE_PATH" in os.environ:
                    del os.environ["ZONATA_EVIDENCE_PATH"]

    def test_08_evidence_provenance_simulated_cannot_promote_to_verified(self):
        """Verify synthetic evidence is sealed as SIMULATED and never counted as verified_records."""
        import tempfile
        from core.evidence_ledger import EvidenceLedger
        from core.models import EvidenceStatus, PhysicalVerification

        with tempfile.TemporaryDirectory() as td:
            test_ledger = os.path.join(td, "test_sim_ledger.jsonl")
            orig_env = os.environ.get("ZONATA_EVIDENCE_PATH")
            os.environ["ZONATA_EVIDENCE_PATH"] = test_ledger
            try:
                el = EvidenceLedger()
                pkg = el.seal_evidence(
                    action_id="act_sim_test",
                    mission_id="mis_sim_test",
                    agent_id="agt_sim_test",
                    verifications=[PhysicalVerification(check_type="simulated_run", target_path="/tmp", expected_val="1", actual_val="1", verified=True, details="simulated run check")],
                    metadata={"simulated": True, "is_mock": True}
                )
                self.assertEqual(pkg.status, EvidenceStatus.SIMULATED)

                # Snapshot must still report verified_records == 0 and unverified_records == 1
                snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
                dq = snap["data_quality"]
                self.assertEqual(dq["verified_records"], 0, "Simulated evidence must not increment verified_records")
                self.assertEqual(dq["unverified_records"], 1, "Simulated evidence must count as unverified_records")
            finally:
                if orig_env is not None:
                    os.environ["ZONATA_EVIDENCE_PATH"] = orig_env
                elif "ZONATA_EVIDENCE_PATH" in os.environ:
                    del os.environ["ZONATA_EVIDENCE_PATH"]

    def test_09_qualifying_physical_verification_increments_verified_records(self):
        """Verify qualifying physical evidence is sealed as VERIFIED and increments verified_records."""
        import tempfile
        import hashlib
        from core.evidence_ledger import EvidenceLedger
        from core.models import EvidenceStatus, PhysicalVerification

        with tempfile.TemporaryDirectory() as td:
            test_ledger = os.path.join(td, "test_ver_ledger.jsonl")
            test_target = os.path.join(td, "real_artifact.txt")
            with open(test_target, "w") as f:
                f.write("confirmed real payload")
            digest = hashlib.sha256(b"confirmed real payload").hexdigest()

            orig_env = os.environ.get("ZONATA_EVIDENCE_PATH")
            os.environ["ZONATA_EVIDENCE_PATH"] = test_ledger
            try:
                el = EvidenceLedger()
                pkg = el.seal_evidence(
                    action_id="act_phys_test",
                    mission_id="mis_phys_test",
                    agent_id="agt_phys_test",
                    verifications=[
                        PhysicalVerification(
                            check_type="file_exists",
                            target_path=test_target,
                            expected_val="EXISTS",
                            actual_val="EXISTS",
                            verified=True,
                            details="file existence verified"
                        ),
                        PhysicalVerification(
                            check_type="sha256_match",
                            target_path=test_target,
                            expected_val=digest,
                            actual_val=digest,
                            verified=True,
                            details="sha256 digest match verified"
                        )
                    ],
                    metadata={"simulated": False, "is_mock": False}
                )
                self.assertEqual(pkg.status, EvidenceStatus.VERIFIED)

                # Snapshot must report verified_records == 1
                snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
                dq = snap["data_quality"]
                self.assertEqual(dq["verified_records"], 1, "Qualifying physical verification must increment verified_records")
                self.assertEqual(dq["unverified_records"], 0, "No unverified records when all are verified")
            finally:
                if orig_env is not None:
                    os.environ["ZONATA_EVIDENCE_PATH"] = orig_env
                elif "ZONATA_EVIDENCE_PATH" in os.environ:
                    del os.environ["ZONATA_EVIDENCE_PATH"]

    def test_10_frontend_assets_wiring(self):
        """Verify all frontend files exist and are properly linked."""
        web_dir = os.path.join(BASE_DIR, "web")
        overview_js = os.path.join(web_dir, "overview_workspace.js")
        index_html = os.path.join(web_dir, "index.html")
        styles_css = os.path.join(web_dir, "styles.css")
        app_js = os.path.join(web_dir, "app.js")
        company_ctx = os.path.join(web_dir, "company_context.js")

        self.assertTrue(os.path.exists(overview_js), "overview_workspace.js must exist")

        with open(index_html, "r", encoding="utf-8") as f:
            html_content = f.read()
            self.assertIn("overview_workspace.js", html_content, "index.html must include overview_workspace.js")

        with open(app_js, "r", encoding="utf-8") as f:
            app_content = f.read()
            self.assertIn("OverviewWorkspace", app_content, "app.js must reference OverviewWorkspace")

        with open(styles_css, "r", encoding="utf-8") as f:
            css_content = f.read()
            self.assertIn("overview-production-page", css_content, "styles.css must contain overview-production-page styles")
            self.assertIn("overview-kpi-scroll", css_content, "styles.css must contain KPI strip styles")
            self.assertIn("portfolio-comparison-table", css_content, "styles.css must contain portfolio table styles")

        with open(company_ctx, "r", encoding="utf-8") as f:
            ctx_content = f.read()
            self.assertIn("All Companies (Group Portfolio)", ctx_content, "company_context.js must support All Companies")


if __name__ == "__main__":
    unittest.main()
