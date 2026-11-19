# ZONATA / URA — GitHub CI/CD & Enterprise Release Process

This document describes the 7-stage automated delivery pipeline implemented in [`.github/workflows/ci_cd.yml`](../../.github/workflows/ci_cd.yml).

---

## 1. The 7-Stage Delivery Pipeline

```
[Git Push / PR]
       │
       ▼
 Stage 1: Change Validation (Syntax, Linting, Secret Screening, K8s Manifests)
       │
       ▼
 Stage 2: Automated Testing (40 Qualification Criteria + 25 Enterprise Tests + 77 Regression Tests)
       │
       ▼
 Stage 3: Security & Supply Chain (CycloneDX SBOM, License Screening, Vulnerability Admission)
       │
       ▼
 Stage 4: Reproducible Build & Provenance (SLSA Level 3 Provenance Digest, Dockerfiles)
       │
       ▼
 Stage 5: Test Environment Deployment (Isolated ephemeral daemon probe on port 8085)
       │
       ▼
 Stage 6: Controlled Promotion (Environment-specific approvals for Staging and Production)
       │
       ▼
 Stage 7: Post-Deployment Verification (Smoke missions, health probes, rollback verification)
```

---

## 2. Stage Breakdown & Verification Criteria

### Stage 1: Change Validation & Secret Screening
- **Branch Protection:** PR required for `main`.
- **Secret Scanning:** Scans working tree for unencrypted PEM keys, API keys (`sk-`, `ghp_`), and credentials.
- **Syntax Check:** Python `py_compile` on entrypoints and modules.
- **Manifest Validation:** Safe YAML loading across all `k8s/*.yaml` files.

### Stage 2: Automated Testing
- **Suite 1:** Universal Automation Fabric Qualification Suite (40 tests).
- **Suite 2:** Enterprise Capability Expansion Qualification Suite (25 tests).
- **Suite 3:** Durable Workflow & Enterprise Settings Regression Suite (77 tests).
- **Suite 4:** Adversarial Security and Multi-Tenant Isolation Suites.

### Stage 3: Security & Supply Chain
- **SBOM Generation:** Generates `docs/cyclonedx_sbom.json` via [`SecureSupplyChainController`](../../core/secure_supply_chain.py).
- **License Screening:** Checks all components against the OSI-approved whitelist (`Apache-2.0`, `MIT`, `BSD-3-Clause`, `BSD-2-Clause`, `ISC`).
- **Vulnerability Gate:** Evaluates CVE thresholds; halts on unresolved High/Critical CVEs.

### Stage 4: Reproducible Build
- Validates multi-stage Docker build definitions (`Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.supervisor`).
- Generates SLSA Level 3 Provenance Attestation binding git commit SHA to artifact hash.

### Stage 5: Ephemeral Test Environment
- Starts API server daemon in test container on port 8085.
- Probes `/api/automation/fabric/status` for `"OPERATIONAL"` health state.
- Gracefully tears down ephemeral test daemon.

### Stage 6: Controlled Promotion
- Automated promotion to development.
- Staging and Production promotions enforce manual executive sign-off.

### Stage 7: Post-Deployment Verification
- Executes safe verification mission using certified workflow template.
- Confirms active connector count (>= 18) and available templates (>= 19).
- Confirms rollback readiness.
