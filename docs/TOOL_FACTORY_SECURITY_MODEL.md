# TOOL FACTORY SECURITY MODEL & SYNTHESIS SPECIFICATION
**ZONATA Universal AI Company Operating System**  
*Classification: RESTRICTED / INTERNAL PRODUCTION AUDIT*  
*Timestamp: 2026-10-02T11:15:00Z*

---

## 1. Constitutional Invariants of the Tool Factory

```
1. TOOL CREATION != PERMISSION
   Synthesizing a tool does not make it executable.

2. TOOL != TRUST
   A newly generated tool is untrusted code subject to static analysis.

3. SCRIPT EXECUTION != PRODUCTION DEPLOYMENT
   Testing a tool in a sandbox does not grant access to production resources.

4. TOOL RESULT != TRUTH
   Output from a tool is observation data requiring independent verification.
```

---

## 2. Governed 7-Stage Tool Lifecycle Pipeline

Every dynamic tool synthesized by AI workforce agents must traverse the following verification stages:

```
[TOOL_DESIGN]
      │
      ▼
[SECURITY_SCAN] ────(Forbidden Primitives Detected)────► [REJECTED / QUARANTINED]
      │
      ▼
   [TEST]
      │
      ▼
[POLICY_REVIEW]
      │
      ▼
[REGISTRATION]
      │
      ▼
  [APPROVAL] ───(High Risk: Financial / Privileged)───► [HUMAN_APPROVAL_QUEUE]
      │                                                         │
      ├─────────────────────────────────────────────────────────┘
      ▼
 [ACTIVATION] (Executable under Least-Privilege Sandboxing)
```

---

## 3. Static Code Security Scanner

In `core/agent_factory_runtime.py`, the `GovernedToolFactory` executes automated regex and AST analysis:

- **Forbidden Primitives**:
  - `import os` / `from os import ...`
  - `import subprocess` / `Popen` / `call`
  - `import socket` / raw TCP sockets
  - `eval()` / `exec()`
  - `__import__()` / reflection escapes
  - `shutil.rmtree` / path traversal
  - Direct unrestricted filesystem writes outside `storage/sandbox/`

Any violation causes immediate rejection with `ToolSecurityViolation`.

---

## 4. Risk Classification & Approval Gates

- **`READ_ONLY`**: Data inspection, read APIs, computation. Automatic activation after security scan.
- **`SANDBOXED_COMPUTATION`**: File processing within designated workspace. Automatic activation.
- **`STATE_MUTATION`**: Modifies database records or CRM entries. Requires manager approval.
- **`FINANCIAL`**: Invoicing, payment initiation, refunds, budget modification. **Mandatory Human-in-the-Loop Approval**.
- **`PRIVILEGED`**: Infrastructure modifications, system restarts. **Mandatory Owner Approval**.
