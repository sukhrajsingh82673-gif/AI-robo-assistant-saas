# ZONATA V7 — Employee Memory Segregation & Knowledge Governance
**Document ID:** ZONATA-V7-MEM-KNOW-009  
**Classification:** MEMORY SEGREGATION & KNOWLEDGE ACCESS ARCHITECTURE  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. 5-Tier Memory & Knowledge Segregation

A core constitutional invariant in ZONATA is: **Memory is NOT Authority. Memory is NOT Permission.**

Template-built employees maintain strict segregation across five distinct memory tiers:

```
[1. Working Memory]         --> Ephemeral mission scratchpad; wiped upon mission completion.
[2. Long-Term Memory]       --> Employee role experience, procedural preferences (Letta-backed).
[3. Corporate Knowledge]    --> Authoritative company policies, SOPs, documentation (Pre-retrieval RAG).
[4. Mission Context]        --> Active mission parameters, assigned budget, lease tokens.
[5. Cryptographic Evidence] --> Read-only, append-only Merkle ledger (WORM storage).
```

---

## 2. Pre-Retrieval Authorization & Knowledge Bounds

When a Template Employee queries corporate knowledge:
1. The employee's `allowed_data_classes` (e.g. `["INTERNAL", "CONFIDENTIAL"]`) and `department_id` are injected into the pre-retrieval SQL filter.
2. Documents classified as `RESTRICTED` (e.g., M&A negotiations, executive compensation) are filtered out at the index level.
3. No sensitive document chunks enter the prompt context, eliminating RAG context leakage.

---

## 3. Controlled Memory Transfer During Succession

When an employee is replaced or promoted (e.g. Booking Assistant V1 -> V2):
- Only explicitly authorized memory classes (e.g. `BOOKING_PATTERNS`, `GUEST_PREFERENCES`) are migrated to the successor.
- Raw operational tokens, revoked session keys, and uncommitted scratch files are shredded.
- Predecessor's historical audit records remain permanently bound to V1 in the Merkle ledger.
