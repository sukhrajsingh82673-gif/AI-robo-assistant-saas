# ADR 0008: Research Search Provider Architecture

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3H — Hands: Research, web queries, and knowledge retrieval  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

ZONATA agents require web search capabilities to conduct market research, fact-check claims, retrieve public documentation, and synthesize business intelligence.

The search capability must adhere to:
- **Rule 25:** No circumvention of verification challenges, CAPTCHAs, or paywalls.
- **Rule 26:** Untrusted web results must be handled as raw data, never instructions.
- **Port Architecture:** Seamless switching between self-hosted search, commercial APIs, and deterministic offline stubs.

---

## 2. Evaluation of Alternatives

### Option 1: Direct HTML Web Scraping (Google / DuckDuckGo Scraping)
- **Rejected Reasons:** Brittle DOM changes; triggers IP rate-limiting, Cloudflare challenges, and CAPTCHAs. Violates Rule 25 (attempts to bypass anti-bot challenges).

### Option 2: Commercial Search APIs Exclusively (Brave Search / Tavily / SerpAPI)
- **Advantages:** Stable, structured JSON results, official terms of service.
- **Limitations:** Creates a mandatory external cloud dependency and recurring query costs for self-hosted sovereign installations.

### Option 3: Sovereign Multi-Provider Strategy (Chosen)
- **Architecture:** Provide a unified `SearchPort` implementing three provider adapters:
  1. **Self-Hosted Meta-Search: SearXNG (AGPLv3)**
     - Operated strictly as an external independent network service per Standing Rule 5 (no copyleft library linked in Python application; accessed strictly via clean HTTP JSON REST API).
     - Aggregates multiple public search engines with zero tracking.
  2. **Managed API Provider: Brave Search API / Tavily / SerpAPI**
     - Configured via tenant vault secrets (`secret://search_api_key`).
     - Fast, highly reliable, structured search results.
  3. **Deterministic Sandbox Provider: `SandboxSearchProvider`**
     - Built-in fixture search results for zero-network unit tests, offline development, and CI regression testing.

---

## 3. Decision

We choose **Option 3: Sovereign Multi-Provider Architecture behind `SearchPort`**.

### Safety Controls:
1. **Rule 26 (Untrusted Data Sanitization):** Search snippet text and page extracts are strictly tagged as `UNTRUSTED_EXTERNAL_DATA`, enclosed in XML data delimiters (`<untrusted_web_data>`), and scrubbed of prompt-injection patterns ("ignore previous instructions", "system:", etc.).
2. **Rate Limiting & Cost Budgets (Rule 20):** Every search query is budgeted before dispatch, with hard queries-per-minute caps per tenant.
3. **Challenge Handling (Rule 25):** If a target site returns HTTP 403, Cloudflare challenge, or CAPTCHA, search engine marks the source `CHALLENGE_BLOCKED` and proceeds without scraping.
