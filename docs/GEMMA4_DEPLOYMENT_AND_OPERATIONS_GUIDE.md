# Google Gemma 4 Deployment & Operations Guide
## ZONATA / URA Universal AI Company Operating System

---

## 1. Deployment Modes

The Gemma 4 Cognitive Integration supports three distinct deployment architectures (Section 27):

### Mode 1: LOCAL (Google AI Edge / On-Premise Sovereign)
- **Use Case**: Restricted / Highly Restricted tenant data; air-gapped deployments; edge gateways.
- **Data Flow**: Prompts and organizational state remain 100% on local infrastructure. Zero data egress to public cloud providers.
- **Runtimes**: Google AI Edge / MediaPipe GenAI / Ollama / vLLM local runtime.
- **Hardware Profile**:
  - `gemma-4-31b-it`: Requires 18.5 GB VRAM (quantized 4-bit/8-bit fits on RTX 4090 or Apple Silicon 32GB/64GB).
  - `gemma-4-26b-a4b-it`: Requires 7.2 GB VRAM (runs comfortably on edge GPUs and high-end laptops).

### Mode 2: REMOTE (Google API / Interactions API)
- **Use Case**: Cloud-native SaaS deployments; high-concurrency environments.
- **Data Flow**: Encrypted TLS 1.3 dispatch to Google Gemini / Gemma endpoints.
- **Features**: Utilizes Google's stateful Conversations and Tool Orchestration endpoints.

### Mode 3: HYBRID (Default Production Mode)
- **Use Case**: Enterprise production SaaS deployments.
- **Data Flow**:
  1. Input is pre-screened locally by `PromptInjectionDefense` and `ModelDataFirewall` (DLP).
  2. PII / Tenant secrets are redacted locally before any outbound request.
  3. Sanitized inference executes on remote Gemma 4 endpoints.
  4. Response is structured and bound to cryptographic evidence locally before action dispatch.

---

## 2. API Security Architecture (Section 28)

1. **Server-Side Model Gateway**: Client browsers and mobile clients never receive raw model API keys.
2. **Pre-Dispatch DLP Inspection**: Sensitive tenant data is scrubbed using regex and entity recognizers.
3. **Audit Logging**: Every model call records `prompt_tokens`, `completion_tokens`, `latency_ms`, and `cost_usd`.

---

## 3. Operations Runbook

### Starting the Server
```bash
# Production entrypoint
python3 api_server.py 8080
```

### Verifying Service Vitals
```bash
# Server Health
curl -s http://localhost:8080/health

# Gemma 4 Cognitive Status
curl -s http://localhost:8080/api/v8/gemma/status

# Benchmark Results
curl -s http://localhost:8080/api/v8/gemma/benchmark
```

### Executing Executive Directives via API
```bash
curl -s -X POST http://localhost:8080/api/v8/chat \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tnt_primary" \
  -H "X-Company-ID: comp_primary" \
  -d '{"message": "Increase hotel bookings by 20% this month."}'
```
