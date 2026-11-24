# ADR 0042: Canonical E-Invoicing Model (EN 16931) and National Clearance/Tax Adapters

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 59 (Systems of Record are Ports), Rule 60 (Statutory Content is Data), Rule 70 (Standards as Data), Rule 73 (Global by Construction)

---

## 1. Context & Problem Statement
Governments worldwide are mandating electronic invoicing (e-invoicing) and continuous transaction controls (CTC). Over 80 jurisdictions have enacted or scheduled mandatory e-invoicing between 2024 and 2027.
Architectural models fall into three broad archetypes:
1. **Clearance Models:** Invoices must be registered and cryptographically stamped by a government portal prior to or concurrent with transmission to the buyer:
   - India (IRP / NIC, JSON payload with HMAC-SHA256 IRN and QR code).
   - Italy (Sistema di Interscambio / SdI, XML FatturaPA).
   - Poland (Krajowy System e-Faktur / KSeF, XML FA_VAT).
   - Saudi Arabia (ZATCA Fatoora Phase 2, UBL 2.1 with cryptographic stamp and ECDSA signature).
   - Mexico (CFDI 4.0, XML with PAC digital timbre).
2. **Post-Audit / Exchange Models:** Bilateral exchange in structured formats with retrospective tax audit:
   - Germany (XRechnung / ZUGFeRD 2.2 hybrid PDF/A-3).
3. **Four-Corner Peppol Networks:** Federated exchange via certified Access Points (e.g., Belgium, Norway, Australia, Singapore).

Hardcoding separate invoice engines for each nation leads to code bloat and fragmented data models.

---

## 2. Decision: EN 16931 Semantic Core with Polymorphic National Export Adapters

We adopt a two-tier architecture:

```
[ Domain Billing / Sales Engine ]
                │
                ▼
┌───────────────────────────────────────────────┐
│ Canonical E-Invoice Model (EN 16931 Semantic) │
│ - Header, Supplier, Customer, Delivery        │
│ - Line Items, Allowances, Charges, Taxes      │
│ - Payment Means, Totals (Integer Minor Units) │
└───────────────────────────────────────────────┘
                │
    ┌───────────┴───────────┬───────────────┬────────────────┐
    ▼                       ▼               ▼                ▼
[India IRP Adapter]   [Italy SdI]     [Saudi ZATCA]    [Peppol BIS 3.0]
 (JSON / IRN hash)     (FatturaPA)     (UBL 2.1 XML)    (UBL 2.1 / CII)
```

1. **Canonical Semantic Core (EN 16931):**
   - We define `CanonicalInvoice` strictly adhering to European Standard **EN 16931-1:2017** (Electronic invoicing - Semantic data model of the core elements of an electronic invoice).
   - Implemented as a type-safe Pydantic model in `core/invoicing/canonical.py`.
   - All amounts are minor integer units in ISO 4217 currencies; all tax rates and codes map to UN/CEFACT EDIFACT 5305 and 5153 codes.
2. **Polymorphic National Adapters:**
   - National formats derive from `BaseInvoiceAdapter`:
     - `IndiaIRPAdapter`: Maps EN 16931 $\to$ India GST e-Invoice Schema (version 1.03 JSON). Generates canonical hash and validates HSN/SAC codes.
     - `ItalySdIAdapter`: Maps EN 16931 $\to$ FatturaPA 1.2 XML with Codice Destinatario or PEC routing.
     - `SaudiZATCAAdapter`: Maps EN 16931 $\to$ ZATCA Phase 2 compliant UBL 2.1 XML, including cryptographic stamps and previous invoice hash chaining.
     - `GermanyZUGFeRDAdapter`: Maps EN 16931 $\to$ Cross Industry Invoice (CII) XML embedded into PDF/A-3.
     - `PeppolBIS3Adapter`: Maps EN 16931 $\to$ Peppol BIS Billing 3.0 UBL 2.1 XML.
3. **Peppol Network Access Point Strategy:**
   - For Peppol connectivity, we integrate via open-source AS4 Access Point software (such as **Oxalis** or **phase4**, both Apache-2.0 licensed) operating as an external network microservice behind `PeppolPort`.
   - Zero GPL code is introduced; AS4 protocol messaging is isolated from the core application.
4. **Statutory Tax Engine & Fallback:**
   - Tax determinations (VAT, GST, Sales Tax) are computed by declarative jurisdiction rule tables.
   - If an invoice requires tax determination but no certified rule exists for that transaction category, the invoice is blocked and escalated to a human tax accountant (`TaxRuleUnverifiedEscalation`).

---

## 3. License, Boundary & Security Notes
- **EN 16931 Standard:** The semantic data definitions are public European standards implemented without proprietary binary blobs.
- **Oxalis / phase4:** Open-source AS4 communication libraries under Apache-2.0.
- **Cryptographic Keys:** Digital signing certificates (e.g., ZATCA ECDSA private keys, India DSC keys) are securely stored in OpenBao Transit/KV and never logged or exposed to LLM principals.
