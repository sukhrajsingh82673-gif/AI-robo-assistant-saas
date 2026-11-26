# ADR 0046: External Benchmark Calibration Harnesses (TheAgentCompany, GDPval, Remote Labor Index)

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 74 (Sealed Benchmarks), Rule 75 (Human Participant Protection)

---

## 1. Context & Problem Statement
Internal benchmarks can suffer from perceived bias or narrowness. To place ZONATA's capabilities in broader scientific and industry context, external public benchmarks provide valuable calibration.
Key public benchmarks include:
- **TheAgentCompany:** Self-hosted simulated corporate environment evaluating autonomous agents across multi-step software, financial, and operational tasks against deterministic checkpoints (published baselines ~24–30% task completion).
- **GDPval:** Curated gold subset of 220 real-world corporate tasks spanning 44 knowledge-worker occupations evaluated by blinded expert pairwise preference.
- **Remote Labor Index:** Real freelance and consulting tasks across 23 domains evaluating autonomous end-to-end task fulfillment.

However, external benchmarks test broad, unconstrained agent behavior and do not reflect specific tenant security boundaries, regulatory compliance constraints, or localized ERP environments. Running them without strict controls could lead to uncontrolled token expenditures or misleading marketing claims.

---

## 2. Decision: Sandboxed Calibration Adapters with Spend Caps and Mandatory Caveats

We implement external benchmark adapters under strict governance:

```
[ External Benchmark Suite ]
           │
           ▼
┌───────────────────────────────────────────────┐
│ External Calibration Adapter                  │
│ - TheAgentCompany Adapter                     │
│ - GDPval Gold Harness                         │
│ - Remote Labor Index Harness                  │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│ Runtime Governance & Guardrails               │
│ - Spend Cap Enforcer (Hard USD Limit)         │
│ - Model, Prompt & Spec Hash Capture           │
│ - Mandatory Context Caveat Injector           │
└───────────────────────────────────────────────┘
```

1. **Standardized Calibration Adapters (`core/benchmarks/external/`):**
   - `TheAgentCompanyAdapter`: Connects to self-hosted Docker/container mock corporate environment, executing checkpoint evaluations (CP1 to CP5) via Step 4 runtime ports.
   - `GDPvalAdapter`: Ingests the 220 gold tasks, runs blinded pairwise comparisons, and scores against public reference rubrics.
   - `RemoteLaborIndexAdapter`: Executes permitted subset tasks in isolated mock environments.
2. **Hard Spend Cap Governance:**
   - Every external benchmark run requires an explicit spend cap token.
   - The token budget enforcer tracks real-time model token consumption and aborts execution immediately if cumulative spend reaches the configured ceiling.
3. **Spec, Prompt, and Model Cryptographic Provenance:**
   - Every external calibration score records:
     - Exact foundation model identifier and provider snapshot (e.g., `claude-3-7-sonnet-20250219`, `gemini-1.5-pro`).
     - SHA-256 hash of system prompts, tool schemas, and agent configuration.
     - Timestamp and execution duration.
4. **Mandatory Context Disclaimer (Rule 74):**
   - Every generated calibration report and leaderboard entry must prominently display the mandatory scientific caveat:
     > *"External calibration benchmarks provide comparative context across generic tasks and do not constitute empirical evidence of performance, compliance, or safety within any specific enterprise tenant, industry sector, or statutory legal jurisdiction."*

---

## 3. License, Boundary & Security Notes
- Calibration harnesses operate against mock environments or recorded fixture sets; zero production tenant data is ever exposed to external benchmark environments.
- Open-source benchmark tool licenses are audited: TheAgentCompany and GDPval are used under their published academic research and open-source terms.
