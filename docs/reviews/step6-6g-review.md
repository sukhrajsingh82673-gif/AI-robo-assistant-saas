# Sub-step 6G Independent Review Dossier — Open-Source Agent and Tool Intake ("Agent Zoo")

**Reviewer:** OpenCode (Independent Architecture & Security Reviewer)
**Sub-step:** 6G (Open-Source Agent and Tool Intake)
**Commit Target:** `step6-evolution`

---

### 1. Review Summary & Decision
- **Status:** **PASS**
- **Preservation Contract (Rule 49):** Strictly respected. All code additions are located in `core/evolution/intake.py` and `tests/test_step6_intake.py`. Zero modifications to Step 1-5 baselines.
- **Supply Chain Security & Rule 32 Compliance:** Confirmed. Scanner rejects pipe-to-shell patterns (`curl | sh`, `wget | bash`) and enforces cryptographic hash locks on dependencies.
- **License Boundary (Rule 5):** Confirmed. Permissive licenses are distinguished from AGPL/GPL `BOUNDARY` components.
- **Human Governance Gate (Rule 53, Rule 57):** Confirmed. Promotion to `ACTIVE` is strictly restricted to human/owner principals.
- **Behavioral Sandbox & Capability Reconciliation:** Confirmed. Egress restriction and declared capability verification operate properly.

---

### 2. Verification Checklist
- [x] State machine properly quarantines discovered intake candidates.
- [x] Pipe-to-shell installers fail static scan.
- [x] Unpinned or unhashed dependencies fail static scan.
- [x] AGPL-3.0 dependencies flagged as BOUNDARY.
- [x] AST parser detects env secret access and prohibited eval calls.
- [x] Sandbox blocks unauthorized egress and directory traversal writes.
- [x] Human approval gate strictly blocks AI promotion to ACTIVE.
- [x] README prompt injection detected.
- [x] Hermes reference evaluation report generated.
- [x] All 8 intake unit tests pass (46/46 cumulative).

---

### 3. Recommendation
Proceed to commit Sub-step 6G, push to remote branch `step6-evolution`, and monitor CI execution.
