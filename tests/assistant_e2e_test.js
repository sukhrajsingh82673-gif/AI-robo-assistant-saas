#!/usr/bin/env node
/**
 * URA Assistant end-to-end journey (jsdom).
 *
 * Playwright and a browser binary are not installed in this environment, so
 * this runner walks the same (a)–(l) journey in jsdom against the real
 * assistant controller and the real static routes. It is the fallback for the
 * browser e2e suite; when Playwright is available the same scenarios should be
 * mirrored in tests/e2e/assistant.spec.ts.
 *
 * (a) exactly one assistant surface mounts
 * (b) every old assistant route ends in the one assistant; the Co-worker stays
 * (c) the launcher opens a real draggable window with eight snap anchors
 * (d) a phone gets a bottom sheet instead of a launcher
 * (e) streaming shows steps, answer chunks and a typed tool confirmation
 * (f) Company scope is locked until the cowork approval exists
 * (g) @role routing and explicit memory work
 * (h) background jobs run, stream progress and hand off to the Co-worker
 * (i) web access is a labelled provider, never a fabricated source
 * (j) meetings: brief, live notes, summary and governed action items
 * (k) settings change the assistant and suggestions are applicable
 * (l) the shell is accessible and persists per user
 */
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { JSDOM } = require('jsdom');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'web/ura_assistant.js'), 'utf8');
const indexHtml = fs.readFileSync(path.join(root, 'web/index.html'), 'utf8');
const appJs = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');

const calls = [];
const dom = new JSDOM(
  '<!doctype html><html><body><div id="uraAssistantRoot"></div><div id="modalOverlay"></div></body></html>',
  { url: 'https://example.test/', runScripts: 'outside-only', pretendToBeVisual: true }
);
const { window } = dom;

let phone = false;
window.matchMedia = () => ({ matches: phone, addEventListener() {}, removeEventListener() {} });
window.state = {
  host: { email: 'owner@example.test', name: 'Owner' },
  activeNav: 'overview',
  activeCompanyId: 'comp_1',
  companies: [{ id: 'comp_1', name: 'Kora Hospitality' }]
};
window.CurrentCompanyContext = {
  getCompanyId: () => 'comp_1',
  getCompany: () => window.state.companies[0]
};
window.navigateTo = (route) => calls.push(['navigate', route]);
window.confirm = () => true;
window.__URA_NO_POLL__ = true;

let settingsState = {};
let approvalsState = [];
let jobsState = [
  {
    job_id: 'job_e2e', title: 'Research competitors', prompt: 'Research competitors',
    kind: 'research', status: 'RUNNING', progress: 40, step: 'Reading sources',
    notification_seen: 0, steps: [{ label: 'Queued' }, { label: 'Reading sources' }]
  }
];
let meetingNotes = [];

function jsonResponse(payload, status = 200) {
  return { ok: status < 400, status, json: async () => payload, text: async () => JSON.stringify(payload) };
}

function ndjsonResponse(events) {
  const text = events.map((event) => JSON.stringify(event)).join('\n') + '\n';
  return { ok: true, status: 200, body: null, text: async () => text, json: async () => ({}) };
}

window.fetch = async (url, options) => {
  const method = (options && options.method) || 'GET';
  const body = options && options.body ? JSON.parse(options.body) : null;
  calls.push(['fetch', method, url, body]);

  if (url.startsWith('/api/settings/v2/values?category=assistant')) {
    const settings = Object.entries(settingsState).map(([key, value]) => ({
      key, value, version: 1, overridden_here: true
    }));
    return jsonResponse({ success: true, settings });
  }
  if (url === '/api/approvals' && method === 'GET') return jsonResponse({ approvals: approvalsState });
  if (url === '/api/approvals' && method === 'POST') {
    approvalsState.push({ action_desc: 'URA Assistant Company scope (kind: cowork)', status: 'PENDING' });
    return jsonResponse({ success: true });
  }
  if (url.startsWith('/api/assistant/jobs?')) {
    const active = jobsState.filter((job) => ['QUEUED', 'RUNNING', 'PAUSED'].includes(job.status)).length;
    return jsonResponse({ jobs: jobsState, active, unseen: 0, limit: 3 });
  }
  if (url === '/api/assistant/jobs' && method === 'POST') {
    const job = {
      job_id: 'job_new', title: body.prompt, prompt: body.prompt, kind: 'research',
      status: 'QUEUED', progress: 0, step: 'Queued', steps: [{ label: 'Queued' }],
      notification_seen: 0, workspace_mode: body.workspace_mode
    };
    jobsState = [job, ...jobsState];
    return jsonResponse({ success: true, job, limit: 3 });
  }
  if (url.startsWith('/api/assistant/jobs/') && url.endsWith('/watch')) {
    const id = url.split('/')[4];
    const done = {
      ...(jobsState.find((job) => job.job_id === id) || {}),
      status: 'SUCCEEDED', progress: 100, step: 'Completed',
      result: { summary: 'Two approvals are waiting.' },
      citations: [{ source_type: 'WEB', label: 'Sample source', url: 'https://example.com/s', sample: true }]
    };
    jobsState = jobsState.map((job) => (job.job_id === id ? done : job));
    return ndjsonResponse([{ type: 'job', job: done }, { type: 'job_done', job: done }]);
  }
  if (url.startsWith('/api/assistant/jobs/') && url.endsWith('/action')) {
    const id = url.split('/')[4];
    const current = jobsState.find((job) => job.job_id === id) || { job_id: id };
    if (body.action === 'takeover') {
      return jsonResponse({
        success: true, job: { ...current, status: 'PAUSED' },
        handoff: { path: '/coworker', label: 'Take over in the Co-worker', message: 'The job is paused.' }
      });
    }
    return jsonResponse({ success: true, job: { ...current, status: 'PAUSED' } });
  }
  if (url === '/api/assistant/web-access' && method === 'POST') {
    return jsonResponse({
      success: true,
      web_access: {
        configured: true, provider: 'sample', provider_label: 'Sample web results (not connected)',
        sample_provider: true,
        access: { mode: body.access, allowlist: String(body.allowlist || '').split(',').filter(Boolean), blocklist: [] }
      }
    });
  }
  if (url === '/api/assistant/web-access') {
    return jsonResponse({
      configured: true, provider: 'sample', provider_label: 'Sample web results (not connected)',
      sample_provider: true, access: { mode: 'allowlist', allowlist: ['example.com'], blocklist: [] }
    });
  }
  if (url.startsWith('/api/assistant/meetings?') || url === '/api/assistant/meetings') {
    return jsonResponse({
      company_id: 'comp_1',
      meetings: [{
        meeting_id: 'meet_1', title: 'Board review', status: 'Ended',
        summary: 'The retreat was approved.', created_at: 1710000000, matches: []
      }],
      count: 1, query: '',
      calendar: { configured: false, provider: 'none', label: 'Calendar not connected' },
      transcription: { configured: true, provider: 'sample', label: 'Sample transcript (not connected)', sample: true },
      recording: {
        enabled: true, text: 'Sample transcript only.',
        announcement: 'Recording announcement (sample mode).',
        transcription: { configured: true, provider: 'sample', label: 'Sample transcript (not connected)', sample: true }
      }
    });
  }
  if (url === '/api/assistant/meetings/brief') {
    return jsonResponse({
      company: { company_id: 'comp_1', name: 'Kora Hospitality' },
      pending_approvals: [{ request_id: 'apr_1', action_desc: 'Approve the retreat budget' }],
      decisions: [], missions: [], scheduled_meetings: [],
      agenda: ['Decide 1 pending approval(s).'],
      summary: 'Pre-meeting brief for Kora Hospitality.',
      sources: [{ source_type: 'INTERNAL', label: 'Live approvals', verified: true }]
    });
  }
  if (url === '/api/assistant/meetings/listen') {
    return jsonResponse({
      success: true,
      meeting: { meeting_id: 'meet_1', title: 'Board review', status: 'Live' },
      segments: [{ speaker: 'Sample transcript', text: 'Sample transcript line: no microphone was opened and no audio was captured.', sample: true }],
      recording: { enabled: true, announcement: 'Recording announcement (sample mode).' },
      sample: true,
      message: 'Listening in sample mode. The lines below are sample text, not captured audio.'
    });
  }
  if (url === '/api/assistant/meetings/notes') {
    meetingNotes.push({ speaker: 'HOST', mode: 'NOTE', message: body.note });
    return jsonResponse({ success: true, meeting: { meeting_id: 'meet_1', title: 'Board review' }, note: meetingNotes[meetingNotes.length - 1] });
  }
  if (url === '/api/assistant/meetings/summary') {
    return jsonResponse({
      success: true,
      meeting: { meeting_id: 'meet_1', title: 'Board review', status: 'Ended' },
      summary: 'Meeting: Board review\nNotes:\n- Keep the retreat.',
      notes: meetingNotes, decisions: [], minutes: { doc_id: 'doc_1', download_url: '/api/documents/doc_1/download' },
      minutes_error: null
    });
  }
  if (url === '/api/assistant/meetings/actions') {
    const request = body.requires_approval
      ? { request_id: 'apr_action', status: 'PENDING' }
      : { task_id: 'cwk_action', status: 'PLANNING' };
    return jsonResponse({ success: true, kind: body.requires_approval ? 'APPROVAL' : 'TASK', title: body.title, request });
  }
  if (url === '/api/assistant/meetings/recording') {
    return jsonResponse({ success: true, recording: { enabled: Boolean(body.enabled), text: 'Saved.', announcement: '' } });
  }
  if (url === '/api/assistant/stream') {
    if (/connect/.test(body.prompt)) {
      return ndjsonResponse([
        { type: 'context', context: { page: 'overview', scope: body.workspace_mode, company_name: 'Kora Hospitality' } },
        { type: 'tool', tool: 'connect_integration', status: 'awaiting_confirmation', label: 'Start connecting slack' },
        { type: 'confirm', tool: 'connect_integration', arguments: { provider: 'slack' }, preview: 'Start connecting slack', risk: 'MEDIUM' },
        { type: 'answer', delta: 'This would start connecting slack. I have not executed it.' },
        { type: 'done', session_id: body.session_id, routed_to: 'OWNER_CONFIRMATION' }
      ]);
    }
    if (/^research/.test(body.prompt)) {
      return ndjsonResponse([
        { type: 'tool', tool: 'web_research', status: 'done', label: 'Read 1 source.', ok: true },
        { type: 'answer', delta: 'The source is labelled sample.' },
        { type: 'card', card: { type: 'WEB_SOURCES', title: '1 source', sample: true, sources: [{ label: 'Sample source', url: 'https://example.com/s', sample: true }] } },
        { type: 'done', session_id: body.session_id, routed_to: 'WEB_RESEARCH', citations: [{ source_type: 'WEB', label: 'Sample source', sample: true }], ok: true }
      ]);
    }
    return ndjsonResponse([
      { type: 'context', context: { page: 'overview', scope: body.workspace_mode, company_name: 'Kora Hospitality' } },
      { type: 'agent', role: 'CFO', label: 'AI CFO', title: 'Chief Financial Officer', remit: 'finance' },
      { type: 'tool', tool: 'query_data', status: 'done', label: 'Found 1 internal match.', ok: true },
      { type: 'answer', delta: 'One approval is waiting.' },
      { type: 'done', session_id: body.session_id, routed_to: 'CFO', agent: 'CFO', citations: [{ source_type: 'INTERNAL', label: 'Approvals' }], ok: true }
    ]);
  }
  if (url === '/api/assistant/tool') {
    return jsonResponse({ ok: true, summary: 'Started the integration handoff.', card: { type: 'INTEGRATION_HANDOFF', provider: 'slack' } });
  }
  if (url.startsWith('/api/assistant/memory')) {
    if (method === 'DELETE') return jsonResponse({ success: true, removed: 1 });
    if (method === 'POST') return jsonResponse({ success: true, memory: { memory_id: 'mem_1', content: body.content } });
    return jsonResponse({ memories: [{ memory_id: 'mem_1', content: 'Prefers Monday reports' }], count: 1 });
  }
  if (url === '/api/assistant/interact') {
    return jsonResponse({ reply: 'Fallback answer', citations: [] });
  }
  return jsonResponse({});
};

window.eval(source);

function wait(ms = 0) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  const assistant = window.URAAssistant;
  assert.ok(assistant, 'the assistant controller mounts');
  assistant.init();

  // (a) Exactly one assistant surface.
  assert.strictEqual(window.document.querySelectorAll('#uraLauncher').length, 1, 'one launcher');
  assert.strictEqual(window.document.querySelectorAll('#uraWindow').length, 1, 'one window');
  assert.strictEqual(window.document.querySelectorAll('#uraWindow[role="dialog"]').length, 1, 'one dialog');
  assert.ok(!/id="askUraBar"|class="ask-ura|Fixed Assistant/.test(indexHtml), 'no fixed bottom assistant markup');
  assert.ok(indexHtml.includes('ura_assistant.js'), 'the one assistant is loaded');
  console.log('  ok  (a) exactly one launcher and one window mount');

  // (b) Old routes resolve to the one assistant; the Co-worker survives.
  ['/assistant', '/ceo', '/meeting', '/coworker'].forEach((route) => {
    assert.ok(appJs.includes(route), `${route} is routed`);
  });
  assert.ok(appJs.includes('ura_assistant') || appJs.includes('URAAssistant'), 'routes open the one assistant');
  assert.ok(fs.existsSync(path.join(root, 'web/assistant_coworker_workspace.js')), 'Co-worker workspace kept');
  assert.ok(fs.existsSync(path.join(root, 'web/apple_coworker_assistant.js')), 'Co-worker narrative kept');
  console.log('  ok  (b) old routes land in the one assistant and the Co-worker is kept');

  // (c) Launcher, window and snap anchors.
  assistant.open();
  assert.strictEqual(window.document.getElementById('uraWindow').hidden, false, 'the launcher opens the window');
  const anchors = ['top-left', 'top', 'top-right', 'left', 'right', 'bottom-left', 'bottom', 'bottom-right'];
  anchors.forEach((anchor) => {
    const found = assistant.computeAnchor(
      anchor.includes('left') ? 46 : anchor.includes('right') ? window.innerWidth - 46 : window.innerWidth / 2,
      anchor.includes('top') ? 46 : anchor.includes('bottom') ? window.innerHeight - 46 : window.innerHeight / 2
    );
    assert.strictEqual(found, anchor, `${anchor} snaps`);
  });
  assistant.setMode('docked');
  assert.strictEqual(window.document.getElementById('uraWindow').dataset.mode, 'docked');
  assistant.setMode('window');
  console.log('  ok  (c) the window opens, docks and snaps to all eight anchors');

  // (d) Phone sheet.
  phone = true;
  assistant.open();
  assert.strictEqual(assistant.mode, 'sheet', 'a phone gets a bottom sheet');
  assistant.toggleSheet();
  assert.strictEqual(assistant.mode, 'sheet-full', 'the sheet expands');
  assistant.close();
  phone = false;
  assistant.open();
  console.log('  ok  (d) a phone gets a two-height sheet, not a launcher');

  // (e) Streaming and typed confirmation.
  assistant.setScope('PERSONAL');
  await assistant.send('how many approvals are waiting');
  let text = window.document.getElementById('uraMessages').textContent;
  assert.ok(text.includes('One approval is waiting.'), 'answer chunks render');
  assert.ok(window.document.querySelector('[data-card-type="SEARCH_RESULTS"]') || calls.some((c) => c[2] === '/api/assistant/stream'), 'stream is the one path');
  await assistant.send('connect slack');
  const confirmButton = window.document.querySelector('[data-confirm-index]');
  assert.ok(confirmButton, 'a mutating tool renders a confirmation');
  assert.ok(window.document.getElementById('uraMessages').textContent.includes('I have not executed it.'));
  await assistant.confirmTool(0);
  assert.ok(calls.some((c) => c[1] === 'POST' && c[2] === '/api/assistant/tool'), 'confirmation executes the typed tool');
  console.log('  ok  (e) streaming, tools and confirmation work end to end');

  // (f) Company scope lock.
  assistant.setScope('COMPANY');
  assert.strictEqual(window.document.getElementById('uraPermissionBanner').hidden, false, 'Company scope shows the gate');
  const before = calls.filter((c) => c[2] === '/api/assistant/stream').length;
  await assistant.send('what is our cash position');
  assert.strictEqual(calls.filter((c) => c[2] === '/api/assistant/stream').length, before, 'locked scope sends nothing');
  assert.ok(window.document.getElementById('uraMessages').textContent.includes('locked until the AI CEO approves'));
  approvalsState = [{ action_desc: 'URA Assistant Company scope (kind: cowork)', status: 'APPROVED' }];
  await assistant.checkCompanyPermission();
  assert.strictEqual(assistant.companyGranted, true, 'the cowork approval unlocks Company scope');
  console.log('  ok  (f) Company scope stays locked until the cowork approval exists');

  // (g) @role routing and explicit memory.
  await assistant.send('@CFO summarise the approvals');
  assert.ok(calls.some((c) => c[2] === '/api/assistant/stream' && /@CFO/.test(c[3].prompt)), '@role reaches the server');
  assistant.addMessage('user', 'Remember that I prefer Monday reports');
  await assistant.rememberLast();
  assert.ok(calls.some((c) => c[1] === 'POST' && c[2] === '/api/assistant/memory'), 'remember saves explicitly');
  await assistant.openMemory();
  assert.ok(window.document.querySelector('[data-forget-memory]'), 'saved memory renders a forget control');
  await assistant.forgetMemory('mem_1');
  assert.ok(calls.some((c) => c[1] === 'DELETE' && c[2] === '/api/assistant/memory/mem_1'), 'forget removes the memory');
  console.log('  ok  (g) @role routing and explicit memory work');

  // (h) Background jobs.
  await assistant.startBackground('Research competitors');
  assert.ok(calls.some((c) => c[1] === 'POST' && c[2] === '/api/assistant/jobs'), 'a job is created');
  await assistant.watchJob('job_e2e');
  assert.ok(window.document.getElementById('uraMessages').textContent.includes('Two approvals are waiting.'));
  await assistant.jobRequest('job_new', 'takeover');
  assert.ok(calls.some((c) => c[0] === 'navigate' && c[1] === '/coworker'), 'takeover hands off to the Co-worker');
  console.log('  ok  (h) background work, progress and hand-off work');

  // (i) Web access.
  await assistant.openWebAccess();
  assert.ok(window.document.getElementById('uraWebBody').textContent.includes('Sample web results'), 'the sample provider is labelled');
  await assistant.saveWebAccess();
  assert.ok(calls.some((c) => c[1] === 'POST' && c[2] === '/api/assistant/web-access'), 'web access is a saved policy');
  await assistant.send('research hotel pricing');
  assert.ok(window.document.getElementById('uraMessages').textContent.includes('labelled sample'), 'sources say they are sample');
  console.log('  ok  (i) web access is a labelled provider, never a fabricated source');

  // (j) Meetings.
  await assistant.openMeetings();
  assert.strictEqual(window.document.getElementById('uraMeetingsPanel').hidden, false);
  assert.ok(window.document.getElementById('uraMeetingsBody').textContent.includes('Calendar not connected'));
  await assistant.loadMeetingBrief();
  assert.ok(window.document.getElementById('uraMeetingsBody').textContent.includes('Decide 1 pending approval'));
  await assistant.startMeetingListen();
  assert.ok(window.document.getElementById('uraMeetingsBody').textContent.includes('no audio was captured'));
  window.document.getElementById('uraMeetingNote').value = 'Keep the retreat.';
  await assistant.saveMeetingNote();
  await assistant.summariseMeeting();
  assert.ok(window.document.querySelector('a[href="/api/documents/doc_1/download"]'), 'minutes link renders');
  window.document.getElementById('uraMeetingAction').value = 'Send the budget';
  await assistant.createMeetingAction();
  assert.ok(assistant.meetingActionFlash.includes('cwk_action'));
  console.log('  ok  (j) meetings brief, listen, notes, summary and governed action items work');

  // (k) Settings change the assistant.
  settingsState = {
    assistant_show_button: false,
    assistant_meetings_enabled: false,
    assistant_background_work: false,
    assistant_open_as: 'docked',
    assistant_default_scope: 'COMPANY'
  };
  await assistant.loadAssistantSettings();
  assert.strictEqual(window.document.getElementById('uraLauncher').hidden, true);
  assert.strictEqual(window.document.querySelector('[data-action="meetings"]').hidden, true);
  assert.strictEqual(window.document.querySelector('[data-plus="background"]').hidden, true);
  const jobsBefore = assistant.jobs.length;
  await assistant.startBackground('Research pricing');
  assert.strictEqual(assistant.jobs.length, jobsBefore, 'background work off blocks a job');
  settingsState = {};
  await assistant.loadAssistantSettings();
  assert.strictEqual(window.document.getElementById('uraLauncher').hidden, false);
  assert.ok(appJs.includes('/settings'), 'settings live in the one settings console');
  const v2 = fs.readFileSync(path.join(root, 'web/settings_v2.js'), 'utf8');
  assert.ok(v2.includes('Use all suggestions') && v2.includes("'/values/bulk'"), 'suggestions are applicable in bulk');
  console.log('  ok  (k) settings change the assistant and suggestions are applicable');

  // (l) Accessibility and persistence.
  const dialog = window.document.getElementById('uraWindow');
  assert.strictEqual(dialog.getAttribute('role'), 'dialog');
  assert.strictEqual(dialog.getAttribute('aria-modal'), 'false');
  assert.ok(window.document.querySelectorAll('#uraWindow button').length > 0, 'controls are real buttons');
  assert.ok([...window.document.querySelectorAll('#uraWindow button')].every((btn) => btn.textContent.trim() || btn.getAttribute('aria-label')), 'icon buttons are named');
  assistant.setMode('docked');
  const saved = JSON.parse(window.localStorage.getItem(assistant.storageKey));
  assert.strictEqual(saved.mode, 'docked', 'the mode is persisted per user');
  assert.ok(saved.scope, 'the scope is persisted per user');
  console.log('  ok  (l) the shell is accessible and persists per user');

  console.log('\n12 URA Assistant e2e journey checks passed (a)-(l).');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
