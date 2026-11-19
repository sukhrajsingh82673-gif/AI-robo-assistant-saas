# ZONATA UNIVERSAL AI CO-WORKER: OPEN-SOURCE ECOSYSTEM LANDSCAPE

**Document Version:** 1.0.0-PROD  
**Classification:** Open-Source Ecosystem Integration & Governance Audit  
**Status:** Certified & Governed  
**Core Invariant:** External projects remain capability providers only; ZONATA retains absolute sovereignty.

---

## 1. Architectural Strategy & Open-Source Integration Philosophy

The ZONATA Universal AI Co-Worker Fabric does not reinvent commodity capabilities where robust, battle-tested open-source ecosystems exist. Instead, ZONATA functions as the **Sovereign Operating System and Governance Layer**, wrapping specialized open-source engines in strict security boundaries, credential vaults, audit ledgers, and hierarchical approval workflows.

### 1.1 Non-Delegable Sovereignty Rules
1. **Zero External Authority:** An external open-source framework can never issue binding business approvals, manipulate tenant isolation boundaries, or bypass ZONATA policy gates.
2. **Untrusted Capability Classification:** All external runtimes, tools, and scripts are treated as potentially malicious or compromised execution providers.
3. **AST & Boundary Sandboxing:** Code generated or imported by external agents undergoes pre-execution AST parsing and filesystem sandboxing.

---

## 2. Comprehensive Open-Source Ecosystem Matrix

| Project Name | Upstream Repository | License | ZONATA Functional Role | ZONATA Classification | Host Execution Reality |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hermes Agent** | `NousResearch/hermes-agent` | MIT | Autonomous reasoning, MCP tool calling, dynamic skills, background jobs | **`REAL_INTEGRATION`** | Fully executed locally on Linux ARM64 |
| **OpenClaw & ClawHub** | `openclaw/openclaw` | MIT | Web search aggregation, DOM extraction, Scrapling/Decodo plugin bridge | **`REAL_INTEGRATION`** | Fully executed locally on Linux ARM64 |
| **OpenHands** | `All-Hands-AI/OpenHands` | MIT | Software engineering co-worker, patch generation, test verification | **`REAL_INTEGRATION`** | Fully executed locally in sandboxed workspace |
| **BrowserCode** | `browser-use/browsercode` | Apache 2.0 | CDP JavaScript execution inside active browser contexts | **`PARTIAL_INTEGRATION`** | Protocol & JS executor verified; CDP bridge ready |
| **Playwright** | `microsoft/playwright` | Apache 2.0 | Headless browser automation and DOM snapshotting | **`PARTIAL_INTEGRATION`** | Client & adapter ready; Chromium binary blocked on ARM64/Python 3.14 |
| **OpenAdapt** | `OpenAdaptAI/OpenAdapt` | MIT | Desktop GUI process recording, replay, and human demonstration learning | **`BLOCKED_EXTERNAL_DEPENDENCY`** | Adapter implemented; blocked by missing physical desktop / X11 |
| **UI-TARS** | `bytedance/UI-TARS` | Apache 2.0 | Vision-Language-Action (VLA) multi-modal GUI control | **`BLOCKED_EXTERNAL_DEPENDENCY`** | Grounding schema implemented; blocked by local GPU / VLM weights |
| **Agent-S** | `simular-ai/Agent-S` | Apache 2.0 | GUI visual grounding, screenshot parsing, bounding box navigation | **`BLOCKED_EXTERNAL_DEPENDENCY`** | Action schema implemented; blocked by external endpoint / GPU |
| **OpenRPA** | `OpenRPA/OpenRPA` | MPL 2.0 | Enterprise Windows desktop RPA and Win32 automation | **`BLOCKED_EXTERNAL_DEPENDENCY`** | Protocol & RPC client implemented; blocked by non-Windows host |
| **Model Context Protocol**| `modelcontextprotocol/*` | MIT | Standardized client-server tool invocation format (`mcp__*`) | **`REAL_INTEGRATION`** | Fully executed locally via ZONATA MCP Gateway |

---

## 3. Deep-Dive Integration & Governance Profiles

### 3.1 NousResearch / Hermes Agent
- **Upstream Overview:** Lightweight, agentic reasoning loop supporting installable Python skills, background process daemons, and MCP tool discovery.
- **ZONATA Governance Wrap:**
  - Embedded as `HermesWorkerRuntime` inside `core/coworker/runtimes/hermes_runtime.py`.
  - Python skills undergo mandatory AST syntax scanning before loading (`HermesSkillAdapter`).
  - Dangerous system calls (`os.system`, `subprocess.Popen`, `eval`) are blocked at parse time.
  - Background processes are bounded by time-limited leases with mandatory heartbeat renewals.

### 3.2 openclaw / OpenClaw & ClawHub
- **Upstream Overview:** Agentic web automation daemon featuring plugin integrations with Scrapling, Decodo, and Apify.
- **ZONATA Governance Wrap:**
  - Implemented as a Dual-Layer system: Layer A (in-tree deterministic HTTP/DOM extractor) and Layer B (governed daemon bridge).
  - Enforces strict SSRF protection blocking private IPv4 subnets, loopback addresses, and AWS/GCP cloud metadata services.
  - Generates immutable SHA-256 evidence tokens for all scraped content.

### 3.3 All-Hands-AI / OpenHands
- **Upstream Overview:** Autonomous software engineering agent capable of reading codebases, formulating multi-file patches, executing tests, and debugging errors.
- **ZONATA Governance Wrap:**
  - Wrapped as `OpenHandsWorkerRuntime` in `core/coworker/runtimes/openhands_runtime.py`.
  - Enforces workspace sandboxing: coding agents are strictly confined to `/root/roboassistant/scratch/` and designated project subdirectories.
  - All generated code must pass syntax validation and test suite execution before sovereign pull request promotion.

### 3.4 browser-use / BrowserCode & Microsoft Playwright
- **Upstream Overview:** Modern web automation libraries executing actions via the Chrome DevTools Protocol (CDP).
- **ZONATA Governance Wrap:**
  - Unified under `browser.execute` in `BrowserWorkerRuntime`.
  - Domain whitelisting, form-submission policy checks, and automated screenshot digest logging.

### 3.5 Bytedance UI-TARS, Simular AI Agent-S, and OpenAdapt
- **Upstream Overview:** Frontier multi-modal models that visually ground UI elements (buttons, inputs, dropdowns) directly from screen pixels and output coordinate actions.
- **ZONATA Governance Wrap:**
  - Unified under the 10-action ZONATA Computer-Use specification (`computer.*`).
  - Action verification pipeline: coordinates are checked against application window bounds to prevent click-jacking or rogue desktop interaction.
  - Cryptographic frame hashing certifies each visual transition before the next action executes.

---

## 4. Supply Chain & License Compliance

All leveraged open-source libraries have been audited for intellectual property and license compatibility:
- **Permissive Open-Source:** MIT (Hermes, OpenClaw, OpenHands, OpenAdapt, MCP) and Apache 2.0 (BrowserCode, UI-TARS, Agent-S, Playwright) permit enterprise commercial bundling and redistribution without copyleft contamination.
- **Weak Copyleft:** MPL 2.0 (OpenRPA) is interfaced strictly over remote RPC boundaries, preventing license contamination of ZONATA core proprietary source.
- **Provenance Tracking:** Inbound third-party skill modules require license metadata disclosure and cryptographic verification before being registered into `SKILL_MEMORY`.
