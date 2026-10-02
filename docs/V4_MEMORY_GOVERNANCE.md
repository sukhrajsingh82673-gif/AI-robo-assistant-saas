# ZONATA V4 — COGNITIVE MEMORY GOVERNANCE & TIERING
**Separation of Ephemeral Context, Long-Term Memory, Corporate Knowledge, & Evidence**

## 1. Cognitive Memory Architecture
A fundamental architectural flaw in conventional agent systems is confusing agent conversational memory with corporate truth. ZONATA V4 strictly separates memory into 4 segregated tiers (`core/memory_governance.py`):

```
┌──────────────────────────────────────────────────────────┐
│  Tier 1: WORKING MEMORY (Scratchpad / Ephemeral Context)  │
│  - Session-scoped, unverified, wiped on mission finish   │
└──────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│  Tier 2: LONG-TERM SEMANTIC MEMORY (Agent Learned Memory) │
│  - Heuristics, past experience; non-authoritative        │
└──────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│  Tier 3: CORPORATE KNOWLEDGE BASE (Governed Documents)   │
│  - Ingested via Corporate Data Plane, versioned, ACLs    │
└──────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│  Tier 4: MERKLE EVIDENCE LEDGER (Immutable Audit Trail)  │
│  - Cryptographically sealed append-only ledger of truth │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Invariant Enforcement
- `MEMORY != EVIDENCE`: Agent working memory cannot be submitted as legal or compliance evidence.
- `MEMORY != AUTHORITY`: An agent cannot grant itself authority or bypass policy because it "recalls" prior approval in its chat history. Every action must obtain fresh cryptographic authorization.
