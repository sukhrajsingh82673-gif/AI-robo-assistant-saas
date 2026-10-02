# AGENT FACTORY SECURITY MODEL & GOVERNANCE SPECIFICATION
**ZONATA Universal AI Company Operating System**  
*Classification: RESTRICTED / INTERNAL PRODUCTION AUDIT*  
*Timestamp: 2026-10-02T11:15:00Z*

---

## 1. Constitutional Invariants of the Agent Factory

The ZONATA Agent Factory operates under seven foundational non-negotiable invariants:

```
1. AGENT != AUTHORITY
   Creating an agent never grants business authority.

2. AGENT != TRUST
   An agent is an untrusted computational worker until verified.

3. AGENT != PERMISSION
   Possession of tools or skills does not convey permission to mutate.

4. AGENT MEMORY != AUTHORITY
   Data stored in Letta memory blocks cannot override policy rules.

5. AGENT CAPABILITY != AUTHORITY
   Registration of capability does not confer right to execute.

6. AGENT CREATION != ACTIVATION
   Synthesizing an agent places it in governed lifecycle review.

7. AGENT SUCCESS != BUSINESS SUCCESS
   Model completion or exit code 0 does not constitute business outcome.
```

---

## 2. Governed 12-State Agent Lifecycle Pipeline

Every autonomous agent created in ZONATA must transition through a controlled state machine:

```
[REQUEST]
   │
   ▼
[DESIGNED] ──► [VALIDATING] ──► [SANDBOXED] ──► [TESTING]
                                                   │
   ┌───────────────────────────────────────────────┘
   │
   ▼
[PENDING_APPROVAL] ──(Human-in-the-Loop)──► [APPROVED]
   │                                           │
   ▼                                           ▼
[REJECTED]                                  [ACTIVE]
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                               ▼                               ▼
          [DEGRADED]                     [SUSPENDED]                     [QUARANTINED]
               │                               │                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
                                      [REVOKED / RETIRED] (Terminal)
```

---

## 3. Server-Side Anti-Explosion Resource Quotas

To prevent infinite agent spawning, runaway delegation, and resource exhaustion, `core/agent_factory_runtime.py` enforces hard server-side boundaries:

| Quota Parameter | Default Value | Enforcement Mechanism | Failure Action |
| :--- | :--- | :--- | :--- |
| **Max Agents per Tenant** | 100 | SQL count check on `governed_agents` | Raises `AgentFactoryQuotaException` |
| **Max Agents per Company** | 50 | SQL count check on `company_id` | Raises `AgentFactoryQuotaException` |
| **Max Child Agents per Parent** | 5 | Checks `parent_agent_id` count | Blocks further spawning from parent |
| **Max Delegation Depth** | 4 | Tracks `delegation_depth` hierarchy | Halts recursive task delegation |
| **Max Concurrent Missions** | 20 | Mission system concurrency limiter | Queues or rejects excess missions |
| **Max Tool Calls per Mission** | 100 | Step execution counter | Halts mission in `BUDGET_EXCEEDED` |
| **Max Token Budget per Run** | 1,000,000 | Token usage governor | Escalates to human approval |

---

## 4. Self-Modification Defense

Autonomous agents are strictly blocked from mutating any of the following immutable governance modules:
- `core.policy`
- `core.authority`
- `core.approvals`
- `core.credential_broker`
- `core.control_kernel`
- `core.evidence_ledger`
- `core.business_causality`
- `core.db`
- `core.auth`
- `core.agent_factory_runtime`
- `core.storage_governor`

Any code-execution, file-write, or tool invocation attempting to modify these files or runtime classes raises `SelfModificationViolation` and instantly transitions the calling agent to `QUARANTINED` status.
