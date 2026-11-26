# ADR 0031: Evolution Experiment Infrastructure, Replay Sandbox, and Holdout Isolation

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Security Arbiter, Repository Owner
- **Governing Rules:** Rule 50 (Off by Default), Rule 51 (Improver Caged), Rule 52 (Held-Out Test Sets), Rule 56 (Evolution Budget)

---

## 1. Context & Problem Statement
Self-improvement processes must be prevented from gaming evaluation metrics, accessing held-out test cases, or consuming runaway computational budgets.

## 2. Decision
1. **Experiment Sandbox:** Candidate prompt mutations, skill refinements, and playbook adaptations execute in an offline sandbox replay environment using recorded task sessions.
2. **Held-Out Test Set Isolation:**
   - Graders, evaluation ground truth, and held-out test sets are located in the **protected set** (`security/protected_paths.yaml`).
   - The proposer and optimizer have zero read or write access to held-out test files or grading rubrics.
3. **Safety Semantic Floor:** Every candidate must pass the baseline safety semantic-floor test set without degradation in addition to achieving performance gains on task accuracy.
4. **Evolution Budget & Rate Limits:**
   - Dedicated evolution budget line item with hard financial ceiling (e.g., $10.00/day max).
   - Maximum 10 proposals per week and maximum 2 concurrent experiments per company.
   - Evolution is automatically suspended during open security incidents.
5. **Staged Rollout & Automatic Rollback:**
   - Staging progression: `SHADOW -> SUPERVISED -> LIMITED_PRODUCTION`.
   - Automatic rollback occurs immediately if error rate, cost, or policy rejection spikes above baseline.

## 3. Consequences
- Prevents Goodhart's Law / reward gaming by AI self-improvers.
- Protects production runtime and financial boundaries.
