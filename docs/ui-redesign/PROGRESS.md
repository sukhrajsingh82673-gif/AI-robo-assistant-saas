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

## Stage 2 — intelligent service (pending)

## Stage 3 — background work and research (pending)

## Stage 4 — meetings (pending)

## Stage 5 — settings and tests (pending)
