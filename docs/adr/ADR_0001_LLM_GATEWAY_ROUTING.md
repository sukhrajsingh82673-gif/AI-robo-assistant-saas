# ADR 0001: LLM Gateway Routing & Provider Client Architecture

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 2B — Model gateway: tiers, budgets, tracing  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

ZONATA requires an enterprise-grade `LLMGateway` supporting multiple model tiers (`PLANNER`, `WORKER`, `FAST`, `VISION`, `EMBEDDING`), structured fallback chains, per-tenant policy enforcement, reserve-then-settle hierarchical budgeting in integer micro-units, circuit breakers, and deterministic test stubs.

We evaluated two architectural strategies:
1. **Adopting an external unified proxy library (e.g., LiteLLM)**
2. **Implementing thin, sovereign adapter clients over standard provider REST endpoints**

---

## 2. Evaluation of Alternatives

### Option 1: External Proxy Library (LiteLLM)
- **Licensing Concerns:** While core LiteLLM is MIT, parts of the codebase in the `enterprise/` directory carry commercial/proprietary license terms. Standing Rule 5 requires legal boundary isolation for any non-permissive code.
- **Dependency Surface:** Heavy dependency footprint (~50+ transitive dependencies including pydantic v2, fastapi, cryptography, httpx, etc.). On ARM64 Android / Termux, complex C/Rust extensions (such as `pydantic-core` and compiled tokenizer wheels) cause build failures on non-standard target triples (`aarch64-unknown-linux-android`).
- **Security & Supply Chain:** High release cadence (multiple releases per week) and historical CVEs in upstream parser libraries increase supply chain attack surface.

### Option 2: Thin Sovereign Adapters over Official Provider REST APIs (Chosen)
- **Zero Third-Party Model Dependencies:** Direct standard HTTP/REST adapters using standard library `urllib` / lightweight HTTP requests over:
  - Anthropic Messages API (`/v1/messages`)
  - OpenAI Chat Completions API (`/v1/chat/completions`)
  - Google Gemini API (`/v1beta/models/...:generateContent`)
  - OpenAI-Compatible Generic Endpoints (vLLM, Ollama, DeepSeek, Local / Hosted)
- **Deterministic Testability:** Clean `SandboxLLMProvider` integrated directly into the `Port` framework (`core/ports/base.py`) providing instantaneous, repeatable, zero-cost unit and contract testing.
- **Strict Budget & Concurrency Control:** Native reserve-then-settle semantics using database row-level locking (`SELECT ... FOR UPDATE`), preventing overspend under heavy concurrency.
- **Full Portability:** 100% pure-Python with zero compiled native binary dependencies, ensuring identical behavior across ARM64 Android (Termux) and Linux/x86_64 CI containers.

---

## 3. Decision

We choose **Option 2: Thin Sovereign Adapters**. 

The gateway will implement:
1. `core.ports.llm.LLMGatewayPort` conforming to the ZONATA Port pattern (`Port` → `RealProvider` → `NotConfiguredProvider` → `SandboxProvider`).
2. Configurable model tier mapping (`PLANNER`, `WORKER`, `FAST`, `VISION`, `EMBEDDING`) via environment variables and database settings, never hardcoded in application logic.
3. Strict circuit breakers, jittered retries, and automated fallback upon provider outage.
4. Pydantic-based output schema validation with one automatic self-correction retry before failing closed.
5. Multi-level hierarchical budget enforcement (tenant → company → department → position/employee → mission → task) in integer micro-USD.
