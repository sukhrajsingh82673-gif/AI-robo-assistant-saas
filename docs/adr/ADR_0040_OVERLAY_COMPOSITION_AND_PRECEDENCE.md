# ADR 0040: Overlay Composition, Layering and Deterministic Precedence

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 68 (Industry Neutrality), Rule 70 (Standards as Data), Rule 71 (Depth Earned by Human Review), Rule 72 (Hard Sector Boundaries)

---

## 1. Context & Problem Statement
An enterprise company instance is never a single monolithic configuration. A pharmaceutical manufacturer in Germany requires:
- Generic ERP & SaaS core capabilities (Step 1–6).
- Departmental workflows (Step 7: Finance, Supply Chain, Operations).
- Industry-specific capabilities (Step 8: Manufacturing BOMs, batch tracking, FDA/GMP compliance).
- Jurisdiction-specific mandates (Step 8: Germany GoBD, German chart of accounts SKR03/SKR04, German tax/e-invoicing).
- Tenant-specific overrides (Company-specific approval hierarchies, chart of accounts mappings).

Without a strictly defined composition algebra, layered configurations suffer from non-deterministic overwrites, ambiguous defaults, and hidden security boundary bypasses.

---

## 2. Decision: 5-Layer Composition Stack with Deterministic Precedence

We define a 5-layer configuration composition hierarchy evaluated in strictly ascending order:

| Layer Level | Layer Name | Priority | Scope & Mutability |
| :--- | :--- | :--- | :--- |
| **L0** | Platform Core (`core/`) | 0 | Baseline system entities, ledger kernel, security enforcers. Immutable. |
| **L1** | Department Packs (`packs/departments/`) | 10 | Standard business workflows (Lead-to-Cash, Procure-to-Pay, Hire-to-Retire). |
| **L2** | Industry Overlay (`packs/industries/`) | 20 | Domain calculators, specialized SOPs, industry document types, sector boundaries. |
| **L3** | Jurisdiction Pack (`packs/jurisdictions/`)| 30 | Statutory accounting standards, tax calculators, e-invoicing adapters, holiday calendars. |
| **L4** | Tenant Customization (`tenants/<tenant_id>/`) | 40 | Tenant-specific configuration overrides, custom approval thresholds, branding. |

### Composition Algebra & Merge Semantics
1. **Additive Extension:** Overlays primarily contribute additive entities (new document schemas, new metric definitions, new calculators).
2. **Conflict Resolution & Collision Detection:**
   - If two layers define the same entity identifier (e.g., both Industry Overlay and Jurisdiction Pack declare `invoice_tax_calculator`), the higher-priority layer wins, but an explicit **Conflict Resolution Record** must be logged and verified.
   - If two sibling overlays at the same layer attempt to override the same entity, the composition engine raises `OverlayCompositionConflictError` and refuses to deploy.
3. **Hard Sector Boundary Immutability (Rule 72):**
   - Boundary policies (e.g., `refuse_clinical_prescription`, `refuse_legal_advice`, `refuse_safety_control_write`) declared in L2 or L0 are **hard non-overrideable limits**.
   - No higher layer (L3 or L4) can weaken or disable a boundary policy. Any attempt to relax a boundary condition in tenant configuration raises `SecurityBoundaryViolationError`.
4. **Promotion Tiers (Rule 71):**
   - Overlays carry a maturity tier: `T0` (Unverified Draft), `T1` (Factory Generated), `T2` (Reference Verified), `T3` (Expert Certified), `T4` (Regulatory Audited).
   - Unreviewed overlays (`T0`/`T1`) cannot elevate autonomy levels beyond supervised execution.

---

## 3. License, Boundary & Security Notes
- Overlays are pure declarative YAML/JSON data files conforming to `zonata.industry-overlay/v1` and `zonata.jurisdiction-pack/v1` schemas.
- Overlay engines execute inside an isolated sandbox with zero dynamic code execution (`eval` or `exec` strictly prohibited).
