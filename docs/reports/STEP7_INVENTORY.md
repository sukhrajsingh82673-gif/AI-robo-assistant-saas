# Step 7 Department Capability Inventory (`docs/reports/STEP7_INVENTORY.md`)

**Date:** 2026-11-24  
**Author:** Antigravity Architect  
**Reviewer:** OpenCode Arbiter  
**Scope:** Department capabilities, systems of record, process packs, region packs, connectors, and tools.

---

## 1. Summary of Inventory

This inventory evaluates the codebase across 10 functional domains to identify existing components, partial implementations, and gaps requiring development in Step 7.

| Domain | Status | Key Existing Modules | Primary Gaps to Address in Step 7 |
| :--- | :--- | :--- | :--- |
| **1. Finance & Accounting** | `PARTIAL` | `core/ledger/` (Double-entry kernel) | AP 3-way match, bank reconciliation, vendor fraud hold, India GST/e-invoicing |
| **2. Sales & CRM** | `PARTIAL` | `core/work/`, `core/sop/`, `core/ports/` | Lead capture deduplication, consent checks, discount limits, CRM adapters |
| **3. Customer Support** | `PARTIAL` | `core/verification/`, `core/sop/` | HelpdeskPort, Chatwoot/Zammad adapter, SLA escalation clocks |
| **4. Marketing & Brand** | `PARTIAL` | `core/documents/`, `core/research/` | Brand guidelines as data, campaign budgeting, first-party attribution |
| **5. HR & Workforce** | `PARTIAL` | `core/organization/`, `core/authority/` | Fairness counterfactual tests, HR Port, payroll deterministic engine, offboarding |
| **6. Operations & Production**| `PARTIAL`| `core/industry_packs/`, `core/sop/` | BOM explosion, OEE calculation, lot holds on failed inspection |
| **7. Supply Chain & Procure** | `PARTIAL` | `core/ledger/`, `core/authority/` | Supplier sanctions checks, RFQ matrix, reorder point policies, carrier tracking |
| **8. R&D & Prototyping** | `PARTIAL` | `core/research/`, `core/agent_import/` | Immutable experiment tracking, PRD templates, sandboxed prototype runners |
| **9. Legal, IT & Security** | `PARTIAL` | `core/security/`, `core/compliance/` | Obligation extraction, contract redlines, IT asset inventory, posture checks |
| **10. Analytics & BI** | `PARTIAL` | `core/kpi/` | Semantic layer (Cube/MetricFlow behind BiPort), unified metric serving |

---

## 2. Detailed Capability Catalog

### 2.1 Finance & Accounting
- `core/ledger/kernel.py` (`EXISTS`, Tested): Core double-entry immutable financial ledger, zero-balance multi-currency verification.
- `core/ledger/accounts.py` (`EXISTS`, Tested): Chart of accounts, account types, balances.
- `core/ledger/transactions.py` (`EXISTS`, Tested): Transaction postings, reversing entries.
- `core/finance/ap_automation.py` (`MISSING`): 3-way matching (PO, receipt, invoice), vendor fraud bank-change cooling-off periods.
- `core/finance/bank_reconciliation.py` (`MISSING`): CSV/MT940/CAMT.053 parser, deterministic line matching with precision/recall scoring.
- `core/finance/gst_india.py` (`MISSING`): India GST e-invoicing JSON schema, IRP submission adapter, TDS hooks.

### 2.2 The Seven Core Process Packs
- `core/process_packs/engine.py` (`EXISTS`, Tested): Dynamic process pack engine running declarative workflows.
- `core/process_packs/schema.py` (`EXISTS`, Tested): Schema validator for process definitions.
- `core/process_packs/lead_to_cash.py` (`PARTIAL`): Order-to-invoice skeleton without real CRM/payment integration.
- `core/process_packs/procure_to_pay.py` (`PARTIAL`): Requisition skeleton without three-way match or vendor hold.
- `core/process_packs/record_to_report.py` (`PARTIAL`): Financial close checklist skeleton.
- `core/process_packs/hire_to_retire.py` (`PARTIAL`): Employee onboarding skeleton without payroll calculation.
- `core/process_packs/plan_to_deliver.py` (`PARTIAL`): BOM explosion and scheduling logic missing.
- `core/process_packs/support.py` (`PARTIAL`): Ticket escalation skeleton missing HelpdeskPort adapter.
- `core/process_packs/compliance.py` (`PARTIAL`): Policy tracking without statutory cite verification.

### 2.3 Region Packs
- `core/region_packs/engine.py` (`EXISTS`, Tested): Region pack loader enforcing sovereign regional rules.
- `packs/regions/india.yaml` (`PARTIAL`): GST rates, state codes, TDS sections (needs e-invoicing schema linkage).
- `packs/regions/us.yaml` (`PARTIAL`): US sales tax and state nexus declarations.
- `packs/regions/eu.yaml` (`PARTIAL`): GDPR retention and Peppol/UBL e-invoicing data.

### 2.4 Company Metrics & KPI Engine
- `core/kpi/engine.py` (`EXISTS`, Tested): Declarative KPI registration, measurement-source verification, freshness thresholds.
- `core/kpi/scorecard.py` (`EXISTS`, Tested): Executive scorecards, threshold evaluations, trend analysis.

### 2.5 Connectors, MCP & Integrations
- `core/mcp/client.py` (`EXISTS`, Tested): Governed client invoking external MCP servers.
- `core/mcp/server.py` (`EXISTS`, Tested): Local MCP tool registry and dispatcher.
- `core/connectors/` (`MISSING`): Formal Connector SDK with typed operations, pagination, rate-limiting, and replay contract fixtures.

### 2.6 Desktop & Browser Tools
- `core/browser/` (`EXISTS`, Tested): Sovereign browser automation engine behind ActionGateway.
- `core/universal_terminal/` (`EXISTS`, Tested): Sandboxed terminal executor with command filtering.
- `core/remote_view/` (`EXISTS`, Tested): Encrypted streaming remote takeover and audit capture.

---

## 3. Preflight Attestation
- **Baseline Invariant:** Steps 1 through 6 are certified and frozen under annotated tag `step6-final`.
- **Preservation Contract (Rule 58):** Zero legacy files from Steps 1–6 will be edited during Step 7. All Step 7 tables live in the `departments` schema.
- **Authoritative Ports:** All external systems (ERPNext, CRM, Helpdesk, Payments, BI) sit strictly behind typed Ports (Rule 59, Rule 60).
