# RoboAssistant — Company OS 2.0

> **UNIVERSAL AI CEO + GOVERNED AI WORKFORCE + DESKTOP ROBOT EXECUTION FABRIC**

Autonomous AI Enterprise Operating System providing multi-tenant portfolio management, an autonomous digital workforce, continuous AI CEO executive intelligence, a trusted desktop/browser robot runtime, secret-isolated credential brokerage, commercial sales & voice workers, and cryptographically verified business causality.

---

## 🏛️ The Three-Brain Architecture

```
                    ┌─────────────────────────┐
                    │       AI CEO BRAIN      │
                    │   Strategy & Decisions  │
                    │    Executive Council    │
                    │      Chief of Staff     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │     WORKFORCE BRAIN     │
                    │  Planning & Delegation  │
                    │  Role Blueprints & KPIs │
                    │   Sales & Voice Agents  │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │       ROBOT BRAIN       │
                    │  Perception & Execution │
                    │   Host Fabric / Daemon  │
                    │   Desktop & Browser     │
                    └───────────┬─────────────┘
                                │
                                ▼
                         REAL COMPUTERS
    (Linux Cloud, Windows Workstation, macOS Studio, Android/iOS)
                                │
                ════════════════╪════════════════
                GOVERNANCE & REALITY VERIFICATION
                ════════════════╪════════════════
                                ▼
                     UNIVERSAL CONTROL KERNEL
                                ▼
                         PHYSICAL TRUTH
                                ▼
                     EVIDENCE LEDGER (SHA256)
                                ▼
                    BUSINESS CAUSALITY ENGINE
              (TASK_SUCCESS != BUSINESS_OUTCOME)
```

---

## 🚀 Key Subsystems in Company OS 2.0

### 1. Continuous Executive Cognition (CEO 2.0)
- **16-Stage Executive Operating Loop**: `OBSERVE` → `UNDERSTAND` → `RECONCILE` → `DETECT` → `DIAGNOSE` → `PRIORITIZE` → `MODEL` → `SIMULATE` → `DECIDE` → `DELEGATE` → `EXECUTE` → `VERIFY` → `MEASURE` → `LEARN` → `REPORT` → `REPLAN`.
- **4 Planning Horizons**:
  - `IMMEDIATE`: Real-time anomalies, outages, payment failures
  - `TODAY`: Daily operating missions, night audit, reconciliations
  - `STRATEGIC`: Weekly/monthly goals (direct bookings, churn reduction, contribution margin)
  - `LONG_TERM`: Quarters/years (platform evolution, market expansion)
- **Executive Council**: Independent dynamic executive roles (`CFO`, `COO`, `CTO`, `CMO`, `CRO`, `CHRO`, `CIO_DATA`, `RISK_OFFICER`, `CHIEF_OF_STAFF`) that critique proposals and prevent single-model confirmation bias.
- **AI Chief of Staff**: Coordinates CEO inbox, open decision queues, deadline tracking, and executive dossiers.

### 2. Differentiated AI Workforce & Performance
- **Role Differentiation**: Explicit boundaries separating Executive, Manager, Specialist, Analyst, Operator, Sales Agent, and Desktop Operator.
- **Dynamic Gap Detection**: Synthesizes structured digital employee blueprints when operational capability gaps appear.
- **Performance & Governance**: Tracks verification rate, failure frequency, and costs without expanding authority.

### 3. Universal Host Execution Fabric & Desktop Robot
- **Trusted Host Daemon**: Reports hardware specs, load averages, processes, and network state across Linux, Windows, macOS, Android, and Cloud.
- **Quarantine Boundary**: Immediate host isolation kill-switch blocking all privileged operations during anomalies.
- **Typed ActionContracts**: Governed execution for `SCREEN`, `MOUSE`, `KEYBOARD`, `WINDOWS`, `FILES`, `PROCESS`, `BROWSER`, and `INSTALLER`.
- **Physical Reality Verification**: Computes real SHA-256 digests, process exit codes, and Merkle audit ledger packages for all state mutations.

### 4. Secret Isolation & Session Management
- **Credential Broker**: AI employees only ever receive opaque handles (e.g. `cred_crm_01`), never raw passwords or API keys in prompts or logs.
- **Session Broker & MFA**: When MFA is required, enters `WAITING_FOR_OWNER` rather than attempting security bypass.

### 5. Commercial Sales Workforce & Governed Voice AI
- **AI Sales Workforce**: Ingests leads, scores purchase intent, and strictly enforces commercial discount ceilings (max 10% autonomous discount; requests >10% are escalated to Owner approval).
- **Governed Voice AI**: Telephony turn processing with strict epistemic separation (`CUSTOMER_SAID`, `SYSTEM_FACT`, `AI_INFERENCE`, `PROPOSED_RESPONSE`).

### 6. Continuous Event Engine & Interactive Meetings
- **Enterprise Event Engine**: Real-time emission and severity classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), automatically dispatching missions within authorized bounds.
- **Interactive Executive Operating Meeting**: Cross-department interrogation where CEO challenges unsupported claims and agrees on actionable missions.

### 7. Business Causality Engine
- **Non-Negotiable Invariant**: `TASK_SUCCESS != BUSINESS_OUTCOME`.
- Completing a task or launching a campaign is NOT business success. Revenue is only credited when verified transaction evidence is presented.

---

## 📁 Repository Structure

```
.
├── api_server.py                # Unified REST API & static Web UI server
├── cli.py                       # Unified CLI Cockpit (cycle, council, meeting, telemetry, causality)
├── serve_web.py                 # Standalone web UI preview server
├── core/
│   ├── truth_types.py           # Truth states, planning horizons, operational reasoning
│   ├── ceo_engine.py            # CEO 2.0 continuous executive intelligence engine
│   ├── executive_council.py     # Multi-role executive council challenge loops
│   ├── ceo_chief_of_staff.py    # AI Chief of Staff inbox & dossier coordination
│   ├── workforce_intelligence.py# Dynamic workforce gap detection & blueprints
│   ├── employee_performance.py  # Governance-bounded performance tracking
│   ├── host_fabric.py           # Universal Host Agent & quarantine boundary
│   ├── desktop_robot.py         # Universal Desktop Robot (files, processes, screen)
│   ├── browser_robot.py         # Browser Robot Execution Fabric
│   ├── credential_broker.py     # Secret-isolated credential broker
│   ├── session_broker.py        # Governed session broker & MFA handling
│   ├── application_fabric.py    # Application discovery & automation adapters
│   ├── software_manager.py      # Governed package installation/uninstallation
│   ├── file_intelligence.py     # File taxonomy, checksums & untrusted data isolation
│   ├── sales_workforce.py       # Commercial sales workforce & discount ceilings
│   ├── voice_agent.py           # Epistemically separated Voice AI platform
│   ├── event_engine.py          # Continuous enterprise event engine
│   ├── interactive_meeting.py   # Daily interactive executive operating meeting
│   ├── business_causality.py    # Attribution engine: Task Success vs Business Outcome
│   ├── db.py                    # Multi-tenant SQLite database persistence
│   ├── portfolio.py             # Multi-entity corporate portfolio engine
│   ├── ceo.py & ceo_brain/      # Executive strategic command & cognitive reasoning
│   ├── control_kernel.py        # Universal Control Kernel with evidence verification
│   └── evidence_ledger.py       # Cryptographic Merkle audit ledger
├── tests/                       # 58 verification tests (100% passing)
├── web/                         # Single-page executive cockpit UI
└── storage/                     # SQLite database and audit ledgers
```

---

## ⚡ Getting Started & CLI Usage

### 1. Start the Unified Server (Web UI + REST API)
```bash
python3 api_server.py 8080
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

### 2. Interactive CLI Cockpit
```bash
# Execute CEO Continuous Operating Cycle across all 4 horizons
python3 cli.py cycle

# Convene Executive Council Challenge Loop
python3 cli.py council "Migrate to multi-cloud infrastructure with automatic failover"

# Conduct Interactive Executive Operating Meeting
python3 cli.py meeting

# Inspect Host Node Telemetry & Desktop Robot Status
python3 cli.py telemetry

# View Verified Business Outcome Causality Attribution
python3 cli.py causality

# Strategic natural language command with AI CEO
python3 cli.py chat "Audit operational risks and prioritize revenue opportunities"
```

### 3. Run Automated Validation Matrix
```bash
python3 -m unittest discover tests
```
*Current test suite: 58/58 tests passing.*

---

## 🔒 Constitutional Security Invariants

1. **Capability != Authority**: Having access to a tool or discovery of an executable never grants permission to invoke it without an authorized contract.
2. **Credential Isolation**: Secrets are vaulted; agents only receive opaque handles (`cred_...`).
3. **MFA Integrity**: MFA requirements enter `WAITING_FOR_OWNER` and cannot be bypassed.
4. **Sandbox Path Isolation**: Desktop robot mutations are strictly bounded to designated workspaces.
5. **No Auto-Execution of Untrusted Data**: External downloads and customer content are treated strictly as data.
6. **Task Success != Business Outcome**: Verified commercial transactions are required before recognizing revenue.
