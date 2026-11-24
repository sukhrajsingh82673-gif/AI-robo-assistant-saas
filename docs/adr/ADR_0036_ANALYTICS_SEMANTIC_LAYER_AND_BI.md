# ADR 0036: Analytics Semantic Layer and Business Intelligence (BI)

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Arbiter, Repository Owner
- **Governing Rules:** Rule 59 (Systems of Record are Ports), Rule 60 (Copyleft Business Systems Stay Separate Services), Rule 65 (Semantic Layer is Source of Truth)

---

## 1. Context & Problem Statement
ZONATA departments require cross-departmental reporting, executive dashboards, KPIs, and LLM-accessible business metrics. Directly running ad-hoc SQL from agents against production operational tables risks data exfiltration, hallucinated calculations, and database lock contention.

## 2. Decision
1. **Semantic Layer Engine:** Adopt **Cube Core** (Apache 2.0) / MetricFlow as the centralized semantic layer.
   - All departmental metrics (e.g. ARR, Gross Margin, AP Aging, DSO, Churn, OEE, Hiring Velocity) are defined as code in version-controlled semantic models (YAML/JS).
   - Cube compiles metric definitions into parameterized SQL queries executed against read replicas or analytical stores.
   - Queries are exposed via three standard interfaces:
     - SQL API (Postgres wire protocol) for BI tools.
     - REST API for frontend applications.
     - Model Context Protocol (MCP) tools for agents and LLMs, preventing agents from writing raw SQL.
2. **Dashboard & Visualization Tier:**
   - **Primary Engine:** **Apache Superset 4.x** (Apache 2.0). Embedded in ZONATA UI via secure guest tokens with tenant and company RLS filters injected into dataset definitions.
   - **Boundary Evaluation:** Metabase was evaluated. Because Metabase open-source is licensed under AGPL-3.0 and enterprise features fall under commercial licensing, Metabase is restricted to optional unmodified standalone network service deployments marked `BOUNDARY — legal review`. Superset is the default, fully permissive Apache 2.0 platform.
3. **Multi-Tenant Security:**
   - Every semantic query automatically passes `tenant_id` and `company_id` through security context tokens.
   - Cube pre-aggregations are strictly partitioned by tenant ID to guarantee cross-tenant isolation in pre-computed caches.
4. **Agent Access Protocol:**
   - AI agents query metrics exclusively via the `BiPort` / `mcp_cube_analytics` toolset. Agents request named metrics and dimensions; the semantic layer resolves calculation logic deterministically.

## 3. Consequences
- Single source of truth for all business calculations across financial, operational, and sales domains.
- AI agents cannot hallucinate calculation logic or bypass tenant isolation.
- Fully permissive open-source stack (Cube Core + Superset under Apache 2.0).
