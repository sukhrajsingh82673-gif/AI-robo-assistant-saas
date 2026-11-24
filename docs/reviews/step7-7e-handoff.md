# Sub-Step 7E Handoff Dossier: Marketing & Brand Depth

**Date:** 2026-11-24  
**Author:** Antigravity Architect  
**Reviewer:** OpenCode Arbiter  
**Scope:** Brand guidelines as structured data, Rule 44 anti-superhuman enforcement, content claim verification, campaign lifecycle with budget commitment, first-party multi-touch attribution, and MarketingPort adapters.

---

## 1. Files Changed & Added (`git diff --stat`)
```
core/marketing/__init__.py           |   1 +
core/marketing/attribution.py        | 104 +++++++++++++++++++
core/marketing/brand.py              |  72 +++++++++++++
core/marketing/campaign.py           |  68 ++++++++++++
core/marketing/claim_verifier.py     |  88 ++++++++++++++++
core/marketing/marketing_port.py     |  72 +++++++++++++
docs/reports/STEP7_REPORT.md         |  32 ++++++
docs/reviews/step7-7e-handoff.md     |  38 +++++++
docs/reviews/step7-7e-review.md      |  34 +++++++
packs/brand/brand_guidelines.json    |  36 +++++++
tests/test_step7e_marketing.py       | 185 +++++++++++++++++++++++++++++++++
11 files changed, 730 insertions(+)
```

## 2. Commands to Re-run
```bash
pytest -v tests/test_step7e_marketing.py
pytest -q tests/test_step7_preflight.py tests/test_preservation_step7.py tests/test_step7b_platform.py tests/test_step7c_finance.py tests/test_step7d_sales_support.py tests/test_step7e_marketing.py
```

## 3. Claims & Invariants Verified
1. **Brand Guidelines Schema:** Structured brand voice rules reject forbidden superlatives and ungrounded marketing hype.
2. **Rule 44 Compliance:** Content scanner strictly detects and blocks 'better than human' or human replacement assertions.
3. **Fact & Benchmark Grounding:** Content claim verifier validates statistical statements against ground truth citations.
4. **Governed Campaign Lifecycle:** Enforces brand approval, legal gateway signature, and department budget spend commitment before scheduling.
5. **Privacy-Safe Multi-Touch Attribution:** Calculates First-Touch, Last-Touch, Linear, Time-Decay, and U-Shaped attribution without third-party cookies.
6. **MarketingPort Platform Adapters:** Google, Meta, and LinkedIn adapters operate behind dynamic authentication leasing (Rule 41).

## 4. Known Gaps / Next Sub-Step
- Sub-Step 7F will implement Human Resources & Workforce Operations (counterfactual fairness, deterministic payroll, offboarding checklist).
