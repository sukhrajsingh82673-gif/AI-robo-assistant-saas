# ADR 0041: Enterprise Localisation Stack (Unicode CLDR, ICU, Babel, and Translation Workflows)

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 70 (Standards as Data), Rule 73 (Global by Construction)

---

## 1. Context & Problem Statement
Prior to Step 8, UI strings were predominantly hardcoded English, with partial translation limited to high-level menus and greetings. Real enterprise operations span global subsidiaries requiring:
- Precise locale-aware formatting of numbers, currencies, dates, and times.
- Multilingual interface localization across Western, Eastern, and Right-to-Left (RTL) scripts (e.g., Arabic, Hebrew).
- Strict separation between presentation-layer formatting and internal machine data representations (Rule 73: *"Money is integer minor units with ISO 4217; time zones come from IANA data; locale formatting comes from CLDR and appears only at the presentation layer"*).
- Reliable translation pipelines separating human-certified legal/compliance strings from draft translations.

---

## 2. Decision: Unicode CLDR / ICU Engine, Python Babel, and Weblate Boundary

We adopt the industry standard Unicode localization framework:

1. **Standard CLDR Data:**
   - We utilize **Unicode CLDR (Common Locale Data Repository)** version 49 (with ICU 79), licensed under the Unicode-3.0 License.
   - Core localization functions (date parsing/formatting, number groupings, currency symbols, collation, plural rules) are implemented via Python `babel` (BSD-3-Clause) and standardized ICU bindings.
2. **Strict Layer Separation (Rule 73):**
   - **Storage & Logic Layer:** Zero locale dependencies. Currency is always stored as minor integer units (e.g., `10050` cents = $100.50) with an ISO 4217 alpha code (e.g., `USD`, `EUR`, `INR`). Timestamps are stored as UTC UNIX epochs or ISO 8601 strings with timezone offsets.
   - **Presentation Layer:** All user-facing rendering passes through `LocalizationService.format_currency(amount_minor, currency_code, locale)` or `format_datetime(dt, locale, timezone)`.
3. **Translation Management & Catalog Pipeline:**
   - Translations are maintained as standard GNU gettext PO/MO catalogs organized per locale in `locales/<lang>_<country>/LC_MESSAGES/`.
   - **Weblate Integration (Copyleft Isolation):** Weblate is licensed under GPL-3.0. In compliance with Rule 58 / Rule 60, Weblate is utilized strictly as an external, unmodified network service communicating via REST APIs or git sync; zero GPL code is embedded or linked into the core platform.
4. **Machine-Translation Guardrails:**
   - Automated machine-translation drafts (via neural translation APIs) are permitted during authoring but must be tagged with `translation_status: "UNVERIFIED_DRAFT"`.
   - Any statutory, contractual, or compliance text (e.g., invoice footers, terms of service, tax disclosures) requires signature by a certified translator or legal professional before promotion to `VERIFIED_LEGAL`.
5. **Right-to-Left (RTL) & Bidirectional Text:**
   - Presentation layer templates incorporate `dir="rtl"` and Unicode Bidi markers for locales `ar_*` and `he_*`.

---

## 3. License, Boundary & Security Notes
- **Unicode-3.0 License:** Permissive open-source license compatible with commercial distribution.
- **Babel (BSD-3-Clause):** Fully compliant with our open-source software register (`docs/reports/OSS_REGISTER.md`).
- **Weblate Boundary:** Documented as `BOUNDARY — legal review`. Kept strictly on the network boundary.
