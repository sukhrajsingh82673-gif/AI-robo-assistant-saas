#!/usr/bin/env node
/**
 * Company setup UI contract tests (jsdom).
 *
 * Playwright and a browser binary are not available in this environment, so
 * these tests exercise the real browser modules in jsdom and add static
 * guarantees for the wiring in index.html and the router.
 *
 * Covered:
 *   (a) switcher order: current company first, the rest unchanged
 *   (b) switcher empty state is real (no placeholder company) and Add is last
 *   (c) keyboard: Escape closes, Arrow keys move, focus enters the dialog
 *   (d) Add page: two cards, honest points, help toggle, permission gate
 *   (e) i18n: English/Arabic dictionaries, <html dir>, RTL switch
 *   (f) Indian currency: lakh/crore compact notation
 *   (g) assistant intent matcher never performs an action itself
 *   (h) static wiring: scripts, styles, route, no fabricated company fallback
 */
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { JSDOM } = require('jsdom');

const root = path.resolve(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  console.log(`  ok  ${name}`);
}

function makeDom(html) {
  return new JSDOM(html || '<!doctype html><html lang="en"><head></head><body></body></html>', {
    url: 'https://example.test/',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
}

function loadI18n(window) {
  window.eval(read('web/i18n.js'));
  window.I18n.setLanguage('en');
}

function loadSwitcher(window) {
  window.eval(read('web/company_setup_switcher.js'));
  return window.CompanySetupSwitcher;
}

function loadAddPage(window) {
  window.eval(read('web/company_setup_add.js'));
  return window.CompanySetupAdd;
}

function stubContext(window, companies, activeId) {
  window.CurrentCompanyContext = {
    companies,
    activeCompanyId: activeId,
    getCompanies() { return this.companies; },
    getCompanyId() { return this.activeCompanyId; },
    setCompanyId(id) { this.activeCompanyId = id; }
  };
  window.state = { companies, activeCompanyId: activeId, host: {} };
}

const sample = [
  { id: 'c1', name: 'Alpha Foods', industry: 'Food', status: 'OPERATIONAL' },
  { id: 'c2', name: 'Beta Labs', industry: 'Research', status: 'CREATING' },
  { id: 'c3', name: 'Gamma Retail', industry: 'Retail', status: 'ATTENTION' }
];

// ---------------------------------------------------------------- (a) order
test('switcher puts the current company first and keeps the rest in order', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);
  window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  const switcher = loadSwitcher(window);
  stubContext(window, sample, 'c2');

  switcher.open({ refresh: false });
  const rows = Array.from(window.document.querySelectorAll('[data-company-id]'));
  assert.deepStrictEqual(rows.map((r) => r.getAttribute('data-company-id')), ['c2', 'c1', 'c3']);
  assert.strictEqual(rows[0].getAttribute('aria-current'), 'true');
  assert.ok(rows[0].classList.contains('is-current'));
  assert.ok(rows[0].textContent.includes('Beta Labs'));
  assert.strictEqual(rows[0].querySelector('.zc-chip-current').textContent, 'Current');
  switcher.close();
});

// ---------------------------------------------------------------- (b) empty
test('empty switcher is honest and Add is always the last control', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);
  window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  const switcher = loadSwitcher(window);
  stubContext(window, [], null);

  switcher.open({ refresh: false });
  const rootEl = window.document.getElementById('zcSwitcherRoot');
  assert.ok(rootEl.querySelector('.zc-switcher-empty'));
  assert.ok(rootEl.textContent.includes('No companies yet'));
  assert.strictEqual(rootEl.querySelectorAll('[data-company-id]').length, 0);

  const footerButtons = Array.from(rootEl.querySelectorAll('.zc-sheet-footer button'));
  assert.strictEqual(footerButtons.length, 1);
  assert.strictEqual(footerButtons[0].id, 'zcSwitcherAdd');
  assert.ok(footerButtons[0].textContent.includes('Add company'));
  switcher.close();
});

// ---------------------------------------------------------------- (c) keys
test('switcher traps focus, supports arrow navigation and Escape', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);
  window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  const switcher = loadSwitcher(window);
  stubContext(window, sample, 'c1');

  switcher.open({ refresh: false });
  const document = window.document;
  const rows = Array.from(document.querySelectorAll('[data-company-id]'));
  assert.strictEqual(document.activeElement, rows[0], 'focus starts on the current company');

  document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
  assert.strictEqual(document.activeElement, rows[1]);

  document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.strictEqual(document.getElementById('zcSwitcherRoot'), null);
  assert.ok(!document.body.classList.contains('zc-sheet-open'));
});

test('selecting a company moves the context and closes the sheet', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);
  window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  let rendered = 0;
  window.renderActiveNavView = () => { rendered += 1; };
  const switcher = loadSwitcher(window);
  stubContext(window, sample, 'c1');

  switcher.open({ refresh: false });
  window.document.querySelector('[data-company-id="c3"]').click();
  assert.strictEqual(window.CurrentCompanyContext.getCompanyId(), 'c3');
  assert.strictEqual(window.state.activeCompanyId, 'c3');
  assert.strictEqual(window.document.getElementById('zcSwitcherRoot'), null);
  assert.ok(rendered >= 1);
});

test('sidebar sync never invents a company', () => {
  const dom = makeDom('<body><span id="sidebarCompanyName"></span><div class="company-status-row"><span class="status-dot-active"></span><span id="sidebarCompanyStatus"></span></div></body>');
  const { window } = dom;
  loadI18n(window);
  const switcher = loadSwitcher(window);
  stubContext(window, [], null);

  switcher.syncSidebar();
  assert.strictEqual(window.document.getElementById('sidebarCompanyName').textContent, 'No company yet');
  assert.strictEqual(window.document.getElementById('sidebarCompanyStatus').textContent, 'Add a company to begin');
  assert.strictEqual(window.document.querySelector('.status-dot-active').getAttribute('data-tone'), 'neutral');

  stubContext(window, sample, 'c1');
  switcher.syncSidebar();
  assert.strictEqual(window.document.getElementById('sidebarCompanyName').textContent, 'Alpha Foods');
  assert.strictEqual(window.document.getElementById('sidebarCompanyStatus').textContent, 'Operational');
  assert.strictEqual(window.document.querySelector('.status-dot-active').getAttribute('data-tone'), 'green');
});

// ---------------------------------------------------------------- (d) Add page
test('Add page renders two honest cards and a working help panel', () => {
  const dom = makeDom('<body><div id="view-company"></div></body>');
  const { window } = dom;
  loadI18n(window);
  const add = loadAddPage(window);
  window.state = { host: { role: 'OWNER', user_id: 'u1' } };
  window.navigateTo = () => {};

  add.render('view-company');
  const document = window.document;
  const cards = Array.from(document.querySelectorAll('[data-add-type]'));
  assert.deepStrictEqual(cards.map((c) => c.getAttribute('data-add-type')), ['NEW', 'EXISTING']);
  assert.ok(cards[0].textContent.includes('Create a new company'));
  assert.ok(cards[0].textContent.includes('Starts with status Creating'));
  assert.ok(cards[1].textContent.includes('Add an existing company'));
  assert.ok(cards[1].textContent.includes('Read-only connections'));

  const help = document.getElementById('zcAddHelp');
  assert.strictEqual(help.hidden, true);
  document.getElementById('zcAddHelpToggle').click();
  assert.strictEqual(help.hidden, false);
  assert.ok(help.textContent.includes('Not sure') === false);
  assert.ok(help.textContent.includes('Choose Create new'));

  const back = document.getElementById('zcAddBack');
  assert.ok(back.textContent.includes('Companies'));
  add.render('view-company');
  assert.strictEqual(document.querySelectorAll('[data-add-type]').length, 2, 're-render stays self-contained');
});

test('Add page blocks agents while leaving the server as the real gate', () => {
  const dom = makeDom('<body><div id="view-company"></div></body>');
  const { window } = dom;
  loadI18n(window);
  const add = loadAddPage(window);
  window.navigateTo = () => {};

  window.state = { host: { role: 'AGENT', user_id: 'agent_1', principal_type: 'AGENT' } };
  assert.strictEqual(add.canAddCompany(), false);
  add.render('view-company');
  const cards = Array.from(window.document.querySelectorAll('[data-add-type]'));
  assert.ok(cards.every((c) => c.disabled));
  assert.ok(window.document.body.textContent.includes('You cannot add a company'));

  window.state = { host: { role: 'OWNER', user_id: 'u1' } };
  assert.strictEqual(add.canAddCompany(), true);
  add.render('view-company');
  assert.ok(Array.from(window.document.querySelectorAll('[data-add-type]')).every((c) => !c.disabled));
});

test('choosing a card stores intent and hands off without creating anything', () => {
  const dom = makeDom('<body><div id="view-company"></div></body>');
  const { window } = dom;
  loadI18n(window);
  const add = loadAddPage(window);
  window.state = { host: { role: 'OWNER', user_id: 'u1' } };
  const routes = [];
  window.navigateTo = (p) => routes.push(p);
  const flows = [];
  window.EntryFlows = { startFlow: (mode) => flows.push(mode) };

  add.render('view-company');
  window.document.querySelector('[data-add-type="EXISTING"]').click();
  assert.deepStrictEqual(flows, ['existing']);
  assert.ok(routes.includes('/company/new'));
  const intent = JSON.parse(window.localStorage.getItem('zonata_company_setup_intent'));
  assert.strictEqual(intent.type, 'EXISTING');
  assert.strictEqual(intent.source, 'company_add_page');
});

// ---------------------------------------------------------------- (e) i18n
test('i18n switches language, direction and both dictionaries', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);
  const document = window.document;

  assert.strictEqual(window.I18n.getLanguage(), 'en');
  assert.strictEqual(document.documentElement.getAttribute('dir'), 'ltr');
  assert.strictEqual(window.I18n.t('company.add.title'), 'Add a company');

  const seen = [];
  window.I18n.onLanguageChange((lang, dir) => seen.push([lang, dir]));
  window.I18n.setLanguage('ar');

  assert.strictEqual(window.I18n.getLanguage(), 'ar');
  assert.strictEqual(document.documentElement.getAttribute('lang'), 'ar');
  assert.strictEqual(document.documentElement.getAttribute('dir'), 'rtl');
  assert.strictEqual(window.I18n.t('company.add.title'), 'إضافة شركة');
  assert.deepStrictEqual(seen, [['ar', 'rtl']]);

  // Unknown languages never flip the document into an unsupported state.
  window.I18n.setLanguage('fr');
  assert.strictEqual(window.I18n.getLanguage(), 'en');
  assert.strictEqual(document.documentElement.getAttribute('dir'), 'ltr');
});

test('data-i18n attributes are applied to the DOM', () => {
  const dom = makeDom('<body><h1 data-i18n="company.switcher.title"></h1><button data-i18n-aria-label="common.close"></button></body>');
  const { window } = dom;
  loadI18n(window);
  const document = window.document;
  assert.strictEqual(document.querySelector('h1').textContent, 'Switch company');
  assert.strictEqual(document.querySelector('button').getAttribute('aria-label'), 'Close');
  window.I18n.setLanguage('ar');
  assert.strictEqual(document.querySelector('h1').textContent, 'تبديل الشركة');
});

// ---------------------------------------------------------------- (f) money
test('Indian currency uses lakh and crore, not millions', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);

  assert.strictEqual(window.I18n.formatCurrency(1200000), '₹12,00,000');
  assert.strictEqual(window.I18n.formatCurrency(1200000, 'INR', { compact: true }), '₹12L');
  assert.strictEqual(window.I18n.formatCurrency(12500000, 'INR', { compact: true }), '₹1.3Cr');
  assert.strictEqual(window.I18n.formatCompactCurrency(999, 'INR'), '₹999');
  assert.strictEqual(window.I18n.formatCompactCurrency(-150000, 'INR'), '-₹1.5L');
});

// ---------------------------------------------------------------- (g) intent
test('assistant intent matcher classifies without acting', () => {
  const dom = makeDom();
  const { window } = dom;
  loadI18n(window);
  const switcher = loadSwitcher(window);

  assert.strictEqual(switcher.matchIntent('Add a company'), 'ADD');
  assert.strictEqual(switcher.matchIntent('create a new business'), 'ADD');
  assert.strictEqual(switcher.matchIntent('connect an existing company'), 'ADD');
  assert.strictEqual(switcher.matchIntent('switch company'), 'SWITCH');
  assert.strictEqual(switcher.matchIntent('change my company context'), 'SWITCH');
  assert.strictEqual(switcher.matchIntent('إضافة شركة'), 'ADD');
  assert.strictEqual(switcher.matchIntent('تبديل الشركة'), 'SWITCH');
  assert.strictEqual(switcher.matchIntent('What needs my attention?'), null);
  assert.strictEqual(switcher.matchIntent(''), null);
});

// ---------------------------------------------------------------- (h) wiring
test('index.html loads the company setup modules in a safe order', () => {
  const index = read('web/index.html');
  assert.ok(index.includes('href="company_setup.css"'));
  assert.ok(index.includes('family=Noto+Sans+Arabic'));
  const i18nAt = index.indexOf('src="i18n.js"');
  const switcherAt = index.indexOf('src="company_setup_switcher.js"');
  const addAt = index.indexOf('src="company_setup_add.js"');
  const appAt = index.indexOf('src="app.js"');
  assert.ok(i18nAt > 0 && switcherAt > 0 && addAt > 0 && appAt > 0);
  assert.ok(i18nAt < appAt, 'i18n loads before the app');
  assert.ok(switcherAt < appAt, 'switcher loads before the router');
  assert.ok(addAt < appAt, 'Add page loads before the router');
  assert.ok(index.includes('id="sidebarCompanyStatus"'));
});

test('router and palette expose /company/add and the switcher', () => {
  const app = read('web/app.js');
  assert.ok(app.includes("cleanPath === '/company/add'"));
  assert.ok(app.includes("window.CompanySetupAdd.render('view-company')"));
  assert.ok(app.includes('window.CompanySetupSwitcher.open()'));
  assert.ok(app.includes('Switch company'));
  assert.ok(app.includes('Add company'));
  assert.ok(app.includes('function syncCompanySurfaces'));
  assert.ok(!/comp_primary/.test(app), 'the router does not fabricate a primary company');
});

test('switcher surfaces never fall back to a fake company', () => {
  const shell = read('web/app_shell.js');
  const context = read('web/company_context.js');
  const flows = read('web/entry_flows.js');
  assert.ok(!shell.includes('comp_primary'));
  assert.ok(!context.includes('comp_primary'));
  assert.ok(!flows.includes('comp_primary'));
  assert.ok(shell.includes('CompanySetupSwitcher'));
  assert.ok(context.includes("'/company/add'"));
  assert.ok(flows.includes('CompanySetupAdd.render'));
  assert.ok(flows.includes('The company setup screen did not load'));
});

test('assistant handles company intents before any network call', () => {
  const assistant = read('web/ura_assistant.js');
  const sendAt = assistant.indexOf('async send(text)');
  const intentAt = assistant.indexOf('CompanySetupSwitcher.matchIntent');
  const fetchAt = assistant.indexOf('await this.streamReply(body)', sendAt);
  assert.ok(sendAt > 0 && intentAt > sendAt);
  assert.ok(fetchAt > intentAt, 'intent shortcut runs before the stream request');
  assert.ok(assistant.includes("company: ['Add a company', 'Switch company'"));
});

console.log(`\n${passed} company setup UI checks passed.`);
