# Stubs and unconnected states

The new URA UI uses **no sample data by default**. `window.USE_SAMPLE_DATA` in
`web/app.js` is the single switch for the named demo samples listed below, and
it defaults to `false`. Every amount, record and reply shown by the new shell
comes from a live API response, or the screen says it is not connected.

This file lists what is still missing, gated, or explicitly unconnected, so
nothing is mistaken for live data.

## Sample-only content behind `USE_SAMPLE_DATA`

`window.USE_SAMPLE_DATA = false` is set in `web/app.js`. Turning it on is a demo
mode, not a fallback. These named samples are gated:

| Sample | Where | What happens by default |
|---|---|---|
| `AppleSalesBoard` deal cards | Marketing > Pipeline (`crm_sales_workspace.js`) | The real `/api/crm/deals` pipeline renders instead. |
| `AppleReportsPreview` report catalog | Reports (`reports_workspace.js`) | The real `/api/reports` list renders instead, with an empty state when there are no reports. |
| `AppleCoworkerAssistant` sample conversation | Legacy assistant renderer | The real co-worker cockpit renders; the sample chat is not used. |

`DepartmentWorkspace` still contains a static department showcase, but it is not
mounted by the new menu; the department screens mount the live workspaces
(`OperationsWorkspace`, `CrmWorkspace`, `FinanceWorkspace`, and so on). It will
be deleted or rebuilt in phase 3B.

## Not connected (honest empty states)

| Area | What the UI shows | Why |
|---|---|---|
| Currency conversion | The real source amount with the suffix `(FX not connected)` when the display currency differs from the company currency | The repo has no exchange-rate source and no `RATES` table. Inventing rates would present fake money. |
| Team management | "Team invites are not connected" and a one-owner explanation in Settings > Menu and team | There is no users/team listing API. No fake roster or invite is shown. |
| Company time zones | A blank clock for companies without a stored time zone | The UI does not guess a zone from the country or currency. |
| Overview financials | "Not connected" under revenue and profit when `financial.has_data` is false | No ledger has been connected for that company. The UI does not substitute a number. |
| Overview lead pipeline | "Connect a CRM" when `sales.has_data` is false | No CRM is connected for that company. |

## Backend limitations the UI does not hide or fix

- `core/ai_ceo_v8.py` still answers some Ask CEO intents from deterministic
  heuristics rather than a model call. The UI sends the real `/api/v8/chat`
  request and relays the reply; it does not invent or embellish answers. If the
  endpoint is unreachable, the screen says so and offers Retry.
- `core/overview_service.py` still derives some fields synthetically
  (`gross_profit`, `revenue_growth_pct`, cash, and some trend points). The new
  Overview deliberately does not display those fields. Fixing the service is a
  backend change outside this redesign.
- A freshly registered owner has no company in the operating portfolio until
  onboarding completes. The UI shows the empty state and the company flows
  instead of inventing a company. The UI smoke test onboards a company before
  it asserts the Companies screen.

## Storage and persistence

- UI settings persist in `localStorage['ura.ui.settings.v1']`, not through a
  user-preferences API. This is a deliberate fallback: `/api/settings/v2` is a
  governed, approval-gated registry whose keys do not map 1:1 to the UI keys.
  See `DECISIONS.md`.
- Settings are per browser profile until a user-preferences API is wired.

## Verification gaps

- Playwright browser binaries could not be installed in this environment, so
  the screenshot requirement (light/dark, English/Arabic) and the browser e2e
  run are still open. `tests/e2e/test_user_journeys.spec.ts` and
  `playwright.config.ts` are unchanged and still target staging.
- Until then, `tests/test_ui_shell_smoke.py` (jsdom against a real server) is
  the automated UI gate.

## Legacy screens

Department, workforce, tools, Terminal and Reports screens currently mount the
existing workspace renderers in tabs. Those renderers use the real backend but
keep their old visual style; they will be rebuilt in phases 3B and 3C. They
still contain hard-coded `₹` symbols and ad-hoc number formatting, which those
phases replace with the shared formatting module. Their amounts come from the
API, not from sample records.
