# ZONATA Universal AI Agent Factory — architecture package

Prepared 2026-11-15. Start with `EXECUTIVE_ARCHITECTURE.md`. Hand `OPENCODE_MASTER_IMPLEMENTATION_PROMPT.md` + this folder to OpenCode and run **Phase 1 (read-only audit) first**.

| # | File |
|---|---|
| 1 | EXECUTIVE_ARCHITECTURE.md |
| 2 | EXISTING_SYSTEM_AUDIT.md (status: UNKNOWN — repo was not accessible; Phase 1 closes this) |
| 3 | OPEN_SOURCE_EVALUATION.md |
| 4 | TARGET_ARCHITECTURE.md |
| 5 | FACTORY_ORGANISATION.md |
| 6 | MANUFACTURING_LIFECYCLE.md |
| 7 | MULTI_AGENT_MANUFACTURING.md |
| 8 | TEMPLATE_AND_CAPABILITY_SYSTEM.md |
| 9 | SECURITY_AND_GOVERNANCE.md |
| 10 | DATABASE_AND_API_SPECIFICATION.md |
| 11 | QA_AND_CERTIFICATION.md |
| 12 | UI_UX_SPECIFICATION.md |
| 13 | INFRASTRUCTURE_AND_DEPLOYMENT.md |
| 14 | IMPLEMENTATION_ROADMAP.md |
| 15 | OPENCODE_MASTER_IMPLEMENTATION_PROMPT.md (self-contained, with tested reference appendices) |
| 16 | GAP_AND_RISK_REGISTER.md |
| 17 | FINAL_ARCHITECTURE_DECISION_RECORD.md |

`reference/` — executed-and-tested artefacts: SQL (17/17 checks on PostgreSQL 16.15), JSON schema/specs, gate policy + evaluator (14/14), batch planner (15/15), signing/ledger reference (11/11), API contract, acceptance tests. Raw outputs are in the `*.last_run.txt` files.
`tools/` — `audit_scan.py` (repo scanner), `check_mermaid.py`, `build.py` (regenerates the top-level docs from `_src/`).

Evidence tags used in the docs: [SRC] read from source, [WEB] fetched 2026-11-15, [KNOWLEDGE] not re-verified, [CLAIM] vendor statement.
