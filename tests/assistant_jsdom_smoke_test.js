#!/usr/bin/env node
/**
 * jsdom smoke test for the single URA Assistant shell.
 *
 * It exercises the real DOM factory, open/minimise/mode changes, the scope
 * lock, a reply round-trip and per-user persistence without Playwright.
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
window.fetch = async (url, options) => {
  calls.push(['fetch', url, options && options.body ? JSON.parse(options.body) : null]);
  if (url === '/api/approvals') return { ok: true, status: 200, json: async () => ({ approvals: [] }) };
  if (url === '/api/approvals/req_1/decide') return { ok: true, status: 200, json: async () => ({ success: true }) };
  if (url === '/api/assistant/interact') {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        reply: 'Two approvals are waiting.',
        citations: [{ source_type: 'INTERNAL', label: 'Approvals' }]
      })
    };
  }
  return { ok: true, status: 200, json: async () => ({}) };
};

window.eval(source);
const assistant = window.URAAssistant;

function tick() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

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

  const blockedBefore = calls.filter((c) => c[0] === 'fetch' && c[1] === '/api/assistant/interact').length;
  await assistant.send('What needs my attention?');
  const blockedAfter = calls.filter((c) => c[0] === 'fetch' && c[1] === '/api/assistant/interact').length;
  assert.strictEqual(blockedAfter, blockedBefore, 'locked Company scope must not call company data');
  console.log('  ok  locked Company scope does not read company data');

  assistant.setScope('PERSONAL');
  await assistant.send('What needs my attention?');
  const call = calls.find((c) => c[0] === 'fetch' && c[1] === '/api/assistant/interact');
  assert.ok(call, 'interact endpoint was called');
  assert.strictEqual(call[2].workspace_mode, 'PERSONAL');
  const messages = window.document.getElementById('uraMessages').textContent;
  assert.ok(messages.includes('Two approvals are waiting.'));
  assert.ok(window.document.querySelector('.ura-msg.user .ura-body'));
  console.log('  ok  sends a question and renders the reply');

  const stored = JSON.parse(window.localStorage.getItem(assistant.storageKey));
  assert.ok(stored, 'state is persisted per user');
  assert.strictEqual(stored.scope, 'PERSONAL');
  assert.ok(Array.isArray(stored.messages));

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

  console.log('\n8 URA Assistant jsdom checks passed.');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
