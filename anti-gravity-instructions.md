# Project Directives: AI Company OS (Paperclip Architecture Integration)

## 1. Core Mandate
Refactor and build the AI Company Operating System using the architectural patterns, agent workflows, state management, and UI/UX structures found in the Paperclip open-source repository.
Treat Paperclip as the structural blueprint. Use its agent orchestration, operational pipelines, setting systems, and frontend layouts as the foundation, while integrating and extending custom company capabilities.

## 2. Strict Naming & Code Hygiene Rules (No Paperclip Artifacts)
To maintain code cleanliness, aesthetics, and white-label professionalism:
- **Zero "Paperclip" Brand Leaks**: Never use the word `paperclip` in file names, folder names, variable names, class names, API endpoints, or database tables.
  - *Bad*: `paperclip-agent-manager.ts`, `PaperclipConfig`, `/api/paperclip/tasks`
  - *Good*: `company-os-manager.ts`, `SystemConfig`, `/api/os/tasks`
- **Clean Naming Conventions**: Adopt domain-driven terminology suited for an enterprise AI Company OS:
  - Agent runtime &rarr; `AgentRuntime`, `Orchestrator`, `WorkerRegistry`
  - Company operating system &rarr; `CompanyOS`, `EnterpriseCore`, `VirtualHQ`
  - Workflows & execution &rarr; `TaskGraph`, `OperationPipeline`, `JobDispatcher`
- **Code Comments & Docstrings**: Do not paste raw upstream header comments referencing "Paperclip". Keep comments focused purely on functionality.

## 3. Preservation of Custom & Existing Features
- **Additive Development Only**: Do not delete, overwrite, or deprecate any custom functions, custom agent tools, proprietary endpoints, or verified features already built in this project.
- **Merge, Do Not Overwrite**: If a feature exists in the current codebase that is also implemented in Paperclip, merge the stability/efficiency of the Paperclip pattern while keeping our custom logic intact.
- **Extension Anchors**: Any functionality required by our product roadmap that Paperclip lacks must be introduced cleanly via pluggable modules or service extensions.

## 4. Architectural Implementation Blueprint
| Domain | Architecture Guidance |
|---|---|
| **Frontend & Dashboard** | Replicate Paperclip's information hierarchy: real-time agent status feeds, company org chart/agent hierarchy, project/task boards, and configuration panels. Use our established design tokens (colors, typography, radii). |
| **Agent Orchestration** | Port Paperclip's task delegation, inter-agent messaging, context handoffs, and feedback loops into our native agent registry. |
| **Settings & Control Plane** | Match Paperclip's configuration architecture for API keys, model routing, autonomous execution limits, and workspace permissions. |
| **State & Persistence** | Follow Paperclip's state schemas for tracking task lifecycle states (`idle`, `in_progress`, `blocked`, `completed`, `review`), persisting agent logs cleanly. |

## 5. Execution Rules for Every Code Generation Task
- **Analyze First**: Inspect existing project files to ensure no custom logic will be broken before generating new files.
- **Abstract the Source**: When extracting logic from Paperclip, refactor it immediately into clean TypeScript/Python/native stack code adhering to our project structure.
- **Verify Imports**: Ensure internal module imports reference native paths (e.g., `@/core/agents`, `@/components/os`), never external upstream repo paths.
