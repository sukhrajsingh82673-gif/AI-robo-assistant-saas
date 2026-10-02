# Third-Party Software Notices & Licenses

This project incorporates components, libraries, and architectural patterns licensed under standard open-source licenses.

---

### 1. Agent Orchestration Engine Patterns
- **Upstream Origin:** Paperclip Open Source Project (Agent Orchestration & State Patterns)
- **License:** MIT License
- **Copyright:** (c) 2025 Paperclip AI
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the MIT license terms preserved in `src/services/agent-engine/THIRD_PARTY_LICENSES.md`.

---

### 2. Runtime Dependencies & Standard Libraries
- **Python Standard Library:** Python Software Foundation (PSF) License
- **SQLite3 Database Engine:** Public Domain
- **OpenSSL / Cryptography:** OpenSSL License / Apache 2.0
- **Cloudflared Tunnel Client:** Apache 2.0

---

### 3. Multi-Agent Workforce Orchestration Framework Patterns
- **Package:** Agency Swarm
- **Upstream Origin:** [VRSEN/agency-swarm](https://github.com/VRSEN/agency-swarm)
- **Version:** 1.12.0 (Commit `9e74353396be1bc04d2b4d6e1c8f13693afacf1a`, Baseline Tag `v1.11.0`)
- **License:** MIT License
- **Copyright:** (c) 2023-2026 Vrsen AI Solutions
- **Integration Method:** Isolated WorkforceRuntime Adapter (`core/workforce_runtime.py`, `core/workforce_orchestrator.py`, `zonata/agent_swarm_adapter.py`)
- **Production Usage:** Autonomous Multi-Agent Coordination, Dynamic Specialist Squads, and Directional Role Handoffs governed by ZONATA Authority, PolicyEngine, ApprovalPipeline, and EvidenceLedger.
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

---

### 4. Stateful Agent Memory, Identity & Long-Horizon Context Patterns
- **Package:** Letta (formerly MemGPT) / Letta Code
- **Upstream Origin:** [letta-ai/letta](https://github.com/letta-ai/letta) and [letta-ai/letta-code](https://github.com/letta-ai/letta-code)
- **Version Baseline:** 0.34.1 / 0.16.8 (Commit `3687ea51f6d11eabc4ad7a7b163c649d023801ba`)
- **License:** Apache License 2.0
- **Copyright:** (c) 2023-2026 Letta Inc.
- **Integration Method:** Stateful Agent Runtime Gateway & Adapter (`core/stateful_agent_runtime.py`, `zonata/stateful_agent_adapter.py`)
- **Production Usage:** Persistent Agent Identities, Working Memory Blocks (Persona & Human), Scoped Memory Storage, Context Budget Compaction, Recall Buffers, and Cross-Session Executive Continuity, strictly governed by ZONATA Authority, PolicyEngine, ApprovalPipeline, and EvidenceLedger.
- **Terms:** Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

---

### 5. Multimodal Perception, Interaction & Local-Assistant Capability Layer
- **Package:** HAL9000
- **Upstream Origin:** [shandar/HAL9000](https://github.com/shandar/HAL9000)
- **Version Baseline:** 1.5.0 (Commit `1160f57f1b21ef0baa1b1353e6b0110617116e8b`)
- **License:** MIT License
- **Copyright:** (c) 2026 Shandar Junaid / Affordance Design Studio
- **Integration Method:** Universal Multimodal Capability Runtime & Governed Adapter (`core/multimodal_capability_runtime.py`, `zonata/hal_multimodal_adapter.py`)
- **Production Usage:** Multimodal human-computer interaction, vision observation, audio/STT processing, speech synthesis (TTS), local-first model routing, desktop robot integration, governed MCP provider, and execution state machine under strict ZONATA Authority, PolicyEngine, ApprovalPipeline, and EvidenceLedger.
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

## 6. LangGraph (langchain-ai/langgraph)
- **Repository:** `https://github.com/langchain-ai/langgraph`
- **Version Baseline:** 1.2.12 (Commit `f6e9ace6395b489778f80c65130d0d02bad4fd1d`)
- **License:** MIT License
- **Copyright:** (c) 2024 LangChain, Inc.
- **Python Version Requirements:** >=3.10 (Running 3.14 on Linux Host)
- **Direct Dependencies:** `langgraph-checkpoint>=4.1.0`, `langgraph-sdk>=0.4.2`, `langgraph-prebuilt>=1.1.0`, `pydantic>=2.7.4`, `langchain-core>=1.4.7`
- **Transitive Dependencies:** `xxhash`, `typing-extensions`, `jsonpath-ng`
- **Integration Method:** Governed Durable Workflow Runtime & LangGraph Provider (`core/durable_workflow_runtime.py`, `zonata/langgraph_adapter.py`)
- **Governance Boundary:** Implements `WorkflowRuntimeProvider` abstraction. LangGraph provides durable execution, checkpoints, state graphs, human-in-the-loop interrupts, deterministic and agentic node compositions, and cyclic workflows without bypassing ZONATA PolicyEngine, AuthorityGateway, ApprovalEngine, or EvidenceLedger.
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

## 7. Agent2Agent (A2A) Protocol (a2aproject/A2A)
- **Repository:** `https://github.com/a2aproject/A2A`
- **Version Baseline:** 1.0.1 (Commit `1ae57a673f729f743b35f2677f3adc302438695a`, Specification v1.0)
- **Host / Organization:** Linux Foundation
- **License:** Apache License 2.0
- **Copyright:** (c) 2024-2026 The A2A Authors (Linux Foundation Project)
- **Python Version Requirements:** >=3.10 (Running 3.14 on Linux Host)
- **Direct Dependencies:** Standard library `urllib`, `json`, `hashlib`, `hmac`, `uuid`, `re` (Clean zero-bloat runtime)
- **Integration Method:** Governed Agent Interoperability Gateway & A2A Provider (`core/a2a_interoperability_runtime.py`, `zonata/a2a_adapter.py`)
- **Governance Boundary:** Implements `AgentInteropProvider` abstraction. A2A operates as an interoperability communication protocol connecting ZONATA with external/independent agents. It provides agent discovery, Agent Cards, capability discovery, remote task delegation, and streaming without granting external agents authority, permission, memory access, or credentials. All remote interactions pass through ZONATA PolicyEngine, AuthorityGateway, ApprovalEngine, EvidenceLedger, and KillSwitch.
- **Terms:** Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

---

## 8. Model Context Protocol (MCP) (modelcontextprotocol/modelcontextprotocol)
- **Repository:** `https://github.com/modelcontextprotocol/modelcontextprotocol`
- **Specification Release:** `2026-07-28` (Normative Stateless Protocol Core, Streamable HTTP + stdio Transports, Tasks Extension)
- **License:** MIT License
- **Copyright:** (c) 2024-2026 Anthropic PBC & Model Context Protocol Authors
- **Python Version Requirements:** >=3.10 (Running 3.14 on Linux Host)
- **Direct Dependencies:** Standard library `urllib`, `json`, `hashlib`, `hmac`, `uuid`, `re`, `subprocess`, `threading` (Zero-bloat governed runtime)
- **Integration Method:** Governed Tool/Data Interoperability Gateway & MCP Provider (`core/mcp_interoperability_runtime.py`, `zonata/mcp_adapter.py`)
- **Governance Boundary:** Implements `ToolInteropProvider` / `MCPToolInteropProvider` abstraction. MCP operates as the standardized Agent ↔ Tool / Data / System interoperability protocol connecting ZONATA with external CRM, ERP, PMS, databases, files, and SaaS endpoints. It provides server registration, tool/resource/prompt discovery, governed tool invocation, streaming HTTP, stdio subprocesses, and inbound MCP hosting without granting external tools authority, permission, memory access, or credentials. All remote tool interactions pass through ZONATA PolicyEngine, Authority Gateway, ApprovalEngine, EvidenceLedger, KillSwitch, and Business Causality Engine (`TASK_SUCCESS != BUSINESS_OUTCOME`).
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

---

## 9. OpenHands (OpenHands/OpenHands & OpenHands/software-agent-sdk)
- **Repositories:** `https://github.com/OpenHands/OpenHands` and `https://github.com/OpenHands/software-agent-sdk`
- **Architectural Baseline:** Software Agent SDK / Agent Server / Ephemeral & Persistent Workspaces / Event Stream / Governed Execution Runtime
- **License:** MIT License
- **Copyright:** (c) 2024-2026 OpenHands Authors
- **Python Version Requirements:** >=3.10 (Running 3.14 on Linux Host)
- **Direct Dependencies:** Standard library `urllib`, `json`, `hashlib`, `uuid`, `re`, `subprocess`, `os`, `shutil`, `threading` (Zero-bloat governed runtime)
- **Integration Method:** Governed Agent Execution Runtime Gateway & OpenHands Provider (`core/openhands_execution_runtime.py`, `zonata/openhands_adapter.py`)
- **Governance Boundary:** Implements `AgentExecutionProvider` abstraction. OpenHands operates as a governed agent execution and workspace runtime beneath ZONATA's existing AI CEO → Agency Swarm → TaskMaker → LangGraph hierarchy. It provides sandboxed workspace isolation, safe file mutations, deterministic command risk classification, artifact registry, and security event auditing without granting agents autonomous business authority or unmonitored system access. All execution lifecycles pass through the ZONATA Multi-Scope KillSwitch, Context Firewall, Command Risk Classifier, Human Approval Escalation, PolicyEngine, Merkle Evidence Ledger sealing, and Business Causality Engine (`TASK_SUCCESS != BUSINESS_OUTCOME`).
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

---

## 10. Browser Use (browser-use/browser-use)
- **Repository:** `https://github.com/browser-use/browser-use`
- **Architectural Baseline:** Governed Autonomous Browser & Web-Computer Execution Layer / Playwright-backed & Deterministic Browser Abstractions / Multi-Tab Sessions / DOM Understanding & Action Execution
- **License:** MIT License
- **Copyright:** (c) 2024-2026 Browser Use Authors
- **Python Version Requirements:** >=3.10 (Running 3.14 on Linux Host)
- **Direct Dependencies:** Standard library `urllib`, `json`, `hashlib`, `uuid`, `re`, `time`, `os`, `shutil`, `typing` (Zero-bloat governed runtime with optional `playwright` bridge)
- **Integration Method:** Governed Autonomous Browser Execution Layer Gateway & BrowserUse Provider (`core/browser_use_execution_runtime.py`, `zonata/browser_use_adapter.py`)
- **Governance Boundary:** Implements `BrowserExecutionProvider` abstraction. Browser Use operates as a governed real-browser execution layer beneath ZONATA's existing AI CEO → Agency Swarm → TaskMaker → LangGraph hierarchy. It provides sandboxed browser session management (ephemeral, persistent, authenticated, read-only), multi-tab coordination, DOM interaction, screenshot/artifact capture, and visual verification without granting autonomous business authority or unrestricted web access. All browser actions pass through the ZONATA Multi-Scope Browser KillSwitch (Global, Tenant, Company, Session, Execution, Domain, Agent), SSRF Defense Boundary (blocking private RFC1918 subnets, loopback, and cloud metadata), Prompt Injection Neutralizer, Action Risk Classifier, Human-in-the-Loop Financial Mutation Escalation, PolicyEngine, Merkle Evidence Ledger sealing, and Business Causality Engine (`TASK_SUCCESS != BUSINESS_OUTCOME`).
---

## 11. Temporal (temporalio/temporal & temporalio/sdk-python)
- **Repositories:** `https://github.com/temporalio/temporal` and `https://github.com/temporalio/sdk-python`
- **Architectural Baseline:** Governed Durable Execution & Long-Running Mission Reliability Layer / Workflows, Activities, Task Queues, Workers, Event History, Signals, Updates, Queries, Schedules, Multi-Scope KillSwitch, Saga Compensations, Merkle Evidence Ledger Sealing, TrustGraph Causality Linking.
- **License:** MIT License
- **Copyright:** (c) 2019-2026 Temporal Technologies Inc.
- **Python Version Requirements:** >=3.10 (Running 3.14 on Linux Host)
- **Direct Dependencies:** Standard library `urllib`, `json`, `hashlib`, `uuid`, `re`, `time`, `sqlite3`, `threading`, `typing` (Zero-bloat governed runtime with optional `temporalio` SDK connection)
- **Integration Method:** Governed Durable Execution Layer Gateway & Temporal Provider (`core/temporal_durable_execution_runtime.py`, `zonata/temporal_adapter.py`)
- **Governance Boundary:** Implements `TemporalExecutionProvider` / `TemporalDurableExecutionGateway` abstraction. Temporal operates as an infrastructure-grade execution reliability layer subordinate to ZONATA's existing AI CEO → Agency Swarm / Workforce → Mission → TaskMaker → LangGraph hierarchy. It provides durable execution state, retry policies, deterministic replay, saga compensations, and human approval waits without granting autonomous business authority, unmonitored execution, or decision-making rights. Temporal does NOT replace ZONATA governance or LangGraph orchestration. All workflows, activities, retries, and reconciliations pass through the ZONATA Multi-Scope KillSwitch (Global, Tenant, Company, Mission, Workflow, Worker, Queue, Activity, Agent), Context Firewall (prompt injection defense, credential scrubbing), Non-Idempotent Mutation Reconciliation, Human-in-the-Loop Approval Escalation, PolicyEngine, Merkle Evidence Ledger sealing, and Business Causality Engine (`TASK_SUCCESS != BUSINESS_OUTCOME`).
- **Terms:** Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
