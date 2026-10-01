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

