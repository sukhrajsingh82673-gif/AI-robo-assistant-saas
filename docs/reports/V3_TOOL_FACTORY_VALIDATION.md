# ZONATA V3 — Tool Factory & Sandboxed Synthesis Validation

## 1. Subsystem Architecture
- **Component:** `core.tool_factory_v2.ToolFactoryV2`
- **Scope:** Dynamic Python tool synthesis, AST security scanning, container sandboxing, capability registration, and cryptographic hash verification.
- **Security Boundary:** Disallows unsafe modules (`os.system`, `subprocess`, `ctypes`, `socket`, `eval`, `exec`) in synthesized tools unless explicitly approved via human-in-the-loop executive council gates.

---

## 2. Invariant & Test Verification Matrix
| Invariant | Test Target | Verification Method | Status | Classification |
|---|---|---|---|---|
| **INV-TOL-01** | AST Security Screening | Static parse rejecting dangerous imports and calls | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TOL-02** | Schema Generation | Extraction of parameter types, docstrings, and defaults | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TOL-03** | Capability Registry Binding | Dynamic tool registration into tenant capability catalog | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TOL-04** | Isolated Sandbox Execution | Subprocess execution with resource limits and timeouts | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-TOL-05** | Cryptographic Signature | SHA-256 code hashing stored in evidence ledger | PASS | `REAL_LOCAL_INFRASTRUCTURE` |

---

## 3. Adversarial Attack Tests
- **Escape Vector 1 (`eval("__import__('os').system('rm -rf /')")`):** Caught by AST analyzer; synthesis rejected immediately with `AST_SECURITY_VIOLATION`.
- **Escape Vector 2 (Dynamic reflection via `getattr`):** Sandboxed subprocess execution restricted; non-zero exit returned without host impact.
- **Classification:** `REAL_LOCAL_INFRASTRUCTURE`
