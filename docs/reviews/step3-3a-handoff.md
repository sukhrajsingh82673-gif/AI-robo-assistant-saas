# Sub-Step 3A Handoff: Preflight, Inventory and ADRs

**Sub-Step:** 3A  
**Branch:** `step3-hands`  
**Commit:** Pending 3A commit  
**Author:** Antigravity (Builder)  
**Reviewer:** OpenCode (Reviewer)  
**Date:** 2026-11-22  

---

## 1. Files Changed
```text
docs/architecture/ADR_0002_BROWSER_ENGINE.md         | 60 +++++++++++++++++++
docs/architecture/ADR_0003_PERCEPTION_STRATEGY.md    | 65 ++++++++++++++++++++
docs/architecture/ADR_0004_HOST_AGENT_RUNTIME.md     | 57 ++++++++++++++++++
docs/architecture/ADR_0005_TRANSPORT_PROTOCOL.md     | 53 ++++++++++++++++
docs/architecture/ADR_0006_REMOTE_VIEW_TAKEOVER.md   | 63 ++++++++++++++++++++
docs/architecture/ADR_0007_IMPORT_LANE_SANDBOX.md    | 53 ++++++++++++++++
docs/architecture/ADR_0008_SEARCH_PROVIDER.md        | 57 ++++++++++++++++++
docs/reports/STEP3_INVENTORY.md                      | 68 +++++++++++++++++++++
docs/reports/STEP3_REPORT.md                         | 72 ++++++++++++++++++++++
tests/test_step3_preflight.py                        | 152 ++++++++++++++++++++++++++++++++++++++++++++++
10 files changed, 700 insertions(+)
```

---

## 2. Commands to Re-run
```bash
# Run the Step 3A preflight, inventory, and ADR test suite
python -W ignore -m unittest tests/test_step3_preflight.py
```

---

## 3. Claims Made
1. **Foundation Gate Readiness:** All 8 foundations from Step 1 and Step 2 are confirmed present, importable, and functional (capability truth table, ActionGateway with approvals/killswitch, LLMGateway with VISION tier, tool registry with agent runtime, human inbox with BLOCKED status, document store with reserved scan channel, DurableScheduler, and evidence ledger).
2. **Codebase Inventory Complete:** `docs/reports/STEP3_INVENTORY.md` exhaustively categorizes all browser, desktop, terminal, secret, and import lane modules into `EXISTS`, `PARTIAL`, or `MISSING`, noting target OS platforms for desktop code (Windows `win32`, macOS `darwin`, Linux `linux`).
3. **7 ADRs Authored:** Authored ADRs 0002 through 0008 with explicit license notes, rejected alternatives, and security invariants conforming to Standing Rules 1–22 and New Rules 23–32.
4. **Zero Fabrication:** Capability reporting accurately records `NATIVE_ACCESSIBILITY_BACKEND_NOT_IMPLEMENTED` and mock stubs where real integrations are not yet wired.

---

## 4. Mutation Checks Done
- Verified in `test_11_mutation_check_fails_on_missing_foundation` that removing or corrupting key foundations (such as `ModelTier.VISION` or `TaskStatus.BLOCKED`) causes the acceptance assertions to fail closed.

---

## 5. Known Gaps
- `zonata-host-agent` executable and pairing protocol are to be implemented in Sub-Step 3B.
- Real Playwright browser automation behind `BrowserPort` is to be integrated in Sub-Step 3E/3F.
- Origin-bound enterprise secret vault is to be implemented in Sub-Step 3D.
