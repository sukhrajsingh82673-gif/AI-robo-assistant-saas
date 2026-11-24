"""
Unit and Integration Tests for Sub-Step 6H: Clean-Room Tool Replication Protocol.
"""

import pytest
from core.evolution.clean_room import (
    ProvenanceTrustClass,
    DecisionLadderStep,
    DecisionLadder,
    ProvenanceLedger,
    ProhibitedInputError,
    AirGapBoundaryViolationError,
    LegalGateBlockedError,
    CodePlagiarismDetectedError,
    AirGappedSpecifier,
    AirGappedImplementer,
    CodeSimilarityAuditor,
    CleanRoomLegalGate,
)


class TestStep6CleanRoom:

    def test_01_decision_ladder_chooses_open_source_first(self):
        """Decision ladder picks Open-Source alternative (Step 1) whenever available."""
        step = DecisionLadder.select_ladder_step(
            has_open_source_alternative=True,
            has_affordable_vendor_api=True,
            clean_room_feasible=True,
        )
        assert step == DecisionLadderStep.OPEN_SOURCE_ALTERNATIVE

    def test_02_decision_ladder_falls_through_to_clean_room(self):
        """Decision ladder falls back to Clean-Room build (Step 3) when OSS and API are absent."""
        step = DecisionLadder.select_ladder_step(
            has_open_source_alternative=False,
            has_affordable_vendor_api=False,
            clean_room_feasible=True,
        )
        assert step == DecisionLadderStep.CLEAN_ROOM_REPLICATION

        # When clean room is not feasible, returns COMMERCIALLY_INFEASIBLE
        step_infeasible = DecisionLadder.select_ladder_step(
            has_open_source_alternative=False,
            has_affordable_vendor_api=False,
            clean_room_feasible=False,
        )
        assert step_infeasible == DecisionLadderStep.COMMERCIALLY_INFEASIBLE

    def test_03_prohibited_input_detector_rejects_decompiled_code(self):
        """Decompiled or disassembled binaries are rejected with ProhibitedInputError (Rule 55)."""
        ledger = ProvenanceLedger()
        decompiled_sample = """
/* Decompiled by Ghidra */
int sub_00401020(void) {
    __asm { mov eax, 1 }
    return 0;
}
"""
        with pytest.raises(ProhibitedInputError) as exc_info:
            ledger.register_input(
                source_name="vendor_binary_dump.c",
                content=decompiled_sample,
                trust_class=ProvenanceTrustClass.PROHIBITED,
            )
        assert "DECOMPILED_OR_DISASSEMBLED_CODE_DETECTED" in str(exc_info.value)

    def test_04_provenance_ledger_verifies_all_spec_requirements_cited(self):
        """Air-gapped specifier verifies that every requirement traces to an allowed provenance record."""
        ledger = ProvenanceLedger()
        rec1 = ledger.register_input(
            source_name="rfc_format_spec.md",
            content="# Standard Data Format\nDefines JSON serialization and timestamp RFC3339.",
            trust_class=ProvenanceTrustClass.PUBLIC_DOC,
        )
        rec2 = ledger.register_input(
            source_name="owner_user_stories.md",
            content="# User Requirements\nNeed ability to parse CSV and export JSON.",
            trust_class=ProvenanceTrustClass.OWNER_AUTHORED,
        )

        requirements = [
            {"id": "REQ-01", "description": "Parse RFC3339 timestamps", "provenance_id": rec1.record_id},
            {"id": "REQ-02", "description": "Export parsed CSV to JSON", "provenance_id": rec2.record_id},
        ]

        spec = AirGappedSpecifier.author_specification("data-transformer-replica", requirements, ledger)
        assert spec.tool_name == "data-transformer-replica"
        assert len(spec.requirements) == 2
        assert len(spec.acceptance_tests) == 2

    def test_05_air_gapped_implementer_blocks_raw_source_reads_spy_test(self):
        """Spy test: implementer session is blocked from reading vendor documentation or raw source."""
        ledger = ProvenanceLedger()
        rec = ledger.register_input(
            source_name="public_api.md",
            content="API endpoint description",
            trust_class=ProvenanceTrustClass.PUBLIC_DOC,
        )
        spec = AirGappedSpecifier.author_specification(
            "csv-cleaner",
            [{"id": "REQ-1", "provenance_id": rec.record_id}],
            ledger,
        )

        implementer = AirGappedImplementer(spec)
        implementer.register_forbidden_context("proprietary_vendor_docs.pdf")

        with pytest.raises(AirGapBoundaryViolationError):
            implementer.attempt_source_read("proprietary_vendor_docs.pdf")

        with pytest.raises(AirGapBoundaryViolationError):
            implementer.attempt_source_read("http://vendor.example.com/api_internal_docs")

    def test_06_similarity_auditor_flags_planted_licensed_code(self):
        """Code similarity auditor detects copied proprietary identifiers and functions."""
        vendor_code = """
def calculate_vendor_proprietary_weighted_distribution_matrix(quantum_scalar_alpha, matrix_tensor_beta):
    intermediate_vector_cache = [quantum_scalar_alpha * i for i in matrix_tensor_beta]
    return intermediate_vector_cache
"""
        # Candidate code that improperly copied unique identifiers
        plagiarized_code = """
def candidate_implementation(quantum_scalar_alpha, matrix_tensor_beta):
    intermediate_vector_cache = [quantum_scalar_alpha * i for i in matrix_tensor_beta]
    return intermediate_vector_cache
"""
        with pytest.raises(CodePlagiarismDetectedError) as exc_info:
            CodeSimilarityAuditor.audit_similarity(plagiarized_code, vendor_code, threshold=0.30)
        assert "Code similarity threshold breached" in str(exc_info.value)

        # Clean independent implementation
        clean_code = """
def compute_weighted_series(factor, dataset):
    results = []
    for item in dataset:
        results.append(item * factor)
    return results
"""
        res = CodeSimilarityAuditor.audit_similarity(clean_code, vendor_code, threshold=0.30)
        assert res["plagiarism_detected"] is False

    def test_07_legal_gate_blocks_tos_restricted_tools_without_owner(self):
        """When vendor ToS prohibits reverse engineering, automated agents and non-owners are blocked."""
        restrictive_terms = """
Section 12.1: The licensee shall not decompile, disassemble, or reverse engineer any portion
of the software or protocol. Automated scraping or extraction is strictly forbidden.
"""
        eval_res = CleanRoomLegalGate.evaluate_terms(restrictive_terms)
        assert eval_res["prohibits_reverse_engineering"] is True

        # Non-owner principal is blocked
        with pytest.raises(LegalGateBlockedError):
            CleanRoomLegalGate.check_owner_authorization("agent:specifier", eval_res)

        # Human non-owner is blocked on restricted terms
        with pytest.raises(LegalGateBlockedError):
            CleanRoomLegalGate.check_owner_authorization("human:engineer_alice", eval_res)

        # Human owner override succeeds
        authorized = CleanRoomLegalGate.check_owner_authorization("owner:sukhraj_legal_signoff", eval_res)
        assert authorized is True

    def test_08_mutation_check_unauthorized_crack_or_keygen_blocked(self):
        """Inputs mentioning keygens, patches, or license bypass are immediately rejected."""
        ledger = ProvenanceLedger()
        malicious_input = "Instructions: Run keygen.exe to bypass_license on server startup."
        with pytest.raises(ProhibitedInputError) as exc_info:
            ledger.register_input(
                source_name="activation_crack.txt",
                content=malicious_input,
                trust_class=ProvenanceTrustClass.PROHIBITED,
            )
        assert "CRACK_OR_LICENSE_BYPASS_INDICATOR_DETECTED" in str(exc_info.value)
