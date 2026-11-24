# ADR 0026: Optimizer Stack — DSPy with GEPA Reflective Prompt Evolution

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Security Arbiter, Repository Owner
- **Governing Rules:** Rule 49 (Preservation Contract), Rule 51 (Improver Caged), Rule 56 (Evolution Budget)

---

## 1. Context & Problem Statement
Self-improvement of autonomous agents requires a governed, reproducible mechanism to optimize prompts, system instructions, and tool descriptions when failure clusters or capability gaps are detected. We must choose an optimization engine that improves performance on verified tasks while strictly preventing reward hacking, hallucination, or safety degradation.

## 2. Decision
1. **Adoption of DSPy with GEPA:** We adopt DSPy (MIT License) with GEPA (Genetic Pareto Prompt Optimization / reflective prompt evolution) as the primary self-improvement optimizer behind a typed ZONATA Port (`EvolutionPort` / `OptimizerPort`).
2. **Frozen Model Constraint:** Optimization operates strictly over system prompts, few-shot exemplars, tool usage descriptions, and SOP instructions with **frozen underlying foundation models**. Model fine-tuning and weight updates are not performed in the self-improvement loop.
3. **Out of Scope (Production Ban):** Autonomous code self-rewriting systems (ADAS, Darwin Gödel Machine, and self-compiling AST mutations) are research-grade, non-deterministic, and strictly **OUT OF SCOPE** for production deployment. Platform code changes may only be proposed as standard pull requests under human review.
4. **License & Boundary:** DSPy (MIT) and GEPA (MIT) are permissive open-source libraries. Pinned dependencies must be audited in `OSS_REGISTER.md`.

## 3. Invariants & Guardrails
- The optimizer executes inside an isolated experiment sandbox with zero access to live database credentials or customer data.
- All candidate prompt mutations are evaluated against held-out regression sets that the optimizer cannot access.
- Candidate improvements must beat the incumbent by a statistically significant margin and cannot regress below the safety semantic floor.
