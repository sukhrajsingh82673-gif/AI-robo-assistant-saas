# ADR 0045: Pre-Registered Benchmark Statistics, Blinding, and Isolated Vault Architecture

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 41 (Zero Plaintext Secrets), Rule 74 (Sealed Benchmarks), Rule 75 (Human Participant Protection)

---

## 1. Context & Problem Statement
Marketing claims regarding AI capability ("superhuman", "10x faster", "99% parity") frequently suffer from severe scientific defects:
- Post-hoc hypothesis formulation (p-hacking and Texas sharpshooter fallacies).
- Test-set contamination, where benchmark tasks bleed into agent training, memory, or system prompts.
- Unblinded evaluations where human evaluators know which deliverable was produced by AI.
- Lack of statistical power analyses and multiple-comparison corrections.
- Vague claims made without confidence intervals or clear task-level breakdowns.

To establish genuine trust, ZONATA requires a sealed, pre-registered, double-blind benchmark program governed by Rule 74 and Rule 75.

---

## 2. Decision: Pre-Registration Ledgers, Blinded Double-Scoring & An Isolated Vault Schema

We establish an immutable benchmark evaluation system:

```
┌────────────────────────────────────────────────────────┐
│ 1. Pre-Registration Protocol                           │
│ - Hypotheses, metrics, power calculations              │
│ - Sealed in Evidence Ledger (SHA-256 Digest)           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. Isolated Benchmark Vault (Schema: `benchmarks`)     │
│ - Encrypted test tasks, references, grader keys        │
│ - Readable ONLY by `benchmark_runner` principal        │
│ - Strict DENY for learning, prompts, evolution, agents │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. Baseline Recorder & Double-Blind Grader Interface   │
│ - Human baselines recorded with consent & timers       │
│ - Deliverables anonymized: Order randomized (A vs B)   │
│ - >= 3 Graders per deliverable with agreement metrics  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. Claims Registry (`benchmark_claims`)                │
│ - Only statistically significant tasks earn claims     │
│ - Claims expire on model, prompt, or spec changes      │
└────────────────────────────────────────────────────────┘
```

1. **Pre-Registration Evidence Seal (Rule 74):**
   - Prior to running any benchmark suite, a formal pre-registration document must be compiled containing:
     - Specific statistical hypotheses (superiority or non-inferiority margins $\delta$).
     - Sample size determination based on statistical power analysis ($\beta \ge 0.80$, $\alpha = 0.05$).
     - Multiple comparison correction formula (Benjamini-Hochberg False Discovery Rate or Bonferroni).
     - SHA-256 hash of the frozen analysis evaluation script.
   - This document is sealed in the cryptographic evidence ledger. The benchmark execution runner **refuses to run** if the pre-registration seal is missing or was created after the test timestamps.
2. **Cryptographically Isolated Vault Schema (`benchmarks`):**
   - All benchmark task descriptions, reference truth datasets, and grader answer keys reside in a dedicated PostgreSQL schema (`benchmarks`).
   - PostgreSQL RLS and role permissions restrict SELECT/INSERT to the dedicated `benchmark_runner` principal.
   - The schema is strictly invisible and inaccessible to all runtime agents, LLM tool dispatchers, self-improving prompt optimizers, and Antigravity/OpenCode development processes.
3. **Automated Contamination Detector:**
   - Before executing a benchmark, the vault runs an automated n-gram and cosine embedding similarity scan between benchmark task texts and all production prompts, playbooks, tools, and documentation.
   - Any detected overlap exceeding the threshold ($>0.65$ similarity) immediately flags the task as **CONTAMINATED**, revokes its benchmark status, and logs a defect.
4. **Double-Blind Grader Interface & Inter-Rater Reliability:**
   - Evaluators review pairs of deliverables (Human vs AI) with randomly assigned identities (A vs B).
   - Each pair is evaluated by at least three independent qualified domain professionals.
   - The platform calculates inter-rater agreement statistics (**Fleiss' Kappa** for categorical classifications and **Krippendorff's Alpha** for continuous rubrics). Evaluations with unresolvable inter-rater discordance are routed to an expert panel for adjudication.
5. **Claims Registry (`benchmark_claims`):**
   - Statements such as "outperforms" or "equivalent to" can only be rendered in customer materials if backed by an active, unexpired row in `benchmark_claims`.
   - Claims automatically expire and void whenever the underlying model ID, prompt hash, or system specification changes.

---

## 3. License, Boundary & Security Notes
- Statistical calculations utilize standard scientific libraries (`scipy`, `statsmodels`, BSD-3-Clause).
- Participant privacy (Rule 75) is guaranteed: human participants are pseudonymized via CSPRNG UUIDs; zero personal identifying information (PII) is stored in the benchmark dataset.
