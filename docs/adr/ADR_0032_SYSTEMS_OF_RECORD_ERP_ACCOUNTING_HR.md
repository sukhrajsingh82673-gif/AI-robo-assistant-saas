# ADR 0032: Systems of Record Architecture — ERP, Accounting, HR and Payroll

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 59 (Systems of Record are Ports), Rule 60 (Copyleft Business Systems Stay Separate Services)

---

## 1. Context & Problem Statement
ZONATA requires enterprise-grade accounting, inventory, manufacturing, and HR/payroll capabilities without re-implementing mature ERP systems from scratch or compromising sovereign database integrity.

## 2. Decision
1. **Lead Solution for ERP & HR:** ERPNext 16 with Frappe HR and India Compliance is selected as the primary external system-of-record container for pilots.
2. **License Isolation (Rule 60):** ERPNext is licensed under GPL-3.0 / AGPL-3.0. It runs exclusively as an unmodified, isolated network container service reached via REST APIs. ZONATA never imports, vendors, or copies ERPNext source code.
3. **Alternative Evaluation:** Odoo 20 Community (LGPL-3.0) was evaluated; however, its advanced manufacturing and full accounting modules are restricted to the proprietary Enterprise edition.
4. **Authoritative Provider Invariant (Rule 59):** For any company, exactly ONE provider (either the native Step 1 Ledger/HR kernel or an external ERPNext instance) is designated as authoritative. Writes to mirror systems must be verified by independent re-read.
5. **Drift Detection:** A scheduled reconciliation job compares balances, transaction counts, and inventory lot hashes between ZONATA and the external ERP, raising failure events upon drift. Drift never auto-corrects.

## 3. Consequences
- Safe adoption of mature open-source ERP systems without copyleft contamination.
- Clear audit trails and authoritative ledger consistency.
