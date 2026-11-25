"""
Tests for Sub-Step 9I: Marketplace Foundations, Sandboxing, Review Pipeline, and Revocation (Rule 81).
"""

import pytest
from core.marketplace.manifest import MarketplaceManifest, CapabilityRequirement
from core.marketplace.registry import MarketplaceRegistry, PackageReviewStatus
from core.marketplace.sandbox import MarketplaceSandbox, SandboxViolationError
from core.marketplace.revocation import PackageRevocationEngine


class TestStep9iMarketplace:

    def test_marketplace_manifest_schema_and_digest(self):
        """Verify zonata.marketplace-package/v1 schema parsing and SHA-256 digest calculation."""
        raw_manifest = {
            "schema_version": "zonata.marketplace-package/v1",
            "package_id": "com.partner.quickbooks-sync",
            "name": "QuickBooks Cloud Sync",
            "version": "1.2.0",
            "publisher": "Intuit Partner Network",
            "description": "Bidirectional ledger synchronization for finance departments",
            "entrypoint": "main.py:sync_handler",
            "capabilities_requested": [
                {"capability": "storage:read", "resource": "invoices", "justification": "Read invoices to sync"},
                {"capability": "network:egress", "resource": "api.intuit.com", "justification": "Egress to Intuit API"},
            ],
            "pricing_type": "free",
        }

        manifest = MarketplaceManifest.from_dict(raw_manifest)
        assert manifest.package_id == "com.partner.quickbooks-sync"
        assert len(manifest.capabilities_requested) == 2
        digest = manifest.compute_digest()
        assert len(digest) == 64

        # Invalid schema version rejection
        bad_manifest = dict(raw_manifest)
        bad_manifest["schema_version"] = "v2_experimental"
        with pytest.raises(ValueError, match="Unsupported manifest schema version"):
            MarketplaceManifest.from_dict(bad_manifest)

    def test_security_review_static_analysis_and_rejection(self):
        """Verify automated scanner detects hostile constructs (eval, exec, os.system) (Rule 81)."""
        registry = MarketplaceRegistry()

        manifest = MarketplaceManifest(
            package_id="ext.clean",
            name="Clean Extension",
            version="1.0.0",
            publisher="Safe Dev",
            description="Safe calculations",
            entrypoint="app.py",
            capabilities_requested=[CapabilityRequirement("compute", None, "Math")],
        )

        # 1. Clean code is APPROVED
        clean_code = "def add(a, b):\n    return a + b\n"
        res_clean = registry.submit_package(manifest, clean_code)
        assert res_clean["review_status"] == PackageReviewStatus.APPROVED

        # 2. Hostile code with eval() is REJECTED
        manifest_hostile = MarketplaceManifest(
            package_id="ext.hostile",
            name="Malicious Extension",
            version="1.0.0",
            publisher="Attacker",
            description="Sneaky",
            entrypoint="exploit.py",
            capabilities_requested=[],
        )
        hostile_code = "def run():\n    eval('__import__(\"os\").system(\"id\")')\n"
        res_hostile = registry.submit_package(manifest_hostile, hostile_code)
        assert res_hostile["review_status"] == PackageReviewStatus.REJECTED
        assert any("eval" in reason for reason in res_hostile["rejection_reasons"])

    def test_installation_and_commercial_truth(self):
        """Verify free packages install and paid listings report NOT_IMPLEMENTED per truth rule."""
        registry = MarketplaceRegistry()

        # Free package
        pkg_free = MarketplaceManifest(
            package_id="ext.free_tool",
            name="Free Helper",
            version="1.0.0",
            publisher="Community",
            description="Helper",
            entrypoint="main.py",
            capabilities_requested=[],
            pricing_type="free",
        )
        registry.submit_package(pkg_free, "print('hello')")
        inst = registry.install_package("tenant_alpha", "ext.free_tool", "1.0.0", [])
        assert inst["status"] == "INSTALLED"

        # Paid package -> Truth rule: NOT_IMPLEMENTED
        pkg_paid = MarketplaceManifest(
            package_id="ext.premium_analytics",
            name="Premium BI",
            version="2.0.0",
            publisher="BI Corp",
            description="Enterprise Analytics",
            entrypoint="bi.py",
            capabilities_requested=[],
            pricing_type="paid",
            price_cents=4900,
        )
        registry.submit_package(pkg_paid, "print('bi')")
        with pytest.raises(NotImplementedError, match="NOT_IMPLEMENTED"):
            registry.install_package("tenant_alpha", "ext.premium_analytics", "2.0.0", [])

    def test_capability_sandbox_enforcement_and_network_egress(self):
        """Verify sandbox strictly blocks ungranted capabilities and unauthorized network egress."""
        # Granted storage:read and network:egress:api.partner.com
        sandbox = MarketplaceSandbox(
            tenant_id="tenant_sandbox",
            package_id="ext.partner",
            granted_capabilities=["storage:read", "network:egress:api.partner.com"],
        )

        # 1. Permitted operation
        op1 = sandbox.execute_operation("storage:read", "invoices")
        assert op1["status"] == "SUCCESS"

        # 2. Denied operation (lacks storage:write)
        with pytest.raises(SandboxViolationError, match="lacks required capability 'storage:write'"):
            sandbox.execute_operation("storage:write", "invoices")

        # 3. Permitted egress to declared partner domain
        op2 = sandbox.execute_operation("network:egress", "api.partner.com")
        assert op2["status"] == "SUCCESS"

        # 4. Denied egress to undeclared domain
        with pytest.raises(SandboxViolationError, match="Egress to domain 'malicious-data-exfil.org' is prohibited"):
            sandbox.execute_operation("network:egress", "malicious-data-exfil.org")

    def test_instant_revocation_engine_sla(self):
        """Verify instantaneous (< 1s) package revocation invalidates all active runtimes."""
        rev_engine = PackageRevocationEngine()
        sandbox1 = MarketplaceSandbox("tenant_1", "ext.vulnerable", ["storage:read"])
        sandbox2 = MarketplaceSandbox("tenant_2", "ext.vulnerable", ["storage:read"])
        rev_engine.register_active_sandbox(sandbox1)
        rev_engine.register_active_sandbox(sandbox2)

        # Execute before revocation: works
        assert sandbox1.execute_operation("storage:read")["status"] == "SUCCESS"

        # Revoke globally
        res = rev_engine.revoke_package_globally(
            package_id="ext.vulnerable",
            reason="CVE-2026-8888 Remote code vulnerability",
            operator_id="op_security_lead",
        )
        assert res["status"] == "REVOKED"
        assert res["runtimes_terminated"] == 2
        assert res["revoked_within_sla"] is True  # Took < 1000ms

        # Immediate subsequent execution on running instance FAILS
        with pytest.raises(SandboxViolationError, match="Package 'ext.vulnerable' has been revoked"):
            sandbox1.execute_operation("storage:read")

        with pytest.raises(SandboxViolationError, match="Package 'ext.vulnerable' has been revoked"):
            sandbox2.execute_operation("storage:read")
