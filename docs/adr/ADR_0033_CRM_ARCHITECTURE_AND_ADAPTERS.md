# ADR 0033: CRM Architecture and Integration Adapters

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 59 (Systems of Record are Ports), Rule 60 (Copyleft Business Systems Stay Separate Services), Rule 64 (Consent-Governed Outreach)

---

## 1. Context & Problem Statement
Customer relationship management involves contact lifecycle tracking, lead scoring, deal pipelines, and automated outreach. We must provide a native CRM while seamlessly integrating with market-leading CRM platforms.

## 2. Decision
1. **Hybrid Architecture:**
   - **Native Lightweight CRM:** Built directly within ZONATA for companies without third-party CRM systems.
   - **CrmPort Adapters:** Pluggable adapters supporting external platforms.
2. **External Candidates:**
   - Atomic CRM (MIT) and Twenty (AGPL-3.0). Twenty runs strictly as an unmodified standalone network service container under Rule 60 with zero vendored code.
   - Commercial SaaS integrations: HubSpot, Zoho, Salesforce, and Pipedrive connected via official REST APIs mediated by MCP.
3. **Consent Enforcement (Rule 64):**
   - All contact interactions must record lawful basis and check unsubscribe/suppression lists.
   - SMS, WhatsApp, and voice outreach channels remain `NOT_CONFIGURED` until legal clearance is granted.

## 3. Consequences
- Zero vendor lock-in for enterprise customers with existing CRM investments.
- Guaranteed compliance with anti-spam and telemarketing regulations.

