# Decisions

Choices made while rebuilding the URA front end. Newest first.

## Stack and structure

- **Stay on the existing stack.** Vanilla classic scripts, plain CSS, the
  existing hash router, `window.UI`, `window.Icon`, `window.AppShell`,
  `window.navigateTo`, auth and workspace renderers. No framework, bundler,
  router or state library was introduced.
- **Add a thin `ura_*` layer over the old app.** `web/ura_ui.css`,
  `ura_core.js`, `ura_settings.js`, `ura_screens.js` and `ura_shell.js` own the
  new shell, screens and tokens. Old workspaces keep running inside
  `.view-section` hosts, so no business logic was rewritten or deleted.
- **Keep the legacy hash router and wrap it.** `ura_screens.js` replaces
  `window.handleRoute` with a resolver for the 17 target screens and falls back
  to the legacy router for auth routes, sub-routes and unknown paths. Legacy
  URLs remain reachable, and back/forward keep working.
- **Reuse the 41 `.view-section` containers.** Renamed screens point at their
  nearest existing host (`view-technology` and `view-security` were added).
  Department, workforce, tools and reports screens show the existing workspace
  renderers in tabs rather than duplicating them.
- **New module boundaries.** `URACore` owns settings storage, i18n and
  formatting; `URASettings` owns the registry and settings screens;
  `URAScreens` owns routing and screen renderers; `URAShell` owns the sidebar,
  top bar, tab bar, palette, sheets and toasts. Scripts load in that order as
  classic scripts.

## Data honesty

- **No fabricated answers or amounts.** The old Ask URA modal invented a
  `₹4,28,500` answer and "2 pending executive approvals". Ask URA now navigates
  to Ask CEO, which calls the real `/api/v8/chat` endpoint. On failure it says
  the service is unreachable and offers Retry; it never shows a made-up answer.
- **Overview ignores backend-synthetic fields.** `/api/overview/snapshot` still
  derives `gross_profit`, `revenue_growth_pct`, cash and some trend points
  synthetically. The new Overview does not display them. It shows only fields
  the service marks as having data, otherwise "Not connected".
- **No FX invention.** There is no exchange-rate source in the repo. When the
  display currency differs from the source currency, the real source amount is
  shown with the suffix `(FX not connected)`. No sample rates were added.
- **Company clocks are not guessed.** A company without a stored time zone
  gets a blank clock, not a capital-city guess.
- **Company cards use real snapshots.** Per-company country, currency, phase,
  health, revenue and profit come from `/api/overview/snapshot?company_id=…`
  with a five-minute in-memory cache. Missing data shows an em dash.
- **Security score is honest.** The new score is computed from the saved UI
  settings plus the real number of high-risk pending approvals. The old
  `apple_security_center.js` fake counters are not used, and no sample findings
  are displayed.
- **Team management says it is not connected.** The repo has no users/team
  listing API. The Settings > Menu and team screen shows an explicit
  "not connected" state instead of a fake roster or invite flow.
- **One sample switch, off by default.** `window.USE_SAMPLE_DATA` is `false` in
  `web/app.js`. It gates only the named demo samples (`AppleSalesBoard`,
  `AppleReportsPreview`, `AppleCoworkerAssistant`); with it off, those screens
  use real API data. `STUBS.md` lists them.

## Settings and behaviour

- **Versioned local store.** Settings live in
  `localStorage['ura.ui.settings.v1']`. The existing `/api/settings/v2` registry
  is approval-gated and does not map cleanly to these keys, so it was not
  wired; a future user-preferences API should migrate this store instead of
  forking it.
- **Theme bridge.** The theme is mirrored to `zonata_theme_preference` so the
  existing `ThemeManager` and legacy screens agree with the new shell.
- **One settings registry.** All seven categories are rendered from the same
  schema, including hints and `suggest(context)`. "Use all suggestions" applies
  the whole category and shows a toast.
- **Connected behaviour is centralised.** Formatting (`t`, money, number, date,
  time), approvals (`needsOwner`), notifications and quiet hours, reports, the
  security score, Terminal visibility and menu hiding all read the same store.
- **Six languages, English fallback.** en, hi, pa, ar, es and fr dictionaries
  cover the menu, group names, page titles, greetings and common actions.
  Arabic sets `dir="rtl"`.

## Shell and screens

- **Hidden pages get a locked card.** A hidden screen opened by link or search
  shows "This screen is hidden" with "Show it again" and "Back to Overview",
  never a silent redirect.
- **Legacy modal retained as a fallback.** `AppShell.openAskUraModal()` keeps the
  old modal reachable if the URA layer fails to load, but the normal path is
  the Ask CEO screen.
- **Icons extend the existing set.** Missing glyphs (`globe`, `file-text`,
  arrows, `refresh-cw`, chevrons, `alert-circle`) were added to `web/icons.js`
  rather than inlined.
- **Container arguments on legacy renderers.** `CompanyWorkspace.render` and
  `ToolsFactory.render` now accept an optional container so the new router can
  mount them without moving the old code.

## Testing

- **A real UI smoke gate, not static string checks.**
  `tests/ui_shell_smoke.js` boots the real page with jsdom against a live
  server and checks the shell, live KPIs, settings persistence, palette
  filtering, Companies, Security, Approvals, the Terminal lock, and Arabic/RTL.
  `tests/test_ui_shell_smoke.py` starts an isolated server, registers an owner
  and onboards a company, then runs the script. `npm run test:ui` runs it.
- **The wrapper owns the server lifecycle.** It allocates a free port, uses a
  temporary database under `/tmp`, waits for `/api/v1/health`, and terminates
  the server in `finally`. The Python test skips only when Node or jsdom is
  unavailable.
- **Playwright e2e is not part of the gate yet.** Browser binaries could not be
  installed in this environment (`npx playwright install chromium` timed out),
  so the existing Playwright config was left untouched. The jsdom gate covers
  the same shell behaviours until a browser is available.

## Repository state

- Work started from the green baseline on `fix/green-baseline`
  (`d9555aa`, PR #9). Phase 1 changes are committed on top of it.
