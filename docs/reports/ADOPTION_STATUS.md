# ZONATA Framework Adoption Status (Rule 37 Honesty Log)

In compliance with **Standing Rule 37 (Adoption Honesty)**:
> "A library counts as adopted only if it is imported by code that the qualification scenario actually executes. Otherwise it is `NOT_ADOPTED` in `docs/reports/ADOPTION_STATUS.md`. The reverse also fails: no doc, UI string or log may name a framework that is not used."

| Subsystem / Framework | Status | Version / Package | Primary Module | Notes |
|:---|:---|:---|:---|:---|
| **Local Agent Runtime** | `ADOPTED` | Sovereign in-process | `core.ports.agent_runtime.LocalAgentRuntimeAdapter` | Step 4B execution adapter routing through LLMGateway and ActionGateway |
| **LangGraph / PostgresCheckpointer** | `ADOPTED` | Sovereign StateGraph Adapter | `core.langgraph.adapter.LangGraphRuntimeAdapter`, `core.langgraph.checkpointer.PostgresCheckpointer` | Step 4C cyclic state graph with KMS Rule 36 encrypted PostgreSQL checkpoints |
| **Temporal Durable Execution** | `NOT_ADOPTED` | `temporalio>=1.5.0` | `core.temporal` | Scheduled for Sub-Step 4D |
| **Google ADK** | `NOT_ADOPTED` | Sovereign Hierarchical Teams | `core.adk` | Scheduled for Sub-Step 4F |
| **Governed MCP Client** | `NOT_ADOPTED` | `mcp>=1.0.0` | `core.mcp` | Scheduled for Sub-Step 4G |
| **OpenTelemetry GenAI** | `NOT_ADOPTED` | `opentelemetry-api` | `core.telemetry` | Scheduled for Sub-Step 4H |
