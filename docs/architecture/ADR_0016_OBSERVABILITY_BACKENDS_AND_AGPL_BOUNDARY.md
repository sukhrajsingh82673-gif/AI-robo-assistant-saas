# ADR 0016: Observability Backends and AGPL-3.0 Licensing Boundary

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4H — Metrics, logs, traces, and dashboard storage  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
ZONATA requires operational monitoring across metrics, logs, and traces. We must select backend services that fulfill enterprise observability needs while strictly adhering to open-source licensing boundaries (Standing Rule 5 & Rule 14).

## 2. Evaluation of Backends and Licenses

| Component | Upstream Licence | Classification | Architecture Role |
|:---|:---:|:---:|:---|
| **Prometheus** | Apache-2.0 | Permissive | Metric time-series storage and alerting rules. |
| **Alertmanager** | Apache-2.0 | Permissive | Alert routing, deduplication, and notification. |
| **Jaeger** | Apache-2.0 | Permissive | Distributed trace visualization and query backend. |
| **Grafana** | AGPL-3.0 | Boundary Service | Operational dashboards for platform operators. |
| **Loki** | AGPL-3.0 | Boundary Service | Log aggregation backend. |
| **Tempo** | AGPL-3.0 | Boundary Service | High-scale trace storage backend. |

## 3. Decision & Compliance Enforcements
1. **Permissive Core:** Prometheus, Alertmanager, and Jaeger serve as the standard Apache-2.0 monitoring baseline.
2. **AGPL-3.0 Boundary Service Rules (Standing Rule 5 & Rule 14):**
   - Grafana, Loki, and Tempo are strictly designated as **BOUNDARY services**.
   - They run as completely unmodified, separate container network services.
   - Zero application code, libraries, or SDKs in ZONATA import AGPL-licensed modules.
   - Client and tenant interactions occur exclusively via standard HTTP APIs and ZONATA's RLS-protected metric gateway, never granting direct database access to external consumers.
