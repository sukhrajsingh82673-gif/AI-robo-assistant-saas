# URA / ZONATA Autonomous Executive Coworker: Enterprise Architecture Specification

**Document Version:** 3.0-EXEC-PROD  
**Classification:** Authoritative Technical Specification  
**Project:** URA / ZONATA Universal AI Company Operating System  
**Repository:** `sukhrajsingh82673-gif/AI-robo-assistant-saas`  
**Baseline Commit:** `c9f1251`  
**Authority:** ZONATA Constitution, AI CEO & System Owner  
**Date:** November 2026  

---

## 1. Architectural Philosophy & Sovereign Constitution

The URA / ZONATA Autonomous Executive Coworker is designed not as a generic conversational chatbot or an isolated copilot, but as an **operational digital executive employee** functioning directly alongside the AI CEO. It operates strictly within the sovereign governance of the ZONATA Constitution, upholding all corporate hierarchies, authority thresholds, and tenant boundaries without usurpation or bypass.

```mermaid
flowchart TD
    CEO["AI CEO (Executive Function)"] -->|CEO Assignments & Directives| EOL["Executive Operating Loop (8 Priority Tiers)"]
    
    subgraph Governance ["Sovereign ZONATA Governance"]
        CONST["ZONATA Constitution"]
        POL["PolicyEngine & RBAC"]
        APP["ApprovalEngine (DoA Threshold: $10,000)"]
        KILL["KillSwitchMatrix"]
        LEDGER["EvidenceLedger (Merkle SHA-256)"]
    end
    
    EOL --> Governance
    
    subgraph Engines ["Specialist Execution Engines"]
        HERMES["Hermes Agent v3 (Local Inference Adapter)"]
        OPENCODE["OpenCode Engine (Autonomous Ralph Loop)"]
        OPENDOTS["OpenDots / Computer Use (X11 Virtual Desktop)"]
        SWARM["Specialist Team Assembler (12 Archetypes)"]
    end
    
    EOL --> Engines
    
    subgraph DefensiveSecurity ["Defensive Security & DLP Fabric"]
        DLP["DLP Engine (12 Categories, 10 Channels)"]
        LADDER["4-Tier Response Ladder (Audit->Mask->Block->Quarantine)"]
        HMAC["Salted HMAC Origin Tracing"]
        PATROL["Defensive Cybersecurity Patrol (5 Tiers)"]
    end
    
    EOL --> DefensiveSecurity
    
    subgraph WorkforceSupport ["Workforce Empowerment"]
        EMP["Employee Support Service (Non-Usurpation Triage)"]
        HUMAN["Human Employees & Subordinate Agents"]
    end
    
    EOL --> WorkforceSupport
    EMP <--> HUMAN
```

### 1.1 Constitutional Invariants & Authority Thresholds
- **Delegation of Authority (DoA) Limit:** The Coworker possesses autonomous financial spending authority capped strictly at **$10,000.00 USD**. Any transaction, resource lease, or vendor commitment exceeding this limit is intercepted by the `ApprovalEngine` and requires explicit human/CEO cryptographic countersigning. Automated test runs enforce a $100.00 auto-approval threshold to prevent accidental capital allocation.
- **Non-Usurpation Invariant:** When assisting human employees or rescuing subordinate agents, the Coworker never alters the corporate hierarchy, strips role ownership, or usurps task governance. The Coworker operates strictly in an advisory, diagnostic, and enablement capacity, returning control to the originating employee upon resolution.
- **Zero-Knowledge Credential Origin Tracing:** Sensitive API tokens and credentials are tracked across all omnidirectional channels using salted HMAC-SHA256 digests. Plaintext keys are never stored in telemetry or audit logs.
- **Merkle Cryptographic Sealing:** Every compound assignment, security incident remediation, and code modification is sealed into the immutable `EvidenceLedger` using SHA-256 Merkle hashes.

---

## 2. Executive Operating Loop (8 Priority Tiers)

The Coworker's core runtime is governed by the `ExecutiveOperatingLoop` (`core/coworker/executive_operating_loop.py`), a priority-queued operational daemon backed by a re-entrant lock (`threading.RLock`) to ensure complete thread-safety without deadlock.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Tier1_CriticalSecurity: Priority 1 (CVSS >= 9.0 / Breach)
    Idle --> Tier2_OutageRecovery: Priority 2 (Service Outage / DB Failover)
    Idle --> Tier3_CEODirective: Priority 3 (CEO Assignment / Board Order)
    Idle --> Tier4_EmployeeBlocker: Priority 4 (Employee Diagnostic Request)
    Idle --> Tier5_ScheduledOperation: Priority 5 (Automated Cron / Maintenance)
    Idle --> Tier6_BackgroundResearch: Priority 6 (AST Capability Screening)
    Idle --> Tier7_ContinuousPatrol: Priority 7 (5-Tier Security Patrol)
    Idle --> Tier8_RoutineMaintenance: Priority 8 (Log Rotation / Worktree Pruning)

    Tier1_CriticalSecurity --> QuarantineAndRemediate
    Tier2_OutageRecovery --> FailoverAndRestore
    Tier3_CEODirective --> DecomposeAndExecute
    Tier4_EmployeeBlocker --> TriageAndReturn
    Tier5_ScheduledOperation --> ExecuteBatch
    Tier6_BackgroundResearch --> SandboxEvaluation
    Tier7_ContinuousPatrol --> SweepAndReport
    Tier8_RoutineMaintenance --> PurgeAndSync

    QuarantineAndRemediate --> EvidenceSeal
    FailoverAndRestore --> EvidenceSeal
    DecomposeAndExecute --> EvidenceSeal
    TriageAndReturn --> EvidenceSeal
    ExecuteBatch --> EvidenceSeal
    SandboxEvaluation --> EvidenceSeal
    SweepAndReport --> EvidenceSeal
    PurgeAndSync --> EvidenceSeal

    EvidenceSeal --> Idle
```

### 2.1 The 8 Execution Tiers
1. **Tier 1: `CRITICAL_SECURITY` (Weight: 100):** Active intrusion attempts, reverse shell detection, cryptographic tampering, and data exfiltration alerts.
2. **Tier 2: `OUTAGE_RECOVERY` (Weight: 90):** Core SaaS infrastructure failures, database disconnects, worker node crashes, and container recovery.
3. **Tier 3: `CEO_DIRECTIVE` (Weight: 80):** Strategic compound assignments originating directly from the AI CEO or Executive Board.
4. **Tier 4: `EMPLOYEE_BLOCKER` (Weight: 70):** Human employee diagnostic triage, build blocker resolution, and subordinate agent rescue.
5. **Tier 5: `SCHEDULED_OPERATION` (Weight: 60):** Recurring business automation, payroll reconciliation, and daily digest compilation.
6. **Tier 6: `BACKGROUND_RESEARCH` (Weight: 50):** AST capability verification, license auditing, and benchmark analysis.
7. **Tier 7: `CONTINUOUS_PATROL` (Weight: 40):** 5-tier threat sweeps across file integrity, listening ports, process tables, and memory maps.
8. **Tier 8: `ROUTINE_MAINTENANCE` (Weight: 30):** Ephemeral worktree cleanup, cache pruning, and log compaction.

---

## 3. Hardware Resource Envelope & Local Inference Cascade

The Coworker is engineered to run reliably in resource-constrained container environments (e.g., Linux ARM64 with 620MB total system RAM).

### 3.1 Local Inference Adapter Specification
- **Process Memory Ceiling:** Enforces an absolute cap of **180MB RAM** for the Coworker process.
- **In-Process Weight Loading Prohibition:** Prohibits loading large-language model weights (e.g. 7B/13B GGUF) directly into process memory on ARM64 containers, preventing fatal Linux kernel OOM kills.
- **Hardware Cascade Hierarchy:**
  1. *Local REST Endpoint Probe:* Probes local daemon (e.g., Ollama at `http://127.0.0.1:11434/api/tags`) with a strict **1.5-second timeout**.
  2. *Runtime Delegation:* If local Ollama is active, dispatches local completions.
  3. *Cloud Runtime Fallback:* If authorized API keys exist, delegates to `core.llm_runtime.llm_runtime`.
  4. *Honest Unavailable Status:* If no endpoint or keys are configured, returns `LLM_UNAVAILABLE` with status `available=False`. Zero hallucination or simulated mock completions are permitted.

---

## 4. Specialist Execution Engines

### 4.1 Hermes Agent v3 (`core/coworker/hermes_agent_v3.py`)
Provides primary autonomous reasoning, tool selection, session checkpointing, and dynamic skill execution. Governed by the `LocalInferenceAdapter` to guarantee operational integrity across diverse hardware configurations.

### 4.2 OpenCode Software Engineering Engine (`core/coworker/opencode_engine.py`)
Specialized software development engine executing the 7-stage Ralph Loop:
1. Isolated Git worktree creation (`git worktree add`).
2. Scoped static analysis and defect identification.
3. Surgical code mutation adhering strictly to target scope.
4. Continuous automated test execution.
5. Stderr/stdout feedback diagnosis and automatic re-edit.
6. Gravitas stale-gate test verification.
7. Worktree cleanup and atomic commit formulation.

### 4.3 OpenDots Computer Use Engine (`core/coworker/computer_use_engine.py`)
Provides visual perception and interactive automation on virtual X11 desktops:
- Virtual framebuffer execution on `DISPLAY=:99` via Xvfb at 1920x1080 resolution.
- Window tree inspection using `xdotool` and `xwininfo`.
- Coordinate-normalized mouse and keyboard input simulation.
- Screen capture and visual element verification.
- Distinct and separate from third-party closed-source products; zero proprietary dependency.

### 4.4 Specialist Team Assembler (`core/coworker/specialist_team_assembler.py`)
Dynamically provisions swarms across **12 Specialist Archetypes**:
`ARCHITECT`, `CODER`, `REVIEWER`, `TESTER`, `SECURITY_ANALYST`, `DEVOPS_ENGINEER`, `DATA_ENGINEER`, `INCIDENT_RESPONDER`, `TECHNICAL_WRITER`, `COMPLIANCE_AUDITOR`, `SRE_OBSERVER`, `INTEGRATION_SPECIALIST`.
Each agent is assigned typed input/output contracts, strict resource quotas, time-bounded leases, and independent peer review requirements.

---

## 5. Defensive Cybersecurity & Data Loss Prevention Fabric

### 5.1 DLP Engine (`core/coworker/dlp_engine.py`)
Monitors 12 sensitive data classifications across 10 omnidirectional channels:
- **12 Categories:** `API_KEYS`, `AWS_SECRETS`, `PRIVATE_KEYS`, `JWT_TOKENS`, `DB_CONNECTION_STRINGS`, `PASSWORDS`, `PII`, `CREDIT_CARDS`, `SSN`, `HEALTHCARE_DATA`, `FINANCIAL_DATA`, `SOURCE_CODE_SECRETS`.
- **10 Channels:** Terminal stdin/stdout, file write/read, clipboard, network egress, LLM prompt/completion, process spawn, inter-agent messages, tool outputs.
- **4-Tier Response Ladder:**
  - *Tier 1 (LOW):* `AUDIT` — Logs event to EvidenceLedger without interrupting execution.
  - *Tier 2 (MEDIUM):* `SANITIZE` — Masks sensitive patterns with SHA-256 tokens in-flight.
  - *Tier 3 (HIGH):* `BLOCK_TRANSFER` — Halts transfer and requires explicit escalation.
  - *Tier 4 (CRITICAL):* `QUARANTINE_AND_ALERT_CEO` — Immediately isolates the process, revokes credentials, and triggers an urgent CEO incident alert.

### 5.2 Credential Origin Tracker (`core/coworker/credential_masking_tracker.py`)
Tracks origin and usage of secret tokens via salted HMAC-SHA256 hashes. Enables full forensic traceability across tool executions without exposing plaintext credentials in memory dumps or persistent logs.

---

## 6. Verification and Acceptance Matrix Summary

| Subsystem / Module | File Path | Architectural Role | Verification Status |
| :--- | :--- | :--- | :--- |
| **ExecutiveOperatingLoop** | `core/coworker/executive_operating_loop.py` | 8-tier priority queue, DoA enforcement, re-entrant locking | **VERIFIED (100% Green)** |
| **LocalInferenceAdapter** | `core/coworker/local_inference_adapter.py` | ARM64 hardware budget, Ollama probe, honest status | **VERIFIED (100% Green)** |
| **DLPEngine** | `core/coworker/dlp_engine.py` | 12 sensitive categories, 10 channels, entropy analysis | **VERIFIED (100% Green)** |
| **DLPResponseLadder** | `core/coworker/dlp_response_ladder.py` | 4-tier risk ladder (Audit, Sanitize, Block, Quarantine) | **VERIFIED (100% Green)** |
| **CredentialMaskingTracker** | `core/coworker/credential_masking_tracker.py` | Salted HMAC-SHA256 zero-knowledge origin tracing | **VERIFIED (100% Green)** |
| **EmployeeSupportService** | `core/coworker/employee_support_service.py` | Diagnostic triage preserving employee role ownership | **VERIFIED (100% Green)** |
| **SpecialistTeamAssembler** | `core/coworker/specialist_team_assembler.py` | 12 archetypes, typed schemas, subordinate leases | **VERIFIED (100% Green)** |
| **CapabilityRegistryV3** | `core/coworker/capability_registry_v3.py` | AST security screening & approved license filter | **VERIFIED (100% Green)** |
| **OpenCodeEngine** | `core/coworker/opencode_engine.py` | 7-stage Ralph Loop defect repair in Git worktrees | **VERIFIED (100% Green)** |
| **ComputerUseEngine** | `core/coworker/computer_use_engine.py` | Virtual X11 desktop, coordinate clicks, window trees | **VERIFIED (100% Green)** |
| **AcceptanceMissions** | `core/coworker/acceptance_missions.py` | Autonomous execution harness for Missions A through N | **VERIFIED (14/14 Green)** |

---

## 7. Conclusion

The Autonomous Executive Coworker architecture represents an enterprise-grade digital executive operating inside the ZONATA SaaS ecosystem. By unifying constitutional governance, priority-driven execution, defensive security, and workforce enablement, it establishes a reliable foundation for enterprise AI operations.
