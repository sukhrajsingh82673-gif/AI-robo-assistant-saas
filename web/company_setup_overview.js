/**
 * ZONATA — Company overview
 *
 * The real company home: identity, key numbers, build/onboarding progress,
 * sources and connections, legal drafts, and the recent audit trail. Edit and
 * Delete live behind one keyboard-accessible options menu. Delete opens the
 * protected wizard, which is a bottom sheet on phones.
 *
 * Route: /company/<company_id>/overview
 */

(function() {
  'use strict';

  const STATUS_TONE = {
    DRAFT: 'neutral',
    CREATING: 'accent',
    ONBOARDING: 'accent',
    OPERATIONAL: 'green',
    NEEDS_ATTENTION: 'orange',
    PENDING_EXPORT: 'orange',
    PENDING_DELETION: 'red',
    DELETED: 'red',
    SUSPENDED: 'orange'
  };

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

  function language() {
    return (window.I18n && window.I18n.getLanguage && window.I18n.getLanguage()) || 'en';
  }

  function locale() {
    return language() === 'ar' ? 'ar-IN' : 'en-IN';
  }

  function normaliseStatus(value) {
    const status = String(value || '').toUpperCase();
    return status === 'ATTENTION' ? 'NEEDS_ATTENTION' : (status || 'UNKNOWN');
  }

  function statusLabel(value) {
    const status = normaliseStatus(value);
    const key = `status.${status.toLowerCase()}`;
    const label = t(key);
    return label === key ? status : label;
  }

  function money(amount, currency) {
    try {
      if (window.I18n && window.I18n.formatCurrency) {
        return window.I18n.formatCurrency(amount, currency || 'INR', { compact: true });
      }
    } catch (err) { /* fall through */ }
    const value = Number(amount) || 0;
    return `${currency || 'INR'} ${Math.round(value).toLocaleString(locale())}`;
  }

  function formatTime(seconds) {
    if (!seconds) return '';
    try {
      return new Intl.DateTimeFormat(locale(), {
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
      }).format(new Date(Number(seconds) * 1000));
    } catch (err) {
      return '';
    }
  }

  function actionLabel(action) {
    const key = `company.activity.${String(action || '').replace(/\./g, '_')}`;
    const label = t(key);
    return label === key ? String(action || '') : label;
  }

  function countdown(purgeAfter, deletion) {
    const target = Number(purgeAfter || 0);
    if (!target) return '';
    const remaining = target - Math.floor(Date.now() / 1000);
    if (deletion && deletion.email_status !== 'SENT' && !deletion.download_confirmed_at) {
      return t('company.overview.deletion.waiting_download');
    }
    if (remaining <= 0) return t('company.overview.deletion.due');
    const days = Math.floor(remaining / 86400);
    const hours = Math.max(0, Math.floor((remaining % 86400) / 3600));
    if (days > 0) return t('company.overview.deletion.countdown_days', { days, hours });
    return t('company.overview.deletion.countdown_hours', { hours });
  }

  class CompanySetupOverview {
    constructor() {
      this.containerId = null;
      this.companyId = null;
      this.company = null;
      this.build = null;
      this.deletion = null;
      this.sources = null;
      this.connections = null;
      this.readiness = null;
      this.legal = null;
      this.events = null;
      this.files = null;
      this.loading = true;
      this.error = null;
      this.partialError = false;
      this.menuOpen = false;
      this._onLanguageChange = this._onLanguageChange.bind(this);
      this._onDocumentClick = this._onDocumentClick.bind(this);
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
    }

    render(containerOrId, companyId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;
      if (!container) return;
      this.containerId = container.id || this.containerId;
      if (companyId) this.companyId = String(companyId);
      if (!this.companyId) this.companyId = this._companyIdFromHash();
      if (!this.companyId) {
        this.loading = false;
        this.error = { code: 'NO_COMPANY', message: t('company.overview.error.no_company') };
        this._render();
        return;
      }
      this.loading = true;
      this.error = null;
      this._render();
      this._load();
    }

    destroy() {
      this.menuOpen = false;
      if (document && document.removeEventListener) {
        document.removeEventListener('click', this._onDocumentClick);
      }
    }

    _companyIdFromHash() {
      const hash = String(window.location.hash || '').replace(/^#/, '');
      const match = hash.match(/^\/company\/([^/]+)\/overview\/?$/);
      return match ? decodeURIComponent(match[1]) : null;
    }

    _onLanguageChange() {
      if (!this.containerId) return;
      const container = document.getElementById(this.containerId);
      if (container && container.querySelector('[data-company-overview]')) this._render();
    }

    _onDocumentClick(event) {
      if (!this.menuOpen) return;
      const menu = document.getElementById('zcOverviewMenu');
      const button = document.getElementById('zcOverviewMenuButton');
      if (menu && menu.contains(event.target)) return;
      if (button && button.contains(event.target)) return;
      this._closeMenu();
    }

    async _get(path) {
      try {
        const response = await fetch(path);
        let data = {};
        try { data = await response.json(); } catch (err) { data = {}; }
        return { ok: response.ok, status: response.status, data };
      } catch (err) {
        return { ok: false, status: 0, data: {}, offline: true };
      }
    }

    async _load() {
      const base = `/api/v1/companies/${encodeURIComponent(this.companyId)}`;
      const company = await this._get(base);
      if (!company.ok) {
        this.loading = false;
        this.error = {
          code: company.status === 404 ? 'NOT_FOUND' : (company.offline ? 'OFFLINE' : 'LOAD_FAILED'),
          message: company.status === 404
            ? t('company.overview.error.not_found')
            : (company.offline ? t('company.overview.error.offline') : t('company.overview.error.load'))
        };
        this._render();
        return;
      }
      this.company = company.data;
      this.build = company.data.build || null;
      this.deletion = company.data.deletion || null;

      const safe = (promise) => promise.catch(() => ({ ok: false, status: 0, data: {} }));
      const [sources, connections, readiness, legal, events, files] = await Promise.all([
        safe(this._get(`${base}/sources`)),
        safe(this._get(`${base}/connections`)),
        safe(this._get(`${base}/readiness`)),
        safe(this._get(`${base}/legal`)),
        safe(this._get(`${base}/audit?limit=12`)),
        safe(this._get(`${base}/files`))
      ]);
      this.sources = sources.ok ? sources.data : null;
      this.connections = connections.ok ? connections.data : null;
      this.readiness = readiness.ok ? readiness.data : null;
      this.legal = legal.ok ? legal.data : null;
      this.events = events.ok ? events.data : null;
      this.files = files.ok ? files.data : null;
      this.partialError = !sources.ok || !connections.ok || !legal.ok || !auditOk(events);
      this.loading = false;
      this._render();
    }

    // ------------------------------------------------------------- rendering
    _render() {
      const container = document.getElementById(this.containerId);
      if (!container) return;
      if (this.loading) {
        container.innerHTML = this._shell(this._loadingHtml());
        this._bind(container);
        return;
      }
      if (this.error) {
        container.innerHTML = this._shell(this._errorHtml());
        this._bind(container);
        return;
      }
      container.innerHTML = this._shell(this._overviewHtml());
      this._bind(container);
    }

    _shell(inner) {
      return `
        <div class="zc-flow-page zc-overview-page" data-company-overview>
          <div class="zc-flow-top">
            <button type="button" class="zc-back-link" id="zcOverviewBack">
              <span class="zc-back-arrow" aria-hidden="true">←</span>
              <span>${escapeHtml(t('company.overview.back'))}</span>
            </button>
            <div class="zc-language-toggle" role="group" aria-label="${escapeHtml(t('common.language'))}">
              <button type="button" data-language="en" aria-pressed="${language() === 'en' ? 'true' : 'false'}">${escapeHtml(t('common.english'))}</button>
              <button type="button" data-language="ar" aria-pressed="${language() === 'ar' ? 'true' : 'false'}">${escapeHtml(t('common.arabic'))}</button>
            </div>
          </div>
          ${inner}
        </div>
      `;
    }

    _loadingHtml() {
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(t('company.overview.title'))}</h1>
          <p class="zc-flow-subtitle" role="status">${escapeHtml(t('common.loading'))}</p>
        </header>
        <div class="zc-skeleton-stack" aria-hidden="true">
          <span class="zc-skeleton zc-skeleton-lg"></span>
          <span class="zc-skeleton"></span>
          <span class="zc-skeleton"></span>
        </div>
      `;
    }

    _errorHtml() {
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert">
          <strong>${escapeHtml(t('company.overview.error.title'))}</strong>
          <span>${escapeHtml(this.error && this.error.message ? this.error.message : t('company.overview.error.load'))}</span>
        </div>
        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcOverviewErrorBack">${escapeHtml(t('company.overview.back'))}</button>
          <button type="button" class="zc-button zc-button-primary" id="zcOverviewReload">${escapeHtml(t('common.retry'))}</button>
        </div>
      `;
    }

    _overviewHtml() {
      const company = this.company || {};
      const permissions = company.permissions || {};
      const status = normaliseStatus(company.status);
      const tone = STATUS_TONE[status] || 'neutral';
      const readOnly = !permissions.edit && !permissions.delete;
      return `
        <header class="zc-overview-header">
          <div class="zc-overview-heading">
            <p class="zc-eyebrow">${escapeHtml(t('company.overview.eyebrow'))}</p>
            <div class="zc-overview-title-row">
              <h1 class="zc-flow-title">${escapeHtml(company.name || t('company.overview.title'))}</h1>
              <span class="zc-pill zc-pill-${tone}">${escapeHtml(statusLabel(status))}</span>
            </div>
            <p class="zc-flow-subtitle">${escapeHtml(company.title || t('company.overview.subtitle'))}</p>
            <p class="zc-overview-meta">
              <span>${escapeHtml(company.industry || t('company.overview.unknown_industry'))}</span>
              <span aria-hidden="true">·</span>
              <span>${escapeHtml(company.type === 'EXISTING' ? t('company.overview.type.existing') : t('company.overview.type.new'))}</span>
              <span aria-hidden="true">·</span>
              <span>${escapeHtml(company.country || '—')}</span>
            </p>
          </div>
          <div class="zc-overview-actions">
            ${readOnly ? `<span class="zc-readonly-note">${escapeHtml(t('company.overview.readonly'))}</span>` : `
              <div class="zc-menu-wrap">
                <button type="button" class="zc-icon-button zc-overview-menu-button" id="zcOverviewMenuButton"
                  aria-haspopup="menu" aria-expanded="false" aria-controls="zcOverviewMenu" aria-label="${escapeHtml(t('company.overview.menu'))}">
                  <span aria-hidden="true">⋯</span>
                </button>
                <div class="zc-menu" id="zcOverviewMenu" role="menu" hidden>
                  ${permissions.edit ? `<button type="button" class="zc-menu-item" role="menuitem" data-overview-action="edit">${escapeHtml(t('company.overview.edit'))}</button>` : ''}
                  ${permissions.delete ? `<button type="button" class="zc-menu-item zc-menu-item-danger" role="menuitem" data-overview-action="delete">${escapeHtml(t('company.overview.delete'))}</button>` : ''}
                </div>
              </div>
            `}
          </div>
        </header>

        ${this._buildHintHtml()}
        ${this._deletionBannerHtml()}
        ${this.partialError ? `<div class="zc-inline-notice zc-inline-notice-muted" role="status">${escapeHtml(t('company.overview.partial'))}</div>` : ''}

        <div class="zc-overview-grid">
          ${this._identityCardHtml()}
          ${this._numbersCardHtml()}
          ${this._progressCardHtml()}
          ${this._sourcesCardHtml()}
          ${this._legalCardHtml()}
          ${this._activityCardHtml()}
        </div>

        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcOverviewWorkspace">${escapeHtml(t('company.overview.open_workspace'))}</button>
        </div>
        <p class="zc-form-footnote">${escapeHtml(t('company.overview.footnote'))}</p>
      `;
    }

    _buildHintHtml() {
      const build = this.build;
      if (!build || String(build.phase_state || '').toUpperCase() !== 'RUNNING') return '';
      return `
        <div class="zc-inline-notice zc-inline-notice-muted" role="status">
          ${escapeHtml(t('company.overview.build_running'))}
        </div>
      `;
    }

    _deletionBannerHtml() {
      const deletion = this.deletion;
      if (!deletion) return '';
      const status = String(deletion.status || '');
      return `
        <section class="zc-deletion-banner" role="status" aria-live="polite">
          <div class="zc-deletion-banner-body">
            <strong>${escapeHtml(t('company.overview.deletion.title'))}</strong>
            <span>${escapeHtml(t(`company.delete.status.${status.toLowerCase()}`, { status }))}</span>
            <span class="zc-deletion-countdown">${escapeHtml(countdown(deletion.purge_after, deletion))}</span>
          </div>
          <div class="zc-deletion-banner-actions">
            ${deletion.export_available ? `<button type="button" class="zc-button zc-button-quiet" data-overview-action="download">${escapeHtml(t('company.overview.deletion.download'))}</button>` : ''}
            <button type="button" class="zc-button zc-button-quiet zc-button-danger" data-overview-action="delete">${escapeHtml(t('company.overview.deletion.manage'))}</button>
          </div>
        </section>
      `;
    }

    _identityCardHtml() {
      const company = this.company || {};
      const owner = company.owner || {};
      return `
        <section class="zc-overview-card">
          <h2 class="zc-section-title">${escapeHtml(t('company.overview.identity.title'))}</h2>
          <dl class="zc-overview-list">
            <div><dt>${escapeHtml(t('company.overview.identity.status'))}</dt><dd>${escapeHtml(statusLabel(company.status))}</dd></div>
            <div><dt>${escapeHtml(t('company.overview.identity.owner'))}</dt><dd>${escapeHtml(owner.name || '—')}${owner.role ? ` · ${escapeHtml(owner.role)}` : ''}</dd></div>
            <div><dt>${escapeHtml(t('company.overview.identity.email'))}</dt><dd>${escapeHtml(owner.email || '—')}</dd></div>
            <div><dt>${escapeHtml(t('company.overview.identity.website'))}</dt><dd>${company.website ? `<a href="${escapeHtml(company.website)}" target="_blank" rel="noopener noreferrer">${escapeHtml(company.website)}</a>` : '—'}</dd></div>
            <div><dt>${escapeHtml(t('company.overview.identity.created'))}</dt><dd>${escapeHtml(formatTime(company.created_at) || '—')}</dd></div>
            <div><dt>${escapeHtml(t('company.overview.identity.updated'))}</dt><dd>${escapeHtml(formatTime(company.updated_at) || '—')}</dd></div>
          </dl>
          ${company.description ? `<p class="zc-overview-description">${escapeHtml(company.description)}</p>` : ''}
        </section>
      `;
    }

    _numbersCardHtml() {
      const company = this.company || {};
      const revenue = company.revenue || {};
      const readiness = this.readiness || {};
      const counts = readiness.counts || {};
      const files = this.files && typeof this.files.total === 'number' ? this.files.total : Number(counts.files || 0);
      const connections = this.connections && Array.isArray(this.connections.connections) ? this.connections.connections.length : Number(counts.sources_connected || 0);
      return `
        <section class="zc-overview-card">
          <h2 class="zc-section-title">${escapeHtml(t('company.overview.numbers.title'))}</h2>
          <div class="zc-overview-metrics">
            <div class="zc-metric">
              <span class="zc-metric-label">${escapeHtml(t('company.overview.numbers.revenue'))}</span>
              <span class="zc-metric-value">${escapeHtml(revenue.amount != null ? money(revenue.amount, revenue.currency || company.currency) : '—')}</span>
              <span class="zc-metric-note">${escapeHtml(revenue.period || '')}</span>
            </div>
            <div class="zc-metric">
              <span class="zc-metric-label">${escapeHtml(t('company.overview.numbers.readiness'))}</span>
              <span class="zc-metric-value">${readiness.score != null ? `${Number(readiness.score)}` : '—'}<small>/100</small></span>
              <span class="zc-metric-note">${escapeHtml(readiness.band ? String(readiness.band) : '')}</span>
            </div>
            <div class="zc-metric">
              <span class="zc-metric-label">${escapeHtml(t('company.overview.numbers.connections'))}</span>
              <span class="zc-metric-value">${connections}</span>
              <span class="zc-metric-note">${escapeHtml(t('company.overview.numbers.readonly'))}</span>
            </div>
            <div class="zc-metric">
              <span class="zc-metric-label">${escapeHtml(t('company.overview.numbers.files'))}</span>
              <span class="zc-metric-value">${files}</span>
              <span class="zc-metric-note">${escapeHtml(t('company.overview.numbers.evidence'))}</span>
            </div>
          </div>
        </section>
      `;
    }

    _progressCardHtml() {
      const build = this.build;
      if (!build) {
        return `
          <section class="zc-overview-card">
            <h2 class="zc-section-title">${escapeHtml(t('company.overview.progress.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.overview.progress.empty'))}</p>
          </section>
        `;
      }
      const percent = Math.max(0, Math.min(100, Number(build.progress_percent || 0)));
      const phases = Array.isArray(build.phases) ? build.phases : [];
      return `
        <section class="zc-overview-card">
          <h2 class="zc-section-title">${escapeHtml(t('company.overview.progress.title'))}</h2>
          <div class="zc-overview-progress-top">
            <span class="zc-pill zc-pill-${build.phase_state === 'DONE' ? 'green' : (build.phase_state === 'FAILED' ? 'red' : 'neutral')}">${escapeHtml(String(build.phase_state || '—'))}</span>
            <span class="zc-overview-percent">${percent}%</span>
          </div>
          <div class="zc-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" aria-label="${escapeHtml(t('company.overview.progress.title'))}">
            <span class="zc-progress-fill" style="width: ${percent}%"></span>
          </div>
          <ol class="zc-overview-phases">
            ${phases.slice(0, 8).map((phase) => `
              <li class="zc-overview-phase zc-phase-${escapeHtml(String(phase.state || 'PENDING').toLowerCase())}">
                <span class="zc-overview-phase-dot" aria-hidden="true"></span>
                <span>${escapeHtml(phase.label || phase.id || '')}</span>
                <span class="zc-overview-phase-state">${escapeHtml(String(phase.state || ''))}</span>
              </li>
            `).join('')}
          </ol>
          <button type="button" class="zc-link-button" data-overview-action="build">${escapeHtml(t('company.overview.progress.open'))}</button>
        </section>
      `;
    }

    _sourcesCardHtml() {
      const sources = this.sources && Array.isArray(this.sources.sources) ? this.sources.sources : [];
      const connections = this.connections && Array.isArray(this.connections.connections) ? this.connections.connections : [];
      return `
        <section class="zc-overview-card">
          <h2 class="zc-section-title">${escapeHtml(t('company.overview.sources.title'))}</h2>
          ${sources.length ? `
            <ul class="zc-overview-sources">
              ${sources.map((source) => `
                <li class="zc-overview-source">
                  <span class="zc-overview-source-name">${escapeHtml(source.name || source.id)}</span>
                  <span class="zc-pill zc-pill-${source.status === 'VERIFIED' ? 'green' : (source.status === 'SKIPPED' ? 'orange' : 'neutral')}">${escapeHtml(t(`company.overview.source.${String(source.status || 'NOT_STARTED').toLowerCase()}`))}</span>
                </li>
              `).join('')}
            </ul>
          ` : `<p class="zc-section-note">${escapeHtml(t('company.overview.sources.empty'))}</p>`}
          ${connections.length ? `
            <h3 class="zc-overview-subtitle">${escapeHtml(t('company.overview.connections.title'))}</h3>
            <ul class="zc-overview-connections">
              ${connections.slice(0, 8).map((connection) => `
                <li>
                  <span>${escapeHtml(connection.name || connection.provider_id || connection.connection_id)}</span>
                  <span class="zc-overview-connection-status">${escapeHtml(String(connection.status || ''))}${connection.verified_at ? ` · ${escapeHtml(t('company.overview.connections.verified'))}` : ''}</span>
                </li>
              `).join('')}
            </ul>
          ` : ''}
        </section>
      `;
    }

    _legalCardHtml() {
      const items = this.legal && Array.isArray(this.legal.legal_items) ? this.legal.legal_items : [];
      return `
        <section class="zc-overview-card">
          <h2 class="zc-section-title">${escapeHtml(t('company.overview.legal.title'))}</h2>
          ${items.length ? `
            <ul class="zc-overview-legal">
              ${items.map((item) => `
                <li>
                  <span class="zc-overview-legal-name">${escapeHtml(item.name || '')}</span>
                  <span class="zc-overview-legal-status">${escapeHtml(item.status || '')}</span>
                  ${item.draft_disclaimer ? `<span class="zc-overview-legal-note">${escapeHtml(item.draft_disclaimer)}</span>` : ''}
                </li>
              `).join('')}
            </ul>
          ` : `<p class="zc-section-note">${escapeHtml(t('company.overview.legal.empty'))}</p>`}
        </section>
      `;
    }

    _activityCardHtml() {
      const events = this.events && Array.isArray(this.events.events) ? this.events.events : [];
      return `
        <section class="zc-overview-card zc-overview-card-wide">
          <h2 class="zc-section-title">${escapeHtml(t('company.overview.activity.title'))}</h2>
          ${events.length ? `
            <ol class="zc-overview-activity">
              ${events.map((event) => `
                <li>
                  <span class="zc-overview-activity-dot" aria-hidden="true"></span>
                  <span class="zc-overview-activity-body">
                    <span class="zc-overview-activity-action">${escapeHtml(actionLabel(event.action))}</span>
                    <span class="zc-overview-activity-meta">${escapeHtml(event.actor_role || '')} · ${escapeHtml(formatTime(event.created_at))}</span>
                  </span>
                </li>
              `).join('')}
            </ol>
          ` : `<p class="zc-section-note">${escapeHtml(t('company.overview.activity.empty'))}</p>`}
        </section>
      `;
    }

    // -------------------------------------------------------------- binding
    _bind(container) {
      const back = container.querySelector('#zcOverviewBack');
      if (back) back.addEventListener('click', () => this._go('/company'));
      const errorBack = container.querySelector('#zcOverviewErrorBack');
      if (errorBack) errorBack.addEventListener('click', () => this._go('/company'));
      const reload = container.querySelector('#zcOverviewReload');
      if (reload) reload.addEventListener('click', () => {
        this.loading = true;
        this.error = null;
        this._render();
        this._load();
      });

      container.querySelectorAll('[data-language]').forEach((button) => {
        button.addEventListener('click', () => {
          if (window.I18n && window.I18n.setLanguage) window.I18n.setLanguage(button.getAttribute('data-language'));
        });
      });

      const menuButton = container.querySelector('#zcOverviewMenuButton');
      const menu = container.querySelector('#zcOverviewMenu');
      if (menuButton && menu) {
        menuButton.addEventListener('click', (event) => {
          event.stopPropagation();
          this._toggleMenu();
        });
        menu.addEventListener('keydown', (event) => this._menuKeydown(event));
      }

      container.querySelectorAll('[data-overview-action]').forEach((button) => {
        button.addEventListener('click', () => this._action(button.getAttribute('data-overview-action')));
      });

      const workspace = container.querySelector('#zcOverviewWorkspace');
      if (workspace) workspace.addEventListener('click', () => {
        if (window.CompanyWorkspace && window.CompanyWorkspace.setSubtab) {
          window.CompanyWorkspace.setSubtab('intelligence', this.companyId);
        } else {
          this._go(`/company/${encodeURIComponent(this.companyId)}/intelligence`);
        }
      });
    }

    _toggleMenu() {
      this.menuOpen = !this.menuOpen;
      this._applyMenu();
    }

    _closeMenu() {
      this.menuOpen = false;
      this._applyMenu();
    }

    _applyMenu() {
      const button = document.getElementById('zcOverviewMenuButton');
      const menu = document.getElementById('zcOverviewMenu');
      if (!button || !menu) return;
      button.setAttribute('aria-expanded', this.menuOpen ? 'true' : 'false');
      menu.hidden = !this.menuOpen;
      if (this.menuOpen) {
        const first = menu.querySelector('[role="menuitem"]');
        if (first) first.focus();
        document.addEventListener('click', this._onDocumentClick);
      } else if (document.removeEventListener) {
        document.removeEventListener('click', this._onDocumentClick);
      }
    }

    _menuKeydown(event) {
      const items = Array.from(document.querySelectorAll('#zcOverviewMenu [role="menuitem"]'));
      const index = items.indexOf(document.activeElement);
      if (event.key === 'Escape') {
        event.preventDefault();
        this._closeMenu();
        const button = document.getElementById('zcOverviewMenuButton');
        if (button) button.focus();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        const next = items[(index + 1) % items.length];
        if (next) next.focus();
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        const prev = items[(index - 1 + items.length) % items.length];
        if (prev) prev.focus();
      }
    }

    _action(action) {
      this._closeMenu();
      if (action === 'edit') {
        this._go(`/company/${encodeURIComponent(this.companyId)}/edit`);
        return;
      }
      if (action === 'build') {
        this._go(`/company/${encodeURIComponent(this.companyId)}/build`);
        return;
      }
      if (action === 'download') {
        if (window.CompanySetupDelete && window.CompanySetupDelete.open) {
          window.CompanySetupDelete.open({
            companyId: this.companyId,
            companyName: this.company ? this.company.name : '',
            startAt: 'export',
            onDone: () => this.render(this.containerId, this.companyId)
          });
        }
        return;
      }
      if (action === 'delete') {
        if (window.CompanySetupDelete && window.CompanySetupDelete.open) {
          window.CompanySetupDelete.open({
            companyId: this.companyId,
            companyName: this.company ? this.company.name : '',
            onDone: () => this.render(this.containerId, this.companyId)
          });
        }
      }
    }

    _go(path) {
      if (typeof window.navigateTo === 'function') {
        window.navigateTo(path);
      } else {
        window.location.hash = `#${path}`;
      }
    }
  }

  function auditOk(result) {
    return !!(result && result.ok);
  }

  const overview = new CompanySetupOverview();
  window.CompanySetupOverview = overview;
})();
