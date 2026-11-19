# UI_UX_SPECIFICATION — Factory Command Centre and Employee Agent Marketplace

> Based on the owner's stated design language (Apple-style enterprise UI; vertical sidebar collapsing to an icon rail; drawer + tab bar on phones; every control must work; plain-language suggestions beside settings; ONE floating assistant). The existing front end was **not inspected**; component names below are semantic and map onto whatever design system exists. **Do not add new top-level menu items** beyond one optional entry; extend the existing *Workforce → Agents* and *Approvals* screens.

## 1. Information architecture

| Surface | Where it lives | Audience |
|---|---|---|
| **Agent Marketplace** | *Workforce → Agents* screen, tab **Marketplace** | Employees (AI employees via their human owner/assistant UI), department heads, owner |
| My requests | *Agents* tab **My requests** | Requesters |
| Registry | *Agents* tab **Registry** (existing agents list upgraded) | Everyone with read |
| **Factory Command Centre** | *Technology (CTO)* section → **Agent Factory** | CTO, CHRO, AI CEO view, owner, security approver |
| Release approvals | Existing **Approvals** queue, new item type "Agent release" | Approvers |
| Assistant | The single floating assistant (`@Factory` shortcuts) | Everyone; **read-only observer** of factory objects |

## 2. Employee Agent Marketplace — pages

### M1 Marketplace home
Search + category chips (19 categories) + cards: name, one-line purpose, risk badge (R0–R3 in plain words: "Reads only", "Reads the web", "Can change things", "High impact"), certification badge (✔ Certified v1.2 · date), rating, "Use" / "Request a copy". Section "Your team's agents". Empty state: "Describe what you need" button.

### M2 New request (one page, progressive)
1. **What do you need?** large text box + 4 example prompts; mode picker as plain choices: *One agent · Several agents · A whole team · Change an existing agent · Bring an open-source agent*.
2. Optional: **Start from a template** (picker with preview).
3. **Details (optional):** who it reports to, tools/data it needs (suggestions pre-filled), budget cap, "release together as a team / separately".
4. **Estimate panel (live after analysis):** agents count, expected time, expected cost, quota impact, risk level, *what approvals will be needed* ("AI CEO", "You") — plain language. 
5. **Submit.** If clarification is needed, a short question card appears (≤5 questions, each with suggested answers).
*Suggestion rule from the owner's design:* every field shows a one-line recommendation; "Use suggestion" fills it.

### M3 Request detail (progress)
Timeline of the 13 stages collapsed into 7 human steps: *Understanding → Designing → Building → Testing → Safety review → Approval → Ready*. For batches: a grid of agent cards with per-agent status and which one blocks which (dependency lines). Live activity feed (SSE). Buttons: Cancel, Retry failed agent, Ask a question (opens the assistant with context). Errors in plain language with next actions.

### M4 Results & certification view
"Test summary" (pass rate bars per area), "Safety review" (counts of issues by severity, all critical/high must be zero to proceed), "What this agent can do / cannot do" (permissions in plain words, with network hosts and tools), "Cost & speed", certificate (ID, date, expiry), download evidence bundle (for managers).

### M5 Agent detail
Overview (role, owner, assignee, version, channel), Capabilities & permissions (read-only inspection), Versions (diff + metrics), Activity & health (SLOs, incidents), Feedback form (stars + category + comment), Actions: Request upgrade, Roll back (authorised), Suspend (authorised), Retire (authorised).

### M6 Assign / use
Assign to an employee/department/team/assistant; shows what the assignee will be able to do; "agents can never use employees" is stated in the help text.

## 3. Factory Command Centre — pages

| # | Page | Content |
|---|---|---|
| C1 | Overview | Active jobs, queue depth/oldest age, success/failure rate (7 d), spend vs budget, sandbox availability, open incidents, pending approvals; **"System honesty bar":** which tiers are enabled (T0/T1/T2, Temporal vs DB-queue) |
| C2 | Jobs & batches | Table with filters; click → **Job inspector** |
| C3 | Job inspector | Manifest, DAG view (waves, blocked items), stage log per item, builds/attempts, cost, evidence ids, kill/cancel (authorised) |
| C4 | Architecture view | Selected request: agent roles, workflow type, contracts, delegation tree, permission diff |
| C5 | Template library | Browse/search, versions, compat, status; submit/review/publish flows (authorised); promote-from-agent |
| C6 | Build history | Per agent version builds, artifacts, scans |
| C7 | QA results | Per suite results, case drill-down, datasets/versions, independence proof (evaluator ≠ builder), held-out share |
| C8 | Security findings | Open findings by severity; waive (security approver); trends |
| C9 | Certifications | Gate table with required vs observed; bundle download; expiry |
| C10 | Release approvals | Approver view: certification summary, **permission diff vs current**, risk, tests; approve/reject (self-approval disabled with explanation) |
| C11 | Registry | Search/filter/categorise; capability inspection; assignments; version history |
| C12 | Runtime monitoring | Per agent/team health, latency, success, tool failures, tokens, cost, feedback, incidents; suspend/rollback |
| C13 | Resources & quotas | Worker pools, per-tenant quotas, model budgets, sandbox usage |
| C14 | Audit evidence | Search ledger entries for factory subjects; verify Merkle proof button; export |
| C15 | Policy | Read-only view of gate policy, approval matrix, autonomy mapping (changes require AI CEO + owner flow elsewhere) |

## 4. User journeys

| Journey | Steps |
|---|---|
| **J1 Employee requests one agent** | M1 → M2 (describe) → live estimate → submit → M3 progress → notification "Ready" → M4 review → Use/assign (M6) |
| **J2 CMO requests a 7-agent team** | M2 mode "A whole team" → analysis shows 7 agent cards + dependency preview → approve design (if R2+) → M3 grid → team QA → approval (AI CEO; owner under "Ask me first") → atomic publish → assigned to Marketing |
| **J3 Agent fails QA** | M3 shows "Safety review found 2 issues" → plain explanation + the failing scenario → "Request a fixed version" creates a new version automatically with the finding as context → re-test |
| **J4 Approver reviews release** | Approvals queue → "Agent release" card → C10 detail: gate table, permission diff, 5 sample transcripts → Approve/Reject with reason |
| **J5 Degradation** | Monitoring alert → C12 → "Roll back to v1.1" (one click, authorised) → evidence → owner notified |
| **J6 Co-worker assistant** | User says "build me an agent that…" → assistant opens M2 prefilled; for company scope asks AI CEO permission; user observes progress in the assistant window (read-only) |

## 5. UX rules

1. One primary action per page; plain language first, technical detail behind "Details".
2. Never show a green state without evidence behind it; unknown = grey "Not monitored yet".
3. Risk is always visible and explained; R2/R3 actions use confirmation with typed reason.
4. All destructive actions (retire, kill) use the multi-step permission pattern the owner specified for company deletion (explain → confirm → type name).
5. Every setting that influences the factory (autonomy level, budget cap, approval rules) shows its suggestion and effect ("Under 'Balanced', agents that can change things need your approval").
6. Accessibility: keyboard, reduced motion, high contrast, RTL, translations for menus/headings as in the owner's existing settings; numbers/currency follow the company locale.
7. Mobile: cards stack; Command Centre is read-mostly on phones; approvals are mobile-friendly.
8. No new dashboard clutter: Command Centre has 6 primary tiles; deeper pages are reachable but not on the landing view.

## 6. Front-end implementation notes (for OpenCode)

Use the existing component library and routing; data via the Factory API only (no direct DB); SSE for progress with polling fallback; optimistic UI never for approvals; contract tests against the OpenAPI schema; empty/error/loading states for every page; feature flag `agent_factory_ui` per tenant.
