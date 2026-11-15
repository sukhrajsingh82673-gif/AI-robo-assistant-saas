/* ==========================================================================
   URA Core — settings defaults, translation, formatting and shared rules.
   Classic browser script: exposes window.URACore.
   ========================================================================== */
(function () {
  'use strict';

  var STORE_KEY = 'ura.ui.settings.v1';
  var LEGACY_KEY = 'zonata_settings';

  var DEFAULTS = {
    theme: 'system',
    accent: 'blue',
    density: 'comfortable',
    sidebar: 'full',
    textSize: 100,
    reduceMotion: false,
    contrast: false,
    lang: 'en',
    tz: 'auto',
    hour: 'auto',
    dateFmt: 'auto',
    numFmt: 'auto',
    currency: 'company',
    autonomy: 'balanced',
    payLimit: 1000,
    hours: '247',
    tone: 'brief',
    n_approvals: true,
    n_security: true,
    n_reports: true,
    n_builds: true,
    quiet: false,
    repFreq: 'weekly',
    repEmail: '',
    repProfit: true,
    repSales: true,
    repSec: false,
    twofa: false,
    session: '1h',
    audit: '90',
    region: 'in',
    terminalOn: true,
    hidden: []
  };

  var LANGS = [
    ['en', 'English'],
    ['hi', 'हिन्दी (Hindi)'],
    ['pa', 'ਪੰਜਾਬੀ (Punjabi)'],
    ['ar', 'العربية (Arabic)'],
    ['es', 'Español (Spanish)'],
    ['fr', 'Français (French)']
  ];

  var REGIONS = {
    in: 'India',
    ae: 'United Arab Emirates',
    gb: 'United Kingdom',
    eu: 'European Union',
    us: 'United States',
    sg: 'Singapore',
    au: 'Australia'
  };

  var TZS = [
    'Asia/Kolkata', 'Asia/Dubai', 'Europe/London', 'Europe/Madrid', 'Europe/Paris',
    'Europe/Berlin', 'America/New_York', 'America/Los_Angeles', 'Asia/Tokyo', 'UTC'
  ];

  var DICT = {
    en: {
      'group.workspace': 'Workspace',
      'group.departments': 'Departments',
      'group.workforce': 'Workforce',
      'group.system': 'System',
      'nav.overview': 'Overview',
      'nav.askceo': 'Ask CEO',
      'nav.approvals': 'Approvals',
      'nav.operations': 'Operations',
      'nav.marketing': 'Marketing & Sales',
      'nav.technology': 'Technology',
      'nav.finance': 'Finance',
      'nav.people': 'People',
      'nav.employees': 'AI Employees',
      'nav.agents': 'Agents',
      'nav.coworker': 'Co-worker',
      'nav.tools': 'Tools & Integrations',
      'nav.security': 'Security',
      'nav.terminal': 'Terminal',
      'nav.reports': 'Reports',
      'nav.companies': 'Companies',
      'nav.settings': 'Settings',
      'page.overview': 'Overview',
      'page.askceo': 'Ask CEO',
      'page.approvals': 'Approvals',
      'page.operations': 'Operations',
      'page.marketing': 'Marketing & Sales',
      'page.technology': 'Technology',
      'page.finance': 'Finance',
      'page.people': 'People',
      'page.employees': 'AI Employees',
      'page.agents': 'Agents',
      'page.coworker': 'Co-worker',
      'page.tools': 'Tools & Integrations',
      'page.security': 'Security',
      'page.terminal': 'Terminal',
      'page.reports': 'Reports',
      'page.companies': 'Companies',
      'page.settings': 'Settings',
      'greeting.morning': 'Good morning',
      'greeting.afternoon': 'Good afternoon',
      'greeting.evening': 'Good evening',
      'action.approve': 'Approve',
      'action.decline': 'Decline',
      'action.save': 'Save',
      'action.cancel': 'Cancel',
      'action.close': 'Close',
      'action.retry': 'Retry',
      'action.search': 'Search pages, companies, actions and settings',
      'action.signout': 'Sign out',
      'action.settings': 'Open settings',
      'action.theme': 'Theme',
      'empty.noData': 'Nothing to show yet',
      'empty.connect': 'Connect the system that provides this data to see it here.'
    },
    hi: {
      'group.workspace': 'कार्यक्षेत्र',
      'group.departments': 'विभाग',
      'group.workforce': 'कार्यबल',
      'group.system': 'सिस्टम',
      'nav.overview': 'अवलोकन',
      'nav.askceo': 'CEO से पूछें',
      'nav.approvals': 'स्वीकृतियाँ',
      'nav.operations': 'संचालन',
      'nav.marketing': 'विपणन और बिक्री',
      'nav.technology': 'प्रौद्योगिकी',
      'nav.finance': 'वित्त',
      'nav.people': 'लोग',
      'nav.employees': 'AI कर्मचारी',
      'nav.agents': 'एजेंट',
      'nav.coworker': 'सह-कर्मी',
      'nav.tools': 'उपकरण और एकीकरण',
      'nav.security': 'सुरक्षा',
      'nav.terminal': 'टर्मिनल',
      'nav.reports': 'रिपोर्ट',
      'nav.companies': 'कंपनियाँ',
      'nav.settings': 'सेटिंग्स',
      'greeting.morning': 'सुप्रभात',
      'greeting.afternoon': 'नमस्कार',
      'greeting.evening': 'शुभ संध्या',
      'action.approve': 'स्वीकृत करें',
      'action.decline': 'अस्वीकार करें',
      'action.save': 'सहेजें',
      'action.cancel': 'रद्द करें',
      'action.close': 'बंद करें',
      'action.search': 'पेज, कंपनियाँ, क्रियाएँ और सेटिंग्स खोजें'
    },
    pa: {
      'group.workspace': 'ਕਾਰਜ ਖੇਤਰ',
      'group.departments': 'ਵਿਭਾਗ',
      'group.workforce': 'ਕਰਮਚਾਰੀ',
      'group.system': 'ਸਿਸਟਮ',
      'nav.overview': 'ਸੰਖੇਪ',
      'nav.askceo': 'CEO ਨੂੰ ਪੁੱਛੋ',
      'nav.approvals': 'ਮਨਜ਼ੂਰੀਆਂ',
      'nav.operations': 'ਸੰਚਾਲਨ',
      'nav.marketing': 'ਮਾਰਕੀਟਿੰਗ ਅਤੇ ਵਿਕਰੀ',
      'nav.technology': 'ਤਕਨਾਲੋਜੀ',
      'nav.finance': 'ਵਿੱਤ',
      'nav.people': 'ਲੋਕ',
      'nav.employees': 'AI ਕਰਮਚਾਰੀ',
      'nav.agents': 'ਏਜੰਟ',
      'nav.coworker': 'ਸਹਿ-ਕਰਮਚਾਰੀ',
      'nav.tools': 'ਟੂਲ ਅਤੇ ਇੰਟੀਗ੍ਰੇਸ਼ਨ',
      'nav.security': 'ਸੁਰੱਖਿਆ',
      'nav.terminal': 'ਟਰਮੀਨਲ',
      'nav.reports': 'ਰਿਪੋਰਟਾਂ',
      'nav.companies': 'ਕੰਪਨੀਆਂ',
      'nav.settings': 'ਸੈਟਿੰਗਾਂ',
      'greeting.morning': 'ਸ਼ੁਭ ਸਵੇਰ',
      'greeting.afternoon': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ',
      'greeting.evening': 'ਸ਼ੁਭ ਸ਼ਾਮ',
      'action.approve': 'ਮਨਜ਼ੂਰ ਕਰੋ',
      'action.decline': 'ਅਸਵੀਕਾਰ ਕਰੋ',
      'action.save': 'ਸੇਵ ਕਰੋ',
      'action.cancel': 'ਰੱਦ ਕਰੋ',
      'action.close': 'ਬੰਦ ਕਰੋ'
    },
    ar: {
      'group.workspace': 'مساحة العمل',
      'group.departments': 'الأقسام',
      'group.workforce': 'فريق العمل',
      'group.system': 'النظام',
      'nav.overview': 'نظرة عامة',
      'nav.askceo': 'اسأل الرئيس التنفيذي',
      'nav.approvals': 'الموافقات',
      'nav.operations': 'العمليات',
      'nav.marketing': 'التسويق والمبيعات',
      'nav.technology': 'التقنية',
      'nav.finance': 'المالية',
      'nav.people': 'الأفراد',
      'nav.employees': 'موظفو الذكاء الاصطناعي',
      'nav.agents': 'الوكلاء',
      'nav.coworker': 'المساعد',
      'nav.tools': 'الأدوات والتكاملات',
      'nav.security': 'الأمان',
      'nav.terminal': 'الطرفية',
      'nav.reports': 'التقارير',
      'nav.companies': 'الشركات',
      'nav.settings': 'الإعدادات',
      'greeting.morning': 'صباح الخير',
      'greeting.afternoon': 'مساء الخير',
      'greeting.evening': 'مساء الخير',
      'action.approve': 'موافقة',
      'action.decline': 'رفض',
      'action.save': 'حفظ',
      'action.cancel': 'إلغاء',
      'action.close': 'إغلاق',
      'action.search': 'ابحث في الصفحات والشركات والإجراءات والإعدادات'
    },
    es: {
      'group.workspace': 'Espacio de trabajo',
      'group.departments': 'Departamentos',
      'group.workforce': 'Equipo',
      'group.system': 'Sistema',
      'nav.overview': 'Resumen',
      'nav.askceo': 'Preguntar al CEO',
      'nav.approvals': 'Aprobaciones',
      'nav.operations': 'Operaciones',
      'nav.marketing': 'Marketing y ventas',
      'nav.technology': 'Tecnología',
      'nav.finance': 'Finanzas',
      'nav.people': 'Personas',
      'nav.employees': 'Empleados de IA',
      'nav.agents': 'Agentes',
      'nav.coworker': 'Compañero',
      'nav.tools': 'Herramientas e integraciones',
      'nav.security': 'Seguridad',
      'nav.terminal': 'Terminal',
      'nav.reports': 'Informes',
      'nav.companies': 'Empresas',
      'nav.settings': 'Ajustes',
      'greeting.morning': 'Buenos días',
      'greeting.afternoon': 'Buenas tardes',
      'greeting.evening': 'Buenas noches',
      'action.approve': 'Aprobar',
      'action.decline': 'Rechazar',
      'action.save': 'Guardar',
      'action.cancel': 'Cancelar',
      'action.close': 'Cerrar'
    },
    fr: {
      'group.workspace': 'Espace de travail',
      'group.departments': 'Départements',
      'group.workforce': 'Équipe',
      'group.system': 'Système',
      'nav.overview': 'Vue d’ensemble',
      'nav.askceo': 'Demander au CEO',
      'nav.approvals': 'Approbations',
      'nav.operations': 'Opérations',
      'nav.marketing': 'Marketing et ventes',
      'nav.technology': 'Technologie',
      'nav.finance': 'Finance',
      'nav.people': 'Personnes',
      'nav.employees': 'Employés IA',
      'nav.agents': 'Agents',
      'nav.coworker': 'Collaborateur',
      'nav.tools': 'Outils et intégrations',
      'nav.security': 'Sécurité',
      'nav.terminal': 'Terminal',
      'nav.reports': 'Rapports',
      'nav.companies': 'Entreprises',
      'nav.settings': 'Réglages',
      'greeting.morning': 'Bonjour',
      'greeting.afternoon': 'Bon après-midi',
      'greeting.evening': 'Bonsoir',
      'action.approve': 'Approuver',
      'action.decline': 'Refuser',
      'action.save': 'Enregistrer',
      'action.cancel': 'Annuler',
      'action.close': 'Fermer'
    }
  };

  var LOCALES = { en: 'en', hi: 'hi-IN', pa: 'pa-IN', ar: 'ar', es: 'es', fr: 'fr' };
  var CURRENCY_BY_SYMBOL = { '₹': 'INR', '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', 'د.إ': 'AED' };

  function readSettings() {
    var raw = null;
    try { raw = JSON.parse(localStorage.getItem(STORE_KEY) || 'null'); } catch (e) { raw = null; }
    if (!raw || typeof raw !== 'object') {
      try { raw = JSON.parse(localStorage.getItem(LEGACY_KEY) || 'null'); } catch (e2) { raw = null; }
    }
    var out = {};
    Object.keys(DEFAULTS).forEach(function (key) { out[key] = DEFAULTS[key]; });
    if (raw && typeof raw === 'object') {
      Object.keys(DEFAULTS).forEach(function (key) {
        if (raw[key] !== undefined) out[key] = raw[key];
      });
    }
    if (!Array.isArray(out.hidden)) out.hidden = [];
    return out;
  }

  function saveSettings(patch) {
    var next = readSettings();
    Object.keys(patch || {}).forEach(function (key) { next[key] = patch[key]; });
    localStorage.setItem(STORE_KEY, JSON.stringify(next));
    return next;
  }

  function getLang() {
    var lang = readSettings().lang;
    return DICT[lang] ? lang : 'en';
  }

  function t(key, vars) {
    var lang = getLang();
    var value = (DICT[lang] && DICT[lang][key]) || DICT.en[key] || key;
    if (vars) {
      Object.keys(vars).forEach(function (name) {
        value = value.replace(new RegExp('\\{' + name + '\\}', 'g'), String(vars[name]));
      });
    }
    return value;
  }

  function locale() {
    return LOCALES[getLang()] || 'en';
  }

  function activeCompany() {
    try {
      var s = (typeof state !== 'undefined' && state) ? state : null;
      if (!s) return null;
      var list = Array.isArray(s.companies) ? s.companies : [];
      return list.find(function (c) { return c && c.id === s.activeCompanyId; }) || list[0] || null;
    } catch (e) { return null; }
  }

  function companyCurrency(company) {
    var c = company || activeCompany();
    if (c && c.currency) return c.currency;
    return 'USD';
  }

  function currencyCode(value) {
    if (!value) return 'USD';
    if (CURRENCY_BY_SYMBOL[value]) return CURRENCY_BY_SYMBOL[value];
    if (/^[A-Z]{3}$/.test(value)) return value;
    return null;
  }

  function formatNumber(value, options) {
    if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return '—';
    var opts = options || {};
    var style = readSettings().numFmt;
    var loc = opts.locale || locale();
    if (style && style !== 'auto') loc = style;
    try {
      return new Intl.NumberFormat(loc, {
        maximumFractionDigits: opts.decimals === undefined ? 2 : opts.decimals,
        minimumFractionDigits: opts.minimumFractionDigits || 0
      }).format(Number(value));
    } catch (e) {
      return String(value);
    }
  }

  function formatMoney(value, options) {
    if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return '—';
    var opts = options || {};
    var settings = readSettings();
    var source = opts.sourceCurrency || companyCurrency();
    var code = currencyCode(source);
    var display = settings.currency && settings.currency !== 'company' ? settings.currency : source;
    var displayCode = currencyCode(display);

    // Never invent an exchange rate. If the chosen display currency differs from
    // the source, keep the real source amount and mark it as not converted.
    if (displayCode && code && displayCode !== code) {
      return formatMoneyRaw(value, source, code, opts) + ' (FX not connected)';
    }
    return formatMoneyRaw(value, source, code, opts);
  }

  function formatMoneyRaw(value, source, code, opts) {
    var options2 = opts || {};
    if (code) {
      try {
        return new Intl.NumberFormat(locale(), {
          style: 'currency',
          currency: code,
          maximumFractionDigits: options2.decimals === undefined ? 2 : options2.decimals
        }).format(Number(value));
      } catch (e) { /* fall through to prefix */ }
    }
    return String(source || '') + formatNumber(value, options2);
  }

  function formatCompact(value, options) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
    try {
      return new Intl.NumberFormat(locale(), { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value));
    } catch (e) { return formatNumber(value, options); }
  }

  function resolveTimeZone() {
    var s = readSettings();
    if (s.tz && s.tz !== 'auto') return s.tz;
    var c = activeCompany();
    return (c && c.timezone) || Intl.DateTimeFormat().resolvedOptions().timeZone;
  }

  function dateParts(value) {
    var date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return {
      year: date.getFullYear(),
      month: date.getMonth() + 1,
      day: date.getDate(),
      hour: date.getHours(),
      minute: date.getMinutes()
    };
  }

  function formatDate(value, options) {
    if (!value) return '—';
    var date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    var s = readSettings();
    var day = String(date.getDate()).padStart(2, '0');
    var month = String(date.getMonth() + 1).padStart(2, '0');
    var year = date.getFullYear();
    if (s.dateFmt === 'dmy') return day + '/' + month + '/' + year;
    if (s.dateFmt === 'mdy') return month + '/' + day + '/' + year;
    if (s.dateFmt === 'iso') return year + '-' + month + '-' + day;
    try {
      return new Intl.DateTimeFormat(locale(), { year: 'numeric', month: 'short', day: 'numeric' }).format(date);
    } catch (e) { return day + '/' + month + '/' + year; }
  }

  function formatTime(value, options) {
    var date = value ? (value instanceof Date ? value : new Date(value)) : new Date();
    if (Number.isNaN(date.getTime())) return '—';
    var s = readSettings();
    var opts = {
      timeZone: (options && options.timeZone) || resolveTimeZone(),
      hour: '2-digit',
      minute: '2-digit'
    };
    if (s.hour === '12') opts.hour12 = true;
    if (s.hour === '24') opts.hour12 = false;
    try {
      return new Intl.DateTimeFormat(locale(), opts).format(date);
    } catch (e) {
      return date.toLocaleTimeString();
    }
  }

  function timeAgo(value) {
    if (!value) return '—';
    var date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    var seconds = Math.round((Date.now() - date.getTime()) / 1000);
    if (Math.abs(seconds) < 45) return 'just now';
    var units = [
      ['year', 31536000], ['month', 2592000], ['week', 604800],
      ['day', 86400], ['hour', 3600], ['minute', 60]
    ];
    for (var i = 0; i < units.length; i += 1) {
      var amount = Math.floor(Math.abs(seconds) / units[i][1]);
      if (amount >= 1) {
        try {
          return new Intl.RelativeTimeFormat(locale(), { numeric: 'auto' }).format(seconds < 0 ? amount : -amount, units[i][0]);
        } catch (e) {
          return amount + ' ' + units[i][0] + (amount === 1 ? '' : 's') + ' ago';
        }
      }
    }
    return 'just now';
  }

  function riskLevel(item) {
    var raw = String((item && (item.risk_level || item.risk || item.severity)) || 'LOW').toUpperCase();
    if (raw === 'CRITICAL' || raw === 'HIGH') return 2;
    if (raw === 'MEDIUM' || raw === 'IMPORTANT') return 1;
    return 0;
  }

  function needsOwner(item, settings) {
    var s = settings || readSettings();
    var autonomy = { ask: -1, balanced: 0, auto: 1 }[s.autonomy];
    if (autonomy === undefined) autonomy = 0;
    var kind = String((item && (item.kind || item.type)) || '').toLowerCase();
    if (kind === 'cowork') return true;
    if (riskLevel(item) > autonomy) return true;
    var amount = Number(item && (item.amount || item.value || item.estimated_value) || 0);
    if (amount > Number(s.payLimit || 0)) return true;
    return false;
  }

  function sessionScore(value) {
    return ({ '15m': 8, '1h': 6, '8h': 2, never: -8 })[value] || 0;
  }

  function auditScore(value) {
    return ({ '30': 1, '90': 4, '365': 7 })[String(value)] || 0;
  }

  function secScore(settings, openFindings, companyRegion, twoStepEnabled) {
    var s = settings || readSettings();
    var score = 58;
    // Two-step is credited only when the server says this account enrolled.
    if (twoStepEnabled) score += 14;
    score += sessionScore(s.session);
    score += auditScore(s.audit);
    score -= 6 * Number(openFindings || 0);
    if (companyRegion && s.region === companyRegion) score += 3;
    return Math.max(8, Math.min(100, score));
  }

  function isQuietHours(now) {
    var date = now || new Date();
    var hour = date.getHours();
    return hour >= 22 || hour < 7;
  }

  function notificationVisible(kind, settings) {
    var s = settings || readSettings();
    var map = {
      approvals: 'n_approvals',
      security: 'n_security',
      reports: 'n_reports',
      builds: 'n_builds'
    };
    var key = map[kind];
    return key ? !!s[key] : true;
  }

  function toArray(value) {
    if (Array.isArray(value)) return value;
    if (value && Array.isArray(value.items)) return value.items;
    if (value && Array.isArray(value.approvals)) return value.approvals;
    if (value && Array.isArray(value.data)) return value.data;
    return [];
  }

  async function api(path, options) {
    var opts = options || {};
    var res = await fetch(path, {
      method: opts.method || 'GET',
      headers: Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {}),
      body: opts.body ? JSON.stringify(opts.body) : undefined
    });
    if (res.status === 401) throw new Error('Your session has expired. Sign in again.');
    var text = await res.text();
    var data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
    if (!res.ok) {
      var message = (data && (data.detail || data.error || data.message)) || ('Request failed (HTTP ' + res.status + ')');
      throw new Error(message);
    }
    return data;
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function toast(message, kind) {
    if (window.URAShell && window.URAShell.toast) return window.URAShell.toast(message, kind);
    if (typeof showToast === 'function') return showToast(message, kind || 'info');
  }

  window.URACore = {
    STORE_KEY: STORE_KEY,
    DEFAULTS: DEFAULTS,
    LANGS: LANGS,
    TZS: TZS,
    REGIONS: REGIONS,
    readSettings: readSettings,
    saveSettings: saveSettings,
    t: t,
    locale: locale,
    activeCompany: activeCompany,
    companyCurrency: companyCurrency,
    currencyCode: currencyCode,
    formatNumber: formatNumber,
    formatMoney: formatMoney,
    formatCompact: formatCompact,
    formatDate: formatDate,
    formatTime: formatTime,
    timeAgo: timeAgo,
    resolveTimeZone: resolveTimeZone,
    dateParts: dateParts,
    needsOwner: needsOwner,
    riskLevel: riskLevel,
    secScore: secScore,
    sessionScore: sessionScore,
    auditScore: auditScore,
    isQuietHours: isQuietHours,
    notificationVisible: notificationVisible,
    toArray: toArray,
    api: api,
    escapeHtml: escapeHtml,
    toast: toast
  };
})();
