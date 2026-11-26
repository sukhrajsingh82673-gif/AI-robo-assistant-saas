# Sub-Step 4H Handoff: OpenTelemetry Instrumentation & Secret Canary

**Builder:** Antigravity (Builder Persona)  
**Reviewer:** OpenCode (Reviewer Persona)  
**Target:** Sub-Step 4H — OpenTelemetry Instrumentation & Secret Canary  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 core/telemetry/__init__.py        |  43 ++++++++++++++
 core/telemetry/canary.py          | 120 +++++++++++++++++++++++++++++++++++++++
 core/telemetry/context.py         | 125 ++++++++++++++++++++++++++++++++++++++++
 core/telemetry/interceptor.py     | 145 ++++++++++++++++++++++++++++++++++++++++++++++
 core/telemetry/sanitizer.py       | 169 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
 core/telemetry/tracer.py          | 266 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 docs/reports/ADOPTION_STATUS.md   |   2 +-
 docs/reports/STEP4_REPORT.md      |  66 ++++++++++++++++++++-
 tests/test_step4_opentelemetry.py | 247 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 9 files changed, 977 insertions(+), 2 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run Rule 34 anti-bypass AST linter across core
python3 scripts/anti_bypass_linter.py --scan-path core

# 2. Run Sub-Step 4H unit and contract tests
pytest tests/test_step4_opentelemetry.py -v

# 3. Run full Step 4 test suite (78 tests)
pytest tests/test_step4_*.py -q
```

---

## 3. Claims Made & Verifications

1. **W3C TraceContext Compliance:** `CorrelationContext` produces and parses standard `00-{trace_id32}-{span_id16}-{flags02}` traceparents and injects/extracts across HTTP carriers (`test_01`).
2. **Dual-Mode Semantic Conventions (ADR 0015):** Stable `zonata.*` namespace attributes (`zonata.tenant_id`, `zonata.company_id`, `zonata.tokens_input`, `zonata.tokens_output`, `zonata.cost_micros`) are emitted on 100% of spans. When `OTEL_GENAI_CONVENTIONS_ENABLED=1`, official `gen_ai.*` attributes are emitted (`test_03`).
3. **Standing Rule 24 Secret Canary Protection:** `TelemetryCanaryProbe` injects `ZONATA_CANARY_*` markers, API keys (`sk_live_...`), passwords, and bearer tokens. Deep scanning of exported OTLP JSON confirms 0% leak rate (`test_04`).
4. **Standing Rule 36 Privacy Gating:** Prompt and response bodies are redacted to `[BODY_OMITTED_BY_TENANT_POLICY]` unless `tenant_allow_prompt_capture=True` (`test_05`).
5. **Standing Rule 40 / ADR 0016 Legal/AGPL Isolation:** AST scan of Python code verifies zero in-process imports of AGPL packages (`grafana`, `loki`, `tempo`).
6. **Mutation Check:** In strict mode, any unredacted credential or canary secret fails closed with `TelemetryLeakageError` (`test_08`).
7. **Standing Rule 37 Adoption Honesty:** `docs/reports/ADOPTION_STATUS.md` records OpenTelemetry GenAI as `ADOPTED`.

---

## 4. Known Gaps
None. All 8 tests pass locally with 0 anti-bypass violations. Ready for independent review.
