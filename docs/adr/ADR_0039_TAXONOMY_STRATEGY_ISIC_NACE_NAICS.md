# ADR 0039: Multi-Scheme Industry Taxonomy Strategy (ISIC Rev. 5, NACE Rev. 2.1, NAICS 2022)

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 68 (Industry Neutrality), Rule 69 (Multi-Scheme Taxonomy), Rule 70 (Standards as Data)

---

## 1. Context & Problem Statement
In previous iterations (Step 1H), industry packs were implemented as ad-hoc, hand-crafted templates (`saas`, `hospitality`, `manufacturing`, `clinic`) loosely keyed to informal sector names. However, global enterprises operate under formal industrial classifications required for statutory reporting, regulatory compliance, risk underwriting, and procurement categorization.

Different jurisdictions enforce competing classification systems:
- **UN ISIC:** International Standard Industrial Classification of All Economic Activities. ISIC Rev. 5 was formally endorsed by the UN Statistical Commission in 2023 with detailed explanatory notes published in 2024. Most historical international datasets reference ISIC Rev. 4.
- **Eurostat NACE:** Statistical Classification of Economic Activities in the European Community. NACE Rev. 2.1 directly maps from ISIC Rev. 5.
- **North American NAICS:** North American Industry Classification System (2022 revision) used across the US, Canada, and Mexico.
- **National Variants:** UK SIC, Australian/NZ ANZSIC, India NIC.

Hardcoding any single taxonomy violates global architectural flexibility. Conversely, hardcoding industry branches in application code violates Rule 68 (*"No industry is special-cased. No code path, table or test branches on an industry name or code"*).

---

## 2. Decision: Universal Stable Identifier with Attribute-Based Multi-Scheme Crosswalks

We adopt an attribute-based, multi-scheme taxonomy architecture:

1. **Stable Internal Identifier (`industry_id`):** Every industrial activity is assigned an opaque, versioned, immutable identifier format: `ind_<sector_slug>_<level_code>`.
   - Example: `ind_manufacturing_c25` for manufacture of fabricated metal products.
2. **First-Class Scheme Mappings (Rule 69):** Each industry definition carries an array of formal activity codes across standard schemes with explicit versioning:
   ```yaml
   industry_id: "ind_manufacturing_c25"
   title: "Manufacture of fabricated metal products, except machinery and equipment"
   classification_codes:
     - scheme: "ISIC"
       version: "Rev.5"
       code: "C25"
       is_primary: true
     - scheme: "ISIC"
       version: "Rev.4"
       code: "25"
     - scheme: "NACE"
       version: "Rev.2.1"
       code: "C.25"
     - scheme: "NAICS"
       version: "2022"
       code: "332"
   ```
3. **Official Crosswalk Tables:** We incorporate the official UNSD ISIC Rev. 4 to Rev. 5 correspondence tables and Eurostat ISIC/NACE crosswalks as declarative JSON datasets in `core/industry/taxonomy/`.
4. **Multi-Activity Company Profile:** Companies can declare one primary `industry_id` and zero or more secondary `industry_id` records, reflecting modern diversified conglomerates.
5. **Migration of Step 1H Packs:** The four historical packs (`saas`, `hospitality`, `manufacturing`, `clinic`) are mapped into this taxonomy without breaking legacy company references:
   - `saas` $\to$ `ind_information_j62` (Computer programming, consultancy and related activities).
   - `hospitality` $\to$ `ind_accommodation_i55` (Accommodation).
   - `manufacturing` $\to$ `ind_manufacturing_c` (General manufacturing division).
   - `clinic` $\to$ `ind_health_q86` (Human health activities).

---

## 3. License, Boundary & Security Notes
- **Taxonomy Data Licenses:** UN ISIC Rev. 4 / Rev. 5 and Eurostat NACE Rev. 2.1 datasets are published as Open Data (Creative Commons / Open Government licenses). NAICS 2022 is in the US public domain.
- **Zero Hardcoded Branches:** Lint rules and automated CI grep tests guarantee zero code branches on `industry`, `sector`, or classification codes (`grep -rn "if industry\|industry ==\|sector ==\|isic\b.*=="` must return 0 results).
