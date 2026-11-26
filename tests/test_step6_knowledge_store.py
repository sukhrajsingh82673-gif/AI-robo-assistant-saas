"""
Unit and Integration Tests for Antigravity Sub-Step 6E:
Governed Knowledge Store (zonata.playbook/v1, pgvector search, agentskills.io scanner, crypto-shredding).
"""

import pytest
from core.evolution.knowledge_store import (
    Playbook,
    KnowledgeStoreEngine,
    AgentSkillsIOScanner,
    PlaybookValidationError,
    SkillSecurityRejectionError,
    CryptoShreddedError,
)


class TestStep6KnowledgeStore:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = KnowledgeStoreEngine()

    def test_01_valid_playbook_passes_schema_validation(self):
        """Verifies a fully conformant zonata.playbook/v1 is accepted and validated."""
        pb = Playbook(
            title="S3 Bucket Storage Quarantine Rollback",
            description="Isolates infected S3 objects and rolls back to pristine version",
            author_principal="system",
            tenant_id="tenant_alpha",
            company_id="company_alpha",
            steps=[
                {
                    "step_id": "step_1",
                    "action": "s3_quarantine_object(bucket, key)",
                    "rollback_action": "s3_restore_object(bucket, key)",
                }
            ],
            preconditions={"storage_enabled": True},
            postconditions={"object_quarantined": True},
            provenance={"source_id": "incident_123", "signature": "ed25519_sig_valid"},
            global_playbook=True,
        )
        assert pb.schema_version == "zonata.playbook/v1"
        assert len(pb.steps) == 1
        assert pb.global_playbook is True

    def test_02_malformed_playbook_missing_rollback_or_provenance_rejected(self):
        """Rule 1: Steps must have rollback_action; provenance is mandatory."""
        # Missing rollback_action
        with pytest.raises(PlaybookValidationError) as exc:
            Playbook(
                title="Irreversible Action Playbook",
                description="Lacks rollback",
                author_principal="model",
                tenant_id="t1",
                company_id="c1",
                steps=[{"step_id": "s1", "action": "delete_all()"}],
                provenance={"source_id": "test"},
            )
        assert "missing mandatory rollback_action" in str(exc.value)

        # Missing provenance
        with pytest.raises(PlaybookValidationError) as exc:
            Playbook(
                title="Unprovenanced Playbook",
                description="Lacks source signature",
                author_principal="model",
                tenant_id="t1",
                company_id="c1",
                steps=[{"step_id": "s1", "action": "do_something()", "rollback_action": "undo()"}],
                provenance={},
            )
        assert "requires valid cryptographic provenance" in str(exc.value)

    def test_03_embedding_similarity_retrieval_returns_relevant_playbook(self):
        """Verifies semantic similarity retrieval surfaces the relevant playbook."""
        pb_stripe = Playbook(
            title="Stripe Payment Webhook Signature Reconciliation",
            description="Handles HMAC signature verification failures on Stripe incoming webhooks",
            author_principal="system",
            tenant_id="system",
            company_id="system",
            steps=[{"step_id": "s1", "action": "verify_header()", "rollback_action": "drop_conn()"}],
            provenance={"source_id": "stripe_fix"},
            global_playbook=True,
        )
        pb_postgres = Playbook(
            title="PostgreSQL Read Replica Failover",
            description="Promotes standby database node during primary database connection timeout",
            author_principal="system",
            tenant_id="system",
            company_id="system",
            steps=[{"step_id": "s1", "action": "promote_replica()", "rollback_action": "demote()"}],
            provenance={"source_id": "db_fix"},
            global_playbook=True,
        )

        self.engine.save_playbook(pb_stripe)
        self.engine.save_playbook(pb_postgres)

        results = self.engine.search_similar(
            caller_tenant_id="tenant_consumer",
            query_text="Stripe Payment Webhook Signature Reconciliation",
            top_k=1,
        )
        assert len(results) == 1
        assert "Stripe" in results[0]["title"]
        assert results[0]["similarity_score"] >= 0.70

    def test_04_cross_tenant_isolation_prevents_leakage_with_rls(self):
        """Rule 45: Tenant B cannot retrieve Tenant A's private playbooks."""
        pb_alpha = Playbook(
            title="Confidential Corporate Strategy Execution",
            description="Internal strategic restructuring procedures",
            author_principal="human",
            tenant_id="tenant_alpha",
            company_id="company_alpha",
            steps=[{"step_id": "s1", "action": "reassign_seats()", "rollback_action": "restore_seats()"}],
            provenance={"source_id": "ceo_directive"},
            global_playbook=False,
        )
        pb_id = self.engine.save_playbook(pb_alpha)

        # Tenant Alpha can access
        retrieved = self.engine.get_playbook(pb_id, caller_tenant_id="tenant_alpha")
        assert retrieved["title"] == "Confidential Corporate Strategy Execution"

        # Tenant Beta direct retrieval rejected
        with pytest.raises(PermissionError) as exc:
            self.engine.get_playbook(pb_id, caller_tenant_id="tenant_beta")
        assert "Cross-tenant access denied" in str(exc.value)

        # Tenant Beta search returns 0 results
        search_results = self.engine.search_similar(
            caller_tenant_id="tenant_beta",
            query_text="Confidential Corporate Strategy Execution",
        )
        assert len(search_results) == 0

    def test_05_agentskills_io_scanner_admits_clean_and_rejects_dangerous_skills(self):
        """Scanner admits clean sandbox skills and strictly denies root, eval, and unconstrained egress."""
        # 1. Clean skill
        clean_manifest = {
            "name": "currency_converter",
            "version": "1.2.0",
            "permissions": ["http_read"],
            "network": {"unrestricted": False, "allowed_hosts": ["api.exchangerate.host"]},
            "entrypoint": "convert.py",
        }
        res = AgentSkillsIOScanner.scan_manifest(clean_manifest)
        assert res["status"] == "PASS"

        # 2. Dangerous: sudo command
        sudo_manifest = {
            "name": "package_installer",
            "permissions": ["system"],
            "setup_command": "sudo apt-get install -y netcat",
        }
        with pytest.raises(SkillSecurityRejectionError) as exc:
            AgentSkillsIOScanner.scan_manifest(sudo_manifest)
        assert "prohibited security token 'sudo'" in str(exc.value)

        # 3. Dangerous: eval code injection
        eval_manifest = {
            "name": "dynamic_math",
            "code": "result = eval(user_input_expression)",
        }
        with pytest.raises(SkillSecurityRejectionError) as exc:
            AgentSkillsIOScanner.scan_manifest(eval_manifest)
        assert "prohibited security token 'eval('" in str(exc.value)

        # 4. Dangerous: unrestricted network
        net_manifest = {
            "name": "web_crawler",
            "network": {"unrestricted": True},
        }
        with pytest.raises(SkillSecurityRejectionError) as exc:
            AgentSkillsIOScanner.scan_manifest(net_manifest)
        assert "Unrestricted outbound network access requested" in str(exc.value)

    def test_06_crypto_shredding_renders_tenant_playbooks_unreadable(self):
        """Rule 46: Wiping the tenant DEK crypto-shreds all tenant playbooks."""
        tenant = "tenant_to_erase"
        pb = Playbook(
            title="Archived Payroll Process",
            description="Payroll automation steps",
            author_principal="human",
            tenant_id=tenant,
            company_id="company_x",
            steps=[{"step_id": "s1", "action": "pay()", "rollback_action": "cancel()"}],
            provenance={"source_id": "hr_doc"},
        )
        pb_id = self.engine.save_playbook(pb)

        # Verifiable before shredding
        res = self.engine.get_playbook(pb_id, caller_tenant_id=tenant)
        assert res["title"] == "Archived Payroll Process"

        # Execute DSAR crypto-shred
        shredded = self.engine.shred_tenant_keys(tenant)
        assert shredded is True

        # Subsequent read must fail with CryptoShreddedError
        with pytest.raises(CryptoShreddedError) as exc:
            self.engine.get_playbook(pb_id, caller_tenant_id=tenant)
        assert "destroyed" in str(exc.value)

    def test_07_mutation_check_tenant_cannot_set_global_true(self):
        """Mutation test: global: true can ONLY be set by 'system' principal."""
        with pytest.raises(PlaybookValidationError) as exc:
            Playbook(
                title="Unauthorized Global Override",
                description="Non-system principal trying to go global",
                author_principal="tenant_admin",
                tenant_id="tenant_attacker",
                company_id="company_attacker",
                steps=[{"step_id": "s1", "action": "modify_dns()", "rollback_action": "revert()"}],
                provenance={"source_id": "attack"},
                global_playbook=True,
            )
        assert "Only 'system' principal may author global playbooks" in str(exc.value)
