# ADR 0002: Browser Automation Engine Architecture

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3E / 3F — Hands: Browser automation & anti-evasion  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

ZONATA requires an enterprise-grade browser automation engine to execute structured web workflows, DOM extraction, and synthetic verification across headless cloud nodes and host machines. The engine must support multi-tab management, screenshot capturing, accessibility tree traversal, strict domain allowlisting, and zero-leakage secret handling.

Furthermore, Standing Rule 25 strictly mandates: **No circumvention of verification challenges**. The system must never solve, bypass, or evade CAPTCHAs, bot checks, or rate limits.

We evaluated three architectural options:
1. **Playwright (Microsoft)**
2. **Selenium WebDriver**
3. **Puppeteer (Google)**
4. **Direct Chrome DevTools Protocol (CDP)**

---

## 2. Evaluation of Alternatives

### Option 1: Playwright (Chosen)
- **Licence:** Apache-2.0 (Permissive; compliant with Standing Rule 5).
- **Architecture:** Fast, out-of-process WebSocket CDP communication with bundled browser binaries (Chromium, Firefox, WebKit).
- **Capabilities:** Native async Python API, deep accessibility tree (`accessibility.snapshot()`), deterministic network request interception, download/upload stream handling, and DOM event listeners.
- **Security:** Clean isolation per browser context (cookies, storage, cache completely isolated per tenant session).
- **Environment Handling:** On resource-constrained environments (e.g., ARM64 Android / Termux), Playwright driver can run in stub/sandbox mode (`SandboxBrowserProvider`) against local fixture sites, with full containerized execution validated authoritatively in GitHub Actions CI.

### Option 2: Selenium WebDriver
- **Licence:** Apache-2.0.
- **Rejected Reasons:** Heavier architecture requiring separate `chromedriver` / `geckodriver` processes, slower execution speed, brittle element wait states, and inferior accessibility tree inspection compared to Playwright.

### Option 3: Puppeteer
- **Licence:** Apache-2.0.
- **Rejected Reasons:** Primarily Node.js native. Python bindings (`pyppeteer`) are unmaintained community ports with stale dependencies and lack parity with modern CDP features.

### Option 4: Direct CDP Client
- **Rejected Reasons:** Extremely high engineering and maintenance overhead; fragile against Chromium version shifts; lacks multi-browser support (Firefox/WebKit).

---

## 3. Decision

We choose **Playwright** as the lead browser engine, wrapped behind `core.ports.browser.BrowserPort`.

### Implementation Safeguards:
1. **Rule 24 (Secret Zero-Exposure):** Passwords and credentials never reach the DOM snapshot, prompt, or log in plaintext. Origin-bound injection occurs directly via isolated Playwright evaluate hooks.
2. **Rule 25 (No Evasion / Solvers):** Explicit deny-list against `playwright-stealth`, undetected-chromedriver, CAPTCHA solver plugins, and proxy rotators. Detection of a challenge (Cloudflare Turnstile, reCAPTCHA, etc.) raises `VerificationChallengeDetectedException` and transitions task to `BLOCKED`.
3. **Rule 26 (Untrusted Content):** All DOM text and extracted attributes are tagged as `UNTRUSTED_EXTERNAL_DATA`. Prompt injection inside web pages is neutralized before reaching model contexts.
4. **Deterministic Testing:** In offline or Termux environments, `BrowserPort` gracefully resolves to `SandboxBrowserProvider` or `NotConfiguredProvider` while reporting accurate capability status.
