# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Distributed Observability & Telemetry Architecture

---

### 1. Unified Telemetry Context
Every request, workflow event, tool execution, and database mutation in ZONATA carries a distributed trace context:
* `request_id`: Edge HTTP identifier (`req_...`).
* `correlation_id`: Distributed transaction chain tracker across worker pods.
* `causality_id`: Cryptographic causality anchor linking actions to real-world outcomes.
* `tenant_id`: Mandatory tenant context to isolate telemetry.
* `agent_id`: Attributable AI employee identity.

---

### 2. Strict Metric Tier Partitioning
To eliminate deceptive claims, ZONATA's `ObservabilityEngine` (`core/observability_engine.py`) enforces strict physical metric tiering:

```
+-----------------------------------------------------------------------------------+
| METRIC TIER 1: REAL (Production customer traffic, actual external API side effects)|
+-----------------------------------------------------------------------------------+
| METRIC TIER 2: SIMULATED (High-concurrency stress test workers, load generators)  |
+-----------------------------------------------------------------------------------+
| METRIC TIER 3: SYNTHETIC (Continuous health probes, automated canary transactions)|
+-----------------------------------------------------------------------------------+
| METRIC TIER 4: SEEDED (Historical database records, pre-warmed tenant fixtures)   |
+-----------------------------------------------------------------------------------+
| METRIC TIER 5: MOCK (Isolated unit test assertions, offline sandbox fixtures)     |
+-----------------------------------------------------------------------------------+
```

> [!CRITICAL]
> **No Metric Merging**: Telemetry dashboards and reports are constitutionally forbidden from aggregating `SIMULATED` or `MOCK` numbers into `REAL` production metrics.
