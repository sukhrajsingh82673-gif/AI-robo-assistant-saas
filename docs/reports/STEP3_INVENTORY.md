# ZONATA Step 3 Inventory & Baseline Audit

**Document Date:** 2026-11-22  
**Context:** OpenCode Step 3A — Hands: Preflight, Inventory, and Architecture Decision Records  
**Author:** ZONATA Systems Architecture  
**Status:** Canonical Baseline Audit  

---

## 1. Executive Summary

This inventory documents all existing code, modules, database tables, and gap areas relating to computer control, browser automation, desktop perception, terminal execution, credentials/secrets, and import lanes prior to implementing Step 3.

Each component is audited against actual source code and categorized as:
- **`EXISTS`**: Fully implemented, tested, and active in the codebase.
- **`PARTIAL`**: Partially implemented, presents a stub, simulation, or fallback, or lacks full real-system integration.
- **`MISSING`**: Does not exist in code, schema, or runtime.

---

## 2. Capability & Component Inventory Table

| Component Category | Target Subsystem / Module / Path | Real Capability / Behavior | Tested? | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Browser: Gateway** | `agent_factory/capabilities/browser_gateway.py` | Performs URL parsing, IP restriction, and domain allowlist validation (`validate_outbound_url`). However, `BrowserGateway.fetch()` returns a hardcoded mock HTML stub (`<html><body>Safe content...</body></html>`) rather than executing an HTTP request or browser session. | Yes (`test_browser_gateway.py`) | **`PARTIAL`** |
| **Browser: Playwright Provider** | `core/coworker/providers/playwright_provider.py` | Implements `CapabilityProvider` for `browser.*`. If Playwright is not available or in fallback, executes HTTP GET via standard library `urllib.request` and regex HTML parsing. Does not control a live browser instance. | Yes (`test_coworker_production_qualification.py`) | **`PARTIAL`** |
| **Browser: Execution Fabric** | `core/browser_robot.py` | State tracker for simulated browser tabs and URLs. Does not attach to a live browser process or CDP socket. | Yes (`test_browser_robot.py`) | **`PARTIAL`** |
| **Browser: Unified Runtime** | `core/coworker/runtimes/browser_runtime.py` | Governed browser worker runtime. Routes actions to providers; defaults to `ACTION_NOT_IMPLEMENTED` for actions requiring real browser interaction (`browser.click`, `browser.type`, `browser.download`). | Yes (`test_coworker_v2_comprehensive.py`) | **`PARTIAL`** |
| **Browser: Execution Runtime** | `core/browser_use_execution_runtime.py` | Orchestrates browser nodes; returns `ACTION_NOT_IMPLEMENTED` on unconfigured actions (lines 1103, 1370). | Yes | **`PARTIAL`** |
| **Browser: Playwright Imports** | `api_server.py:6109`, `core/settings_service.py:1293` | Contains `import playwright  # noqa: F401` as placeholder/optional import guards without core runtime usage. | N/A | **`EXISTS`** |
| **Desktop: Perception & Control** | `core/desktop_robot.py` | Coordinate and window state model; simulated action recording. | Yes | **`PARTIAL`** |
| **Desktop: Native Providers** | `core/coworker/providers/desktop_native_providers.py` | Base provider and OS-specific subclasses: `WindowsDesktopProvider` (targets `win32` / Microsoft UI Automation), `MacOSDesktopProvider` (targets `darwin` / `AXUIElement` / AppleScript), and `LinuxDesktopProvider` (targets `linux` / X11 / AT-SPI). `desktop.accessibility_tree` and UI element interaction explicitly fail with `NATIVE_ACCESSIBILITY_BACKEND_NOT_IMPLEMENTED` (lines 116, 119) because native OS bindings are not compiled into the runtime. | Yes (`test_coworker_v3_acceptance.py`) | **`PARTIAL`** |
| **Desktop: Computer Use Engine** | `core/coworker/computer_use_engine.py` | Visual computer-use engine targeting Linux X11 display environment (`DISPLAY`). Fails with `ACTION_NOT_IMPLEMENTED` and reason `NO_DISPLAY` when run in headless environments or on ARM64 without Xvfb (line 750). | Yes (`test_coworker_runtimes_hermes_openclaw.py`) | **`PARTIAL`** |
| **Terminal: Universal Terminal** | `core/universal_terminal/universal_terminal.py` | Full Universal Linux Terminal abstraction with 22 capabilities, command plan isolation, snapshotting, and postcondition verification. | Yes (`test_universal_terminal_*.py`) | **`EXISTS`** |
| **Terminal: Agent & Controller** | `core/universal_terminal/terminal_agent.py`, `core/coworker/controllers/terminal_controller.py` | Governed terminal worker agent and controller routing terminal execution requests through governance gates. | Yes | **`EXISTS`** |
| **Terminal: Shell Provider** | `core/coworker/providers/terminal_provider.py` | Governed shell execution provider enforcing Rule 11 (Exit code 0 != business success) and zero-secret logging. | Yes | **`EXISTS`** |
| **Terminal: On/Off Setting** | `core/settings/definitions.py`, `core/settings_service.py`, `core/universal_terminal/security_gateway.py` | System-wide and tenant-scoped `terminal_enabled` toggle and execution mode setting. Security gateway halts execution when disabled. | Yes (`test_universal_terminal_security.py`) | **`EXISTS`** |
| **Assistant: "Watch me"** | Described in `docs/ui-redesign/ASSISTANT.md`, `PROGRESS.md` | Conceptual design for human action demonstration and recording. Backend daemon, event capture pipeline, and session recorder are completely absent from backend code. | No | **`MISSING`** |
| **Assistant: Jobs** | `core/baseline/scheduler.py` | `DurableScheduler` with `ScheduledJobRecord`, monotonic timing, leader lease election, and 30s failover. Backed by tables `scheduled_jobs` and `scheduler_leader_leases`. | Yes (`test_step1_always_on_baseline.py`) | **`EXISTS`** |
| **Assistant: Scope & Grants** | `core/action_envelope.py` | `ActionEnvelope` contains `tenant_id` and `company_id`. However, host-enforced device permissions, device pairing, and scope separation (`PERSONAL` vs `COMPANY`, `OBSERVE`, `CONFIRM_EACH`, `AUTONOMOUS_IN_SCOPE`) do not exist. | No | **`MISSING`** |
| **Secrets: Vault Client** | `core/vault_client.py` | HashiCorp Vault dynamic credential broker with scoped leases. | Yes (`test_vault_hardening.py`) | **`EXISTS`** |
| **Secrets: Vault Manager** | `core/secret_manager.py` | JIT credential leasing, opaque handle broker (`cred_*`), and automated regex redaction engine. | Yes (`test_secrets.py`) | **`EXISTS`** |
| **Secrets: Secret Vault Core** | `core/secret_vault.py` | Encrypted storage engine with `secret://<id>` URI scheme. | Yes | **`EXISTS`** |
| **Secrets: Database Tables** | `migrations/common/0003_settings_v2_schema.sql`, `migrations/pg/0007_settings_v2_tenant_keys.sql`, `migrations/pg/0013_agent_factory_core.sql` | Tables `secrets` and `agent_signing_keys` exist. However, dedicated `enterprise_secret_vault` and host-side origin-bound credential tables (enforcing Rule 24) do not exist. | Yes | **`PARTIAL`** |
| **Import Lane: Quarantine** | `agent_factory/importer/quarantine.py` | `QuarantinedAgentImporter` validates untrusted third-party agent bundles, performs AST extraction, security boundary checks, and quarantine routing. | Yes (`test_agent_factory_importer_quarantine.py`) | **`EXISTS`** |
| **Import Lane: Document Pipeline** | `core/documents/pipeline.py`, `core/documents/schema.py` | `DocumentChannel.IMPORT_LANE` routes through ClamAV virus scanning and quarantine storage before any inspection. | Yes (`test_step1_documents.py`) | **`EXISTS`** |

---

## 3. Desktop Target Operating Systems Analysis

Existing desktop automation code in `core/coworker/providers/desktop_native_providers.py` targets three distinct operating systems:
1. **Microsoft Windows (`win32`):**
   - Implemented in `WindowsDesktopProvider`.
   - Intended subsystem: Microsoft UI Automation (UIA) and .NET Framework 4.8.
   - Current Status: Returns `BLOCKED_EXTERNAL_DEPENDENCY` on non-Windows hosts, and returns `NATIVE_ACCESSIBILITY_BACKEND_NOT_IMPLEMENTED` on Windows because native C# / COM bindings are not compiled.
2. **Apple macOS (`darwin`):**
   - Implemented in `MacOSDesktopProvider`.
   - Intended subsystem: `AXUIElement`, AppleScript, and Quartz.
   - Current Status: Returns `BLOCKED_EXTERNAL_DEPENDENCY` on non-macOS hosts, and returns `NATIVE_ACCESSIBILITY_BACKEND_NOT_IMPLEMENTED` on macOS due to missing PyObjC / Accessibility framework bindings.
3. **Linux (`linux`):**
   - Implemented in `LinuxDesktopProvider`.
   - Intended subsystem: X11, Wayland, and AT-SPI (Assistive Technology Service Provider Interface).
   - Current Status: `desktop.launch_app` executes via `subprocess.Popen`, but accessibility tree inspection and mouse/keyboard interaction are not connected to AT-SPI/libatspi.
4. **Visual Computer Use Engine (`core/coworker/computer_use_engine.py`):**
   - Targets Linux X11 with `DISPLAY` environment variable and `pyautogui`.
   - Headless or container environments without a virtual framebuffer fail immediately with `NO_DISPLAY` / `ACTION_NOT_IMPLEMENTED`.

---

## 4. Key Gaps Identified for Step 3 Implementation

1. **Host-Side Permission Enforcement (Rule 23):**
   - Current execution models push commands from the server to providers without local grant verification.
   - Step 3B must implement a small, standalone host agent (`zonata-host-agent`) that enforces local allowlists, pairing keys in the OS keystore, and human confirmation on the physical host machine.
2. **Origin-Bound Credential Isolation (Rule 24):**
   - Existing secret brokers return secret values to callers for injection.
   - Step 3D must establish strict origin binding: secrets never leave the host agent or secure browser context, never appear in prompts, DOM snapshots, logs, or traces, and can only be injected into exact target origins.
3. **No Circumvention of Verification Challenges (Rule 25):**
   - Automated workflows must detect CAPTCHAs, bot blocks, and rate limits and fail gracefully / hand off to a human, without stealth spoofing or solver services.
4. **Browser Integration (Rule 30):**
   - Playwright lead engine must be cleanly integrated behind `BrowserPort`, providing headless execution in CI and local fixture testing, with probe reporting `NOT_CONFIGURED` when browser binaries are absent.
