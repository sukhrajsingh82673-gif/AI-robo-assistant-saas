#!/usr/bin/env node
/**
 * URA UI shell smoke test (jsdom).
 *
 * Boots the real front end from a running ZONATA / URA server and exercises the
 * new URA shell end to end:
 *   - authenticated boot, sidebar, tab bar, company chip
 *   - live Overview KPIs from /api/overview/snapshot
 *   - settings hub, appearance controls and settings persistence
 *   - command palette open + filter
 *   - Companies, Security and Approvals screens
 *   - Terminal hidden state
 *   - language switch to Arabic and RTL layout
 *
 * Environment:
 *   URA_BASE_URL   server origin (default http://127.0.0.1:8099/)
 *   URA_AUTH_FILE  JSON file containing { token, user } from the auth API
 *
 * The pytest wrapper tests/test_ui_shell_smoke.py boots an isolated server and
 * supplies both variables. Run it manually with:
 *   node tests/ui_shell_smoke.js
 */
'use strict';

const fs = require('fs');

let JSDOM;
let VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require('jsdom'));
} catch (e) {
  console.error('jsdom is required: npm install --save-dev jsdom');
  process.exit(2);
}

const authPath = process.env.URA_AUTH_FILE;
if (!authPath) {
  console.error('URA_AUTH_FILE must point to a JSON file with { token, user }');
  process.exit(2);
}
const auth = JSON.parse(fs.readFileSync(authPath, 'utf8'));
const base = (process.env.URA_BASE_URL || 'http://127.0.0.1:8099/').replace(/\/?$/, '/');

const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', (e) => errors.push('jsdomError: ' + (e && e.message)));
vc.on('error', (...a) => errors.push('console.error: ' + a.join(' ')));
vc.on('warn', () => {});
vc.on('log', () => {});

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
async function waitFor(fn, ms) {
  const end = Date.now() + (ms || 4000);
  while (Date.now() < end) {
    try { if (fn()) return true; } catch (e) { /* keep waiting */ }
    await sleep(100);
  }
  return false;
}

(async () => {
  const dom = await JSDOM.fromURL(base, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.__fetchLog = [];
      window.fetch = async (input, init) => {
        const u = typeof input === 'string' ? input : (input && input.url) || String(input);
        window.__fetchLog.push('START ' + u);
        try {
          const r = await fetch(new URL(u, base).toString(), init);
          window.__fetchLog.push('DONE ' + r.status + ' ' + u);
          return r;
        } catch (e) {
          window.__fetchLog.push('ERR ' + e.message + ' ' + u);
          throw e;
        }
      };
      window.matchMedia = (q) => ({
        matches: false,
        media: q,
        addEventListener() {},
        removeEventListener() {},
        addListener() {},
        removeListener() {}
      });
      window.scrollTo = () => {};
      window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
      window.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 0);
      window.addEventListener('unhandledrejection', (e) => errors.push('unhandledrejection: ' + (e.reason && (e.reason.stack || e.reason.message || e.reason))));
      window.addEventListener('error', (e) => errors.push('window.error: ' + (e.error && (e.error.stack || e.error.message) || e.message)));
      window.HTMLCanvasElement.prototype.getContext = () => ({
        scale() {}, clearRect() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {},
        stroke() {}, fill() {}, arc() {}, closePath() {}, setTransform() {}, fillText() {},
        save() {}, restore() {}, measureText() { return { width: 0 }; },
        createLinearGradient() { return { addColorStop() {} }; }
      });
      const user = Object.assign({}, auth.user, { token: auth.token });
      window.localStorage.setItem('zonata_host_session', JSON.stringify(user));
      window.localStorage.setItem('zonata_auth_token', auth.token);
      window.localStorage.setItem('zonata_companies', JSON.stringify([{
        id: auth.user.company_id,
        name: 'Smoke Co',
        industry: 'SaaS',
        status: 'OPERATIONAL',
        currency: 'USD',
        country: 'US',
        timezone: 'America/New_York'
      }]));
      window.localStorage.setItem('zonata_active_company_id', auth.user.company_id);
      window.localStorage.setItem('ura.ui.settings.v1', JSON.stringify({ theme: 'light', lang: 'en' }));
    }
  });

  const { window } = dom;
  await new Promise((resolve) => {
    if (window.document.readyState === 'complete') resolve();
    else window.addEventListener('load', resolve);
  });

  const d = window.document;
  await waitFor(() => d.querySelectorAll('#view-overview .ura-kpi').length >= 3, 15000);
  await sleep(300);

  const out = [];
  function check(name, ok, detail) {
    out.push((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
  }

  check('appShell visible', d.getElementById('appShell').style.display === 'flex');
  check('nav rendered', d.querySelectorAll('#uraNav .nav-item').length >= 15, String(d.querySelectorAll('#uraNav .nav-item').length));
  check('tabbar rendered', d.querySelectorAll('#uraTabbar .ura-tab').length === 5);
  check('company chip filled', (d.getElementById('companyChipName').textContent || '').length > 0, d.getElementById('companyChipName').textContent);

  const ovHtml = d.getElementById('view-overview').innerHTML || '';
  check('overview rendered', ovHtml.length > 200, String(ovHtml.length));
  if (!ovHtml.includes('ura-kpi')) {
    console.error('Overview did not render KPIs. First 500 chars:\n' + ovHtml.slice(0, 500));
    console.error('Fetches:\n' + (window.__fetchLog || []).join('\n'));
  }
  check('overview has KPI', d.querySelectorAll('#view-overview .ura-kpi').length >= 3, String(d.querySelectorAll('#view-overview .ura-kpi').length));
  check('breadcrumb set', (d.getElementById('topbarBreadcrumbs').textContent || '').includes('Overview'));

  // Settings hub.
  window.navigateTo('/settings');
  await waitFor(() => (d.getElementById('view-settings').innerHTML || '').includes('Use all suggestions'), 5000);
  check('settings hub', (d.getElementById('view-settings').innerHTML || '').includes('Use all suggestions'));

  // Appearance controls bind to the versioned settings store.
  window.navigateTo('/settings/appearance');
  await waitFor(() => (d.getElementById('view-settings').innerHTML || '').includes('Accent colour'), 5000);
  const settingsHtml = d.getElementById('view-settings').innerHTML || '';
  check('appearance settings', settingsHtml.includes('Accent colour'));
  check('suggestion boxes', d.querySelectorAll('#view-settings .ura-suggest').length >= 5);
  const motionToggle = d.querySelector('#view-settings [data-toggle="reduceMotion"]');
  if (motionToggle) {
    motionToggle.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await sleep(300);
  }
  check('motion setting persisted',
    (window.localStorage.getItem('ura.ui.settings.v1') || '').includes('"reduceMotion":true'),
    (window.localStorage.getItem('ura.ui.settings.v1') || '').slice(0, 220));

  // Command palette.
  d.getElementById('uraSearchBtn').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(150);
  check('palette open', !!d.getElementById('uraPaletteInput'));
  const input = d.getElementById('uraPaletteInput');
  input.value = 'secur';
  input.dispatchEvent(new window.Event('input', { bubbles: true }));
  await sleep(150);
  check('palette filters', (d.getElementById('uraPaletteList').textContent || '').includes('Security'));
  window.URAShell.closePalette();

  // Companies.
  window.navigateTo('/companies');
  await waitFor(() => (d.getElementById('view-company').innerHTML || '').indexOf('Switch to this company') !== -1 || (d.getElementById('view-company').innerHTML || '').indexOf('Current company') !== -1, 15000);
  const coHtml = d.getElementById('view-company').innerHTML || '';
  check('companies screen', coHtml.includes('Current company') || coHtml.includes('Switch to this company'), coHtml.slice(0, 200));

  // Security.
  window.navigateTo('/security');
  await waitFor(() => (d.getElementById('view-security').innerHTML || '').includes('Security score'), 6000);
  check('security screen', (d.getElementById('view-security').innerHTML || '').includes('Security score'));

  // Approvals.
  window.navigateTo('/approvals');
  await waitFor(() => (d.getElementById('view-approvals').innerHTML || '').includes('Waiting'), 6000);
  check('approvals screen', (d.getElementById('view-approvals').innerHTML || '').includes('Waiting'));

  // Top bar popover opens and Escape closes it.
  d.getElementById('uraStatusPill').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(250);
  check('topbar status popover', !!d.querySelector('.ura-popover'));
  d.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  await sleep(150);
  check('escape closes popover', !d.querySelector('.ura-popover'));

  // Dark theme is a real root attribute, not a per-screen class.
  window.URASettings.set('theme', 'dark');
  await sleep(250);
  check('dark theme applied', d.documentElement.getAttribute('data-theme') === 'dark');
  window.URASettings.set('theme', 'light');

  // Currency conversion has no rate source, so the UI must say so.
  const sourceCurrency = window.URACore.companyCurrency();
  const sourceCode = window.URACore.currencyCode(sourceCurrency);
  window.URASettings.set('currency', sourceCode === 'INR' ? 'USD' : 'INR');
  await sleep(150);
  check('FX gap is labelled',
    window.URACore.formatMoney(100, { sourceCurrency: sourceCurrency }).includes('FX not connected'),
    window.URACore.formatMoney(100, { sourceCurrency: sourceCurrency }));
  window.URASettings.set('currency', 'company');

  // Every route renders its own section and never a generic error card.
  const routes = [
    ['/overview', 'view-overview'],
    ['/ask-ceo', 'view-ceo'],
    ['/approvals', 'view-approvals'],
    ['/operations', 'view-operations'],
    ['/marketing', 'view-customers'],
    ['/technology', 'view-technology'],
    ['/finance', 'view-finance'],
    ['/people', 'view-people'],
    ['/employees', 'view-workforce'],
    ['/agents', 'view-agent-factory'],
    ['/coworker', 'view-coworker'],
    ['/tools', 'view-tools'],
    ['/security', 'view-security'],
    ['/reports', 'view-reports'],
    ['/companies', 'view-company'],
    ['/settings', 'view-settings'],
    ['/settings/language', 'view-settings'],
    ['/settings/ai', 'view-settings'],
    ['/settings/notifications', 'view-settings'],
    ['/settings/reports', 'view-settings'],
    ['/settings/security', 'view-settings'],
    ['/settings/menu', 'view-settings']
  ];
  for (const [route, section] of routes) {
    window.navigateTo(route);
    const ok = await waitFor(() => {
      const el = d.getElementById(section);
      if (!el || !el.classList.contains('active')) return false;
      const html = el.innerHTML || '';
      return html.length > 120 &&
        html.indexOf('This screen could not render') === -1 &&
        html.indexOf('Something went wrong') === -1;
    }, route.indexOf('/settings/') === 0 ? 5000 : 12000);
    const sectionEl = d.getElementById(section);
    const title = (sectionEl.querySelector('.ura-title') || {}).textContent || '';
    const titleOk = route.indexOf('/settings') === 0 || title.trim().length > 0;
    check('route ' + route, ok && titleOk,
      'title=' + JSON.stringify(title) + ' html=' + (sectionEl.innerHTML || '').slice(0, 120));
    if (route === '/marketing') {
      check('marketing uses live pipeline',
        (sectionEl.innerHTML || '').indexOf('Alpine Luxury Chalet Retreat') === -1);
    }
    if (route === '/reports') {
      check('reports uses live reports',
        (sectionEl.innerHTML || '').indexOf('Weekly Executive Briefing') === -1);
    }
  }

  // Hidden Terminal screen.
  window.URASettings.set('terminalOn', false);
  await sleep(300);
  check('terminal nav removed', !d.querySelector('#uraNav .nav-item[data-nav="terminal"]'));
  window.navigateTo('/terminal');
  await sleep(400);
  check('terminal locked card', (d.getElementById('view-terminal').innerHTML || '').includes('This screen is hidden'));
  window.URASettings.set('terminalOn', true);

  // Language switch and RTL.
  window.URASettings.set('lang', 'ar');
  await sleep(300);
  check('rtl applied', d.documentElement.getAttribute('dir') === 'rtl');
  check('arabic nav', (d.querySelector('#uraNav .nav-item[data-nav="overview"] .ura-label') || {}).textContent === 'نظرة عامة');
  window.URASettings.set('lang', 'en');

  // Applying every suggestion is a real, persisted action.
  window.navigateTo('/settings/appearance');
  await waitFor(() => (d.getElementById('view-settings').innerHTML || '').includes('Use all'), 5000);
  const useAll = d.querySelector('#view-settings [data-use-all="appearance"]');
  check('use all suggestions button', !!useAll);
  if (useAll) {
    useAll.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await sleep(400);
  }
  check('use all suggestions applied',
    (d.getElementById('view-settings').innerHTML || '').includes('All suggestions applied'));

  console.log(out.join('\n'));
  console.log('\nCaptured errors: ' + errors.length);
  errors.slice(0, 12).forEach((e) => console.log('  ' + e));
  const failed = out.filter((x) => x.startsWith('FAIL')).length;
  console.log('\nRESULT: ' + (failed ? failed + ' failed' : 'all checks passed'));
  dom.window.close();
  process.exit(failed || errors.length ? 1 : 0);
})().catch((e) => {
  console.error('SMOKE ERROR', e);
  process.exit(2);
});
