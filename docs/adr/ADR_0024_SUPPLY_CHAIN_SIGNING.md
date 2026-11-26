# ADR 0024: Software Supply-Chain Security, Provenance, and Container Signing

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 42 (Least privilege), Rule 45 (Crypto agility)

---

## 1. Context and Problem Statement
Deploying autonomous agent workloads requires strict guarantees that code, dependencies, and container images running in production match exact audited commits without tampering or injection. Supply-chain security solutions must be selected with consideration of repository visibility and enterprise plan dependencies.

## 2. Alternatives Considered

| Supply Chain Strategy | Technology & Licensing | Requirements & Constraints | Decision |
| :--- | :--- | :--- | :--- |
| **GitHub Artifact Attestations** | Sigstore / GitHub Actions native | **Constraint:** GitHub documentation states that artifact attestations on private repositories require a paid GitHub Enterprise Cloud plan. | **CONDITIONAL ADOPTION:** Used if repository is public or on GitHub Enterprise Cloud. |
| **Cosign + OpenBao Transit** | Cosign (Apache-2.0) + OpenBao (MPL-2.0) | Completely sovereign. Key pair generated and managed inside OpenBao Transit engine (`transit/keys/cosign-release`). Zero vendor lock-in. | **ADOPTED AS PRIMARY SOVEREIGN STANDARD:** Works across all git providers, private registries, and air-gapped environments without third-party plan restrictions. |
| **Docker Content Trust (DCT)** | Notary v1 / The Update Framework | Legacy Docker notary system. Deprecated in modern OCI registries. | **REJECTED:** Superseded by Cosign and Sigstore. |

## 3. Decision
1. **Cosign with OpenBao Transit as Authoritative Signer:**
   - Container images and release tarballs are signed in CI using `cosign sign --key "hashivault://transit/keys/cosign-release" <image>`.
   - The signing private key never leaves the OpenBao cryptographic boundary. CI runners authenticate via short-lived OIDC workload tokens.
2. **Sigstore Attestations in Public CI:**
   - In open-source or public release workflows, GitHub Artifact Attestations generate SLSA Level 3 build provenance.
3. **Admission Enforcement:**
   - Production container runtimes (e.g., Kubernetes via Kyverno/Gatekeeper, or Docker via signature verification wrapper) refuse to launch any image lacking a valid signature from `transit/keys/cosign-release`.
4. **Dependency Pinning & Vulnerability Scanning:**
   - All Python requirements must be pinned with exact hashes (`--require-hashes`).
   - CI builds run Trivy and OSV-Scanner, failing on any `CRITICAL` or unpatched `HIGH` CVE.

## 4. Consequences
- **Positive:** Complete provenance and non-repudiation of production software artifacts; zero vulnerability to compromised CI runners stealing long-lived private signing keys.
- **Negative:** Requires maintaining the Cosign signing step in release pipelines.
