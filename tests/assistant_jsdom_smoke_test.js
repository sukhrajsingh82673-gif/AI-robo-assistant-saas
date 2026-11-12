#!/usr/bin/env node
/**
 * jsdom smoke test for the single URA Assistant shell.
 *
 * Exercises the real DOM factory, open/minimise/mode changes, the scope lock,
 * the NDJSON streaming contract, typed tool confirmations, memory actions and
 * per-user persistence without Playwright.
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

window.fetch = async (url, options) => {
  const method = (options && options.method) || 'GET';
  const body = options && options.body ? JSON.parse(options.body) : null;
  calls.push(['fetch', method, url, body]);
  if (url === '/api/approvals') return jsonResponse({ approvals: [] });
  if (url === '/api/approvals/req_1/decide') return jsonResponse({ success: true });
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

  console.log('\n10 URA Assistant jsdom checks passed.');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
