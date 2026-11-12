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

## Stage 1 — shell (pending)

## Stage 2 — intelligent service (pending)

## Stage 3 — background work and research (pending)

## Stage 4 — meetings (pending)

## Stage 5 — settings and tests (pending)
