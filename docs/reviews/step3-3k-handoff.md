# OpenCode Step 3K Handoff — Golden Evals & Final Step 3 Qualification Scenario

## 1. Summary of Work Delivered
Sub-Step 3K delivers the final qualification scenario (`scripts/step3_scenario.py`) for OpenCode Step 3 (Hands), exercising all 10 sovereign hands components against the standing rules:
- **Milestone 1:** Preflight & Capability Truth — Validates 18 standard capabilities probed against the reality table (Rule 30).
- **Milestone 2:** Host Permission Model & Pairing (3B) — Sovereign Ed25519 key generation, one-time pairing code with human step-up auth, and local host grant enforcement (Rule 23).
- **Milestone 3:** Desktop Perception & Control (3C) — Layer 1 OS Accessibility Tree parsing, relative coordinate transformation, password & secret masking on host, visual masking, out-of-grant coordinate boundary rejection (Rule 24, 28).
- **Milestone 4:** Origin-Bound Credential Vault (3D) — Origin-bound late-binding credential injection, cross-origin mismatch rejection, zero plaintext export invariant (Rule 24).
- **Milestone 5:** Governed Browser Engine & Download Scanning (3E) — Local fixture login, untrusted page content delimiting (`<<<PAGE_CONTENT>>>`), ClamAV quarantine scanning, executable download blocking (Rule 26, 32).
- **Milestone 6:** Anti-Evasion Policy & Rate Limiting (3F) — AST repository hygiene scan, proxy rotation denial, challenge detection halting and human handoff (Rule 25).
- **Milestone 7:** Remote View & Human Takeover (3G) — Viewport-bounded frame streaming, pre-transmission masking, agent command suppression during takeover, explicit state assertion handback (Rule 27, 28).
- **Milestone 8:** Research Hand & Search Provider (3H) — SearchPort query resolution, delimited citation containment (`<<<SEARCH_RESULTS>>>`), prompt injection neutralization (Rule 26, 30).
- **Milestone 9:** Terminal Governance & Safety Controls (3I) — Strict denial of dangerous commands (`sudo`, `rm -rf /`, `curl | sh`), human approval gating for high-impact commands, safe delimited execution (Rule 23, 27).
- **Milestone 10:** Agent Factory Import Lane & Sandboxing (3J) — Permissive open-source license gating (Rule 5), AST and ClamAV code scanning, scratch directory isolation and cleanup (Rule 32).

---

## 2. Files Changed & Impact Analysis
- `scripts/step3_scenario.py`: Full end-to-end qualification scenario script covering all 10 milestones.
- `.github/workflows/ci.yml`: Added `python3 scripts/step3_scenario.py` under both `sqlite_dev_tests` and `contract_and_postgres_tests`.
- `docs/reports/STEP3_REPORT.md`: Appended Sub-Step 3K report section with real command outputs.
- `docs/reviews/step3-3k-handoff.md`: This handoff document.
- `docs/reviews/step3-3k-review.md`: Independent reviewer evaluation.

---

## 3. Verification Commands & Outputs
```bash
python3 scripts/step3_scenario.py
======================================================================
STEP 3 QUALIFICATION SCENARIO: 10/10 MILESTONES PASSED [GREEN]
======================================================================

pytest tests/test_step3* -q
======================================================================
67 passed in 23.29s

python3 scripts/anti_evasion_linter.py
======================================================================
[PASS] Zero Rule 25 anti-evasion or captcha solver violations found.
```

---

## 4. Mutation Checks & Invariant Guarantees
- **Host-Side Enforcement (Rule 23):** Tested that coordinate dispatches exceeding granted bounds raise `OutOfGrantCoordinatesError`.
- **Zero Export Invariant (Rule 24):** Tested that calling `vault.export_secret()` raises `SecretExportForbiddenError`.
- **Rule 25 Anti-Evasion:** Verified that `scan_repository_anti_evasion()` passes with 0 violations across the entire repo.
- **Rule 26 Content Delimiting:** Verified `<<<PAGE_CONTENT>>>`, `<<<SEARCH_RESULTS>>>`, and `<<<TERMINAL_OUTPUT>>>` formatting.
- **Rule 27 Human Takeover:** Verified that human takeover suppresses agent commands with `AgentExecutionSuppressedError`.
- **Rule 32 Antivirus & Sandboxing:** Verified ClamAV scan and scratch isolation.
