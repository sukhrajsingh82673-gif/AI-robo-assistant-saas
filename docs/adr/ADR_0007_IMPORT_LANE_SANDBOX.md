# ADR 0007: Import Lane and Untrusted Agent Sandboxing

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3J — Hands: Agent import lane & untrusted software execution  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

ZONATA allows importing open-source agent blueprints, tool definitions, and automation scripts through the Agent Factory Import Lane (`DocumentChannel.IMPORT_LANE`). 

Untrusted third-party code may contain malware, prompt injections, credential harvest backdoors, or system exploit payloads. The execution environment must guarantee that untrusted code cannot compromise the host, cloud infrastructure, or multi-tenant databases.

---

## 2. Evaluation of Alternatives

### Option 1: In-Process Python Restricted Execution (`exec` / `eval` with restricted globals)
- **Rejected Reasons:** Python is fundamentally unsafe for in-process sandboxing. Introspection exploits (e.g., `(1).__class__.__bases__[0].__subclasses__()`) routinely bypass restricted globals and escape to standard OS execution.

### Option 2: Standard Docker Container (`runc`)
- **Rejected Reasons:** Standard Linux containers share the host kernel directly. Kernel privilege escalation CVEs (e.g., Dirty COW, CVE-2024-21626) permit container escapes to host root.

### Option 3: Tiered Defense with gVisor / MicroVM Isolation (Chosen)
- **Tier 1 (Static Analysis & Quarantine):**
  - Document ingestion via `DocumentChannel.IMPORT_LANE`.
  - Anti-virus scan via ClamAV daemon (`AntivirusPort`).
  - Python AST parsing for dangerous imports (`ctypes`, `os.system`, socket calls, subprocess manipulation).
- **Tier 2 (Sandboxed Runtime Execution):**
  - Containerization using **gVisor (`runsc`)** or **Firecracker MicroVM** (Apache-2.0).
  - gVisor provides a user-space application kernel that intercepts and virtualizes all Linux system calls, completely isolating the host kernel from untrusted payloads.
  - Execution parameters: Read-only root filesystem, dropped capabilities (`--cap-drop=ALL`), zero network egress (`--network=none`), memory/CPU quotas, and 30-second hard execution timeouts.

---

## 3. Decision

We choose **Option 3: Tiered Defense with Static AST/ClamAV Quarantine followed by gVisor / MicroVM Sandboxing**.

### Enforcement Guarantees:
1. Untrusted imported code never runs on the developer's workstation or production host machine.
2. In Termux or non-containerized test environments, `QuarantinedAgentImporter` enforces Tier 1 static inspection and blocks execution with `SANDBOX_UNAVAILABLE` unless running in certified CI sandbox containers.
