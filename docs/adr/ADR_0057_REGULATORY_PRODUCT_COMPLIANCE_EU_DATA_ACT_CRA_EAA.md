# ADR 0057: Regulatory Product Compliance — EU Data Act, CRA, EAA (Rule 77 & Rule 84)

## Status
Accepted

## Context
Operating as a global B2B SaaS platform in 2026 demands strict adherence to mandatory European and international regulatory frameworks:
1. **EU Data Act (Regulation EU 2023/2854):** Mandates customer data portability, non-discriminatory cloud switching, zero switching charges, and machine-readable export formats.
2. **Cyber Resilience Act (CRA - Regulation EU 2024/2847):** Mandates security-by-design, Software Bill of Materials (SBOM) maintenance, and rapid vulnerability and incident notification.
3. **European Accessibility Act (EAA - Directive 2019/882) / WCAG 2.2 AA:** Mandates digital accessibility across digital services and web consoles.

## Decision
1. **EU Data Act Switching Engine:**
   - Implement an automated, self-service tenant export and cloud switching package (`core/compliance/data_act_export.py`).
   - Export all tenant data, schema definitions, audit logs, and workflow histories in structured, open, machine-readable formats (JSON, CSV, Parquet) with zero exit fees or artificial lock-in friction.
2. **CRA Security Operations & SBOM:**
   - Maintain a real-time machine-readable CycloneDX / SPDX Software Bill of Materials.
   - Establish and document the CRA Incident and Vulnerability Handling Runbook (`docs/security/CRA_INCIDENT_RUNBOOK.md`) covering CSIRT/ENISA 24-hour notification pathways.
3. **EAA / WCAG 2.2 AA Compliance & ACR:**
   - Enforce automated accessibility quality gates in CI/CD (checking contrast, keyboard navigation, aria labels, semantic HTML).
   - Maintain an updated Accessibility Conformance Report (VPAT / ACR) in `docs/accessibility/DRAFT_ACR_VPAT.md`.

## Consequences
- **Positive:** Full regulatory readiness for European and global enterprise procurement; audited legal compliance.
- **Negative:** Ongoing maintenance of accessibility standards and compliance artifacts across all releases.
