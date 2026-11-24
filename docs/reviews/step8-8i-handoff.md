# Sub-Step 8I Handoff: Step 8 Final Qualification & Scenario

## 1. Files Changed
```text
 scripts/step8_scenario.py
 tests/test_step8i_final_scenario.py
 docs/reports/STEP8_REPORT.md
```

## 2. Commands to Re-run
```bash
python scripts/step8_scenario.py
PYTHONPATH=. pytest -v tests/test_step8i_final_scenario.py tests/test_preservation_step8.py
```

## 3. Claims & Evidence
1. **Multi-Sector Synthetic Scenario:** 3 corporate groups (Apex Industrial C28/DE, SilkRoute Holdings G47/IN/US, Al-Sharq Transport H52/SA/BE) simulated across 30 days of operations (`tests/test_step8i_final_scenario.py`).
2. **Deep E-Invoicing Regimes:** Germany ZUGFeRD 2.2 CII XML, India IRP GST JSON with IRN hash, and Peppol BIS 3.0 UBL XML verified.
3. **Multi-Lingual & Arabic RTL:** Verified RTL metadata, alignment, and bi-directional text marks for Arabic alongside German and Indian CLDR presentation.
4. **Multi-Company Group Consolidation:** IAS 21 multi-currency balance translation with CTA equity plug and two-sided intercompany matching ($debits - credits = 0$).
5. **Adversarial Boundary Invariant Probes:** 7/7 adversarial boundary cases blocked:
   - Clinical prescription refusal
   - Consumer credit scoring advice refusal
   - Unverified statutory tax rate escalation
   - Unreviewed legal machine translation refusal
   - Cross-region cellular data transfer refusal without lawful basis
   - Concurrency burst throttling
   - Missing buyer procurement evidence rejection
6. **Scenario Seal:** Cryptographic SHA-256 scenario digest generated (`24092f0c095b2a74ff7505e049c80c99558ac2e6a8a515467cad21164dc60174`).
7. **Preservation Invariant (Rule 67):** 100% hash match on all 2,137 Step 1–7 baseline files (`tests/test_preservation_step8.py`).
8. **Industry Neutrality (Rule 68):** Zero `if industry == ...` code branches (`tests/test_step8a_preflight.py::test_06`).

## 4. Known Gaps
- None. Complete qualification across all sub-steps 8A through 8I.
