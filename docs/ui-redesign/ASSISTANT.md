# URA Assistant — Stage 0 inventory and plan

Status: stage 0 (discovery only, no application code changed).

Sources read: `AGENTS.md` (not present on this branch), `docs/ui-redesign/SPEC.md`,
`docs/ui-redesign/prototype.html` (searched by `pgCeo`, `ceoReply`, `sendChat`,
`addTask`, `pgCoworker`, `cwRun`, `cwRequest`, `cwScope`), `PROGRESS.md`
(missing; created with this stage) and `AUDIT.md` (missing on this branch; the
audit exists only on `fix/green-baseline`). The prototype has no floating
launcher: the launcher and window in this task are new.

There is **one code base with three competing assistant surfaces** plus two
assistant-shaped screens. `web/index.html` mounts a fixed "Ask URA" bar, a
fixed floating ZONATA AI assistant, an "AI CEO" console with a chat box, and a
"Co-worker" screen. Only the floating assistant is wired to a real backend
(`/api/assistant/interact`); the Ask URA bar returns a fabricated answer.

**Co-worker correction (user decision).** The Co-worker is not an assistant to
delete. It is an agent/employee workspace with real mission, fleet, approval,
terminal and node capabilities. It keeps its menu entry, route, screen and
renderers; the URA Assistant is the conversational front door and links to the
Co-worker for execution work. The "exactly one assistant" rule therefore
removes the Ask URA bar, the floating assistant, and the AI CEO chat, not the
Co-worker.

## 1. Surface inventory

| # | Surface | Where | What it does today | Decision | Plan |
|---|---------|-------|--------------------|----------|------|
| 1 | Fixed "Ask URA" spotlight bar | `web/index.html:398-409`; `.ask-ura-bar-wrap` `web/app_shell.css:260-323`; `AppShell.openAskUra` / `submitAskUra` `web/app_shell.js:94-190`; `AppShell.init` Cmd/Ctrl+K `web/app_shell.js:15-23` | Fixed to the bottom-centre of every page. Opens a modal, then streams a **hard-coded** answer (`₹4,28,500`, "2 pending executive approvals", fake leak amount). Second Cmd/Ctrl+K listener conflicts with `app.js`. | **Remove** | Delete the markup, CSS and fake modal. Replace with the one URA Assistant launcher. Cmd/Ctrl+K stays search; Cmd/Ctrl+J opens the assistant. |
| 2 | Floating ZONATA AI assistant (FAB + flyout) | `web/index.html:431-432`; `web/floating_assistant.js` (919 lines); CSS `web/styles.css:4663-5200`; init `web/app.js:1068-1069`; `/assistant` route `web/app.js:713-719` | Draggable 4-corner FAB with persisted corner, flyout window, scope AUTO/PERSONAL/COMPANY, attachments, document cards, meeting cards, approval cards, emergency stop, status polling. Calls `/api/assistant/interact`, `/api/assistant/documents/upload`, `/api/assistant/emergency-stop`, `/api/approvals/{id}/decision`, `/api/v2/coworker/status`. | **Merge** | Keep and port the working logic (drag/snap/persist, upload, approvals, emergency stop, document/meeting cards, honest failure states) into the new window. Replace the old file, markup and CSS with `web/ura_assistant.js` / `.css` and mount it at `#uraAssistantRoot`. |
| 3 | "Coworker 2.0" screen (agent / employee) | Nav `web/index.html:79-85`; section `:357`; route `/coworker` `web/app.js:721,787-788`; `web/assistant_coworker_workspace.js` (Coworker 3.0 cockpit, mission pipeline, fleet HUD, approvals, governed terminal, activity, artifacts, nodes); `web/apple_coworker_assistant.js` | A full agent/employee workplace: autonomous missions, 7-stage pipeline, agent cloud, OpenCode/Hermes execution, security patrol, approvals, terminal and fleet nodes. The conversational sample in `apple_coworker_assistant.js` is not mounted by the router. | **Keep (do not remove)** | Keep the nav item, `view-coworker`, `/coworker` route, the workspace manager, its tabs, and all mission/terminal/fleet APIs. The Co-worker is an employee/agent surface, not an assistant: it stays a destination screen. From the URA Assistant, "Manage Co-worker" / delegation cards link to it. The assistant's Company scope uses the same coworker task/permission APIs. Do not delete `apple_coworker_assistant.js`; it stays as the Co-worker's execution narrative and must not be mounted as a second chat. |
| 4 | "AI CEO" console chat (the "Ask CEO" surface) | Nav `web/index.html:190-195`; `/ceo`, `/ai-ceo`, `/workspace/ai-ceo` `web/app.js:693-695`; chat box `web/ai_ceo_workspace.js:229-245`; `sendQuickCommand` → `/api/v8/chat` `:1667-1700`; Overview link `web/overview_workspace.js:1649-1650`; prototype `pgCeo`, `ceoReply`, `sendChat`, `addTask` | A chat box inside a 14-section executive console. Replies come from the real CEO conversation endpoint (`/api/v8/chat`) with model/evidence metadata. | **Remove chat; merge** | Delete the chat box, suggested chips and `/ceo` menu item. `/ceo` (and aliases) open the assistant instead. The assistant becomes the only place to chat with the CEO. |
| 5 | AI CEO console body (14 sections) | `web/ai_ceo_workspace.js` (strategy, objectives, departments, workforce, missions, KPIs, finance, risks, opportunities, decisions, approvals, evidence, reports, plus capital/contracts/scenarios/constitution) | Executive operating console backed by `/api/v8/*`. Not an assistant, but it would be lost if `/ceo` were deleted. | **Keep, re-home** | Preserve every section as a non-assistant screen at `/company/ceo-records` ("AI CEO records"), linked from Company and Governance. Remove only its chat pane and its "AI CEO" menu entry. List in the final report. |
| 6 | "AI CEO Meeting Room" | Route `/meeting`, `/ceo/meeting` `web/app.js:731,822-823`; `web/meeting_room_workspace.js` (648 lines); no menu item; real meeting APIs | Video/voice room with live transcript, decisions and reports. Dead route, no menu entry. | **Remove screen/route; merge** | Fold briefs, live notes/transcript, summaries, decisions and action items into the assistant's Meetings area. Old `/meeting` links open the assistant in Meetings. Keep all `/api/meetings/*` endpoints. |
| 7 | "AI Company Discovery" panel | `web/company_workspace.js:661+` | Onboarding discovery actions for websites/public data/documents. Not a chat assistant. | **Keep** | No change; it is part of the company intake flow. |
| 8 | `ai_orb.js` | `web/ai_orb.js`; used by auth, onboarding hero, entity tiles and the old Ask URA bar | Decorative assistant orb (idle/listening/speaking states). | **Keep, reuse** | Keep for onboarding/entity tiles. The new launcher uses the sparkle glyph and its own working ring; the orb is not a second assistant entry point. |
| 9 | Design preview link | `web/design_preview_workspace.js:343-345` | Button "Open Co-Worker Assistant (/assistant)". | **Update** | Point at the new assistant and rename the label. |
| 10 | Coworker execution sample | `web/apple_coworker_assistant.js` (INITIAL_MESSAGES) | A sample Personal/Company conversation with fabricated amounts. Not routed today; the real Co-worker screen is item 3. | **Keep file, not as an assistant** | Preserve the file and its Co-worker control vocabulary; do not mount it as a chat and do not show its sample amounts as live data. If it is ever surfaced, it must be clearly labelled sample content. |

## 2. Routes, menu, tab bar and palette

| Item | Where | Decision |
|------|-------|----------|
| `/assistant` | `web/app.js:713-719` | Keep as an alias that opens the launcher (no page). |
| `/ceo`, `/ai-ceo`, `/workspace/ai-ceo`, `/workspace/ceo` | `web/app.js:693-695` | Open the assistant (and remove the nav item). Console moves to `/company/ceo-records`. |
| `/coworker`, `/workspace/coworkers` | `web/app.js:721` | **Keep.** The Co-worker is an agent/employee screen, not an assistant surface. The assistant links to it. |
| `/meeting`, `/ceo/meeting` | `web/app.js:731` | Open the assistant in Meetings. |
| Nav "Coworker 2.0" | `web/index.html:79-85` | **Keep.** The Co-worker is a first-class agent/employee workspace. |
| Nav "AI CEO" | `web/index.html:190-195` | Replace with "AI CEO records" (same console, no chat). |
| Breadcrumbs `assistant`, `ceo`, `meeting` | `web/app.js:485-512` | Remove those assistant labels; the assistant is an overlay and never a breadcrumb. Keep `coworker` (a real screen). |
| Phone bottom tab bar | `web/index.html:435-452` (Home, Work, Records, Menu) | Five tabs with **Assistant in the middle**: Home, Work, Assistant, Records, Menu. It opens the bottom sheet. |
| Command palette | `web/index.html` `#globalSearchInput`; `/api/search` `web/app.js:930-1000` | Keep search; add the command "Ask the assistant" (and "Open assistant"). The palette closes before the window opens. |
| Keyboard | Cmd/Ctrl+K search (`app.js:1004-1011`, `app_shell.js:15-23`); no assistant shortcut | Keep one Cmd/Ctrl+K listener; add Cmd/Ctrl+J for the assistant; Esc minimises the window. |
| Top bar | `web/index.html:322-345` | Add a sparkle button (aria-label "Open URA Assistant") next to notifications/theme. |
| Translation keys | None exist on this branch | Add keys under the new assistant namespace (`assistant.*`), English first with fallback; remove the labels deleted above. |
| Bottom padding | `web/styles.css:5710` (70px mobile only) | Replace per-surface offsets with one global bottom clearance variable on the workspace scroll container (desktop and phone), so the last item scrolls clear of the launcher. |

## 3. Fixed / sticky overlays audit

Only the launcher, toasts and the phone tab bar may be fixed to the bottom.

| Element | Position | Decision |
|---------|----------|----------|
| `.ask-ura-bar-wrap` (`app_shell.css:260`) | fixed bottom | Remove. |
| `.floating-assistant-container` (`styles.css:4663`) | fixed bottom-left | Replace with `.ura-assistant-launcher` (draggable, corner-snapped). |
| `.mobile-bottom-nav` (`styles.css:5537`) | fixed bottom, phone only | Keep; add the middle Assistant tab. |
| `#toastContainer` (`styles.css:2198`) | fixed bottom-right | Keep (transient toast). |
| `.settings-toast` (`styles.css:7532`) | fixed bottom-right | Keep; it is a toast. |
| `.docked-save-bar` (`styles.css:9375`) | fixed bottom, Settings only | Keep but make it stack above the launcher clearance; it is not on every page. |
| `.floating-assistant-flyout` / `#assistantFlyout` | fixed, anchored to a corner | Remove; the new window is `position: fixed` only while open and docked/expanded, never page content. |
| `.apple-inspector-panel`, modal overlays, drawers | fixed edges | Keep (not bottom bars). |

## 4. Server-side assistant inventory

| Capability | Where | Reuse |
|------------|-------|-------|
| Unified interact pipeline (personal/company/document/meeting/ambiguous, storage boundary, persistence) | `core/assistant_service.py:291-510` (`FloatingAssistantService.interact`) | Extend; do not duplicate. |
| LLM-backed honest chat (internal search citations, degraded state when no model) | `core/assistant_service.py:1446-1574` (`handle_ai_chat`), `/api/assistant/chat` | Use as the answer path, add streaming. |
| CEO conversation | `/api/v8/chat` (used by `ai_ceo_workspace.js`) | Keep endpoint; call it for CEO-routed questions. |
| Documents: upload/search/generate/download | `/api/assistant/documents/*` (`api_server.py:2425-2452, 6245-6318`) | Reuse for `+` attachments. |
| Meetings | `/api/meetings/*`, `/api/assistant/meetings/schedule`, `core/meeting_service.py` | Reuse; port UI into the assistant. |
| Coworker task lifecycle + permission tiers | `/api/assistant/coworker/task(s)`, `core/assistant_service.py:1576-1773`, table `coworker_tasks` | Reuse for Company scope; add the `cowork` approval. |
| Calendar | `core/calendar_provider.py` (Google Calendar via `ZONATA_GOOGLE_CALENDAR_*` env) | Reuse behind an adapter; no key in the browser. |
| Approvals | `POST /api/approvals`, `GET /api/approvals`, decision endpoints | Reuse for assistant confirmations and permission requests. |
| Model provider | `core/llm_runtime.py`, `core/neon_ai_gateway.py`, `core/model_gateway.py` (registry mentions `claude-3-7-sonnet`; no assistant UI is labelled Sonnet/Claude) | Use the existing runtime/model selection; keys stay server-side via env. |
| Conversation memory | `assistant_messages` (`core/db.py:4073`) | Add search/forget/clear endpoints and retention. |
| Web search / transcription | **None** | Build adapters with a labelled sample provider; list in `STUBS.md`. |
| Background jobs | No assistant job store (`durable_workflow_runtime.py` exists) | Add `assistant_jobs` + worker; max 3 concurrent. |

## 5. Plan

### Stage 1 — one assistant shell
- New `web/ura_assistant.js` + `web/ura_assistant.css` (loaded after the shell):
  - One 52px glass launcher with sparkle, drag by pointer/touch, corner/edge
    snap with spring, persisted per user, states idle/working/needs-you,
    visibility setting.
  - One non-modal window (`role="dialog"`), 380×560 (min 320×420), title-bar
    drag, corner resize, dock/expand/minimise/close, persisted mode/size/place.
  - Phone: no launcher; middle tab opens a two-height bottom sheet with
    swipe-down.
  - Top bar sparkle, Cmd/Ctrl+J, palette command, `/assistant`, `/ceo`,
    `/coworker`, `/meeting` aliases.
  - Global bottom clearance on the workspace scroll area.
- Remove the Ask URA bar and fake modal, the AI CEO chat box and its menu
  entry (the console moves to `/company/ceo-records`), and the Meeting Room
  route. **Do not remove the Co-worker screen, nav item, route or workspace.**
  It remains the agent/employee execution surface and the assistant links to it.
- Keep `apple_coworker_assistant.js` for the Co-worker's execution narrative but
  do not mount it as a second assistant chat.
- Re-home the CEO console at `/company/ceo-records`.
- Update `tests/assistant_floating_ui_test.js` and add a jsdom smoke test for
  launcher/window modes, drag/snap persistence, keyboard and removal of old
  surfaces.

### Stage 2 — one intelligent service
- Extend `core/assistant_service.py` with a streaming orchestrator
  (`assistant_stream`) and a typed tool registry:
  `navigate`, `query_data`, `create_task`/`delegate`, `decide_approval`,
  `change_setting`, `run_security_scan`, `generate_report`/`email_report`,
  `install_agent`, `connect_integration`, `run_terminal`.
- Server-Sent Events over authenticated `fetch` (not `EventSource`), each tool
  step emitted as a typed event and written to activity; risky tools call the
  existing `needsOwner`/autonomy/payment-limit rules and wait for an in-window
  Approve/Decline.
- Page context chip from `{route, company, selection}` sent by the client.
- Scope Personal/Company; Company needs the `cowork` approval
  (`POST /api/approvals`, kind `cowork`).
- `@CEO/@COO/@CMO/@CTO/@CFO/@CHRO` routing with "Answered by …" labels.
- Memory endpoints (list/search/remember/forget/clear) over
  `assistant_messages`, retention from the activity-log setting.

### Stage 3 — foreground/background and research
- `assistant_jobs` table + worker (max 3), progress events, launcher badge,
  Jobs list, pause/cancel/retry, result card and bell notification.
- "Watch me" steps with pause/take-over/stop; "Run in background" survives
  reload.
- `core/ura_assistant/adapters/web_search.py`: `WebSearchProvider` interface;
  real provider only when configured server-side, `SampleWebSearchProvider`
  behind `URA_ASSISTANT_WEB_SEARCH_PROVIDER=sample` and a visible sample label;
  default "web access not configured". Web-access setting, allow/block lists,
  source cards and numbered citations.

### Stage 4 — meetings
- `CalendarAdapter` around `core/calendar_provider.py`; pre-meeting brief from
  company data/decisions; join/listen, live notes, summary, decisions, action
  items → tasks/approvals; recording banner and announcement setting;
  searchable meeting library.
- `TranscriptionAdapter` with a sample provider when no provider is configured.

### Stage 5 — settings and tests
- Assistant settings category with control, plain-language hint, suggestion and
  reason per item, plus "Use all suggestions": show button, open as, default
  scope, background work, web access, meetings, announce recording,
  confirmations, remember conversations. Autonomy, payment limit, tone and
  Terminal settings continue to apply.
- E2E coverage (a)-(l) from the task, runnable locally (jsdom fallback when no
  Chromium), screenshots in light/dark.

## 6. Adapters and STUBS

To be listed in `STUBS.md` when built:

| Need | Adapter | Default behaviour |
|------|---------|-------------------|
| Web search/read | `WebSearchProvider` | Not connected; honest "web access is not configured". Sample provider only when explicitly enabled and visibly labelled. |
| Calendar | `CalendarAdapter` | Real Google Calendar when env is configured; otherwise "calendar not connected" (no fake event). |
| Transcription | `TranscriptionAdapter` | No transcript; browser speech input may still be used for composing. Sample transcript only when explicitly enabled and labelled. |
| Model | Existing `llm_runtime` | Uses the app's configured provider/model; no key in the front end. |

## 7. Fake-data findings to remove with the merge

- `web/app_shell.js:169-173` fabricated profit/approvals/leak answer.
- `web/apple_coworker_assistant.js` sample conversation: keep the file for the
  Co-worker, but never mount it as a chat or present its sample amounts as live.
- `web/ceo_command_center.js:61+` hard-coded department metrics (adjacent, not
  an assistant; flag for the redesign backlog).
- `web/ai_ceo_workspace.js` shows `model_used` from the API; keep only real
  metadata from `/api/v8/chat`.

## 8. Risks and decisions

- **Deleting `/ceo` must not delete the console.** Decision: re-home the
  non-chat console at `/company/ceo-records`; `/ceo` becomes an assistant alias.
- **Two fixed elements until the swap.** The new launcher and the old bar must
  not coexist after stage 1; remove the old bar in the same commit.
- **Meeting Room has no menu entry**, so removing its route is low risk; all
  API calls remain.
- **No i18n exists on this branch.** Add English keys with fallback; do not
  claim full translations until the other language files exist.
- **No Playwright browser in this environment.** Write the Playwright spec and
  a jsdom-based local smoke gate; screenshots are an unfinished item if
  Chromium remains unavailable.
