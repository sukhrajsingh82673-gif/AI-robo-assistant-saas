# ZONATA Co-Worker — Third-Party Open-Source Supply Chain & Licensing Governance

## 1. Executive Summary & Sovereignty Invariant

The ZONATA Universal AI Co-Worker Fabric integrates open-source execution engines, RPA toolkits, browser automations, and desktop vision-language frameworks behind strict corporate contracts. 

> [!IMPORTANT]
> **Sovereign Authority Invariant**:
> External open-source components are **execution providers only**. Under no circumstances does an open-source library, runtime, agent framework, or external protocol obtain sovereign authority over ZONATA. All executions remain subordinate to the **Company Kernel**, **PolicyEngine**, **ApprovalEngine**, **AuthorityGateway**, **CredentialAuthority**, and **EvidenceLedger**.

Every external dependency is audited, quarantined in sandboxes, cryptographically bounded by HMAC execution leases, and restricted from unauthorized credential access.

---

## 2. Integrated Open-Source Projects Inventory

| Project | Upstream Repository | License (SPDX) | Integration Version | Tracked Commit | Upstream Activity | Confinement Profile |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Crawlee** | `https://github.com/apify/crawlee-python` | Apache-2.0 | `v0.4.2` | `d7f19a2` | Active (weekly releases) | Sandboxed HTTP Client, Token Bucket |
| **Playwright** | `https://github.com/microsoft/playwright-python` | Apache-2.0 | `v1.44.0` | `b3e811c` | Active (bi-weekly releases) | Remote Worker Node, Ephemeral Context |
| **OpenClaw** | `https://github.com/openclaw/openclaw` | MIT | `v1.0.0` | `8f3b2a1` | Active (monthly releases) | Headless Tokenizer, No Display |
| **Agent-S** | `https://github.com/simular-ai/Agent-S` | Apache-2.0 | `v0.2.1` | `24c8b3a` | Active (OSWorld Research) | Visual CUA, Supervised Human Takeover |
| **UI-TARS** | `https://github.com/bytedance/UI-TARS` | Apache-2.0 | `v1.0.0` | `3a1f8c4` | Active (ByteDance Seed) | VLM Grounding Only, Read-Only Frame |
| **OpenAdapt** | `https://github.com/OpenAdaptAI/OpenAdapt` | MIT | `v0.3.1` | `9c2b4d8` | Active (community driven) | Deterministic Macro Replay, Scrubbed PII |
| **Hermes Agent** | `https://github.com/NousResearch/Hermes-Agent` | Apache-2.0 | `v0.3.0` | `6d4a1b9` | Active (Nous Research) | Sandboxed Subworker, JSON IPC |
| **OpenHands** | `https://github.com/All-Hands-AI/OpenHands` | MIT | `v0.9.1` | `e2b8c5f` | Highly Active (daily commits) | Docker/PRoot Container, Read/Write Jail |
| **MCP Python SDK** | `https://github.com/modelcontextprotocol/python-sdk` | MIT | `v1.1.0` | `c4f721d` | Active (Anthropic / Linux Foundation) | Local Stdio / SSE Transport Sandbox |
| **PyAutoGUI** | `https://github.com/asweigart/pyautogui` | BSD-3-Clause | `v0.9.54` | `7e1a3b5` | Stable / Maintenance | Native OS Desktop Dispatch, Rate-Limited |
| **LangGraph Core** | `https://github.com/langchain-ai/langgraph` | MIT | `v0.2.14` | `f5a91d2` | Highly Active (daily commits) | Zero-Secret SQLite State Checkpointing |
| **Robocorp RPA** | `https://github.com/robocorp/rpaframework` | Apache-2.0 | `v28.0.0` | `1b8c4d2` | Stable / Enterprise | Governed RPA Execution Layer |
| **OpenRPA** | `https://github.com/open-rpa/openrpa` | AGPL-3.0* | `v1.4.52` | `5e9a2f1` | Active | Isolated Out-of-Process Worker Node |

*\*Note on OpenRPA AGPL-3.0: Integrated strictly across out-of-process network/IPC boundary (A2A JSON-RPC / REST) to guarantee complete license isolation from ZONATA proprietary enterprise core.*

---

## 3. Dependency Footprint & Transitive Audit

### 3.1 Network & HTTP Scraping Stack
- **Direct Dependencies**: `urllib.request`, `urllib.robotparser`, `html.parser`, `json`, `hashlib`, `ssl`.
- **Transitive Footprint**: Zero external C-extensions required for native fallback layer. Eliminates supply-chain bloat and compile-time vulnerabilities on ARM64 and embedded platforms.
- **External Node Footprint**: Optional remote node packages (`crawlee`, `playwright`, `playwright-stealth`) isolated to dedicated remote node environments.

### 3.2 Visual & Computer-Use Stack
- **Direct Dependencies**: Built-in coordinate mapping, JSON grounding schema, Base64 frame serialization.
- **Transitive Footprint**: PyAutoGUI (optional on display-equipped nodes), Pillow / OpenCV (optional for screenshot diffing).
- **VLM Inference Isolation**: Vision-Language model grounding (Qwen2-VL, Claude-3.5-Sonnet) operates behind zero-retention API gateways or local self-hosted GPU nodes without local file read access.

---

## 4. Security Audit, CVE History & Vulnerability Mitigation

| Upstream Project | Known CVE History | Current Severity | ZONATA Confinement & Defensive Countermeasures |
| :--- | :--- | :--- | :--- |
| **Playwright / Chromium** | CVE-2023-4863 (libwebp), CVE-2024-0519 (V8) | Mitigated upstream | Ephemeral browser contexts, non-root user execution, sandboxed storage isolation, and dispatch to dedicated remote worker nodes. |
| **OpenHands** | CVE-2024-43405 (sandbox escape attempt in docker agent) | Patched upstream | Confined inside restricted subdirectories with path traversal guards (`os.path.commonpath`), command allowlisting, and PolicyEngine killswitch. |
| **Model Context Protocol (MCP)** | Stdio pipe injection risks | None active | Stdio streams validated against strict JSON-RPC 2.0 schemas. Process arguments sanitized against shell injection. |
| **OpenAdapt** | PII leakage in recording logs | Scrubbed | Pre-capture PII scrubbers enabled. Screen buffer cleared immediately after hashing. No persistent keystroke logs. |
| **urllib / http.client** | Header injection / CRLF | Mitigated | URLs strictly parsed through `urllib.parse.urlsplit()`. Strict validation of HTTP headers against newline injection. |

---

## 5. Sandboxing & Privilege Confinement Posture

1. **Principle of Least Privilege**:
   - Web harvesting workers possess **read-only egress HTTP** capabilities. They cannot write to the system root, spawn shell processes, or query corporate credential vaults.
   - Computer-use workers run with strict coordinate bounds, rate-limited keystroke entry, and mandatory policy evaluation on sensitive windows.
2. **Cryptographic Execution Leases**:
   - Workers cannot execute capabilities without a cryptographically signed lease token containing tenant ID, authority ceiling, and expiry timestamp.
3. **Zero-Secret Checkpoint Storage**:
   - Checkpoints recorded in SQLite pass through automated secret scanners (RegEx token patterns for API keys, AWS credentials, Bearer tokens).
4. **KillSwitch & Emergency Isolation**:
   - Global, Tenant, and Provider-level killswitches take precedence over all running execution processes, immediately revoking active leases.
