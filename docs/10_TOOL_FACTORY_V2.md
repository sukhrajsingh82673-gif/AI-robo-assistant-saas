# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Tool Factory V2 & Runtime Sandbox Isolation Specification

---

### 1. Zero Direct Host Execution Invariant
Generated tools and dynamic scripts are strictly prohibited from executing directly on the control-plane host.
The `ToolFactoryV2` (`core/tool_factory_v2.py`) enforces two-tier isolation:
1. **Tier 1: Static AST Security Scanning**: Rejects imports of `os`, `subprocess`, `socket`, `pty`, `commands`, `ctypes` and invocations of `eval()`, `exec()`, `__import__()`, `open()`.
2. **Tier 2: Rootless Container Sandboxing**: Runs inside ephemeral rootless containers with:
   - Read-only root filesystem (`read_only_root_fs: true`)
   - Non-privileged execution (`is_privileged: false`)
   - Strict PID limit (`max_pids: 32`)
   - Memory ceiling (`max_memory_mb: 256`)
   - Network egress: `BLOCK_ALL` (or explicit domain allowlist)
   - Execution timeout: 30 seconds
