# ADR 0034: Customer Support and Helpdesk Architecture

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 59 (Systems of Record are Ports), Rule 60 (Separate Boundary Services)

---

## 1. Context & Problem Statement
Customer support operations require ticket ingestion, SLA clock monitoring, escalation trees, and multi-channel customer communications.

## 2. Decision
1. **HelpdeskPort Interface:** All ticketing, ticket status queries, SLA alerts, and notes pass through typed `HelpdeskPort`.
2. **Lead Platform:** Chatwoot (MIT core / boundary container) is selected for live chat and omnichannel support. Zammad (GPL-3.0) and FreeScout (AGPL) are supported as alternative network service containers.
3. **IT Service Management:** GLPI (GPL-3.0) is designated for internal IT helpdesk and asset lifecycle tickets.
4. **SLA Timers & Escalations:** Governed by Temporal workflows with controllable virtual clocks to test escalation triggers deterministically.

## 3. Consequences
- Standardized ticket schema across multiple support platforms.
- Independent SLA escalation tracking immune to clock manipulation.
