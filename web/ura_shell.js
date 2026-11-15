/* ==========================================================================
   URA Shell — sidebar, top bar, drawer, tab bar, palette and overlays.
   Classic browser script: exposes window.URAShell.
   ========================================================================== */
(function () {
  'use strict';

  var C = window.URACore;
  if (!C) return;

  var shellState = {
    paletteOpen: false,
    paletteIndex: 0,
    paletteItems: [],
    popover: null,
    sheet: null,
    lastFocus: null,
    notifications: [],
    notifLoaded: false
  };

  function h(v) { return C.escapeHtml(v); }

  function icon(name, size) {
    return window.Icon ? window.Icon({ name: name, size: size || 18, tone: 'default' }) : '';
  }

  function activeCompany() {
    try {
      var s = (typeof state !== 'undefined' && state) ? state : null;
      if (!s) return null;
      var list = Array.isArray(s.companies) ? s.companies : [];
      return list.find(function (c) { return c && c.id === s.activeCompanyId; }) || null;
    } catch (e) { return null; }
  }

  // ---------------------------------------------------------------------------
  // Sidebar
  // ---------------------------------------------------------------------------
  function renderNav() {
    var host = document.getElementById('uraNav');
    if (!host || !window.URAScreens) return;
    var settings = C.readSettings();
    var hidden = Array.isArray(settings.hidden) ? settings.hidden : [];
    var groups = [];
    var byGroup = {};
    window.URAScreens.NAV.forEach(function (item) {
      if (item.id !== 'overview' && hidden.indexOf(item.id) !== -1) return;
      if (item.id === 'terminal' && settings.terminalOn === false) return;
      if (!byGroup[item.group]) { byGroup[item.group] = []; groups.push(item.group); }
      byGroup[item.group].push(item);
    });

    var html = groups.map(function (group) {
      return '<div class="ura-group"><div class="ura-group-label">' + h(C.t('group.' + group.toLowerCase()) === 'group.' + group.toLowerCase() ? group : C.t('group.' + group.toLowerCase())) + '</div>' +
        byGroup[group].map(navItem).join('') + '</div>';
    }).join('');

    host.innerHTML = html;

    var footer = document.getElementById('uraSidebarFooter');
    if (footer) {
      var screen = window.URAScreens.screenById('settings');
      footer.innerHTML = navItem(screen) + '<div class="ura-sidebar-footer-text" style="padding:8px 12px 2px;color:var(--ura-fg-3);font-size:10.5px;">URA · ' +
        h((typeof state !== 'undefined' && state.host && state.host.tenant_id) || 'local workspace') + '</div>';
    }
    updateActiveNav();
  }

  function navLabel(item) {
    if (!item) return '';
    var key = 'nav.' + String(item.id).replace(/-/g, '');
    var translated = C.t(key);
    return translated === key ? item.label : translated;
  }

  function navItem(item) {
    if (!item) return '';
    var pending = item.id === 'approvals' && shellState.notifications.length;
    var label = navLabel(item);
    return '<button type="button" class="ura-nav-item nav-item" data-nav="' + h(item.id) + '" title="' + h(label) + '" aria-label="' + h(label) + '">' +
      '<span class="ura-nav-icon">' + (window.Icon ? window.Icon({ name: item.icon, size: 18, tone: 'default' }) : '') + '</span>' +
      '<span class="ura-label">' + h(label) + '</span>' +
      (pending ? '<span class="ura-nav-badge">' + shellState.notifications.length + '</span>' : '') +
    '</button>';
  }

  function updateActiveNav() {
    var nav = (typeof state !== 'undefined' && state.activeNav) || 'overview';
    document.querySelectorAll('#uraNav .nav-item, #uraSidebarFooter .nav-item').forEach(function (el) {
      var on = el.getAttribute('data-nav') === nav;
      el.classList.toggle('active', on);
      el.classList.toggle('is-active', on);
      if (on) el.setAttribute('aria-current', 'page');
      else el.removeAttribute('aria-current');
    });
  }

  function renderTabbar() {
    var host = document.getElementById('uraTabbar');
    if (!host || !window.URAScreens) return;
    var tabs = [
      ['overview', 'nav.overview', 'Overview', 'home'],
      ['ask-ceo', 'nav.askceo', 'Ask CEO', 'crown'],
      ['approvals', 'nav.approvals', 'Approvals', 'check-circle'],
      ['employees', 'nav.employees', 'Staff', 'badge'],
      ['more', '', 'More', 'sliders']
    ];
    host.innerHTML = tabs.map(function (t) {
      var label = t[1] ? C.t(t[1]) : t[2];
      if (label === t[1]) label = t[2];
      if (t[0] === 'more') {
        return '<button type="button" class="ura-tab" data-more="1" aria-label="' + h(label) + '">' +
          icon(t[3], 19) + '<span>' + h(label) + '</span></button>';
      }
      return '<button type="button" class="ura-tab" data-tab-nav="' + t[0] + '" aria-label="' + h(label) + '">' +
        icon(t[3], 19) + '<span>' + h(label) + '</span></button>';
    }).join('');
    host.querySelectorAll('[data-tab-nav]').forEach(function (btn) {
      btn.addEventListener('click', function () { window.navigateTo('/' + btn.getAttribute('data-tab-nav')); });
    });
    host.querySelector('[data-more]').addEventListener('click', function () { toggleDrawer(true); });
    updateTabbar();
  }

  function updateTabbar() {
    var host = document.getElementById('uraTabbar');
    if (!host) return;
    var nav = (typeof state !== 'undefined' && state.activeNav) || 'overview';
    var inTabs = false;
    host.querySelectorAll('[data-tab-nav]').forEach(function (btn) {
      var on = btn.getAttribute('data-tab-nav') === nav;
      btn.classList.toggle('is-active', on);
      if (on) { inTabs = true; btn.setAttribute('aria-current', 'page'); }
      else btn.removeAttribute('aria-current');
    });
    var more = host.querySelector('[data-more]');
    if (more) {
      more.classList.toggle('is-active', !inTabs);
      if (!inTabs) more.setAttribute('aria-current', 'page');
      else more.removeAttribute('aria-current');
    }
  }

  // ---------------------------------------------------------------------------
  // Top bar
  // ---------------------------------------------------------------------------
  function setBreadcrumbs(page, group) {
    var host = document.getElementById('topbarBreadcrumbs');
    if (!host) return;
    var company = activeCompany();
    var companyName = company ? company.name : (typeof state !== 'undefined' && state.companies && state.companies.length ? 'All companies' : 'Workspace');
    host.innerHTML = '<button type="button" class="breadcrumb-item root" data-crumb="companies">' + h(companyName) + '</button>' +
      '<span class="breadcrumb-separator" aria-hidden="true">/</span>' +
      (group ? '<span class="breadcrumb-item">' + h(group) + '</span><span class="breadcrumb-separator" aria-hidden="true">/</span>' : '') +
      '<span class="breadcrumb-item active" aria-current="page">' + h(page) + '</span>';
    var crumb = host.querySelector('[data-crumb]');
    if (crumb) crumb.addEventListener('click', function () { window.navigateTo('/companies'); });
  }

  function refreshCompanyChip() {
    var c = activeCompany();
    var nameEl = document.getElementById('companyChipName');
    var subEl = document.getElementById('companyChipSub');
    var avEl = document.getElementById('companyChipAvatar');
    if (!nameEl) return;
    if (c) {
      nameEl.textContent = c.name || 'Company';
      var phase = String(c.status || '').toUpperCase().indexOf('OPERAT') !== -1 ? 'Operating' : (String(c.status || '').toUpperCase().indexOf('BUILD') !== -1 ? 'Building' : 'Operating');
      subEl.textContent = [c.country || c.location, phase].filter(Boolean).join(', ') || (c.industry || 'Company');
      if (avEl) avEl.textContent = String(c.name || 'C').charAt(0).toUpperCase();
    } else {
      nameEl.textContent = (typeof state !== 'undefined' && state.companies && state.companies.length) ? 'All companies' : 'No company yet';
      subEl.textContent = (typeof state !== 'undefined' && state.companies && state.companies.length) ? 'Group portfolio' : 'Create or connect one';
      if (avEl) avEl.textContent = 'U';
    }
  }

  function refreshClock() {
    var el = document.getElementById('uraClock');
    var c = activeCompany();
    var tz = (c && c.timezone) || undefined;
    if (el) {
      try {
        el.textContent = C.formatTime(new Date(), tz ? { timeZone: tz } : undefined);
        el.title = tz ? 'Local time in ' + c.name + ' (' + tz + ')' : 'Your local time';
      } catch (e) {
        el.textContent = C.formatTime(new Date());
      }
    }
    document.querySelectorAll('[data-company-clock]').forEach(function (node) {
      var zone = node.getAttribute('data-company-clock');
      if (!zone) return;
      try { node.textContent = C.formatTime(new Date(), { timeZone: zone }); } catch (e) { /* ignore bad zone */ }
    });
  }

  function refreshStatusPill() {
    var textEl = document.getElementById('uraStatusText');
    if (!textEl) return;
    var hours = C.readSettings().hours;
    textEl.textContent = hours === 'biz' ? 'Business hours' : (hours === 'night' ? 'Overnight watch' : '24/7 watch');
  }

  function themeIcon() {
    var el = document.getElementById('themeToggleIcon');
    if (!el) return;
    var effective = document.documentElement.getAttribute('data-theme');
    if (effective === 'dark') {
      el.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    } else {
      el.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
    }
  }

  // ---------------------------------------------------------------------------
  // Popovers and sheets
  // ---------------------------------------------------------------------------
  function closePopover() {
    if (shellState.popover) {
      shellState.popover.remove();
      shellState.popover = null;
    }
  }

  function openPopover(anchor, html, opts) {
    closePopover();
    var el = document.createElement('div');
    el.className = 'ura-popover';
    el.setAttribute('role', 'dialog');
    el.innerHTML = html;
    document.body.appendChild(el);
    var rect = anchor.getBoundingClientRect();
    var width = el.getBoundingClientRect().width;
    var left = Math.min(window.innerWidth - width - 12, Math.max(12, rect.right - width));
    var top = rect.bottom + 8;
    if (top + el.getBoundingClientRect().height > window.innerHeight - 12) {
      top = Math.max(12, rect.top - el.getBoundingClientRect().height - 8);
    }
    el.style.left = left + 'px';
    el.style.top = top + 'px';
    shellState.popover = el;
    setTimeout(function () {
      document.addEventListener('click', outsidePopover, true);
    }, 0);
    if (opts && opts.onMount) opts.onMount(el);
    return el;
  }

  function outsidePopover(e) {
    if (shellState.popover && !shellState.popover.contains(e.target) && !e.target.closest('[data-popover-anchor]')) {
      closePopover();
      document.removeEventListener('click', outsidePopover, true);
    }
  }

  function closeSheet() {
    if (shellState.sheet) {
      shellState.sheet.remove();
      shellState.sheet = null;
    }
    if (shellState.lastFocus && shellState.lastFocus.focus) {
      try { shellState.lastFocus.focus(); } catch (e) { /* ignore */ }
    }
  }

  function openSheet(title, bodyHtml, onMount) {
    closeSheet();
    shellState.lastFocus = document.activeElement;
    var wrap = document.createElement('div');
    wrap.className = 'ura-sheet-wrap';
    wrap.innerHTML = '<div class="ura-sheet" role="dialog" aria-modal="true" aria-label="' + h(title) + '">' +
      '<div class="ura-sheet-head"><h2>' + h(title) + '</h2>' +
      '<button type="button" class="ura-icon-btn" data-sheet-close aria-label="Close">' + icon('x') + '</button></div>' +
      '<div class="ura-sheet-body">' + bodyHtml + '</div></div>';
    document.body.appendChild(wrap);
    shellState.sheet = wrap;
    wrap.addEventListener('click', function (e) {
      if (e.target === wrap) closeSheet();
    });
    wrap.querySelector('[data-sheet-close]').onclick = closeSheet;
    wrap.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var nodes = wrap.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!nodes.length) return;
      var first = nodes[0];
      var last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    var focusable = wrap.querySelector('input, textarea, select, button:not([data-sheet-close])');
    if (focusable) setTimeout(function () { focusable.focus(); }, 30);
    if (onMount) onMount(wrap);
    return wrap;
  }

  // ---------------------------------------------------------------------------
  // Company menu
  // ---------------------------------------------------------------------------
  function openCompanyMenu(anchor) {
    var companies = [];
    try { companies = (typeof state !== 'undefined' && state.companies) || []; } catch (e) { companies = []; }
    var activeId = (typeof state !== 'undefined' && state.activeCompanyId) || '';
    var rows = companies.map(function (c) {
      var on = c.id === activeId;
      return '<button type="button" class="ura-pop-row" data-company="' + h(c.id) + '">' +
        '<span class="ura-company-avatar" style="width:28px;height:28px;flex:0 0 28px;font-size:11px;">' + h(String(c.name || 'C').charAt(0).toUpperCase()) + '</span>' +
        '<span class="rt"><b>' + h(c.name) + '</b><small>' + h(c.industry || 'Company') + '</small></span>' +
        (on ? '<span class="ura-pill good">Active</span>' : '') + '</button>';
    }).join('');

    var target = anchor || document.getElementById('companyChipBtn');
    var pop = openPopover(target,
      '<h3>Companies</h3>' +
      (rows || '<div class="ura-host-loading">No company yet. Create or connect one below.</div>') +
      '<div class="ura-pop-sep"></div>' +
      '<button type="button" class="ura-pop-row" data-company-action="new"><span class="ura-nav-icon">' + icon('plus') + '</span><span class="rt"><b>Add company</b><small>Create from a brief or connect an existing business</small></span></button>' +
      '<button type="button" class="ura-pop-row" data-company-action="all"><span class="ura-nav-icon">' + icon('building') + '</span><span class="rt"><b>See all companies</b><small>Switch context and see the portfolio</small></span></button>');

    pop.querySelectorAll('[data-company]').forEach(function (btn) {
      btn.onclick = function () {
        closePopover();
        if (typeof handleGlobalCompanyContextChange === 'function') handleGlobalCompanyContextChange(btn.getAttribute('data-company'));
      };
    });
    pop.querySelectorAll('[data-company-action]').forEach(function (btn) {
      btn.onclick = function () {
        closePopover();
        window.navigateTo(btn.getAttribute('data-company-action') === 'new' ? '/company/new' : '/companies');
      };
    });
  }

  // ---------------------------------------------------------------------------
  // Notifications
  // ---------------------------------------------------------------------------
  function readSet() {
    try { return JSON.parse(localStorage.getItem('ura.notif.read') || '[]'); } catch (e) { return []; }
  }

  function writeRead(list) {
    localStorage.setItem('ura.notif.read', JSON.stringify(list));
  }

  async function loadNotifications() {
    try {
      var data = await C.api('/api/coworker/approvals');
      var items = C.toArray(data).filter(function (a) {
        return String(a.status || 'PENDING').toUpperCase() === 'PENDING';
      }).filter(function (a) {
        return C.needsOwner({ amount: a.cost_estimate_usd, risk: a.risk_level, kind: a.kind || a.type });
      }).map(function (a) {
        return {
          id: a.approval_id || a.request_id,
          title: a.what || a.action_desc || 'Approval requested',
          why: a.why || a.reason || 'Waiting for your decision',
          risk: a.risk_level || 'LOW',
          when: a.created_at || a.requested_at
        };
      });
      shellState.notifications = C.notificationVisible('approvals') ? items : [];
    } catch (e) {
      shellState.notifications = [];
    }
    shellState.notifLoaded = true;
    updateBadge();
    updateActiveNav();
  }

  function updateBadge() {
    var badge = document.getElementById('uraBellBadge');
    if (!badge) return;
    var quiet = C.readSettings().quiet && C.isQuietHours();
    var count = shellState.notifications.length;
    var unread = shellState.notifications.filter(function (n) { return readSet().indexOf(n.id) === -1; }).length;
    if (quiet) {
      badge.style.display = 'none';
    } else {
      badge.style.display = count ? 'grid' : 'none';
      badge.textContent = String(unread || count);
    }
    var navBadge = document.querySelector('#uraNav .nav-item[data-nav="approvals"] .ura-nav-badge');
    if (navBadge) navBadge.style.display = quiet ? 'none' : '';
  }

  function openBell(anchor) {
    var items = shellState.notifications;
    var read = readSet();
    var rows = items.map(function (n) {
      return '<button type="button" class="ura-pop-row" data-notif="' + h(n.id) + '">' +
        '<span class="ura-status-dot ' + (String(n.risk).toUpperCase() === 'HIGH' || String(n.risk).toUpperCase() === 'CRITICAL' ? 'bad' : (String(n.risk).toUpperCase() === 'MEDIUM' ? 'warn' : '')) + '"></span>' +
        '<span class="rt"><b>' + h(n.title) + '</b><small>' + h(n.why) + ' · ' + h(n.when ? C.timeAgo(n.when) : '') + '</small></span>' +
        (read.indexOf(n.id) === -1 ? '<span class="ura-bell-dot" aria-label="Unread"></span>' : '') + '</button>';
    }).join('');
    var pop = openPopover(anchor,
      '<div style="display:flex;align-items:center;gap:8px;"><h3 style="flex:1;">Notifications</h3>' +
      '<button type="button" class="ura-link-btn" data-mark-read>Mark all read</button></div>' +
      (rows || '<div class="ura-host-loading">No notifications from connected services.</div>') +
      '<div class="ura-pop-sep"></div>' +
      '<button type="button" class="ura-pop-row" data-go-pop="/settings/notifications"><span class="ura-nav-icon">' + icon('settings') + '</span><span class="rt"><b>Notification settings</b><small>Choose what reaches this bell</small></span></button>');
    pop.querySelectorAll('[data-notif]').forEach(function (btn) {
      btn.onclick = function () {
        var list = readSet();
        var id = btn.getAttribute('data-notif');
        if (list.indexOf(id) === -1) list.push(id);
        writeRead(list);
        closePopover();
        window.navigateTo('/approvals');
      };
    });
    var mark = pop.querySelector('[data-mark-read]');
    if (mark) mark.onclick = function () {
      writeRead(items.map(function (n) { return n.id; }).concat(readSet()));
      updateBadge();
      closePopover();
    };
    var go = pop.querySelector('[data-go-pop]');
    if (go) go.onclick = function () { closePopover(); window.navigateTo(go.getAttribute('data-go-pop')); };
    loadNotifications();
  }

  // ---------------------------------------------------------------------------
  // CEO status
  // ---------------------------------------------------------------------------
  async function openStatus(anchor) {
    var company = activeCompany();
    var pop = openPopover(anchor, '<h3>CEO status</h3><div class="ura-host-loading">Reading live status…</div>');
    var snap = null;
    try { snap = await C.api('/api/coworker/dashboard'); } catch (e) { snap = null; }
    if (!pop || !pop.isConnected) return;
    if (!snap) {
      pop.innerHTML = '<h3>CEO status</h3><div class="ura-empty"><b>Status unavailable</b><p>The co-worker service did not answer. Nothing is being simulated.</p></div>';
      return;
    }
    var metrics = snap.metrics || {};
    var hours = C.readSettings().hours;
    pop.innerHTML = '<h3>CEO status</h3>' +
      '<div class="ura-pop-row"><span class="ura-status-dot"></span><span class="rt"><b>Watching all of ' + h(company ? company.name : 'your workspace') + '</b>' +
      '<small>' + (hours === 'biz' ? 'Business hours' : hours === 'night' ? 'Overnight watch' : '24/7 watch') + '</small></span></div>' +
      '<div class="ura-pop-sep"></div>' +
      '<div class="ura-pop-row"><span class="rt"><b>Agents running</b><small>Active co-workers</small></span><span class="ura-pill">' + h(metrics.active_coworkers_count || 0) + '</span></div>' +
      '<div class="ura-pop-row"><span class="rt"><b>Tasks</b><small>Background missions</small></span><span class="ura-pill">' + h(metrics.background_missions_count || 0) + '</span></div>' +
      '<div class="ura-pop-row"><span class="rt"><b>Fleet</b><small>Registered nodes</small></span><span class="ura-pill">' + h(metrics.fleet_nodes_count || 0) + '</span></div>' +
      (snap.killswitch_engaged ? '<div class="ura-suggest" style="margin-top:8px;">' + icon('alert-triangle') + '<span><b>Kill switch engaged.</b> Work is paused.</span></div>' : '') +
      '<div class="ura-pop-sep"></div>' +
      '<button type="button" class="ura-pop-row" data-status-go="/coworker"><span class="ura-nav-icon">' + icon('hand') + '</span><span class="rt"><b>Open Co-worker</b><small>Missions, runtime and activity</small></span></button>';
    var go = pop.querySelector('[data-status-go]');
    if (go) go.onclick = function () { closePopover(); window.navigateTo('/coworker'); };
  }

  // ---------------------------------------------------------------------------
  // Help and profile
  // ---------------------------------------------------------------------------
  function openHelp(anchor) {
    var pop = openPopover(anchor, '<h3>Help</h3>' +
      '<button type="button" class="ura-pop-row" data-help="how"><span class="ura-nav-icon">' + icon('info') + '</span><span class="rt"><b>How URA works</b><small>The CEO, departments and approval gates</small></span></button>' +
      '<button type="button" class="ura-pop-row" data-help="keys"><span class="ura-nav-icon">' + icon('terminal') + '</span><span class="rt"><b>Keyboard shortcuts</b><small>Navigate without the mouse</small></span></button>' +
      '<button type="button" class="ura-pop-row" data-help="search"><span class="ura-nav-icon">' + icon('search') + '</span><span class="rt"><b>Search</b><small>Pages, companies, actions and settings</small></span></button>' +
      '<div class="ura-pop-sep"></div>' +
      '<button type="button" class="ura-pop-row" data-help="settings"><span class="ura-nav-icon">' + icon('settings') + '</span><span class="rt"><b>Open settings</b><small>Appearance, language, security and more</small></span></button>');
    pop.querySelectorAll('[data-help]').forEach(function (btn) {
      btn.onclick = function () {
        var what = btn.getAttribute('data-help');
        closePopover();
        if (what === 'settings') { window.navigateTo('/settings'); return; }
        if (what === 'search') { openPalette(); return; }
        if (what === 'keys') {
          openSheet('Keyboard shortcuts', '<div class="ura-list">' + [
            ['Search and command palette', 'Ctrl / Cmd + K'],
            ['Close a popover or sheet', 'Esc'],
            ['Move in the palette', 'Arrow up / down'],
            ['Open the selected result', 'Enter'],
            ['Show the menu on a phone', 'Menu tab']
          ].map(function (row) {
            return '<div class="ura-row"><div class="rt"><b>' + h(row[0]) + '</b></div><span class="ura-kbd">' + h(row[1]) + '</span></div>';
          }).join('') + '</div>');
          return;
        }
        openSheet('How URA works',
          '<p style="margin:0 0 10px;color:var(--ura-fg-2);line-height:1.6;">You give URA a company. An AI CEO reads everything and delegates to department heads: COO for operations, CMO for marketing and sales, CTO for technology, CFO for finance, and CHRO for people.</p>' +
          '<p style="margin:0 0 10px;color:var(--ura-fg-2);line-height:1.6;">AI employees do task-specific work under SOPs and KRA/KPI. Agents are tools. Employees may use agents; agents never use employees.</p>' +
          '<p style="margin:0 0 10px;color:var(--ura-fg-2);line-height:1.6;">Risky, costly or company-touching work stops at an approval gate. Your autonomy and payment limit decide what reaches you.</p>' +
          '<div class="ura-head-actions"><button type="button" class="ura-btn primary" onclick="URAShell.closeSheet(); window.navigateTo(\'/ask-ceo\')">Ask the CEO</button>' +
          '<button type="button" class="ura-btn" onclick="URAShell.closeSheet(); window.navigateTo(\'/approvals\')">See approvals</button></div>');
      };
    });
  }

  function openProfile(anchor) {
    var host = null;
    try { host = (typeof state !== 'undefined' && state.host) || null; } catch (e) { host = null; }
    var current = C.readSettings().theme;
    var name = (host && host.name) || 'Owner';
    var email = (host && host.email) || 'owner@local';
    var pop = openPopover(anchor,
      '<div class="ura-pop-row"><span class="ura-avatar">' + h(name.charAt(0).toUpperCase()) + '</span><span class="rt"><b>' + h(name) + '</b><small>' + h(email) + '</small></span></div>' +
      '<div class="ura-pop-sep"></div>' +
      '<div style="padding:4px 6px 8px;"><div class="ura-eyebrow" style="margin-bottom:6px;">Theme</div>' +
      '<div class="ura-seg" role="group" aria-label="Theme">' +
        ['system', 'light', 'dark'].map(function (t) {
          return '<button type="button" class="' + (current === t ? 'is-on' : '') + '" data-theme-set="' + t + '">' + t.charAt(0).toUpperCase() + t.slice(1) + '</button>';
        }).join('') + '</div></div>' +
      '<button type="button" class="ura-pop-row" data-profile="settings"><span class="ura-nav-icon">' + icon('settings') + '</span><span class="rt"><b>Settings</b><small>Appearance, language, security and team</small></span></button>' +
      '<button type="button" class="ura-pop-row" data-profile="signout"><span class="ura-nav-icon" style="color:var(--ura-bad);">' + icon('arrow-right') + '</span><span class="rt"><b style="color:var(--ura-bad);">Sign out</b><small>End this session on this device</small></span></button>');
    pop.querySelectorAll('[data-theme-set]').forEach(function (btn) {
      btn.onclick = function () {
        if (window.URASettings) window.URASettings.set('theme', btn.getAttribute('data-theme-set'));
        closePopover();
      };
    });
    pop.querySelectorAll('[data-profile]').forEach(function (btn) {
      btn.onclick = function () {
        var what = btn.getAttribute('data-profile');
        closePopover();
        if (what === 'settings') { window.navigateTo('/settings'); return; }
        confirmSignOut();
      };
    });
  }

  function confirmSignOut() {
    openSheet('Sign out?', '<p style="margin:0 0 14px;color:var(--ura-fg-2);font-size:12.5px;">You will need to sign in again on this device. Nothing in your company is deleted.</p>' +
      '<div class="ura-head-actions"><button type="button" class="ura-btn danger" id="uraSignOutYes">Sign out</button>' +
      '<button type="button" class="ura-btn" id="uraSignOutNo">Cancel</button></div>', function (sheet) {
        sheet.querySelector('#uraSignOutNo').onclick = closeSheet;
        sheet.querySelector('#uraSignOutYes').onclick = function () {
          closeSheet();
          if (typeof clearSession === 'function') clearSession();
          if (typeof renderApp === 'function') renderApp();
          C.toast('Signed out', 'info');
        };
      });
  }

  // ---------------------------------------------------------------------------
  // Command palette
  // ---------------------------------------------------------------------------
  function paletteItems() {
    var items = [];
    var screens = (window.URAScreens && window.URAScreens.NAV) || [];
    var hidden = C.readSettings().hidden || [];
    screens.forEach(function (s) {
      if (s.id !== 'overview' && hidden.indexOf(s.id) !== -1) return;
      if (s.id === 'terminal' && C.readSettings().terminalOn === false) return;
      items.push({ group: 'Screens', label: navLabel(s), detail: s.group, icon: s.icon, run: function () { window.navigateTo(s.route); } });
    });
    items.push({ group: 'Screens', label: 'Settings', detail: 'System', icon: 'settings', run: function () { window.navigateTo('/settings'); } });

    var companies = [];
    try { companies = (typeof state !== 'undefined' && state.companies) || []; } catch (e) { companies = []; }
    companies.forEach(function (c) {
      items.push({ group: 'Companies', label: c.name, detail: c.industry || 'Company', icon: 'building', run: function () {
        if (typeof handleGlobalCompanyContextChange === 'function') handleGlobalCompanyContextChange(c.id);
        window.navigateTo('/overview');
      } });
    });

    items.push({ group: 'Actions', label: 'Ask the CEO', detail: 'Open the chat', icon: 'crown', run: function () { window.navigateTo('/ask-ceo'); } });
    items.push({ group: 'Actions', label: 'Delegate a task', detail: 'Create a CEO mission', icon: 'plus', run: function () { window.URAScreens.openDelegateSheet(); } });
    items.push({ group: 'Actions', label: 'Create a company', detail: 'New company flow', icon: 'plus', run: function () { window.navigateTo('/company/new'); } });
    items.push({ group: 'Actions', label: 'Run a security scan', detail: 'Refresh security posture', icon: 'shield', run: function () { window.navigateTo('/security'); } });

    (window.URASettings ? window.URASettings.CATS : []).forEach(function (cat) {
      items.push({ group: 'Settings', label: cat.name, detail: cat.blurb, icon: cat.icon, run: function () { window.navigateTo('/settings/' + cat.id); } });
    });

    [['Records', '/records'], ['Files & documents', '/files'], ['Activity', '/activity'], ['Artifacts', '/artifacts'],
      ['Workflows', '/workflows'], ['TaskMaker', '/tasks'], ['Meeting room', '/meeting'], ['Organization', '/organization'],
      ['Governance', '/governance'], ['Plugins', '/plugins'], ['Agent network', '/agent-network'], ['MCP network', '/mcp-network'],
      ['OpenHands execution', '/openhands-execution'], ['Browser execution', '/browser-execution'], ['Durable temporal', '/temporal-durable'],
      ['Nango integrations', '/nango-integrations'], ['Processes', '/processes'], ['TrustGraph', '/trustgraph'], ['Design preview', '/design']
    ].forEach(function (row) {
      items.push({ group: 'More screens', label: row[0], detail: 'Legacy workspace', icon: 'layers', run: function () { window.navigateTo(row[1]); } });
    });

    return items;
  }

  function openPalette() {
    if (shellState.paletteOpen) return;
    closePopover();
    shellState.paletteOpen = true;
    shellState.paletteIndex = 0;
    shellState.paletteItems = paletteItems();
    var wrap = document.createElement('div');
    wrap.className = 'ura-palette-wrap';
    wrap.innerHTML = '<div class="ura-palette" role="dialog" aria-modal="true" aria-label="Search and commands">' +
      '<div class="ura-palette-input-wrap">' + icon('search', 17) +
      '<input class="ura-palette-input" id="uraPaletteInput" placeholder="' + h(C.t('action.search')) + '" aria-label="Search pages, companies, actions and settings" autocomplete="off">' +
      '<span class="ura-kbd">Esc</span></div><div class="ura-palette-list" id="uraPaletteList"></div></div>';
    document.body.appendChild(wrap);
    shellState.paletteWrap = wrap;
    var input = wrap.querySelector('#uraPaletteInput');
    paintPalette('');
    input.focus();
    input.addEventListener('input', function () { paintPalette(input.value); });
    wrap.addEventListener('click', function (e) { if (e.target === wrap) closePalette(); });
    document.addEventListener('keydown', paletteKeys);
  }

  function closePalette() {
    if (shellState.paletteWrap) {
      shellState.paletteWrap.remove();
      shellState.paletteWrap = null;
    }
    shellState.paletteOpen = false;
    document.removeEventListener('keydown', paletteKeys);
  }

  function paintPalette(query) {
    var list = document.getElementById('uraPaletteList');
    if (!list) return;
    var q = String(query || '').toLowerCase().trim();
    var items = shellState.paletteItems.filter(function (item) {
      return !q || (item.label + ' ' + item.detail + ' ' + item.group).toLowerCase().indexOf(q) !== -1;
    });
    if (shellState.paletteIndex >= items.length) shellState.paletteIndex = 0;
    if (!items.length) {
      list.innerHTML = '<div class="ura-palette-empty">No match for "' + h(query) + '".</div>';
      return;
    }
    var groups = [];
    items.forEach(function (item) { if (groups.indexOf(item.group) === -1) groups.push(item.group); });
    list.innerHTML = groups.map(function (group) {
      var groupItems = items.filter(function (i) { return i.group === group; });
      return '<div class="ura-palette-group">' + h(group) + '</div>' + groupItems.map(function (item) {
        var index = items.indexOf(item);
        return '<button type="button" class="ura-palette-item ' + (index === shellState.paletteIndex ? 'is-active' : '') + '" data-pal="' + index + '">' +
          '<span class="ura-nav-icon">' + (window.Icon ? window.Icon({ name: item.icon, size: 17, tone: 'default' }) : '') + '</span>' +
          '<span class="rt"><b>' + h(item.label) + '</b><small>' + h(item.detail) + '</small></span></button>';
      }).join('');
    }).join('');
    list.querySelectorAll('[data-pal]').forEach(function (btn) {
      btn.onclick = function () {
        var item = items[Number(btn.getAttribute('data-pal'))];
        closePalette();
        if (item) item.run();
      };
    });
  }

  function paletteKeys(e) {
    if (!shellState.paletteOpen) return;
    var input = document.getElementById('uraPaletteInput');
    var q = input ? input.value : '';
    var visible = shellState.paletteItems.filter(function (item) {
      return !q || (item.label + ' ' + item.detail + ' ' + item.group).toLowerCase().indexOf(q.toLowerCase()) !== -1;
    });
    if (e.key === 'Escape') { e.preventDefault(); closePalette(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      shellState.paletteIndex = Math.min(visible.length - 1, shellState.paletteIndex + 1);
      paintPalette(q);
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      shellState.paletteIndex = Math.max(0, shellState.paletteIndex - 1);
      paintPalette(q);
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      var item = visible[shellState.paletteIndex];
      closePalette();
      if (item) item.run();
    }
  }

  // ---------------------------------------------------------------------------
  // Drawer and rail
  // ---------------------------------------------------------------------------
  function toggleDrawer(force) {
    var sidebar = document.getElementById('appSidebar');
    var backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar) return;
    var open = typeof force === 'boolean' ? force : !sidebar.classList.contains('drawer-open');
    sidebar.classList.toggle('drawer-open', open);
    if (backdrop) backdrop.classList.toggle('active', open);
  }

  function closeDrawer() { toggleDrawer(false); }

  function toggleRail() {
    var s = C.readSettings();
    C.saveSettings({ sidebar: s.sidebar === 'rail' ? 'full' : 'rail' });
    if (window.URASettings) window.URASettings.apply();
  }

  // ---------------------------------------------------------------------------
  // Toasts
  // ---------------------------------------------------------------------------
  function toast(message, kind) {
    var host = document.getElementById('toastContainer');
    if (!host) return;
    var el = document.createElement('div');
    el.className = 'ura-toast' + (kind === 'error' ? ' error' : '');
    el.setAttribute('role', 'status');
    el.textContent = message;
    host.appendChild(el);
    setTimeout(function () {
      el.style.opacity = '0';
      el.style.transform = 'translateY(4px)';
      setTimeout(function () { el.remove(); }, 200);
    }, 3600);
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------
  function onSettingsApplied() {
    renderNav();
    updateActiveNav();
    refreshStatusPill();
    refreshClock();
    themeIcon();
    updateBadge();
  }

  function init() {
    renderNav();
    renderTabbar();
    refreshCompanyChip();
    refreshClock();
    refreshStatusPill();
    themeIcon();
    setBreadcrumbs('Overview', '');
    loadNotifications();
    setInterval(refreshClock, 30000);
    setInterval(loadNotifications, 60000);

    var chip = document.getElementById('companyChipBtn');
    if (chip) chip.addEventListener('click', function (e) {
      e.preventDefault();
      // One switcher for the whole app: the company setup switcher owns
      // listing, selecting and adding companies. The local menu is only a
      // fallback when that layer has not loaded.
      if (window.CompanySetupSwitcher && typeof window.CompanySetupSwitcher.open === 'function') {
        window.CompanySetupSwitcher.open();
        return;
      }
      openCompanyMenu(chip);
    });

    var menu = document.getElementById('menuToggleBtn');
    if (menu) menu.addEventListener('click', function (e) { e.preventDefault(); toggleDrawer(); });

    var rail = document.getElementById('railToggleBtn');
    if (rail) rail.addEventListener('click', function (e) { e.preventDefault(); toggleRail(); });

    var search = document.getElementById('uraSearchBtn');
    if (search) search.addEventListener('click', function (e) { e.preventDefault(); openPalette(); });

    var status = document.getElementById('uraStatusPill');
    if (status) status.addEventListener('click', function (e) { e.preventDefault(); openStatus(status); });

    var bell = document.getElementById('uraBellBtn');
    if (bell) bell.addEventListener('click', function (e) { e.preventDefault(); openBell(bell); });

    var help = document.getElementById('uraHelpBtn');
    if (help) help.addEventListener('click', function (e) { e.preventDefault(); openHelp(help); });

    var profile = document.getElementById('uraProfileBtn');
    if (profile) profile.addEventListener('click', function (e) { e.preventDefault(); openProfile(profile); });

    document.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openPalette();
        return;
      }
      if (e.key === 'Escape') {
        closePopover();
        closeSheet();
      }
    });

    var backdrop = document.getElementById('sidebarBackdrop');
    if (backdrop) backdrop.addEventListener('click', closeDrawer);
  }

  // The shell markup is already in the DOM when this script runs at the end of
  // the body. Build the dynamic parts immediately so app.js binds to them.
  init();

  window.URAShell = {
    init: init,
    renderNav: renderNav,
    setBreadcrumbs: setBreadcrumbs,
    updateActiveNav: updateActiveNav,
    updateTabbar: updateTabbar,
    onSettingsApplied: onSettingsApplied,
    refreshCompanyChip: refreshCompanyChip,
    toggleDrawer: toggleDrawer,
    closeDrawer: closeDrawer,
    toggleRail: toggleRail,
    openCompanyMenu: openCompanyMenu,
    openPopover: openPopover,
    closePopover: closePopover,
    openSheet: openSheet,
    closeSheet: closeSheet,
    openPalette: openPalette,
    closePalette: closePalette,
    openHelp: openHelp,
    openProfile: openProfile,
    toast: toast,
    loadNotifications: loadNotifications
  };
})();
