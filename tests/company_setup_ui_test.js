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

async function testAsync(name, fn) {
  await fn();
  passed += 1;
  console.log(`  ok  ${name}`);
}

function jsonResponse(data, status) {
  return Promise.resolve({
    ok: (status || 200) < 400,
    status: status || 200,
    json: async () => data
  });
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

function loadCreateFlow(window) {
  window.eval(read('web/company_setup_create.js'));
  return window.CompanySetupCreate;
}

function loadProgress(window) {
  window.eval(read('web/company_setup_progress.js'));
  return window.CompanySetupProgress;
}

function loadExistingFlow(window) {
  window.eval(read('web/company_setup_existing.js'));
  return window.CompanySetupExisting;
}

function setField(window, name, value) {
  const el = window.document.getElementById(`zcField-${name}`);
  assert.ok(el, `field ${name} exists`);
  el.value = value;
  el.dispatchEvent(new window.Event('input', { bubbles: true }));
  return el;
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

  add.render('view-company');
  window.document.querySelector('[data-add-type="EXISTING"]').click();
  assert.ok(routes.includes('/company/existing'), 'existing companies open the onboarding flow');
  const intent = JSON.parse(window.localStorage.getItem('zonata_company_setup_intent'));
  assert.strictEqual(intent.type, 'EXISTING');
  assert.strictEqual(intent.source, 'company_add_page');

  window.document.querySelector('[data-add-type="NEW"]').click();
  assert.ok(routes.includes('/company/create'), 'new companies open the build flow');
  assert.strictEqual(routes.length, 2);
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
  const createAt = index.indexOf('src="company_setup_create.js"');
  const existingAt = index.indexOf('src="company_setup_existing.js"');
  const progressAt = index.indexOf('src="company_setup_progress.js"');
  assert.ok(createAt > addAt && createAt < appAt, 'create flow loads before the router');
  assert.ok(existingAt > createAt && existingAt < appAt, 'existing flow loads before the router');
  assert.ok(progressAt > addAt && progressAt < appAt, 'progress loads before the router');
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
  assert.ok(app.includes("cleanPath === '/company/create'"));
  assert.ok(app.includes('window.CompanySetupCreate.render'));
  assert.ok(app.includes("cleanPath === '/company/existing'"));
  assert.ok(app.includes('window.CompanySetupExisting.render'));
  assert.ok(app.includes('window.CompanySetupProgress.render'));
  assert.ok(app.includes('/build\\/?$'), 'the build route is explicit');
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

// ------------------------------------------------------- (i) create flow
test('create flow renders one column, guided toggle and collapsed extras', () => {
  const dom = makeDom('<div id="view"></div>');
  const { window } = dom;
  window.scrollTo = () => {};
  loadI18n(window);
  const create = loadCreateFlow(window);

  create.render('view');
  const root = window.document.querySelector('[data-company-create]');
  assert.ok(root, 'create page rendered');
  assert.ok(root.querySelector('#zcField-name'));
  assert.ok(root.querySelector('#zcField-title'));
  assert.ok(root.querySelector('#zcField-owner_name'));
  assert.ok(root.querySelector('#zcField-country'));
  assert.ok(root.querySelector('#zcField-industry'));

  const guided = root.querySelector('[data-description-mode="guided"]');
  assert.strictEqual(guided.getAttribute('aria-pressed'), 'false');
  const optionalBody = root.querySelector('#zcOptional');
  assert.strictEqual(optionalBody.hidden, true, 'optional section starts collapsed');
  const optionalToggle = root.querySelector('#zcOptionalToggle');
  optionalToggle.click();
  assert.strictEqual(optionalBody.hidden, false);
  assert.strictEqual(optionalToggle.getAttribute('aria-expanded'), 'true');
});

test('guided answers compose one description and the preview follows', () => {
  const dom = makeDom('<div id="view"></div>');
  const { window } = dom;
  window.scrollTo = () => {};
  loadI18n(window);
  const create = loadCreateFlow(window);
  create.render('view');

  window.document.querySelector('[data-description-mode="guided"]').click();
  setField(window, 'guided_offer', 'Ordering software for bakeries');
  setField(window, 'guided_audience', 'independent bakery owners');
  const preview = window.document.getElementById('zcGuidedPreview');
  assert.ok(preview.textContent.includes('Ordering software for bakeries'));
  assert.ok(preview.textContent.includes('It serves independent bakery owners.'));

  const data = create.data();
  assert.strictEqual(data.description_mode, 'guided');
  assert.ok(create.effectiveDescription().length > 20);
});

test('client validation blocks review and focuses the first problem', () => {
  const dom = makeDom('<div id="view"></div>');
  const { window } = dom;
  window.scrollTo = () => {};
  loadI18n(window);
  const create = loadCreateFlow(window);
  create.render('view');

  const form = window.document.getElementById('zcCreateForm');
  form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
  assert.strictEqual(create.step, 'form');
  assert.ok(window.document.getElementById('zcErr-name').textContent.includes('company name'));
  assert.ok(window.document.getElementById('zcErr-country') === null || create.errors.name);
});

// ------------------------------------------------ (j) existing-company flow
const CATALOGUE = [
  {
    id: 'accounting', name: 'Accounting and books', category: 'FINANCIAL',
    examples: ['Tally', 'Zoho Books'], reads: 'Ledger summary and invoices.',
    why: 'Shows margin and cash risk.', never: 'Salaries or personal bank details.',
    scope: ['read:ledger'], requires_secret: true, requires_verification: true
  },
  {
    id: 'banking', name: 'Bank accounts', category: 'FINANCIAL',
    examples: ['Statement feed'], reads: 'Balances and transactions.',
    why: 'Shows the real cash position.', never: 'Card numbers or credentials.',
    scope: ['read:balance'], requires_secret: true, requires_verification: true
  },
  {
    id: 'payments', name: 'Payments and settlements', category: 'FINANCIAL',
    examples: ['Razorpay'], reads: 'Settlements and fees.',
    why: 'Shows revenue quality.', never: 'Full card numbers.',
    scope: ['read:settlements'], requires_secret: true, requires_verification: true
  },
  {
    id: 'commerce', name: 'Store, POS and orders', category: 'OPERATIONAL',
    examples: ['Shopify'], reads: 'Orders and stock.',
    why: 'Shows what sells.', never: 'Customer addresses.',
    scope: ['read:orders'], requires_secret: true, requires_verification: true
  },
  {
    id: 'crm', name: 'CRM and pipeline', category: 'CUSTOMER',
    examples: ['HubSpot'], reads: 'Pipeline stages.',
    why: 'Shows where revenue stalls.', never: 'Contact notes.',
    scope: ['read:pipeline'], requires_secret: true, requires_verification: true
  },
  {
    id: 'workspace', name: 'Files and spreadsheets', category: 'DOCUMENT',
    examples: ['Google Workspace'], reads: 'Only the files you select.',
    why: 'Reuses trusted reports.', never: 'The rest of the drive.',
    scope: ['read:selected_files'], requires_secret: true, requires_verification: true
  },
  {
    id: 'communications', name: 'Email and business messaging', category: 'CUSTOMER',
    examples: ['Gmail read-only'], reads: 'Counts only.',
    why: 'Shows service load.', never: 'Message bodies.',
    scope: ['read:thread_metadata'], requires_secret: true, requires_verification: true
  },
  {
    id: 'uploads', name: 'Upload files directly', category: 'DOCUMENT',
    examples: ['CSV', 'XLSX'], reads: 'Only the files you upload.',
    why: 'Fastest way to start.', never: 'Anything outside the file.',
    scope: ['read:uploaded_files'], requires_secret: false, requires_verification: false
  }
];

function fillExistingDetails(window, existing) {
  const set = (name, value) => {
    const el = window.document.getElementById(`zcExistField-${name}`);
    assert.ok(el, `field ${name} exists`);
    el.value = value;
    el.dispatchEvent(new window.Event('input', { bubbles: true }));
  };
  set('name', 'Onboarding Bakery');
  set('title', 'Neighbourhood bakery chain');
  set('description', 'A six-store bakery serving walk-in and online customers every day.');
  set('industry', 'Food & Beverage');
  set('business_model', 'Retail bakery with online ordering and corporate catering.');
  set('revenue_amount', '12000000');
  set('revenue_currency', 'INR');
  set('revenue_period', 'ANNUAL');
  set('owner_name', 'Amina Rao');
  set('owner_role', 'Founder');
}

test('existing flow renders the business, revenue and role fields', () => {
  const dom = makeDom('<div id="view"></div>');
  const { window } = dom;
  window.scrollTo = () => {};
  loadI18n(window);
  const existing = loadExistingFlow(window);
  existing.render('view');

  const root = window.document.querySelector('[data-company-existing]');
  assert.ok(root, 'existing page rendered');
  ['name', 'title', 'description', 'industry', 'business_model', 'revenue_amount', 'owner_name', 'owner_role']
    .forEach((field) => assert.ok(root.querySelector(`#zcExistField-${field}`), `${field} exists`));
  assert.ok(root.querySelector('#zcExistField-revenue_currency'));
  assert.ok(root.querySelector('#zcExistField-revenue_period'));
  assert.ok(root.textContent.includes('How it makes money'));

  // Client validation mirrors the server: revenue, period, role and model are required.
  existing.toSources();
  assert.strictEqual(existing.step, 'details');
  assert.ok(existing.errors.revenue_amount);
  assert.ok(existing.errors.business_model);
  assert.ok(existing.errors.owner_role);
});

(async () => {
  await testAsync('existing sources show read/why/never and require a skip reason', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const existing = loadExistingFlow(window);
    window.fetch = (url) => {
      if (url === '/api/v1/companies/sources/catalogue') return jsonResponse({ sources: CATALOGUE });
      if (url === '/api/v1/companies/drafts') return jsonResponse({ draft_id: 'drf_ex' });
      return jsonResponse({}, 404);
    };
    existing.render('view');
    fillExistingDetails(window, existing);
    existing.toSources();
    assert.strictEqual(existing.step, 'sources');
    await existing.loadCatalogue();

    const cards = window.document.querySelectorAll('[data-source-card]');
    assert.strictEqual(cards.length, 8);
    const first = cards[0];
    assert.ok(first.textContent.includes('Ledger summary and invoices.'));
    assert.ok(first.textContent.includes('Shows margin and cash risk.'));
    assert.ok(first.textContent.includes('Salaries or personal bank details.'));
    assert.strictEqual(first.querySelectorAll('[data-source-choice]').length, 3);

    existing._setSourceChoice('commerce', 'skip');
    const reasonBox = window.document.querySelector('[data-source-reason-box="commerce"]');
    assert.strictEqual(reasonBox.hidden, false);
    assert.strictEqual(existing.toReview(), false, 'a skip without a reason blocks review');
    assert.ok(window.document.getElementById('zcSourceReasonErr-commerce').textContent.length > 0);

    const reason = window.document.getElementById('zcSourceReason-commerce');
    reason.value = 'Orders are kept in a paper book.';
    reason.dispatchEvent(new window.Event('input', { bubbles: true }));
    assert.strictEqual(existing.toReview(), true);
    assert.strictEqual(existing.step, 'review');
    const review = window.document.querySelector('.zc-review');
    assert.ok(review.textContent.includes('Store, POS and orders'));
    assert.ok(review.textContent.includes('Orders are kept in a paper book.'));
    existing.reset();
    dom.window.close();
  });

  await testAsync('existing submit saves choices then starts onboarding', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const existing = loadExistingFlow(window);
    const calls = [];
    window.fetch = (url, init) => {
      calls.push({ url, method: (init && init.method) || 'GET', body: init && init.body });
      if (url === '/api/v1/companies/sources/catalogue') return jsonResponse({ sources: CATALOGUE });
      if (url === '/api/v1/companies/drafts') return jsonResponse({ draft_id: 'drf_ex' });
      if (url === '/api/v1/companies') return jsonResponse({ id: 'comp_9' }, 201);
      if (/\/sources\/commerce\/skip$/.test(url)) return jsonResponse({ skipped: true });
      if (/\/connections$/.test(url)) return jsonResponse({ connection_id: 'con_1', status: 'NEEDS_CHECK' }, 201);
      if (/\/comp_9\/submit$/.test(url)) return jsonResponse({ workflow_started: true }, 202);
      return jsonResponse({ deleted: true });
    };
    const navigations = [];
    window.navigateTo = (path) => navigations.push(path);

    existing.render('view');
    fillExistingDetails(window, existing);
    existing.toSources();
    await existing.loadCatalogue();
    existing._setSourceChoice('accounting', 'connect');
    existing._setSourceChoice('commerce', 'skip');
    existing.sources().commerce.reason = 'Orders are kept in a paper book.';
    assert.strictEqual(existing.toReview(), true);

    await existing.submit();
    const created = calls.find((call) => call.url === '/api/v1/companies' && call.method === 'POST');
    assert.ok(created, 'company created');
    const body = JSON.parse(created.body);
    assert.strictEqual(body.type, 'EXISTING');
    assert.strictEqual(body.name, 'Onboarding Bakery');
    assert.deepStrictEqual(body.revenue, { amount: 12000000, currency: 'INR', period: 'ANNUAL' });
    assert.strictEqual(body.owner.role, 'Founder');

    const skip = calls.find((call) => /\/sources\/commerce\/skip$/.test(call.url));
    assert.ok(skip, 'skip applied');
    assert.strictEqual(JSON.parse(skip.body).reason, 'Orders are kept in a paper book.');
    const connect = calls.find((call) => call.url === '/api/v1/companies/comp_9/connections');
    assert.ok(connect, 'connection recorded');
    assert.strictEqual(JSON.parse(connect.body).source_id, 'accounting');
    assert.ok(calls.some((call) => /\/comp_9\/submit$/.test(call.url)));
    assert.deepStrictEqual(navigations, ['/company/comp_9/build']);
    existing.reset();
    dom.window.close();
  });

  await testAsync('existing create errors stay on the field and never fake success', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const existing = loadExistingFlow(window);
    window.fetch = (url) => {
      if (url === '/api/v1/companies/sources/catalogue') return jsonResponse({ sources: CATALOGUE });
      if (url === '/api/v1/companies/drafts') return jsonResponse({ draft_id: 'drf_ex' });
      if (url === '/api/v1/companies') {
        return jsonResponse({ error: 'exists', code: 'DUPLICATE_COMPANY_NAME' }, 409);
      }
      return jsonResponse({}, 404);
    };
    let navigated = null;
    window.navigateTo = (path) => { navigated = path; };

    existing.render('view');
    fillExistingDetails(window, existing);
    existing.toSources();
    await existing.loadCatalogue();
    existing.toReview();
    await existing.submit();

    assert.strictEqual(existing.step, 'details');
    assert.ok(window.document.getElementById('zcExistErr-name').textContent.toLowerCase().includes('already exists'));
    assert.strictEqual(navigated, null, 'no navigation on failure');
    existing.reset();
    dom.window.close();
  });

  await testAsync('review shows the brief and submit creates then starts the build', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const create = loadCreateFlow(window);
    create.render('view');

    setField(window, 'name', 'Nightowl Bakery');
    setField(window, 'title', 'Neighbourhood bakery with online ordering');
    setField(window, 'description', 'A bakery that sells bread, pastries and coffee to walk-in and online customers.');
    setField(window, 'owner_name', 'Amina Rao');
    setField(window, 'industry', 'Food & Beverage');
    window.document.getElementById('zcCreateReview').click();

    assert.strictEqual(create.step, 'review');
    const review = window.document.querySelector('.zc-review');
    assert.ok(review);
    assert.ok(review.textContent.includes('Nightowl Bakery'));
    assert.ok(review.textContent.includes('Amina Rao'));

    const calls = [];
    window.fetch = (url, init) => {
      calls.push({ url, method: (init && init.method) || 'GET', body: init && init.body });
      if (url === '/api/v1/companies/drafts') return jsonResponse({ draft_id: 'drf_1' });
      if (url === '/api/v1/companies') return jsonResponse({ id: 'comp_1' }, 201);
      if (url.indexOf('/api/v1/companies/comp_1/submit') === 0) {
        return jsonResponse({ company: { status: 'NEEDS_ATTENTION' }, workflow_started: true }, 202);
      }
      return jsonResponse({ deleted: true });
    };
    const navigations = [];
    window.navigateTo = (path) => navigations.push(path);

    await create.submit();
    const created = calls.find((call) => call.url === '/api/v1/companies');
    assert.ok(created, 'create call made');
    const body = JSON.parse(created.body);
    assert.strictEqual(body.type, 'NEW');
    assert.strictEqual(body.name, 'Nightowl Bakery');
    assert.ok(body.description.length > 20);
    assert.ok(calls.some((call) => call.url.endsWith('/comp_1/submit')));
    assert.deepStrictEqual(navigations, ['/company/comp_1/build']);
    create.reset();
    dom.window.close();
  });

  await testAsync('duplicate company names are shown on the name field, never faked', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const create = loadCreateFlow(window);
    create.render('view');

    setField(window, 'name', 'Nightowl Bakery');
    setField(window, 'title', 'Neighbourhood bakery');
    setField(window, 'description', 'A bakery that sells bread and coffee to walk-in customers.');
    setField(window, 'owner_name', 'Amina Rao');
    setField(window, 'industry', 'Food & Beverage');
    window.document.getElementById('zcCreateReview').click();
    assert.strictEqual(create.step, 'review');

    window.fetch = (url) => {
      if (url === '/api/v1/companies') {
        return jsonResponse({ error: 'exists', code: 'DUPLICATE_COMPANY_NAME' }, 409);
      }
      return jsonResponse({ draft_id: 'drf_1' });
    };
    window.navigateTo = () => {};

    await create.submit();
    assert.strictEqual(create.step, 'form');
    assert.ok(window.document.getElementById('zcErr-name').textContent.toLowerCase().includes('already exists'));
    create.reset();
    dom.window.close();
  });

  await testAsync('progress shows real phases, gaps and a working retry', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const progress = loadProgress(window);

    const build = {
      build_id: 'bld_1',
      company_id: 'comp_1',
      phase: 'VERIFY',
      phase_state: 'DONE_WITH_GAPS',
      progress: 0.57,
      progress_percent: 57,
      attempt: 1,
      estimate: { min_days: 1, max_days: 3, is_estimate: true },
      phases: [
        { id: 'INTAKE', label: 'Understanding your brief', state: 'DONE', note: 'Brief confirmed' },
        { id: 'RESEARCH', label: 'Researching the market', state: 'SKIPPED', note: 'No provider connected' },
        { id: 'BUILD', label: 'Building base systems', state: 'SKIPPED', note: 'No builder connected' },
        { id: 'VERIFY', label: 'Checking everything', state: 'DONE', note: 'Built with gaps' },
        { id: 'OPERATIONAL', label: 'Going operational', state: 'PENDING', note: '' }
      ],
      log: [{ at: 1794559547, phase: 'INTAKE', level: 'success', message: 'Brief confirmed.' }],
      gaps: [
        { phase: 'RESEARCH', message: 'Market research needs a connected provider.' },
        { phase: 'BUILD', message: 'Base systems need a connected builder.' }
      ],
      waiting_on: [
        { phase: 'RESEARCH', message: 'Market research needs a connected provider.' },
        { phase: 'BUILD', message: 'Base systems need a connected builder.' }
      ]
    };
    const calls = [];
    window.fetch = (url, init) => {
      calls.push({ url, method: (init && init.method) || 'GET' });
      if (url === '/api/v1/companies/comp_1') {
        return jsonResponse({ id: 'comp_1', name: 'Nightowl Bakery', status: 'NEEDS_ATTENTION' });
      }
      if (url === '/api/v1/companies/comp_1/build') return jsonResponse(build);
      if (url === '/api/v1/companies/comp_1/build/retry') {
        return jsonResponse({ workflow_started: true, build }, 202);
      }
      return jsonResponse({}, 404);
    };
    const navigations = [];
    window.navigateTo = (path) => navigations.push(path);

    await progress.render('view', 'comp_1');
    const root = window.document.querySelector('[data-company-build]');
    assert.ok(root, 'progress page rendered');
    assert.ok(root.textContent.includes('Nightowl Bakery'));
    assert.strictEqual(root.querySelector('[role="progressbar"]').getAttribute('aria-valuenow'), '57');
    assert.ok(root.textContent.includes('Researching the market'));
    assert.ok(root.textContent.includes('Skipped'));
    const waiting = root.querySelectorAll('.zc-waiting-item');
    assert.strictEqual(waiting.length, 2);
    assert.ok(root.textContent.includes('Waiting on you'));

    await progress.retry();
    assert.ok(calls.some((call) => call.url.endsWith('/build/retry') && call.method === 'POST'));

    const overview = root.querySelector('#zcBuildOverview');
    overview.click();
    assert.ok(navigations.includes('/company/comp_1/overview'));
    progress.destroy();
    dom.window.close();
  });

  await testAsync('progress never shows a build that does not exist', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const progress = loadProgress(window);
    window.fetch = (url) => {
      if (url === '/api/v1/companies/comp_2') {
        return jsonResponse({ id: 'comp_2', name: 'Quiet Co', status: 'DRAFT' });
      }
      return jsonResponse({ error: 'No build run', code: 'BUILD_NOT_FOUND' }, 404);
    };
    window.navigateTo = () => {};

    await progress.render('view', 'comp_2');
    const root = window.document.querySelector('[data-company-build]');
    assert.ok(root.textContent.includes('No build has started'));
    assert.strictEqual(root.querySelectorAll('.zc-phase').length, 0);
    progress.destroy();
    dom.window.close();
  });

  await testAsync('progress shows readiness, a named diagnosis gap and sources for onboarding', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    window.scrollTo = () => {};
    loadI18n(window);
    const progress = loadProgress(window);

    const build = {
      build_id: 'bld_2',
      company_id: 'comp_3',
      run_type: 'ONBOARDING',
      phase: 'ACT',
      phase_state: 'DONE_WITH_GAPS',
      progress: 0.83,
      progress_percent: 83,
      attempt: 1,
      estimate: { min_days: 1, max_days: 3, is_estimate: true },
      phases: [
        { id: 'CONNECT_VERIFY', label: 'Connecting', state: 'DONE', note: '1 connected' },
        { id: 'STUDY', label: 'Studying', state: 'SKIPPED', note: 'No adapter' },
        { id: 'DIAGNOSE', label: 'Diagnosing', state: 'SKIPPED', note: 'No provider' },
        { id: 'PLAN', label: 'Planning', state: 'DONE', note: '2 workstreams' },
        { id: 'ACT', label: 'Acting', state: 'SKIPPED', note: 'No approved action' },
        { id: 'OPERATIONAL', label: 'Going operational', state: 'PENDING', note: '' }
      ],
      log: [],
      waiting_on: [{ phase: 'STUDY', message: 'Nothing was read.' }],
      diagnosis: { available: false, findings: [], reason: 'No source was read, so no finding was invented.' },
      study: { read: false },
      sources: [
        { source_id: 'accounting', name: 'Accounting and books', status: 'NEEDS_CHECK', skipped: false },
        { source_id: 'commerce', name: 'Store, POS and orders', status: 'SKIPPED', skipped: true, skip_reason: 'Paper book' }
      ],
      readiness: {
        score: 58,
        band: 'MEDIUM',
        counts: { sources_connected: 1, sources_verified: 0, sources_skipped: 1, files: 0 },
        checks: [],
        reasons: [{ id: 'source_verified', label: 'Ownership verified', detail: 'Confirm ownership first.' }]
      }
    };
    const calls = [];
    window.fetch = (url, init) => {
      calls.push({ url, method: (init && init.method) || 'GET' });
      if (url === '/api/v1/companies/comp_3') {
        return jsonResponse({ id: 'comp_3', name: 'Onboarding Bakery', status: 'ONBOARDING' });
      }
      if (url === '/api/v1/companies/comp_3/build') return jsonResponse(build);
      if (url === '/api/v1/companies/comp_3/build/retry') {
        return jsonResponse({ workflow_started: true, build }, 202);
      }
      return jsonResponse({}, 404);
    };
    window.navigateTo = () => {};

    await progress.render('view', 'comp_3');
    const root = window.document.querySelector('[data-company-build]');
    assert.ok(root.textContent.includes('Onboarding progress'));
    assert.ok(root.textContent.includes('Readiness'));
    assert.strictEqual(root.querySelector('.zc-readiness-number').textContent, '58');
    assert.ok(root.textContent.includes('Ownership verified'));
    assert.ok(root.textContent.includes('No diagnosis was produced'));
    assert.ok(root.textContent.includes('no finding was invented'));
    assert.ok(root.textContent.includes('Store, POS and orders'));
    assert.ok(root.textContent.includes('Skipped'));
    assert.ok(root.textContent.includes('Waiting on you'));

    assert.ok(progress.canRetry(), 'ONBOARDING companies can retry');
    await progress.retry();
    assert.ok(calls.some((call) => call.url.endsWith('/build/retry') && call.method === 'POST'));
    progress.destroy();
    dom.window.close();
  });

  // ---------------------------------------------------------------- Stage 5
  // Overview, edit and the protected deletion wizard.

  function loadOverview(window) {
    window.eval(read('web/company_setup_overview.js'));
    return window.CompanySetupOverview;
  }

  function loadEdit(window) {
    window.eval(read('web/company_setup_edit.js'));
    return window.CompanySetupEdit;
  }

  function loadDelete(window) {
    window.eval(read('web/company_setup_delete.js'));
    return window.CompanySetupDelete;
  }

  // The page modules kick off their own fetches and re-render when they
  // settle. jsdom has real timers, so yield until the module is quiet.
  async function settle(isDone, label) {
    for (let i = 0; i < 200; i += 1) {
      if (isDone()) return;
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    throw new Error(`timed out waiting for ${label || 'render'}`);
  }

  function companyFixture(overrides) {
    return Object.assign({
      id: 'comp_1',
      tenant_id: 'tnt_1',
      type: 'EXISTING',
      name: 'Nightowl Bakery',
      title: 'Sourdough, wholesale and a small cafe',
      description: 'A neighbourhood bakery that supplies four cafes and runs one counter.',
      status: 'ONBOARDING',
      country: 'IN',
      industry: 'Food & Beverage',
      website: 'https://nightowl.example',
      currency: 'INR',
      owner: { name: 'Aarti Rao', email: 'aarti@nightowl.example', role: 'Founder' },
      revenue: { amount: 4800000, currency: 'INR', period: 'ANNUAL' },
      budget: { amount: 500000, currency: 'INR' },
      business_model: 'Wholesale bread plus counter sales',
      target_customers: 'Cafes and walk-in customers',
      timeline: 'Ready in about 2 weeks',
      setup_notes: 'Two ovens, no POS yet.',
      assets: ['https://nightowl.example/brand.pdf'],
      readiness_score: 58,
      created_at: 1794000000,
      updated_at: 1794550000,
      permissions: { view: true, edit: true, delete: true, manage_connections: true },
      build: null,
      deletion: null
    }, overrides || {});
  }

  function overviewFetch(window, options) {
    const opts = options || {};
    const company = opts.company || companyFixture();
    return (url) => {
      if (url === '/api/v1/companies/comp_1') return jsonResponse(company);
      if (url === '/api/v1/companies/comp_1/sources') {
        if (opts.sourcesFails) return jsonResponse({ error: 'nope' }, 500);
        return jsonResponse({
          sources: [
            { id: 'accounting', name: 'Accounting and books', status: 'VERIFIED' },
            { id: 'commerce', name: 'Store, POS and orders', status: 'SKIPPED' }
          ]
        });
      }
      if (url === '/api/v1/companies/comp_1/connections') {
        return jsonResponse({
          connections: [
            { connection_id: 'con_1', name: 'Tally', status: 'NEEDS_CHECK', verified_at: null }
          ]
        });
      }
      if (url === '/api/v1/companies/comp_1/readiness') {
        return jsonResponse({
          score: 58,
          band: 'MEDIUM',
          counts: { sources_connected: 1, sources_verified: 1, sources_skipped: 1, files: 2 }
        });
      }
      if (url === '/api/v1/companies/comp_1/legal') {
        return jsonResponse({
          legal_items: [
            { name: 'Founder agreement (draft)', status: 'DRAFT', draft_disclaimer: 'A draft, not a filing.' }
          ]
        });
      }
      if (url === '/api/v1/companies/comp_1/audit?limit=12') {
        return jsonResponse({
          events: [
            { action: 'company.created', actor_role: 'OWNER', created_at: 1794000100 },
            { action: 'company.connection_added', actor_role: 'OWNER', created_at: 1794550000 }
          ]
        });
      }
      if (url === '/api/v1/companies/comp_1/files') return jsonResponse({ total: 2, files: [] });
      return jsonResponse({}, 404);
    };
  }

  await testAsync('overview renders the real record, numbers and audit trail', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const overview = loadOverview(window);
    window.fetch = overviewFetch(window);
    window.navigateTo = () => {};

    overview.render('view', 'comp_1');
    await settle(() => !overview.loading, 'overview load');

    const root = window.document.querySelector('[data-company-overview]');
    assert.ok(root, 'overview rendered');
    assert.ok(root.textContent.includes('Nightowl Bakery'));
    assert.ok(root.textContent.includes('Food & Beverage'));
    assert.ok(root.textContent.includes('Aarti Rao'));
    assert.ok(root.textContent.includes('₹48L') || root.textContent.includes('48,00,000'), 'Indian compact revenue');
    assert.strictEqual(root.querySelectorAll('.zc-metric').length, 4);
    assert.strictEqual(root.querySelectorAll('.zc-overview-activity li').length, 2);
    assert.ok(root.textContent.includes('Company created'));
    assert.ok(root.textContent.includes('Connection added'));
    assert.ok(root.textContent.includes('Accounting and books'));
    assert.ok(root.textContent.includes('Founder agreement (draft)'));
    assert.strictEqual(overview.partialError, false);

    overview.destroy();
    dom.window.close();
  });

  await testAsync('overview menu only exists for editors and opens with the keyboard', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const overview = loadOverview(window);
    window.fetch = overviewFetch(window);
    window.navigateTo = () => {};

    overview.render('view', 'comp_1');
    await settle(() => !overview.loading, 'overview load');
    const button = window.document.getElementById('zcOverviewMenuButton');
    const menu = window.document.getElementById('zcOverviewMenu');
    assert.ok(button && menu, 'menu exists for an owner');
    assert.strictEqual(button.getAttribute('aria-expanded'), 'false');
    assert.strictEqual(menu.hidden, true);

    button.click();
    assert.strictEqual(button.getAttribute('aria-expanded'), 'true');
    assert.strictEqual(menu.hidden, false);
    assert.strictEqual(menu.querySelectorAll('[role="menuitem"]').length, 2);
    assert.ok(window.document.activeElement.textContent.includes('Edit company'), 'focus enters the menu');

    menu.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    assert.strictEqual(menu.hidden, true);
    assert.strictEqual(button.getAttribute('aria-expanded'), 'false');

    overview.destroy();
    dom.window.close();
  });

  await testAsync('overview hides edit and delete from an agent', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const overview = loadOverview(window);
    window.fetch = overviewFetch(window, {
      company: companyFixture({ permissions: { view: true, edit: false, delete: false } })
    });
    window.navigateTo = () => {};

    overview.render('view', 'comp_1');
    await settle(() => !overview.loading, 'overview load');
    const root = window.document.querySelector('[data-company-overview]');
    assert.strictEqual(root.querySelector('#zcOverviewMenuButton'), null);
    assert.ok(root.textContent.includes('View only'));
    overview.destroy();
    dom.window.close();
  });

  await testAsync('overview deletion banner shows the real window and opens the export view', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const overview = loadOverview(window);
    const purgeAfter = Math.floor(Date.now() / 1000) + 6 * 86400 + 3600;
    window.fetch = overviewFetch(window, {
      company: companyFixture({
        status: 'PENDING_DELETION',
        deletion: {
          status: 'PENDING_DELETION',
          export_status: 'READY',
          export_available: true,
          export_filename: 'nightowl-bakery-export.pdf.zip',
          email_status: 'NOT_CONFIGURED',
          purge_after: purgeAfter
        }
      })
    });
    window.navigateTo = () => {};

    overview.render('view', 'comp_1');
    await settle(() => !overview.loading, 'overview load');
    const root = window.document.querySelector('[data-company-overview]');
    const banner = root.querySelector('.zc-deletion-banner');
    assert.ok(banner, 'deletion banner rendered');
    assert.ok(banner.textContent.includes('Waiting for the export to be downloaded'), 'honest countdown without email');
    assert.ok(banner.textContent.includes('Waiting for the recovery window'), 'real deletion status');

    let opened = null;
    window.CompanySetupDelete = { open: (opts) => { opened = opts; } };
    banner.querySelector('[data-overview-action="download"]').click();
    assert.ok(opened, 'download action opened the wizard');
    assert.strictEqual(opened.startAt, 'export');
    assert.strictEqual(opened.companyId, 'comp_1');

    overview.destroy();
    dom.window.close();
  });

  await testAsync('overview survives a failing secondary panel without inventing data', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const overview = loadOverview(window);
    window.fetch = overviewFetch(window, { sourcesFails: true });
    window.navigateTo = () => {};

    overview.render('view', 'comp_1');
    await settle(() => !overview.loading, 'overview load');
    const root = window.document.querySelector('[data-company-overview]');
    assert.strictEqual(overview.partialError, true);
    assert.ok(root.textContent.includes('Some secondary details could not be loaded'));
    assert.ok(root.textContent.includes('No source catalogue state has been recorded.'));
    overview.destroy();
    dom.window.close();
  });

  function editFetch(window, options) {
    const opts = options || {};
    const company = opts.company || companyFixture();
    return (url, init) => {
      const method = (init && init.method) || 'GET';
      if (url === '/api/v1/companies/comp_1' && method === 'GET') return jsonResponse(company);
      if (url === '/api/v1/companies/comp_1' && method === 'PATCH') {
        opts.patchCalls.push(JSON.parse(init.body));
        if (opts.patchResponse) return opts.patchResponse;
        return jsonResponse(Object.assign({}, company, JSON.parse(init.body)));
      }
      if (url === '/api/v1/companies/comp_1/connections') return jsonResponse({ connections: [] });
      if (url === '/api/v1/companies/sources/catalogue') {
        return jsonResponse({ sources: [{ id: 'accounting', name: 'Accounting and books' }] });
      }
      return jsonResponse({}, 404);
    };
  }

  await testAsync('edit prefills real facts and rejects an empty name locally', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const edit = loadEdit(window);
    const patchCalls = [];
    window.fetch = editFetch(window, { patchCalls });
    const navigations = [];
    window.navigateTo = (path) => navigations.push(path);

    edit.render('view', 'comp_1');
    await settle(() => !edit.loading, 'edit load');
    const root = window.document.querySelector('[data-company-edit]');
    assert.ok(root, 'edit page rendered');
    assert.strictEqual(window.document.getElementById('zcField-name').value, 'Nightowl Bakery');
    assert.strictEqual(window.document.getElementById('zcField-owner_email').value, 'aarti@nightowl.example');
    assert.strictEqual(window.document.getElementById('zcField-revenue_amount').value, '4800000');

    setField(window, 'name', '');
    window.document.getElementById('zcEditSave').click();
    await settle(() => !edit.saving, 'edit save');
    assert.strictEqual(patchCalls.length, 0, 'no request for an invalid form');
    assert.ok(edit.errors.name);
    const rerendered = window.document.querySelector('[data-company-edit]');
    assert.ok(rerendered.textContent.includes('Enter the company name.'));
    assert.strictEqual(navigations.length, 0);
    dom.window.close();
  });

  await testAsync('edit sends cleared optional fields as empty and goes back on success', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const edit = loadEdit(window);
    const patchCalls = [];
    window.fetch = editFetch(window, { patchCalls });
    const navigations = [];
    window.navigateTo = (path) => navigations.push(path);
    const toasts = [];
    window.showToast = (message, tone) => toasts.push({ message, tone });

    edit.render('view', 'comp_1');
    await settle(() => !edit.loading, 'edit load');
    setField(window, 'title', '');
    setField(window, 'setup_notes', '');
    setField(window, 'revenue_amount', '');
    await edit.save();
    await settle(() => navigations.length > 0, 'edit navigation');

    assert.strictEqual(patchCalls.length, 1);
    assert.strictEqual(patchCalls[0].title, '', 'cleared title is sent, not silently kept');
    assert.strictEqual(patchCalls[0].setup_notes, '');
    assert.strictEqual(patchCalls[0].revenue.amount, null);
    assert.ok(navigations[0].endsWith('/company/comp_1/overview'));
    assert.ok(toasts.some((toast) => toast.tone === 'success'));
    dom.window.close();
  });

  await testAsync('edit keeps the form open and maps a duplicate name to the name field', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const edit = loadEdit(window);
    const patchCalls = [];
    window.fetch = editFetch(window, {
      patchCalls,
      patchResponse: jsonResponse({ error: 'exists', code: 'DUPLICATE_COMPANY_NAME' }, 409)
    });
    const navigations = [];
    window.navigateTo = (path) => navigations.push(path);

    edit.render('view', 'comp_1');
    await settle(() => !edit.loading, 'edit load');
    setField(window, 'name', 'Nightowl Bakery Two');
    await edit.save();
    await settle(() => !edit.saving, 'edit save');

    assert.strictEqual(patchCalls.length, 1);
    assert.ok(/already exists/i.test(edit.errors.name));
    assert.strictEqual(navigations.length, 0);
    const root = window.document.querySelector('[data-company-edit]');
    assert.ok(root.textContent.includes('already exists'));
    assert.strictEqual(window.document.getElementById('zcField-name').getAttribute('aria-invalid'), 'true');
    dom.window.close();
  });

  function planFixture(overrides) {
    return Object.assign({
      company_id: 'comp_1',
      company_name: 'Nightowl Bakery',
      removal_summary: {
        will_remove: { departments: 2, employees: 7, workflows: 3, connections: 1, files: 4, approvals: 5 },
        will_keep: ['a minimal audit record of the deletion'],
        will_stop: ['running workflows']
      },
      recovery_days: 7,
      mfa_required: false,
      two_step_configured: true,
      email_available: false,
      email_recipient: '',
      export_format: 'PDF, split into numbered parts and zipped when needed'
    }, overrides || {});
  }

  function deleteFetch(window, options) {
    const opts = options || {};
    const state = { posts: [], deletion: null };
    state.fetch = (url, init) => {
      const method = (init && init.method) || 'GET';
      if (method !== 'GET') state.posts.push({ url, method, body: init.body ? JSON.parse(init.body) : null });
      if (url === '/api/v1/companies/comp_1') return jsonResponse(companyFixture());
      if (url === '/api/v1/companies/comp_1/deletion') return jsonResponse({ deletion: state.deletion });
      if (url === '/api/v1/companies/comp_1/delete/plan') return jsonResponse(opts.plan || planFixture());
      if (url === '/api/v1/companies/comp_1/delete/request' && method === 'POST') {
        state.deletion = { status: 'AWAITING_NAME', purge_after: 0 };
        return jsonResponse(state.deletion, 201);
      }
      if (url === '/api/v1/companies/comp_1/delete/confirm-name' && method === 'POST') {
        state.deletion = { status: 'AWAITING_IDENTITY' };
        return jsonResponse(state.deletion);
      }
      if (url === '/api/v1/companies/comp_1/delete/confirm-identity' && method === 'POST') {
        if (opts.identityResponse) return opts.identityResponse(state);
        return jsonResponse({ error: 'No verifier', code: 'TWO_STEP_NOT_CONFIGURED' }, 501);
      }
      if (url === '/api/v1/companies/comp_1/delete/cancel' && method === 'POST') {
        state.deletion = null;
        return jsonResponse({ cancelled: true, company_status: 'ONBOARDING' });
      }
      return jsonResponse({}, 404);
    };
    return state;
  }

  await testAsync('delete wizard shows real counts and refuses a wrong company name offline', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const wizard = loadDelete(window);
    const state = deleteFetch(window);
    window.fetch = state.fetch;
    window.navigateTo = () => {};

    wizard.open({ companyId: 'comp_1', companyName: 'Nightowl Bakery' });
    await settle(() => !!window.document.querySelector('.zc-delete-sheet') && !wizard.loading, 'delete load');

    const sheet = window.document.querySelector('.zc-delete-sheet');
    assert.strictEqual(sheet.getAttribute('role'), 'dialog');
    assert.strictEqual(sheet.getAttribute('aria-modal'), 'true');
    assert.ok(sheet.textContent.includes('What will be removed'));
    assert.ok(sheet.textContent.includes('7 days'), 'real recovery window');
    assert.strictEqual(wizard.step, 'what');

    sheet.querySelector('[data-delete-action="request"]').click();
    await settle(() => wizard.step === 'name', 'delete name step');

    const nameInput = window.document.getElementById('zcDeleteName');
    nameInput.value = 'Nightowl Bakery Ltd';
    nameInput.dispatchEvent(new window.Event('input', { bubbles: true }));
    const continueButton = window.document.querySelector('[data-delete-action="name-continue"]');
    assert.strictEqual(continueButton.disabled, true, 'a wrong name cannot be submitted by click');

    // Even if the click guard is bypassed, the module refuses before the server.
    wizard.nameInput = 'Nightowl Bakery Ltd';
    await wizard.confirmName();
    await settle(() => !!wizard.error, 'name mismatch');
    assert.strictEqual(wizard.error.code, 'NAME_MISMATCH');
    assert.strictEqual(state.posts.filter((post) => post.url.endsWith('/confirm-name')).length, 0, 'server never sees a wrong name');

    const corrected = window.document.getElementById('zcDeleteName');
    corrected.value = 'Nightowl Bakery';
    corrected.dispatchEvent(new window.Event('input', { bubbles: true }));
    window.document.querySelector('[data-delete-action="name-continue"]').click();
    await settle(() => wizard.step === 'identity', 'identity step');
    assert.strictEqual(state.posts.filter((post) => post.url.endsWith('/confirm-name')).length, 1);
    wizard.close(false);
    dom.window.close();
  });

  await testAsync('delete stops honestly when no two-step verifier exists', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const wizard = loadDelete(window);
    const state = deleteFetch(window, {
      plan: planFixture({ mfa_required: true, two_step_configured: false })
    });
    window.fetch = state.fetch;
    window.navigateTo = () => {};

    wizard.open({ companyId: 'comp_1', companyName: 'Nightowl Bakery' });
    await settle(() => !!window.document.querySelector('.zc-delete-sheet') && !wizard.loading, 'delete load');
    assert.ok(window.document.querySelector('.zc-delete-sheet').textContent.includes('no authenticator is configured'));

    wizard.deletion = { status: 'AWAITING_IDENTITY' };
    wizard.step = 'identity';
    wizard._render();
    wizard.password = 'correct horse';
    const password = window.document.getElementById('zcDeletePassword');
    password.value = 'correct horse';
    password.dispatchEvent(new window.Event('input', { bubbles: true }));
    window.document.querySelector('[data-delete-action="identity-confirm"]').click();
    await settle(() => !!wizard.error, 'identity error');

    assert.strictEqual(wizard.error.code, 'TWO_STEP_NOT_CONFIGURED');
    assert.ok(/no verifier|no authenticator/i.test(wizard.error.message));
    assert.ok(/Nothing was deleted/i.test(wizard.error.message));
    assert.strictEqual(wizard.step, 'identity', 'never advances past the missing verifier');
    wizard.close(false);
    dom.window.close();
  });

  await testAsync('delete downloads the real export, never fakes email, and can be cancelled', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const wizard = loadDelete(window);
    const purgeAfter = Math.floor(Date.now() / 1000) + 7 * 86400;
    const deletion = {
      status: 'PENDING_DELETION',
      export_status: 'READY',
      export_available: true,
      export_filename: 'nightowl-bakery-export.pdf.zip',
      export_size_bytes: 204800,
      export_parts: 3,
      export_sha256: 'abcdef0123456789abcdef0123456789',
      export_download_path: '/api/v1/companies/comp_1/export',
      email_status: 'NOT_CONFIGURED',
      email_recipient: '',
      purge_after: purgeAfter,
      purge_blocked_reason: 'WAITING_FOR_DOWNLOAD',
      recovery_days: 7
    };
    const state = deleteFetch(window, {
      identityResponse: () => jsonResponse({
        deletion,
        export: { status: 'READY', filename: deletion.export_filename, message: 'The export is ready.' }
      })
    });
    state.deletion = deletion;
    window.fetch = (url, init) => {
      if (url === '/api/v1/companies/comp_1/export') {
        return Promise.resolve({
          ok: true,
          status: 200,
          blob: async () => new window.Blob(['%PDF-1.4'])
        });
      }
      return state.fetch(url, init);
    };
    window.URL.createObjectURL = () => 'blob:mock-export';
    window.URL.revokeObjectURL = () => {};
    window.HTMLAnchorElement.prototype.click = function click() {};
    window.navigateTo = () => {};

    wizard.open({ companyId: 'comp_1', companyName: 'Nightowl Bakery' });
    await settle(() => !!window.document.querySelector('.zc-delete-sheet') && !wizard.loading, 'delete load');
    assert.strictEqual(wizard.step, 'recovery', 'an existing request resumes at its real step');

    const sheet = () => window.document.querySelector('.zc-delete-sheet');
    assert.ok(sheet().textContent.includes('nightowl-bakery-export.pdf.zip'));
    assert.ok(sheet().textContent.includes('200 KB'));
    assert.ok(sheet().textContent.includes('3'));
    assert.ok(sheet().textContent.includes('Email is not configured'));
    assert.ok(sheet().textContent.includes('Purge is waiting for the export download'));

    sheet().querySelector('[data-delete-action="download"]').click();
    await settle(() => !!wizard.notice, 'download');
    assert.ok(wizard.notice.includes('nightowl-bakery-export.pdf.zip'));
    assert.ok(!wizard.notice.toLowerCase().includes('emailed'));

    sheet().querySelector('[data-delete-action="cancel"]').click();
    await settle(() => wizard.step === 'done', 'cancel');
    assert.strictEqual(wizard.cancelled, true);
    assert.ok(state.posts.some((post) => post.url.endsWith('/delete/cancel')));
    assert.ok(sheet().textContent.includes('Deletion cancelled'));
    assert.ok(sheet().textContent.includes('No company data was removed'));
    wizard.close(false);
    dom.window.close();
  });

  await testAsync('delete never pretends a failed export succeeded', async () => {
    const dom = makeDom('<div id="view"></div>');
    const { window } = dom;
    loadI18n(window);
    const wizard = loadDelete(window);
    const state = deleteFetch(window, {
      identityResponse: () => jsonResponse({
        deletion: { status: 'PENDING_DELETION', export_status: 'FAILED', export_available: false, purge_blocked_reason: 'EXPORT_FAILED' },
        export: { status: 'FAILED', message: 'The export could not be generated. Nothing has been purged.' }
      })
    });
    window.fetch = state.fetch;
    window.navigateTo = () => {};

    wizard.open({ companyId: 'comp_1', companyName: 'Nightowl Bakery' });
    await settle(() => !!window.document.querySelector('.zc-delete-sheet') && !wizard.loading, 'delete load');
    wizard.deletion = { status: 'AWAITING_IDENTITY' };
    wizard.step = 'identity';
    wizard._render();
    const password = window.document.getElementById('zcDeletePassword');
    password.value = 'correct horse';
    password.dispatchEvent(new window.Event('input', { bubbles: true }));
    window.document.querySelector('[data-delete-action="identity-confirm"]').click();
    await settle(() => wizard.step === 'export', 'failed export step');

    const sheet = window.document.querySelector('.zc-delete-sheet');
    assert.ok(sheet.textContent.includes('The export failed, so nothing was purged'));
    assert.ok(sheet.querySelector('[data-delete-action="export-retry"]'));
    assert.strictEqual(sheet.querySelector('[data-delete-action="download"]'), null, 'no download for a missing file');
    wizard.close(false);
    dom.window.close();
  });

  await testAsync('stage 5 wiring is present in the shell, router and scripts', async () => {
    const html = read('web/index.html');
    const app = read('web/app.js');
    const workspace = read('web/company_workspace.js');
    assert.ok(html.includes('company_setup_overview.js'));
    assert.ok(html.includes('company_setup_edit.js'));
    assert.ok(html.includes('company_setup_delete.js'));
    assert.ok(html.indexOf('company_setup_overview.js') < html.indexOf('<script src="app.js">'), 'modules load before the router');
    assert.ok(app.includes('/^\\/company\\/([^/]+)\\/overview\\/?$/'));
    assert.ok(app.includes('/^\\/company\\/([^/]+)\\/edit\\/?$/'));
    assert.ok(workspace.includes("if (tab === 'overview')"));
    assert.ok(workspace.includes('/edit'));
    assert.ok(!app.includes('comp_primary'), 'no legacy primary-company fallback in the router');
  });

  console.log(`\n${passed} company setup UI checks passed.`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
