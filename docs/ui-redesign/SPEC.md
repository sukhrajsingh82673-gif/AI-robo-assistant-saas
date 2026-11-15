# URA front-end redesign: master prompt for opencode

You are redesigning the front end of **URA**, an AI company operating system, in the existing codebase. A finished, working design prototype is in `docs/ui-redesign/prototype.html` (one HTML file, no build step). Open it in a browser and use it as the visual and behavioural reference. This document is the specification. Where they disagree, this document wins.

## 0. Rules of engagement

1. **Do not guess the stack.** Inspect the repo first. Use the framework, router, state library, styling approach and component conventions that already exist. Do not introduce a new framework.
2. **Do not paste the prototype into the app.** It is a reference. Rebuild each part as proper components in the existing stack. Search the prototype by the function names given below to see exact behaviour.
3. **Reskin and reorganise, do not delete.** Keep all existing business logic, API calls, auth and data models. If an existing feature has no home in the new menu, put it on the nearest screen and list it in `docs/ui-redesign/AUDIT.md`.
4. **Do not change backend contracts.** If the UI needs data the API does not provide, use a typed adapter with sample data behind one switch (`USE_SAMPLE_DATA`) and list it in `docs/ui-redesign/STUBS.md`.
5. **No dead controls.** Every icon, button, menu item and setting must do something real. If the backend is not ready, wire it to the sample-data adapter and show a clear message such as "Sample data. Not connected yet." Never leave a control that does nothing.
6. **Work in phases** (section 12). After each phase: run the type check, lint, build and tests, fix everything, commit with a clear message, and write a 5-line summary. Do not start the next phase with a failing build.
7. **Decide, do not ask.** Make the most reasonable choice, write it in `docs/ui-redesign/DECISIONS.md`, and continue. The only checkpoint is after Phase 0.
8. At the end of Phase 1, add a short "UI rules" section to `AGENTS.md` in the repo root containing the rules in sections 3, 8 and 11, so future sessions keep them.

## 1. What URA is (so the UI makes sense)

- The owner gives URA a company. An **AI CEO** reads everything and delegates to department heads: **COO** (operations), **CMO** (marketing and sales), **CTO** (technology), **CFO** (finance), **CHRO** (people: AI employees and agents).
- **New company flow:** the owner enters a name and a long free-text brief. The CEO reads it and delegates. A build phase of about 1 to 3 days follows, then operations.
- **Existing company flow:** a structured form (website, booking engine, sales engine, CRM, other tools). URA connects them, studies the company and competitors, finds where profit leaks, splits the work by department, then operates.
- **AI employees** are task-specific and run under SOPs and KRA/KPI. **Agents** are tools. Rule: employees may use agents, agents may never use employees. If no suitable agent exists, an employee builds one from templates, or finds an open-source agent (for example on GitHub) and installs it through the app's terminal, after approval.
- **Co-worker** is the owner's "real world Jarvis": browser and desktop automation. Free for personal tasks. Needs the AI CEO's permission to touch company work.
- The app has a **Terminal**. URA is responsible for the **security** of every company. The owner receives profit reports and PDFs by email and can ask the CEO anything.
- Users are enterprises with **many companies in many countries**, so currency, time zone, language, date and number formats must follow the user's settings and the active company.

## 2. Phase 0: audit (no code changes yet)

Write `docs/ui-redesign/AUDIT.md` containing:
- Stack summary (framework, router, state, styling, i18n, build, test tools).
- Table of every existing screen/route/component and where it maps in the new menu (section 5).
- List of existing icons/buttons that currently do nothing or are visually broken (for example transparent icons in the top bar).
- List of existing settings and where each lands in the new settings model (section 8).
- Gaps: what the new design needs that the codebase lacks.
- A phased plan with file-level detail.

Then **stop and show me the plan** before editing code.

## 3. Design language (Apple-style)

Principles: clarity, deference (content first, chrome quiet), depth (layers, soft shadows, blur). One accent colour. Sentence case. Plain words a new user understands. Touch targets at least 44px on phones. Motion answers an action; nothing animates on its own except the live status dot. No emoji as icons. One consistent stroke icon set (about 1.6px stroke, rounded caps), for example Lucide; the prototype has an inline set you can copy paths from (`icon()` function).

**Tokens** (implement as CSS variables or your styling system's equivalent; light values then dark values):

| Token | Light | Dark |
|---|---|---|
| bg | #f5f5f7 | #000000 |
| surface | #ffffff | #1c1c1e |
| surface-2 | #f9f9fb | #252528 |
| glass (sidebar, top bar) | rgba(250,250,252,.76) | rgba(34,34,37,.74) |
| fg | #1d1d1f | #f5f5f7 |
| fg-2 | #515154 | #c7c7cc |
| fg-3 | #6e6e73 | #98989f |
| line | rgba(0,0,0,.12) | rgba(255,255,255,.16) |
| fill (controls) | rgba(120,120,128,.13) | rgba(120,120,128,.26) |
| good / warn / bad (text) | #1d7f37 / #8f5200 / #c8102e | #32d74b / #ffb340 / #ff6961 |
| good / warn / bad (tint bg) | rgba(52,199,89,.17) / rgba(255,159,10,.18) / rgba(255,59,48,.12) | rgba(48,209,88,.18) / rgba(255,159,10,.2) / rgba(255,69,58,.2) |

Accent options (light, dark, text-on-accent): blue #0071e3 / #0a84ff / white (default), indigo #5856d6 / #7d7aff / white, purple #9d3fc4 / #bf5af2 / white, pink #d6246e / #ff5c8a / white, orange #b85400 / #ff9f0a / black, green #1a7f37 / #30d158 / black, graphite #48484d / #aeaeb2 / black. `accent-soft` is the accent at 11% (light) or 20% (dark) opacity.

Shape and type: cards radius 18px with a 1px hairline and a very soft shadow; sidebar radius 22px; buttons are pills (height 34px); segmented controls (radius 10px) and iOS switches (51×31). Font stack: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", Inter, "Noto Sans Devanagari", "Noto Sans Gurmukhi", "Noto Sans Arabic", "Segoe UI", Roboto, sans-serif`. Mono: `ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas`. Body 14px (13px compact), page title 30px bold with -0.022em tracking, section titles 16 to 18px semibold. Use `font-variant-numeric: tabular-nums` for numbers.

Colour must always come from tokens. Dark mode is a designed palette, not an inversion. All text must meet 4.5:1 contrast.

## 4. App shell

- **Layout:** a floating, translucent sidebar (17rem wide, or 5rem "icons only" rail) beside a scrolling workspace with a floating top bar. Use CSS logical properties everywhere (`margin-inline-start`, `inset-inline-end`, and so on) so right-to-left works.
- **Sidebar:** company switcher at the top (company chip with initials, name, "Country, phase"; opens a menu of all companies with "Add company" and "See all companies"). Then four groups of menu items (section 5). Settings sits at the bottom. The nav list scrolls with a soft fade at the bottom; at 900px height all 17 items must fit without scrolling. Rail mode shows icons with tooltips. Each item has an icon, a label and an optional badge (Approvals shows the waiting count).
- **Top bar** (every control must work and have an `aria-label`): menu toggle (collapse/expand, drawer on phones); breadcrumb (company, then page); search field that opens the **command palette** (Ctrl/Cmd+K) listing pages, companies, actions, settings, employees and agents with keyboard navigation; **CEO status pill** (opens a popover with agents running, tasks, "Watching all of <company>"); **company clock** showing the company's local time in the user's time and clock settings; **notifications bell** (popover list, unread dots, mark as read, click opens the related page, respects notification settings and quiet hours); **help** (search, "How URA works", keyboard shortcuts, link to Settings); **profile** (name and email, theme switcher, link to Settings, sign out with an in-page confirmation).
- **Phones (under about 860px):** the sidebar becomes a drawer; a bottom tab bar shows Overview, Ask CEO, Approvals, Staff and More. No horizontal page scroll at 390px. Sheets become bottom sheets. KPI tiles show 2 across.
- **Overlays:** popovers (anchored, close on outside click and Escape), sheets (centered on desktop, bottom on phones, focus trapped, Escape closes), toasts (bottom, `aria-live`, with Undo where it makes sense), and a command palette.
- **Hidden pages:** if a screen is hidden (see Settings > Menu and team, or Terminal off), opening it by link or search shows a "This screen is hidden" card with "Show it again" and "Back to Overview", not a silent redirect (`pgLocked` in the prototype).
- Routing uses plain, shareable URLs for every screen and every settings category. Back and forward must work.

## 5. Menu (17 screens, in this order)

| Group | Item | What it is |
|---|---|---|
| Workspace | Overview | Daily summary for the active company |
| Workspace | Ask CEO | Chat with the AI CEO |
| Workspace | Approvals | Decisions the owner must make (badge) |
| Departments | Operations (COO) | Operations tasks, throughput, SOPs |
| Departments | Marketing & Sales (CMO) | Campaigns and the lead pipeline |
| Departments | Technology (CTO) | Websites, systems, builds, integrations health |
| Departments | Finance (CFO) | Revenue, costs, profit, invoices |
| Departments | People (CHRO) | AI employees and agents overview, hiring |
| Workforce | AI Employees | Roster, KRA/KPI, SOPs, hire |
| Workforce | Agents | Installed agents, templates, install |
| Workforce | Co-worker | The Jarvis assistant |
| System | Tools & Integrations | Connected systems, MCPs, APIs |
| System | Security | Score, findings, scan |
| System | Terminal | Command line |
| System | Reports | Scheduled and on-demand reports |
| System | Companies | All companies, add or connect one |
| (bottom) | Settings | Section 8 |

Reference: `PAGES`, `NAV`, `pgOverview`, `pgCeo`, `pgApprovals`, `pgDept`, `pgEmployees`, `pgAgents`, `pgCoworker`, `pgTools`, `pgSecurity`, `pgTerminal`, `pgReports`, `pgCompanies`, `pgPrefs`.

## 6. Screen requirements (short form)

- **Overview:** time-of-day greeting; subtitle with company, country and phase; actions "Delegate task" and "Ask CEO". For an **operating** company: four KPI tiles (revenue this month, net profit, open leads, agents running) with sparklines; "Decisions waiting" with inline Approve/Decline; net profit by week chart (4, 12, 26 weeks; Chart/Table toggle; tooltips); department status; activity feed. For a company **being built**: build progress and the 5 build steps. For a company **being studied** (existing flow): the 5 steps (connect systems, study company and competitors, find profit leaks, split work, start operating) and the leaks found. Charts use token colours, one axis, a legend when there are two or more series, and a table alternative.
- **Ask CEO:** chat with suggested prompts, attach, send. Replies use real company data and the user's currency and formats. Some replies delegate and create a task. Honour the "How the CEO answers" setting (brief or detailed). In the prototype replies are scripted (`ceoReply`); replace with the real CEO agent call behind the same function signature.
- **Approvals:** tabs Waiting and History. Cards show title, detail, from-department, amount (in the display currency), risk pill (low, medium, high), time, and Approve and Decline. Items the CEO is allowed to handle alone are not shown as waiting; show them in History as "Handled by the CEO". The sidebar badge and the bell use the same list.
- **Departments:** head status, KPIs, tasks, team, an "Instruct" box that creates a task. CMO has the lead pipeline (New, Contacted, Negotiating, Won) with Advance. CFO shows costs against the payment limit.
- **AI Employees:** roster, status, KRA and KPI bars, SOP steps, agents each employee uses, pause and resume, "Hire AI employee" sheet. Show the rule banner "Employees can use agents. Agents never use employees."
- **Agents:** list with source (template, open-source, in-house), status, "Install agent" sheet (template or GitHub URL). Open-source installs need approval and write a line to the Terminal log.
- **Co-worker:** segmented Personal | Company. Personal runs freely. Company mode is locked until the CEO grants permission; "Ask CEO for permission" creates an approval of kind `cowork`. Show recent actions.
- **Tools & Integrations:** catalog by category (website, booking, sales/CRM, payments, messaging, MCP, API, browser tools). Connect and disconnect with a short flow, last-sync time, "Built by agents" badge, "Released after the task" note for browser-used tools.
- **Security:** score ring computed as in section 9, checks list, findings with Resolve, "Run scan" with progress, writes to activity and the Terminal.
- **Terminal:** commands `help status companies use <name> agents approvals scan (or security scan) whoami theme currency lang accent ura agent search|install clear`; history with up/down arrows; the output reflects real state. Role-gated by the "Show the Terminal" setting.
- **Reports:** list with Generate now, Preview, Email me. The schedule line ("Next report: ...") comes from Settings > Reports and uses the user's date and time formats. Include profit, sales and security sections according to settings.
- **Companies:** cards (name, country, currency, phase, health), Switch, "Create new company" (name + long brief + country, the CEO shows which departments get what), "Connect existing company" (website, booking engine, sales engine, CRM, other tools), and a world clock of company local times.

## 7. Data and formatting rules (multi-company, multi-country)

- Every company has: id, name, country code, currency, time zone, default language, data region, phase (building, studying, operating), industry.
- The active company drives: displayed currency (when "Each company's own currency" is chosen), number style (auto), the company clock, and the suggested language and data region.
- Route **all** formatting through one small module and ban ad-hoc `toLocaleString`, `toFixed` for money, or hard-coded symbols. Required helpers: `t(key)`, `formatMoney(amountUSD, {compact})`, `formatNumber`, `formatDate`, `formatTime`, `timeAgo`. Reference: `money`, `nloc`, `fmtDate`, `ago`, `dparts`.
- Money is stored in USD (or the company's currency plus a rate) and converted for display. Replace the sample `RATES` with a real daily FX source behind the same function; show "Rates are samples" until then.
- Number style "Automatic" follows language plus the viewed company's country (English + India gives en-IN with lakh and crore; + UK gives en-GB; + UAE gives en-AE; otherwise en-US).
- Date style options: automatic, day first, month first, year first. Clock: automatic, 12-hour, 24-hour. Time zone: automatic (device) or a fixed zone.

## 8. Settings (schema-driven, every setting has a suggestion)

Build Settings from **one registry** (see `SET` in the prototype). Each item: `key`, `label`, `type` (segmented, switch, select, swatch, email), `options`, `hint` (what it changes, in plain words), `suggest(context) -> { value, why }`. The UI renders the same way for every item:
- A control on the right, the label and hint on the left.
- Under it, a suggestion box. Green with a check when the value matches ("Matches our suggestion. <why>"). Blue when it differs ("Suggested: <value>. <why> Use this"). A small dot marks the suggested option inside segmented controls.
- Each category header has a card: "New here? Read the blue tip under each setting." with **Use all N suggestions** (or "All suggestions applied"). Applying shows a toast.
- Suggestions can depend on context (the active company's country, language, device settings).
- Settings hub lists the categories with an icon, name and one-line blurb. On phones it is a list that drills into a category with a Back button.
- Persist settings per user through the existing user-preferences API (fall back to local storage). Apply instantly with no page reload.

Categories, keys, defaults and the suggestion logic:

**Appearance**
- `theme` (system | light | dark), default system; suggest system.
- `accent` (7 swatches), default blue; suggest blue.
- `density` (comfortable | compact), default comfortable; suggest comfortable, mention compact for many companies.
- `sidebar` (full | rail), default full; suggest full for new users.
- `textSize` (90 | 100 | 115 | 130 percent), default 100.
- `reduceMotion` (switch), default follows the OS; suggest the OS value.
- `contrast` (switch, higher contrast), default off.

**Language and region**
- `lang` (en, hi, pa, ar, es, fr), suggest the active company's language, else the device language. Arabic sets `dir="rtl"`.
- `tz` (automatic or a zone), suggest automatic.
- `hour` (auto | 12 | 24), suggest auto.
- `dateFmt` (auto | dmy | mdy | iso), suggest iso when companies span countries.
- `numFmt` (auto | en-US | en-IN | de-DE | fr-FR), suggest auto.
- `currency` (company | USD | INR | EUR | GBP | AED | JPY), suggest company.

**AI CEO and autonomy**
- `autonomy` (ask | balanced | auto), default balanced.
- `payLimit` (0 | 250 | 1000 | 5000 | 25000 USD), default 1000.
- `hours` (247 | biz | night), default 247, shown in the status pill.
- `tone` (brief | detailed), default brief, changes CEO replies.

**Notifications**
- `n_approvals`, `n_security`, `n_reports`, `n_builds` (switches, default on), `quiet` (hides the red badge 22:00 to 07:00 in the user's time zone; items still wait in the bell). Suggest quiet on when companies span time zones.

**Reports**
- `repFreq` (daily | weekly | monthly), `repEmail`, `repProfit`, `repSales`, `repSec` (switches). Defaults: weekly, owner email, profit on, sales on, security off.

**Security and privacy**
- `session` (15m | 1h | 8h | never, suggest 1h), `audit` (30 | 90 | 365 days, suggest 365), `region` (data location, suggest the active company's region), `terminalOn` (default on).
- Two-step sign-in is **not** a local preference. Since Stage 7 it is a real TOTP enrollment per account (`/api/auth/two-step/*`), shown from server state on the Security screen and set up in the company-deletion identity step. Do not add a local switch for it.

**Menu and team**
- Show or hide each menu screen (Settings and Overview cannot be hidden). Invite, edit role and remove teammates (owner, admin, member, viewer) through sheets.

## 9. How settings must change the rest of the app (connected behaviour)

Implement these as real, tested rules, not per-screen hacks:

1. **Appearance:** theme, accent, density, text size, sidebar style, reduced motion and contrast apply to every screen through root attributes and CSS variables. Theme "system" follows the OS and any host theme.
2. **Language:** all UI strings come from translation files (`en, hi, pa, ar, es, fr`), falling back to English per key. Arabic flips the whole layout. Use `unicode-bidi: plaintext` for mixed text. Ship translations for the menu, group names, page titles, greetings and common buttons first; then widen.
3. **Formats:** currency, number, date, time and time zone settings change every amount, date and time on every screen.
4. **Approvals rule** (`needsOwner`): an item needs the owner when its risk level is above the autonomy level (ask = -1, balanced = 0, auto = 1, with low = 0, medium = 1, high = 2), or its amount is above `payLimit`, or its kind is `cowork`. The Approvals list, the sidebar badge, the Overview "Decisions waiting" and the bell all use this one function. In the sample data: ask me first gives 6 waiting, balanced 4, mostly autonomous 3.
5. **Notifications:** the bell and badge show only enabled categories. Quiet hours hide the badge.
6. **Reports:** the Reports screen and its "Next report" line use frequency, recipient and included sections.
7. **Security score** (`secScore`): 58 + 14 only when the server reports this account's two-step enrollment + session (15m +8, 1h +6, 8h +2, never -8) + audit retention (30 days +1, 90 days +4, 365 days +7) - 6 for each open finding + 3 if the data region matches the company's region, clamped 8 to 100. The Security screen updates live when these settings change; two-step comes from `/api/auth/two-step/status`, never from a local toggle.
8. **Terminal:** off hides it from the menu and the palette, and opening it directly shows the "hidden" card.
9. **Menu and team:** hidden screens disappear from the menu, tabs and palette.
10. **CEO tone and hours:** `tone` changes CEO replies; `hours` changes the status pill text.

## 10. Accessibility and quality bar

- Real `<button>`, `<a>`, `<input>` and `<label>` elements. Icon-only buttons have `aria-label`. Switches use `role="switch"` with `aria-checked`. Dialogs use `role="dialog"` and `aria-modal`, trap focus and restore it on close. Visible keyboard focus everywhere. `aria-current="page"` on the active menu item.
- Respect `prefers-reduced-motion`. Honour the in-app setting too.
- Layouts work from 360px to 1920px. No horizontal scroll. Tables and wide content scroll inside their own container.
- Empty states say what will appear and how to add the first item. Errors say what went wrong and how to fix it. No lorem ipsum.
- Writing: plain words, active voice, sentence case, the same name for the same action everywhere ("Approve" gives "Approved").

## 11. Testing (required)

Add Playwright (or the repo's existing e2e tool) tests and keep them in the repo:
1. Visit every route at 1440×900 and 390×844: no console errors, no empty page, no horizontal overflow.
2. Click every button, menu item and control on every screen. Fail the test if a click throws, or if a control that should change something changes nothing.
3. Top bar: each control opens its popover, sheet or page; Escape closes it.
4. Settings behaviour: currency changes the Overview KPIs; language `ar` sets `dir="rtl"` and changes menu labels; theme dark changes the computed background; autonomy changes the Approvals count (6, 4, 3 with the sample data); Terminal off shows the hidden card; two-step sign-in changes the security score; "Use all suggestions" applies every suggestion.
5. Command palette: Ctrl/Cmd+K opens, typing filters, Enter navigates.
6. Create a company from the brief and from the existing-company form; it appears in the switcher and Companies.
7. Screenshot each screen in light and dark, in English and Arabic, and attach the paths to your final report.

## 12. Phases and deliverables

- **Phase 0:** audit (section 2). Stop and show the plan.
- **Phase 1:** tokens, theme engine, icon set, base components (button, card, segmented, switch, select, list, chip, sheet, popover, toast, tooltip), app shell (sidebar, top bar, drawer, tab bar, command palette, routing, locked-page card). Add the `AGENTS.md` UI rules.
- **Phase 2:** settings registry and store, persistence, i18n and RTL, formatting module, the Settings screens with suggestions, and all connected behaviour in section 9.
- **Phase 3A:** Overview, Ask CEO, Approvals, Companies (including both company flows).
- **Phase 3B:** the five department screens, AI Employees, Agents, Co-worker.
- **Phase 3C:** Tools & Integrations, Security, Terminal, Reports.
- **Phase 4:** polish, accessibility pass, tests, screenshots, cleanup of old UI code that is no longer used (only after the new screens replace it).

Final report: what changed, a map from old screens to new, files added or removed, test results, the list in `STUBS.md` (anything still on sample data), the list in `DECISIONS.md`, and anything you could not do and why.
