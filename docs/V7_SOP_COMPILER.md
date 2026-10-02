# ZONATA V7 — SOP Ingestion & Operational Policy Compiler
**Document ID:** ZONATA-V7-SOP-003  
**Classification:** KNOWLEDGE INGESTION & POLICY COMPILATION SPECIFICATION  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. SOP Interpretation Pipeline

ZONATA's `SOPPolicyCompiler` (`core/sop_compiler.py`) converts unstructured and semi-structured corporate standard operating procedures into machine-executable policy rules:

```
[Raw Corporate SOP Document (Markdown, TXT, PDF extract)]
                           |
                           v
              [1. Structural Section Parser]
                           |
                           v
        +------------------+------------------+
        |                  |                  |
[Responsibilities]    [Authorities]     [Constraints]
        |                  |                  |
[Process Steps]       [Escalations]     [KPI/Metrics]
        |                  |                  |
        +------------------+------------------+
                           |
                           v
         [2. Source Provenance Linker]
                           |
                           v
     [3. Discretionary Ambiguity Detection]
       - Discretionary language flagged:
         "AMBIGUOUS_REQUIRES_REVIEW"
                           |
                           v
       [Structured SOP Compilation Result]
```

---

## 2. Policy Rule Provenance Tracking

Every machine-interpreted policy retains an unbroken cryptographic link to the exact document section and verbatim statement from which it was extracted:

| Rule ID | Rule Type | Source Doc | Source Section | Extracted Statement | Interpreted Machine Policy | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rul_8f1a` | `AUTHORITY` | `Royal_Hotel_SOP.md` | `Authority and Approvals` | *"Spending ceiling up to ₹10,000"* | `MAX_FINANCIAL_THRESHOLD <= 10000.0` | `VALIDATED` |
| `rul_9b2c` | `CONSTRAINT` | `Royal_Hotel_SOP.md` | `Authority and Approvals` | *"Must not offer room upgrades beyond Deluxe"* | `HARD_CONSTRAINT: beyond Deluxe` | `VALIDATED` |
| `rul_4c3d` | `AUTHORITY` | `Royal_Hotel_SOP.md` | `Authority and Approvals` | *"Handle VIP complaints at discretion"* | `AMBIGUOUS_DISCRETIONARY_INSTRUCTION` | **`AMBIGUOUS_REQUIRES_REVIEW`** |

---

## 3. Discretionary Ambiguity Guardrails

AI assistants frequently "hallucinate" authorization rules when presented with ambiguous human directives (e.g., *"use your best judgment"*, *"handle at discretion"*).

ZONATA V7 enforces the **Non-Hallucination Invariant**:
- If an operational instruction contains discretionary language without a clear mathematical ceiling or supervisor signoff trigger, the compiler assigns a confidence score $< 0.50$.
- The statement is marked `AMBIGUOUS_REQUIRES_REVIEW` and flagged in the compilation report.
- The Employee Factory requires explicit supervisor confirmation before provisioning.
