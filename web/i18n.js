/**
 * ZONATA — Internationalisation runtime (English + Arabic)
 *
 * A deliberately small runtime: dictionary lookup, `data-i18n` application,
 * document direction, and Indian (lakh/crore) number and currency formatting.
 * It is not a framework and it adds no dependency.
 *
 * Usage:
 *   I18n.t('company.add.title')
 *   I18n.setLanguage('ar')        // sets <html lang="ar" dir="rtl">
 *   I18n.formatCurrency(1200000)  // ₹12,00,000
 *   I18n.formatCurrency(1200000, 'INR', { compact: true }) // ₹12 L
 *
 * Elements can declare translations:
 *   <h1 data-i18n="company.add.title"></h1>
 *   <button data-i18n-aria-label="common.close"></button>
 */

(function() {
  'use strict';

  const STORAGE_KEY = 'zonata_language';
  const SUPPORTED = ['en', 'ar'];

  const DICTIONARIES = {
    en: {
      'common.cancel': 'Cancel',
      'common.close': 'Close',
      'common.back': 'Back',
      'common.retry': 'Try again',
      'common.loading': 'Loading…',
      'common.english': 'English',
      'common.arabic': 'العربية',
      'common.language': 'Language',

      'status.draft': 'Draft',
      'status.creating': 'Creating',
      'status.onboarding': 'Onboarding',
      'status.operational': 'Operational',
      'status.needs_attention': 'Needs attention',
      'status.pending_export': 'Pending export',
      'status.pending_deletion': 'Pending deletion',
      'status.deleted': 'Deleted',
      'status.suspended': 'Suspended',
      'status.unknown': 'Unknown status',

      'company.switcher.title': 'Switch company',
      'company.switcher.subtitle': 'Your current company is shown first.',
      'company.switcher.current': 'Current',
      'company.switcher.empty.title': 'No companies yet',
      'company.switcher.empty.body': 'Add your first company to start operating.',
      'company.switcher.empty.sidebar': 'No company yet',
      'company.switcher.empty.status': 'Add a company to begin',
      'company.switcher.add': 'Add company',
      'company.switcher.switched': 'Switched to {name}',
      'company.switcher.refresh_failed': 'Could not refresh. Showing the companies last loaded on this device.',
      'company.switcher.refreshing': 'Refreshing companies…',
      'company.switcher.portfolio': 'All companies (portfolio)',
      'company.switcher.unknown_industry': 'Operating company',

      'company.add.back': 'Companies',
      'company.add.title': 'Add a company',
      'company.add.subtitle': 'Choose how this company joins ZONATA. You can edit or delete it later.',
      'company.add.new.badge': 'New',
      'company.add.new.title': 'Create a new company',
      'company.add.new.body': 'For a business that does not exist yet. ZONATA builds the company with you.',
      'company.add.new.point1': 'Starts with status Creating',
      'company.add.new.point2': 'Guided build, typically 1–3 days',
      'company.add.new.point3': 'Legal and operating setup drafted for your review',
      'company.add.new.point4': 'You can edit or delete it later',
      'company.add.new.cta': 'Create new company',
      'company.add.existing.badge': 'Existing',
      'company.add.existing.title': 'Add an existing company',
      'company.add.existing.body': 'For a business already operating. ZONATA studies it and diagnoses what to improve.',
      'company.add.existing.point1': 'Starts with status Onboarding',
      'company.add.existing.point2': 'Read-only connections — nothing is written back',
      'company.add.existing.point3': 'Diagnosis and readiness findings with evidence',
      'company.add.existing.point4': 'Your data stays in your own systems',
      'company.add.existing.cta': 'Add existing company',
      'company.add.not_sure': 'Not sure which one?',
      'company.add.help.title': 'A quick way to decide',
      'company.add.help.new': 'Choose Create new if the company has no history in ZONATA and little or no operating data.',
      'company.add.help.existing': 'Choose Add existing if it already has customers, revenue, tools, or records.',
      'company.add.help.note': 'Both paths start as a draft. Nothing is submitted until you review and confirm.',
      'company.add.denied.title': 'You cannot add a company',
      'company.add.denied.body': 'Only the owner or an allowed admin can add a company. You can still ask the assistant to prepare a draft.',
      'company.add.intent_new': 'Opening the new company setup. Nothing has been created yet.',
      'company.add.intent_existing': 'Opening the existing company intake. Nothing has been connected yet.',
      'company.add.footnote': 'Your company list is scoped to your organisation. Other tenants can never see or change it.',

      'assistant.add_opened': 'Opening the Add company page. Nothing has been created yet.',
      'assistant.switch_opened': 'Opening your companies. Nothing has been switched yet.',

      'format.lakh': 'L',
      'format.crore': 'Cr',
      'format.thousand': 'K'
    },

    ar: {
      'common.cancel': 'إلغاء',
      'common.close': 'إغلاق',
      'common.back': 'رجوع',
      'common.retry': 'إعادة المحاولة',
      'common.loading': 'جارٍ التحميل…',
      'common.english': 'English',
      'common.arabic': 'العربية',
      'common.language': 'اللغة',

      'status.draft': 'مسودة',
      'status.creating': 'قيد الإنشاء',
      'status.onboarding': 'قيد التهيئة',
      'status.operational': 'تعمل',
      'status.needs_attention': 'تحتاج إلى انتباه',
      'status.pending_export': 'بانتظار التصدير',
      'status.pending_deletion': 'بانتظار الحذف',
      'status.deleted': 'محذوفة',
      'status.suspended': 'موقوفة',
      'status.unknown': 'حالة غير معروفة',

      'company.switcher.title': 'تبديل الشركة',
      'company.switcher.subtitle': 'تظهر شركتك الحالية أولاً.',
      'company.switcher.current': 'الحالية',
      'company.switcher.empty.title': 'لا توجد شركات بعد',
      'company.switcher.empty.body': 'أضف شركتك الأولى لبدء العمل.',
      'company.switcher.empty.sidebar': 'لا توجد شركة بعد',
      'company.switcher.empty.status': 'أضف شركة للبدء',
      'company.switcher.add': 'إضافة شركة',
      'company.switcher.switched': 'تم التبديل إلى {name}',
      'company.switcher.refresh_failed': 'تعذّر التحديث. يتم عرض الشركات المحمّلة سابقاً على هذا الجهاز.',
      'company.switcher.refreshing': 'جارٍ تحديث الشركات…',
      'company.switcher.portfolio': 'كل الشركات (المحفظة)',
      'company.switcher.unknown_industry': 'شركة عاملة',

      'company.add.back': 'الشركات',
      'company.add.title': 'إضافة شركة',
      'company.add.subtitle': 'اختر كيف تنضم هذه الشركة إلى ZONATA. يمكنك تعديلها أو حذفها لاحقاً.',
      'company.add.new.badge': 'جديدة',
      'company.add.new.title': 'إنشاء شركة جديدة',
      'company.add.new.body': 'لعمل لم يوجد بعد. تبني ZONATA الشركة معك خطوة بخطوة.',
      'company.add.new.point1': 'تبدأ بحالة قيد الإنشاء',
      'company.add.new.point2': 'بناء موجّه، عادة من يوم إلى ثلاثة أيام',
      'company.add.new.point3': 'مسودة للهيكل القانوني والتشغيلي لمراجعتك',
      'company.add.new.point4': 'يمكنك تعديلها أو حذفها لاحقاً',
      'company.add.new.cta': 'إنشاء شركة جديدة',
      'company.add.existing.badge': 'موجودة',
      'company.add.existing.title': 'إضافة شركة موجودة',
      'company.add.existing.body': 'لعمل يعمل بالفعل. تدرسه ZONATA وتشخّص ما يحتاج إلى تحسين.',
      'company.add.existing.point1': 'تبدأ بحالة قيد التهيئة',
      'company.add.existing.point2': 'اتصالات للقراءة فقط — لا يُكتب أي شيء في أنظمتك',
      'company.add.existing.point3': 'تشخيص ونتائج جاهزية مع الأدلة',
      'company.add.existing.point4': 'تبقى بياناتك في أنظمتك',
      'company.add.existing.cta': 'إضافة شركة موجودة',
      'company.add.not_sure': 'لست متأكداً من الاختيار؟',
      'company.add.help.title': 'طريقة سريعة للقرار',
      'company.add.help.new': 'اختر «إنشاء شركة جديدة» إذا لم يكن للشركة سجل في ZONATA ولا تملك بيانات تشغيلية تُذكر.',
      'company.add.help.existing': 'اختر «إضافة شركة موجودة» إذا كان لديها عملاء أو إيرادات أو أدوات أو سجلات.',
      'company.add.help.note': 'يبدأ المساران كمسودة. لا يُرسل أي شيء حتى تراجع وتؤكد.',
      'company.add.denied.title': 'لا يمكنك إضافة شركة',
      'company.add.denied.body': 'يمكن للمالك أو المسؤول المصرّح له فقط إضافة شركة. يمكنك دائماً أن تطلب من المساعد إعداد مسودة.',
      'company.add.intent_new': 'جارٍ فتح إعداد الشركة الجديدة. لم يتم إنشاء أي شيء بعد.',
      'company.add.intent_existing': 'جارٍ فتح استقبال الشركة الموجودة. لم يتم ربط أي شيء بعد.',
      'company.add.footnote': 'قائمة شركاتك مرتبطة بمؤسستك فقط. لا يمكن لمستأجر آخر رؤيتها أو تغييرها.',

      'assistant.add_opened': 'جارٍ فتح صفحة إضافة شركة. لم يتم إنشاء أي شيء بعد.',
      'assistant.switch_opened': 'جارٍ فتح شركاتك. لم يتم تبديل أي شيء بعد.',

      'format.lakh': ' لك',
      'format.crore': ' كر',
      'format.thousand': ' ألف'
    }
  };

  const listeners = new Set();
  let language = 'en';

  function normaliseLanguage(value) {
    const raw = String(value || '').toLowerCase().split('-')[0];
    return SUPPORTED.indexOf(raw) >= 0 ? raw : 'en';
  }

  function readStoredLanguage() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function writeStoredLanguage(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (err) {
      // Private mode / blocked storage: keep the in-memory choice.
    }
  }

  function lookup(dict, key) {
    if (!key) return '';
    if (Object.prototype.hasOwnProperty.call(dict, key)) return dict[key];
    // Allow a flat dictionary to be addressed with dotted keys.
    const parts = String(key).split('.');
    let node = dict;
    for (const part of parts) {
      if (node && typeof node === 'object' && Object.prototype.hasOwnProperty.call(node, part)) {
        node = node[part];
      } else {
        return '';
      }
    }
    return typeof node === 'string' ? node : '';
  }

  function interpolate(text, vars) {
    if (!vars || typeof text !== 'string') return text;
    return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => {
      const value = vars[name];
      return value === undefined || value === null ? match : String(value);
    });
  }

  function t(key, vars) {
    const current = DICTIONARIES[language] || DICTIONARIES.en;
    const fallback = DICTIONARIES.en;
    const value = lookup(current, key) || lookup(fallback, key) || key;
    return interpolate(value, vars);
  }

  function dirFor(lang) {
    return lang === 'ar' ? 'rtl' : 'ltr';
  }

  function apply(root) {
    const scope = root && root.querySelectorAll ? root : document;
    if (!scope || !scope.querySelectorAll) return;

    scope.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    scope.querySelectorAll('[data-i18n-aria-label]').forEach((el) => {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria-label')));
    });
    scope.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
    scope.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });
  }

  function setLanguage(next, options) {
    const value = normaliseLanguage(next);
    const changed = value !== language;
    language = value;
    writeStoredLanguage(value);

    const html = document.documentElement;
    if (html) {
      html.setAttribute('lang', value);
      html.setAttribute('dir', dirFor(value));
    }

    apply(document);
    listeners.forEach((fn) => {
      try {
        fn(value, dirFor(value));
      } catch (err) {
        console.warn('[I18n] listener failed', err);
      }
    });

    if (changed && options && options.announce === false) return value;
    document.dispatchEvent(new CustomEvent('zonata:languagechange', { detail: { language: value, dir: dirFor(value) } }));
    return value;
  }

  function onLanguageChange(fn) {
    if (typeof fn !== 'function') return () => {};
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function getLanguage() {
    return language;
  }

  function getDir() {
    return dirFor(language);
  }

  function locale() {
    return language === 'ar' ? 'ar-IN' : 'en-IN';
  }

  function formatNumber(value, options) {
    const n = Number(value);
    const safe = Number.isFinite(n) ? n : 0;
    try {
      return new Intl.NumberFormat(locale(), options || {}).format(safe);
    } catch (err) {
      return String(safe);
    }
  }

  function formatCurrency(amount, currency, options) {
    const code = String(currency || 'INR').toUpperCase();
    const opts = options || {};
    const n = Number(amount);
    const safe = Number.isFinite(n) ? n : 0;

    if (opts.compact) {
      return formatCompactCurrency(safe, code);
    }

    try {
      return new Intl.NumberFormat(locale(), {
        style: 'currency',
        currency: code,
        maximumFractionDigits: opts.maximumFractionDigits === undefined ? 0 : opts.maximumFractionDigits,
        minimumFractionDigits: opts.minimumFractionDigits === undefined ? 0 : opts.minimumFractionDigits
      }).format(safe);
    } catch (err) {
      return `${code} ${formatNumber(safe, opts)}`;
    }
  }

  function currencySymbol(code) {
    try {
      const parts = new Intl.NumberFormat(locale(), { style: 'currency', currency: code, maximumFractionDigits: 0 })
        .formatToParts(0);
      const symbol = parts.find((part) => part.type === 'currency');
      return symbol ? symbol.value : code;
    } catch (err) {
      return code === 'INR' ? '₹' : code;
    }
  }

  /**
   * Indian compact notation: 1,00,000 -> 1 L, 1,00,00,000 -> 1 Cr.
   * Non-INR currencies fall back to the locale's compact notation.
   */
  function formatCompactCurrency(amount, currency) {
    const code = String(currency || 'INR').toUpperCase();
    const n = Number(amount);
    const safe = Number.isFinite(n) ? n : 0;
    const sign = safe < 0 ? '-' : '';
    const abs = Math.abs(safe);
    const symbol = currencySymbol(code);

    if (code === 'INR') {
      if (abs >= 1e7) {
        const value = abs / 1e7;
        return `${sign}${symbol}${formatNumber(value, { maximumFractionDigits: value >= 10 ? 0 : 1 })}${t('format.crore')}`;
      }
      if (abs >= 1e5) {
        const value = abs / 1e5;
        return `${sign}${symbol}${formatNumber(value, { maximumFractionDigits: value >= 10 ? 0 : 1 })}${t('format.lakh')}`;
      }
      if (abs >= 1e3) {
        return `${sign}${symbol}${formatNumber(abs / 1e3, { maximumFractionDigits: 0 })}${t('format.thousand')}`;
      }
      return `${sign}${symbol}${formatNumber(abs, { maximumFractionDigits: 0 })}`;
    }

    try {
      return new Intl.NumberFormat(locale(), {
        style: 'currency',
        currency: code,
        notation: 'compact',
        maximumFractionDigits: 1
      }).format(safe);
    } catch (err) {
      return `${sign}${symbol}${formatNumber(abs, { notation: 'compact', maximumFractionDigits: 1 })}`;
    }
  }

  function init() {
    const stored = readStoredLanguage();
    language = normaliseLanguage(stored || 'en');
    const html = document.documentElement;
    if (html) {
      html.setAttribute('lang', language);
      html.setAttribute('dir', dirFor(language));
    }
    apply(document);
    return language;
  }

  window.I18n = {
    SUPPORTED,
    t,
    apply,
    init,
    setLanguage,
    getLanguage,
    getDir,
    onLanguageChange,
    formatNumber,
    formatCurrency,
    formatCompactCurrency,
    locale
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
