# ZONATA V4 — CENTRAL AI MODEL GATEWAY & ROUTING
**Multi-Provider Mediation, Token Accounting, Rate Limiting, & Circuit Breaking**

## 1. Gateway Overview
The Model Gateway (`core/model_gateway_v4.py`) provides a single governed conduit for all LLM interactions in ZONATA. No AI Employee, agent process, or background worker communicates with external AI providers directly.

### Supported Providers & Models
- Anthropic Claude (Claude 3.7 Sonnet, Claude 3.5 Haiku)
- OpenAI (GPT-4o, GPT-4o-mini)
- Google Gemini (Gemini 1.5 Pro, Gemini 1.5 Flash)
- Sovereign Local Inference (Llama 3.3 70B, Qwen 2.5 72B via local hardware)

---

## 2. Token Budgeting & Circuit Breaking
- **Pre-Dispatch Checks**: Each model invocation checks employee budget balance and tenant spend limits.
- **Circuit Breakers**: If an external provider experiences 5 consecutive HTTP 5xx errors or elevated latency (>30s), the gateway trips a circuit breaker and automatically fails over to an equivalent alternate model.
- **Cost Accounting**: Every token consumed (input and completion) is logged into `model_usage_telemetry` with exact USD cost calculations.
