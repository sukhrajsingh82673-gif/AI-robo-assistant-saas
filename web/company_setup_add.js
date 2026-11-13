/**
 * ZONATA — Add company page
 *
 * The single "Add a company" screen: two cards (create new / add existing),
 * honest hints about what each path will do, a "Not sure which one?" helper,
 * and a permission-aware state. The server enforces the real permission; this
 * page only reflects it and never pretends a company was created.
 *
 * Route: /company/add (also used by /company/new through EntryFlows).
 */

(function() {
  'use strict';

  const INTENT_KEY = 'zonata_company_setup_intent';

  function t(key, vars) {
    if (window.I18n && typeof window.I18n.t === 'function') return window.I18n.t(key, vars);
    return String(key || '');
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function decodeTokenRole() {
    let token = '';
    try {
      token = localStorage.getItem('zonata_auth_token') || '';
      if (!token && window.state && window.state.host) token = window.state.host.token || '';
    } catch (err) {
      token = '';
    }
    if (!token || token.indexOf('.') < 0) return {};
    try {
      const lastDot = token.lastIndexOf('.');
      const payload = JSON.parse(token.slice(0, lastDot));
      return { role: payload.role, user_id: payload.user_id, principal_type: payload.principal_type };
    } catch (err) {
      return {};
    }
  }

  function viewer() {
    const host = (window.state && window.state.host) || {};
    const token = decodeTokenRole();
    const role = String(host.role || token.role || '').toUpperCase();
    const userId = String(host.user_id || host.id || token.user_id || '');
    const principalType = String(host.principal_type || token.principal_type || 'USER').toUpperCase();
    const agent = principalType.indexOf('AGENT') >= 0
      || role.indexOf('AGENT') >= 0
      || /^(agent_|agt_|ai_agent_)/i.test(userId);
    // Mirrors the server's create rule (OWNER / GLOBAL_ADMIN / EXECUTIVE).
    // SOVEREIGN_HOST is the local dev bootstrap host; the server still decides.
    const allowedRoles = ['OWNER', 'SOVEREIGN_HOST', 'GLOBAL_ADMIN', 'EXECUTIVE'];
    // Unknown roles are not blocked in the UI; the server still denies them.
    const allowed = !agent && (role === '' || allowedRoles.indexOf(role) >= 0);
    return { role, userId, agent, allowed };
  }

  class AddCompanyPage {
    constructor() {
      this.helpOpen = false;
      this.containerId = null;
      this._onLanguageChange = this._onLanguageChange.bind(this);
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
    }

    _onLanguageChange() {
      if (!this.containerId) return;
      const container = document.getElementById(this.containerId);
      if (container && container.querySelector('[data-company-setup-add]')) {
        this.render(this.containerId);
      }
    }

    canAddCompany() {
      return viewer().allowed;
    }

    render(containerOrId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;
      if (!container) return;
      this.containerId = container.id || this.containerId;

      const access = viewer();
      const disabled = access.allowed ? '' : ' aria-disabled="true" disabled';
      const denied = access.allowed ? '' : `
        <div class="zc-inline-notice zc-inline-notice-warning" role="status">
          <strong>${escapeHtml(t('company.add.denied.title'))}</strong>
          <span>${escapeHtml(t('company.add.denied.body'))}</span>
        </div>
      `;

      const language = (window.I18n && window.I18n.getLanguage()) || 'en';

      container.innerHTML = `
        <div class="zc-add-page" data-company-setup-add>
          <div class="zc-add-top">
            <button type="button" class="zc-back-link" id="zcAddBack">
              <span class="zc-back-arrow" aria-hidden="true">←</span>
              <span>${escapeHtml(t('company.add.back'))}</span>
            </button>
            <div class="zc-language-toggle" role="group" aria-label="${escapeHtml(t('common.language'))}">
              <button type="button" data-language="en" aria-pressed="${language === 'en' ? 'true' : 'false'}">${escapeHtml(t('common.english'))}</button>
              <button type="button" data-language="ar" aria-pressed="${language === 'ar' ? 'true' : 'false'}">${escapeHtml(t('common.arabic'))}</button>
            </div>
          </div>

          <header class="zc-add-header">
            <h1 class="zc-add-title">${escapeHtml(t('company.add.title'))}</h1>
            <p class="zc-add-subtitle">${escapeHtml(t('company.add.subtitle'))}</p>
          </header>

          ${denied}

          <div class="zc-add-grid">
            <button type="button" class="zc-add-card zc-add-card-new" data-add-type="NEW"${disabled}>
              <span class="zc-add-card-top">
                <span class="zc-add-tile zc-add-tile-new" aria-hidden="true">
                  ${window.Icon ? window.Icon({ name: 'plus', size: 22, tone: 'white' }) : '+'}
                </span>
                <span class="zc-add-badge zc-add-badge-new">${escapeHtml(t('company.add.new.badge'))}</span>
              </span>
              <span class="zc-add-card-title">${escapeHtml(t('company.add.new.title'))}</span>
              <span class="zc-add-card-body">${escapeHtml(t('company.add.new.body'))}</span>
              <span class="zc-add-points">
                <span class="zc-add-point">${escapeHtml(t('company.add.new.point1'))}</span>
                <span class="zc-add-point">${escapeHtml(t('company.add.new.point2'))}</span>
                <span class="zc-add-point">${escapeHtml(t('company.add.new.point3'))}</span>
                <span class="zc-add-point">${escapeHtml(t('company.add.new.point4'))}</span>
              </span>
              <span class="zc-add-cta">${escapeHtml(t('company.add.new.cta'))} <span aria-hidden="true">→</span></span>
            </button>

            <button type="button" class="zc-add-card zc-add-card-existing" data-add-type="EXISTING"${disabled}>
              <span class="zc-add-card-top">
                <span class="zc-add-tile zc-add-tile-existing" aria-hidden="true">
                  ${window.Icon ? window.Icon({ name: 'building', size: 22, tone: 'white' }) : '🏢'}
                </span>
                <span class="zc-add-badge zc-add-badge-existing">${escapeHtml(t('company.add.existing.badge'))}</span>
              </span>
              <span class="zc-add-card-title">${escapeHtml(t('company.add.existing.title'))}</span>
              <span class="zc-add-card-body">${escapeHtml(t('company.add.existing.body'))}</span>
              <span class="zc-add-points">
                <span class="zc-add-point">${escapeHtml(t('company.add.existing.point1'))}</span>
                <span class="zc-add-point">${escapeHtml(t('company.add.existing.point2'))}</span>
                <span class="zc-add-point">${escapeHtml(t('company.add.existing.point3'))}</span>
                <span class="zc-add-point">${escapeHtml(t('company.add.existing.point4'))}</span>
              </span>
              <span class="zc-add-cta">${escapeHtml(t('company.add.existing.cta'))} <span aria-hidden="true">→</span></span>
            </button>
          </div>

          <div class="zc-add-help">
            <button type="button" class="zc-help-toggle" id="zcAddHelpToggle" aria-expanded="${this.helpOpen ? 'true' : 'false'}" aria-controls="zcAddHelp">
              <span class="zc-help-mark" aria-hidden="true">?</span>
              <span>${escapeHtml(t('company.add.not_sure'))}</span>
            </button>
            <div class="zc-help-panel" id="zcAddHelp" ${this.helpOpen ? '' : 'hidden'}>
              <h3 class="zc-help-title">${escapeHtml(t('company.add.help.title'))}</h3>
              <p>${escapeHtml(t('company.add.help.new'))}</p>
              <p>${escapeHtml(t('company.add.help.existing'))}</p>
              <p class="zc-help-note">${escapeHtml(t('company.add.help.note'))}</p>
            </div>
          </div>

          <p class="zc-add-footnote">${escapeHtml(t('company.add.footnote'))}</p>
        </div>
      `;

      this._bind(container);
    }

    _bind(container) {
      const back = container.querySelector('#zcAddBack');
      if (back) {
        back.addEventListener('click', () => {
          if (typeof window.navigateTo === 'function') window.navigateTo('/company');
          else window.location.hash = '#/company';
        });
      }

      container.querySelectorAll('[data-add-type]').forEach((card) => {
        card.addEventListener('click', () => this.choose(card.getAttribute('data-add-type')));
      });

      container.querySelectorAll('[data-language]').forEach((button) => {
        button.addEventListener('click', () => {
          const language = button.getAttribute('data-language');
          if (window.I18n && typeof window.I18n.setLanguage === 'function') {
            window.I18n.setLanguage(language);
          }
        });
      });

      const toggle = container.querySelector('#zcAddHelpToggle');
      const panel = container.querySelector('#zcAddHelp');
      if (toggle && panel) {
        toggle.addEventListener('click', () => {
          this.helpOpen = panel.hidden;
          panel.hidden = !this.helpOpen;
          toggle.setAttribute('aria-expanded', this.helpOpen ? 'true' : 'false');
        });
      }
    }

    choose(type) {
      const kind = String(type || '').toUpperCase();
      if (kind !== 'NEW' && kind !== 'EXISTING') return;
      if (!this.canAddCompany()) {
        if (window.UI && typeof window.UI.showToast === 'function') {
          window.UI.showToast(t('company.add.denied.body'), 'warning');
        }
        return;
      }

      const mode = kind === 'EXISTING' ? 'existing' : 'new';
      try {
        localStorage.setItem(INTENT_KEY, JSON.stringify({
          type: kind,
          selected_at: Date.now(),
          source: 'company_add_page'
        }));
      } catch (err) { /* storage blocked */ }

      if (window.UI && typeof window.UI.showToast === 'function') {
        window.UI.showToast(t(kind === 'NEW' ? 'company.add.intent_new' : 'company.add.intent_existing'), 'info');
      }

      // Reuse the existing intake surfaces for now. Stage 3 replaces the
      // collector with the typed company setup workflow.
      if (window.EntryFlows && typeof window.EntryFlows.startFlow === 'function') {
        if (typeof window.navigateTo === 'function') window.navigateTo('/company/new');
        window.EntryFlows.startFlow(mode, 'view-company');
      } else if (typeof window.navigateTo === 'function') {
        window.navigateTo('/company/new');
      } else {
        window.location.hash = '#/company/new';
      }
    }
  }

  window.CompanySetupAdd = new AddCompanyPage();
})();
