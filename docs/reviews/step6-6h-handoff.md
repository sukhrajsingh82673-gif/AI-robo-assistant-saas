# Sub-step 6H Handoff Dossier — Clean-Room Tool Replication Protocol

## 1. Summary of Changes
- Implemented `core/evolution/clean_room.py`:
  - `DecisionLadder`: Prioritized tool acquisition ladder (Open-source -> Official Vendor API -> Clean-room -> Infeasible).
  - `ProvenanceLedger`: Cryptographic provenance registration (`PUBLIC_DOC`, `OPEN_SOURCE`, `OWNER_AUTHORED`, `BLACK_BOX_OBSERVATION`) requiring every spec requirement to cite non-prohibited records.
  - `ProhibitedInputDetector`: Detects and rejects decompiled/disassembled binaries, crack/keygen indicators, and illicit source dumps under Rule 55.
  - `AirGappedSpecifier` & `AirGappedImplementer`: Air-gapped boundary ensuring Implementers have zero read access to raw vendor documents, binaries, or assets.
  - `CodeSimilarityAuditor`: N-gram token overlap analysis catching plagiarized identifiers and function structure.
  - `CleanRoomLegalGate`: Evaluates vendor Terms of Service for anti-reverse-engineering clauses and enforces mandatory human owner sign-off.
- Added comprehensive unit and integration tests in `tests/test_step6_clean_room.py` (8 tests).
- Updated `.github/workflows/ci-evolution.yml` to include `tests/test_step6_clean_room.py`.
- Updated `docs/reports/STEP6_REPORT.md` with complete Sub-step 6H verification records.

## 2. Git Diff Stat
```text
 .github/workflows/ci-evolution.yml |   4 +-
 docs/reports/STEP6_REPORT.md       |  25 ++++
 core/evolution/clean_room.py       | 335 +++++++++++++++++++++++++++++++++++++
 tests/test_step6_clean_room.py     | 185 +++++++++++++++++++++++++++
 4 files changed, 547 insertions(+), 2 deletions(-)
```

## 3. Commands to Re-run
```bash
python -m pytest tests/test_step6_clean_room.py -v
python -m pytest tests/test_step6_preservation_contract.py -v
```

## 4. Claims and Verification
1. **Decision Ladder (First Match Wins):** Open-source alternative takes precedence over API and clean-room replication. Verified in `test_01_decision_ladder_chooses_open_source_first` and `test_02_decision_ladder_falls_through_to_clean_room`.
2. **Rule 55 Prohibition on Decompiled Code & Cracks:** Decompiled Ghidra/IDA dumps or keygens rejected with `ProhibitedInputError`. Verified in `test_03_prohibited_input_detector_rejects_decompiled_code` and `test_08_mutation_check_unauthorized_crack_or_keygen_blocked`.
3. **Mandatory Provenance Citation (Rule 53):** Every requirement in `CleanRoomSpec` traces to registered provenance. Verified in `test_04_provenance_ledger_verifies_all_spec_requirements_cited`.
4. **Air-Gap Separation (Spy Test):** Implementer session blocked from reading raw vendor docs or URLs. Verified in `test_05_air_gapped_implementer_blocks_raw_source_reads_spy_test`.
5. **Code Plagiarism Detection:** Candidate sharing proprietary tokens/structure rejected with `CodePlagiarismDetectedError`. Verified in `test_06_similarity_auditor_flags_planted_licensed_code`.
6. **Legal Gate & Human Authorization:** Restrictive ToS blocks automated progression; human owner override required. Verified in `test_07_legal_gate_blocks_tos_restricted_tools_without_owner`.
7. **Preservation Contract (Rule 49):** Working tree integrity verified against `STEP1-5_BASELINE.json`. Zero legacy files touched.

## 5. Mutation Checks Performed
- Input containing keygen/patcher keywords rejected.
- Specifier referencing unprovenanced requirement fails.
- Implementer attempting read of vendor source raises `AirGapBoundaryViolationError`.
- Plagiarized code snippet triggers `CodePlagiarismDetectedError`.

## 6. Known Gaps
- None. Fully self-contained, no external network dependencies, 100% passing tests.
