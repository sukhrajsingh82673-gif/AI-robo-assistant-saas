# ADR 0015: OpenTelemetry Conventions, Stable Attributes & Secret Canary

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4H — Distributed tracing, spans, and telemetry security  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
ZONATA requires unified distributed tracing spanning Temporal workflows, LangGraph nodes, Google ADK teams, MCP tool calls, and LLMGateway model invocations.

Standing Rule 24 and Rule 36 dictate:
- No plaintext credentials, passwords, or customer PII in spans, attributes, or logs.
- Secret canary injection tests must verify zero plaintext leakage across all telemetry.
- GenAI semantic conventions are currently evolving upstream.

## 2. Upstream Standards & Licensing
- **SDK:** Official `opentelemetry-api` and `opentelemetry-sdk` Python packages (Apache-2.0).
- **GenAI Semantic Conventions:** As of mid-2026, `gen_ai.*` semantic conventions remain at *Development* status in OpenTelemetry.

## 3. Decision & Architecture
1. **Stable Core Attributes:** ZONATA will always emit stable, forward-compatible `zonata.*` namespace attributes across all spans:
   - `zonata.tenant_id`, `zonata.company_id`, `zonata.user_id`
   - `zonata.run_id`, `zonata.step_id`, `zonata.trace_id`
   - `zonata.action_class`, `zonata.authority_profile`
   - `zonata.tokens_input`, `zonata.tokens_output`, `zonata.cost_micros`
2. **GenAI Convention Feature Flag:** `gen_ai.*` attributes (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.*`) are emitted behind an explicit configuration flag (`OTEL_GENAI_CONVENTIONS_ENABLED=1`).
3. **Attribute Allow-List & Secret Redaction:** All span attributes pass through a strict regex and key allow-list. Prompt and response text bodies are omitted by default, captured only if tenant policy explicitly permits.
4. **Automated Canary Tests:** CI executes automated secret canary scans across serialized trace spans and collector outputs to prove zero plaintext exposure.
