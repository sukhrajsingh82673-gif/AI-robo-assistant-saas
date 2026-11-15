/* ==========================================================================
   URA Screens — the 17-screen registry, route aliases and screen renderers.
   Classic browser script: exposes window.URAScreens.
   ========================================================================== */
(function () {
  'use strict';

  var C = window.URACore;
  if (!C) return;

  // ---------------------------------------------------------------------------
  // Registry
  // ---------------------------------------------------------------------------
  var NAV = [
    { id: 'overview', group: 'Workspace', label: 'Overview', icon: 'home', route: '/overview', section: 'view-overview' },
    { id: 'ask-ceo', group: 'Workspace', label: 'Ask CEO', icon: 'crown', route: '/ask-ceo', section: 'view-ceo' },
    { id: 'approvals', group: 'Workspace', label: 'Approvals', icon: 'check-circle', route: '/approvals', section: 'view-approvals' },
    { id: 'operations', group: 'Departments', label: 'Operations (COO)', icon: 'flow', route: '/operations', section: 'view-operations' },
    { id: 'marketing', group: 'Departments', label: 'Marketing & Sales (CMO)', icon: 'megaphone', route: '/marketing', section: 'view-customers' },
    { id: 'technology', group: 'Departments', label: 'Technology (CTO)', icon: 'chip', route: '/technology', section: 'view-technology' },
    { id: 'finance', group: 'Departments', label: 'Finance (CFO)', icon: 'coins', route: '/finance', section: 'view-finance' },
    { id: 'people', group: 'Departments', label: 'People (CHRO)', icon: 'people', route: '/people', section: 'view-people' },
    { id: 'employees', group: 'Workforce', label: 'AI Employees', icon: 'badge', route: '/employees', section: 'view-workforce' },
    { id: 'agents', group: 'Workforce', label: 'Agents', icon: 'sparkles', route: '/agents', section: 'view-agent-factory' },
    { id: 'coworker', group: 'Workforce', label: 'Co-worker', icon: 'hand', route: '/coworker', section: 'view-coworker' },
    { id: 'tools', group: 'System', label: 'Tools & Integrations', icon: 'layers', route: '/tools', section: 'view-tools' },
    { id: 'security', group: 'System', label: 'Security', icon: 'shield', route: '/security', section: 'view-security' },
    { id: 'terminal', group: 'System', label: 'Terminal', icon: 'terminal', route: '/terminal', section: 'view-terminal' },
    { id: 'reports', group: 'System', label: 'Reports', icon: 'chart', route: '/reports', section: 'view-reports' },
    { id: 'companies', group: 'System', label: 'Companies', icon: 'building', route: '/companies', section: 'view-company' }
  ];

  var SETTINGS_SCREEN = { id: 'settings', group: 'System', label: 'Settings', icon: 'settings', route: '/settings', section: 'view-settings' };
  var ALL = NAV.concat([SETTINGS_SCREEN]);
  var BY_ID = {};
  ALL.forEach(function (s) { BY_ID[s.id] = s; });

  var ALIASES = {
    '/': 'overview', '/overview': 'overview', '/home': 'overview', '/dashboard': 'overview',
    '/ask-ceo': 'ask-ceo', '/ceo': 'ask-ceo', '/ai-ceo': 'ask-ceo', '/assistant': 'ask-ceo',
    '/approvals': 'approvals',
    '/operations': 'operations', '/missions': 'operations', '/work': 'operations', '/schedule': 'operations',
    '/marketing': 'marketing', '/sales': 'marketing', '/crm': 'marketing', '/customers': 'marketing',
    '/technology': 'technology', '/tech': 'technology',
    '/finance': 'finance', '/accounting': 'finance',
    '/people': 'people', '/hr': 'people',
    '/employees': 'employees', '/workforce': 'employees',
    '/agents': 'agents', '/agent-factory': 'agents',
    '/coworker': 'coworker', '/coworkers': 'coworker',
    '/tools': 'tools', '/integrations': 'tools',
    '/security': 'security', '/governance': 'security',
    '/terminal': 'terminal',
    '/reports': 'reports', '/bi': 'reports',
    '/companies': 'companies'
  };

  // Paths with sub-paths that stay with their legacy workspace.
  function legacyPath(clean) {
    if (/^\/company(\/|$)/.test(clean) && clean !== '/company' && clean !== '/companies') return true;
    if (/^\/finance(\/|$)/.test(clean) && clean !== '/finance') return true;
    if (/^\/reports(\/|$)/.test(clean) && clean !== '/reports') return true;
    if (/^\/tools(\/|$)/.test(clean) && clean !== '/tools') return true;
    if (/^\/employees(\/|$)/.test(clean) && clean !== '/employees') return true;
    if (/^\/agents(\/|$)/.test(clean) && clean !== '/agents') return true;
    return false;
  }

  function resolve(path) {
    var clean = String(path || '/').split('?')[0].split('#')[0];
    clean = clean.replace(/\/+$/, '') || '/';
    if (clean === '/company') return { screen: 'companies', path: '/' };
    if (clean === '/companies') return { screen: 'companies', path: '/' };
    if (clean === '/settings' || clean === '/settings-legacy') return { screen: 'settings', sub: '', path: clean };
    if (clean.indexOf('/settings/') === 0) return { screen: 'settings', sub: clean.slice('/settings/'.length), path: clean };
    if (legacyPath(clean)) return null;
    if (ALIASES[clean]) {
      var id = ALIASES[clean];
      if (id === 'companies') return { screen: 'companies', path: clean };
      return { screen: id, path: clean };
    }
    // Prefix match for the canonical routes only.
    var keys = Object.keys(ALIASES).filter(function (k) { return k !== '/'; });
    for (var i = 0; i < keys.length; i += 1) {
      if (keys[i] !== '/companies' && clean.indexOf(keys[i] + '/') === 0) {
        var hit = ALIASES[keys[i]];
        return { screen: hit, path: clean };
      }
    }
    return null;
  }

  function screenById(id) { return BY_ID[id] || null; }

  // ---------------------------------------------------------------------------
  // Shared helpers
  // ---------------------------------------------------------------------------
  function h(v) { return C.escapeHtml(v); }

  function money(value, source) {
    return C.formatMoney(value, source ? { sourceCurrency: source } : undefined);
  }

  function num(value, decimals) {
    return C.formatNumber(value, { decimals: decimals === undefined ? 0 : decimals });
  }

  function pct(value) {
    if (value === null || value === undefined || value === '') return '—';
    return C.formatNumber(value, { decimals: 1 }) + '%';
  }

  function phaseOf(status) {
    var s = String(status || '').toUpperCase();
    if (s.indexOf('BUILD') !== -1) return 'Building';
    if (s.indexOf('STUD') !== -1 || s.indexOf('ONBOARD') !== -1) return 'Studying';
    if (s.indexOf('OPERAT') !== -1 || s.indexOf('ACTIVE') !== -1) return 'Operating';
    return 'Operating';
  }

  function companyLabel() {
    var c = C.activeCompany();
    return c ? c.name : 'All companies';
  }

  function pageHead(eyebrow, title, subtitle, actions) {
    return '<div class="ura-page-head"><div><div class="ura-eyebrow">' + h(eyebrow || 'Workspace') + '</div>' +
      '<h1 class="ura-title">' + h(title) + '</h1>' +
      (subtitle ? '<p class="ura-subtitle">' + h(subtitle) + '</p>' : '') + '</div>' +
      (actions ? '<div class="ura-head-actions">' + actions + '</div>' : '') + '</div>';
  }

  function errorCard(message, retry) {
    return '<div class="ura-card" style="border-color:var(--ura-bad-bg);">' +
      '<b>Something went wrong</b><p style="color:var(--ura-fg-2);margin:6px 0 12px;">' + h(message) + '</p>' +
      (retry ? '<button class="ura-btn" type="button" data-retry="' + h(retry) + '">' + icon('refresh-cw') + 'Retry</button>' : '') +
    '</div>';
  }

  function emptyCard(title, body, action) {
    return '<div class="ura-empty"><b>' + h(title) + '</b><p>' + h(body) + '</p>' + (action || '') + '</div>';
  }

  function icon(name) {
    return window.Icon ? window.Icon({ name: name, size: 16, tone: 'accent' }) : '';
  }

  function pill(text, tone) {
    return '<span class="ura-pill ' + (tone || '') + '">' + h(text) + '</span>';
  }

  function riskPill(level) {
    var level2 = String(level || 'LOW').toUpperCase();
    var tone = level2 === 'HIGH' || level2 === 'CRITICAL' ? 'bad' : (level2 === 'MEDIUM' ? 'warn' : 'good');
    return pill(level2.charAt(0) + level2.slice(1).toLowerCase() + ' risk', tone);
  }

  function sparkline(values, tone) {
    if (!values || values.length < 2) return '';
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var span = max - min || 1;
    var points = values.map(function (v, i) {
      var x = (i / (values.length - 1)) * 100;
      var y = 28 - ((v - min) / span) * 24;
      return x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ');
    return '<svg viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true" style="width:100%;height:30px;margin-top:6px;">' +
      '<polyline points="' + points + '" fill="none" stroke="' + (tone || 'var(--ura-accent)') + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></polyline>' +
    '</svg>';
  }

  function kpi(label, value, foot, values, tone) {
    return '<div class="ura-card ura-kpi"><div class="k-label">' + h(label) + '</div>' +
      '<div class="k-value">' + h(value) + '</div>' +
      '<div class="k-foot">' + (foot || '') + '</div>' + sparkline(values, tone) + '</div>';
  }

  function activeSection(id) {
    var section = document.getElementById(id);
    if (!section) return null;
    document.querySelectorAll('.view-section').forEach(function (el) { el.classList.remove('active'); });
    section.classList.add('active');
    return section;
  }

  // ---------------------------------------------------------------------------
  // Overview
  // ---------------------------------------------------------------------------
  var overviewState = { period: '30d', weeks: 4, chart: 'chart' };

  async function renderOverview(el) {
    var companyId = (typeof state !== 'undefined' && state.activeCompanyId) || '';
    el.innerHTML = pageHead('Workspace', greeting() + ', ' + ownerName(), 'Watching ' + companyLabel() + '.') +
      '<div class="ura-card"><div class="ura-host-loading">Reading the live company snapshot…</div></div>';

    var snap;
    try {
      var qs = '/api/overview/snapshot?period=' + encodeURIComponent(overviewState.period);
      if (companyId) qs += '&company_id=' + encodeURIComponent(companyId);
      snap = await C.api(qs);
    } catch (err) {
      el.innerHTML = pageHead('Workspace', greeting() + ', ' + ownerName(), 'Watching ' + companyLabel() + '.') +
        errorCard(err.message || 'The overview service did not answer.', 'overview');
      return;
    }

    var company = snap.company || {};
    var financial = snap.financial || {};
    var sales = snap.sales || {};
    var workforce = snap.workforce || {};
    var missions = snap.missions || {};
    var attention = snap.attention || {};
    var currency = financial.currency || company.currency || C.companyCurrency();

    var trend = Array.isArray(financial.trend_points) ? financial.trend_points : [];
    var revSeries = trend.map(function (p) { return Number(p.revenue) || 0; });
    var profitSeries = trend.map(function (p) { return Number(p.profit) || 0; });

    // Decisions that only the owner can clear.
    var waiting = [];
    try { waiting = await ownerApprovals(); } catch (e) { waiting = []; }

    var phase = phaseOf(company.status);
    var location = company.location || company.country || '—';

    var kpis = '<div class="ura-grid k4 kpi">' +
      kpi('Revenue this month', financial.has_data ? money(financial.revenue, currency) : '—',
        financial.has_data ? '<span class="ura-delta">Live</span><span>· ' + h(humanPeriod(snap.context)) + '</span>' : '<span class="ura-delta muted">Not connected</span>',
        revSeries, 'var(--ura-accent)') +
      kpi('Net profit', financial.has_data ? money(financial.operating_profit, currency) : '—',
        financial.has_data ? '<span class="ura-delta' + (Number(financial.operating_profit) < 0 ? ' bad' : '') + '">' + pct(financial.operating_margin_pct) + ' margin</span>' : '<span class="ura-delta muted">Not connected</span>',
        profitSeries, 'var(--ura-good)') +
      kpi('Open leads', sales.has_data ? num(sales.total_leads) : '—',
        sales.has_data ? '<span class="ura-delta muted">' + money(sales.pipeline_value, currency) + ' pipeline</span>' : '<span class="ura-delta muted">Connect a CRM</span>',
        [], 'var(--ura-warn)') +
      kpi('Agents running', (workforce.active_workers !== undefined && workforce.active_workers !== null) ? num(workforce.active_workers) : '—',
        (workforce.ai_workforce !== undefined && workforce.ai_workforce !== null) ? '<span class="ura-delta muted">' + num(workforce.ai_workforce) + ' AI employees</span>' : '<span class="ura-delta muted">No workforce yet</span>',
        [], 'var(--ura-fg-2)') +
    '</div>';

    var decisions = '<div class="ura-grid k2" style="align-items:start;">' +
      '<div class="ura-card"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">' +
        '<h2 style="margin:0;font-size:1rem;flex:1;">Decisions waiting</h2>' +
        (waiting.length ? pill(String(waiting.length) + ' waiting', 'warn') : pill('Clear', 'good')) + '</div>' +
        (waiting.length ? waiting.slice(0, 4).map(function (item) {
          return '<div class="ura-row"><div class="rt"><b>' + h(item.what || 'Approval requested') + '</b>' +
            '<small>' + riskPill(item.risk_level) + ' ' + h(item.why || '') + '</small></div>' +
            '<div class="ura-head-actions"><button class="ura-btn small" type="button" data-approve="' + h(item.approval_id) + '">Approve</button>' +
            '<button class="ura-btn small plain" type="button" data-deny="' + h(item.approval_id) + '">Decline</button></div></div>';
        }).join('') + '<div style="margin-top:8px;"><button class="ura-btn plain small" type="button" data-go="/approvals">See all approvals ' +
          (window.Icon ? window.Icon({ name: 'arrow-right', size: 14, tone: 'muted' }) : '') + '</button></div>'
          : emptyCard('Nothing needs you', 'Routine work is running under your autonomy setting. New decisions appear here and in the bell.')) +
      '</div>' +
      '<div class="ura-card"><h2 style="margin:0 0 10px;font-size:1rem;">Company at a glance</h2>' +
        '<div class="ura-row"><div class="rt"><b>Phase</b><small>' + h(phase) + '</small></div>' + pill(phase, phase === 'Operating' ? 'good' : 'accent') + '</div>' +
        '<div class="ura-row"><div class="rt"><b>Location</b><small>' + h(location) + '</small></div><span class="ura-pill">' + h(company.industry || '—') + '</span></div>' +
        '<div class="ura-row"><div class="rt"><b>Waiting approval</b><small>Needs your decision</small></div><span class="ura-pill ' + (missions.awaiting_approval ? 'warn' : 'good') + '">' + num(missions.awaiting_approval || 0) + '</span></div>' +
        '<div class="ura-row"><div class="rt"><b>Critical attention</b><small>From the live overview service</small></div><span class="ura-pill ' + (attention.critical_count ? 'bad' : 'good') + '">' + num(attention.critical_count || 0) + '</span></div>' +
      '</div>' +
    '</div>';

    var departments = '<div class="ura-card"><h2 style="margin:0 0 10px;font-size:1rem;">Departments</h2><div class="ura-grid k3">' +
      deptCard('Operations', 'COO', missions.active_missions !== undefined ? num(missions.active_missions) + ' active missions' : 'No mission data', '/operations', 'flow') +
      deptCard('Marketing & Sales', 'CMO', sales.has_data ? num(sales.total_leads) + ' open leads' : 'No CRM connected', '/marketing', 'megaphone') +
      deptCard('Technology', 'CTO', 'Systems, builds and integrations', '/technology', 'chip') +
      deptCard('Finance', 'CFO', financial.has_data ? money(financial.revenue, currency) + ' revenue' : 'No ledger connected', '/finance', 'coins') +
      deptCard('People', 'CHRO', workforce.ai_workforce !== undefined ? num(workforce.ai_workforce) + ' AI employees' : 'No workforce yet', '/people', 'people') +
    '</div></div>';

    var chart = '<div class="ura-card"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">' +
      '<h2 style="margin:0;font-size:1rem;flex:1;">Net profit by week</h2>' +
      '<div class="ura-seg" role="group" aria-label="Chart range">' + [4, 12, 26].map(function (w) {
        return '<button type="button" class="' + (overviewState.weeks === w ? 'is-on' : '') + '" data-weeks="' + w + '">' + w + ' weeks</button>';
      }).join('') + '</div>' +
      '<div class="ura-seg" role="group" aria-label="Chart type">' +
        '<button type="button" class="' + (overviewState.chart === 'chart' ? 'is-on' : '') + '" data-chart="chart">Chart</button>' +
        '<button type="button" class="' + (overviewState.chart === 'table' ? 'is-on' : '') + '" data-chart="table">Table</button>' +
      '</div></div>' + chartBody(trend, currency) + '</div>';

    el.innerHTML = pageHead('Workspace', greeting() + ', ' + ownerName(),
      'Watching ' + (company.name || companyLabel()) + (location !== '—' ? ' · ' + location : '') + ' · ' + phase,
      '<button class="ura-btn" type="button" data-delegate="1">' + icon('plus') + 'Delegate task</button>' +
      '<button class="ura-btn primary" type="button" data-go="/ask-ceo">' + icon('sparkles') + 'Ask CEO</button>') +
      kpis + '<div class="ura-stack" style="margin-top:14px;">' + decisions + departments + chart + '</div>';

    bindScreenActions(el);
  }

  function humanPeriod(context) {
    var label = context && context.period_label;
    if (!label) return 'Current period';
    return String(label).replace(/^Showing data:\s*/, '').replace(/\s+/g, ' ');
  }

  function chartBody(trend, currency) {
    if (overviewState.chart === 'table') {
      if (!trend.length) return emptyCard('No series yet', 'Connect an accounting source to see weekly profit.');
      return '<div style="overflow:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;">' +
        '<thead><tr><th style="text-align:start;padding:8px 6px;border-bottom:1px solid var(--ura-line-2);">Period</th>' +
        '<th style="text-align:end;padding:8px 6px;border-bottom:1px solid var(--ura-line-2);">Revenue</th>' +
        '<th style="text-align:end;padding:8px 6px;border-bottom:1px solid var(--ura-line-2);">Profit</th></tr></thead><tbody>' +
        trend.map(function (p) {
          return '<tr><td style="padding:8px 6px;border-bottom:1px solid var(--ura-line-2);">' + h(p.date || '—') + '</td>' +
            '<td style="padding:8px 6px;text-align:end;border-bottom:1px solid var(--ura-line-2);">' + money(p.revenue, currency) + '</td>' +
            '<td style="padding:8px 6px;text-align:end;border-bottom:1px solid var(--ura-line-2);">' + money(p.profit, currency) + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    }
    if (!trend.length) return emptyCard('No series yet', 'Connect the systems that hold revenue and costs to see a real weekly chart.');
    var points = trend.slice(-Math.max(4, Math.min(overviewState.weeks, trend.length)));
    var values = points.map(function (p) { return Number(p.profit) || 0; });
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var span = max - min || 1;
    var w = 640, ht = 180;
    var path = values.map(function (v, i) {
      var x = (i / Math.max(1, values.length - 1)) * (w - 40) + 20;
      var y = ht - 24 - ((v - min) / span) * (ht - 56);
      return (i === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1);
    }).join(' ');
    var dots = values.map(function (v, i) {
      var x = (i / Math.max(1, values.length - 1)) * (w - 40) + 20;
      var y = ht - 24 - ((v - min) / span) * (ht - 56);
      return '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="3" fill="var(--ura-accent)"><title>' +
        h((points[i].date || '') + ': ' + money(points[i].profit, currency)) + '</title></circle>';
    }).join('');
    return '<div style="overflow-x:auto;"><svg viewBox="0 0 ' + w + ' ' + ht + '" role="img" aria-label="Net profit by week" style="width:100%;min-width:480px;height:auto;">' +
      '<line x1="20" y1="' + (ht - 24) + '" x2="' + (w - 20) + '" y2="' + (ht - 24) + '" stroke="var(--ura-line-2)"></line>' +
      '<path d="' + path + '" fill="none" stroke="var(--ura-accent)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"></path>' +
      dots + '</svg></div>' +
      '<div class="ura-kpi" style="margin-top:6px;"><div class="k-foot"><span class="ura-delta muted">' +
      h((points[0] && points[0].date) || '') + ' → ' + h((points[points.length - 1] && points[points.length - 1].date) || '') +
      '</span><span>· Source: overview snapshot</span></div></div>';
  }

  function deptCard(title, head, detail, route, iconName) {
    return '<button type="button" class="ura-card pad-sm" data-go="' + h(route) + '" style="text-align:start;border:1px solid var(--ura-line-2);background:var(--ura-surface-2);">' +
      '<div style="display:flex;align-items:center;gap:8px;"><span class="ura-nav-icon">' + (window.Icon ? window.Icon({ name: iconName, size: 17, tone: 'accent' }) : '') + '</span>' +
      '<b style="font-size:12.5px;flex:1;">' + h(title) + '</b><span class="ura-pill">' + h(head) + '</span></div>' +
      '<div style="margin-top:6px;color:var(--ura-fg-2);font-size:11.5px;">' + h(detail) + '</div></button>';
  }

  function greeting() {
    var hour = new Date().getHours();
    if (hour < 12) return C.t('greeting.morning');
    if (hour < 17) return C.t('greeting.afternoon');
    return C.t('greeting.evening');
  }

  function ownerName() {
    try { return (state.host && state.host.name) ? state.host.name.split(' ')[0] : 'Owner'; } catch (e) { return 'Owner'; }
  }

  // ---------------------------------------------------------------------------
  // Approvals
  // ---------------------------------------------------------------------------
  async function fetchCoworkerApprovals() {
    var data = await C.api('/api/coworker/approvals');
    return C.toArray(data).filter(function (a) {
      return String(a.status || 'PENDING').toUpperCase() === 'PENDING';
    });
  }

  function normalizeApproval(a) {
    return {
      raw: a,
      id: a.approval_id || a.request_id || a.id,
      what: a.what || a.action_desc || 'Approval requested',
      why: a.why || a.reason || '',
      risk: a.risk_level || 'LOW',
      worker: a.worker || a.agent_id || '',
      when: a.created_at || a.requested_at,
      amount: a.cost_estimate_usd !== undefined ? a.cost_estimate_usd : a.amount,
      currency: a.cost_estimate_usd !== undefined ? 'USD' : (a.currency || null)
    };
  }

  async function ownerApprovals() {
    var items = await fetchCoworkerApprovals();
    return items.map(normalizeApproval).filter(function (a) { return C.needsOwner(a); });
  }

  var approvalsState = { tab: 'waiting' };

  async function renderApprovals(el) {
    el.innerHTML = pageHead('Workspace', 'Approvals', 'Decisions that need the owner. Lower-risk work runs under your autonomy setting.') +
      '<div class="ura-tabs" role="tablist">' +
      '<button class="ura-tab ' + (approvalsState.tab === 'waiting' ? 'is-active' : '') + '" data-apptab="waiting" role="tab">Waiting</button>' +
      '<button class="ura-tab ' + (approvalsState.tab === 'history' ? 'is-active' : '') + '" data-apptab="history" role="tab">History</button>' +
      '</div><div id="uraApprovalsBody"><div class="ura-host-loading">Loading approvals…</div></div>';
    await paintApprovals(el);
  }

  async function paintApprovals(el) {
    var body = el.querySelector('#uraApprovalsBody');
    if (!body) return;
    try {
      if (approvalsState.tab === 'history') {
        var hist = await C.api('/api/approvals');
        var decided = C.toArray(hist).filter(function (a) { return String(a.status || '').toUpperCase() !== 'PENDING'; });
        body.innerHTML = decided.length ? '<div class="ura-card">' + decided.map(function (a) {
          var ok = String(a.status).toUpperCase() === 'APPROVED';
          return '<div class="ura-row"><div class="rt"><b>' + h(a.action_desc || a.request_id || 'Request') + '</b>' +
            '<small>' + h(a.reason || '') + '</small></div>' +
            '<div class="rmeta">' + pill(ok ? 'Approved' : 'Declined', ok ? 'good' : 'bad') +
            '<div style="margin-top:4px;">' + h(a.decided_at ? C.timeAgo(toDate(a.decided_at)) : '') + '</div></div></div>';
        }).join('') + '</div>' : emptyCard('No history yet', 'Decided approvals appear here from the approvals ledger.');
        return;
      }

      var all = await fetchCoworkerApprovals();
      var waiting = all.map(normalizeApproval).filter(function (a) { return C.needsOwner(a); });
      var auto = all.length - waiting.length;
      body.innerHTML = (waiting.length ? '<div class="ura-grid k2" style="align-items:start;">' + waiting.map(function (a) {
        return '<div class="ura-card"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">' +
          riskPill(a.risk) + '<span class="ura-pill">' + h(a.worker || 'AI workforce') + '</span>' +
          '<span style="margin-inline-start:auto;color:var(--ura-fg-3);font-size:11px;">' + h(a.when ? C.timeAgo(toDate(a.when)) : '') + '</span></div>' +
          '<h3 style="margin:0 0 5px;font-size:0.95rem;line-height:1.3;">' + h(a.what) + '</h3>' +
          '<p style="margin:0 0 8px;color:var(--ura-fg-2);font-size:12px;line-height:1.5;">' + h(a.why) + '</p>' +
          (a.amount !== undefined && a.amount !== null ? '<div style="margin-bottom:10px;font-size:12px;">Amount <b>' + money(a.amount, a.currency) + '</b></div>' : '') +
          '<div class="ura-head-actions"><button class="ura-btn primary small" type="button" data-approve="' + h(a.id) + '">' + icon('check') + 'Approve</button>' +
          '<button class="ura-btn small" type="button" data-deny="' + h(a.id) + '">' + icon('x') + 'Decline</button></div></div>';
      }).join('') + '</div>' : emptyCard('No decisions waiting', 'Everything inside your autonomy and payment limits has been handled. New decisions appear here.')) +
        (auto > 0 ? '<div class="ura-suggest ok" style="margin-top:12px;">' + icon('info') + '<span><b>' + auto + ' lower-risk item' + (auto === 1 ? '' : 's') + '</b> did not need you under the current autonomy setting.</span></div>' : '');
    } catch (err) {
      body.innerHTML = errorCard(err.message || 'The approvals service did not answer.', 'approvals');
    }
  }

  function toDate(value) {
    if (!value) return null;
    if (typeof value === 'number') return new Date(value > 1e12 ? value : value * 1000);
    return new Date(value);
  }

  async function decideApproval(id, decision) {
    await C.api('/api/coworker/approvals/' + encodeURIComponent(id) + '/decide', {
      method: 'POST',
      body: { decision: decision }
    });
    C.toast(decision === 'APPROVE' ? 'Approved' : 'Declined', 'success');
  }

  // ---------------------------------------------------------------------------
  // Ask CEO
  // ---------------------------------------------------------------------------
  var chatState = { messages: [], pending: false, attachment: null };

  function renderAskCeo(el) {
    var company = companyLabel();
    var suggestions = [
      'How is ' + company + ' doing this week?',
      'What needs my approval right now?',
      'Where are we losing money?',
      'Summarise the sales pipeline.'
    ];
    el.innerHTML = pageHead('Workspace', 'Ask CEO', 'Answers use the live company snapshot. Nothing is scripted.',
      '<button class="ura-btn" type="button" data-go="/approvals">' + icon('check-circle') + 'Approvals</button>') +
      '<div class="ura-card" style="display:flex;flex-direction:column;min-height:420px;">' +
        '<div id="uraChatLog" style="flex:1;display:flex;flex-direction:column;gap:10px;overflow:auto;max-height:52vh;padding:2px;">' +
          chatMessagesHtml() + '</div>' +
        '<div style="display:flex;gap:7px;flex-wrap:wrap;margin:12px 0 8px;">' + suggestions.map(function (q) {
          return '<button class="ura-pill accent" type="button" data-ask="' + h(q) + '" style="border:0;cursor:pointer;">' + h(q) + '</button>';
        }).join('') + '</div>' +
        '<div id="uraChatAttach" style="display:none;margin-bottom:6px;"></div>' +
        '<div style="display:flex;gap:7px;align-items:center;">' +
          '<button class="ura-icon-btn" type="button" data-attach="1" aria-label="Attach a document">' + icon('file-text') + '</button>' +
          '<input id="uraChatInput" class="ura-input" placeholder="Ask about profit, leads, risk or what to do next…" aria-label="Message the CEO" style="flex:1;">' +
          '<button class="ura-btn primary" type="button" data-send="1" aria-label="Send">' + icon('arrow-right') + '</button>' +
        '</div>' +
        '<input type="file" id="uraChatFile" style="display:none" aria-hidden="true">' +
      '</div>';
    bindChat(el);
  }

  function chatMessagesHtml() {
    if (!chatState.messages.length) {
      return '<div class="ura-empty"><b>Start with a question</b><p>The CEO reads the same live snapshot as Overview. If a service is not connected, it says so instead of guessing.</p></div>';
    }
    return chatState.messages.map(function (m) {
      if (m.role === 'user') {
        return '<div style="align-self:flex-end;max-width:86%;padding:9px 12px;border-radius:16px 16px 4px 16px;background:var(--ura-accent);color:var(--ura-accent-fg);font-size:12.5px;line-height:1.5;">' + h(m.text) + '</div>';
      }
      if (m.role === 'pending') {
        return '<div class="ura-host-loading" style="align-self:flex-start;">' + h(m.text) + '</div>';
      }
      return '<div style="align-self:flex-start;max-width:92%;padding:10px 12px;border-radius:16px 16px 16px 4px;background:var(--ura-surface-2);border:1px solid var(--ura-line-2);font-size:12.5px;line-height:1.6;white-space:pre-wrap;">' +
        h(m.text) + (m.meta ? '<div style="margin-top:6px;font-size:10.5px;color:var(--ura-fg-3);">' + h(m.meta) + '</div>' : '') + '</div>';
    }).join('');
  }

  function bindChat(el) {
    var input = el.querySelector('#uraChatInput');
    var file = el.querySelector('#uraChatFile');
    el.addEventListener('click', function (e) {
      var ask = e.target.closest('[data-ask]');
      if (ask) { sendChat(el, ask.getAttribute('data-ask')); return; }
      if (e.target.closest('[data-send]')) { sendChat(el, input ? input.value : ''); return; }
      if (e.target.closest('[data-attach]') && file) file.click();
    });
    el.addEventListener('keydown', function (e) {
      if (e.target === input && e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat(el, input.value);
      }
    });
    if (file) {
      file.addEventListener('change', function () {
        var f = file.files && file.files[0];
        if (!f) return;
        var reader = new FileReader();
        reader.onload = async function () {
          try {
            var res = await C.api('/api/assistant/documents/upload', {
              method: 'POST',
              body: { filename: f.name, content_base64: reader.result, storage_boundary: 'PERSONAL' }
            });
            chatState.attachment = { name: f.name, id: (res.document && (res.document.doc_id || res.document.document_id || res.document.id)) || '' };
            var box = el.querySelector('#uraChatAttach');
            if (box) {
              box.style.display = 'block';
              box.innerHTML = '<span class="ura-pill accent">' + icon('file-text') + ' ' + h(f.name) + '</span>';
            }
            C.toast('Document attached', 'success');
          } catch (err) {
            C.toast('Upload failed: ' + err.message, 'error');
          }
        };
        reader.readAsDataURL(f);
      });
    }
  }

  async function sendChat(el, text) {
    text = String(text || '').trim();
    if (!text || chatState.pending) return;
    var input = el.querySelector('#uraChatInput');
    if (input) input.value = '';
    chatState.messages.push({ role: 'user', text: text });
    chatState.messages.push({ role: 'pending', text: C.t('action.search') ? 'Thinking…' : 'Thinking…' });
    chatState.pending = true;
    paintChat(el);

    var tone = C.readSettings().tone;
    var message = (tone === 'detailed' ? 'Answer in full detail with concrete figures. ' : 'Answer briefly. ') + text;
    if (chatState.attachment) {
      message += '\n\nAttached document: ' + chatState.attachment.name + (chatState.attachment.id ? ' (id ' + chatState.attachment.id + ')' : '') + '.';
    }

    try {
      var res = await C.api('/api/v8/chat', { method: 'POST', body: { message: message } });
      var reply = (res && res.reply) || {};
      var answer = reply.answer || (res && res.answer);
      if (!answer) throw new Error('The CEO service returned an empty answer.');
      chatState.messages.pop();
      var meta = [];
      if (reply.model_used) meta.push(reply.model_used);
      if (reply.epistemic_classification) meta.push(reply.epistemic_classification);
      if (reply.evidence_digest) meta.push('Evidence ' + String(reply.evidence_digest).slice(0, 18));
      chatState.messages.push({ role: 'assistant', text: answer, meta: meta.join(' · ') });
      chatState.attachment = null;
      var attachBox = el.querySelector('#uraChatAttach');
      if (attachBox) { attachBox.style.display = 'none'; attachBox.innerHTML = ''; }
    } catch (err) {
      chatState.messages.pop();
      chatState.messages.push({ role: 'assistant', text: 'I could not reach the CEO service. ' + (err.message || '') + ' Nothing is being simulated — try again when the service is available.' });
    }
    chatState.pending = false;
    paintChat(el);
  }

  function paintChat(el) {
    var log = el.querySelector('#uraChatLog');
    if (!log) return;
    log.innerHTML = chatMessagesHtml();
    log.scrollTop = log.scrollHeight;
  }

  // ---------------------------------------------------------------------------
  // Companies
  // ---------------------------------------------------------------------------
  var companyMeta = {};

  async function loadCompanyMeta(id) {
    var cached = companyMeta[id];
    if (cached && Date.now() - cached.at < 300000) return cached.snap;
    try {
      var snap = await C.api('/api/overview/snapshot?period=30d&company_id=' + encodeURIComponent(id));
      companyMeta[id] = { at: Date.now(), snap: snap };
      return snap;
    } catch (e) {
      companyMeta[id] = { at: Date.now(), snap: null };
      return null;
    }
  }

  async function renderCompanies(el) {
    var companies = [];
    try { companies = (typeof state !== 'undefined' && state.companies) || []; } catch (e) { companies = []; }
    if (!companies.length) {
      el.innerHTML = pageHead('System', 'Companies', 'All companies in this workspace.',
        '<button class="ura-btn primary" type="button" data-go="/company/new">' + icon('plus') + 'Create new company</button>') +
        emptyCard('No company yet', 'Create a company from a brief, or connect an existing business with its website, booking, sales and CRM systems.',
          '<button class="ura-btn primary" type="button" data-go="/company/new">Start the company flow</button>');
      bindScreenActions(el);
      return;
    }

    el.innerHTML = pageHead('System', 'Companies', 'All companies in this workspace.',
      '<button class="ura-btn" type="button" data-go="/company/new">' + icon('plus') + 'Connect existing</button>' +
      '<button class="ura-btn primary" type="button" data-go="/company/new">' + icon('plus') + 'Create new company</button>') +
      '<div class="ura-card"><div class="ura-host-loading">Reading company records and local time…</div></div>';

    var snaps = await Promise.all(companies.map(function (c) { return loadCompanyMeta(c.id); }));
    var merged = companies.map(function (c, i) {
      var snap = snaps[i] || {};
      return { base: c, company: snap.company || {}, financial: snap.financial || {}, attention: snap.attention || {} };
    });

    var activeId = (typeof state !== 'undefined' && state.activeCompanyId) || '';
    var cards = merged.map(function (row) {
      var c = row.base;
      var meta = row.company;
      var financial = row.financial;
      var phase = phaseOf(meta.status || c.status);
      var isActive = c.id === activeId;
      var currency = meta.currency || c.currency;
      var hasMoney = financial.has_data === true;
      var critical = Number(row.attention.critical_count) || 0;
      return '<div class="ura-card" style="display:flex;flex-direction:column;gap:10px;">' +
        '<div style="display:flex;align-items:flex-start;gap:10px;">' +
          '<div class="ura-company-avatar" style="width:40px;height:40px;flex:0 0 40px;font-size:14px;">' + h(String(meta.name || c.name || 'C').charAt(0).toUpperCase()) + '</div>' +
          '<div style="flex:1;min-width:0;"><b style="display:block;font-size:0.95rem;">' + h(meta.name || c.name) + '</b>' +
          '<small style="color:var(--ura-fg-3);">' + h(meta.industry || c.industry || 'General') + (meta.location ? ' · ' + h(meta.location) : '') + '</small></div>' +
          (isActive ? pill('Active', 'good') : '') + '</div>' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap;">' + pill(phase, phase === 'Operating' ? 'good' : 'accent') +
          (currency ? pill(currency) : '') + pill(critical ? critical + ' critical' : 'Healthy', critical ? 'bad' : 'good') + '</div>' +
        '<div class="ura-list">' +
          '<div class="ura-row"><div class="rt"><b>Revenue</b><small>' + (hasMoney ? 'Recorded by the company ledger' : 'No ledger connected') + '</small></div><span>' + (hasMoney ? money(financial.revenue, currency) : '—') + '</span></div>' +
          '<div class="ura-row"><div class="rt"><b>Net profit</b><small>' + (hasMoney ? 'Operating profit' : 'No ledger connected') + '</small></div><span>' + (hasMoney ? money(financial.operating_profit, currency) : '—') + '</span></div>' +
          '<div class="ura-row"><div class="rt"><b>Workforce</b><small>AI employees and agents</small></div><span>' + num(c.workforce_count || 0) + '</span></div>' +
          '<div class="ura-row"><div class="rt"><b>Missions</b><small>Active and completed</small></div><span>' + num(c.missions_count || 0) + '</span></div>' +
        '</div>' +
        '<div class="ura-head-actions"><button class="ura-btn' + (isActive ? '' : ' primary') + ' small" type="button" data-switch-company="' + h(c.id) + '"' + (isActive ? ' disabled' : '') + '>' +
          (isActive ? 'Current company' : 'Switch to this company') + '</button>' +
          '<button class="ura-btn small plain" type="button" data-go="/overview">Open overview</button></div>' +
      '</div>';
    }).join('');

    el.innerHTML = pageHead('System', 'Companies', companies.length + ' compan' + (companies.length === 1 ? 'y' : 'ies') + ' in this workspace.',
      '<button class="ura-btn" type="button" data-go="/company/new">' + icon('plus') + 'Connect existing</button>' +
      '<button class="ura-btn primary" type="button" data-go="/company/new">' + icon('plus') + 'Create new company</button>') +
      '<div class="ura-grid k3">' + cards + '</div>' +
      '<div class="ura-card" style="margin-top:14px;"><h2 style="margin:0 0 6px;font-size:1rem;">Company clock</h2>' +
        '<p style="margin:0 0 10px;color:var(--ura-fg-2);font-size:12.5px;">Local time is shown only for companies that store a time zone. Missing time zones are left blank instead of guessed.</p>' +
        clockRows(merged) + '</div>';
    bindScreenActions(el);
  }

  function clockRows(rows) {
    var out = rows.filter(function (row) { return row.company && row.company.timezone; }).map(function (row) {
      var name = row.company.name || row.base.name;
      var tz = row.company.timezone;
      return '<div class="ura-row"><div class="rt"><b>' + h(name) + '</b><small>' + h(tz) + '</small></div>' +
        '<span class="ura-clock" data-company-clock="' + h(tz) + '">' + C.formatTime(new Date(), { timeZone: tz }) + '</span></div>';
    });
    return out.length ? out.join('') : '<div class="ura-host-loading">No company has a stored time zone yet.</div>';
  }

  // ---------------------------------------------------------------------------
  // Department and system hosts
  // ---------------------------------------------------------------------------
  var hostTabs = {};

  function hostScreen(el, screen, subtitle, tabs, actions) {
    var key = screen.id;
    var active = hostTabs[key] || 0;
    if (active >= tabs.length) active = 0;
    el.innerHTML = pageHead(screen.group, screen.label, subtitle, actions) +
      (tabs.length > 1 ? '<div class="ura-tabs" role="tablist">' + tabs.map(function (t, i) {
        return '<button type="button" class="ura-tab ' + (i === active ? 'is-active' : '') + '" data-host-tab="' + i + '" role="tab">' + h(t.label) + '</button>';
      }).join('') + '</div>' : '') +
      '<div class="ura-host"><div class="ura-host-body" id="uraHostBody"></div></div>';

    function paint() {
      var body = el.querySelector('#uraHostBody');
      if (!body) return;
      var tab = tabs[active] || tabs[0];
      body.innerHTML = '<div class="ura-host-loading">Loading…</div>';
      try {
        var out = tab.run(body, screen);
        if (out && typeof out.catch === 'function') {
          out.catch(function (err) { body.innerHTML = errorCard(err.message || 'This workspace could not load.', screen.id); });
        }
      } catch (err) {
        body.innerHTML = errorCard(err.message || 'This workspace could not load.', screen.id);
      }
    }

    el.querySelectorAll('[data-host-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        hostTabs[key] = Number(btn.getAttribute('data-host-tab')) || 0;
        el.querySelectorAll('[data-host-tab]').forEach(function (b) { b.classList.toggle('is-active', b === btn); });
        paint();
      });
    });
    paint();
  }

  function legacyCall(fnName, method, args) {
    return function (body, screen) {
      var obj = window[fnName];
      if (!obj || typeof obj[method] !== 'function') {
        body.innerHTML = emptyCard('Not available', fnName + ' is not loaded in this build.');
        return null;
      }
      return obj[method].apply(obj, [body.id].concat(args || []));
    };
  }

  function renderOperations(el, screen) {
    hostScreen(el, screen, 'Operations tasks, throughput and the work schedule.',
      [
        { label: 'Work orders', run: legacyCall('OperationsWorkspace', 'render') },
        { label: 'Schedule', run: legacyCall('ScheduleWorkspace', 'render') },
        { label: 'Missions', run: legacyCall('AssistantCoworkerWorkspace', 'renderMissions') }
      ],
      '<button class="ura-btn" type="button" data-go="/schedule">' + icon('calendar') + 'Open schedule</button>');
  }

  function renderMarketing(el, screen) {
    hostScreen(el, screen, 'Campaigns, leads and the sales pipeline.',
      [
        { label: 'Pipeline', run: legacyCall('CrmWorkspace', 'render') },
        { label: 'Missions', run: legacyCall('AssistantCoworkerWorkspace', 'renderMissions') },
        { label: 'Reports', run: legacyCall('ReportsWorkspace', 'render') }
      ]);
  }

  function renderTechnology(el, screen) {
    hostScreen(el, screen, 'Websites, systems, builds and integration health.',
      [
        { label: 'Integrations', run: legacyCall('IntegrationsWorkspace', 'render') },
        { label: 'Agent factory', run: legacyCall('AgentFactoryWorkspace', 'render') },
        { label: 'MCP network', run: legacyCall('McpWorkspace', 'render') },
        { label: 'Browser use', run: legacyCall('browserWorkspace', 'render') }
      ]);
  }

  function renderFinance(el, screen) {
    hostScreen(el, screen, 'Revenue, costs, profit and invoices.', [
      { label: 'Finance', run: legacyCall('FinanceWorkspace', 'render', [window.location.hash.replace(/^#/, '') || '/finance']) }
    ]);
  }

  function renderPeople(el, screen) {
    hostScreen(el, screen, 'AI employees, agents and hiring.', [
      { label: 'People', run: legacyCall('PeopleWorkspace', 'render') }
    ]);
  }

  function renderEmployees(el, screen) {
    hostScreen(el, screen, 'Roster, KRA/KPI and SOPs. Employees can use agents; agents never use employees.', [
      { label: 'AI employees', run: legacyCall('WorkforceWorkspace', 'render') }
    ], '<button class="ura-btn primary" type="button" data-go="/agents">' + icon('sparkles') + 'Browse agents</button>');
  }

  function renderAgents(el, screen) {
    hostScreen(el, screen, 'Installed agents, templates and the agent network.', [
      { label: 'Agent factory', run: legacyCall('AgentFactoryWorkspace', 'render') },
      { label: 'Agent network', run: legacyCall('AgentNetworkWorkspace', 'render') }
    ]);
  }

  function renderCoworker(el, screen) {
    hostScreen(el, screen, 'The owner\'s personal Jarvis for browser and desktop work.', [
      { label: 'Co-worker', run: legacyCall('AssistantCoworkerWorkspace', 'renderCoworker') }
    ]);
  }

  function renderTools(el, screen) {
    hostScreen(el, screen, 'Connected systems, MCPs and APIs.', [
      { label: 'Tools', run: function (body) {
        if (window.ToolsFactory && window.ToolsFactory.render) return window.ToolsFactory.render(window.location.hash.replace(/^#/, '') || '/tools', body.id);
        body.innerHTML = emptyCard('Not available', 'The tools registry is not loaded.');
      } },
      { label: 'Integrations', run: legacyCall('IntegrationsWorkspace', 'render') },
      { label: 'Nango sync', run: legacyCall('NangoWorkspaceManager', 'render') }
    ]);
  }

  function renderTerminal(el, screen) {
    hostScreen(el, screen, 'Commands run against the real host and write to the audit log.', [
      { label: 'Terminal', run: legacyCall('AssistantCoworkerWorkspace', 'renderTerminal') }
    ]);
  }

  function renderReports(el, screen) {
    hostScreen(el, screen, 'Scheduled and on-demand reports.', [
      { label: 'Reports', run: legacyCall('ReportsWorkspace', 'render') }
    ]);
  }

  // ---------------------------------------------------------------------------
  // Security (real settings posture + real pending high-risk findings)
  // ---------------------------------------------------------------------------
  async function renderSecurity(el) {
    var settings = C.readSettings();
    var company = C.activeCompany();
    var region = company && (company.region || company.country);
    el.innerHTML = pageHead('System', 'Security', 'The score is computed from your settings and open high-risk decisions. No sample findings.') +
      '<div id="uraSecurityBody"><div class="ura-host-loading">Checking security posture…</div></div>';
    await paintSecurity(el, settings, region);
  }

  async function paintSecurity(el, settings, region) {
    var body = el.querySelector('#uraSecurityBody');
    if (!body) return;
    var findings = [];
    try { findings = (await fetchCoworkerApprovals()).map(normalizeApproval).filter(function (a) { return C.riskLevel(a) === 2; }); }
    catch (e) { findings = []; }
    var score = C.secScore(settings, findings.length, region);
    var tone = score >= 80 ? 'good' : (score >= 60 ? 'warn' : 'bad');
    var ring = 2 * Math.PI * 54;
    var dash = ring * (score / 100);

    body.innerHTML = '<div class="ura-grid k2" style="align-items:start;">' +
      '<div class="ura-card" style="display:flex;gap:18px;align-items:center;flex-wrap:wrap;">' +
        '<svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label="Security score ' + score + ' out of 100">' +
          '<circle cx="70" cy="70" r="54" fill="none" stroke="var(--ura-line-2)" stroke-width="12"></circle>' +
          '<circle cx="70" cy="70" r="54" fill="none" stroke="var(--ura-' + (tone === 'good' ? 'good' : tone === 'warn' ? 'warn' : 'bad') + ')" stroke-width="12" stroke-linecap="round" stroke-dasharray="' + dash.toFixed(1) + ' ' + ring.toFixed(1) + '" transform="rotate(-90 70 70)"></circle>' +
          '<text x="70" y="76" text-anchor="middle" font-size="30" font-weight="700" fill="var(--ura-fg)">' + score + '</text>' +
        '</svg>' +
        '<div style="flex:1;min-width:180px;"><div class="ura-eyebrow">Security score</div>' +
          '<h2 style="margin:4px 0 6px;font-size:1.3rem;">' + (score >= 80 ? 'Strong' : score >= 60 ? 'Needs attention' : 'At risk') + '</h2>' +
          '<p style="margin:0;color:var(--ura-fg-2);font-size:12.5px;">Two-step sign-in, session length, audit retention and data region change this score live.</p>' +
          '<div class="ura-head-actions" style="margin-top:10px;"><button class="ura-btn small" type="button" data-scan="1">' + icon('refresh-cw') + 'Run scan</button>' +
          '<button class="ura-btn small plain" type="button" data-go="/settings/security">Review settings</button></div>' +
        '</div></div>' +
      '<div class="ura-card"><h2 style="margin:0 0 8px;font-size:1rem;">Checks</h2>' + [
        ['Two-step sign-in', settings.twofa, settings.twofa ? 'On' : 'Off — turn on in Security settings'],
        ['Session length', settings.session !== 'never', settings.session === 'never' ? 'Until sign out' : 'Ends after ' + settings.session],
        ['Audit retention', true, settings.audit + ' days'],
        ['Data region', !!region, region ? 'Company region: ' + region : 'Company region not stored'],
        ['Terminal policy', settings.terminalOn, settings.terminalOn ? 'Visible to the owner' : 'Hidden from menu and search']
      ].map(function (row) {
        return '<div class="ura-row"><div class="rt"><b>' + h(row[0]) + '</b><small>' + h(row[2]) + '</small></div>' +
          pill(row[1] ? 'On' : 'Off', row[1] ? 'good' : 'bad') + '</div>';
      }).join('') + '</div>' +
    '</div>' +
    '<div class="ura-card" style="margin-top:14px;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">' +
      '<h2 style="margin:0;font-size:1rem;flex:1;">Open high-risk decisions</h2>' + pill(String(findings.length), findings.length ? 'bad' : 'good') + '</div>' +
      (findings.length ? findings.map(function (a) {
        return '<div class="ura-row"><div class="rt"><b>' + h(a.what) + '</b><small>' + h(a.why) + '</small></div>' +
          '<button class="ura-btn small" type="button" data-go="/approvals">Review</button></div>';
      }).join('') : emptyCard('No high-risk findings', 'High-risk approvals appear here. Run a scan to check again.')) +
    '</div>' +
    '<div class="ura-suggest" style="margin-top:12px;">' + icon('info') +
      '<span><b>What is real here:</b> the score and checks come from your saved settings; findings come from pending high-risk approvals. The app does not invent a scan result.</span></div>';
  }

  // ---------------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------------
  var settingsCat = '';

  function renderSettings(el, route, sub) {
    settingsCat = String(sub || '').split('/')[0] || '';
    if (!window.URASettings) {
      el.innerHTML = errorCard('The settings registry did not load.');
      return;
    }
    window.URASettings.render(el, settingsCat);
    window.URASettings.bind(el);
  }

  // ---------------------------------------------------------------------------
  // Locked screen
  // ---------------------------------------------------------------------------
  function renderLocked(el, screen, reason) {
    el.innerHTML = pageHead(screen.group, 'This screen is hidden', 'You can restore it at any time. Nothing was deleted.') +
      '<div class="ura-card" style="max-width:620px;"><h2 style="margin:0 0 6px;font-size:1rem;">' + h(screen.label) + ' is hidden</h2>' +
      '<p style="margin:0 0 12px;color:var(--ura-fg-2);font-size:12.5px;">' + h(reason) + '</p>' +
      '<div class="ura-head-actions"><button class="ura-btn primary" type="button" data-unhide="' + h(screen.id) + '">Show it again</button>' +
      '<button class="ura-btn" type="button" data-go="/overview">Back to Overview</button></div></div>';
  }

  function isHidden(screen) {
    var s = C.readSettings();
    if (screen.id === 'terminal' && s.terminalOn === false) return 'The Terminal is turned off in Settings > Security and privacy.';
    if (Array.isArray(s.hidden) && s.hidden.indexOf(screen.id) !== -1) return 'It was hidden in Settings > Menu and team.';
    return null;
  }

  // ---------------------------------------------------------------------------
  // Action binding
  // ---------------------------------------------------------------------------
  document.addEventListener('click', function (e) {
    var go = e.target.closest('[data-go]');
    if (go) {
      e.preventDefault();
      window.navigateTo(go.getAttribute('data-go'));
      return;
    }
    var retry = e.target.closest('[data-retry]');
    if (retry) {
      window.navigateTo('/' + retry.getAttribute('data-retry'));
      return;
    }
    var approve = e.target.closest('[data-approve]');
    if (approve) {
      e.preventDefault();
      decideApproval(approve.getAttribute('data-approve'), 'APPROVE').then(function () {
        var el = document.querySelector('.view-section.active');
        if (el && el.id === 'view-approvals') paintApprovals(el);
        if (el && el.id === 'view-overview') renderOverview(el);
      }).catch(function (err) { C.toast(err.message || 'Could not approve', 'error'); });
      return;
    }
    var deny = e.target.closest('[data-deny]');
    if (deny) {
      e.preventDefault();
      decideApproval(deny.getAttribute('data-deny'), 'DENY').then(function () {
        var el = document.querySelector('.view-section.active');
        if (el && el.id === 'view-approvals') paintApprovals(el);
        if (el && el.id === 'view-overview') renderOverview(el);
      }).catch(function (err) { C.toast(err.message || 'Could not decline', 'error'); });
      return;
    }
    var tab = e.target.closest('[data-apptab]');
    if (tab) {
      approvalsState.tab = tab.getAttribute('data-apptab');
      var section = document.getElementById('view-approvals');
      if (section) renderApprovals(section);
      return;
    }
    var weeks = e.target.closest('[data-weeks]');
    if (weeks) {
      overviewState.weeks = Number(weeks.getAttribute('data-weeks')) || 4;
      var ov = document.getElementById('view-overview');
      if (ov) renderOverview(ov);
      return;
    }
    var chart = e.target.closest('[data-chart]');
    if (chart) {
      overviewState.chart = chart.getAttribute('data-chart');
      var ov2 = document.getElementById('view-overview');
      if (ov2) renderOverview(ov2);
      return;
    }
    var sw = e.target.closest('[data-switch-company]');
    if (sw) {
      var id = sw.getAttribute('data-switch-company');
      if (typeof handleGlobalCompanyContextChange === 'function') handleGlobalCompanyContextChange(id);
      C.toast('Company switched', 'success');
      return;
    }
    var unhide = e.target.closest('[data-unhide]');
    if (unhide) {
      var screenId = unhide.getAttribute('data-unhide');
      var s = C.readSettings();
      if (screenId === 'terminal') {
        C.saveSettings({ terminalOn: true });
      } else {
        var hidden = (Array.isArray(s.hidden) ? s.hidden : []).filter(function (x) { return x !== screenId; });
        C.saveSettings({ hidden: hidden });
      }
      if (window.URASettings) window.URASettings.apply();
      if (window.URAShell && window.URAShell.renderNav) window.URAShell.renderNav();
      var target = BY_ID[screenId];
      if (target) window.navigateTo(target.route);
      return;
    }
    var scan = e.target.closest('[data-scan]');
    if (scan) {
      var sec = document.getElementById('view-security');
      if (sec) {
        scan.disabled = true;
        scan.textContent = 'Scanning…';
        renderSecurity(sec).then(function () { C.toast('Security posture refreshed', 'success'); });
      }
      return;
    }
    var delegate = e.target.closest('[data-delegate]');
    if (delegate) {
      openDelegateSheet();
      return;
    }
  });

  function bindScreenActions(el) {
    // All actions are delegated at document level; this hook exists so future
    // screen-specific bindings have one place to live.
    void el;
  }

  function openDelegateSheet() {
    if (!window.URAShell) return;
    window.URAShell.openSheet('Delegate a task', '' +
      '<p style="margin:0 0 10px;color:var(--ura-fg-2);font-size:12.5px;">The CEO receives the task and decides which department should own it.</p>' +
      '<textarea id="uraDelegateText" class="ura-input" rows="4" placeholder="What should the company do?" style="min-height:96px;padding:10px;"></textarea>' +
      '<div class="ura-head-actions" style="margin-top:12px;"><button class="ura-btn primary" type="button" id="uraDelegateSend">Delegate to CEO</button>' +
      '<button class="ura-btn" type="button" id="uraDelegateCancel">Cancel</button></div>',
      function (sheet) {
        var send = sheet.querySelector('#uraDelegateSend');
        var cancel = sheet.querySelector('#uraDelegateCancel');
        if (cancel) cancel.onclick = function () { window.URAShell.closeSheet(); };
        if (send) send.onclick = async function () {
          var text = (sheet.querySelector('#uraDelegateText') || {}).value || '';
          if (!text.trim()) { C.toast('Write the task first', 'error'); return; }
          send.disabled = true;
          send.textContent = 'Delegating…';
          try {
            await C.api('/api/coworker/mission', { method: 'POST', body: { prompt: text.trim(), initiator: 'Owner' } });
            window.URAShell.closeSheet();
            C.toast('Task delegated to the CEO', 'success');
            window.navigateTo('/ask-ceo');
          } catch (err) {
            send.disabled = false;
            send.textContent = 'Delegate to CEO';
            C.toast('Could not delegate: ' + err.message, 'error');
          }
        };
      });
  }

  // ---------------------------------------------------------------------------
  // Router
  // ---------------------------------------------------------------------------
  var RENDERERS = {
    overview: renderOverview,
    'ask-ceo': renderAskCeo,
    approvals: renderApprovals,
    operations: renderOperations,
    marketing: renderMarketing,
    technology: renderTechnology,
    finance: renderFinance,
    people: renderPeople,
    employees: renderEmployees,
    agents: renderAgents,
    coworker: renderCoworker,
    tools: renderTools,
    security: renderSecurity,
    terminal: renderTerminal,
    reports: renderReports,
    companies: renderCompanies,
    settings: renderSettings
  };

  function setNav(screen) {
    document.querySelectorAll('.nav-item').forEach(function (item) {
      var on = item.getAttribute('data-nav') === screen.id;
      item.classList.toggle('active', on);
      item.classList.toggle('is-active', on);
      if (on) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
  }

  function renderRoute(route, path) {
    var screen = screenById(route.screen);
    if (!screen) return false;
    if (typeof state !== 'undefined') state.activeNav = screen.id;
    var el = activeSection(screen.section);
    if (!el) return false;
    setNav(screen);
    if (window.URAShell) {
      window.URAShell.setBreadcrumbs(screen.label, screen.group);
      window.URAShell.refreshCompanyChip();
      window.URAShell.updateTabbar();
      window.URAShell.closeDrawer();
    }
    var reason = isHidden(screen);
    if (reason) {
      renderLocked(el, screen, reason);
      return true;
    }
    try {
      if (route.screen === 'settings') {
        renderSettings(el, path, route.sub);
      } else {
        RENDERERS[screen.id](el, screen);
      }
    } catch (err) {
      el.innerHTML = errorCard(err.message || 'This screen could not render.', screen.id);
    }
    return true;
  }

  function installRouter() {
    if (typeof window.handleRoute !== 'function' || window.__uraRouterInstalled) return;
    var legacy = window.handleRoute;
    window.handleRoute = function (path) {
      var clean = String(path || '/').split('?')[0];
      // Keep auth screens and unknown routes with the legacy router.
      if (clean === '/login' || clean === '/signin' || clean === '/register' || clean === '/signup') {
        legacy(path);
        return;
      }
      var route = resolve(clean);
      if (!route) {
        legacy(path);
        return;
      }
      var host = null;
      try { host = (typeof state !== 'undefined' && state.host) || null; } catch (e) { host = null; }
      if (!host) { legacy(path); return; }
      if (renderRoute(route, clean)) {
        document.title = (screenById(route.screen) ? screenById(route.screen).label + ' · ' : '') + 'URA';
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        legacy(path);
      }
    };
    window.__uraRouterInstalled = true;
  }

  // Re-render the current screen after a settings change that affects it.
  document.addEventListener('ura:settings', function (e) {
    var current = (window.location.hash || '#/overview').replace(/^#/, '') || '/overview';
    var route = resolve(current);
    if (!route) return;
    if (route.screen === 'settings') return;
    var el = document.getElementById((screenById(route.screen) || {}).section);
    if (!el) return;
    var detail = (e && e.detail) || {};
    var key = detail.key || '';
    var affectsAll = detail.all || ['lang', 'tz', 'hour', 'dateFmt', 'numFmt', 'currency', 'theme', 'accent', 'density', 'textSize', 'reduceMotion', 'contrast'].indexOf(key) !== -1;
    if (affectsAll && (route.screen === 'overview' || route.screen === 'security' || route.screen === 'ask-ceo')) {
      if (route.screen === 'ask-ceo') return;
      RENDERERS[route.screen](el, current);
    } else if (key === 'terminalOn') {
      renderRoute(route, current);
    } else if (key === 'hidden') {
      renderRoute(route, current);
    }
  });

  installRouter();

  window.URAScreens = {
    NAV: NAV,
    ALL: ALL,
    ALIASES: ALIASES,
    resolve: resolve,
    screenById: screenById,
    renderRoute: renderRoute,
    installRouter: installRouter,
    settingsCategory: function () { return settingsCat; },
    setNav: setNav,
    openDelegateSheet: openDelegateSheet
  };
})();
