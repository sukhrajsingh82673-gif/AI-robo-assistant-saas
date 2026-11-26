# ADR 0027: External Open-Source Agent Intake Architecture & Hermes Evaluation

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Security Arbiter, Repository Owner
- **Governing Rules:** Rule 5 (OSI Allow-list), Rule 32 (No Curl-to-Shell), Rule 53 (Mandatory Provenance)

---

## 1. Context & Problem Statement
To enrich the ZONATA Agent Factory without reinventing external community patterns, we require an intake lane ("Agent Zoo") for evaluating, quarantining, and governing third-party open-source agents and toolkits.

## 2. Decision
1. **Intake State Machine:** All external agents follow a mandatory lifecycle:
   `DISCOVERED -> QUARANTINED -> EVALUATED -> APPROVED_FOR_SANDBOX -> CERTIFIED -> ACTIVE`
   Promotion to `ACTIVE` requires explicit human owner approval.
2. **Hermes Agent Candidate:** We select Hermes Agent (Nous Research, MIT License) as the baseline candidate for Sub-Step 6G evaluation.
3. **Installation & Security Restrictions:**
   - External agents must be checked out from pinned git commits with cryptographic SHA-256 dependency hashes.
   - Pipe-to-shell installers (`curl | sh` or `wget | bash`) are strictly **prohibited** under Standing Rule 32.
   - Sibling components licensed under AGPL-3.0 remain strictly `BOUNDARY` (isolated network service containers) or excluded.
   - Community skill hubs and uncurated registries are treated as untrusted data inputs.
4. **Runtime Isolation:** External agents run behind `ExternalAgentPort` with gateway mediation, zero host credentials, no host filesystem mounts, and disabled self-update capabilities.

## 3. Consequences
- Safe evaluation of external agent architectures.
- High-risk external code cannot escalate privileges or access internal infrastructure.
