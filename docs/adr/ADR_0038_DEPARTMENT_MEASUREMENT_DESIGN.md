# ADR 0038: Department Measurement Design & Benchmarking Framework

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 37 (Verification Pyramid), Rule 63 (Counterfactual Fairness), Rule 66 (Department Workload Performance Metrics)

---

## 1. Context & Problem Statement
To demonstrate production readiness and prove that autonomous department workflows operate accurately, safely, and fairly, ZONATA requires rigorous, reproducible evaluation benchmarks that quantify performance across all 10 domains.

## 2. Decision
1. **Benchmarking Foundation:**
   - Implement evaluation benchmarks inspired by **TheAgentCompany** checkpoint scoring methodology and **GDPval** blinded pairwise comparison.
   - For every department domain (Finance, Sales, Marketing, HR, Operations, Supply Chain, R&D, Legal/Security, Analytics, Cross-Department), 25 deterministic golden evaluation tasks are established (total 250 golden tasks across company-in-a-box).
2. **Deterministic Checkpoint Scoring (TheAgentCompany Style):**
   - Each golden task defines discrete, machine-verifiable checkpoints:
     - Checkpoint 1: State validation before operation.
     - Checkpoint 2: Action authorization and gateway gate compliance.
     - Checkpoint 3: Schema and data contract invariants.
     - Checkpoint 4: Independent re-read verification on secondary and primary records.
     - Checkpoint 5: Audit log entry and ledger balance verification.
   - Overall score is calculated deterministically as percentage of passed checkpoints.
3. **Blinded Pairwise Comparison (GDPval Style):**
   - For complex, generative outputs (e.g., job descriptions, marketing copy, PRD drafts, contract summaries), outputs are evaluated blindly against human baseline drafts or reference standards.
   - Evaluation evaluates: Factual accuracy, Compliance adherence, Brand guideline fidelity, and Counterfactual fairness.
4. **Standard Department Performance Metrics (Rule 66):**
   - **Finance:** AP cycle time (< 4h), Bank reconciliation match rate (> 98%), 3-way match precision (100%).
   - **Sales:** Lead response latency (< 30s), Quote generation accuracy (100%), CRM sync latency (< 1s).
   - **HR:** Counterfactual fairness disparity ratio between 0.95 and 1.05 across demographic test slices; 100% offboarding credential revocation.
   - **Operations & Supply Chain:** BOM explosion correctness (100%), OEE calculation precision (0.01%), Sanctions list check latency (< 50ms).
   - **Legal/Security:** High-impact human gateway approval compliance (100%), Policy mapping coverage (> 95%).
5. **Continuous Regression Testing:**
   - Benchmarks run automatically in CI via `tests/benchmarks/test_department_benchmarks.py`. Any drop in checkpoint score or fairness violation triggers an immediate CI failure.

## 3. Consequences
- Objective, reproducible qualification criteria for all enterprise department functions.
- Prevents regressions in core business logic and regulatory compliance.
