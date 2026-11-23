"""
Step 5I Acceptance Test Suite: End-to-End Qualification Scenario (8 Milestones)
==============================================================================
Validates the complete Step 5 Trust Layer qualification scenario, ensuring every
security mechanism, secrets provider, identity control, database transaction scope,
WAF/SBOM defense, SIEM audit chain, containment playbook, and crypto algorithm
meets the rigorous constitutional standards of OpenCode Step 5.
"""

import os
import unittest

from scripts.step5_scenario import (
    run_all,
    run_milestone_1,
    run_milestone_2,
    run_milestone_3,
    run_milestone_4,
    run_milestone_5,
    run_milestone_6,
    run_milestone_7,
    run_milestone_8,
)


class TestStep5QualificationScenario(unittest.TestCase):
    """Sub-Step 5I Test Suite executing all 8 qualification milestones."""

    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        os.environ["APP_ENV"] = "test"

    def test_milestone_01_preflight_and_governance(self):
        """Milestone 1: Preflight Reality Check & Security Inventory (5A)."""
        self.assertTrue(run_milestone_1())

    def test_milestone_02_secrets_platform(self):
        """Milestone 2: OpenBao Secrets Platform & Transit KMS (5B)."""
        self.assertTrue(run_milestone_2())

    def test_milestone_03_identity_and_access(self):
        """Milestone 3: Identity & Access — Keycloak/OIDC, Workload & Ownership (5C)."""
        self.assertTrue(run_milestone_3())

    def test_milestone_04_database_isolation(self):
        """Milestone 4: Database & Tenant Isolation Hardening — Transaction-Scoped RLS (5D)."""
        self.assertTrue(run_milestone_4())

    def test_milestone_05_app_and_supply_chain(self):
        """Milestone 5: Application & Supply-Chain Security — ASVS, WAF, SBOM & Cosign (5E)."""
        self.assertTrue(run_milestone_5())

    def test_milestone_06_audit_and_compliance(self):
        """Milestone 6: SIEM Audit Logging, Privacy Engineering & Rule 46 Control Matrix (5F)."""
        self.assertTrue(run_milestone_6())

    def test_milestone_07_incident_response(self):
        """Milestone 7: Incident Response Playbooks & Security Resilience Chaos Drills (5G)."""
        self.assertTrue(run_milestone_7())

    def test_milestone_08_crypto_agility(self):
        """Milestone 8: Cryptographic Agility, PQC Hybrid Envelopes & Online Rewrapping (5H)."""
        self.assertTrue(run_milestone_8())

    def test_milestone_09_full_qualification_pipeline(self):
        """Milestone 9: Complete End-to-End Qualification Pipeline Under 5,000ms Budget."""
        self.assertTrue(run_all())
