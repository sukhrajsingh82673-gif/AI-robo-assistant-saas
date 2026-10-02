# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Action Risk Governance & Invariant Enforcement

### 1. The Core Constitutional Invariants

1. **`capability != authority`**: The fact that a Salesforce or Stripe connection exists in Nango does not give an AI agent permission to invoke operations.
2. **`connection != authorization`**: Holding an active OAuth connection never grants unmonitored execution authority.
3. **`TASK_SUCCESS != BUSINESS_OUTCOME`**: A `200 OK` from an external API or a completed sync job is operational execution, not proof of commercial business outcome.
4. **`retry != safe replay`**: Non-idempotent or financial mutations must never be automatically retried without re-verifying business state.

---

### 2. Action Risk Classification Framework

Every integration capability is categorized into one of 8 risk tiers:

| Risk Class | Description | Policy Gate | Approval Requirement |
| :--- | :--- | :--- | :--- |
| `READ_ONLY` | Read-only data queries (e.g. read contacts, get balances) | Automated | None |
| `LOW_RISK` | Low-impact operational actions (e.g. post Slack status) | PolicyEngine check | None |
| `DATA_ENTRY` | Standard CRUD entry (e.g. create lead, file Jira bug) | PolicyEngine check | None |
| `BUSINESS_MUTATION` | Modifies existing business state (e.g. update opportunity) | PolicyEngine check | Conditional |
| `FINANCIAL` | Money movement or invoicing (e.g. Stripe charge, QB invoice) | Strict Policy | **Human Approval Mandatory** |
| `PRIVILEGED` | System configuration or permission alteration | Strict Policy | **Human Approval Mandatory** |
| `DESTRUCTIVE` | Record deletion or purge operations | Strict Policy | **Human Approval Mandatory** |
| `IRREVERSIBLE` | Uncompensated transactions or public external broadcasts | Strict Policy | **Human Approval Mandatory** |

---

### 3. Merkle Evidence Ledger & Business Causality Linkage

When an external action completes:
1. Physical assertions (exit codes, response status, idempotency key verification) are compiled.
2. An `EvidencePackage` is cryptographically sealed with SHA-256 hashes in `storage/evidence/audit_ledger.jsonl`.
3. The `BusinessCausalityEngine` records the causal chain from `Strategy -> Mission -> Task -> Action -> Transaction -> Revenue` (`OutcomeStatus.VERIFIED_SUCCESS`), proving commercial causality.
