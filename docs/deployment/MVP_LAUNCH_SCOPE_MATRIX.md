# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# MVP Launch Scope Matrix & Integration Boundaries

**Document Version:** 1.0.0-GA  
**Last Updated:** 2026-10-17  
**Target Release:** Initial Production Cloud Staging & MVP Public Launch  

---

## 1. Executive Policy on External Integrations

To ensure honest engineering qualification, high customer trust, and zero misleading marketing claims, ZONATA enforces strict release boundaries:

> [!IMPORTANT]
> **MVP Gate Principle:** Any connector or third-party integration that has not been verified against a genuine live sandbox or live production API must NOT be presented to end users as an active, supported integration. Unverified integrations are either excluded from the initial public release surface or marked as "Sandbox / Beta Gated."

---

## 2. Comprehensive Integration Scope Matrix

| Subsystem / Capability | Initial MVP Launch Scope | Operational State in Release Candidate | Required Verification Evidence | Public Availability in MVP |
| :--- | :---: | :---: | :--- | :---: |
| **Autonomous Multi-Agent Workspace** | **IN SCOPE** | **QUALIFIED (100%)** | 228 local tests, task graphs, state persistence, audit trail | **YES (Core Product)** |
| **Enterprise Identity & Multi-Tenancy** | **IN SCOPE** | **QUALIFIED (100%)** | Tenant isolation, timing-safe auth, token revocation, RBAC | **YES (Core Product)** |
| **PostgreSQL 16 Storage & Pooling** | **IN SCOPE** | **QUALIFIED (100%)** | 12 CI tests, connection pooling, ANSI conflict resolution, migrations | **YES (Core Product)** |
| **Disaster Recovery & WORM Backups** | **IN SCOPE** | **QUALIFIED (100%)** | AES-256-GCM envelope, SHA-256, WORM retention, restore drill (RTO 0.03s, RPO 7.16s) | **YES (Infrastructure)** |
| **Production SRE Observability** | **IN SCOPE** | **QUALIFIED (100%)** | Prometheus rules, Alertmanager, low cardinality metrics, Grafana | **YES (Operations)** |
| **Stripe Payments** | **GATED OPTION** | `IMPLEMENTED BUT SANDBOX UNVERIFIED` | Unit tests pass; requires injection of genuine Stripe test API keys (`sk_test_...`) | **Beta / Admin-Enabled Only** |
| **Razorpay Payments** | **GATED OPTION** | `IMPLEMENTED BUT UNVERIFIED` | Unit tests pass; requires injection of Razorpay test credentials | **Beta / Admin-Enabled Only** |
| **Intuit QuickBooks** | **EXCLUDED FROM MVP** | `IMPLEMENTED BUT UNVERIFIED` | Unit tests pass; awaiting Intuit Developer sandbox approval | **NO (Scheduled for Phase 12)** |
| **Oracle Opera / PMS** | **EXCLUDED FROM MVP** | `BLOCKED` | Awaiting Oracle Partner Network (OPN) agreement and OHIP sandbox | **NO (Enterprise Roadmap)** |
| **Salesforce CRM** | **EXCLUDED FROM MVP** | `MOCK ONLY` | In-memory mock adapter only; no live adapter | **NO (Roadmap)** |
| **Google Workspace** | **EXCLUDED FROM MVP** | `MOCK ONLY` | In-memory mock adapter only; no live adapter | **NO (Roadmap)** |

---

## 3. Launch Path Recommendations

### Pathway 1: Self-Contained MVP Launch (Fastest & Zero-Blocker)
- **Scope:** Complete Autonomous AI Operating System, Coworker Registry, Enterprise Workspaces, Document & Report Generators, Tenant IAM, PostgreSQL 16 Persistence, WORM Backups, and Ingress Security.
- **Billing Method:** Free tier, invoice/manual enterprise onboarding, or admin voucher codes.
- **External Dependencies:** Zero (no waiting for Oracle, QuickBooks, or third-party approval).
- **Time to Staging:** Immediate upon AWS account and domain provisioning.

### Pathway 2: SaaS Commercial Launch (Pathway 1 + Payments)
- **Scope:** Pathway 1 + Stripe / Razorpay live sandbox qualification.
- **Prerequisite:** Injection of sandbox API keys into AWS Secrets Manager (`STRIPE_API_KEY`, `RAZORPAY_KEY_ID`).
- **Additional Verification:** Live webhook round-trip test against Stripe test mode.

### Pathway 3: Enterprise Hospitality & ERP Launch
- **Scope:** Pathway 2 + Oracle Opera and QuickBooks.
- **Prerequisite:** Execution of partner contracts and credential verification.
- **Gating:** Scheduled for enterprise rollout after MVP stability is established.
