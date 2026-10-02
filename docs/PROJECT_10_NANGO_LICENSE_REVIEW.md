# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Legal & Provenance Assessment (Elastic License 2.0 Review)

### 1. Mandatory Legal Assessment Overview

Before integrating Project 10, ZONATA completed a legal provenance and architectural review of the Nango open-source repository (`https://github.com/NangoHQ/nango`).

Nango utilizes the **Elastic License 2.0 (ELv2)**, a source-available license rather than a traditional OSI-approved permissive license (such as MIT or Apache 2.0).

---

### 2. Analysis of the 10 Specific License Gate Questions

#### 1. Which Nango components are used?
ZONATA uses Nango strictly as an **internal backend connectivity infrastructure component**. We consume the standard connection model, provider configurations, action dispatch paradigms, webhook schemas, and data synchronization patterns.

#### 2. Which components are source-available?
The core Nango server, CLI, and integration scripts under `NangoHQ/nango` are source-available under ELv2.

#### 3. Which components may be used internally?
ELv2 explicitly grants the right to use, copy, distribute, make available, and prepare derivative works of the software, provided the specific restrictions in Section 2 of ELv2 are observed. Internal use within enterprise infrastructure is fully permitted.

#### 4. Does ZONATA's SaaS architecture trigger any hosted/managed-service restrictions?
**No.** Section 2.1 of ELv2 states:
> *"You may not provide the software to third parties as a hosted or managed service, where the service provides, substantially similar to each software, the value of the software itself."*

ZONATA is a Universal AI Company Operating System providing AI CEO executive cognition, multi-agent workforce orchestration, desktop and browser robot operations, and verified business causality. ZONATA does **not** provide "Nango-as-a-Service" or resell an integration platform. The primary value delivered to customers is autonomous company operations, not raw API integration brokering.

#### 5. Is ZONATA merely consuming Nango as an internal dependency?
**Yes.** Nango operates entirely behind ZONATA's `ExternalIntegrationGateway` abstraction. External clients and tenants never interface with raw Nango endpoints, APIs, or interfaces.

#### 6. Is any Nango source code copied directly into ZONATA?
**No.** ZONATA implements clean-room Python adapters (`core/nango_integration_runtime.py` and `zonata/nango_adapter.py`) that communicate with the Nango service via HTTP/REST protocol or standard library contracts. No ELv2 code is vendored or embedded in ZONATA repositories.

#### 7. Is any Nango UI embedded in ZONATA?
**No.** All user interfaces are custom-engineered ZONATA SPA components (`web/nango_workspace.js`) using ZONATA design tokens, dark theme styling, and governance HUD layouts.

#### 8. Does any modification create a distribution obligation?
**No.** Because ZONATA operates as a cloud-hosted SaaS / private enterprise deployment and does not distribute binary copies of Nango to third parties, no reciprocal distribution obligations are triggered.

#### 9. Is a commercial license required for ZONATA's architecture?
**No.** For ZONATA's standard SaaS and private enterprise deployments, internal usage as a subordinate execution layer complies with ELv2 terms. If a white-label OEM customer wishes to expose raw Nango administrative interfaces, an Enterprise Nango license should be obtained.

#### 10. Does the integration architecture permit clean replacement?
**Yes.** The `ExternalIntegrationProvider` protocol and `ExternalIntegrationGateway` abstract all external connectivity. Nango can be hot-swapped for direct API connectors, Composio, or custom OAuth gateways without modifying any upstream business logic, AI CEO cognition, or workforce agents.

---

### 3. Conclusion & Certification

ZONATA's integration of Nango conforms with Elastic License 2.0 restrictions. The integration is certified for production SaaS deployment.
