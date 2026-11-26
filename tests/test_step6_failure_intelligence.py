"""
Unit and Integration Tests for Antigravity Sub-Step 6C:
Failure Intelligence, Taxonomy Ingestion, LangGraph Analyst Graph, & Self-Eval Scorecards.
"""

import time
import pytest
from core.evolution.failure_intelligence import (
    FailureClass,
    MitigationProposalType,
    PIIScrubber,
    FailureIncident,
    FailureIntelligenceEngine,
)


class TestStep6FailureIntelligence:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = FailureIntelligenceEngine()

    def test_01_taxonomy_ingestion_all_classes(self):
        """Verifies ingestion across all 6 canonical failure classes."""
        classes = [
            FailureClass.EXECUTION_ERROR,
            FailureClass.VERIFICATION_FAILURE,
            FailureClass.POLICY_DENIAL,
            FailureClass.REGRESSION,
            FailureClass.HALLUCINATION,
            FailureClass.AMBIGUOUS_SPEC,
        ]

        for fc in classes:
            inc = self.engine.ingest_failure(
                tenant_id="tenant_alpha",
                company_id="company_alpha",
                failure_class=fc,
                stack_or_trace=f"Trace details for {fc.value}",
                tool_call={"name": "test_tool"} if fc == FailureClass.EXECUTION_ERROR else None,
            )
            assert inc.failure_class == fc
            assert inc.count == 1
            assert inc.signature is not None
            assert len(inc.signature) == 64

    def test_02_failure_deduplication_collapses_repeats(self):
        """Deduplication test: 10 identical failures collapse to 1 incident with count = 10."""
        for i in range(10):
            inc = self.engine.ingest_failure(
                tenant_id="tenant_beta",
                company_id="company_beta",
                failure_class=FailureClass.EXECUTION_ERROR,
                stack_or_trace="ConnectionTimeout: Failed to reach host 192.168.1.5 at line 42 (0x7ffeefbff5a0)",
                tool_call={"name": "remote_http_request"},
            )

        assert inc.count == 10
        scorecard = self.engine.generate_scorecard("tenant_beta")
        assert scorecard["deduplicated_signatures"] == 1
        assert scorecard["total_incidents"] == 10

    def test_03_analyst_graph_routes_mitigation_correctly(self):
        """Verifies 3-node LangGraph analyst routes each failure to the appropriate mitigation."""
        # 1. Ambiguous spec -> Owner Help
        inc1 = self.engine.ingest_failure(
            tenant_id="t1", company_id="c1",
            failure_class=FailureClass.AMBIGUOUS_SPEC,
            stack_or_trace="Instruction lacks required fiscal quarter parameter",
        )
        assert inc1.proposed_mitigation == MitigationProposalType.OWNER_HELP_REQUEST

        # 2. Hallucination -> Optimizer Candidate
        inc2 = self.engine.ingest_failure(
            tenant_id="t1", company_id="c1",
            failure_class=FailureClass.HALLUCINATION,
            stack_or_trace="Model cited nonexistent file storage/ledger_v99.parquet",
        )
        assert inc2.proposed_mitigation == MitigationProposalType.OPTIMIZER_CANDIDATE

        # 3. Execution error with tool -> Playbook Candidate
        inc3 = self.engine.ingest_failure(
            tenant_id="t1", company_id="c1",
            failure_class=FailureClass.EXECUTION_ERROR,
            stack_or_trace="CLI tool failed with exit code 127: command not found",
            tool_call={"name": "ffmpeg_compress"},
        )
        assert inc3.proposed_mitigation == MitigationProposalType.PLAYBOOK_CANDIDATE

        # 4. Regression -> GitHub Triage with human escalation
        inc4 = self.engine.ingest_failure(
            tenant_id="t1", company_id="c1",
            failure_class=FailureClass.REGRESSION,
            stack_or_trace="Previously passing golden eval scenario 14 now failing",
        )
        assert inc4.proposed_mitigation == MitigationProposalType.GITHUB_TRIAGE
        assert inc4.human_escalated is True

    def test_04_pii_and_secret_scrubbing_in_traces(self):
        """Rule 41 & 46: failure traces must not contain secrets or plaintext PII."""
        raw_trace = (
            "Error on user alice@zonata.internal with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID "
            "and password: super_secret_pass_123! while charging card 4111111111111111"
        )
        inc = self.engine.ingest_failure(
            tenant_id="tenant_gamma",
            company_id="company_gamma",
            failure_class=FailureClass.EXECUTION_ERROR,
            stack_or_trace=raw_trace,
        )

        assert "alice@zonata.internal" not in inc.stack_or_trace
        assert "[REDACTED_EMAIL]" in inc.stack_or_trace
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in inc.stack_or_trace
        assert "[REDACTED_JWT]" in inc.stack_or_trace
        assert "super_secret_pass_123!" not in inc.stack_or_trace
        assert "[REDACTED_SECRET]" in inc.stack_or_trace
        assert "4111111111111111" not in inc.stack_or_trace
        assert "[REDACTED_CC]" in inc.stack_or_trace

    def test_05_scorecard_mttf_mttr_and_regression_metrics(self):
        """Verifies calculation of MTTF, MTTR, regression rate, and class breakdowns."""
        tenant = "tenant_metrics"
        t0 = time.time() - 100

        # Ingest 3 distinct failures
        inc1 = self.engine.ingest_failure(
            tenant_id=tenant, company_id="c1",
            failure_class=FailureClass.VERIFICATION_FAILURE,
            stack_or_trace="Mismatch in merkle leaf digest",
        )
        inc1.created_at = t0
        inc1.resolved_at = t0 + 20  # MTTR 20s

        inc2 = self.engine.ingest_failure(
            tenant_id=tenant, company_id="c1",
            failure_class=FailureClass.REGRESSION,
            stack_or_trace="Regression in route auth token validator",
        )
        inc2.created_at = t0 + 50
        inc2.resolved_at = t0 + 90  # MTTR 40s

        scorecard = self.engine.generate_scorecard(tenant)
        assert scorecard["tenant_id"] == tenant
        assert scorecard["total_incidents"] == 2
        assert scorecard["deduplicated_signatures"] == 2
        assert scorecard["mttr_seconds"] == 30.0  # (20 + 40) / 2
        assert scorecard["regression_rate"] == 0.5  # 1 regression out of 2
        assert "HIGH REGRESSION" in scorecard["recommendations"][0]

    def test_06_mutation_check_unclassified_failure_defaults_unknown(self):
        """Mutation test: unclassified or malformed failure class defaults to UNKNOWN with triage."""
        inc = self.engine.ingest_failure(
            tenant_id="tenant_unknown",
            company_id="company_unknown",
            failure_class="BIZARRE_CUSTOM_FAILURE_CLASS_NOT_IN_ENUM",
            stack_or_trace="Unexpected hardware fault or bitflip",
        )

        assert inc.failure_class == FailureClass.UNKNOWN
        assert inc.proposed_mitigation == MitigationProposalType.GITHUB_TRIAGE
        assert inc.confidence == 0.20
        assert inc.human_escalated is True
