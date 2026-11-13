# URA assistant consolidation — progress

Branch: `ui-redesign`. Never pushed to `main`.

## Stage 0 — discovery and plan (complete, no app code)

**Found.** Four assistant entry points and two assistant screens exist at the
same time:

1. fixed "Ask URA" bar (fabricated answer);
2. fixed draggable ZONATA AI assistant (real `/api/assistant/interact`);
3. "Coworker 2.0" screen and route;
4. "AI CEO" console with a chat box and `/api/v8/chat`.

The Meeting Room (`/meeting`) is a fifth, menu-less surface. Full inventory,
route/menu/tab/palette audit, fixed-overlay audit, server capabilities and the
stage-by-stage plan are in `docs/ui-redesign/ASSISTANT.md`.

**Decisions.**
- One launcher/window. Old `/assistant`, `/ceo` and `/meeting` links open it.
- **The Co-worker stays.** It is an agent/employee workspace with real mission,
  fleet, approval, terminal and node capabilities. Keep its menu entry,
  `view-coworker`, `/coworker` route, `assistant_coworker_workspace.js` and
  `apple_coworker_assistant.js`. The assistant links to it; it is not mounted as
  a second chat.
- The CEO console's non-chat sections are preserved at `/company/ceo-records`;
  only its chat and menu entry are removed.
- Reuse `FloatingAssistantService`, the coworker task/permission API, the
  meetings API, the calendar provider and `llm_runtime`; build a streaming tool
  layer, job store, web-search adapter and transcription adapter on top.
- Sample providers only when explicitly enabled and visibly labelled; listed in
  `STUBS.md` when built.

**Gates (baseline, after the docs change).**
- `node --check` across `web/*.js`: pass.
- `npm run build`: pass.
- `node tests/assistant_floating_ui_test.js`: 14 passed.
- No `typecheck` or `lint` npm script exists on this branch; both are added in
  stage 1 so later stages have a real gate.

**Files changed in stage 0.**
- added `docs/ui-redesign/ASSISTANT.md`
- added `docs/ui-redesign/PROGRESS.md`

**Next.** Stage 1: remove the Ask URA bar and AI CEO chat, add the launcher/window
and aliases, one global bottom clearance, update tests. The Co-worker screen is
preserved.

## Stage 1 — the one shell (complete)

**Removed.** The fixed Ask URA bar and its fabricated modal, the old
`floating_assistant.js` flyout, and the AI CEO chat box/suggested chips. The
duplicate Cmd/Ctrl+K listener moved out of `app_shell.js`. Old assistant CSS
blocks were removed so no stale fixed-bottom bar remains.

**Kept (Co-worker correction).** `Coworker 2.0` nav item, `view-coworker`,
`/coworker`, `assistant_coworker_workspace.js` and
`apple_coworker_assistant.js` are untouched. The Co-worker remains an
employee/agent workspace; the assistant opens it from the “+” menu.

**Built.**
- `web/ura_assistant.js` + `web/ura_assistant.css`: one 52px glass launcher
  with eight snap anchors, pointer drag, state ring/badge/dot, and one
  non-modal `role="dialog"` window (380×560, min 320×420, 280ms spring).
- Window controls: dock, expand, minimise (Esc), close; title-bar drag and
  corner resize; size/place/mode/scope persisted per user.
- Phone: no launcher; the middle bottom-bar tab opens a two-height sheet with
  swipe-down minimise.
- Entry points: top-bar sparkle, Ctrl/Cmd+J, command-palette “Ask the
  assistant”, `/assistant`, `/ceo`, `/ai-ceo`, `/ceo/meeting`, `/meeting`.
- The AI CEO console is re-homed at `/company/ceo-records` and its menu item is
  now “AI CEO Records” (no chat).
- One global `.workspace-content` bottom clearance (104px desktop, 80px phone)
  replacing the old per-page/mobile 70px offset.
- Uploads still go to `/api/assistant/documents/upload` before being attached;
  document, meeting, workforce and approval cards keep their honest states;
  screen observation and emergency stop keep their previous behaviour.
- New gates: `npm run typecheck`, `npm run lint`, `npm run test:assistant`.

**Gates (after the final Stage 1 edit).**
- `npm run typecheck`: 60 JavaScript files parsed.
- `npm run lint`: assistant consolidation checks passed.
- `npm run build`: passed.
- `npm run test:assistant`: 18 static contract tests + 8 jsdom checks passed.
- Playwright/Chromium is not installed in this environment, so browser
  screenshots and the Playwright e2e run remain pending (see Stage 5).

## Stage 2 — intelligent service (complete)

**One service.** `core/ura_assistant_service.py` now owns the assistant brain:
deterministic planning, typed tools, scope gating, agent routing, memory and an
NDJSON event stream. The browser (`web/ura_assistant.js`) consumes
`POST /api/assistant/stream` incrementally and falls back to
`POST /api/assistant/interact` on an older server.

**Stream events.** `context`, `agent`, `tool` (running/done/blocked), `permission`,
`confirm`, `answer` chunks, `card`, `done`, `error`. The HTTP layer emits chunked
`application/x-ndjson` (`_start_ndjson` / `_write_ndjson` / `_end_ndjson`).

**Typed tools** (`TOOL_SPECS`, all with a JSON parameter schema, `mutating` and
`scope`): `navigate`, `query_data`, `delegate_task`, `decide_approval`,
`change_setting`, `run_security_scan`, `generate_report`, `install_agent`,
`connect_integration`, `run_terminal`. Each tool delegates to the existing
implementation (`GlobalSearchEngine`, `create_coworker_task`,`ApprovalPipeline`,
`settings_service`, `DefensiveCybersecurityMonitor`, `EnterpriseReportsEngine`,
`EnterpriseAgentFactory`). Nothing is fabricated: a refused or unavailable tool
returns a blocked result.

**Planning is deterministic.** A regex/intent map picks the executing tool; the
model may compose prose but never chooses an executing tool. Navigation
intent wins over search so "open reports" is a screen change.

**App awareness.** Every request carries `page_context` (screen key, hash path);
the service names the current screen in its answer and the window shows a
"Looking at …" chip.

**Personal / Company scope.** Personal is the private sandbox. Company scope is
locked until an `APPROVED` approval whose `action_desc` contains
"URA Assistant" and "(kind: cowork)" exists; otherwise the stream emits a
`permission` event and stops without reading company data. "Ask the AI CEO" files
the cowork request through `POST /api/assistant/permission`.

**Agent routing.** `@CEO/@COO/@CMO/@CTO/@CFO/@CHRO` (and "chief …" aliases) resolve
to a role chip, change the answer's remit, and route delegation/query arguments.
An unknown role is refused rather than silently ignored.

**Memory.** Explicit only: `assistant_memory` table plus
`GET/POST /api/assistant/memory` and
`DELETE /api/assistant/memory[/{id}]`. "Remember this", "Saved memory" and
"Forget all" in the "+" menu. Scoped per user (and per company for company
memory); the model never writes memory on its own.

**Safety.** Mutating tools never execute on the first turn. The stream returns a
`confirm` event with a preview and risk; the UI renders a confirmation card and
only `POST /api/assistant/tool` executes it, re-checking scope, approver role and
the global killswitch. Terminal and integration connections are explicit
handoffs to their governed screens.

**Gates (after the final Stage 2 edit).**
- `npm run typecheck`: 60 JavaScript files parsed.
- `npm run lint`: assistant consolidation checks passed.
- `npm run build`: passed.
- `npm run test:assistant`: 24 static contract tests + 10 jsdom checks +
  18 pytest service tests passed.
- Playwright/Chromium remains unavailable; browser e2e/screenshots are Stage 5.

## Stage 3 — background work and research (complete)

**Jobs.** `assistant_jobs` (schema in `core/db.py`, store/runner in
`core/ura_assistant_jobs.py`) keeps a job across reloads. At most three may be
active (queued, running or paused) per user; the limit is enforced on the
server. Every job records progress, steps, result, citations and a plain error.
Pause, resume, cancel, retry and take-over act on the stored row; the worker
checks the row between steps, so a pause from another request really stops
progress. A job left `RUNNING` by a server restart is marked `FAILED` with
"the server restarted" when jobs are next read — never a stale success.

**Kinds.** `research` (web) and `query` (live company data). Mutating work stays
in the foreground behind the existing confirmation gate; it is never queued as
a background job.

**Web research.** `core/ura_assistant_web.py` defines a typed
`WebSearchProvider` with `NoWebSearchProvider` (default), `TavilySearchProvider`,
`BraveSearchProvider` and a clearly-labelled `SampleWebSearchProvider` (only with
`URA_ASSISTANT_WEB_SEARCH_PROVIDER=sample`). Keys live in `TAVILY_API_KEY` /
`BRAVE_SEARCH_API_KEY` on the server only. Results are filtered by the company
policy (`off` / `allowlist` / `open`, plus a block list) and every excluded
source is reported with its reason. Sample results carry `sample=true` and are
labelled in the UI.

**Endpoints.** `GET/POST /api/assistant/jobs`, `GET /api/assistant/jobs/{id}`,
`POST /api/assistant/jobs/{id}/action`, `POST /api/assistant/jobs/{id}/watch`
(NDJSON snapshots), `POST /api/assistant/jobs/inbox/seen`,
`GET/POST /api/assistant/web-access`.

**UI.** Jobs bell with unseen badge, jobs panel (status, progress bar, last
steps, actions), "Watch me" stream, "Run in background", "Research the web",
web-access panel with mode and lists. `WEB_SOURCES`, `JOB_RESULT` and `HANDOFF`
cards; citation links are rendered only when a URL exists; take-over pauses the
job and hands off to the preserved Co-worker.

**Gates (after the final Stage 3 edit).**
- `npm run typecheck`: 60 JavaScript files parsed.
- `npm run lint`: assistant consolidation checks passed.
- `npm run build`: passed.
- `npm run test:assistant`: 29 static contract tests + 17 jsdom checks +
  41 pytest service/jobs tests passed.
- Playwright/Chromium remains unavailable; browser e2e/screenshots are Stage 5.

## Stage 4 — meetings (pending)

## Stage 5 — settings and tests (pending)
