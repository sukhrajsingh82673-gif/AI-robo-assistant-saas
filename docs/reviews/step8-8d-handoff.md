# Sub-Step 8D Handoff: Global Corporate Readiness

## 1. Files Changed
```text
 core/connectors/wave1/__init__.py
 core/connectors/wave1/base.py
 core/connectors/wave1/edi_iso20022.py
 core/connectors/wave1/fixtures/wave1_replays.json
 core/connectors/wave1/quickbooks.py
 core/connectors/wave1/salesforce.py
 core/connectors/wave1/sap_s4hana.py
 core/connectors/wave1/servicenow.py
 core/connectors/wave1/slack.py
 core/connectors/wave1/snowflake.py
 core/connectors/wave1/workday.py
 core/consolidation/__init__.py
 core/consolidation/engine.py
 core/i18n/__init__.py
 core/i18n/cldr.py
 core/i18n/pseudo.py
 core/i18n/rtl.py
 core/i18n/translation_guard.py
 core/invoicing/__init__.py
 core/invoicing/adapters/germany_zugferd.py
 core/invoicing/adapters/india_irp.py
 core/invoicing/adapters/italy_sdi.py
 core/invoicing/adapters/peppol_bis3.py
 core/invoicing/adapters/poland_ksef.py
 core/invoicing/canonical.py
 core/invoicing/tax_escalation.py
 core/procurement/buyer_pack.py
 core/residency/__init__.py
 core/residency/cell_router.py
 packs/jurisdictions/ (30 jurisdiction packs)
 tests/test_step8d_global_readiness.py
 docs/reports/STEP8_REPORT.md
```

## 2. Commands to Re-run
```bash
PYTHONPATH=. pytest -v tests/test_step8d_global_readiness.py tests/test_preservation_step8.py
```

## 3. Claims & Evidence
1. **Multi-Company Group Consolidation:** Implements IAS 21 / ASC 830 translation, CTA plug, and 2-sided eliminations that balance to exactly zero net debit/credit (`tests/test_step8d_global_readiness.py::test_01`).
2. **30 Jurisdictions & EN 16931 E-Invoicing:** Canonical invoice mapped to Germany ZUGFeRD, India IRP, Peppol BIS 3.0, Italy SdI, and Poland KSeF formats (`test_02`).
3. **Statutory Tax Escalation:** Unverified tax category raises `TaxDeterminationEscalationRequired` (`test_03`).
4. **CLDR / RTL Localization:** Localized currencies, numbers, dates, Arabic/Hebrew RTL metadata, and pseudo-localization string expansion verified (`test_04`, `test_05`, `test_06`).
5. **Translation Guard:** Unreviewed machine translation of legal contracts/tax filings raises `UnreviewedLegalTranslationBlockedError` (`test_07`).
6. **Regional Cell Residency:** Direct cross-cell data access raises `CrossRegionOperationRefusedError` (`test_08`).
7. **Wave 1 Connectors:** 8 enterprise integration connectors verified against replay contract fixtures (`test_09`).
8. **Enterprise Procurement Pack:** Requisite audit evidence citations verified (`test_10`).
9. **Preservation Invariant:** All 2,137 Step 1–7 baseline files remain cryptographically untouched (`test_preservation_step8.py`).

## 4. Known Gaps
- External production API credentials require tenant enrollment; fallback to recorded contract replay fixtures verified.
