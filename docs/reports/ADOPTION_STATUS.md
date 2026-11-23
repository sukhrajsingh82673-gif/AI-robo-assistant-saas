# ZONATA Framework Adoption Status (Rule 37 Honesty Log)

In compliance with **Standing Rule 37 (Adoption Honesty)**:
> "A library counts as adopted only if it is imported by code that the qualification scenario actually executes. Otherwise it is `NOT_ADOPTED` in `docs/reports/ADOPTION_STATUS.md`. The reverse also fails: no doc, UI string or log may name a framework that is not used."

| Subsystem / Framework | Status | Version / Package | Primary Module | Notes |
|:---|:---|:---|:---|:---|
| **Local Agent Runtime** | `ADOPTED` | Sovereign in-process | `core.ports.agent_runtime.LocalAgentRuntimeAdapter` | Step 4B execution adapter routing through LLMGateway and ActionGateway |
| **LangGraph / PostgresCheckpointer** | `ADOPTED` | Sovereign StateGraph Adapter | `core.langgraph.adapter.LangGraphRuntimeAdapter`, `core.langgraph.checkpointer.PostgresCheckpointer` | Step 4C cyclic state graph with KMS Rule 36 encrypted PostgreSQL checkpoints |
| **Temporal Durable Execution** | `ADOPTED` | Sovereign Durable Engine | `core.temporal.adapter.TemporalRuntimeAdapter`, `core.temporal.workflows.ZonataAgentWorkflow` | Step 4D enterprise durable workflow and worker execution with deterministic idempotency |
| **Google ADK** | `ADOPTED` | Sovereign Hierarchical Teams | `core.adk.adapter.GoogleADKRuntimeAdapter`, `core.adk.coordinator.HierarchicalTeamCoordinator` | Step 4F supervisor-worker-critic squads bounded by tree depth <= 3 and feedback loops <= 5 |
| **Governed MCP Client** | `ADOPTED` | Sovereign Governed MCP Client | `core.mcp.client.GovernedMCPClient`, `core.mcp.server.SandboxedMCPServer` | Step 4G tool schema hash pinning, prompt injection neutralization, and ActionGateway execution |
| **OpenTelemetry GenAI** | `ADOPTED` | Sovereign OTel GenAI Engine | `core.telemetry.tracer.ZonataTracer`, `core.telemetry.canary.TelemetryCanaryProbe` | Step 4H OpenTelemetry distributed tracing, GenAI semantic conventions, and secret canary validation |
| **24/7 Autonomous Daemon** | `ADOPTED` | Sovereign Supervisor Daemon | `core.daemon.autonomous_daemon.AutonomousDaemon`, `core.daemon.self_healing.SelfHealingSupervisor` | Step 4I distributed leader leases, leased scheduler, outbox DLQ, and self-healing recovery |
