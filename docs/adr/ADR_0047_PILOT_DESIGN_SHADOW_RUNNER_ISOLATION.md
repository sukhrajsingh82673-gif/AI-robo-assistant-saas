# ADR 0047: Enterprise Pilot Design, Passive Shadow Runner, and Tenant Isolation

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 41 (Zero Plaintext Secrets), Rule 67 (Preservation Extension), Rule 76 (Pilot Guardrails)

---

## 1. Context & Problem Statement
Deploying autonomous agent capabilities into real enterprise client environments poses acute operational and liability risks. Enterprise stakeholders require ironclad safety guarantees before permitting autonomous operations:
- A progressive, phased onboarding path starting with non-intrusive observation.
- A guarantee that early pilot phases cannot mutate production systems of record.
- Immediate kill-switch capability to cut off agent access within seconds.
- Seamless, complete data export and guaranteed cryptographic erasure upon pilot termination.
- An objective readiness gate that prevents premature deployment.

---

## 2. Decision: 3-Stage Pilot Progression, Zero-Write Shadow Runner, and Automated Readiness Gate

We establish a comprehensive pilot qualification framework:

```
┌────────────────────────────────────────────────────────┐
│  Phase 0: Passive Shadow Mode                          │
│  - Reads production webhooks/events via Ports          │
│  - Generates proposed actions & shadow predictions     │
│  - ZERO external writes (Hardware/software spy proof)  │
└───────────────────────────┬────────────────────────────┘
                            │ Human Review & Decision
                            ▼
┌────────────────────────────────────────────────────────┐
│  Phase 1: Supervised HITL Mode                         │
│  - Executes low-risk reads and drafts                  │
│  - High-impact actions require explicit human signoff  │
└───────────────────────────┬────────────────────────────┘
                            │ Human Review & Decision
                            ▼
┌────────────────────────────────────────────────────────┐
│  Phase 2: Bounded Autonomous Mode                      │
│  - Governed autonomy within strictly budgeted limits   │
│  - ActionGateway dual-control enforcement              │
└────────────────────────────────────────────────────────┘
```

1. **Passive Shadow Runner (`core/pilot/shadow_runner.py`):**
   - The shadow runner connects to the partner system as a read-only observer.
   - For every incoming event (new sales lead, incoming vendor invoice, customer support ticket), the shadow runner executes full reasoning and drafts target responses or journal entries.
   - All proposed actions are recorded into an internal shadow evaluation store.
   - **Zero-Write Invariant (Spy Verification):** Contract and unit tests incorporate spy mocks on all external API adapters, proving that zero HTTP POST/PUT/DELETE requests or mutation queries are dispatched to partner systems during shadow mode.
2. **Dedicated Isolated Tenant:**
   - Every pilot runs in a strictly segregated tenant environment with its own dedicated database schema, encryption key in OpenBao, and isolated Temporal task queue.
3. **Emergency Kill-Switch Drill:**
   - Every pilot tenant possesses a hardware/software kill switch callable via API or UI button.
   - Tripping the kill switch immediately revokes all active session tokens, cancels pending Temporal workflow executions, disconnects webhooks, and freezes the tenant into read-only quarantine.
   - Kill-switch drill execution and sub-second cutoffs must be verified in pre-flight drills before any pilot launch.
4. **Automated Pilot Readiness Gate (`scripts/pilot_readiness.py`):**
   - Evaluates platform readiness across 7 mandatory criteria:
     1. Preservation proof (Steps 1–7 regression tests passing).
     2. Security posture and SOC 2 / ISO 27001 control compliance.
     3. Pilot charter on file with signed human sponsor.
     4. Verified industry and jurisdiction overlays ($\ge \text{T2}$ with human reviewer credentials).
     5. Benchmark report on file with verified claims.
     6. Successful kill-switch and backup restoration drill.
     7. Zero unmitigated high/critical vulnerability findings.
   - The script outputs either `NOT_READY` (listing exact missing prerequisites) or `READY_FOR_HUMAN_GO_DECISION`.
   - **Critical Rule 76 Constraint:** The automated gate script **never outputs an autonomous "GO"**; only a human executive can make the go decision.
5. **Clean Exit & Return Plan:**
   - At pilot conclusion, the platform executes a two-phase offboarding:
     - Full data export pack generated via Step 1F export tools.
     - Cryptographic data shredding and deletion certificate emission via Step 5F data erasure workflows.

---

## 3. License, Boundary & Security Notes
- All pilot monitoring metrics are emitted locally; zero client personal or financial data leaves the sovereign regional cell.
- Readiness reports are dynamically synthesized from cryptographically verifiable audit records; static manual editing of report files cannot satisfy the gate check.
