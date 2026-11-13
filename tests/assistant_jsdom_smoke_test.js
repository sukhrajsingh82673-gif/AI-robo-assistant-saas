#!/usr/bin/env node
/**
 * jsdom smoke test for the single URA Assistant shell.
 *
 * Exercises the real DOM factory, open/minimise/mode changes, the scope lock,
 * the NDJSON streaming contract, typed tool confirmations, memory actions,
 * background jobs, web access and per-user persistence without Playwright.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { JSDOM } = require('jsdom');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'web/ura_assistant.js'), 'utf8');

const calls = [];
const dom = new JSDOM('<!doctype html><html><body><div id="uraAssistantRoot"></div><div id="modalOverlay"></div></body></html>', {
  url: 'https://example.test/',
  runScripts: 'outside-only',
  pretendToBeVisual: true
});
const { window } = dom;
let phone = false;
window.matchMedia = () => ({ matches: phone, addEventListener() {}, removeEventListener() {} });
window.state = {
  host: { email: 'owner@example.test', name: 'Owner' },
  activeNav: 'approvals',
  activeCompanyId: 'comp_1',
  companies: [{ id: 'comp_1', name: 'Kora Hospitality', country: 'IN', currency: 'INR' }]
};
window.CurrentCompanyContext = {
  getCompanyId: () => 'comp_1',
  getCompany: () => window.state.companies[0]
};
window.navigateTo = (route) => calls.push(['navigate', route]);
window.confirm = () => true;

function jsonResponse(payload, status = 200) {
  return { ok: status < 400, status, json: async () => payload, text: async () => JSON.stringify(payload) };
}

function ndjsonResponse(events) {
  const text = events.map((event) => JSON.stringify(event)).join('\n') + '\n';
  return { ok: true, status: 200, body: null, text: async () => text, json: async () => ({}) };
}

window.__URA_NO_POLL__ = true;

let jobsState = [
  {
    job_id: 'job_1', title: 'Research competitors', prompt: 'Research competitors', kind: 'research',
    status: 'RUNNING', progress: 35, step: 'Searching the web', notification_seen: 0,
    steps: [{ label: 'Queued' }, { label: 'Searching the web' }]
  },
  {
    job_id: 'job_2', title: 'Approvals count', prompt: 'How many approvals are waiting?', kind: 'query',
    status: 'SUCCEEDED', progress: 100, step: 'Completed', notification_seen: 0,
    result: { summary: 'There are 2 approvals waiting.' }, steps: [{ label: 'Completed' }]
  }
];

window.fetch = async (url, options) => {
  const method = (options && options.method) || 'GET';
  const body = options && options.body ? JSON.parse(options.body) : null;
  calls.push(['fetch', method, url, body]);
  if (url === '/api/approvals') return jsonResponse({ approvals: [] });
  if (url === '/api/approvals/req_1/decide') return jsonResponse({ success: true });
  if (url === '/api/assistant/jobs' && method === 'POST') {
    const job = {
      job_id: 'job_new', title: body.prompt, prompt: body.prompt, kind: 'research',
      status: 'QUEUED', progress: 0, step: 'Queued', steps: [{ label: 'Queued' }],
      notification_seen: 0, workspace_mode: body.workspace_mode
    };
    jobsState = [job, ...jobsState];
    return jsonResponse({ success: true, job, limit: 3 });
  }
  if (url === '/api/assistant/jobs/inbox/seen') {
    jobsState = jobsState.map((job) => ({ ...job, notification_seen: 1 }));
    return jsonResponse({ success: true, marked: jobsState.length });
  }
  if (url.startsWith('/api/assistant/jobs/') && url.endsWith('/watch')) {
    const id = url.split('/')[4];
    const finished = {
      ...(jobsState.find((job) => job.job_id === id) || {}),
      status: 'SUCCEEDED', progress: 100, step: 'Completed', notification_seen: 0,
      result: { summary: 'There are 2 approvals waiting.' },
      citations: [{ source_type: 'WEB', label: 'Sample source', url: 'https://example.com/sample', sample: true }]
    };
    jobsState = jobsState.map((job) => (job.job_id === id ? finished : job));
    return ndjsonResponse([{ type: 'job', job: finished }, { type: 'job_done', job: finished }]);
  }
  if (url.startsWith('/api/assistant/jobs/') && url.endsWith('/action')) {
    const id = url.split('/')[4];
    const current = jobsState.find((job) => job.job_id === id) || { job_id: id };
    if (body.action === 'takeover') {
      const paused = { ...current, status: 'PAUSED', step: 'Paused for you to take over' };
      jobsState = jobsState.map((job) => (job.job_id === id ? paused : job));
      return jsonResponse({
        success: true, job: paused,
        handoff: {
          path: '/coworker', label: 'Take over in the Co-worker',
          message: 'The job is paused. Continue it yourself in the Co-worker.'
        }
      });
    }
    const statuses = { pause: 'PAUSED', resume: 'RUNNING', cancel: 'CANCELLED', retry: 'QUEUED' };
    const updated = { ...current, status: statuses[body.action] || current.status };
    jobsState = jobsState.map((job) => (job.job_id === id ? updated : job));
    return jsonResponse({ success: true, job: updated });
  }
  if (url.startsWith('/api/assistant/jobs?')) {
    const active = jobsState.filter((job) => ['QUEUED', 'RUNNING', 'PAUSED'].includes(job.status)).length;
    const unseen = jobsState.filter((job) => !job.notification_seen).length;
    return jsonResponse({ jobs: jobsState, active, unseen, limit: 3 });
  }
  if (url === '/api/assistant/web-access' && method === 'POST') {
    return jsonResponse({
      success: true,
      web_access: {
        configured: true, provider: 'sample',
        provider_label: 'Sample web results (not connected)', sample_provider: true,
        access: {
          mode: body.access,
          allowlist: String(body.allowlist || '').split(',').map((s) => s.trim()).filter(Boolean),
          blocklist: []
        }
      }
    });
  }
  if (url === '/api/assistant/web-access') {
    return jsonResponse({
      configured: true, provider: 'sample',
      provider_label: 'Sample web results (not connected)', sample_provider: true,
      access: { mode: 'open', allowlist: [], blocklist: [] }
    });
  }
  if (url === '/api/assistant/stream') {
    return ndjsonResponse([
      { type: 'context', context: { page: 'approvals', path: '/approvals', scope: body.workspace_mode, company_id: 'comp_1', company_name: 'Kora Hospitality', agent: 'CFO', agent_label: 'AI CFO' } },
      { type: 'agent', role: 'CFO', label: 'AI CFO', title: 'Chief Financial Officer', remit: 'finance' },
      { type: 'tool', tool: 'query_data', status: 'running', label: 'Searching live app data' },
      { type: 'tool', tool: 'query_data', status: 'done', label: 'Found 2 internal match(es).', ok: true },
      { type: 'answer', delta: 'Two approvals are ' },
      { type: 'answer', delta: 'waiting.' },
      { type: 'card', card: { type: 'SEARCH_RESULTS', title: '2 matches', items: [{ title: 'Invoice approval', category: 'approvals' }] } },
      { type: 'done', session_id: 's1', routed_to: 'AI_CEO', agent: 'CFO', citations: [{ source_type: 'INTERNAL', label: 'Approvals' }], tool: 'query_data', ok: true }
    ]);
  }
  if (url === '/api/assistant/tool') {
    return jsonResponse({ success: true, tool: body.tool, result: { ok: true, summary: 'Delegated to the Co-worker (PLANNING).', card: { type: 'COWORKER_TASK', task_id: 'cwk_1', status: 'PLANNING' } } });
  }
  if (url.startsWith('/api/assistant/memory')) {
    if (method === 'DELETE' && url.includes('/mem_1')) return jsonResponse({ success: true, memory_id: 'mem_1' });
    if (method === 'DELETE') return jsonResponse({ success: true, removed: 1 });
    if (method === 'POST') return jsonResponse({ success: true, memory: { memory_id: 'mem_1', content: body.content } });
    return jsonResponse({ memories: [{ memory_id: 'mem_1', content: 'Prefers Monday reports', scope: 'PERSONAL' }], count: 1, scope: 'PERSONAL' });
  }
  if (url === '/api/assistant/interact') {
    return jsonResponse({ reply: 'Fallback answer', citations: [] });
  }
  return jsonResponse({});
};

window.eval(source);
const assistant = window.URAAssistant;

const wait = () => new Promise((resolve) => setTimeout(resolve, 0));

(async () => {
  assistant.init();
  assert.ok(window.document.getElementById('uraLauncher'), 'launcher is rendered once');
  assert.ok(window.document.getElementById('uraWindow'), 'window is rendered once');
  assert.strictEqual(window.document.querySelectorAll('#uraAssistantRoot').length, 1);
  assert.strictEqual(window.document.querySelector('#uraWindow').getAttribute('role'), 'dialog');
  assert.strictEqual(window.document.querySelector('#uraWindow').getAttribute('aria-modal'), 'false');
  console.log('  ok  one launcher and one non-modal window');

  assistant.open();
  assert.strictEqual(window.document.getElementById('uraWindow').hidden, false);
  assert.ok(window.document.getElementById('uraContextChip').textContent.includes('Approvals'));
  console.log('  ok  opens with live page context');

  assistant.setScope('COMPANY');
  assert.strictEqual(assistant.scope, 'COMPANY');
  assert.strictEqual(window.document.getElementById('uraPermissionBanner').hidden, false);
  assert.strictEqual(window.document.querySelector('[data-scope="COMPANY"]').getAttribute('aria-pressed'), 'true');
  console.log('  ok  Company scope shows the permission gate');

  const blockedBefore = calls.filter((c) => c[2] === '/api/assistant/stream').length;
  await assistant.send('What needs my attention?');
  const blockedAfter = calls.filter((c) => c[2] === '/api/assistant/stream').length;
  assert.strictEqual(blockedAfter, blockedBefore, 'locked Company scope must not call company data');
  console.log('  ok  locked Company scope does not read company data');

  assistant.setScope('PERSONAL');
  await assistant.send('@CFO what needs my attention?');
  const streamCall = calls.find((c) => c[2] === '/api/assistant/stream');
  assert.ok(streamCall, 'stream endpoint was called');
  assert.strictEqual(streamCall[3].workspace_mode, 'PERSONAL');
  assert.strictEqual(streamCall[3].page_context.page, 'approvals');
  await wait();
  const messages = window.document.getElementById('uraMessages').textContent;
  assert.ok(messages.includes('Two approvals are waiting.'));
  assert.ok(window.document.querySelector('.ura-msg.user .ura-body'));
  assert.strictEqual(window.document.getElementById('uraAgentChip').hidden, false);
  assert.ok(window.document.getElementById('uraAgentChip').textContent.includes('AI CFO'));
  assert.ok(messages.includes('Found 2 internal match'));
  console.log('  ok  streams tool steps, answer chunks and the @agent route');

  const stored = JSON.parse(window.localStorage.getItem(assistant.storageKey));
  assert.ok(stored, 'state is persisted per user');
  assert.strictEqual(stored.scope, 'PERSONAL');
  assert.ok(Array.isArray(stored.messages));

  // Confirmation card paths.
  assistant.handleStreamEvent({ type: 'confirm', tool: 'delegate_task', arguments: { prompt: 'Follow up with leads' }, preview: 'Delegate “Follow up with leads” to the Co-worker', risk: 'MEDIUM' });
  const confirmButton = window.document.querySelector('[data-confirm-index]');
  assert.ok(confirmButton, 'confirmation card renders a confirm button');
  await assistant.confirmTool(0);
  const toolCall = calls.find((c) => c[2] === '/api/assistant/tool');
  assert.ok(toolCall, 'confirmed tool executes through /api/assistant/tool');
  assert.strictEqual(toolCall[3].tool, 'delegate_task');
  console.log('  ok  typed tool confirmation executes the gated endpoint');

  assistant.addMessage('user', 'Remember that I prefer Monday reports');
  await assistant.rememberLast();
  const memoryPost = calls.find((c) => c[1] === 'POST' && c[2] === '/api/assistant/memory');
  assert.ok(memoryPost, 'memory POST is called');
  await assistant.openMemory();
  assert.ok(window.document.querySelector('[data-forget-memory]'), 'saved memory renders a forget control');
  await assistant.forgetMemory('mem_1');
  const memoryDelete = calls.find((c) => c[1] === 'DELETE' && c[2] === '/api/assistant/memory/mem_1');
  assert.ok(memoryDelete, 'forget calls the memory endpoint');
  console.log('  ok  remember, list and forget memory');

  // Stage 3 — background jobs, watch, hand-off and web access.
  await assistant.refreshJobs();
  assert.strictEqual(assistant.jobs.length, 2);
  assert.strictEqual(assistant.jobsBadgeCount(), 2);
  assistant.openJobs();
  assert.strictEqual(window.document.getElementById('uraJobsPanel').hidden, false);
  const jobsText = window.document.getElementById('uraJobsList').textContent;
  assert.ok(jobsText.includes('Research competitors'));
  assert.ok(window.document.getElementById('uraJobsLimit').textContent.includes('1 of 3 active'));
  assert.strictEqual(window.document.getElementById('uraJobsBadge').hidden, false);
  console.log('  ok  jobs panel lists jobs, progress and the active limit');

  await assistant.startBackground('Research pricing tools');
  const createJob = calls.find((c) => c[1] === 'POST' && c[2] === '/api/assistant/jobs');
  assert.ok(createJob, 'background start posts to the jobs endpoint');
  assert.strictEqual(createJob[3].prompt, 'Research pricing tools');
  assert.strictEqual(createJob[3].workspace_mode, 'PERSONAL');
  assert.ok(assistant.jobs.some((job) => job.job_id === 'job_new'));
  console.log('  ok  Run in background creates a persisted job');

  await assistant.jobRequest('job_new', 'takeover');
  assert.ok(calls.some((c) => c[0] === 'navigate' && c[1] === '/coworker'), 'take over hands off to the Co-worker');
  assert.ok(window.document.getElementById('uraMessages').textContent.includes('The job is paused'));
  await assistant.jobRequest('job_new', 'cancel');
  assert.ok(assistant.jobs.find((job) => job.job_id === 'job_new').status === 'CANCELLED');
  console.log('  ok  take over hands off and stop cancels the job');

  await assistant.watchJob('job_1');
  assert.ok(calls.some((c) => c[2] === '/api/assistant/jobs/job_1/watch'), 'watch streams the job');
  assert.strictEqual(assistant.jobs.find((job) => job.job_id === 'job_1').status, 'SUCCEEDED');
  assert.ok(window.document.getElementById('uraMessages').textContent.includes('There are 2 approvals waiting.'));
  assert.ok(window.document.querySelector('.ura-citations a[href="https://example.com/sample"]'), 'sources render as labelled links');
  console.log('  ok  watch streams progress and opens the cited result');

  await assistant.markJobsSeen();
  assert.ok(calls.some((c) => c[1] === 'POST' && c[2] === '/api/assistant/jobs/inbox/seen'));
  assert.ok(assistant.jobs.every((job) => job.notification_seen), 'unseen notifications are cleared');
  assert.strictEqual(assistant.jobsBadgeCount(), 0);
  console.log('  ok  the jobs badge reflects unseen notifications');

  await assistant.jobRequest('job_2', 'retry');
  const retryCall = calls.find((c) => c[2] === '/api/assistant/jobs/job_2/action');
  assert.ok(retryCall && retryCall[3].action === 'retry');
  assert.strictEqual(assistant.jobs.find((job) => job.job_id === 'job_2').status, 'QUEUED');
  await assistant.jobRequest('job_2', 'cancel');
  console.log('  ok  retry and cancel act on the stored job');

  await assistant.openWebAccess();
  assert.strictEqual(window.document.getElementById('uraWebPanel').hidden, false);
  const webBody = window.document.getElementById('uraWebBody').textContent;
  assert.ok(webBody.includes('Sample web results'));
  assert.ok(webBody.includes('Sample provider is on'));
  assert.strictEqual(window.document.getElementById('uraWebMode').value, 'open');
  window.document.getElementById('uraWebMode').value = 'allowlist';
  window.document.getElementById('uraWebAllow').value = 'example.com';
  await assistant.saveWebAccess();
  const webSave = calls.find((c) => c[1] === 'POST' && c[2] === '/api/assistant/web-access');
  assert.ok(webSave, 'web access saves through the settings endpoint');
  assert.strictEqual(webSave[3].access, 'allowlist');
  assert.strictEqual(webSave[3].allowlist, 'example.com');
  console.log('  ok  web access loads, labels sample data and saves the allow list');

  assistant.action('dock');
  assert.strictEqual(window.document.getElementById('uraWindow').dataset.mode, 'docked');
  assistant.action('expand');
  assert.strictEqual(window.document.getElementById('uraWindow').dataset.mode, 'expanded');
  assistant.action('minimise');
  assert.strictEqual(window.document.getElementById('uraWindow').hidden, true);
  assert.strictEqual(assistant.isOpen, false);
  console.log('  ok  dock, expand and minimise work');

  phone = true;
  assistant.open();
  assert.strictEqual(assistant.mode, 'sheet');
  assistant.toggleSheet();
  assert.strictEqual(assistant.mode, 'sheet-full');
  console.log('  ok  phone opens a sheet and expands it');

  const anchors = ['top-left', 'top', 'top-right', 'left', 'right', 'bottom-left', 'bottom', 'bottom-right'];
  for (const anchor of anchors) {
    const found = assistant.computeAnchor(
      anchor.includes('left') ? 46 : anchor.includes('right') ? window.innerWidth - 46 : window.innerWidth / 2,
      anchor.includes('top') ? 46 : anchor.includes('bottom') ? window.innerHeight - 46 : window.innerHeight / 2
    );
    assert.strictEqual(found, anchor);
  }
  console.log('  ok  all eight snap anchors resolve');

  console.log('\n17 URA Assistant jsdom checks passed.');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
