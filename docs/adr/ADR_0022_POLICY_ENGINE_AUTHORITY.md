# ADR 0022: Policy Engine Authority & Tenant Policy Architecture

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 33 (Frameworks are replaceable adapters), Rule 2C (Single Sovereign ActionGateway Authority)

---

## 1. Context and Problem Statement
ZONATA established `ActionGateway` (`core/action_gateway.py`) in Step 2 as the single sovereign authority for evaluating actions, autonomy tiers, budgets, approvals, and kill switches. As the platform adds support for tenant-authored custom business policies, external policy engines (Open Policy Agent / OPA, AWS Cedar, and Keycloak AuthZEN) must be evaluated without compromising the sovereign authority of `ActionGateway`.

## 2. Alternatives Considered

| Policy Solution | License | Execution Model | Decision |
| :--- | :--- | :--- | :--- |
| **ZONATA ActionGateway (Native Python AST)** | Proprietary (ZONATA Core) | In-process, microsecond latency, direct binding to budget guards and evidence ledger. | **MAINTAIN AS SOVEREIGN AUTHORITY:** Cannot be delegated away or replaced by any external framework. |
| **Open Policy Agent (OPA / Rego)** | Apache-2.0 | Declarative policy, WebAssembly compilation, widespread adoption. | **ADOPTED AS OPTIONAL TENANT PLUGIN:** Used strictly as an auxiliary filter for tenant-custom rules. |
| **Cedar Policy Engine (AWS)** | Apache-2.0 | Formally verified, Rust-based, designed for authorization. | **VIABLE ALTERNATIVE:** Strong ergonomics, but adds Rust compilation boundary in Python/Termux environments. |
| **Keycloak AuthZEN (Experimental)** | Apache-2.0 | OpenID Foundation emerging standard for authorization decision APIs. | **EXPERIMENTAL OBSERVATION:** Monitor for future standard interop; not ready for production core. |

## 3. Decision
1. **Unquestioned Sovereignty of `ActionGateway`:**
   External policy engines (OPA, Cedar, AuthZEN) never hold ultimate authorization or budget authority. The `ActionGateway` is the sole authority that can grant execution permission.
2. **Auxiliary Policy Adapter:**
   External engines may act solely as upstream policy inputs to `ActionGateway`. If an external policy engine evaluates `ALLOW`, the `ActionGateway` still performs its full battery of checks:
   - Autonomy tier ceiling.
   - Company spend budget guard.
   - Dual-control human approval threshold.
   - Global emergency kill-switch status.
3. **Fail-Closed Integration:** If an auxiliary tenant policy engine is unreachable or times out (>50ms), the decision evaluates to `DENY`.

## 4. Consequences
- **Positive:** Preserves inviolable safety boundaries (Rule 33); prevents complex external policy definitions from bypassing foundational spend and kill-switch protections.
- **Negative:** Dual evaluation adds a small processing overhead for tenant-custom policies.
