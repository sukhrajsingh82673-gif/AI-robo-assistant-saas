# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Tool Factory Security Model (V2)

---

### 1. Invariants & Security Boundaries
* **TOOL != PERMISSION**: Discovering or registering an executable tool never grants execution rights. Every invocation requires a cleared `ActionEnvelope`.
* **CONTROL PLANE DEFENSE**: Control-plane processes (API server, database engine, supervisor) are physically separated from worker containers executing dynamic tools.
* **STATIC & DYNAMIC DUAL-GATE**: Passing AST static inspection is necessary but not sufficient; execution occurs only within unprivileged container sandboxes.
* **KILL CAPABILITY**: Every running tool process is monitored by a watchdog thread and terminated immediately if execution exceeds 30 seconds or violates memory ceilings.
