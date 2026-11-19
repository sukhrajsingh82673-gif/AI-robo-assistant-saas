/* ==========================================================================
   URA Settings — one registry, one renderer, every suggestion is real.
   Classic browser script: exposes window.URASettings.
   ========================================================================== */
(function () {
  'use strict';

  var C = window.URACore;
  if (!C) return;

  var AC = window.AppRouter;

  var ACCENTS = [
    ['blue', '#0071e3'], ['indigo', '#5856d6'], ['purple', '#9d3fc4'],
    ['pink', '#d6246e'], ['orange', '#b85400'], ['green', '#1a7f37'],
    ['graphite', '#48484d']
  ];

  var CATS = [
    { id: 'appearance', icon: 'sun', name: 'Appearance', blurb: 'Theme, colour, size, motion and contrast.' },
    { id: 'language', icon: 'globe', name: 'Language and region', blurb: 'Language, time zone, dates, numbers and currency.' },
    { id: 'ceo', icon: 'crown', name: 'AI CEO and autonomy', blurb: 'How much the CEO decides alone and how it answers.' },
    { id: 'notifications', icon: 'bell', name: 'Notifications', blurb: 'What reaches the bell and the red badge.' },
    { id: 'reports', icon: 'file-text', name: 'Reports', blurb: 'How often reports arrive and what they contain.' },
    { id: 'security', icon: 'shield', name: 'Security and privacy', blurb: 'Sign-in, sessions, audit retention and data region.' },
    { id: 'menu', icon: 'sliders', name: 'Menu and team', blurb: 'Hide screens and manage who has access.' }
  ];

  function deviceLang() {
    var lang = String(navigator.language || 'en').slice(0, 2).toLowerCase();
    return C.LANGS.some(function (l) { return l[0] === lang; }) ? lang : 'en';
  }

  function ctx() {
    var company = C.activeCompany();
    var companies = [];
    try { companies = (typeof state !== 'undefined' && state.companies) || []; } catch (e) { companies = []; }
    var countries = {};
    companies.forEach(function (c) { if (c && c.country) countries[c.country] = true; });
    return {
      company: company,
      companies: companies,
      deviceLang: deviceLang(),
      osReduce: !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches),
      osDark: !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches),
      manyCompanies: companies.length > 3,
      spansCountries: Object.keys(countries).length > 1,
      companyLang: (company && company.language) || null,
      companyRegion: (company && (company.region || company.country)) || null
    };
  }

  function s(v, why) { return { value: v, why: why }; }

  // ---------------------------------------------------------------------------
  // Registry. Every item is rendered by the same generic renderer.
  // ---------------------------------------------------------------------------
  var SET = [
    // Appearance
    { key: 'theme', cat: 'appearance', label: 'Theme', hint: 'Light, dark or the same as your device.', type: 'seg',
      options: [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']],
      suggest: function () { return s('system', 'Following your device keeps the app comfortable day and night.'); } },
    { key: 'accent', cat: 'appearance', label: 'Accent colour', hint: 'The one colour used for actions and selected items.', type: 'swatch',
      options: ACCENTS, suggest: function () { return s('blue', 'Blue is the calm default and stays readable in both themes.'); } },
    { key: 'density', cat: 'appearance', label: 'Density', hint: 'Comfortable spacing or a tighter view for long lists.', type: 'seg',
      options: [['comfortable', 'Comfortable'], ['compact', 'Compact']],
      suggest: function (c) {
        return s('comfortable', c.manyCompanies
          ? 'You manage many companies, so Compact shows more rows at once.'
          : 'Comfortable is easiest to read when you are new.');
      } },
    { key: 'sidebar', cat: 'appearance', label: 'Sidebar', hint: 'Show the full menu or just the icons.', type: 'seg',
      options: [['full', 'Full'], ['rail', 'Icons only']],
      suggest: function () { return s('full', 'New users find screens faster with the labels visible.'); } },
    { key: 'textSize', cat: 'appearance', label: 'Text size', hint: 'Scales every screen without breaking the layout.', type: 'seg',
      options: [['90', '90%'], ['100', '100%'], ['115', '115%'], ['130', '130%']],
      suggest: function () { return s('100', '100% matches your device default.'); } },
    { key: 'reduceMotion', cat: 'appearance', label: 'Reduce motion', hint: 'Turns off animation except the live status dot.', type: 'switch',
      suggest: function (c) { return s(c.osReduce, c.osReduce ? 'Your device already asks apps to reduce motion.' : 'Motion is short and only answers your actions.'); } },
    { key: 'contrast', cat: 'appearance', label: 'Higher contrast', hint: 'Stronger borders and darker secondary text.', type: 'switch',
      suggest: function () { return s(false, 'The default palette already meets 4.5:1 contrast.'); } },

    // Language and region
    { key: 'lang', cat: 'language', label: 'Language', hint: 'Menus, page titles and common buttons.', type: 'select',
      options: C.LANGS.map(function (l) { return [l[0], l[1]]; }),
      suggest: function (c) {
        var proposed = c.companyLang || c.deviceLang;
        var why = c.companyLang ? 'Your active company works in this language.' : 'This matches your device language.';
        return s(proposed, why);
      } },
    { key: 'tz', cat: 'language', label: 'Time zone', hint: 'Used for the company clock, reports and quiet hours.', type: 'select',
      options: [['auto', 'Automatic']].concat(C.TZS.map(function (z) { return [z, z]; })),
      suggest: function (c) {
        var proposed = (c.company && c.company.timezone) || 'auto';
        return s(proposed, proposed === 'auto' ? 'Automatic follows your device.' : 'This is your active company time zone.');
      } },
    { key: 'hour', cat: 'language', label: 'Clock', hint: '12-hour or 24-hour time.', type: 'seg',
      options: [['auto', 'Automatic'], ['12', '12-hour'], ['24', '24-hour']],
      suggest: function () { return s('auto', 'Automatic follows your language and device.'); } },
    { key: 'dateFmt', cat: 'language', label: 'Date style', hint: 'Day first, month first or year first.', type: 'seg',
      options: [['auto', 'Automatic'], ['dmy', 'Day first'], ['mdy', 'Month first'], ['iso', 'Year first']],
      suggest: function (c) { return s(c.spansCountries ? 'iso' : 'auto', c.spansCountries ? 'Year first is unambiguous across countries.' : 'Automatic follows your language.'); } },
    { key: 'numFmt', cat: 'language', label: 'Number style', hint: 'Grouping and decimal marks for amounts.', type: 'select',
      options: [['auto', 'Automatic'], ['en-US', '1,234.56'], ['en-IN', '1,23,456.78'], ['de-DE', '1.234,56'], ['fr-FR', '1 234,56']],
      suggest: function () { return s('auto', 'Automatic follows your language and company country.'); } },
    { key: 'currency', cat: 'language', label: 'Display currency', hint: 'Amounts keep their real source value until a rate source is connected.', type: 'select',
      options: [['company', 'Each company\'s own currency'], ['USD', 'US dollar'], ['INR', 'Indian rupee'], ['EUR', 'Euro'], ['GBP', 'Pound sterling'], ['AED', 'UAE dirham'], ['JPY', 'Japanese yen']],
      suggest: function () { return s('company', 'Each company shows its own currency, which avoids wrong conversions.'); } },

    // AI CEO and autonomy
    { key: 'autonomy', cat: 'ceo', label: 'Autonomy', hint: 'What the CEO may do without asking you.', type: 'seg',
      options: [['ask', 'Ask me first'], ['balanced', 'Balanced'], ['auto', 'Mostly autonomous']],
      suggest: function () { return s('balanced', 'Balanced lets routine work run and asks you for risky or costly decisions.'); } },
    { key: 'payLimit', cat: 'ceo', label: 'Payment limit', hint: 'Anything above this always needs your approval.', type: 'select',
      options: [['0', 'No spend without me'], ['250', 'Up to $250'], ['1000', 'Up to $1,000'], ['5000', 'Up to $5,000'], ['25000', 'Up to $25,000']],
      suggest: function () { return s('1000', '$1,000 covers routine tools while keeping large spend under your control.'); } },
    { key: 'hours', cat: 'ceo', label: 'Working hours', hint: 'Shown in the CEO status pill.', type: 'seg',
      options: [['247', '24/7'], ['biz', 'Business hours'], ['night', 'Overnight']],
      suggest: function () { return s('247', 'Your CEO can keep watching while your team sleeps.'); } },
    { key: 'tone', cat: 'ceo', label: 'How the CEO answers', hint: 'Brief answers or the full detail.', type: 'seg',
      options: [['brief', 'Brief'], ['detailed', 'Detailed']],
      suggest: function () { return s('brief', 'Brief answers make the decision faster; ask for detail when you need it.'); } },

    // Notifications
    { key: 'n_approvals', cat: 'notifications', label: 'Approvals', hint: 'When something waits for your decision.', type: 'switch',
      suggest: function () { return s(true, 'Approvals are the one thing only you can clear.'); } },
    { key: 'n_security', cat: 'notifications', label: 'Security', hint: 'High-risk findings and blocked actions.', type: 'switch',
      suggest: function () { return s(true, 'Security warnings are worth seeing immediately.'); } },
    { key: 'n_reports', cat: 'notifications', label: 'Reports', hint: 'When a scheduled report is ready.', type: 'switch',
      suggest: function () { return s(true, 'Reports are sent on the schedule you choose.'); } },
    { key: 'n_builds', cat: 'notifications', label: 'Builds', hint: 'Company build progress and finished steps.', type: 'switch',
      suggest: function () { return s(true, 'Build updates tell you when a company is ready to operate.'); } },
    { key: 'quiet', cat: 'notifications', label: 'Quiet hours', hint: 'Hides the red badge from 22:00 to 07:00. Items still wait in the bell.', type: 'switch',
      suggest: function (c) { return s(c.spansCountries, c.spansCountries ? 'Your companies span time zones, so quiet hours protect your night.' : 'Your companies share a time zone, so a badge is useful around the clock.'); } },

    // Reports
    { key: 'repFreq', cat: 'reports', label: 'Frequency', hint: 'How often the owner report is prepared.', type: 'seg',
      options: [['daily', 'Daily'], ['weekly', 'Weekly'], ['monthly', 'Monthly']],
      suggest: function () { return s('weekly', 'Weekly is enough to see profit move without inbox noise.'); } },
    { key: 'repEmail', cat: 'reports', label: 'Send to', hint: 'The address that receives the report.', type: 'email',
      suggest: function () {
        var email = '';
        try { email = (typeof state !== 'undefined' && state.host && state.host.email) || ''; } catch (e) { email = ''; }
        return s(email, 'Your signed-in owner address is the safest recipient.');
      } },
    { key: 'repProfit', cat: 'reports', label: 'Include profit', hint: 'Revenue, costs and net profit.', type: 'switch',
      suggest: function () { return s(true, 'Profit is the main reason to read the report.'); } },
    { key: 'repSales', cat: 'reports', label: 'Include sales', hint: 'Leads, pipeline and wins.', type: 'switch',
      suggest: function () { return s(true, 'Sales explains where next month\'s profit comes from.'); } },
    { key: 'repSec', cat: 'reports', label: 'Include security', hint: 'Score, findings and blocked actions.', type: 'switch',
      suggest: function () { return s(false, 'Security detail belongs in its own screen unless you must forward it.'); } },

    // Security and privacy
    // Two-step is not a local preference: it is a real authenticator enrollment
    // managed by the server. It is shown on the Security screen and set up in
    // the deletion sheet, so there is no local switch here that could claim it.
    { key: 'session', cat: 'security', label: 'Stay signed in', hint: 'How long a session lasts before it asks again.', type: 'seg',
      options: [['15m', '15 min'], ['1h', '1 hour'], ['8h', '8 hours'], ['never', 'Until I sign out']],
      suggest: function () { return s('1h', 'One hour balances safety with not interrupting your work.'); } },
    { key: 'audit', cat: 'security', label: 'Keep audit history', hint: 'How long decisions and actions are kept.', type: 'seg',
      options: [['30', '30 days'], ['90', '90 days'], ['365', '1 year']],
      suggest: function () { return s('365', 'A year covers annual reviews and disputes.'); } },
    { key: 'region', cat: 'security', label: 'Data region', hint: 'Where company data should be stored.', type: 'select',
      options: Object.keys(C.REGIONS).map(function (k) { return [k, C.REGIONS[k]]; }),
      suggest: function (c) { return s(c.companyRegion || 'in', 'Keeping data in the company region is the simplest policy to explain.'); } },
    { key: 'terminalOn', cat: 'security', label: 'Show the Terminal', hint: 'The Terminal disappears from the menu and search when off.', type: 'switch',
      suggest: function () { return s(true, 'The Terminal is how agents install tools, so keep it on unless policy forbids it.'); } }
  ];

  var BY_KEY = {};
  SET.forEach(function (item) { BY_KEY[item.key] = item; });

  function suggestions() {
    var c = ctx();
    var out = {};
    SET.forEach(function (item) {
      try {
        var res = item.suggest(c);
        out[item.key] = { value: String(res.value), why: res.why };
      } catch (e) {
        out[item.key] = { value: String(C.DEFAULTS[item.key]), why: 'Default value.' };
      }
    });
    return out;
  }

  function get(key) { return C.readSettings()[key]; }

  function set(key, value) {
    var patch = {};
    patch[key] = value;
    C.saveSettings(patch);
    apply();
    document.dispatchEvent(new CustomEvent('ura:settings', { detail: { key: key, value: value } }));
  }

  function apply() {
    var s = C.readSettings();
    var root = document.documentElement;
    var effective = s.theme;
    if (s.theme === 'system') {
      effective = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    }
    root.setAttribute('data-theme', effective);
    root.setAttribute('data-accent', s.accent);
    root.setAttribute('data-density', s.density);
    root.setAttribute('data-contrast', s.contrast ? 'high' : 'normal');
    root.setAttribute('data-motion', s.reduceMotion ? 'reduce' : 'full');
    root.style.setProperty('--ura-text-scale', String(Number(s.textSize) / 100 || 1));
    root.setAttribute('lang', s.lang);
    root.setAttribute('dir', s.lang === 'ar' ? 'rtl' : 'ltr');
    localStorage.setItem('zonata_theme_preference', s.theme === 'system' ? 'auto' : s.theme);
    var sidebar = document.getElementById('appSidebar');
    if (sidebar) sidebar.classList.toggle('rail', s.sidebar === 'rail');
    if (window.URAShell && window.URAShell.onSettingsApplied) window.URAShell.onSettingsApplied();
  }

  function cycleTheme() {
    var order = ['system', 'light', 'dark'];
    var current = C.readSettings().theme;
    var next = order[(order.indexOf(current) + 1) % order.length];
    set('theme', next);
    C.toast('Theme: ' + next.charAt(0).toUpperCase() + next.slice(1), 'info');
  }

  function useSuggestions(catId) {
    var all = suggestions();
    var keys = SET.filter(function (item) { return !catId || item.cat === catId; }).map(function (item) { return item.key; });
    var patch = {};
    keys.forEach(function (key) { if (all[key]) patch[key] = all[key].value; });
    C.saveSettings(patch);
    apply();
    document.dispatchEvent(new CustomEvent('ura:settings', { detail: { all: keys } }));
    C.toast(keys.length + ' suggestion' + (keys.length === 1 ? '' : 's') + ' applied', 'success');
  }

  function allApplied(catId) {
    var all = suggestions();
    var current = C.readSettings();
    return SET.filter(function (item) { return !catId || item.cat === catId; }).every(function (item) {
      return String(current[item.key]) === String(all[item.key].value);
    });
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------
  function esc(v) { return C.escapeHtml(v); }

  function control(item, value, sug) {
    var isSuggested = String(value) === String(sug.value);
    if (item.type === 'seg') {
      return '<div class="ura-seg" role="group" aria-label="' + esc(item.label) + '">' +
        item.options.map(function (opt) {
          var on = String(value) === String(opt[0]);
          var dot = String(sug.value) === String(opt[0]) ? '<span class="ura-sug-dot" aria-hidden="true"></span>' : '';
          return '<button type="button" class="' + (on ? 'is-on' : '') + '" aria-pressed="' + on + '" data-set="' + esc(item.key) + '" data-value="' + esc(opt[0]) + '">' +
            esc(opt[1]) + dot + '</button>';
        }).join('') + '</div>';
    }
    if (item.type === 'switch') {
      var checked = value === true || value === 'true';
      return '<button type="button" class="ura-switch" role="switch" aria-checked="' + checked + '" aria-label="' + esc(item.label) + '" data-toggle="' + esc(item.key) + '"></button>';
    }
    if (item.type === 'swatch') {
      return '<div class="ura-swatch-row" role="group" aria-label="' + esc(item.label) + '">' +
        item.options.map(function (opt) {
          return '<button type="button" class="ura-swatch' + (String(value) === opt[0] ? ' is-on' : '') + '" style="background:' + opt[1] + '" aria-label="' + esc(opt[0]) + '" aria-pressed="' + (String(value) === opt[0]) + '" data-set="' + esc(item.key) + '" data-value="' + opt[0] + '"></button>';
        }).join('') + '</div>';
    }
    if (item.type === 'email') {
      return '<input class="ura-input" type="email" value="' + esc(value || '') + '" aria-label="' + esc(item.label) + '" data-email="' + esc(item.key) + '" style="max-width:280px;">';
    }
    return '<select class="ura-select" aria-label="' + esc(item.label) + '" data-select="' + esc(item.key) + '">' +
      item.options.map(function (opt) {
        return '<option value="' + esc(opt[0]) + '"' + (String(value) === String(opt[0]) ? ' selected' : '') + '>' + esc(opt[1]) + '</option>';
      }).join('') + '</select>';
  }

  function suggestionBox(item, value, sug) {
    var match = String(value) === String(sug.value);
    if (match) {
      return '<div class="ura-suggest ok">' + icon('check-circle') + '<span><b>Matches our suggestion.</b> ' + esc(sug.why) + '</span></div>';
    }
    return '<div class="ura-suggest">' + icon('sparkles') + '<span><b>Suggested: ' + esc(sug.value) + '.</b> ' + esc(sug.why) +
      ' <button type="button" class="ura-link-btn" data-set="' + esc(item.key) + '" data-value="' + esc(sug.value) + '">Use this</button></span></div>';
  }

  function icon(name) {
    return window.Icon ? window.Icon({ name: name, size: 16, tone: 'accent' }) : '';
  }

  function renderHub(container) {
    var counts = {};
    SET.forEach(function (item) { counts[item.cat] = (counts[item.cat] || 0) + 1; });
    container.innerHTML =
      '<div class="ura-page-head">' +
        '<div><div class="ura-eyebrow">Workspace</div><h1 class="ura-title">Settings</h1>' +
        '<p class="ura-subtitle">Every setting explains itself and shows the value we recommend.</p></div>' +
        '<div class="ura-head-actions"><button class="ura-btn" type="button" data-use-all="all">' + icon('sparkles') + 'Use all suggestions</button></div>' +
      '</div>' +
      '<div class="ura-settings-layout"><div class="ura-settings-nav" role="tablist">' +
        CATS.map(function (cat) {
          return '<button type="button" data-settings-cat="' + cat.id + '">' +
            (window.Icon ? window.Icon({ name: cat.icon, size: 17, tone: 'accent' }) : '') +
            '<span><b>' + esc(cat.name) + '</b><small>' + counts[cat.id] + ' settings</small></span></button>';
        }).join('') +
      '</div><div class="ura-settings-body"><div class="ura-card">' +
        '<h2 style="margin:0 0 4px;font-size:1rem;">Start here</h2>' +
        '<p style="margin:0 0 12px;color:var(--ura-fg-2);font-size:12.5px;">New here? Read the blue tip under each setting. It explains the change in plain words and offers the value we recommend.</p>' +
        '<div class="ura-grid k2">' +
          CATS.map(function (cat) {
            return '<button type="button" class="ura-row" style="border:0;background:transparent;text-align:start;width:100%;padding:10px 2px;" data-settings-cat="' + cat.id + '">' +
              '<span class="ura-nav-icon">' + (window.Icon ? window.Icon({ name: cat.icon, size: 18, tone: 'accent' }) : '') + '</span>' +
              '<span class="rt"><b>' + esc(cat.name) + '</b><small>' + esc(cat.blurb) + '</small></span>' +
              '<span class="ura-nav-icon">' + (window.Icon ? window.Icon({ name: 'chevron-right', size: 16, tone: 'muted' }) : '') + '</span></button>';
          }).join('') +
        '</div></div></div></div>';
  }

  function renderCategory(container, catId) {
    var cat = CATS.filter(function (c) { return c.id === catId; })[0];
    if (!cat) { renderHub(container); return; }
    if (catId === 'menu') { renderMenu(container, cat); return; }

    var current = C.readSettings();
    var sug = suggestions();
    var items = SET.filter(function (item) { return item.cat === catId; });
    var done = allApplied(catId);

    container.innerHTML =
      '<div class="ura-page-head">' +
        '<div><button type="button" class="ura-btn plain small" data-settings-cat="">' + (window.Icon ? window.Icon({ name: 'chevron-left', size: 15, tone: 'muted' }) : '') + 'Settings</button>' +
        '<h1 class="ura-title" style="margin-top:6px;">' + esc(cat.name) + '</h1>' +
        '<p class="ura-subtitle">' + esc(cat.blurb) + '</p></div>' +
        '<div class="ura-head-actions"><button class="ura-btn' + (done ? '' : ' primary') + '" type="button" data-use-all="' + catId + '"' + (done ? ' disabled' : '') + '>' +
        icon('sparkles') + (done ? 'All suggestions applied' : 'Use all ' + items.length + ' suggestions') + '</button></div>' +
      '</div>' +
      '<div class="ura-card">' + items.map(function (item) {
        var value = current[item.key];
        var itemSug = sug[item.key];
        return '<div class="ura-setting-row"><div class="sl"><b>' + esc(item.label) + '</b><div class="sh">' + esc(item.hint) + '</div>' +
          suggestionBox(item, value, itemSug) + '</div><div class="sc">' + control(item, value, itemSug) + '</div></div>';
      }).join('') + '</div>';
  }

  function renderMenu(container, cat) {
    var current = C.readSettings();
    var hidden = Array.isArray(current.hidden) ? current.hidden : [];
    var screens = (window.URAScreens && window.URAScreens.NAV) ? window.URAScreens.NAV : [];
    var rows = screens.filter(function (item) { return item.id !== 'overview' && item.id !== 'settings'; }).map(function (item) {
      var visible = hidden.indexOf(item.id) === -1;
      return '<div class="ura-setting-row"><div class="sl"><b>' + esc(item.label) + '</b><div class="sh">' + esc(item.group) + ' screen</div></div>' +
        '<div class="sc"><button type="button" class="ura-switch" role="switch" aria-checked="' + visible + '" aria-label="Show ' + esc(item.label) + '" data-menu="' + esc(item.id) + '"></button></div></div>';
    }).join('');

    var host = null;
    try { host = (typeof state !== 'undefined' && state.host) || null; } catch (e) { host = null; }

    container.innerHTML =
      '<div class="ura-page-head"><div><button type="button" class="ura-btn plain small" data-settings-cat="">' +
        (window.Icon ? window.Icon({ name: 'chevron-left', size: 15, tone: 'muted' }) : '') + 'Settings</button>' +
        '<h1 class="ura-title" style="margin-top:6px;">' + esc(cat.name) + '</h1>' +
        '<p class="ura-subtitle">' + esc(cat.blurb) + '</p></div></div>' +
      '<div class="ura-grid k2" style="align-items:start;">' +
        '<div class="ura-card"><h2 style="margin:0 0 6px;font-size:1rem;">Screens</h2>' +
          '<p style="margin:0 0 8px;color:var(--ura-fg-2);font-size:12.5px;">Overview and Settings always stay visible. Hidden screens remain reachable by link and show a card that can restore them.</p>' +
          rows + '</div>' +
        '<div class="ura-card"><h2 style="margin:0 0 6px;font-size:1rem;">Team</h2>' +
          '<p style="margin:0 0 12px;color:var(--ura-fg-2);font-size:12.5px;">This workspace has one owner account. Team invitations need the team service, which is not connected in this build.</p>' +
          '<div class="ura-row"><div class="ura-avatar">' + esc((host && host.name ? host.name : 'O').charAt(0).toUpperCase()) + '</div>' +
            '<div class="rt"><b>' + esc((host && host.name) || 'Owner') + '</b><small>' + esc((host && host.email) || 'owner@local') + ' · Owner</small></div>' +
            '<span class="ura-pill good">Active</span></div>' +
          '<div class="ura-empty" style="margin-top:14px;"><b>Team invites are not connected</b><p>When the team service is enabled, you will invite people here and choose Owner, Admin, Member or Viewer.</p>' +
          '<button type="button" class="ura-btn" data-team-info="1">What will this do?</button></div>' +
        '</div>' +
      '</div>';
  }

  function render(container, sub) {
    if (!container) return;
    var parts = String(sub || '').split('/').filter(Boolean);
    var catId = parts[0] || '';
    if (!catId) renderHub(container);
    else renderCategory(container, catId);
  }

  // ---------------------------------------------------------------------------
  // One delegated listener for every settings control.
  // ---------------------------------------------------------------------------
  function bind(container) {
    if (!container || container.getAttribute('data-ura-settings-bound') === '1') return;
    container.setAttribute('data-ura-settings-bound', '1');
    container.addEventListener('click', function (e) {
      var nav = e.target.closest('[data-settings-cat]');
      if (nav) {
        var cat = nav.getAttribute('data-settings-cat');
        window.navigateTo(cat ? '/settings/' + cat : '/settings');
        return;
      }
      var useAll = e.target.closest('[data-use-all]');
      if (useAll) {
        var scope = useAll.getAttribute('data-use-all');
        useSuggestions(scope === 'all' ? '' : scope);
        render(container, scope === 'all' ? '' : scope);
        return;
      }
      var seg = e.target.closest('[data-set]');
      if (seg && !seg.classList.contains('ura-swatch')) {
        set(seg.getAttribute('data-set'), seg.getAttribute('data-value'));
        render(container, (window.URAScreens && window.URAScreens.settingsCategory()) || '');
        return;
      }
      var swatch = e.target.closest('.ura-swatch[data-set]');
      if (swatch) {
        set(swatch.getAttribute('data-set'), swatch.getAttribute('data-value'));
        render(container, 'appearance');
        return;
      }
      var toggle = e.target.closest('[data-toggle]');
      if (toggle) {
        var key = toggle.getAttribute('data-toggle');
        set(key, !C.readSettings()[key]);
        render(container, (window.URAScreens && window.URAScreens.settingsCategory()) || '');
        return;
      }
      var menu = e.target.closest('[data-menu]');
      if (menu) {
        var id = menu.getAttribute('data-menu');
        var s = C.readSettings();
        var hidden = Array.isArray(s.hidden) ? s.hidden.slice() : [];
        var at = hidden.indexOf(id);
        if (at === -1) hidden.push(id); else hidden.splice(at, 1);
        set('hidden', hidden);
        if (window.URAShell && window.URAShell.renderNav) window.URAShell.renderNav();
        render(container, 'menu');
        return;
      }
      var info = e.target.closest('[data-team-info]');
      if (info) {
        C.toast('Team management needs the team service. Nothing is simulated here.', 'info');
      }
    });
    container.addEventListener('change', function (e) {
      var select = e.target.closest('[data-select]');
      if (select) {
        set(select.getAttribute('data-select'), select.value);
        render(container, (window.URAScreens && window.URAScreens.settingsCategory()) || '');
        return;
      }
      var email = e.target.closest('[data-email]');
      if (email) {
        set(email.getAttribute('data-email'), email.value.trim());
        C.toast('Saved', 'success');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Theme manager bridge. Keep the legacy controller working but let this
  // registry own the actual theme decision.
  // ---------------------------------------------------------------------------
  function patchThemeManager() {
    if (!window.ThemeManager) return;
    window.ThemeManager.apply = apply;
    window.ThemeManager.init = function () { apply(); };
    window.ThemeManager.cycle = cycleTheme;
    window.ThemeManager.getPreference = function () {
      var t = C.readSettings().theme;
      return t === 'system' ? 'auto' : t;
    };
  }

  if (window.matchMedia) {
    try {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
        if (C.readSettings().theme === 'system') apply();
      });
    } catch (e) { /* older browsers */ }
  }

  patchThemeManager();
  apply();

  window.URASettings = {
    CATS: CATS,
    SET: SET,
    suggestions: suggestions,
    get: get,
    set: set,
    apply: apply,
    cycleTheme: cycleTheme,
    useSuggestions: useSuggestions,
    allApplied: allApplied,
    render: render,
    bind: bind
  };
})();
