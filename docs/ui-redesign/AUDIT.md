# URA Front-End Redesign — Phase 0 Audit

**Date:** 10 November 2026
**Scope:** Phase 0 only. No application code has been changed.
**Sources of truth:** `docs/ui-redesign/SPEC.md` (wins on disagreement) and `docs/ui-redesign/prototype.html` (visual and behavioural reference).

---

## 1. Stack summary

| Layer | What exists today | Evidence | Consequence for the redesign |
|---|---|---|---|
| Language / framework | Plain browser JavaScript. No React, Vue, Svelte, Angular, TypeScript or JSX. | `web/*.js`; no framework dependency in `package.json`. | Rebuild the prototype with the existing vanilla stack. Do not introduce a framework. |
| Module system | None. ~50 classic `<script>` tags in load order, each an IIFE or global. Shared APIs hang off `window` (`window.UI`, `window.Icon`, `window.AppShell`, `window.navigateTo`, `window.*Workspace`). | `web/index.html` script block; `web/components.js`, `web/icons.js`, `web/app_shell.js`. | New code must follow the same global/IIFE convention, or the whole app stops loading. |
| Entry point | `web/index.html` — auth container, static app shell, 39 empty `<section class="view-section">` containers, modal and toast containers. | `web/index.html` | The shell markup is static and must be replaced in place; workspace sections are render targets. |
| Router | Hash router in `web/app.js`. `window.navigateTo()` sets `location.hash`; `handleRoute()` maps path aliases to a `navKey`, toggles `.nav-item.active` and `.view-section.active`, then dispatches to a workspace renderer. Unknown routes render a real 404 view, not a silent redirect. | `web/app.js:581–900`. | Keep the hash router and shareable URLs. Extend it with a route registry; do not replace it with a new router. |
| State | One mutable global `state` object in `app.js`, plus per-module state. localStorage keys: `zonata_companies`, `zonata_workforce`, `zonata_missions`, `zonata_custom_tools`, `zonata_settings`, `zonata_theme_preference`, `zonata_theme`, `zonata_auth_token`, `zonata_active_tenant_id`, `zonata_active_company_id`, `zonata_host_session`, `zonata_company_draft`, `zonata_assistant_corner`, `zonata_dev_autologin`. | `web/app.js:1–120`, `saveData()` at 441. | Add a settings store and a formatting module; keep the existing state shape and auth/session logic. |
| Rendering | Template strings injected into `.view-section` containers; some direct DOM creation. Heavy inline `style=""`. | `web/*_workspace.js`. | Preserve render targets; replace markup inside them. |
| Styling | Six global stylesheets: `design_tokens.css` (8 KB), `components.css` (18 KB), `app_shell.css` (10 KB), `styles.css` (223 KB), `settings_v2.css` (20 KB), plus a Google Fonts link. Tokens exist, but screens also contain **992 inline hex colours** and **3,243 emoji used as icons/decoration**. | `web/index.html` head; grep counts. | Extend tokens and add new component CSS; stop adding to `styles.css`. Old styles are only removed in Phase 4 after replacement. |
| Component primitives | `window.UI` in `components.js`: Button, Input, Card, modal, toast, badge, toggle, segmented (partial), list row, empty state, spinner, etc. `window.Icon` in `icons.js`: one consistent 24 px stroke set (1.75 px stroke), ~70 names. | `web/components.js`, `web/icons.js`. | Extend `window.UI` and `window.Icon`. Do not create a parallel component system. |
| Icons | SVG icon set exists, but many workspaces still use emoji (`🚀`, `🧪`, `🏢`, `💰`, `⚙️`, `🛡️`, etc.). | grep: 3,243 emoji matches under `web/*.js`. | Replace emoji with `window.Icon` names as each screen is rebuilt. |
| i18n / RTL | None. No translation files, no `t()` function, no `dir` attribute switching. Only `meeting_room_workspace.js` sets `lang='en-US'` for speech recognition. | grep for `i18n`, `translate`, `dir=`. | New `i18n.js` plus locale files and `t()` are required in Phase 2. |
| Formatting | Ad hoc. **158 hard-coded `₹` symbols**, plus hard-coded `$`; **94** uses of `toLocaleString`/`toFixed` for money/dates. Currency fallback is `₹` in several places. | `web/app.js:417`, `ai_ceo_workspace.js`, `agent_factory_workspace.js`, etc. | One formatting module is required. Ban ad-hoc money/date formatting in new screens. |
| Theme | `ThemeManager` in `app.js` supports `light`, `dark`, `auto` (day/night by local hour) and sets `data-theme` on `<html>`. Dark tokens exist in `design_tokens.css`. Many components still hard-code light colours, so dark mode is partial. `design_preview_workspace.js` writes a **different** key (`zonata_theme`) that `ThemeManager` never reads. | `web/app.js:129–204`; `design_tokens.css:96`; `design_preview_workspace.js:396`. | Replace with one theme engine driven by the settings registry. Keep `data-theme` for compatibility. |
| Backend | Python `api_server.py` and `core/`. Large `/api/*` surface (A2A, agent engine, browser, coworker, MCP, OpenHands, Temporal, Nango, `v8`, settings v2, etc.). Auth is Bearer + `X-Tenant-ID`, fail-closed on 401. | `api_server.py`; `core/settings/api_v2.py`. | Do not change contracts. New screens call the same endpoints. |
| Settings backend | `/api/settings/v2` exists with a 16-section catalogue and typed definitions. **There is no user-preferences endpoint.** 6 of 16 sections are editable in Settings V2 (`READY_SECTIONS`); the other 10 render a legacy/coming-soon panel. | `core/settings/sections.py`; `web/settings_v2.js:18–27, 1189`. | Use `/api/settings/v2` where a key maps. For the new 7-category model, persist unmapped keys in localStorage and document the fallback. |
| Build | `npm run build` is a placeholder that prints success. No bundler, transpiler or asset pipeline. | `package.json`. | Replace the placeholder with a real static integrity check; do not add a bundler. |
| Type check / lint | None. No `tsconfig`, `jsconfig`, ESLint config or lint script. | `package.json`, repo root. | Add `node --check` for every JS file plus a new-module type check and ESLint. See §6.1. |
| Tests | 142 Python test files (unittest), including UI-string tests that assert exact CSS/JS/HTML snippets (`test_apple_design_foundations.py`, `test_apple_app_shell.py`, `test_apple_primitives.py`, `test_settings_v2_ui_smoke.py`, …). Playwright suite in `tests/e2e/test_user_journeys.spec.ts` (12 tests, journeys 1–12). | `tests/`, `playwright.config.ts`. | The old UI-string tests must be updated or retired per screen in Phase 4. Playwright currently targets staging, not a local server. |
| Playwright | `testDir: ./tests/e2e`, `baseURL: https://zonata-staging.onrender.com` (overridable with `BASE_URL`), projects `chromium-desktop` and `chromium-mobile`, workers 1. | `playwright.config.ts`. | Phase 1 adds a local `webServer` and a local URL so tests do not depend on staging. |
| CI | Five workflows: `ci_cd.yml`, `cloud_staging_deploy.yml`, `docker_staging_qualification.yml`, `e2e-browser.yml`, `postgres_16_qualification.yml`. Current green branch: `fix/green-baseline` at `d9555aa` (PR #9). | `.github/workflows/`. | Keep all workflows green. Do not weaken the gates. |

---

## 2. Old-to-new screen map

### 2.1 Current navigation (28 items) and extra routes

The current sidebar has 28 `data-nav` items. The router also exposes several routes that are not in the sidebar. The target menu has 17 screens (SPEC §5). Everything below keeps its existing feature, moved into a tab, section or secondary route of its new screen.

| # | Current nav / route | Current renderer and files | Data / API | New screen | Placement and notes |
|---|---|---|---|---|---|
| 1 | `/` `/overview` `Home` | `overview_workspace.js`; fallback `renderOverview()` in `app.js` | `/api/portfolio`, `/api/v8/*` | **Overview** | Primary screen. Rebuild greeting, KPI tiles, decisions, profit chart, department status, activity. |
| 2 | `/coworker` `Coworker 2.0` | `assistant_coworker_workspace.js`, `apple_coworker_assistant.js` | `/api/coworker/*`, `/api/v2/coworker/*` | **Co-worker** | Personal / Company segmented control, permission sheet, recent actions. |
| 3 | `/missions` `/work` `Work & Missions` | `assistant_coworker_workspace.js` (`renderMissions`) | `/api/coworker/missions`, `/api/v8/missions` | **Operations (COO)** | “Tasks & missions” tab. Mission detail stays. Links from Overview activity remain. |
| 4 | `/schedule` `Schedule` | `schedule_workspace.js` | `/api/schedules`, `/api/schedules/parse-nl` | **Operations (COO)** | “Schedule” tab. |
| 5 | `/operations` `Operations` | `operations_workspace.js` | `/api/companies`, operations endpoints | **Operations (COO)** | Primary screen. Host/health, throughput, SOPs, team, Instruct box. |
| 6 | `/customers` `Customers / CRM` | `crm_sales_workspace.js`, `apple_sales_board.js` | `/api/crm/customers`, `/api/crm/deals` | **Marketing & Sales (CMO)** | Pipeline (New, Contacted, Negotiating, Won) with Advance; customer 360 tab. |
| 7 | `/finance` `Finance & GL` | `finance_workspace.js` | `/api/finance/expenses`, `/api/v8/*` | **Finance (CFO)** | Revenue, costs, profit, invoices, payment-limit card. |
| 8 | `/people` `People & HR` | `people_workspace.js`, `apple_workforce_board.js` | `/api/employees`, workforce endpoints | **People (CHRO)** | CHRO overview plus hire entry. AI employee roster itself is **AI Employees**. |
| 9 | `/records` `Records` | `records_workspace.js` | `/api/records` | **Security** | “Evidence & audit” tab (immutable event ledger). |
| 10 | `/files` `Files` | `files_workspace.js` | `/api/files` | **Reports** | “Documents & artifacts” tab; also linked from Co-worker artifacts. |
| 11 | `/reports` `Reports` | `reports_workspace.js`, `apple_reports_preview.js` | `/api/reports`, `/api/v8/reports` | **Reports** | Primary screen. Generate now, Preview, Email me, schedule line. |
| 12 | `/agent-factory` `Dynamic Workforce` | `agent_factory_workspace.js` | `/api/agent-factory/blueprints`, `/api/agent-factory/synthesize` | **AI Employees** | “Hire AI employee” sheet and blueprints; also linked from Agents. |
| 13 | `/integrations` `Integrations` | `integrations_workspace.js` | `/api/integrations/marketplace`, `/api/connections` | **Tools & Integrations** | Connected / marketplace tabs. |
| 14 | `/approvals` `Approvals` | `assistant_coworker_workspace.js` (`renderApprovals`) | `/api/v8/approvals`, `/api/workflows/approvals`, `/api/coworker/approvals`, `/api/a2a/approvals`, `/api/browser/approvals`, `/api/temporal/approvals` | **Approvals** | Waiting / History tabs. Add the shared `needsOwner()` rule and badge. |
| 15 | `/activity` `Activity` | `assistant_coworker_workspace.js` (`renderActivity`) | activity endpoints | **Overview** | Activity feed on Overview; full log remains in Security “Audit”. |
| 16 | `/governance` `Governance & Risk` | `governance_workspace.js`, `apple_security_center.js` | governance endpoints | **Security** | “Governance & risk” tab, merged with security findings. |
| 17 | `/ceo` `/ai-ceo` `/workspace/ai-ceo` `AI CEO` | `ai_ceo_workspace.js`, `ceo_command_center.js` | `/api/v8/ceo/*`, `/api/v8/chat`, `/api/agent-engine/*` | **Ask CEO** | Primary chat. The large AI CEO console (20 tabs, stress tests, capital allocation) stays as secondary tabs/sections under Ask CEO; not deleted. |
| 18 | `/workforce` `AI Workforce` | `workforce_workspace.js`, `apple_workforce_board.js` | `/api/employees`, workforce endpoints | **AI Employees** | Roster, KRA/KPI, SOPs, pause/resume. |
| 19 | `/company` `Company` | `company_workspace.js` (160 KB) | `/api/companies`, `/api/onboard` | **Companies** | Company list, create/connect flows, company detail. |
| 20 | `/terminal` `Terminal` | `apple_governed_terminal.js` | `/api/terminal/execute`, `/api/terminal/diagnostics` | **Terminal** | Primary screen; role-gated by the `terminalOn` setting. |
| 21 | `/workflows` `Workflows` | `workflow_workspace.js` | `/api/workflows`, `/api/workflows/runs` | **Operations (COO)** | “Automations” tab; durable execution links to Technology. |
| 22 | `/agent-network` `Agent Network` | `agent_network_workspace.js` | `/api/a2a/*` | **Agents** | “Network” tab. |
| 23 | `/mcp-network` `MCP Network` | `mcp_workspace.js` | `/api/mcp/*` | **Tools & Integrations** | “MCP servers” tab. |
| 24 | `/openhands-execution` `OpenHands` | `openhands_workspace.js` | `/api/openhands/*` | **Technology (CTO)** | “Execution” tab. |
| 25 | `/browser-execution` `Browser Execution` | `browser_workspace.js` | `/api/browser/*` | **Technology (CTO)** | “Browser execution” tab; Co-worker browses through the same data. |
| 26 | `/temporal-durable` `Temporal` | `temporal_workspace.js` | `/api/temporal/*` | **Technology (CTO)** | “Durable workflows” tab. |
| 27 | `/trustgraph` `TrustGraph` | `trustgraph_workspace.js` | trust graph endpoints | **Security** | “Trust graph” tab. |
| 28 | `/settings` `Settings` | `settings_v2.js` by default; `settings_enterprise.js` for legacy deep links | `/api/settings/v2`, `/api/settings/effective`, `/api/settings/audit` | **Settings** | Rebuild as 7 categories with suggestions. Keep legacy console at `/settings-legacy`. |
| 29 | `/tasks` (route only) | `taskmaker_workspace.js` | task endpoints | **Operations (COO)** | “Tasks” tab. |
| 30 | `/processes` (route only) | `processes_workspace.js` | process endpoints | **Operations (COO)** | “Processes / SOPs” tab. |
| 31 | `/organization` (route only) | `org_workspace.js` | `/api/v1/zonata/org-design/*` | **Companies** | “Organization design” tab; also linked from People. |
| 32 | `/meeting` `/ceo/meeting` (route only) | `meeting_room_workspace.js` | `/api/meetings/*` | **Ask CEO** | “Executive meeting” tab. |
| 33 | `/plugins` (route only) | `plugins_workspace.js` | `/api/plugins` | **Tools & Integrations** | “Plugins” tab. |
| 34 | `/nango-integrations` (route only) | `nango_workspace.js` | `/api/nango/*` | **Tools & Integrations** | “Nango connectors” tab; technology health shown in Technology. |
| 35 | `/tools` (route only) | `tools_factory.js` | `/api/tools`, `/api/tools/build`, `/api/tools/discover` | **Tools & Integrations** | “Tool registry / build a tool” tab. |
| 36 | `/artifacts` (route only) | `assistant_coworker_workspace.js` (`renderArtifacts`) | `/api/coworker/artifacts` | **Reports** | “Artifacts” tab. |
| 37 | `/design` (route only) | `design_preview_workspace.js` | local only | **Settings → Appearance** | Keep `/design` as a developer/preview route; move theme preview into Appearance. |
| 38 | `/404` | `renderNotFoundView()` in `app.js` | none | **404** | Keep. Still show the hidden-page card when a hidden screen is opened directly. |

### 2.2 Current view containers (39)

`index.html` defines 39 `<section class="view-section">` containers: `overview, coworker, missions, work, schedule, operations, customers, finance, people, records, files, reports, agent-factory, integrations, approvals, activity, governance, company, organization, ceo, meeting, workforce, terminal, tasks, workflows, agent-network, mcp-network, openhands-execution, browser-execution, temporal-durable, nango-integrations, processes, trustgraph, tools, plugins, settings, artifacts, design, 404`.

The target shell needs only the 17 screens (16 menu items plus Settings) and 404. Old containers are removed from `index.html` only in Phase 4, after their renderer is replaced or merged. Until then, both can coexist behind the router.

### 2.3 Screens with no current route but loaded code

These files are loaded but have no sidebar item or direct route. They must be given a home rather than dropped:

| Component | Current access | New home |
|---|---|---|
| `department_workspace.js` | Not routed. Instantiated as `window.DepartmentWorkspace`. | Used by the five department screens (COO/CMO/CTO/CFO/CHRO) as the shared department layout. |
| `apple_workforce_board.js` | Used by People and Workforce. | **AI Employees** and **People (CHRO)**. |
| `apple_sales_board.js` | Used by CRM/Sales. | **Marketing & Sales (CMO)**. |
| `apple_reports_preview.js` | Used by Reports. | **Reports**. |
| `apple_security_center.js` | Used by Governance. | **Security**. |
| `apple_governed_terminal.js` | Used by Terminal. | **Terminal**. |
| `apple_coworker_assistant.js` | Used by Co-worker. | **Co-worker**. |
| `ai_action_card.js` | Shared card. | Shared component. |
| `ai_orb.js` / `ceo_command_center.js` | Shell / CEO decoration. | Ask CEO and Overview status. |
| `company_context.js` | Company context helpers. | Shared multi-company context. |
| `entry_flows.js` | Company onboarding and auth. | **Companies** create/connect flows. |
| `floating_assistant.js` | Legacy floating assistant. | Co-worker / command palette. Retire only after replacement. |
| `motion.js` | Animation helpers. | Shared motion, respecting reduced motion. |

---

## 3. Dead, fake or visually broken controls

These are the concrete findings from the current shell and screens. Each is scheduled for a phase below.

| # | Control / location | Current behaviour | Severity | Fix phase |
|---|---|---|---|---|
| 1 | **Ask URA / ⌘K modal** — `web/app_shell.js:157–195` | Returns a fabricated answer: `₹4,28,500`, “+12% vs last week”, “2 pending executive approvals”, then simulates typing. It is not connected to the CEO API or company data. | **High — fake data presented as live** | 3A (wire to real CEO chat) |
| 2 | **⌘K shortcut** — `app_shell.js:18–24` and `app.js:1008–1016` | Two global keydown listeners fire for the same shortcut: one opens the Ask URA modal, the other focuses the top-bar search. Behaviour depends on listener order. | **High** | 1 (single command palette) |
| 3 | **Notification bell** — `index.html:341–345` | Clicking navigates to Approvals. `#topbarNotificationBadge` is never written by any JS, so the unread badge is permanently `display:none`. No popover, no mark-as-read. | **High** | 1 (bell popover), 2 (notification rules) |
| 4 | **Status pill** — `index.html:334–338` | Static “Kernel Active” with a pulsing dot. Not fed by `/api/v8/control-loop/state`, agent status or the `hours` setting; not clickable. Spec requires a CEO status popover. | **High** | 1 (popover), 2 (`hours`) |
| 5 | **Company clock** | Missing entirely. No clock component in the top bar. | High (spec requirement) | 1 |
| 6 | **Help control** | Missing entirely. No “How URA works”, shortcuts or help search. | High (spec requirement) | 1 |
| 7 | **Profile control** | Missing from the top bar. Sign-out exists only in the host profile area, not as a profile menu. | High (spec requirement) | 1 |
| 8 | **Breadcrumb root “ZONATA”** — `index.html:308` | A `<span>`, not a link; cannot return to Overview/Companies. | Medium | 1 |
| 9 | **Sidebar company switcher** — `index.html:42–66` | Entire card is a `<div onclick>`, and it contains a nested `<button>` with no handler (invalid nested interactive elements). The “Switch Company” chevron only works by event bubbling. | Medium (a11y) | 1 |
| 10 | **Mobile bottom tab bar** | CSS exists (`.apple-mobile-tab-bar` in `app_shell.css:385`) but there is **no markup** in `index.html` and no JS injection. Phones get a drawer only. | High (spec requirement) | 1 |
| 11 | **Global search** — `index.html:315–321`, `app.js:915–985` | A debounced `/api/search` dropdown only. Cannot find pages, companies, settings, employees or agents locally; no keyboard navigation; no actions. | High (spec requirement) | 1 |
| 12 | **Ask URA floating bar** | Always visible, overlaps the workspace on narrow screens; opens the fabricated modal (#1). `app_shell.css` positions it by hard-coded pixel offsets. | Medium | 1 (replace with palette/Ask CEO entry) |
| 13 | **`zonata_settings`** — `app.js:441–448` | Settings are persisted but `state.settings` is **never read** anywhere. Every saved setting is inert. Only `zonata_theme_preference` has an effect. | **High — dead settings model** | 2 |
| 14 | **Design preview theme** — `design_preview_workspace.js:393–396` | Writes `localStorage.zonata_theme`, which `ThemeManager` never reads. Theme chosen in the preview is lost on reload. | Medium | 2 |
| 15 | **Settings V2 non-ready sections** — `settings_v2.js:18–27, 1189` | 10 of 16 sections render a legacy/coming-soon panel instead of editable controls. “Coming soon” counts exist but many controls do nothing. | High | 2 |
| 16 | **Two settings consoles** — `/settings` → `SettingsV2`; `/settings/<domain>` and `/settings-legacy` → `EnterpriseSettings` (32 domains) | Two different information architectures, scopes and persistence models in one product. Deep links silently switch UI. | High | 2 |
| 17 | **Emoji as icons** | 3,243 emoji occurrences across workspaces; spec bans emoji as icons. Visually inconsistent and often missing accessible labels. | Medium (design) | 3A–3C |
| 18 | **Hard-coded currencies** | 158 `₹` symbols plus hard-coded `$`; amounts mix currencies and formats. | **High — correctness** | 2 (formatting), 3A–3C (screens) |
| 19 | **992 inline hex colours** | Bypass tokens; dark mode is incomplete and contrast is uncontrolled. | Medium | 3A–3C |
| 20 | **`alert()` for errors/success** — e.g. `agent_network_workspace.js`, `browser_workspace.js`, `assistant_coworker_workspace.js`, `ai_ceo_workspace.js` | Blocking native dialogs, not accessible, inconsistent with the design language. | Medium | 3A–3C |
| 21 | **“Simulate” actions presented alongside live actions** — `app.js:2432`, `2760`, `3219`, `3534`; `company_workspace.js:2223–2231`, `2667`; `org_workspace.js` simulator; `ai_ceo_workspace.js` stress-test | Some are legitimate sandboxes; others create fake records or pretend completion. No visible “Sample data” label. | High (trust) | 3A–3C |
| 22 | **`state.settings` default `{}`** | No registry, no defaults, no validation, no suggestions. | High | 2 |
| 23 | **Sidebar “active” state** | Router toggles `.nav-item.active`, but hidden/unknown routes have no `nav-item`, so no item is marked current and `aria-current` is absent. | Medium | 1 |
| 24 | **Modal accessibility** — `components.js` modal | Focus is placed but not trapped; background is not `aria-hidden`; focus is not reliably restored. | Medium (a11y) | 1 |
| 25 | **No visible keyboard focus** in several workspaces | Inline styles reset outlines; many clickable `<div>`s are used instead of buttons. | Medium (a11y) | 1 / 4 |
| 26 | **`localStorage` auth token** | Existing behaviour, out of scope. Not changed; documented so redesign does not accidentally break it. | Info | — |

**Controls that do work today:** the theme cycle button (`ThemeManager.cycle`), the company context `<select>` (`handleGlobalCompanyContextChange`), sidebar navigation and hash routing, modal open/close, toasts, and the workspace data fetches (when authenticated). These are retained.

---

## 4. Settings mapping

### 4.1 Current settings surfaces

1. **Settings V2** — `web/settings_v2.js` + `web/settings_v2.css`, default at `/settings`. Registry-driven from `/api/settings/v2/registry`. 16 sections, 6 ready. Scopes: organization / company / department / agent / user. Supports approvals and audit drawers.
2. **Enterprise Settings** — `web/settings_enterprise.js`, reachable at `/settings-legacy` and any `/settings/<domain>` deep link. 6 pillars / 32 domains, scope dropdown, diagnostics, audit drawer, reset-to-inherited.
3. **Ad-hoc preferences** — theme in `app.js` (`zonata_theme_preference`), assistant corner (`zonata_assistant_corner`), design preview (`zonata_theme`, unread), plus scattered `localStorage` writes.

### 4.2 Old 16 settings sections → new 7 categories

| Old section | New category | Mapping detail |
|---|---|---|
| `general_organization` | **Language and region** + **Menu and team** | Locale, currency, time zone and formats move to Language and region. Org profile stays under Menu and team / Companies. |
| `companies` | **Companies** (screen) + **Language and region** | Company list stays on the Companies screen. Per-company currency/time zone feed the formatter. |
| `team_access` | **Menu and team** | Members, roles, invites, permission matrix, SSO. |
| `ai_agents_employees` | **AI CEO and autonomy** | Autonomy, model routing, behaviour, permissions, SOPs, emergency controls. |
| `spending_budgets` | **AI CEO and autonomy** + **Finance** | Owner payment limit (`payLimit`) is a core setting. Detailed budgets remain on Finance. |
| `integrations` | **Tools & Integrations** | Connector and API-token management stays on the screen, not in Settings. |
| `browser_automation` | **Security and privacy** + **Co-worker** | Domain policy, sessions and evidence under Security; personal/company permission under Co-worker. |
| `security_compliance` | **Security and privacy** | MFA, sessions, encryption, residency, DLP, incident response. |
| `reports_documents` | **Reports** | Frequency, recipient, included sections, templates, retention. |
| `notifications` | **Notifications** | Every switch, quiet hours, digest and channel. |
| `data_storage_backups` | **Security and privacy** | Storage, backups, restore drills, erasure. |
| `infrastructure_stack` | **Security and privacy → Advanced** | Preserve as an advanced sub-tab; no setting is deleted. |
| `billing_plan` | **Security and privacy → Billing** | Preserve as a sub-tab; plan/seat data remains read/write through its existing API. |
| `appearance_accessibility` | **Appearance** | Theme, accent, density, text size, motion, contrast, shortcuts. |
| `audit_activity` | **Security and privacy** | Audit retention (`audit`) and the immutable ledger. |
| `advanced_danger` | **Security and privacy → Advanced** | Flags, ownership transfer, destructive actions. |

### 4.3 Enterprise 32 domains → new 7 categories

| Pillar | Domains | New home |
|---|---|---|
| I. Identity & Access | `account`, `company`, `users`, `enterprise` | Menu and team (`account`, `users`, `enterprise`); Companies (`company`). |
| II. AI & Executive Intelligence | `ai_ceo`, `workforce`, `automation`, `ai_providers` | AI CEO and autonomy (`ai_ceo`, `ai_providers`); AI Employees (`workforce`); Operations (`automation`). |
| III. Execution Fabric | `tools`, `desktop`, `browser`, `terminal`, `mcp`, `a2a` | Tools & Integrations (`tools`, `mcp`); Co-worker / Security (`desktop`, `browser`, `terminal`); Agents (`a2a`). |
| IV. Business & Finance | `integrations`, `data`, `communication`, `finance`, `billing` | Tools & Integrations (`integrations`); Security (`data`); Reports/Notifications (`communication`); Finance (`finance`); Security → Billing (`billing`). |
| V. Governance & Trust | `security`, `governance`, `privacy`, `notifications`, `audit`, `recovery` | Security and privacy; Approvals (`governance`); Notifications; Audit and Recovery under Security. |
| VI. Platform & Operations | `monitoring`, `api`, `webhooks`, `localization`, `appearance`, `advanced`, `diagnostics` | Security → System health (`monitoring`, `diagnostics`); Tools & Integrations (`api`, `webhooks`); Language and region (`localization`); Appearance; Security → Advanced (`advanced`). |

### 4.4 New setting keys and current status

The new registry keys in SPEC §8 are **new**. Only `theme` has a working equivalent today. Every other key is either stored inertly or does not exist.

| New category | Keys | Current state |
|---|---|---|
| Appearance | `theme`, `accent`, `density`, `sidebar`, `textSize`, `reduceMotion`, `contrast` | `theme` works (light/dark/auto). Accent/density/sidebar/textSize/motion/contrast do not exist. |
| Language and region | `lang`, `tz`, `hour`, `dateFmt`, `numFmt`, `currency` | None exist. Hard-coded `₹`, device time zone only, no translations. |
| AI CEO and autonomy | `autonomy`, `payLimit`, `hours`, `tone` | No rule engine. Pay limits exist as scattered form fields. |
| Notifications | `n_approvals`, `n_security`, `n_reports`, `n_builds`, `quiet` | Bell has no popover and no category filtering. |
| Reports | `repFreq`, `repEmail`, `repProfit`, `repSales`, `repSec` | Report UI exists; no schedule model in the UI. |
| Security and privacy | `session`, `audit`, `region`, `terminalOn`; two-step via real TOTP enrollment | Enterprise Settings has related fields; two-step is now real server state (Stage 7); other keys not wired to the new UI or `secScore`. |
| Menu and team | hidden screens, invite, role, remove | Roles exist in data; no menu-hiding or invite UI. |

### 4.5 Persistence decision (to be recorded in `DECISIONS.md`)

The spec says “Persist settings per user through the existing user-preferences API (fall back to local storage).” **No user-preferences API exists in this repo.** Phase 2 will:

1. Use `/api/settings/v2` for keys that map to an existing typed definition.
2. Store the new presentation/format/autonomy keys in `localStorage` under one versioned object (`ura.ui.settings.v1`), with a clear “Saved on this device” label.
3. Read existing `zonata_settings` once for migration, then stop writing the dead key.
4. Document every unmapped key in `STUBS.md`.

---

## 5. Gaps: what the new design needs that the codebase lacks

| Gap | Detail | Phase |
|---|---|---|
| Design-token coverage | Tokens exist but not the full SPEC palette (accent variants, fill tokens, `fg-2`/`fg-3`, density, text scale, contrast). Many screens bypass tokens. | 1 |
| Component kit | No segmented control, switch (iOS style), select, sheet, popover, tooltip, list, chip, KPI tile, chart with tooltip/table toggle, or focus-trapped sheet. Modal/toast exist but need a11y work. | 1 |
| App shell | No floating translucent sidebar, no icons-only rail with tooltips, no floating top bar, no company chip menu, no CEO status popover, no clock, no bell popover, no help, no profile menu, no mobile tab bar markup. | 1 |
| Command palette | Current search is an API dropdown only. No local pages/companies/actions/settings/employees/agents index, no keyboard navigation, no `aria-activedescendant`. | 1 |
| Routing | Hash router works, but no route registry, no per-screen URL for settings categories, no back/forward guarantee after shell re-render, no hidden-page card. | 1 |
| Settings registry | No schema, no suggestions, no defaults, no "Use all suggestions", no instant apply, no category drill-down on mobile. | 2 |
| i18n / RTL | No `t()`, no locale files, no `dir="rtl"`, no `unicode-bidi: plaintext`, no translated menu. | 2 |
| Formatting | No `formatMoney`, `formatNumber`, `formatDate`, `formatTime`, `timeAgo`, `dparts`. 158 hard-coded `₹`. | 2 |
| Connected behaviour | No `needsOwner`, `secScore`, `vis`, `pgLocked`; no single settings store feeding the shell, notifications, approvals, security and terminal. | 2 |
| Sample-data adapter | No `USE_SAMPLE_DATA` switch, no typed sample fixtures, no “Sample data. Not connected yet.” label. Several screens show raw API errors instead. | 3A–3C |
| Charts | Prototype has SVG area/bar charts with tooltips and table fallback; current screens mostly use static numbers or CSS bars. | 3A |
| Company lifecycle | Create/new-company brief, connect-existing-company form and the 5-step build/study states exist in pieces (`entry_flows.js`, `company_workspace.js`) but are not the new Companies experience. | 3A |
| Approvals model | Approvals are spread across six endpoints and several card shapes. No single waiting/history model, no risk pill, no autonomy rule, no shared badge. | 3A |
| Department screens | `department_workspace.js` exists but has no route. The five departments are not first-class screens today. | 3B |
| AI employee / agent model | Roster, KRA/KPI, SOPs and install flows exist across Workforce, Agent Factory and Agent Network, but not in the new structure. | 3B |
| Co-worker permission | Permission/approval flow exists in pieces; no `cowork` approval kind enforced. | 3B |
| Tools / security / terminal / reports | Large existing implementations, but old markup, emoji, `alert()`, hard-coded values, and no settings connection. | 3C |
| Accessibility | Clickable `<div>`s, missing labels, no focus trap, no visible focus in places, no `aria-current`. | 1 / 4 |
| Mobile | Drawer exists; bottom tabs are CSS-only; sheets are not bottom sheets; some workspaces overflow at 390 px. | 1 / 4 |
| Tests | Playwright points at staging; no local webServer. Old Python tests assert exact old markup, so they will fail during the redesign and must be updated per phase. | 1 / 4 |
| Tooling | No type check or lint. CI does not run front-end static checks. | 1 |
| Local development | `npm start` runs `python3 api_server.py`; Playwright does not start it. Need a documented local flow and `BASE_URL`. | 1 |
| Sample FX / rates | Spec requires money in USD with rates; no FX source or rate table in the UI. | 2 |
| Notifications data | No unified notification feed; the bell badge is dead. | 2 |

---

## 6. Phased plan with file-level detail

### 6.0 Verification gate (adopted for every phase)

The repo has no type checker or linter, so the SPEC gate needs an explicit, honest adaptation. This is a tooling addition, not an application framework.

| Gate | How it will run | What it proves |
|---|---|---|
| Type check | `npm run typecheck`: `node --check` every `web/*.js` + `tsc --noEmit --allowJs --checkJs` on the new JSDoc-annotated modules (`settings_registry.js`, `settings_store.js`, `format.js`, `i18n.js`, `rules.js`, `route_registry.js`). | Syntax is valid everywhere; new modules are type-checked. |
| Lint | `npm run lint`: ESLint flat config (`eslint.config.mjs`) with browser globals, `no-undef`, `no-unused-vars`, `no-redeclare`, `no-dupe-keys`, `eqeqeq`. | No undefined globals, duplicate declarations or obvious dead code. |
| Build | `npm run build`: new `scripts/verify_static_build.mjs` checks every `<script>`/`<link>` target exists, no duplicate DOM ids, all 17 routes registered, all menu ids resolve, no missing translation keys. | The static app can load and route. |
| Tests | `python3 -m pytest -q` plus `npx playwright test` against a local `webServer` (`BASE_URL=http://127.0.0.1:8000`). | Backend and browser behaviour are verified. |
| Commit | One atomic commit per phase with the gate output in the message/body. | No phase starts on a failing build. |

**Important:** the current Python tests include exact-string assertions about the old CSS/JS. Phase 1 will update only the shell/DOM assertions it invalidates, and Phase 4 will retire the rest. Tests are never deleted merely to make a phase pass; each change is justified in the phase summary.

---

### Phase 1 — Tokens, theme engine, icons, base components, app shell

**Goal:** the new shell works end to end with the current screens still rendering inside it.

**Files to add**
- `web/ui_kit.css` — component styles for segmented, switch, select, list, chip, sheet, popover, tooltip, KPI tile, chart shell, focus states, reduced-motion and contrast rules. (Keeps `components.css` from growing further.)
- `web/shell_v3.css` — floating sidebar, rail, top bar, drawer, bottom tab bar, palette, popovers; logical properties throughout.
- `web/shell_v3.js` — new `AppShell` implementation: sidebar/rail, company chip menu, breadcrumbs, top bar controls (palette, status, clock, bell, help, profile), drawer, tab bar, overlay manager.
- `web/palette.js` — command palette index (pages, companies, actions, settings, employees, agents), keyboard navigation, `Ctrl/Cmd+K`, `aria-activedescendant`.
- `web/route_registry.js` — the 17 screens, group names, icons, settings category routes, hidden-page logic, aliases from §2.1.
- `web/theme.js` — token/theme engine driven by settings: theme, accent, density, text size, motion, contrast. (May absorb `ThemeManager` and keep `window.ThemeManager` as an alias.)
- `web/shell_icons.js` or additions to `web/icons.js` — missing glyphs: `home`, `chat`, `approve`, `ops`, `mkt`, `tech`, `fin`, `people`, `bot`, `spark`, `plug`, `shield`, `term`, `doc`, `building`, `sliders`, `clock`, `help`, `user`, `bell`, `search`, `chevL/R`, `panel`.
- `tests/e2e/redesign_shell.spec.ts` — every route at 1440×900 and 390×844; shell controls; palette; escape; no overflow.
- `eslint.config.mjs`, `scripts/typecheck.mjs`, `scripts/verify_static_build.mjs`, `jsconfig.json`.

**Files to modify**
- `web/index.html` — replace the static shell block with the 17-item menu, company chip, top bar controls, mobile tab bar and overlay containers; remove the old Ask URA bar and its inline handlers; add new scripts/styles in the correct order.
- `web/design_tokens.css` — complete SPEC tokens: light/dark, accent options, `--fill`, `--fg-2/3`, density, text scale, contrast, reduced motion, safe-area insets.
- `web/components.js` — add `Segmented`, `Switch`, `Select`, `Sheet`, `Popover`, `Tooltip`, `List`, `Chip`, `Kpi`, `EmptyState`, `Dialog` with focus trap and restore; keep existing APIs.
- `web/components.css` — align existing primitives with new tokens; add visible focus.
- `web/app.js` — delegate shell/nav/palette/theme to the new modules; keep auth and `navigateTo`; remove duplicate ⌘K and the old `handleRoute` nav-toggling; add hidden-page rendering and `aria-current`.
- `web/app_shell.js` and `web/app_shell.css` — keep temporarily as a compatibility shim if any workspace calls `AppShell.*`; otherwise remove in Phase 4.
- `AGENTS.md` — add the “UI rules” section required by SPEC §0.8.
- `package.json` — `typecheck`, `lint`, `build`, `test`, `test:e2e` scripts.
- `playwright.config.ts` — local `webServer`, `BASE_URL` default, keep two projects.
- `tests/e2e/test_user_journeys.spec.ts` — update only shell assumptions if required.

**Exit criteria**
- 16 menu items in 4 groups plus Settings at the bottom (17 screens); all routes render; rail/drawer/tab bar work; no horizontal scroll at 390 px.
- Every top-bar control works: menu toggle, breadcrumb, search → palette, CEO status popover, company clock, bell popover, help, profile → theme → Settings → sign out.
- Palette opens with ⌘K, filters, navigates with Enter, closes with Escape.
- Theme/accent/density/text-size/contrast/reduced-motion apply through root attributes.
- No dead control in the shell: each has a handler, `aria-label`, and a real result.
- Type check, lint, build, Python tests and shell Playwright tests pass.

---

### Phase 2 — Settings registry and store, i18n/RTL, formatting, connected behaviour

**Goal:** one registry, one store, one formatter, and all SPEC §9 rules live.

**Files to add**
- `web/settings_registry.js` — the `SET` registry from SPEC §8: keys, types, options, hints, defaults, `suggest(context)`, category metadata, `SETLIST`.
- `web/settings_store.js` — load/save/merge, migration from `zonata_settings`, localStorage fallback (`ura.ui.settings.v1`), `/api/settings/v2` adapter, change subscriptions, instant apply.
- `web/i18n.js` — `t(key, vars)`, locale loading, fallback to English per key, `dir` switching, `unicode-bidi: plaintext` helpers.
- `web/locales/en.js`, `hi.js`, `pa.js`, `ar.js`, `es.js`, `fr.js` — menu, groups, page titles, greetings, common buttons first.
- `web/format.js` — `formatMoney`, `formatNumber`, `formatDate`, `formatTime`, `timeAgo`, `dparts`, time-zone resolution, number-style resolution from language + country.
- `web/rules.js` — `needsOwner`, `secScore`, `vis` (hidden screens), `pgLocked`, notification filtering, `hours` label.
- `web/settings_screen.js` — new 7-category Settings UI: hub, drill-down, suggestion boxes, “Use all N suggestions”, reset, toasts, mobile Back.
- `web/settings_screen.css` — settings layout, suggestion states, category list.
- `docs/ui-redesign/STUBS.md` — sample FX rates, unmapped keys, any sample data.
- `docs/ui-redesign/DECISIONS.md` — persistence fallback, route choices, migration.
- `tests/e2e/redesign_settings.spec.ts` — SPEC §11.4 and §11.5 behaviours.

**Files to modify**
- `web/app.js` — initialise store/registry/i18n/format on boot; route `/settings` and `/settings/<category>`; apply language direction; remove the dead `state.settings` path.
- `web/index.html` — load the new modules before `app.js`.
- `web/settings_v2.js` / `web/settings_enterprise.js` — keep reachable at `/settings-legacy`; label them “Legacy settings” and link back. Do not delete yet.
- `web/settings_v2.css` — retain for legacy only.
- `web/app_shell.js` / `web/shell_v3.js` — apply `hours`, notification visibility, quiet hours, hidden screens, profile/theme links.
- `web/app_shell.css` / `web/shell_v3.css` — `dir="rtl"` layout fixes, `unicode-bidi`.

**Exit criteria**
- Every SPEC §8 setting renders from the registry with a control, hint and suggestion box.
- “Use all suggestions” applies every suggestion and shows a toast.
- Currency changes Overview KPIs; `ar` sets `dir="rtl"` and changes menu labels; dark theme changes computed background; autonomy changes the approvals count (6/4/3); Terminal off shows the hidden card; two-factor changes the security score.
- Settings apply without reload and persist across reload.
- No hard-coded money/date formatting remains in the new shell/settings/Overview code.
- Gates green.

---

### Phase 3A — Overview, Ask CEO, Approvals, Companies

**Goal:** the four owner-critical screens, fully wired.

**Files to add**
- `web/overview_screen.js` — greeting, subtitle, actions, KPI tiles, sparklines, decisions waiting, profit chart (4/12/26 weeks, Chart/Table, tooltips), department status, activity feed, building/studying states.
- `web/charts.js` — SVG area/bar chart primitives with tooltip, keyboard/table alternative, token colours.
- `web/ask_ceo_screen.js` — chat, suggested prompts, attach, send, streaming, tone setting, delegation creates a task; wraps the real CEO call and preserves the existing AI CEO console as secondary tabs.
- `web/approvals_screen.js` — Waiting/History, card anatomy, risk pill, approve/decline, handled-by-CEO history, shared `needsOwner`, shared badge count.
- `web/companies_screen.js` — company cards, switcher, create-new (name + long brief + country + department preview), connect-existing (website, booking, sales, CRM, other tools), world clock.
- `web/sample_data.js` — typed fixtures behind one `USE_SAMPLE_DATA` switch, with the visible “Sample data. Not connected yet.” label.
- `tests/e2e/redesign_3a.spec.ts` — the four screens, both company flows, approvals counts, chart toggle.

**Files to modify**
- `web/index.html` — replace the four section containers or add new ones.
- `web/app.js` — dispatch the four routes to the new screens; keep aliases.
- `web/overview_workspace.js`, `ai_ceo_workspace.js`, `assistant_coworker_workspace.js` (approvals/activity), `company_workspace.js`, `entry_flows.js` — keep as data/logic providers; strip their old view markup only where fully replaced.
- `web/rules.js` — use the same approvals list for sidebar badge, Overview and bell.

**Exit criteria**
- Operating, building and studying Overview states all render from real or clearly labelled sample data.
- Ask CEO uses company data, the user’s currency/format, and `tone`; a delegation creates a task.
- Approvals Waiting/History and the badge/bell agree for all three autonomy settings.
- Both company flows create a company that appears in the switcher and Companies.
- No dead control on these four screens; gates green.

---

### Phase 3B — Five departments, AI Employees, Agents, Co-worker

**Files to add**
- `web/operations_screen.js` — COO: head status, KPIs, tasks, team, Instruct, schedule, missions, automations, processes.
- `web/marketing_sales_screen.js` — CMO: campaigns, lead pipeline with Advance, customer 360.
- `web/technology_screen.js` — CTO: websites, systems, builds, integration health, OpenHands, browser, Temporal, Nango.
- `web/finance_screen.js` — CFO: revenue, costs, profit, invoices, costs vs payment limit.
- `web/people_screen.js` — CHRO: AI employees and agents overview, hiring.
- `web/ai_employees_screen.js` — roster, KRA/KPI bars, SOP steps, agents used, pause/resume, Hire sheet, rule banner.
- `web/agents_screen.js` — installed agents, templates, install sheet (template or GitHub URL), approval + Terminal log, network tab.
- `web/coworker_screen.js` — Personal/Company segmented, permission lock, Ask CEO, recent actions, browser artifacts.
- `tests/e2e/redesign_3b.spec.ts`.

**Files to modify**
- `web/index.html`, `web/app.js` — containers and dispatch.
- `department_workspace.js` — reuse as shared layout/data provider; remove old markup as replaced.
- `workforce_workspace.js`, `apple_workforce_board.js`, `agent_factory_workspace.js`, `agent_network_workspace.js`, `assistant_coworker_workspace.js`, `apple_coworker_assistant.js`, `crm_sales_workspace.js`, `apple_sales_board.js`, `finance_workspace.js`, `operations_workspace.js`, `schedule_workspace.js`, `workflow_workspace.js`, `taskmaker_workspace.js`, `processes_workspace.js`, `org_workspace.js` — data/logic preserved; old view paths retired per screen.

**Exit criteria**
- Each department has head status, KPIs, tasks, team and Instruct creating a task.
- CMO pipeline advances; CFO shows costs against the payment limit.
- Employee rule banner is visible; KRA/KPI and SOP render; pause/resume works.
- Open-source agent install requires approval and writes a Terminal line.
- Co-worker Company mode is locked until CEO permission creates a `cowork` approval.
- Gates green.

---

### Phase 3C — Tools & Integrations, Security, Terminal, Reports

**Files to add**
- `web/tools_screen.js` — catalog by category (website, booking, sales/CRM, payments, messaging, MCP, API, browser tools), connect/disconnect, last sync, built-by-agents badge, released-after-task note; plugins and Nango tabs.
- `web/security_screen.js` — score ring from `secScore`, checks, findings + Resolve, Run scan with progress, activity + Terminal write; evidence/audit, governance, trust graph, system health, billing/advanced tabs.
- `web/terminal_screen.js` — command parser (`help status companies use <name> agents approvals scan whoami theme currency lang accent ura agent search|install clear`), history with up/down, role gate.
- `web/reports_screen.js` — list, Generate now, Preview, Email me, schedule line from settings, profit/sales/security sections; documents/artifacts tabs.
- `tests/e2e/redesign_3c.spec.ts`.

**Files to modify**
- `web/index.html`, `web/app.js` — containers and dispatch.
- `tools_factory.js`, `integrations_workspace.js`, `plugins_workspace.js`, `mcp_workspace.js`, `nango_workspace.js`, `governance_workspace.js`, `apple_security_center.js`, `trustgraph_workspace.js`, `records_workspace.js`, `apple_governed_terminal.js`, `reports_workspace.js`, `apple_reports_preview.js`, `files_workspace.js` — preserve API calls; replace old view markup.

**Exit criteria**
- Every catalog item connects/disconnects through the real API or a labelled sample adapter.
- Security score reacts live to two-factor, session, audit and region settings.
- Terminal commands all work; terminal off hides it from menu/palette and direct links show the hidden card.
- Reports schedule line follows frequency/recipient/sections and formatting settings; Preview and Email me work.
- Gates green.

---

### Phase 4 — Polish, accessibility, tests, screenshots, old-UI cleanup

**Files to add**
- `tests/e2e/redesign_full.spec.ts` — every route at both viewports; click every control; no console errors, empty pages or overflow.
- `tests/e2e/redesign_screenshots.spec.ts` — light/dark, English/Arabic, every screen; output paths in the final report.
- `docs/ui-redesign/FINAL_REPORT.md` — old-to-new map, files added/removed, test results, STUBS, DECISIONS, anything not done.

**Files to modify**
- All new screens/CSS — a11y pass: focus trap/restore, labels, `aria-current`, `role="switch"`, contrast, 44 px targets, 360–1920 px, reduced motion.
- `web/index.html` — remove obsolete script tags, view sections and the old Ask URA bar.
- `web/styles.css` — remove rules used only by retired screens; keep shared legacy rules until the last screen is replaced.
- `web/app_shell.js` / `web/app_shell.css`, `web/settings_v2.*`, `web/settings_enterprise.js` — archive or remove only after legacy routes are retired.
- `tests/test_apple_*.py`, `tests/test_settings_v2_ui_smoke.py` — update exact-string assertions to the new names, or replace with behavioural checks. No test is deleted to hide a regression.
- `package.json`, `playwright.config.ts`, workflows — final gate wiring.

**Exit criteria**
- SPEC §11.1–§11.7 pass locally and in CI.
- No console errors, no horizontal overflow, no dead controls.
- Screenshots attached.
- Old UI code used by nothing is removed; anything retained is documented with a reason.
- Final report complete.

---

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `styles.css` is 223 KB and heavily overrides new components. | New styles live in `ui_kit.css` / `shell_v3.css`; load order is explicit; old rules are removed screen-by-screen, not globally. |
| 50 global scripts can collide when new modules load. | New modules use IIFEs and a single `window` namespace per module. `window.UI`, `window.Icon`, `window.AppShell` remain compatible. |
| Python tests assert exact old CSS/HTML strings. | Update them per phase with the same behaviour; keep a list in the phase summary. |
| Playwright currently needs staging and auth. | Phase 1 adds a local `webServer` and documents `BASE_URL`; sample-data screens are testable without backend auth. |
| Settings persistence has no user-preferences API. | Documented adapter: `/api/settings/v2` where mapped, versioned localStorage otherwise, `STUBS.md` entry. |
| Six approval endpoints have different shapes. | One normaliser in `rules.js` / `approvals_screen.js`; no backend contract change. |
| Multi-company formatting changes many screens. | Phase 2 formatter is the only path; Phase 3 screens consume it; a grep gate bans new `₹`/`toFixed`/`toLocaleString` in new files. |
| Hidden/removed screens might still be linked. | Hidden-page card (`pgLocked`), route aliases, and a redirect map documented in `DECISIONS.md`. |

---

## 8. Approval checkpoint

Phase 0 is complete. The plan above matches SPEC §12:

1. **Phase 1** — tokens, theme, icons, components, app shell.
2. **Phase 2** — settings registry/store, i18n/RTL, formatting, connected behaviour.
3. **Phase 3A** — Overview, Ask CEO, Approvals, Companies.
4. **Phase 3B** — five departments, AI Employees, Agents, Co-worker.
5. **Phase 3C** — Tools & Integrations, Security, Terminal, Reports.
6. **Phase 4** — polish, accessibility, tests, screenshots, old-UI cleanup.

No application code has been edited. Work will start on Phase 1 only after explicit approval.
