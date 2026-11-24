# Enterprise Production Pilot Charter & Governance Agreement (ADR 0047 & Rule 74)

## 1. Pilot Scope and Parameters

- **Customer Organization:** `{{CUSTOMER_LEGAL_NAME}}`
- **Designated Enterprise Cell:** `{{TARGET_REGIONAL_CELL}}` (e.g., `cell-eu-frankfurt`)
- **Evaluated Domain Overlays:** `{{TARGET_ISIC_CODES}}` (e.g., `C28`, `G47`)
- **Pilot Term:** 30 Calendar Days (Effective `{{START_DATE}}` to `{{END_DATE}}`)
- **Execution Mode:** Passive Shadow Mode (Phase 1: Day 1–14) -> Governed Assisted Mode (Phase 2: Day 15–30).

---

## 2. Invariant Commitments & Safeguards

1. **Passive Shadow Mode Zero-Write Invariant (Rule 74):**
   - During Phase 1, Zonata operates purely in shadow observation mode.
   - The system intercepts read-only webhooks and generates recommendations in an isolated shadow ledger.
   - **Zero external writes, zero database commits, and zero production side-effects.**
2. **Hard Sector Boundary Enforcement (Rule 72):**
   - Automated refusal of clinical prescriptions, legal advice, consumer credit scoring, or unapproved payment disbursement.
3. **Emergency Isolation & Kill-Switch (Rule 75):**
   - Either party may trip the tenant kill-switch at any moment for any security or operational anomaly.
   - Tripping the kill-switch halts all autonomous workers and revokes credentials in $< 1.0$ second.
4. **Clean Exit & Irreversible Erasure:**
   - At the conclusion of the pilot, client data may either be transitioned to full production or completely exported and cryptographically erased with an official Erasure Receipt under GDPR Art. 17.

---

## 3. Designated Human Gatekeepers

| Role | Client Representative | Contact & PGP Key |
| :--- | :--- | :--- |
| **Executive Sponsor** | `{{CLIENT_EXEC_NAME}}` | `{{CLIENT_EXEC_EMAIL}}` |
| **Data Protection Officer (DPO)** | `{{CLIENT_DPO_NAME}}` | `{{CLIENT_DPO_EMAIL}}` |
| **IT Security Lead** | `{{CLIENT_CISO_NAME}}` | `{{CLIENT_CISO_EMAIL}}` |
| **Zonata Pilot Lead** | `{{ZONATA_LEAD_NAME}}` | `{{ZONATA_LEAD_EMAIL}}` |

---

## 4. Formal Signoff

```text
CLIENT AUTHORIZED SIGNATURE: __________________________   DATE: ______________
ZONATA AUTHORIZED SIGNATURE: __________________________   DATE: ______________
```
