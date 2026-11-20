# ZONATA Architectural Patterns & References

**Document Version:** 1.0.0  
**Purpose:** Record design inspirations and architectural patterns reimplemented in ZONATA's proprietary sovereign design without code or prompt copying.

---

## 1. Reimplemented Patterns

### 1.1 Router / Worker "Super-Agent" Pattern
* **Inspiration:** DeepSeek Super-Agent / Dual-Loop Architecture (MIT pattern) and LangGraph Supervisor pattern.
* **ZONATA Sovereign Reimplementation:**
  - The URA Assistant serves as the unified conversational router (`web/ura_assistant.js`, `core/ura_assistant_service.py`).
  - It receives requests and events, checks admission against the Charter, and dispatches bounded Work Items to isolated workers.
  - Workers run one Work Item each in an isolated session, governed by token/budget limits, and report findings back to the router.
  - Follow-up user messages skip the router via thread subscriptions.

### 1.2 Deterministic Governance Gates (Code over Models)
* **Inspiration:** NASA / FAA safety-critical avionics state machines, NIST AI RMF, and ISO 26262.
* **ZONATA Sovereign Reimplementation:**
  - No LLM holds a gate.
  - Gates G00 through G13 evaluate mathematically via Python AST checking, regex scanning, Wilson score lower bound confidence intervals, and cryptographic signature validation.
  - Implemented in `agent_factory/cert/gates.py` and `core/approvals.py`.

### 1.3 Evidence-Before-Effect & Merkle Audit Trail
* **Inspiration:** Git Merkle DAGs, Certificate Transparency (RFC 6962), and Double-Entry Bookkeeping.
* **ZONATA Sovereign Reimplementation:**
  - State changes in database tables (`af_*`) require prior cryptographic event logging in `EvidenceLedger` before side effects take place.
  - Enforced by `agent_factory.domain.transition.transition()`.

### 1.4 Lean SIPOC & Kaizen Continuous Improvement
* **Inspiration:** Toyota Production System (TPS), Kaizen, and Six Sigma SIPOC (Suppliers, Inputs, Process, Outputs, Customers).
* **ZONATA Sovereign Reimplementation:**
  - Declarative Process Packs with explicit SIPOC definitions, waste tags (waiting, rework, over-processing, handoff, defects, unused talent), and andon cord conditions.
  - Automated KPI collection and shadow-mode improvement proposals.

### 1.5 Autonomy L0–L4 Graduated Dial
* **Inspiration:** SAE J3016 autonomous driving levels adapted for enterprise cognitive workflows.
* **ZONATA Sovereign Reimplementation:**
  - Autonomy is dialed per process, from L0 (Observe-only) to L4 (Autonomous with post-review sampling).
  - Promotion requires empirical evidence (run count, first-pass yield, zero critical incidents).
