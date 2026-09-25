# RoboAssistant — Company OS 1.0 (AI Robo Assistant SaaS)

Autonomous AI Company Operating System providing multi-tenant portfolio management, an autonomous AI workforce, an AI CEO executive command engine, cryptographic evidence logging, and production enterprise connectors.

---

## 🚀 Key Capabilities

- **Executive Cockpit & Web UI**: Single-page interactive corporate management console for tracking operations, workforce status, and attention-required items.
- **AI CEO Strategic Brain**: Natural language strategic direction translation into actionable department missions and KPIs.
- **Universal Control Kernel & Evidence Ledger**: Cryptographically verified audit logging for every tool execution, action, and mission transition.
- **Multi-Tenant Portfolio Engine**: Support for multiple corporate entities across industries (Hospitality, Manufacturing, B2B SaaS, and Executive Operations).
- **Autonomous Workforce & Employment Contracts**: Dynamic agent contracts with explicit tool permissions, spending limits, and escalation policies.
- **First-Class Approval Pipeline**: Multi-tiered human-in-the-loop review system with digital signatures for high-risk or financial actions.
- **Digital Twin Simulator**: Epistemic truth tracking and predictive simulation before live state mutations.
- **Enterprise Connectors**: Built-in integrations for Hospitality PMS, Accounting ledgers, and Payment gateways.

---

## 📁 Repository Structure

```
.
├── api_server.py                # Unified REST API & static Web UI server
├── cli.py                       # Unified CLI Cockpit (portfolio, briefing, chat)
├── serve_web.py                 # Standalone web UI preview server
├── core/
│   ├── db.py                    # Multi-tenant SQLite persistence layer
│   ├── portfolio.py             # Multi-entity portfolio & onboarding engine
│   ├── ceo.py & ceo_brain.py    # AI CEO executive decision engine & reasoning
│   ├── control_kernel.py        # Universal Control Kernel with evidence verification
│   ├── tool_fabric.py           # Tool fabric & runtime capability registry
│   ├── workforce.py             # Autonomous agent employment contracts & factory
│   ├── approvals.py             # Human-in-the-loop approval pipeline
│   ├── decision_center.py       # Owner 'Attention Required' governance hub
│   ├── digital_twin.py          # Digital twin simulation engine
│   └── connectors.py            # Enterprise connectors (PMS, Accounting, Gateway)
├── workloads/
│   ├── hospitality.py           # Night audit & hospitality operations
│   ├── manufacturing.py         # Factory bottleneck & throughput analysis
│   ├── saas.py                  # Churn analysis & subscription health
│   └── personal.py              # File hygiene & host operations
├── web/                         # Production Single-Page Cockpit interface
│   ├── index.html
│   └── src/
├── storage/                     # SQLite database and evidence ledgers
├── tests/                       # Comprehensive verification test matrix
└── docs/                        # Architectural specifications
```

---

## ⚡ Getting Started

### 1. Requirements
- Python 3.10+
- SQLite3

### 2. Start the Unified Server (Web UI + REST API)
```bash
python3 api_server.py 8080
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

### 3. Unified CLI Interface
```bash
# View corporate portfolio overview
python3 cli.py portfolio

# Generate daily executive briefing
python3 cli.py briefing

# Strategic directive with AI CEO
python3 cli.py chat "Audit operational risks and summarize revenue opportunities"
```

### 4. Running Verification Tests
```bash
python3 -m unittest discover tests
```

---

## 🔒 Security & Governance

- Strict read-only verification before database or file mutation.
- Hard spending limits enforced by the Universal Control Kernel.
- Tamper-evident JSONL audit ledger for full traceability.
