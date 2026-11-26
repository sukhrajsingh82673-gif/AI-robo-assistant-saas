# Sub-Step 3A Review: Preflight, Inventory and ADRs

**Sub-Step:** 3A  
**Branch:** `step3-hands`  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-22  
**Verdict:** **PASS**  

---

## 1. Audit Against Acceptance Criteria

| Criteria | Required Invariant | Audit Findings | Result |
| :--- | :--- | :--- | :--- |
| **Gate Check** | All 8 foundations from Step 1 & 2 must be confirmed present and green. | Verified via `tests/test_step3_preflight.py`: capability truth table, ActionGateway + approvals + killswitch, LLMGateway VISION tier, tool registry, human inbox + BLOCKED, document store reserved scan channel, DurableScheduler, and evidence ledger all import and assert true. | **PASS** |
| **Inventory Report** | `docs/reports/STEP3_INVENTORY.md` must list modules/tables, real capability, testing status, status classification (`EXISTS`, `PARTIAL`, `MISSING`), and target OS for desktop code. | Full audit report present. Accurately notes mock fetch in `browser_gateway.py`, urllib fallback in `playwright_provider.py`, Windows (`win32`), macOS (`darwin`), and Linux (`linux`) desktop targets, and backend absence of "Watch me". | **PASS** |
| **ADR 0002 (Browser Engine)** | Playwright lead, license notes, rejected alternatives (Selenium, Puppeteer, raw CDP), Rule 25 anti-evasion. | Documented with Apache-2.0 license, headless/container execution in CI, offline stubs, and strict prohibition of CAPTCHA solvers and stealth evasions. | **PASS** |
| **ADR 0003 (Perception)** | Accessibility tree first, screenshot + VISION second, rejected vision-only and tree-only. | Documented two-tier architecture: UIA/AXUIElement/AT-SPI Tier 1, masked VISION LLM Tier 2. | **PASS** |
| **ADR 0004 (Host Agent)** | Lightweight daemon, no Docker, native OS keystore (DPAPI/Keychain/SecretService), code-signable, auto-updatable. | Documented `zonata-host-agent` single-file Python executable using native OS crypto/keystores. | **PASS** |
| **ADR 0005 (Transport)** | Outbound-only TLS WebSocket, mutual auth, signed envelopes with monotonic sequence and nonce. | Documented outbound `wss://` protocol with Ed25519 signatures, timestamp drift checks, and anti-replay counters. | **PASS** |
| **ADR 0006 (Remote View)** | WebRTC / frame streaming, license check rejecting GPL VNC (TigerVNC/TightVNC/libvncserver), privacy masking. | Permissive WebRTC (BSD-3-Clause `aiortc` / native) chosen; copyleft GPL libraries rejected; Rule 24 secret masking enforced. | **PASS** |
| **ADR 0007 (Import Sandbox)** | Tiered isolation: static AST / ClamAV quarantine followed by gVisor container / microVM isolation. | Documented Tier 1 ClamAV/AST quarantine + Tier 2 gVisor (`runsc`) / Firecracker microVM with dropped capabilities. | **PASS** |
| **ADR 0008 (Search Provider)** | Sovereign multi-provider architecture behind `SearchPort` (SearXNG external REST, Brave/Tavily/SerpAPI, sandbox stub). | Documented multi-provider search with untrusted data tagging and Rule 25 challenge compliance. | **PASS** |
| **Acceptance Testing** | Unit/contract tests verifying gate, inventory, ADRs, and mutation checks. | `tests/test_step3_preflight.py` ran 11 tests in 0.632s with 100% PASS. | **PASS** |

---

## 2. Reviewer Verdict

**STATUS: PASS.**  
Sub-Step 3A satisfies all gate requirements, inventory documentation, architectural decision records, and acceptance testing. The builder is authorized to commit Sub-Step 3A and proceed to Sub-Step 3B (`Host permission model and the host agent`).
