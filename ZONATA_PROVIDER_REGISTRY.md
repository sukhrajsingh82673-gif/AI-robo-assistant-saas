# ZONATA Provider & Runtime Qualification Registry

## 1. The 5-Level Qualification Standard

Every capability provider, execution runtime, and worker node in the ZONATA Co-Worker Fabric is qualified against a strict 5-level qualification rubric. 

```
Level 0: Specification Defined
    ↓
Level 1: Contract-Compliant Adapter Implemented
    ↓
Level 2: Sandboxed Integration Tested
    ↓
Level 3: Independently Verified Real Execution
    ↓
Level 4: Stress, Chaos, Failure, and Soak Tested
    ↓
Level 5: Production Certified
```

### Detailed Criteria:
- **Level 0 (SPEC_DEFINED)**: Capability interfaces, inputs, outputs, error models, and risk levels are specified in machine-readable JSON Schema.
- **Level 1 (ADAPTER_IMPLEMENTED)**: Implements all 14 methods of `UniversalWorkerContract` and the 16 canonical metadata fields. Adheres to ZONATA Policy and Approval interfaces.
- **Level 2 (SANDBOX_INTEGRATED)**: Successfully mounts inside execution sandboxes (PRoot, Docker, or isolated process jail). Verifies prerequisite checks, memory/CPU bounds, and credential isolation.
- **Level 3 (INDEPENDENTLY_VERIFIED)**: Executes real-world workloads against live targets with physical evidence (read-after-write disk check, HTTP response verification, AST inspection) verified by an external verifier.
- **Level 4 (STRESS_CHAOS_QUALIFIED)**: Passes simulated and real failure injection (connection drops, process kill, ambiguous mutation quarantine, and accelerated 6h/24h/72h soak cycles) without data loss.
- **Level 5 (PRODUCTION_CERTIFIED)**: Fully qualified across multi-platform fleet nodes, integrated into CEO Mission routing, hardened against supply-chain vulnerabilities, and certified for autonomous production deployment.

---

## 2. Capability Provider Master Registry

| Provider ID | Provider Name | Capability Domain | Supported Platforms | Qualification Level | Fallback Chain | Security Profile |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `provider_web_scraping_family` | ZONATA Web Scraping Family | Web Extraction, Crawling, Merkle Hashing (20 ops) | Linux, Windows, macOS | **Level 5 (Production Certified)** | `provider_openclaw` → `provider_playwright` | Sandboxed HTTP Client, Token Bucket |
| `provider_terminal` | Governed Terminal Runtime | CLI, Bash, Scripting, Build Tooling | Linux, macOS, Windows | **Level 5 (Production Certified)** | `provider_hermes` → `provider_openhands` | Strict Command Allowlist, PTY Jail |
| `provider_api_mcp` | API & Model Context Protocol | REST, GraphQL, MCP Tools, OpenAPI | Universal (Any) | **Level 5 (Production Certified)** | Local Native Adapter → Remote Node | Stdio / SSE Transport Jail |
| `provider_openclaw` | OpenClaw Resilient Web Parser | High-Speed Table Extraction, Link Crawling | Linux, Windows, macOS | **Level 5 (Production Certified)** | `provider_web_scraping_family` | Headless In-Memory Tokenizer |
| `provider_computer_use_router` | Open-Source Computer-Use Router | Unified GUI Automation (Mouse, Keyboard, VLM) | Linux, Windows, macOS | **Level 4 (Stress/Chaos Qualified)** | `provider_agent_s` → `provider_ui_tars` → Remote Node | Governed GUI Dispatch, Human Takeover |
| `provider_openadapt` | OpenAdapt Process Automation | GUI Recording & Deterministic Replay | Windows, macOS, Linux | **Level 4 (Stress/Chaos Qualified)** | `provider_robocorp` → `provider_openrpa` | PII Scrubbing, Offset Reconciliation |
| `provider_agent_s` | Agent-S (Simular AI / OSWorld) | Hierarchical Visual GUI Subgoal Planning | Linux, Windows, macOS | **Level 3 (Verified Execution)** | `provider_ui_tars` → Remote Node | Supervised Visual CUA |
| `provider_ui_tars` | UI-TARS (ByteDance Seed) | Vision-Language Bounding Box Grounding | Linux, Windows, macOS, GPU | **Level 3 (Verified Execution)** | `provider_agent_s` → Remote VLM Node | Read-Only Frame Buffer, Zero Persistence |
| `provider_playwright` | Playwright Browser Engine | Full DOM Rendering, JS Execution, Screenshots | Linux, Windows, macOS | **Level 3 (Verified Execution)** | `provider_openclaw` → Remote Browser Node | Ephemeral Incognito Context |
| `provider_linux_desktop` | Linux Native Desktop | X11/Wayland Desktop Automation | Linux | **Level 3 (Verified Execution)** | `provider_computer_use_router` | Coordinate Boundary Check |
| `provider_windows_desktop` | Windows Native Desktop | Windows UI Automation (UIA) | Windows | **Level 3 (Verified Execution)** | Remote Windows Node Protocol | Win32 / UIA Accessibility Sandbox |
| `provider_macos_desktop` | macOS Native Desktop | AppleScript & AXAccessibility | macOS | **Level 3 (Verified Execution)** | Remote macOS Node Protocol | Apple TCC Permission Sandbox |
| `provider_robocorp` | Robocorp RPA Framework | Enterprise Tabular / Desktop RPA | Windows, Linux | **Level 3 (Verified Execution)** | `provider_openrpa` | Isolated Subprocess |
| `provider_openrpa` | OpenRPA Engine | Industrial Legacy Automation | Windows | **Level 2 (Sandbox Integrated)** | Remote Windows Node | Out-of-Process A2A Protocol |

---

## 3. Worker Runtime Registry

| Runtime Identifier | Technology Base | Execution Role | Dispatch Mode | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| `runtime_hermes` | Hermes Agent (Nous Research) | Autonomous multi-step CLI & subworker tool execution | In-Process / Stdio Subprocess | Output Digest & JSON AST Validation |
| `runtime_openclaw` | OpenClaw / Crawl4AI | Resilient HTML traversal, deep link parsing, tables | In-Process Native Engine | Merkle Content Root & HTTP Status Check |
| `runtime_openhands` | OpenHands Sandbox | Sandboxed file system and software workspace tasks | Container / PRoot Jail | Read-After-Write File Hash Verification |
| `runtime_durable` | CoworkerDurableWorkflowEngine | Long-running 24/7/72h missions and crash recovery | SQLite State Journal | Merkle Checkpoint Hash Chain |
| `runtime_fleet_agent` | NodeAgent Daemon | Remote multi-platform execution node listener | TLS / HMAC Remote RPC | HMAC-SHA256 Signed Execution Evidence |

---

## 4. Multi-Platform Remote Worker Node Standards

When an execution capability requires an OS, hardware architecture, display server, or GPU accelerator not physically present on the local control plane:

1. **Deterministic Node Capability Discovery**: The Co-Worker queries the live `FleetNodeRegistry`.
2. **Cryptographic Lease Assignment**: The Authority Gateway issues an HMAC-SHA256 signed lease token specifying maximum CPU/RAM, duration, and authority ceiling.
3. **Zero-Mock Dispatch**: If no remote node is currently online, the system truthfully outputs `READY_FOR_REMOTE_NODE` accompanied by the standalone bootstrap package (`node_agent.py`), never fabricating a synthetic local pass.
4. **Heartbeat & Orphan Sweep**: Remote worker heartbeats are monitored every 5–15 seconds; leases from disconnected nodes are swept and quarantined.
