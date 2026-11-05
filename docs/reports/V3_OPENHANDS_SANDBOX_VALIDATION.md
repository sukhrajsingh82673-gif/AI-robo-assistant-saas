# ZONATA V3 — OpenHands Governed Agent Execution Validation

## 1. Subsystem Architecture
- **Component:** `core.openhands_execution_runtime.OpenHandsRuntimeGateway` (Project 07)
- **Scope:** Governed code writing, shell command execution, workspace containment, file modifications, git operations, and software synthesis.
- **Isolation Modes:**
  - `LOCAL_PROCESS`: Sandboxed unprivileged execution within restricted tenant directories.
  - `DOCKER_CONTAINER`: Disposable container execution with CPU/RAM cgroups and network restrictions.

---

## 2. Invariant & Test Verification Matrix
| Invariant | Test Target | Verification Method | Status | Classification |
|---|---|---|---|---|
| **INV-OPH-01** | Path Traversal Protection | Strict rejection of `../` and absolute host paths | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-OPH-02** | Command Risk Screening | Sudo/destructive shell commands requiring approval | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-OPH-03** | Distributed Killswitch | Instant process group termination upon kill event | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-OPH-04** | Artifact Integrity | SHA-256 evidence hashing of generated files | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-OPH-05** | Production Remote Docker Daemon | Remote TLS Docker engine orchestration | BLOCKED | `BLOCKED — DAEMON ACCESS REQUIRED` |

---

## 3. Operational Classification
- **Sandboxed Execution Runtime:** `REAL_LOCAL_INFRASTRUCTURE`
- **Remote Production Container Orchestrator:** `BLOCKED — DAEMON ACCESS REQUIRED`
