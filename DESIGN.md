# URA / ZONATA — Apple-Grade Design System & Front-End Architecture

**Universal AI Company Operating System**  
*Quiet • Spacious • Fast • Obvious*

---

## 1. Design Vision & Philosophy

URA transforms company operations by providing an AI CEO and a team of C-suite executives and specialists who build, run, and scale businesses for a human owner.

The interface is how a solo founder or company owner watches, steers, approves, and communicates with their autonomous enterprise. The product must feel like a premium Apple operating system:
* **Obvious in 5 Seconds**: A first-time owner must immediately understand what the AI company is doing, why, and what needs their attention without reading documentation.
* **Calm & Spacious**: Generous whitespace, subdued backgrounds, and semantic accents. No flashing alarms, sensory overload, or dense unformatted JSON.
* **Simplicity Wins Every Tie**: If a screen has two ways to represent state, choose the one with fewer elements. Remove before adding.
* **Every Animation Explains Cause & Effect**: Motion is physical and spring-based. It indicates where an element came from, what it is doing, and where it went. Zero gratuitous decoration.
* **Zero Invented Business Data**: All metrics, balances, and customer accounts reflect real records or an explicit, clean empty state.
* **Accessibility Built-in**: Full WCAG 2.2 AA compliance, visible `:focus-visible` rings, ARIA roles, touch targets $\ge 44\text{px}$, and comprehensive reduced-motion support.

---

## 2. Design Tokens & Foundations (`web/design_tokens.css`)

### Color System
Tokens dynamically adapt between Light Mode (default) and Dark Mode (`[data-theme="dark"]`).

| Token | Light Mode | Dark Mode | Role |
| :--- | :--- | :--- | :--- |
| `--bg` | `#F5F5F7` | `#000000` | App canvas background |
| `--surface` | `#FFFFFF` | `#1C1C1E` | Primary elevated card & sheet surface |
| `--surface-2` | `#F2F2F7` | `#2C2C2E` | Secondary container / grouped row |
| `--surface-3` | `#E5E5EA` | `#3A3A3C` | Tertiary / disabled / progress track |
| `--label` | `#1D1D1F` | `#FFFFFF` | Primary high-contrast typography |
| `--label-2` | `#6E6E73` | `#8E8E93` | Secondary metadata and descriptions |
| `--label-3` | `#86868B` | `#636366` | Tertiary timestamps & captions |
| `--separator` | `rgba(0,0,0,0.08)` | `rgba(255,255,255,0.12)` | Subtle hairline borders (0.5px) |
| `--accent` | `#0071E3` | `#0A84FF` | Apple blue primary action |
| `--green` | `#34C759` | `#30D158` | Positive trend, healthy status, profit |
| `--orange` | `#FF9500` | `#FF9F0A` | Needs human attention / medium risk |
| `--red` | `#FF3B30` | `#FF453A` | Destructive action / high risk / errors |
| `--purple` | `#AF52DE` | `#BF5AF2` | Strategy / executive vision / CMO |
| `--teal` | `#30B0C7` | `#40C8E0` | Operations / telemetry / COO |
| `--indigo` | `#5856D6` | `#5E5CE6` | Workforce governance / CHRO |

### Typography Scale
Strict typographic hierarchy using SF Pro / Inter font stack. Tabular numbers (`tabular-nums`) are enforced across all currency, metrics, timestamps, and ledger counts.

* `--t-display`: `40px` / `48px` line-height (Hero metrics like monthly profit)
* `--t-large-title`: `34px` / `41px` (Page titles)
* `--t-title-1`: `28px` / `34px` (Section headers)
* `--t-title-2`: `22px` / `28px` (Card group titles)
* `--t-title-3`: `20px` / `25px` (Sub-headers)
* `--t-headline`: `17px` / `22px` (Semi-bold `600`)
* `--t-body`: `17px` / `22px` (Regular `400`)
* `--t-callout`: `16px` / `21px`
* `--t-subheadline`: `15px` / `20px`
* `--t-footnote`: `13px` / `18px`
* `--t-caption`: `12px` / `16px`
* `--t-caption-2`: `11px` / `13px`

### 4-Point Spacing Grid
* `--s-1`: `4px`
* `--s-2`: `8px`
* `--s-3`: `12px`
* `--s-4`: `16px`
* `--s-5`: `20px`
* `--s-6`: `24px`
* `--s-8`: `32px`
* `--s-10`: `40px`
* `--s-12`: `48px`
* `--s-16`: `64px`

### Concentric Corner Radii
* Inner inputs & tags: `--r-sm` (`6px`) / `--r-md` (`10px`)
* Standard cards & sheets: `--r-lg` (`14px`) / `--r-xl` (`18px`)
* Large containers & modal sheets: `--r-2xl` (`22px`)
* Pills & badges: `--r-full` (`9999px`)

---

## 3. Motion System (`web/motion.js`)

Spring physics provide natural, responsive tactile feedback:
* `Motion.spring.snappy`: `cubic-bezier(0.2, 0.0, 0.0, 1.0)` — 80ms press states (`scale(0.97)`).
* `Motion.spring.smooth`: `cubic-bezier(0.25, 1.0, 0.5, 1.0)` — 240ms modal & drawer slides.
* `Motion.spring.bouncy`: `cubic-bezier(0.34, 1.56, 0.64, 1.0)` — Checkmarks & toast alerts.
* `Motion.animateCountUp(element, endVal, duration)`: Animates tabular figures smoothly on metric change.
* **Reduced Motion Guarantee**: When `prefers-reduced-motion: reduce` is active, animations fall back to zero duration and opacity-only fades.

---

## 4. Squircles & Iconography (`web/app_tile.js`, `web/icons.js`)

* **AppTile (`window.AppTile`)**: Implements Apple's concentric squircle geometry (~22% border-radius curvature) with signature vertical linear gradients and crisp white glyphs for all 9 core entities:
  * `ceo`: Royal blue-to-deep navy
  * `coo`: Cyan-to-teal
  * `cmo`: Purple-to-pink
  * `cto`: Vivid orange-to-amber
  * `cfo`: Emerald-to-green
  * `chro`: Violet-to-indigo
  * `security`: Crimson-to-rose
  * `assistant`: Gradient multi-hue
  * `company`: Classic dark slate
* **Icon (`window.Icon`)**: Clean SVG icons drawn on a 24x24 grid with consistent 1.75px stroke weight, round line-caps, and round joins.

---

## 5. Signature AI Presence (`web/ai_orb.js`)

* **AiOrb (`window.AiOrb`)**: Signature breathing orb conveying autonomous AI state at a glance:
  * `idle`: Gentle breathing pulse (calm presence).
  * `thinking`: Rotating concentric rings (active reasoning/computing).
  * `speech`: Sound-wave ripple oscillations (speaking or generating text).
  * `needs-you`: Warm amber alert glow (decision waiting for human owner).

---

## 6. Primitive Components (`web/components.js`, `web/components.css`)

All components are exposed through `window.UI`:
1. `UI.Button`: Primary filled, Secondary glass, Plain text, Destructive, Icon-only, and loading spinner state.
2. `UI.Input`: Rounded text field with focus ring, leading icon, clear button, and error message.
3. `UI.Card`: Standard card, interactive hover-lift card, and hero highlight card.
4. `UI.Chip`: Status tags with 12% tint background and full-strength text and icons.
5. `UI.Toggle`: Apple-grade physical switch with smooth slider translation.
6. `UI.SegmentedControl`: Segmented tab switcher with active glass background pill.
7. `UI.ListRow`: Grouped table row with leading icon/tile, title, value, and chevron.
8. `UI.Skeleton`: Shimmer placeholder for fast perceived loading.
9. `UI.ProgressBar`: Accessible progress bar with `role="progressbar"`.
10. `UI.EmptyState`: Meaningful, actionable prompt with primary CTA.
11. `UI.showToast`: Floating notification toast with auto-dismiss.
12. `UI.openModal` / `UI.closeModal`: Smooth glass bottom sheet / dialog with `aria-modal="true"`.

---

## 7. App Shell & Navigation (`web/app_shell.js`, `web/app_shell.css`)

* **Sidebar**: 264px glass sidebar in expanded mode, collapsible into a 72px icon rail with tooltips.
* **Company Switcher**: Instant switching between connected enterprises or creation of a new company.
* **Spotlight Command Palette (`⌘K`)**: Fast modal search across all screens, employees, departments, and actions.
* **Inspector Drawer (`window.Inspector`)**: 380px slide-out drawer from the right edge for inspecting any employee, task, deal, or transaction without losing context.
* **Floating "Ask URA" Bar**: Omnipresent floating natural language bar in top-right header with microphone trigger.
* **Mobile Bottom Tab Bar**: Fixed 5-tab bar on viewports $< 768\text{px}$.

---

## 8. The Two Entry Flows (`web/entry_flows.js`)

* **Flow A — New Company**:
  1. Welcome screen with 180px breathing AiOrb.
  2. Idea composer with prompt chips ("Boutique hotel in Goa", "SaaS billing tool", "D2C skincare brand"), voice input, and live clarity meter.
  3. Executive Brief preview sheet.
  4. Smooth hand-off animation.
  5. 8-stage interactive Build Timeline (Brief understood → Plan approved → Website engines → Marketing setup → Finance setup → AI team hired → Final CEO check → Go live).
* **Flow B — Existing Company Intake**:
  1. 5-step stepper: Company Profile → Tools & Stack → Import Data → Team & Access → First Objective.
  2. Popular integration catalog (Stripe, Shopify, Google Workspace, GitHub, WhatsApp, HubSpot).
  3. Live connection verification.
  4. Instant Loophole Analyzer scanning and presenting the top 3 ranked leaks with one-tap "Approve Fix".

---

## 9. 5-Part AI Action Pattern (`web/ai_action_card.js`)

Every autonomous decision and action card follows the strict 5-part pattern:
1. **Intent**: Short, active verb phrase (*"Optimized room pricing for peak weekend dates"*).
2. **Reason**: Plain English causality (*"3 regional competitors raised luxury suite rates by 8%"*).
3. **Progress**: Live state pill with status dot (*Working*, *Done*, *Needs You*).
4. **Result**: Measured impact (*"Average daily rate expanded by 6%. Extra profit: ₹45,000/mo"*).
5. **Control**: On-demand explainability (*"Why?"* button) and undo window (*"Undo (30s)"*).

* **Approval Card (`ApprovalCard`)**: Categorized by risk tier (Low, Medium, High). High-risk actions trigger a confirmation modal detailing irreversible consequences before dispatch.

---

## 10. Core Workspaces & Governance

### CEO Command Center (`web/ceo_command_center.js`)
* Calm morning greeting, date, and single-line status sentence.
* Single hero metric: **This Month's Profit** in `--t-display` with trend arrow and mini SVG sparkline.
* "Needs You" strip containing waiting approvals.
* 6 Executive department cards with status dots and metrics.
* Key Numbers row (Revenue, Margin, Leads, Conversion).
* Live Activity Feed with 5-part Action Cards.

### Department Workspaces (`web/department_workspace.js`)
* Single unified template supporting COO, CMO, CTO, CFO, CHRO, and Security with department header color tints.
* Monthly objective progress bar and department KPIs.
* Work in progress (Running, Waiting, Done today).
* Department AI workforce roster with assigned SOPs and authorized agent tools.
* Department-specific extras: CMO lead funnel, CTO MCP server status, CFO double-entry ledger balance, CHRO governance rule banner.

### AI Workforce & Governance Board (`web/apple_workforce_board.js`)
* Enforces the constitutional rule: **AI Employees hold corporate roles, own SOPs, and operate AI Agents. AI Agents are execution tools and can never control Employees.**
* Filtering by department, instant search, and employee card profiles opening in the Inspector.
* Provisioning modal with SOP assignment and tool authorization boundaries.

### Sales Pipeline Kanban Board (`web/apple_sales_board.js`)
* 5 stages: Inbound & Discovery → Qualified & Scored → Proposal Sent → Negotiation → Won & Booked.
* Top metrics: Total Pipeline Value, Weighted Value, Win Rate, and Average Deal Size in tabular figures.
* Deal cards displaying assigned AI specialists, win probability, and next scheduled follow-up.

### Executive Reports Preview (`web/apple_reports_preview.js`)
* Document Paper Canvas matching exportable PDF document layout.
* Instant switcher: Weekly Executive Briefing, Monthly Financial P&L Statement, Workforce SOP Compliance Audit, Cyber Defense Certificate.
* Tamper-proof SHA-256 Merkle root hash verification and instant print/PDF export.

### Governed Terminal (`web/apple_governed_terminal.js`)
* Fixed permission bar: Governed vs. Root mode, container isolation scope, and active Emergency Kill Switch.
* Human-readable English intent translations above shell commands.
* Glass titlebar with Apple window dots, stream pause/resume controls, and pre-verified directive presets.

### Security Center (`web/apple_security_center.js`)
* 13 concentric defense rings with Apple Fitness-style circular SVG telemetry meters.
* Security Score: 99.4% "Enterprise Fortress".
* SHA-256 Merkle chain verification and zero-leakage DLP egress monitor (0 bytes leaked across 4,200 screened payloads).
* Sovereign Authority Cascade hierarchy.

### Co-Worker AI Assistant (`web/apple_coworker_assistant.js`)
* Central Mode Switch:
  * **Personal Mode**: Free, unrestricted personal assistant for owner's tasks (notes, calendar, travel).
  * **Company Mode**: Governed by AI CEO with constitutional safeguards and ActionCard proposals.
* AiOrb header avatar with dynamic breathing/thinking states.

---

## 11. Accessibility (WCAG 2.2 AA) Audit

* **Contrast**: All text pairs meet or exceed 4.5:1 for normal text and 3:1 for large display titles.
* **Focus Visibility**: All interactive elements utilize `--focus-ring` (2px background gap with 2px solid accent outline).
* **ARIA & Semantics**: Modals use `role="dialog"` and `aria-modal="true"`; tabs use `role="tablist"`; progress bars use `role="progressbar"`; icon buttons include explicit `aria-label`.
* **Reduced Motion**: Full compatibility with `@media (prefers-reduced-motion: reduce)`.
