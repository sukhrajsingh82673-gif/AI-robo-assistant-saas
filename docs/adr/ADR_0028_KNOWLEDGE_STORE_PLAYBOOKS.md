# ADR 0028: Governed Knowledge Store — PostgreSQL pgvector & `zonata.playbook/v1`

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Security Arbiter, Repository Owner
- **Governing Rules:** Rule 41 (No Plaintext Secrets), Rule 43 (Transaction-Scoped RLS), Rule 53 (Mandatory Provenance)

---

## 1. Context & Problem Statement
The system requires a persistent, multi-tenant knowledge store to record learned playbooks, verified lessons, execution exemplars, and anti-patterns derived from failure analysis and owner instructions.

## 2. Decision
1. **Storage Substrate:** We utilize PostgreSQL 16 with the `pgvector` extension for semantic embedding retrieval, backed by strict Row-Level Security (`tenant_id`, `company_id`).
2. **Declarative Schema (`zonata.playbook/v1`):** Playbooks are versioned declarative structures containing trigger conditions, step instructions, parameter templates, risk classes, and mandatory cryptographic provenance links to verified evidence IDs.
3. **Dual Retrieval Strategy:** Retrieval operates via deterministic exact matching (taxonomy, tool, error code) first, followed by cosine similarity semantic ranking.
4. **Open Standard Compatibility:** We provide an import/export adapter for the open `agentskills.io` standard, gated by AST sanitization to neutralize prompt injection payloads.
5. **Prompt Injection Boundary:** Learned playbooks enter model context in a strictly delimited and labelled data block, subordinate to system constitutional rules.

## 3. Consequences
- Zero cross-tenant knowledge leakage.
- Direct traceability from every learned playbook to the verified evidence that justified its creation.
- Crypto-shredding (GDPR Art. 17) deletes all derived playbooks when a tenant key is destroyed.
