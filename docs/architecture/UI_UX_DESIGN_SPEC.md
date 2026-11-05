# RoboAssistant — Universal AI Workforce & Company Operating System
## Enterprise SaaS UI, UX & Frontend Design Specification

**Target Product:** RoboAssistant 1.0.0-GA / ROBO-GA-1.0.0-PROD  
**Design Paradigm:** Autonomous Business OS / Universal AI Workforce Platform  
**Target Environments:** Web (Desktop & Tablet) + Mobile Responsive View (Native Companion)  
**Design Reference:** Inspired by modern enterprise systems (Notion, Linear, Salesforce, Stripe, HubSpot)  

---

### 1. Executive Summary & Design Principles

The RoboAssistant UI/UX is built specifically for **Company Owners and Executives** rather than developers. The primary design goal is:

> *"The owner manages business outcomes, strategic objectives, and workforce boundaries — not low-level software plumbing or raw LLM prompts."*

#### Core UX Rules:
1. **Show Only What's Needed (Minimalist Cognitive Load):** Critical operational metrics (Revenue, Active Employees, Running Missions, System Health) are visible at a glance; deep audit ledgers, ELF/PE binary checks, and Merkle proofs remain accessible under **Reports & Truth** without cluttering daily workflows.
2. **Predictable Strategic Interaction:** High-level intent is expressed conversationally through **Chat & Command** ("Ask, Command, or Delegate"), which decomposes requests into explicit department assignments and milestone steppers (`Analyze` $\rightarrow$ `Plan` $\rightarrow$ `Assign` $\rightarrow$ `Execute` $\rightarrow$ `Verify`).
3. **Strict Authority Visibility:** Every AI employee card explicitly displays its **Authority Level**, current monthly cost, token usage, and active missions.
4. **Instant Multi-Entity Context Switching:** Switch between hospitality properties, precision manufacturing plants, SaaS ventures, or personal operations in one click.
5. **Universal Dark & Light Theme Support:** Premium dark theme by default (deep space slate `#090E1A` with neon cyan `#06B6D4`, royal blue `#3B82F6`, and emerald `#10B981`), fully convertible to crisp high-contrast light mode.

---

### 2. Design Tokens & Color Palette

```
┌─────────────────────────────────────────────────────────────┐
│                      COLOR PALETTE                          │
├───────────────────┬─────────────────────────────────────────┤
│ Background Body   │ #090E1A (Dark) / #F8FAFC (Light)        │
│ Sidebar / Headers │ #0E1526 (Dark) / #FFFFFF (Light)        │
│ Card Surfaces     │ #141C2E (Dark) / #FFFFFF (Light)        │
│ Card Hover State  │ #1B263E (Dark) / #F1F5F9 (Light)        │
│ Border Color      │ #1E293B (Dark) / #E2E8F0 (Light)        │
│ Accent Primary    │ #3B82F6 (Blue 500) • #2563EB (Hover)    │
│ Accent Secondary  │ #06B6D4 (Cyan 500)                      │
│ Accent Success    │ #10B981 (Emerald 500)                   │
│ Accent Purple     │ #8B5CF6 (Violet 500)                    │
│ Accent Warning    │ #F59E0B (Amber 500)                     │
│ Accent Danger     │ #F43F5E (Rose 500)                      │
│ Text Primary      │ #F8FAFC (Dark) / #0F172A (Light)        │
│ Text Secondary    │ #94A3B8 (Dark) / #475569 (Light)        │
│ Text Muted        │ #64748B (Dark) / #94A3B8 (Light)        │
└───────────────────┴─────────────────────────────────────────┘
```

#### Typography Stack:
- **Primary Font:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif`
- **Monospace Font:** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`
- **Scale:** H1 (24px, -0.02em tracking), H2 (18px), H3 (15px), Body (13.5px), Captions (11px).

---

### 3. Screen Breakdown & Functional Architecture

#### Screen 1: Main Dashboard (Owner View)
- **Greeting Banner:** Personalized time-aware greeting ("Good Evening, Ravi Sharma / Your AI workforce is operating smoothly.").
- **Top 4 KPI Metric Cards:**
  1. *Total Revenue:* `₹ 4,82,560` (`+12.5% vs last week`)
  2. *Active Employees:* `12` (`+2 new provisioned`)
  3. *Running Missions:* `8` (`● On track`)
  4. *System Health:* `99.7%` (`Excellent / 0 policy escapes`)
- **Business Performance Interactive Chart:** Smooth Bézier curves charting `Revenue (₹)` vs `Bookings` across 7D, 30D, 90D, and 1Y timeframes.
- **Quick Actions Grid:** Direct access to `Create Mission`, `Add Employee`, `Manage Hosts`, and `View Reports`.
- **Active AI Employees Widget:** Real-time running mission counts for Marketing Director, Sales Manager, and Finance Agent with one-click drill-down.

#### Screen 2: Chat & Command Interface ("Ask, Command, or Delegate")
- **Executive Message Thread:**
  - Owner enters high-level business goal: *"Increase hotel occupancy to 85% next month while maintaining ADR above ₹7,500."*
  - AI CEO decomposes into strategic steps:
    1. *Analyze market data & competitor pricing*
    2. *Optimize room rates & distribution inventory*
    3. *Launch targeted marketing campaigns*
    4. *Engage corporate and group banquet sales*
    5. *Monitor daily performance and adjust*
  - Dynamic Specialist Assignment badges (`Revenue Manager`, `Marketing Director`, `Sales Manager`, `Operations Manager`).
  - Interactive Orchestration Stepper: `Analyze (Done)` $\rightarrow$ `Plan (Done)` $\rightarrow$ `Assign (Done)` $\rightarrow$ `Execute (In Progress)` $\rightarrow$ `Verify`.
- **Command Suggestions Chips:** Instant pre-configured prompts (`Prefer free tools`, `Run night-audit`, `Cap budget to ₹50,000`, `Investigate Cell-3 CNC bottleneck`).

#### Screen 3: AI Workforce (Employee Directory)
- **Directory Filter Bar:** Real-time text search, department dropdown (`Executive`, `Marketing`, `Sales`, `Finance`, `Operations`, `HR`, `Research`, `Support`), and status filter (`Online`, `Idle`, `Offline`).
- **Specialist Agent Cards:**
  - Dynamic gradient role avatars and badges.
  - Active mission count indicators.
  - Status indicators with glowing pulse dots.
  - Click-through to detailed employee modal.

#### Screen 4: Employee Detail & Customization Modal
- **Tabbed Interface:** `Overview`, `Permissions`, `Data Sources`, `Performance`, `Logs`, `Settings`.
- **Contract Boundary Card:**
  - Manager hierarchy (reports to `AI CEO`).
  - Authority Ceiling (`MEDIUM: Idempotent + Sandbox`).
  - Token Usage progress bar (`4,280 / 10,000`).
  - Monthly Incurred Cost (`₹ 3,240 / ₹ 10,000`).
- **Current Missions Queue:** Status badges and expected completion times.

#### Screen 5: Settings Panel (Global & Per-Agent)
- **Subnav Categories:** General, Organization, AI Employees, Data Sources, Tokens & Usage, Security, Notifications, Billing, Advanced.
- **Per-Agent Configuration Controls:**
  - *AI Aggressiveness Slider:* Interactive 10% to 100% dial.
  - *Max Operational Budget:* Monthly spend ceiling in INR (`₹ 50,000`).
  - *Token Consumption Limits:* Bounded daily or monthly allowances.
  - *Permitted Data Access Toggles:* Checkbox access control (`AI Website`, `Social Media`, `Market Data`).
  - *Policy Toggles:* Auto-approve low risk actions, allow creative generation, track reality ROI.

#### Screen 6: Hosts & Devices (Execution Environments)
- **Connected Fleet Table:**
  - *Windows Workstation:* Windows 11, Primary Host, 6 agents, 32% load.
  - *macOS Studio:* macOS 14 Sonoma, 3 agents, 16% load.
  - *Linux Cloud Node:* Ubuntu 22.04 LTS, 4 agents, 45% load.
  - *Android Phone:* Pixel 7, 2 agents, 21% load.
  - *iOS Remote Session:* iPhone 15 Pro, 1 agent, 12% load.
- Real-time latency indicators and CPU load progress bars.

#### Screen 7: Missions & Reality Verification
- **Missions Table:** End-to-end status tracking from `DISCOVER` to `VERIFIED`.
- Links to physical output files and SHA-256 evidence digests.

#### Screen 8: Mobile Responsive Companion
- A built-in smartphone frame mockup simulating the native mobile experience with bottom tab bar (`Home`, `Chat`, `Team`, `More`).
