# ADR 0043: Multi-Company Group Consolidation Architecture

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 59 (Independent Re-Read), Rule 67 (Preservation Extension), Rule 73 (Global by Construction)

---

## 1. Context & Problem Statement
In Steps 1 through 7, each company operates with an isolated, immutable double-entry ledger in the `core/ledger/` engine. Large enterprise customers operate as multi-entity groups comprising parent holding companies, international operating subsidiaries, regional sales offices, and special purpose entities (SPEs).

Consolidating group financials across disparate entities involves:
- Multi-currency translation across functional and presentation currencies (IAS 21 / ASC 830).
- Intercompany balance reconciliation and automated eliminations (intercompany sales, payables/receivables, dividends).
- Minority interest (non-controlling interest) calculations.
- Parallel statutory local GAAP vs Group IFRS/US-GAAP reporting.

Crucially, **Rule 67 strictly prohibits modifying the Step 1–7 financial ledger kernel**. Group consolidation must be purely additive.

---

## 2. Decision: Additive Consolidation Schema, Independent Entity Ledgers & Elimination Layers

We design an additive, non-invasive consolidation engine:

```
┌────────────────────────────────────────────────────────┐
│                   Group Consolidation                  │
│               Schema: `consolidation`                  │
│                                                        │
│  ┌───────────────────────┐   ┌──────────────────────┐  │
│  │ FX Translation Engine │   │ Elimination Engine   │  │
│  │ (IAS 21 / ASC 830)    │   │ (Intercompany Auto)  │  │
│  └───────────────────────┘   └──────────────────────┘  │
└───────────────────────────▲────────────────────────────┘
                            │ Read via LedgerPort
            ┌───────────────┼───────────────┐
            │               │               │
     ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
     │ Subsidiary  │ │ Subsidiary  │ │ Parent Co   │
     │ Entity A    │ │ Entity B    │ │ Entity C    │
     │ Ledger (EUR)│ │ Ledger (INR)│ │ Ledger (USD)│
     └─────────────┘ └─────────────┘ └─────────────┘
```

1. **Autonomous Legal Entities:**
   - Every legal entity remains a sovereign `company` with its own immutable double-entry general ledger, chart of accounts, and local functional currency.
   - Entity ledgers are never directly mutated or written to by the consolidation process.
2. **Read Access via `LedgerPort` (Rule 59):**
   - The consolidation service reads entity account balances and journal lines exclusively through typed queries on `LedgerPort`.
3. **Additive Consolidation Schema (`consolidation`):**
   - All group structures, consolidation runs, currency translation adjustments (CTA), and elimination journals are stored in tables within a dedicated `consolidation` database schema:
     - `consolidation_groups`: Group hierarchy, presentation currency, consolidation accounting method.
     - `consolidation_entities`: Member companies, ownership percentage, consolidation method (Full, Proportionate, Equity).
     - `consolidation_runs`: Period-specific consolidation execution records with cryptographic evidence seals.
     - `consolidation_journals`: Elimination and reclassification entries (e.g., eliminating intercompany AP/AR and intercompany revenue/COGS).
4. **Currency Translation (IAS 21 / ASC 830):**
   - **Current Rate Method:** Assets and liabilities translated at period-end closing spot rate; income and expense translated at period average rate; equity translated at historical rates. The resulting translation difference is posted to the Cumulative Translation Adjustment (CTA) reserve in group equity.
   - **Temporal Method:** For hyperinflationary economies or subsidiaries with functional currency matching the parent.
   - Exchange rates are sourced directly from the historical exchange rate tables in the Step 1 database.
5. **Two-Sided Intercompany Reconciliation:**
   - Automated identification of matching intercompany transaction pairs (`entity_a_ar == entity_b_ap`).
   - If balances mismatch beyond a configured tolerance, the system creates a discrepancy record and triggers an intercompany reconciliation task.

---

## 3. License, Boundary & Security Notes
- Zero changes to `core/ledger/kernel.py` or existing migration scripts.
- Multi-company access is strictly gated by group-level RLS policies, preventing unauthorized cross-company visibility.
